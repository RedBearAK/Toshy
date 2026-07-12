import time
import inspect

from evdev import ecodes, InputEvent
from dataclasses import dataclass

from . import pointer_monitor
from .config_api import (
    _ENVIRON,
    _REPEATING_KEYS,
    escape_next_key,
    escape_next_combo,
    ignore_key,
    get_configuration,
)
from .layout_correction import (
    correct_key_for_match,
    decorrect_key_for_output,
    get_correction_map,
    xkb_symbol_for_key,
)
from .lib import logger
from .lib.asyncio_utils import get_or_create_event_loop
from .lib.key_context import KeyContext
from .lib.logger import debug
from .models.action import Action
from .models.combo import Combo, ComboHint, PreCorrectedCombo
from .models.trigger import Trigger
from .models.key import Key
from .models.keymap import Keymap
from .models.keystate import Keystate
from .models.modifier import Modifier
from .models.modmap import Modmap, MultiModmap
from .output import Output

_MODMAPS: list[Modmap] = None
_MULTI_MODMAPS: list[MultiModmap] = None
_KEYMAPS: list[Keymap] = None
_TIMEOUTS = None

def boot_config():
    global _MODMAPS
    global _MULTI_MODMAPS
    global _KEYMAPS
    global _TIMEOUTS
    _MODMAPS, _MULTI_MODMAPS, _KEYMAPS, _TIMEOUTS = \
        get_configuration()


# ============================================================ #


_active_keymaps = None
_output = Output()
_key_states: dict[Key, Keystate] = {}
_sticky = {}



@dataclass
class RepeatCache:
    """
    Cache for repeat key remapping results to avoid redundant transform_key() evaluation.

    ONLY caches simple outputs:
    - 'passthrough': Direct key passthrough (no remapping)
    - 'combo': Single Combo output
    - 'key': Single Key output

    Does NOT cache:
    - Callables/functions (need re-evaluation for fresh state)
    - Action lists (complex to track, rarely meant to repeat)
    - Nested keymaps (stateful)

    These complex cases fall back to normal evaluation path (no performance loss,
    just no cache benefit). Most performance gain comes from simple repeating
    shortcuts like cursor movement (Emacs Ctrl+F/B) or gaming (WASD remaps).

    Cached on key PRESS, replayed on REPEAT, invalidated on:
    - Different key press
    - Modifier state change
    - Key release
    - Nested keymap entry

    Attributes:
        inkey: Input key that was remapped
        mods_held: Frozen snapshot of modifiers at press time (tuple of Key objects)
        output_type: 'passthrough', 'combo', or 'key'
        output_data: Replayable output - Key | Combo | tuple[Key, Action]
        valid: Quick invalidation flag
    """
    inkey: Key
    mods_held: tuple
    output_type: str
    output_data: "Key | Combo | tuple[Key, Action]"
    valid: bool = True


@dataclass
class HeldComboContext:
    """
    Context for a combo output being held on the virtual keyboard for
    compositor-driven repeat.

    Created on the first repeat event when the output is a single Combo.
    The output key and modifiers stay pressed on the virtual device, and
    incoming repeat events are suppressed. The compositor drives repeat
    at the DE-configured rate.

    Teardown fires when:
    - The trigger key is released (normal case).
    - Any new key is pressed (interleaved input).
    - An input modifier from the original combo is released while the
        trigger key is still held.

    Attributes:
        trigger_key:          Input key whose release triggers teardown.
        output_combo:         The Combo being held on output.
        released_input_mods:  Input modifier Keys that were lifted during setup.
        pressed_output_mods:  Output modifier Keys that were pressed during setup.
        output_key:           The non-modifier Key held on output.
        setup_time:           time.time() at setup, for duration logging.
        suppress_count:       Number of input repeat events suppressed during sustain.
    """
    trigger_key:            "Key"
    output_combo:           "Combo"
    released_input_mods:    "list[Key]"
    pressed_output_mods:    "list[Key]"
    output_key:             "Key"
    setup_time:             float
    suppress_count:         int = 0


_repeat_cache: "RepeatCache | None"         = None
_modifiers_changed_since_cache              = False
_awaiting_first_repeat_key                  = None
_first_repeat_processed                     = False
_held_combo_ctx: "HeldComboContext | None"  = None


def invalidate_repeat_cache():
    """Invalidate the repeat cache, forcing re-evaluation on next repeat."""
    global _repeat_cache, _first_repeat_processed
    if _repeat_cache is not None:
        _repeat_cache.valid = False
        _first_repeat_processed = False
        if logger.VERBOSE:
            debug("Repeat cache invalidated")


def _get_modifier_snapshot():
    """
    Get current modifier state as a hashable tuple for cache comparison.
    Returns tuple of pressed modifier Key objects, sorted for consistent comparison.
    """
    mod_keys = [x.key for x in _key_states.values() if x.key_is_pressed]
    mod_keys = [x for x in mod_keys if Modifier.is_key_modifier(x)]
    return tuple(sorted(mod_keys, key=lambda k: k.value))


def try_replay_cached_repeat(key: Key, action: Action):
    """
    Attempt to replay cached remapping result for repeat events.
    Returns True if cache hit and replay succeeded, False otherwise.

    OPTIMIZED: Only checks modifier state if _modifiers_changed_since_cache flag is set.
    This reduces repeat overhead from ~15-25 ops to ~5-10 ops in common case.
    """
    global _repeat_cache, _modifiers_changed_since_cache

    # No cache or cache invalidated
    if _repeat_cache is None or not _repeat_cache.valid:
        return False

    # Different key repeating
    if key != _repeat_cache.inkey:
        return False

    # OPTIMIZATION: Only check modifier state if flag indicates change
    if _modifiers_changed_since_cache:
        current_mods = _get_modifier_snapshot()
        _modifiers_changed_since_cache = False  # Clear flag after checking

        if current_mods != _repeat_cache.mods_held:
            # Mods changed mid-repeat - invalidate and force re-evaluation
            invalidate_repeat_cache()
            if logger.VERBOSE:
                debug("Modifier state changed during repeat - cache invalidated")
            return False

    # Cache hit! Replay the cached output
    if logger.VERBOSE:
        debug(f"Repeat cache HIT for {key} - replaying cached {_repeat_cache.output_type}")

    # Replay based on output type
    if _repeat_cache.output_type == 'passthrough':
        # For passthrough, send the current action (not the cached one)
        _output.send_key_action_fast(key, action)
    elif _repeat_cache.output_type == 'combo':
        _output.send_combo(_repeat_cache.output_data)
    elif _repeat_cache.output_type == 'key':
        _output.send_key(_repeat_cache.output_data)
    else:
        # Unknown type - shouldn't happen, but fall back to normal evaluation
        debug(f"Unknown cache output_type: {_repeat_cache.output_type}")
        return False

    return True


def populate_repeat_cache(key: Key, action: Action):
    """
    Populate the repeat cache from output tracking after successful transform.
    Only caches simple outputs (passthrough, combo, key).
    Complex outputs (callables, lists, nested keymaps) are not cached.

    NOW CALLED ON FIRST REPEAT (not on PRESS) to avoid overhead for keys that don't repeat.
    """
    global _repeat_cache, _modifiers_changed_since_cache, _awaiting_first_repeat_key

    # Only cache on first REPEAT event (not press)
    if not action.is_repeat:
        return

    # Check if output was tracked (from previous PRESS event)
    if _output._last_output_for_cache is None:
        _awaiting_first_repeat_key = None  # Clear awaiting flag
        return

    output_type, output_data = _output._last_output_for_cache

    # Only cache simple output types
    if output_type not in ('passthrough', 'combo', 'key'):
        _awaiting_first_repeat_key = None  # Clear awaiting flag
        _output.clear_cache_tracking()
        return

    # Don't cache when in nested keymap state
    if _active_keymaps is not None and _active_keymaps not in (escape_next_key, escape_next_combo):
        # Check if _active_keymaps is a list and not the top-level KEYMAPS
        if isinstance(_active_keymaps, list) and _active_keymaps != _KEYMAPS:
            _awaiting_first_repeat_key = None  # Clear awaiting flag
            _output.clear_cache_tracking()
            return

    # Get current modifier snapshot
    mods_snapshot = _get_modifier_snapshot()

    # Create the cache
    _repeat_cache = RepeatCache(
        inkey=key,
        mods_held=mods_snapshot,
        output_type=output_type,
        output_data=output_data,
        valid=True
    )

    # Reset modifier change flag since we just cached current state
    _modifiers_changed_since_cache = False

    # Clear awaiting flag
    _awaiting_first_repeat_key = None

    if logger.VERBOSE:
        debug(f"First repeat: Cache populated: {key} -> {output_type} with {len(mods_snapshot)} mods")

    # Clear the output tracking now that cache is populated
    _output.clear_cache_tracking()


def teardown_held_combo():
    """
    Tear down an active held combo, releasing the output key and modifiers,
    and restoring input modifiers that are still physically held.

    Safe to call when no held combo is active (no-op).
    Logs a summary line with hold duration and suppressed repeat count.
    """
    global _held_combo_ctx
    if _held_combo_ctx is None:
        return

    ctx = _held_combo_ctx
    _held_combo_ctx = None

    # Build a set of currently-pressed output-side identities. Keystates are
    # keyed on inkey (pre-modmap), but released_input_mods came from the
    # output side (_pressed_modifier_keys, post-modmap), so we have to
    # match on keystate.key, not the dict key.
    pressed_output_keys = {
        ks.key for ks in _key_states.values() if ks.key_is_pressed
    }

    mods_to_restore = [
        k for k in ctx.released_input_mods
        if k in pressed_output_keys
    ]

    _output.send_combo_held_teardown(
        ctx.output_key,
        ctx.pressed_output_mods,
        mods_to_restore,
    )

    duration = time.time() - ctx.setup_time
    debug(
        f"Held combo teardown: {ctx.output_key} held {duration:.2f}s, "
        f"suppressed {ctx.suppress_count} repeats"
    )


def reset_transform():
    global _active_keymaps
    global _output
    global _key_states
    global _sticky
    global _repeat_cache
    global _modifiers_changed_since_cache
    global _awaiting_first_repeat_key
    global _first_repeat_processed
    global _held_combo_ctx
    _active_keymaps                     = None
    _output                             = Output()
    _key_states                         = {}
    _sticky                             = {}
    _repeat_cache                       = None
    _modifiers_changed_since_cache      = False
    _awaiting_first_repeat_key          = None
    _first_repeat_processed             = False
    _held_combo_ctx                     = None


def shutdown():
    teardown_held_combo()
    _output.shutdown()

# ============================================================ #


def none_pressed():
    return len(_key_states) == 0


def get_pressed_mods():
    # Changing Keystate.is_pressed() to use property decorator, for consistency.
    keys = [x.key for x in _key_states.values() if x.key_is_pressed]
    keys = [x for x in keys if Modifier.is_key_modifier(x)]
    return [Modifier.from_key(key) for key in keys]


def get_pressed_states():
    # Changing Keystate.is_pressed() to use property decorator, for consistency.
    return [x for x in _key_states.values() if x.key_is_pressed]


def is_sticky(key):
    for k in _sticky.keys():
        if k == key:
            return True
    return False


def update_pressed_states(keystate: Keystate):
    # release
    if keystate.action == Action.RELEASE:
        # pop() returns None if key not found, avoiding possible KeyError
        # Removed try/except and debug line, because ALL keys come in 
        # here now, when released. Excessive/irrelevant logging resulted.
        _key_states.pop(keystate.inkey, None)

    # press / add
    if keystate.inkey not in _key_states:
        # add state
        if keystate.action == Action.PRESS:
            _key_states[keystate.inkey] = keystate
        return


# ─── SUSPEND AND RESUME INPUT SIDE ──────────────────────────────────────────────


# keep track of how long until we need to resume the input
# and send held keys to the output (that haven't been used
# as part of a combo)
_suspend_timer = None
_last_suspend_timeout = 0


def resume_keys():
    global _last_suspend_timeout
    global _suspend_timer
    if not is_suspended():
        return

    _suspend_timer.cancel()
    _last_suspend_timeout = 0
    _suspend_timer = None
    pointer_monitor.unlisten()

    # keys = get_suspended_mods()
    states: list[Keystate] = [x for x in _key_states.values() if x.suspended]
    if len(states) > 0:
        debug("resuming keys:", [x.key for x in states])

    for ks in states:
        # spent keys that are held long enough to resume
        # no longer count as spent
        ks.spent = False
        # sticky keys (input side) remain silently held
        # and are only lifted when they are lifted from the input
        ks.suspended = False
        if ks.key in _sticky:
            continue

        # if some other key PRESS is waking us up then we must be a modifier (we
        # know because if we were waking ourself it would happen in on_key)
        # but if a key RELEASE is waking us then we still might be momentary -
        # IF we were still the last key that was pressed

        # EVENT-BASED LOGIC: Use the flag instead of complicated heuristics
        if ks.is_multi:
            # Check if another key was pressed while this multikey was held
            if ks.other_key_pressed_while_held:
                # Another key was pressed → resolve as modifier
                ks.resolve_as_modifier()
            else:
                # Timeout reached but no other key pressed
                # Treat as modifier (timeout fallback behavior)
                # This handles the case where user just holds the key down
                other_mods = [e.key for e in states if e.key != ks.key]
                special_shift_case = (
                    len(other_mods) == 1
                    and other_mods[0] in Modifier.SHIFT.keys
                    and ks.multikey in Modifier.SHIFT.keys
                    and _last_key == ks.key
                )
                if not special_shift_case:
                    ks.resolve_as_modifier()
                else:
                    # Special case: keep as momentary
                    pass

        if not ks.exerted_on_output:
            ks.exerted_on_output = True
            _output.send_key_action(ks.key, Action.PRESS)


def is_suspended():
    return _suspend_timer is not None


def resuspend_keys(timeout):
    # we should not be able to resuspend for a shorter timeout, ie
    # a multi timeout of 1s should not be overruled by a shorter timeout
    if is_suspended():
        if timeout < _last_suspend_timeout:
            return
    _suspend_timer.cancel()
    debug("resuspending keys")
    suspend_keys(timeout)


def pressed_mods_not_exerted_on_output():
    return [key for key in get_pressed_mods() if not _output.is_mod_pressed(key)]


def suspend_or_resuspend_keys(timeout):
    if is_suspended():
        resuspend_keys(timeout)
    else:
        suspend_keys(timeout)


def suspend_keys(timeout):
    global _suspend_timer
    global _last_suspend_timeout

    debug("suspending keys:", pressed_mods_not_exerted_on_output())

    # Changed Keystate.key_is_pressed() to use property decorator, for consistency.
    states: list[Keystate] = [x for x in _key_states.values() if x.key_is_pressed]
    for s in states:
        s.suspended = True

    loop = get_or_create_event_loop()

    _last_suspend_timeout = timeout
    _suspend_timer = loop.call_later(timeout, resume_keys)

    pointer_monitor.listen(loop, resume_keys)

    # Motionless-click rescue: if the pointer was used just before this
    # modifier press, treat it as pointer-combo intent and resume now,
    # so a click with no motion of its own still lands on a held mod.
    if pointer_monitor.recent_activity_within():
        debug("resume because of recent pointer activity before mod press")
        resume_keys()


# ─── DUMP DIAGNOSTICS ────────────────────────────────────────────────────────


def dump_diagnostics():
    print("*** TRANSFORM  ***")
    print(f"are we suspended: {is_suspended()}")
    print("_suspend_timer:")
    print(_suspend_timer)
    print("_last_key:")
    print(_last_key)
    print("_key_states:")
    print(_key_states)
    print("_sticky:")
    print(_sticky)
    _output.diag()
    print("")


# ─── COMBO CONTEXT LOGGING ────────────────────────────────────────────────────────


def log_combo_context(combo, ctx: KeyContext, keymap: Keymap, _active_keymaps: list[Keymap]):
    """Log context around usage of combo"""
    import textwrap

    debug("")
    debug(f"WM_CLASS: '{ctx.wm_class}' | WM_NAME: '{ctx.wm_name}'")
    debug(f"DEVICE: '{ctx.device_name}' | CAPS_LOCK: '{ctx.capslock_on}' | NUM_LOCK: '{ctx.numlock_on}'")
    debug(f'ACTIVE KEYMAPS:')

    indent = ' ' * 5
    max_len = max(80 - len(indent), 64)
    wrapped_items = textwrap.wrap(", ".join([f"'{item.name}'" for item in _active_keymaps]), width=max_len)
    output_str = f"{indent}{wrapped_items[0]}"
    for item in wrapped_items[1:]:
        if not item.startswith("'"):
            item = ' … ' + item
        output_str += f"\n{indent}{item}"
    print(output_str)

    debug(f"COMBO: {combo} => {keymap[combo]} in KMAP: '{keymap.name}'")


# ─── KEYBOARD INPUT PROCESSING HELPERS ──────────────────────────────────────────


# last key that sent a PRESS event (used to track press/release of multi-keys
# to decide to use their temporary form)
_last_key = None


# translate keycode (like xmodmap)
def apply_modmap(keystate: Keystate, ctx: KeyContext):
    inkey = keystate.inkey
    keystate.key = inkey
    # first modmap is always the default, unconditional
    active_modmap = _MODMAPS[0]
    # debug("active", active_modmap)
    conditional_modmaps: list[Modmap] = _MODMAPS[1:]
    # debug("conditionals", conditional_modmaps)
    if conditional_modmaps:
        for modmap in conditional_modmaps:
            if inkey in modmap:
                if modmap.conditional(ctx):
                    active_modmap = modmap
                    break
    if active_modmap and inkey in active_modmap:
        debug(f"MODMAP: {inkey} => {active_modmap[inkey]} [{active_modmap.name}]")
        keystate.key = active_modmap[inkey]


def apply_multi_modmap(keystate: Keystate, ctx: KeyContext):
    active_multi_modmap = _MULTI_MODMAPS[0]
    conditional_multimaps: list[MultiModmap] = _MULTI_MODMAPS[1:]
    if conditional_multimaps:
        for modmap in conditional_multimaps:
            if keystate.inkey in modmap:
                if modmap.conditional(ctx):
                    active_multi_modmap = modmap
                    break

    if active_multi_modmap:
        if keystate.key in active_multi_modmap:
            momentary, held, _ = active_multi_modmap[keystate.key]
            keystate.key = momentary
            keystate.multikey = held
            keystate.is_multi = True

            # Log the multipurpose mapping
            held_mod_name = Modifier.get_modifier_name(held)
            held_suffix = f" ({held_mod_name} mod)" if held_mod_name else ""
            debug(f"MULTI_MODMAP: {keystate.inkey} => {momentary} / {held}{held_suffix} [{active_multi_modmap.name}]")


JUST_KEYS = []
JUST_KEYS.extend([Key[x] for x in "QWERTYUIOPASDFGHJKLZXCVBNM"])


# from .lib.benchit import *
def find_keystate_or_new(inkey, action):
    if inkey not in _key_states:
        return Keystate(inkey=inkey, action=action)

    keystate: Keystate = _key_states[inkey]
    keystate.prior = keystate.copy()
    delattr(keystate.prior, "prior")
    keystate.action = action
    keystate.time = time
    return keystate


# ─── KEYBOARD INPUT PROCESSING PIPELINE ─────────────────────────────────────────

# The input processing pipeline:
#
# - on_event
#   - forward non key events
#   - modmapping
#   - multi-mapping
# - on_key
#   - on_mod_key
#   - suspend/resume, etc
# - transform_key
# - handle_commands
#   - process the actual combos, commands


session_type    = _ENVIRON['session_type']
wl_compositor   = _ENVIRON['wl_compositor']

from .lib.window_context import WindowContextProviderInterface as WCPI

window_context                  = WCPI.make_provider(session_type, wl_compositor)
_last_press_ctx_data            = {"wm_class": "", "wm_name": "", "wndw_ctxt_error": False}

ignore_repeating_keys = _REPEATING_KEYS['ignore_repeating_keys']


# @benchit
def on_event(event: InputEvent, device):
    global _last_press_ctx_data, _awaiting_first_repeat_key, _first_repeat_processed

    # Early exit for non-key events - they should not touch cache tracking
    if event.type != ecodes.EV_KEY or device is None:
        # Wheel scroll on a grabbed pointer device signals pointer intent,
        # same as the pointer monitor does for ungrabbed devices. Guard
        # ordering matters: is_suspended() is the cheapest test and almost
        # always False, and this branch runs on every motion event from
        # every grabbed pointer device.
        if (is_suspended()
                and event.type == ecodes.EV_REL
                and event.code in pointer_monitor.TRIGGER_REL_CODES):
            debug("resume because of wheel scroll on grabbed device")
            resume_keys()
        _output.send_event(event)
        return

    # Now we know it's a key event - safe to do clear/preserve logic
    key_code = event.code

    # Clear tracking in most cases - preserve only when awaiting first repeat
    if (_awaiting_first_repeat_key is None 
        or _first_repeat_processed
        or key_code != _awaiting_first_repeat_key):
        _output.clear_cache_tracking()

    # Get action for knowing about repeats, press/release
    action = Action(event.value)

    # EXPERIMENTAL: Pass through "repeat" key events without further processing, blindly.
    # Drastically decreases CPU usage when holding a non-modifier key down (e.g., gaming).
    # This blind passthrough can be enabled using the ignore_repeating_keys() API function
    # in the user's config file, like so: ignore_repeating_keys(True)
    if ignore_repeating_keys and action.is_repeat:
        if logger.VERBOSE:
            print()     # give some space from regular event blocks in the log
            debug(
                "### Passing through repeating key event unprocessed to reduce CPU usage. ###", 
                ctx="--"
            )
        _output.send_event(event)
        return

    key = Key(event.code)
    keystate = find_keystate_or_new(inkey=key, action=action)

    # This blank line separates each logging block from the
    # previous block for better readability.
    debug()

    if action.is_released or action.is_repeat:
        ctx = KeyContext.from_cache(device, _last_press_ctx_data)
    else:
        ctx = KeyContext(device, window_context)
        if action.just_pressed:
            _last_press_ctx_data = {
                "wm_class": ctx.wm_class,
                "wm_name": ctx.wm_name,
                "wndw_ctxt_error": ctx.wndw_ctxt_error
            }

    debug(f"in {key} ({action})", ctx="II")

    # if there is a window context error (we don't have any window context)
    # then we turn off all mappings until it's resolved and act
    # more or less as a pass thru for all input => output
    if ctx.wndw_ctxt_error:
        keystate.key = keystate.key or keystate.inkey

    # we only do modmap on the PRESS pass, keys may not
    # redefine themselves midstream while repeating or
    # as they are lifted
    if not keystate.key:
        apply_modmap(keystate, ctx)
        apply_multi_modmap(keystate, ctx)

    on_key(keystate, ctx)


# def on_mod_key(keystate: Keystate, ctx):
#     global _modifiers_changed_since_cache
#     hold_output = False
#     should_suspend = False

#     key, action = (keystate.key, keystate.action)

#     # Set flag when modifier state changes
#     if action.is_pressed or action.is_released:
#         _modifiers_changed_since_cache = True
#         if logger.VERBOSE:
#             debug(f"Modifier state changed: {key} {action}")

#     # Changing is_pressed to use a property decorator, for consistentcy.
#     if action.is_pressed:
#         if none_pressed():
#             should_suspend = True

#     # Changing Action.is_released() to use a property decorator, for consistentcy.
#     elif action.is_released:
#         if is_sticky(key):
#             outkey = _sticky[key]
#             debug(f"lift of BIND {key} => {outkey}")
#             _output.send_key_action(outkey, Action.RELEASE)
#             del _sticky[key]
#             hold_output = not keystate.exerted_on_output
#         elif keystate.spent:
#             # if we are being released (after spent) before we can be resumed
#             # then our press (as far as output is concerned) should be silent
#             debug("silent lift of spent mod", key)
#             hold_output = not keystate.exerted_on_output
#         else:
#             debug("resume because of mod release")
#             resume_keys()

#     update_pressed_states(keystate)

#     if should_suspend or is_suspended():
#         keystate.suspended = True
#         hold_output = True
#         # Changed just_pressed to use property decorator, for consistency.
#         if action.just_pressed:
#             suspend_or_resuspend_keys(_TIMEOUTS["suspend"])

#     if not hold_output:
#         if action.is_repeat:
#             _output.send_key_action_fast(key, action)
#         else:
#             _output.send_key_action(key, action)
#         # Changing Action.is_released() to use a property decorator, for consistentcy.
#         if action.is_released:
#             keystate.exerted_on_output = False


def on_mod_key(keystate: Keystate, ctx):
    global _modifiers_changed_since_cache
    hold_output = False
    should_suspend = False

    key, action = (keystate.key, keystate.action)

    # Set flag when modifier state changes
    if action.is_pressed or action.is_released:
        _modifiers_changed_since_cache = True
        if logger.VERBOSE:
            debug(f"Modifier state changed: {key} {action}")

    # ──────────────────────────────────────────────────────────────────────────
    # MULTIPURPOSE-KEY HANDLING IN THE MODIFIER PATH
    #
    # A multipurpose key whose *tap* identity is itself a modifier (a piercing
    # Super-tap, e.g. tap = LEFT_META / hold = RIGHT_CTRL) is dispatched to this
    # function by on_key, because on_key checks `is_key_modifier(key)` BEFORE the
    # is_multi branch and the tap identity satisfies it. Such keys therefore never
    # reach the multipurpose suspend/resolve branches in on_key, and on_mod_key
    # must carry the multipurpose semantics itself:
    #
    #   1. (press) Force suspension for any multi-key, not just the first key in a
    #      chord, so each multi-key gets its own tap-vs-hold resolve cycle.
    #   2. (press) Arm the multipurpose timeout, not the suspend timeout, so the
    #      window has a real duration to distinguish a quick tap from a held mod.
    #   3. (release) Resolve tap-vs-hold here, before resume, mirroring the
    #      multi-key release branch in on_key.
    #
    # The root cause is that the dispatch in on_key keys off "is this a modifier"
    # rather than "is this a multipurpose tap identity" — information that does not
    # currently exist at the dispatch point. The cleaner long-term fix is to make
    # that provenance explicit at dispatch and route all multi-keys to a single set
    # of branches regardless of tap identity; until then, the tap-vs-hold release
    # decision below is intentionally kept in sync with on_key's `is_multi`
    # release branch (resolve_as_modifier / resolve_as_momentary on the
    # other_key_pressed_while_held flag).
    # ──────────────────────────────────────────────────────────────────────────

    # Changing is_pressed to use a property decorator, for consistentcy.
    if action.is_pressed:
        if none_pressed():
            should_suspend = True

        # (1) Multi-keys must suspend regardless of chord position. The
        # none_pressed() gate above only catches the first key down; without this,
        # a second piercing key arriving mid-chord skips suspension entirely and
        # leaks its tap (Super) identity onto the output.
        if keystate.is_multi:
            should_suspend = True

    # Changing Action.is_released() to use a property decorator, for consistentcy.
    elif action.is_released:
        if is_sticky(key):
            outkey = _sticky[key]
            debug(f"lift of BIND {key} => {outkey}")
            _output.send_key_action(outkey, Action.RELEASE)
            del _sticky[key]
            hold_output = not keystate.exerted_on_output
        elif keystate.spent:
            # if we are being released (after spent) before we can be resumed
            # then our press (as far as output is concerned) should be silent
            debug("silent lift of spent mod", key)
            hold_output = not keystate.exerted_on_output

        # (3) Multipurpose release resolution. Resolve the identity BEFORE
        # resume_keys() so the press and the release agree on which key is
        # emitted. If we let resume_keys() decide via its timeout-fallback, it
        # always picks the hold identity, producing a hold-identity press paired
        # with a tap-identity release on a quick tap — a stuck-modifier hazard.
        # The fall-through at the bottom of this function emits the release of the
        # now-resolved identity (no transform_key call needed, unlike on_key).
        elif keystate.is_multi:
            debug("Multipurpose key (mod-tap) released before timeout expired", key)
            if keystate.other_key_pressed_while_held:
                # Used in a chord → resolve as the hold modifier.
                mod_name = Modifier.get_modifier_name(keystate.multikey)
                mod_suffix = f" ({mod_name} mod)" if mod_name else ""
                debug(f"Resolved multi-key {keystate.inkey.name} as {keystate.multikey.name}{mod_suffix} (hold)")
                keystate.resolve_as_modifier()
            else:
                # Quick lone release, nothing else pressed → resolve as the tap.
                debug(f"Resolved multi-key {keystate.inkey.name} as {keystate.key.name} (tap)")
                keystate.resolve_as_momentary()
            resume_keys()

        else:
            debug("resume because of mod release")
            resume_keys()

    update_pressed_states(keystate)

    if should_suspend or is_suspended():
        keystate.suspended = True
        hold_output = True
        # Changed just_pressed to use property decorator, for consistency.
        if action.just_pressed:
            # (2) Select the multipurpose timeout for multi-keys so the suspend
            # window has a real duration (normally ~1s). The suspend timeout is
            # often 0, which collapses the window to a single loop tick and makes
            # the timer-fallback resolve every key as a hold before its release
            # can arrive. Ordinary modifiers keep the suspend timeout unchanged.
            if keystate.is_multi:
                suspend_timeout = _TIMEOUTS["multipurpose"]
            else:
                suspend_timeout = _TIMEOUTS["suspend"]
            suspend_or_resuspend_keys(suspend_timeout)

    if not hold_output:
        if action.is_repeat:
            _output.send_key_action_fast(key, action)
        else:
            _output.send_key_action(key, action)
        # Changing Action.is_released() to use a property decorator, for consistentcy.
        if action.is_released:
            keystate.exerted_on_output = False


def on_key(keystate: Keystate, ctx):
    global _last_key, _awaiting_first_repeat_key, _first_repeat_processed

    key, action = (keystate.key, keystate.action)

    # ⚡ EARLY EXIT - Skip all cache logic for button events (BTN_*)
    # Mouse buttons pass through cleanly but shouldn't engage cache machinery
    # designed for keyboard key repeat optimization.
    if key.name.startswith('BTN_'):
        mod_name = Modifier.get_modifier_name(key)
        mod_suffix = f" ({mod_name} mod)" if mod_name else ""
        debug("on_key", f"{key}{mod_suffix}", action)
        if action.just_pressed and is_suspended():
            debug("resume because of button press")
            resume_keys()
        _output.send_key_action_fast(key, action)
        return

    # ⚡ HELD COMBO CHECK — Must fire before cache logic or any other processing.
    # If a held combo is active, either sustain (suppress repeats) or teardown.
    if _held_combo_ctx is not None:

        # Sustain — suppress trigger key repeats, compositor drives output
        if action.is_repeat and key == _held_combo_ctx.trigger_key:
            _held_combo_ctx.suppress_count += 1
            if logger.VERBOSE:
                debug(
                    f"Held combo sustain: suppressed repeat "
                    f"#{_held_combo_ctx.suppress_count} for {key}"
                )
            return

        # Trigger key release — teardown and consume the event
        if action.is_released and key == _held_combo_ctx.trigger_key:
            teardown_held_combo()
            update_pressed_states(keystate)
            _awaiting_first_repeat_key = None
            _first_repeat_processed = False
            _output.clear_cache_tracking()
            return

        # New key press — teardown first, then fall through to process it
        if action.just_pressed:
            teardown_held_combo()
            # Fall through to normal processing for the new keypress

        # Modifier release — combo is no longer valid as a unit, teardown
        # then fall through to process the modifier release normally
        elif action.is_released and Modifier.is_key_modifier(key):
            teardown_held_combo()
            # Fall through to normal processing for the modifier release

        # Non-trigger, non-modifier release (e.g., releasing a previously
        # held key unrelated to the active combo) — no teardown, just fall
        # through to normal processing. The held combo stays active.

    # ⚡ CACHE LOGIC - Skip entirely when no cache exists (fast typing optimization)
    if _repeat_cache is not None:
        # Cache exists - do cache operations
        if action.is_repeat and try_replay_cached_repeat(key, action):
            return  # Cache hit - we're done!

        # Invalidate cache when a different non-modifier key is pressed
        if action.just_pressed and not Modifier.is_key_modifier(key):
            if _repeat_cache.inkey != key:
                invalidate_repeat_cache()
                if logger.VERBOSE:
                    debug(f"Cache invalidated: different key pressed ({key} vs "
                            f"cached {_repeat_cache.inkey})")
        # Invalidate cache when the cached key is released
        elif action.is_released and key == _repeat_cache.inkey:
            invalidate_repeat_cache()
            if logger.VERBOSE:
                debug(f"Cache invalidated: cached key released ({key})")

    # Handle first repeat - cache miss but we have tracking from PRESS
    if action.is_repeat and not _first_repeat_processed and not Modifier.is_key_modifier(key):
        _first_repeat_processed = True  # Latch — stops further attempts
        # This is the first repeat - populate cache from preserved PRESS tracking
        populate_repeat_cache(key, action)
        # Now replay from newly populated cache
        if _repeat_cache is not None and try_replay_cached_repeat(key, action):
            return

    # Clear awaiting flag if DIFFERENT key pressed or awaiting key released
    if action.just_pressed and not Modifier.is_key_modifier(key):
        if _awaiting_first_repeat_key is not None and key.value != _awaiting_first_repeat_key:
            _awaiting_first_repeat_key = None
            _first_repeat_processed = False
            _output.clear_cache_tracking()
    elif action.is_released and _awaiting_first_repeat_key == key.value:
        _awaiting_first_repeat_key = None
        _first_repeat_processed = False
        _output.clear_cache_tracking()

    mod_name = Modifier.get_modifier_name(key)
    mod_suffix = f" ({mod_name} mod)" if mod_name else ""
    debug("on_key", f"{key}{mod_suffix}", action)

    # ──────────────────────────────────────────────────────────────────────────
    # EVENT-BASED MULTIKEY DETECTION
    # When ANY key is pressed, check if we have suspended multikeys
    # and resolve them immediately as modifiers
    # ──────────────────────────────────────────────────────────────────────────
    # Changed just_pressed to use property decorator, for consistency.
    if action.just_pressed and not keystate.is_multi:
        for ks in _key_states.values():
            # Changing Keystate.is_pressed() to use a property decorator, for consistentcy.
            if ks.is_multi and ks.suspended and ks.key_is_pressed:
                # debug(f"Resolving {ks.key} as modifier due to {key} press")

                mod_name = Modifier.get_modifier_name(ks.multikey)
                mod_suffix = f" ({mod_name} mod)" if mod_name else ""
                debug(f"Resolving {ks.inkey.name} as {ks.multikey.name}{mod_suffix} due to {key} press")

                ks.resolve_as_modifier()
                ks.suspended = False
                ks.other_key_pressed_while_held = True
                if not ks.exerted_on_output:
                    _output.send_key_action(ks.key, Action.PRESS)
                    ks.exerted_on_output = True

    # Continue with normal processing...
    if Modifier.is_key_modifier(key):
        on_mod_key(keystate, ctx)

    # Changed just_pressed to use property decorator, for consistency.
    elif keystate.is_multi and action.just_pressed:
        # debug("multi pressed", key)
        keystate.suspended = True
        keystate.other_key_pressed_while_held = False  # Initialize flag
        update_pressed_states(keystate)
        suspend_keys(_TIMEOUTS["multipurpose"])

    elif keystate.is_multi and action.is_repeat and keystate.suspended:
        pass
        # do nothing

    # regular key releases, not modifiers (though possibly a multi-mod)
    # Changing Action.is_released() to use a property decorator, for consistentcy.
    elif action.is_released:
        if _output.is_key_pressed(key):
            _output.send_key_action_fast(key, action)
        if keystate.is_multi:
            # debug("multi released early", key)
            debug("Multipurpose key released before timeout expired", key)
            # EVENT-BASED DECISION: Check the flag instead of _last_key
            if keystate.other_key_pressed_while_held:
                # Another key was pressed while held → this was used as modifier
                mod_name = Modifier.get_modifier_name(keystate.multikey)
                mod_suffix = f" ({mod_name} mod)" if mod_name else ""
                debug(f"Resolved multi-key {keystate.inkey.name} as {keystate.multikey.name}{mod_suffix} (hold)")
                keystate.resolve_as_modifier()
            else:
                # No other key pressed while held → this was a tap
                debug(f"Resolved multi-key {keystate.inkey.name} as {keystate.key.name} (tap)")
                keystate.resolve_as_momentary()
            resume_keys()
            transform_key(key, action, ctx)
            # update_pressed_states(keystate)
        # Moved this out of "if keystate.is_multi" block to ensure always resetting keystate
        update_pressed_states(keystate)
    else:
        # not a modifier or a multi-key, so pass straight to transform
        transform_key(key, action, ctx)

    # Set awaiting flag after successful PRESS (output tracking preserved for first repeat)
    if action.just_pressed and not Modifier.is_key_modifier(key):
        _awaiting_first_repeat_key = key.value

    # Changed just_pressed to use property decorator, for consistency.
    if action.just_pressed:
        _last_key = key


def transform_key(key, action: Action, ctx: KeyContext):
    global _active_keymaps
    is_top_level = False

    # if we do not have window context information we essentially short-circuit
    # the keymapper, acting in essentially a pass thru mode sending what is
    # typed straight thru from input to output
    if ctx.wndw_ctxt_error:
        resume_keys()
        _output.send_key_action_fast(key, action)
        return

    # combo = Combo(get_pressed_mods(), key)
    match_key = correct_key_for_match(key)
    if logger.VERBOSE and match_key is not key:
        debug(f"Layout correction: combo lookup treats {_annotate(key)} as {match_key!r}", ctx="LC")
    combo = Combo(get_pressed_mods(), match_key)

    if _active_keymaps is escape_next_key:
        debug(f"Escape key: {combo} => {key}")
        _output.send_key_action_fast(key, action)
        _active_keymaps = None
        return

    # New version of `escape_next_key` that doesn't strip out modifiers from next combo.
    # We need this to wait for a non-modifier key, then send through the unremapped combo (or key).
    # More complicated than just escaping the very next normal key press.

    if _active_keymaps is escape_next_combo:
        # Ignore modifier keys and releases - wait for next actual keypress
        # Changing Action.is_released() to use a property decorator, for consistentcy.
        if Modifier.is_key_modifier(key) or action.is_released:
            _output.send_key_action_fast(key, action)
            return  # Stay in escape mode, don't consume the flag

        # This is a non-modifier key press - apply escape and consume flag
        debug(f"Escape combo: {combo} => {combo}")
        resume_keys()  # Ensure current modifiers are on output
        _output.send_key_action_fast(key, action)
        _active_keymaps = None  # Consume the flag now
        return

    # Decide keymap(s)
    if _active_keymaps is None:
        is_top_level = True
        _active_keymaps = [km for km in _KEYMAPS if km.matches(ctx)]

    for keymap in _active_keymaps:
        if combo not in keymap:
            continue

        if logger.VERBOSE:
            log_combo_context(combo, ctx, keymap, _active_keymaps)

        held = get_pressed_states()
        for ks in held:
            # if we are triggering a momentary on the output we can mark ourselves
            # spent, but if the key is already asserted on the output then we cannot
            # count it as spent and must hold it so that it's release later will
            # trigger the release on the output
            if not _output.is_mod_pressed(ks.key):
                ks.spent = True
        debug("spent modifiers", [_.key for _ in held if _.spent])
        reset_mode = handle_commands(keymap[combo], key, action, ctx, combo)
        if reset_mode:
            _active_keymaps = None
        return

    # Not found in all KEYMAPS
    if is_top_level:
        # need to output any keys we've suspended
        resume_keys()
        # If it's top-level, pass through keys
        # _output.send_key_action(key, action)
        # Use the "fast" version of send_key_action for "normal" typing:
        _output.send_key_action_fast(key, action)

    _active_keymaps = None


# ─── AUTO BIND AND STICKY KEYS SUPPORT ──────────────────────────────────────────


# binds the first input modifier to the first output modifier
def simple_sticky(combo: Combo, output_combo: Combo):
    inmods = combo.modifiers
    outmods = output_combo.modifiers
    if len(inmods) == 0 or len(outmods) == 0:
        return {}
    inkey = inmods[0].get_key()
    outkey = outmods[0].get_key()

    # _key_states is keyed on the physical inkey (pre-modmap), but `inkey` here is
    # an output-side modifier identity (post-modmap) — e.g. a multipurpose key that
    # resolved to RIGHT_CTRL, whose keystate is still filed under its physical key.
    # Match on keystate.key, not the dict key, same as teardown_held_combo() does.
    keystate = next(
        (ks for ks in _key_states.values() if ks.key == inkey),
        None
    )

    if keystate is not None and keystate.exerted_on_output:
        key_in_output = any([inkey in mod.keys for mod in outmods])
        if not key_in_output:
            # we are replacing the input key with the bound outkey, so if
            # the input key is exerted on the output we should lift it
            _output.send_key_action(inkey, Action.RELEASE)
            # its release later will still need to result in us lifting
            # the sticky out key from output, but that is currently handled
            # by `_sticky` in `on_key`
            keystate.exerted_on_output = False

    stuck = {inkey: outkey}
    debug("BIND:", stuck)
    return stuck


def auto_sticky(combo, input_combo):
    global _sticky

    # can not engage a second sticky over top of a first
    if len(_sticky) > 0:
        debug("refusing to engage second sticky bind over existing sticky bind")
        return

    _sticky = simple_sticky(input_combo, combo)
    for k in _sticky.values():
        if not _output.is_mod_pressed(k):
            _output.send_key_action(k, Action.PRESS)


# ─── COMMAND PROCESSING ───────────────────────────────────────────────────────


def _annotate(key):
    """Append the active-layout symbol to a key's repr for log readability —
    e.g. "<Key.W: 17> (XKB: 'z')". Bare repr when no symbol is known (US-like
    layouts, or a key outside the correction set)."""
    symbol = xkb_symbol_for_key(key)
    return f"{key!r} (XKB: {symbol!r})" if symbol else repr(key)


def _decorrect_output_command(command):
    """Inverse-correct the key of a matched-remap output so XKB renders the
    intended symbol on the active layout. A Combo is rebuilt with its key
    de-corrected (modifiers are never corrected); a bare Key is de-corrected
    directly. Every other command type — callables, lists, nested Keymaps, the
    escape/bind/ignore sentinels, None — is returned unchanged, so its identity
    survives the downstream `is` checks and its inner keys get de-corrected when
    they recurse back through this same loop.

    A PreCorrectedCombo is returned untouched: it carries keystrokes the string
    emitter already built against the active layout (via the symbol table), so
    de-correcting it would double-apply correction. The check precedes the Combo
    branch because PreCorrectedCombo is a Combo subclass and would otherwise be
    caught and rewritten by it.

    Called only when a correction map is installed; the caller gates on that, so
    there is no internal no-op short-circuit here."""
    if isinstance(command, PreCorrectedCombo):
        return command
    if isinstance(command, Combo):
        out_key = decorrect_key_for_output(command.key)
        if logger.VERBOSE and out_key is not command.key:
            debug(f"Layout correction (output): {command.key!r} -> {_annotate(out_key)}", ctx="LC")
        return Combo(command.modifiers, out_key)
    if isinstance(command, Key):
        out_key = decorrect_key_for_output(command)
        if logger.VERBOSE and out_key is not command:
            debug(f"Layout correction (output): {command!r} -> {_annotate(out_key)}", ctx="LC")
        return out_key
    return command


def handle_commands(commands, key, action, ctx, input_combo=None):
    """
    returns: reset_mode (True/False) if this is True, _active_keymaps will be reset
    """
    global _active_keymaps, _held_combo_ctx
    _next_bind = False

    if not isinstance(commands, list):
        commands = [commands]
    elif len(commands) > 1:
        _output._last_output_for_cache = ('uncacheable', None)

    # if input_combo and input_combo.hint == ComboHint.BIND:
        # auto_sticky(commands[0], input_combo)

    # resuspend any keys still not exerted on the output, giving
    # them a chance to be lifted or to trigger another macro as-is
    if is_suspended():
        resuspend_keys(_TIMEOUTS["suspend"])

    with _output.suspend_when_lifting():
        # Execute commands
        correction_active = bool(get_correction_map())
        for command in commands:
            if correction_active:
                command = _decorrect_output_command(command)
            if callable(command):
                # very likely we're just passing None forwards here but that OK
                cmd_param_cnt = len(inspect.signature(command).parameters)
                # if command doesn't take arguments, don't give it context object
                if cmd_param_cnt == 0:
                    reset_mode = handle_commands(command(), key, action, ctx)
                else:
                    reset_mode = handle_commands(command(ctx), key, action, ctx)
                # if the command wants to disable reset, lets propagate that
                if reset_mode is False:
                    return False
            elif isinstance(command, Combo):
                if _next_bind:
                    auto_sticky(command, input_combo)
                    _output.send_combo(command)
                elif (len(commands) != 1
                        or input_combo is None
                        or action is None
                        or not action.just_pressed):
                    _output.send_combo(command)
                else:
                    # Single Combo on initial press: use held combo for
                    # compositor-driven repeat instead of tap cycle
                    result = _output.send_combo_held_setup(command)
                    if result is None:
                        _output.send_combo(command)
                    else:
                        released_input_mods, pressed_output_mods = result
                        _held_combo_ctx = HeldComboContext(
                            trigger_key         = key,
                            output_combo        = command,
                            released_input_mods = released_input_mods,
                            pressed_output_mods = pressed_output_mods,
                            output_key          = command.key,
                            setup_time          = time.time(),
                        )
                        if logger.VERBOSE:
                            debug(f"Held combo setup: {command} (trigger: {key})")
            elif isinstance(command, Key):
                _output.send_key(command)
            elif command is escape_next_key:
                _active_keymaps = escape_next_key
                return False
            elif command is escape_next_combo:
                _active_keymaps = escape_next_combo
                return False
            elif command is ComboHint.BIND:
                _next_bind = True
                continue
            elif command is ignore_key:
                debug("ignore_key", key)
                return True
            # Go to next keymap
            elif isinstance(command, Keymap):
                keymap = command
                if Trigger.IMMEDIATELY in keymap:
                    handle_commands(keymap[Trigger.IMMEDIATELY], None, None, ctx)
                _active_keymaps = [keymap]
                return False
            #
            # TODO: figure out if the block below is deprecated now that these functions return 
            # inner functions instead of lists (but the inner functions still return lists):
            #
            # to_keystrokes and unicode_keystrokes produce lists so
            # we'll just handle it recursively
            elif isinstance(command, list):
                reset_mode = handle_commands(command, key, action, ctx)
                if reset_mode is False:
                    return False
            elif command is None:
                pass
            else:
                debug(f"unknown command {command}")
            _next_bind = False
        # Reset keymap in ordinary flow
        return True


# End of File #
