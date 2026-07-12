import os
import re
import sys
import time
import inspect
import itertools
import unicodedata

try:
    from anyascii import anyascii as _anyascii_fn
    _HAVE_ANYASCII = True
except ImportError:
    _anyascii_fn = None
    _HAVE_ANYASCII = False

from inspect import signature
from pprint import pformat as ppf

# Removed typing imports (Dict, List) to avoid trouble with Python 3.15+
# from typing import Dict, List

from .layout_correction import get_symbol_table, keystrokes_for_symbol
from .lib.logger import error, debug, warn, FLUSH
from .lib.key_context import KeyContext
from .lib.window_context import WindowContextProviderInterface as WCPI
from .models.action import Action
from .models.combo import Combo, ComboHint, PreCorrectedCombo
from .models.trigger import Trigger
from .models.key import Key, ASCII_TO_KEY
from .models.keymap import Keymap
from .models.modifier import Modifier
from .models.modmap import Modmap, MultiModmap


# GLOBALS
bind                            = ComboHint.BIND
escape_next_key                 = ComboHint.ESCAPE_NEXT_KEY
ignore_key                      = ComboHint.IGNORE
escape_next_combo               = ComboHint.ESCAPE_NEXT_COMBO

immediately                     = Trigger.IMMEDIATELY


# keycode translation
# e.g., { Key.CAPSLOCK: Key.LEFT_CTRL }
_MODMAPS: 'list[Modmap]' = []

# multipurpose keys
# e.g, {Key.LEFT_CTRL: [Key.ESC, Key.LEFT_CTRL, Action.RELEASE]}
_MULTI_MODMAPS: 'list[MultiModmap]' = []


TIMEOUT_DEFAULTS = {
    "multipurpose": 1.0,
    "suspend": 1.0,
    # TODO: not implemented yet
    "post_combo": 0.5,
}

# multipurpose timeout
_TIMEOUTS = TIMEOUT_DEFAULTS


LAYOUT_CORRECTION_DEFAULTS = {

    # Layout correction off by default for now, since it manipulates output.
    # User can activate from config file by calling the API function.
    'correction_enabled':       False,

    # Some layouts like French AZERTY have the number row flipped (digits on the
    # Shift layer). Leaving the number row uncorrected maintains number-shortcut
    # behavior consistency.
    'correct_number_row':       False,

    # What the keymapper does when a symbol cannot be reached via keystrokes on
    # the active layout. Valid options:
    #   'refuse'      - no output, show error
    #   'fold'        - replace with closest ASCII equivalent
    #   'placeholder' - replace with symbol_placeholder (see below)
    'symbol_miss_policy':       'refuse',

    # What the keymapper does when symbol_miss_policy is 'fold' and the folded
    # symbol STILL cannot be reached on the active layout. Valid options:
    #   'refuse'      - no output, show error
    #   'placeholder' - replace with symbol_placeholder (see below)
    # The API accepts None here meaning "unset"; it resolves to 'refuse'. A
    # non-default value passed while symbol_miss_policy is not 'fold' is ignored
    # (with a debug note), since it has nothing to fall back from.
    'folded_miss_policy':       'refuse',

    # The character or string substituted when 'placeholder' is the active
    # symbol miss policy or folding miss policy (see above). An empty string
    # drops the missing character silently. Ignored under non-placeholder paths.
    'symbol_placeholder':       '?',

}

_LAYOUT_CORRECTION = LAYOUT_CORRECTION_DEFAULTS


_DEVICE_ARGS: 'dict[str, str]' = {
    'only_devices': [],
    'add_devices': [],
    'ignore_devices': [],
}


# Defaults are set here so that X11/Xorg environments keep 
# working without needing to use API in config file.
_ENVIRON = {
        'session_type'  :   'x11',
        'wl_compositor':    None,
        'wl_desktop_env':   None,
}


def devices_api(*,
        only_devices: 'list[str]' = [],
        # add_devices: 'list[str]' = [],
        ignore_devices: 'list[str]' = [],
        ):
    """
    API function to specify device names to A) replicate the command-line
    '--devices' arguments, or device names to B) add (for instances where a
    device does not get naturally "grabbed" at startup), or device names
    to C) ignore (for instances where a device does get grabbed, but should
    not be grabbed at startup).

    Matching is done by exact device name, exact device path, by-id symlink
    path (resolved through realpath), or device uniq string.

    The ignore list takes priority over the allowlist — if a device appears
    in both, it will be ignored.

    Populates the `_DEVICE_ARGS` dictionary variable, to be returned to
    `transform.py` when `get_configuration()` is called.

    First parameter '*,' requires all arguments to be named, allows having
    any named parameter by itself, or multiple parameters can be used in
    any order, since all have to be named.
    """
    global _DEVICE_ARGS

    def validate_list_of_strings(param, param_name):
        if not isinstance(param, list):
            error(f"The '{param_name}' parameter must be a list.")
            raise ValueError
        if not all(isinstance(item, str) for item in param):
            error(f"All items in the '{param_name}' parameter must be strings.")
            raise ValueError

    validate_list_of_strings(only_devices, 'only_devices')
    # validate_list_of_strings(add_devices, 'add_devices')
    validate_list_of_strings(ignore_devices, 'ignore_devices')

    # if add_devices:
    #     error("The 'add_devices' parameter is not supported yet. Setting to empty list.")
    #     add_devices = []

    _DEVICE_ARGS = {
        'only_devices':     only_devices,
        # 'add_devices':      add_devices,
        'ignore_devices':   ignore_devices,
    }



def get_all_supported_environments():
    """Get the full list of supported environments from the
    window context module's registry of supported environments
    advertised by all providers in the module. The form is
    a list of (session_type, window_manager) tuples."""
    return WCPI.get_all_supported_environments()


def environ_api(*, session_type='x11', wl_compositor=None, wl_desktop_env=None):
    """
    API function to specify the session type (X11/Xorg or Wayland)
    and if Wayland, which Wayland compositor, to be used to try
    to instantiate the correct window context provider object.

    Default session type is 'x11' for backwards compatibility
    with existing configs that don't call this API to adapt to
    Wayland environments.

    The Wayland "desktop environment" argument is deprecated and
    may be removed at some point if no other use is found for it.
    (Deprecated as of 2025-02-11. TODO: Remove by 2027-02-15.)
    """

    # Disregard any capitalization variations given in manual usage
    if isinstance(session_type, str):       session_type        = session_type.casefold()
    if isinstance(wl_compositor, str):      wl_compositor       = wl_compositor.casefold()
    if isinstance(wl_desktop_env, str):     wl_desktop_env      = wl_desktop_env.casefold()

    # Get the currently supported environments currently being 
    # advertized by provider classes in the window context module.
    supported_environments = get_all_supported_environments()

    # Construct the environment tuple based on the provided values,
    # screening first for 'x11' to match the window context provider
    # tuple of ('x11', None).
    if session_type == 'x11':
        provided_environment_tup = (session_type, None)
    elif wl_compositor:
        provided_environment_tup = (session_type, wl_compositor)
    # Preserve usage of the older argument if 'wl_compositor' argument not provided
    elif wl_desktop_env:
        provided_environment_tup = (session_type, wl_desktop_env)
    else:
        print()
        error(  f"Logic error, or bad argument values?"
                f"\n\t{session_type     = }"
                f"\n\t{wl_compositor    = }"
                f"\n\t{wl_desktop_env   = }"
                f"\n")
        sys.exit(1)

    if provided_environment_tup not in supported_environments:
        if wl_compositor:
            print()
            error(
                f'Unsupported environment: '
                f"\n\tSession type     = '{session_type}'"
                f"\n\tWindow manager   = '{wl_compositor}'"
                f"\n")
        else:
            print()
            error(
                f'Unsupported environment: '
                f"\n\tSession type     = '{session_type}'"
                f"\n\tDesktop env      = '{wl_desktop_env}' (DEPRECATED, use 'wl_compositor' arg)"
                f"\n")
        debug(f"Supported environments: ('session_type', 'window_mgr')\n\t" +
                '\n\t'.join(ppf(item) for item in supported_environments) + '\n')
        sys.exit(1)

    if session_type == 'x11':
        # For 'x11' case, window context provider tuple to match is ('x11', None)
        _ENVIRON.update({
            'session_type':     session_type,
            'wl_compositor':    None,
        })
    elif wl_compositor:
        _ENVIRON.update({
            'session_type':     session_type,
            'wl_compositor':    wl_compositor,
        })
    else:
        # transform.py uses only 'wl_compositor' now, but this preserves 'wl_desktop_env' usage
        _ENVIRON.update({
            'session_type':     session_type,
            'wl_compositor':    wl_desktop_env,
        })

    if wl_compositor:
        print()
        debug(
            f"ENVIRON API: "
            f"\n\tSession type     = '{session_type}'"
            f"\n\tWindow manager   = '{wl_compositor}'"
            f"\n")
    else:
        print()
        debug(
            f"ENVIRON API: "
            f"\n\tSession type     = '{session_type}'"
            f"\n\tDesktop env      = '{wl_desktop_env}' (DEPRECATED, use 'wl_compositor' arg)"
            f"\n")


# global dict of delay values used to mitigate Unicode entry sequence and macro or combo failures
THROTTLE_DELAY_DEFAULTS = {
    'key_pre_delay_ms': 0,
    'key_post_delay_ms': 0,
}
_THROTTLES = THROTTLE_DELAY_DEFAULTS


def clamp(num, min_value, max_value):
    return max(min(num, max_value), min_value)


def throttle_delays(key_pre_delay_ms=0, key_post_delay_ms=0):
    """Mitigate out-of-order key event issues with some macro output, esp. with ibus"""
    ms_min, ms_max = 0.0, 150.0
    if any([not(ms_min <= e <= ms_max) for e in [key_pre_delay_ms, key_post_delay_ms]]):
        error(f'Throttle delay value out of range. Clamping to valid range: {ms_min} to {ms_max}.')
    _THROTTLES.update({ 'key_pre_delay_ms' : clamp(key_pre_delay_ms, ms_min, ms_max), 
                        'key_post_delay_ms': clamp(key_post_delay_ms, ms_min, ms_max) })
    debug(  f'THROTTLES: Pre-key: {_THROTTLES["key_pre_delay_ms"]}ms, '
            f'Post-key: {_THROTTLES["key_post_delay_ms"]}ms')


_SYMBOL_MISS_POLICIES           = ('refuse', 'fold', 'placeholder')
_FOLDED_MISS_POLICIES           = ('refuse', 'placeholder')
_SYMBOL_PLACEHOLDER_MAX_LEN     = 8


def keyboard_layout_correction(
    correction_enabled: bool                = False,
    correct_number_row: bool                = False,
    symbol_miss_policy: str                 = 'refuse',
    folded_miss_policy: 'str | None'        = None,
    symbol_placeholder: str                 = '?',
):
    """
    Opt in to non-US keyboard layout correction.

    correction_enabled  - master switch. When on, correction applies to
                          everything it can. Off by default, because correction
                          manipulates output and must be a deliberate choice.
    correct_number_row  - treat a position-flipped number row as corrected base
                          keys instead of leaving it positional (the default).
                          Only coherent where the row differs by position, not by
                          Shift level.

    The next three govern string/Unicode OUTPUT only (phase 2): when a macro
    types a character the active layout cannot produce, that character is a
    "miss". Most characters are reachable on most Latin layouts, so misses are
    rare; these decide what happens when one occurs.

    symbol_miss_policy  - what to do with an unreachable character:
                            'refuse'      - emit nothing for the whole string and
                                            log the offending character. Loud and
                                            safe; the default. The macro visibly
                                            does nothing, with a journal trace.
                            'fold'        - replace the character with its closest
                                            ASCII equivalent and continue (e.g.
                                            'e' for an unreachable accented e).
                                            Uses anyascii when available, else a
                                            built-in unicodedata fold. Lossy by
                                            consent - opt in knowing it
                                            approximates, and that a folded string
                                            meant to trigger an action could
                                            behave differently than typed.
                            'placeholder' - replace the character with
                                            symbol_placeholder and continue, so
                                            the gap is visible in the output.

    folded_miss_policy  - only meaningful when symbol_miss_policy is 'fold': what
                          to do with a character that is STILL unreachable after
                          folding. Defaults to None, which resolves to 'refuse'.
                            'refuse'      - emit nothing for the whole string and
                                            log the character (loud, the default).
                            'placeholder' - replace it with symbol_placeholder.
                          A non-None value passed while symbol_miss_policy is not
                          'fold' is ignored, with a debug note, since there is no
                          fold for it to fall back from.

    symbol_placeholder  - the string substituted under any 'placeholder' path
                          (primary or folding). Any string (default '?'); an empty
                          string drops the character silently. Ignored where no
                          placeholder path is active.

    What `correction_enabled` turns on, as it is built out:
        shortcut match + output correction (flat keycode map) ........ phase 1
        typed-string letter/punct correction (rides inverse map) ..... phase 1
        typed-string digit + symbol correction (symbol table) ........ phase 2
        Unicode output correction (symbol table) ..................... phase 2
        non-Latin handling (mechanism TBD; currently passthrough) .... later
    """
    global _LAYOUT_CORRECTION

    for name, val in (('correction_enabled', correction_enabled),
                        ('correct_number_row', correct_number_row)):
        if val not in (True, False):
            raise ValueError(
                f"keyboard_layout_correction() wants True or False for '{name}'.")

    if symbol_miss_policy not in _SYMBOL_MISS_POLICIES:
        raise ValueError(
            f"keyboard_layout_correction() wants one of {_SYMBOL_MISS_POLICIES} for "
            f"'symbol_miss_policy', got {symbol_miss_policy!r}.")

    # Detect explicit-vs-default BEFORE resolving the sentinel: a non-None value
    # passed while the primary policy is not 'fold' has nothing to fall back
    # from, so note that it is being ignored rather than silently storing it.
    if folded_miss_policy is not None and symbol_miss_policy != 'fold':
        debug(
            f"keyboard_layout_correction(): 'folded_miss_policy' "
            f"({folded_miss_policy!r}) is ignored because 'symbol_miss_policy' is "
            f"{symbol_miss_policy!r}, not 'fold'.", ctx="LC")

    # Resolve the sentinel to the real default, then validate the resolved value
    # so an illegal value (e.g. 'fold') is caught whether or not it was passed.
    if folded_miss_policy is None:
        folded_miss_policy = 'refuse'
    if folded_miss_policy not in _FOLDED_MISS_POLICIES:
        raise ValueError(
            f"keyboard_layout_correction() wants one of {_FOLDED_MISS_POLICIES} for "
            f"'folded_miss_policy', got {folded_miss_policy!r}.")

    if not isinstance(symbol_placeholder, str):
        raise ValueError(
            f"keyboard_layout_correction() wants a string for 'symbol_placeholder', "
            f"got {type(symbol_placeholder).__name__}.")
    if len(symbol_placeholder) > _SYMBOL_PLACEHOLDER_MAX_LEN:
        raise ValueError(
            f"keyboard_layout_correction() wants 'symbol_placeholder' no longer than "
            f"{_SYMBOL_PLACEHOLDER_MAX_LEN} characters, got {len(symbol_placeholder)} "
            f"({symbol_placeholder!r}).")

    _LAYOUT_CORRECTION = {
        'correction_enabled':           correction_enabled,
        'correct_number_row':           correct_number_row,
        'symbol_miss_policy':           symbol_miss_policy,
        'folded_miss_policy':           folded_miss_policy,
        'symbol_placeholder':           symbol_placeholder,
    }
    debug(f"Keyboard layout correction: {_LAYOUT_CORRECTION}", ctx="LC")


def layout_correction_options():
    """Return a copy of the current keyboard-layout-correction options."""
    return dict(_LAYOUT_CORRECTION)


# Setting this to False now, in favor of the newer, more sophisticated
# caching of Combo, Key and passthrough events that allows "repeat"
# events to be "replayed", giving CPU usage for repeating keys in the 
# 0.1-0.5% range, on a system that uses 1.1-1.6% for regular, FAST typing.
_REPEATING_KEYS = {
    'ignore_repeating_keys': False,
}


# def ignore_repeating_keys(true_or_false: bool = True):
#     """Toggle at startup whether to ignore (default) or process repeated keys."""
#     debug("WARNING: ignore_repeating_keys prevents repeating remaps (e.g. Emacs movement)")
#     if true_or_false not in [True, False]:
#         raise ValueError("The ignore_repeated_keys() function wants True or False.")
#     _REPEATING_KEYS['ignore_repeating_keys'] = true_or_false
#     debug(f"Ignore repeating keys  = '{true_or_false}'")


def ignore_repeating_keys(true_or_false: bool = False):
    """
    Toggle at startup whether to ignore or process repeated keys.
    
    NOTICE: This function is largely obsoleted by the new repeat cache mechanism,
    which provides similar performance (~0.1-0.5% CPU) while maintaining full
    remapping functionality on common types of repeat events (Combo, Key).
    
    Setting this to True will prevent the repeat cache from working and will
    prevent remaps from repeating (though this only affects certain things like
    Emacs-style cursor movement combos that need to repeat when held).
    
    Consider removing this function call from your config to use the new
    repeat cache instead, which gives you both performance AND functionality.
    """

    if true_or_false not in [True, False]:
        raise ValueError("The ignore_repeated_keys() function wants True or False.")

    # Warn about breakage if True
    if true_or_false is True:
        print("    ", "=" * 75)
        warn("WARNING: ignore_repeating_keys(True) is enabled")
        print("     - This PREVENTS the new repeat cache from working", flush=FLUSH)
        print("     - This BREAKS repeating remaps (e.g., Emacs movement shortcuts)", flush=FLUSH)
        print("     - The new repeat cache provides similar performance (0.1-0.5% CPU)", flush=FLUSH)
        print("       while maintaining full functionality", flush=FLUSH)

    # Always show recommendation (whether True or False)
    print("    ", "=" * 75)
    warn("RECOMMENDATION: Remove ignore_repeating_keys() from your config")
    print("                     to use the improved repeat cache mechanism", flush=FLUSH)
    print("    ", "=" * 75)

    _REPEATING_KEYS['ignore_repeating_keys'] = true_or_false
    debug(f"Ignore repeating keys  = '{true_or_false}'")


# keymaps
_KEYMAPS: 'list[Keymap]' = []

# hotkeys for debugging
DUMP_DIAGNOSTICS_KEY = Key.F15
EMERGENCY_EJECT_KEY = Key.F16


# needed for testing teardowns
def reset_configuration():
    """reset configuration settings completely"""
    global _MODMAPS
    global _MULTI_MODMAPS
    global _KEYMAPS
    global _TIMEOUTS
    global _PENDING_HYPER_EXPANSIONS
    global _LAYOUT_CORRECTION

    _MODMAPS = []
    _MULTI_MODMAPS = []
    _KEYMAPS = []
    _TIMEOUTS = TIMEOUT_DEFAULTS
    _PENDING_HYPER_EXPANSIONS = []
    _LAYOUT_CORRECTION = LAYOUT_CORRECTION_DEFAULTS


# how transform hooks into the configuration
def get_configuration():
    """API for exporting the current configuration"""
    global _MODMAPS
    global _MULTI_MODMAPS
    global _DEVICE_ARGS

    # setup modmaps
    conditionals = [mm for mm in _MODMAPS if mm.conditional]
    default = [mm for mm in _MODMAPS if not mm.conditional] or [
        Modmap("default", {})
    ]
    if len(default) > 1:
        error(
            "You may only have a single default (non-conditional modmap),"
            f" you have {len(default)} currently."
        )
        sys.exit(0)
    _MODMAPS = default + conditionals

    # setup multi-modmaps
    conditionals = [mm for mm in _MULTI_MODMAPS if mm.conditional]
    default = [mm for mm in _MULTI_MODMAPS if not mm.conditional] or [
        MultiModmap("default", {})
    ]
    if len(default) > 1:
        error(
            "You may only have a single default (non-conditional multi-modmap),"
            f" you have {len(default)} currently."
        )
        sys.exit(0)
    _MULTI_MODMAPS = default + conditionals

    for pending in _PENDING_HYPER_EXPANSIONS:
        expansion_dict = _generate_hyper_expansion(pending)
        keymap("Hyper modifier expansions (auto-gen)",
                expansion_dict, when = pending['when'])

    return (_MODMAPS, _MULTI_MODMAPS, _KEYMAPS, _TIMEOUTS)


# ─── HOTKEYS ─────────────────────────────────────────────────────────────────


def dump_diagnostics_key(key):
    global DUMP_DIAGNOSTICS_KEY
    if isinstance(key, Key):
        DUMP_DIAGNOSTICS_KEY = key


def emergency_eject_key(key):
    global EMERGENCY_EJECT_KEY
    if isinstance(key, Key):
        EMERGENCY_EJECT_KEY = key


# ============================================================ #
# Utility functions for keymap
# ============================================================ #


def sleep(sec):
    """Sleep sec in commands"""

    def sleeper():
        time.sleep(sec)

    return sleeper


def usleep(usec):
    """Sleep usec in commands"""

    def sleeper():
        time.sleep(usec / 1000)

    return sleeper


# ============================================================ #


class CharacterNotSupported(Exception):
    pass


class TypingTooLong(Exception):
    pass


class UnicodeNumberToolarge(Exception):
    pass


def _fold_to_ascii(string_to_fold: str) -> str:
    """Transliterate a string to its closest plain-ASCII form for the 'fold'
    miss policy. Prefers anyascii (broad, sensible transliterations like 'EUR'
    for the euro sign); falls back to a stdlib NFD decomposition that strips
    combining marks (so 'é' -> 'e', but characters with no decomposition, like
    most symbols and all non-Latin scripts, are left as-is and will simply miss
    again downstream). Either way the result is only a REDUCTION of misses, not a
    guarantee of reachability — whatever still misses after folding is handled by
    folded_miss_policy at the call site."""
    if _HAVE_ANYASCII:
        return _anyascii_fn(string_to_fold)
    decomposed = unicodedata.normalize('NFD', string_to_fold)
    return ''.join(decomposed_char for decomposed_char in decomposed
                    if not unicodedata.combining(decomposed_char))


def _combos_from_steps(steps) -> list:
    """Convert a symbol-table sequence — a list of (base Key, [modifier Keys])
    steps — into PreCorrectedCombo objects. One step for a directly-typeable
    character, two for a dead-key character (dead key, then base). The combos are
    marked pre-corrected so output de-correction leaves them alone: the table
    already yields active-layout keycodes, and de-correcting them again would
    double-apply. Routed (like any Combo) through the throttled send path by
    handle_commands, so dead-key sequencing keeps proper inter-press delays."""
    combos = []
    for base_key, modifier_keycodes in steps:
        modifiers = [Modifier.from_key(modifier_keycode)
                        for modifier_keycode in modifier_keycodes]
        combos.append(PreCorrectedCombo(modifiers, base_key))
    return combos


def _placeholder_combos(placeholder_str: str) -> 'list | None':
    """Build the keystrokes for a placeholder substitution by running each of
    its characters through the symbol table. Returns a (possibly empty) list of
    combos on success, or None if ANY character of the placeholder is itself
    unreachable on the active layout (caller treats that as a config error and
    refuses the whole string).

    An empty placeholder string returns an empty list — the missing character
    contributes no keystrokes and is silently dropped, which is the documented
    empty-placeholder behaviour."""
    combos = []
    for placeholder_char in placeholder_str:
        steps = keystrokes_for_symbol(placeholder_char)
        if steps is None:
            return None
        combos.extend(_combos_from_steps(steps))
    return combos


def str_to_keystrokes(string_to_process: str):
    """
    Turn an alphanumeric string (with spaces and some ASCII), up to 100
    characters, into keystroke commands.

    On a US-like layout (no symbol table installed) this behaves exactly as it
    always has: each character maps to its US-positional key(s). On a non-US
    layout (a symbol table is installed by the layout-correction subsystem) each
    character is instead looked up in that table, which yields the keystroke
    sequence that actually types it on the active layout. A character the active
    layout cannot produce is a "miss", handled per the configured policy
    (see keyboard_layout_correction()).
    """
    if len(string_to_process) > 100:
        raise TypingTooLong("`str_to_keystrokes` only supports strings of 100 characters or less")

    def _str_to_keystrokes(ctx: KeyContext):
        symbol_table = get_symbol_table()

        # ── US-like layout: empty table. Run the original US-positional path
        # verbatim, so this common case is byte-for-byte unchanged and free of
        # any table/option overhead. ──
        if not symbol_table:
            combo_list = []
            for character in string_to_process:
                if ord(character) > 127:
                    combo_list.append(unicode_addr_to_keystrokes(ord(character)))
                elif character.isupper():
                    if ctx.capslock_on: combo_list.append(combo(character))
                    else: combo_list.append(combo("Shift-" + character))
                elif (str.isdigit(character)):
                    combo_list.append(Key[character.upper()])
                elif (str.isalpha(character)):
                    if ctx.capslock_on: combo_list.append(combo("Shift-" + character))
                    else: combo_list.append(Key[character.upper()])
                elif character in ASCII_TO_KEY:
                    combo_list.append(ASCII_TO_KEY[character])
                elif character in ASCII_WITH_SHIFT:
                    combo_list.append(ASCII_WITH_SHIFT[character])
                else:
                    raise CharacterNotSupported(
                        f"The character {character} is not supported by `str_to_keystrokes` yet.")
            return combo_list

        # ── Non-US layout: a symbol table is installed. Look every character up
        # in the table; handle misses by policy. ──
        options             = layout_correction_options()
        primary_policy      = options['symbol_miss_policy']
        folding_policy      = options['folded_miss_policy']
        placeholder_str     = options['symbol_placeholder']

        # Folding is a whole-string pre-pass (it can be one-to-many, e.g. an
        # unreachable ligature -> two ASCII letters, which changes length). After
        # folding, every character still goes through the table — folding only
        # changes WHICH characters are looked up, it does not bypass the table.
        # Once folded, the in-loop miss handler uses folding_policy; unfolded, it
        # uses primary_policy (which here is only ever 'refuse' or 'placeholder',
        # never 'fold'). So the loop consults a single effective policy.
        if primary_policy == 'fold':
            chars           = _fold_to_ascii(string_to_process)
            effective_miss  = folding_policy
            if chars != string_to_process:
                debug(
                    f"str_to_keystrokes: fold policy altered {string_to_process!r} "
                    f"-> {chars!r} for the active layout.", ctx="LC")
        else:
            chars           = string_to_process
            effective_miss  = primary_policy

        combo_list = []
        for target_char in chars:
            # Tab/newline are not produced by the string processor (it is for
            # text only; line structure is built from separate Key/Combo macro
            # elements). They are not in the table and were never supported here,
            # so they continue to raise exactly as before.
            if target_char in ('\t', '\n'):
                raise CharacterNotSupported(
                    f"The character {target_char!r} is not supported by `str_to_keystrokes` yet.")

            steps = keystrokes_for_symbol(target_char)
            if steps is not None:
                combo_list.extend(_combos_from_steps(steps))
                continue

            # Miss. Resolve by the single effective policy.
            if effective_miss == 'placeholder':
                placeholder_combos = _placeholder_combos(placeholder_str)
                if placeholder_combos is None:
                    # Placeholder itself is unreachable on this layout — a config
                    # error the user must fix. Refuse the whole string, loudly.
                    error(
                        f"str_to_keystrokes: symbol_placeholder {placeholder_str!r} is not "
                        f"typeable on the active layout; refusing the whole string "
                        f"{string_to_process!r}.", ctx="LC")
                    return []
                combo_list.extend(placeholder_combos)
                continue

            # effective_miss == 'refuse': abandon the whole string, name the
            # offending character in the journal.
            error(
                f"str_to_keystrokes: character {target_char!r} is not typeable on the active "
                f"layout (policy {effective_miss!r}); refusing the whole string {string_to_process!r}.",
                ctx="LC")
            return []

        # CapsLock, if on, would alter the letter case the baked-in modifiers
        # produce. Bracket the whole sequence with CapsLock toggles (same tactic
        # as unicode_addr_to_keystrokes), which is content-agnostic and leaves the
        # table's own modifiers untouched — correct across letters, digits, and
        # punctuation alike. Only meaningful when something was actually emitted.
        if combo_list and ctx.capslock_on:
            combo_list.insert(0, Key.CAPSLOCK)
            combo_list.append(Key.CAPSLOCK)

        return combo_list

    return _str_to_keystrokes


def _digits(n, base):
    digits = []
    while n > 0:
        digits.insert(0, n%base)
        n //= base
    return digits


def insert_delay(msec):
    """"Insert a millisecond delay in the output"""
    def _insert_delay():
        if msec != 0:
            time.sleep(msec/1000)
    return _insert_delay


def unicode_addr_to_keystrokes(codepoint_int):
    """Turn a single Unicode address (codepoint integer) into keystroke commands
    via the Shift+Ctrl+U entry mechanism. Takes the integer codepoint (e.g.
    0x20AC for the euro sign), not a character.

    Every key emitted here is a literal Unicode-entry keystroke (the compose
    trigger, the hex digits, Enter). Each hex character is typed via the active
    layout's correct physical key (symbol-table lookup) and emitted as a
    PreCorrectedCombo, immune to output de-correction. On a layout with a
    correction map installed (e.g. AZERTY), a bare Key would be de-corrected to
    the wrong physical key and the codepoint would corrupt; PreCorrectedCombo
    keeps the already-correct key intact.
    """
    if codepoint_int > 0x10ffff:
        raise UnicodeNumberToolarge(
            f"{hex(codepoint_int)} too large for Unicode keyboard entry.")

    def _unicode_addr_to_keystrokes(ctx: KeyContext):
        symbol_table = get_symbol_table()

        # ── US-like layout: empty table. Original US-positional path, verbatim,
        # so this common case is byte-for-byte unchanged and free of any table
        # overhead. ──
        if not symbol_table:
            combo_list = [
                combo("Shift-Ctrl-u"),
                *[Key[hexdigit]
                    for digit in _digits(codepoint_int, 16)
                    for hexdigit in hex(digit)[2:].upper()
                ],
                Key.ENTER,
            ]
            if ctx.capslock_on:
                combo_list.insert(0, Key.CAPSLOCK)
                combo_list.append(Key.CAPSLOCK)
            return combo_list

        # ── Non-US layout: a symbol table is installed. Look every hex character
        # up so it is typed via the active layout's correct physical key, and emit
        # each as PreCorrectedCombo so the de-correction pass leaves it alone. ──

        # Compose trigger: look up lowercase 'u', then force exactly Ctrl+Shift as
        # the modifiers (ignore any the table associates with 'u' — the trigger is
        # definitionally Ctrl+Shift+U, not Ctrl+Shift+whatever-u-needs).
        u_steps = keystrokes_for_symbol('u')
        if u_steps is None or len(u_steps) != 1:
            error(
                "unicode_addr_to_keystrokes: 'u' is not directly typeable on the "
                "active layout (needed for the Shift+Ctrl+U trigger); refusing "
                f"Unicode entry of {hex(codepoint_int)}.", ctx="LC")
            return []
        u_key, _u_mods_ignored = u_steps[0]
        compose_modifiers = [
            Modifier.from_key(Key.LEFT_CTRL),
            Modifier.from_key(Key.LEFT_SHIFT),
        ]
        combo_list = [PreCorrectedCombo(compose_modifiers, u_key)]

        # Hex digits: each typed through the table, single-step only.
        for digit in _digits(codepoint_int, 16):
            for hexdigit in hex(digit)[2:].upper():
                hex_steps = keystrokes_for_symbol(hexdigit)
                if hex_steps is None or len(hex_steps) != 1:
                    error(
                        f"unicode_addr_to_keystrokes: hex digit {hexdigit!r} is not "
                        "directly typeable on the active layout; refusing Unicode "
                        f"entry of {hex(codepoint_int)}.", ctx="LC")
                    return []
                hex_key, hex_mods = hex_steps[0]
                modifiers = [
                    Modifier.from_key(modifier_keycode)
                    for modifier_keycode in hex_mods
                ]
                combo_list.append(PreCorrectedCombo(modifiers, hex_key))

        # Enter terminates the compose sequence: a control key, not a character,
        # so it is emitted marked-and-direct (no table lookup — it is not in the
        # table, and a lookup would spuriously refuse on its absence).
        combo_list.append(PreCorrectedCombo([], Key.ENTER))

        if ctx.capslock_on:
            combo_list.insert(0, PreCorrectedCombo([], Key.CAPSLOCK))
            combo_list.append(PreCorrectedCombo([], Key.CAPSLOCK))
        return combo_list

    return _unicode_addr_to_keystrokes


def unicode_str_to_keystrokes(string_to_process: str):
    """
    Turn a string into keystroke commands by routing EVERY character through
    Unicode entry (Shift+Ctrl+U + codepoint hex). Layout-independent, but slow
    and dependent on a working IBus/fcitx Unicode entry path. Prefer
    str_to_keystrokes (or a literal key) for ASCII and reserve this for
    genuinely non-typeable characters.
    """
    if len(string_to_process) > 100:
        raise TypingTooLong(
            "`unicode_str_to_keystrokes` only supports strings of 100 characters or less")

    # Warn once per ASCII character at build time: this is a property of how the
    # macro was written, not a per-execution event, so it belongs here (when the
    # processor is evaluated as the config builds) rather than inside the inner
    # function (which would re-warn on every trigger).
    for target_char in string_to_process:
        if ord(target_char) <= 127:
            debug(
                f"unicode_str_to_keystrokes: ASCII character {target_char!r} routed "
                f"through Unicode entry (Shift+Ctrl+U). This path is for characters the "
                f"active layout cannot type; prefer str_to_keystrokes or a literal key "
                f"for ASCII.", ctx="LC")

    def _unicode_str_to_keystrokes(ctx: KeyContext):
        combo_list = []
        for target_char in string_to_process:
            combo_list.append(unicode_addr_to_keystrokes(ord(target_char)))
        return combo_list

    return _unicode_str_to_keystrokes


def to_US_keystrokes(string_to_process: str):
    """Deprecated name for str_to_keystrokes(). Delegates unchanged."""
    warn("to_US_keystrokes() is deprecated and may be removed any time after "
            "mid-2027; use str_to_keystrokes() instead.")
    return str_to_keystrokes(string_to_process)


def unicode_keystrokes(codepoint_int):
    """Deprecated name for unicode_addr_to_keystrokes(). Delegates unchanged."""
    warn("unicode_keystrokes() is deprecated and may be removed any time after "
            "mid-2027; use unicode_addr_to_keystrokes() instead.")
    return unicode_addr_to_keystrokes(codepoint_int)


def combo(exp):  # pylint: disable=invalid-name
    "Helper function to specify keymap"
    modifier_strs = []
    while True:
        aliases = "|".join(Modifier.all_aliases())
        m = re.match(f"\\A({aliases})-", exp)
        if m is None:
            break
        modifier = m.group(1)
        modifier_strs.append(modifier)
        exp = re.sub(rf"\A{modifier}-", "", exp)
    key_str = exp.upper()
    key = Key[key_str]
    return Combo(_create_modifiers_from_strings(modifier_strs), key)


# legacy helper name
K = combo
# short form for most common used helper
C = combo


def _create_modifiers_from_strings(modifier_strs):
    modifiers = []
    for modifier_str in modifier_strs:
        key = Modifier.from_alias(modifier_str)
        if key not in modifiers:
            modifiers.append(key)
    return modifiers


ASCII_WITH_SHIFT = {
    "~":    combo("Shift-Grave"),
    "!":    combo("Shift-1"),
    "@":    combo("Shift-2"),
    "#":    combo("Shift-3"),
    "$":    combo("Shift-4"),
    "%":    combo("Shift-5"),
    "^":    combo("Shift-6"),
    "&":    combo("Shift-7"),
    "*":    combo("Shift-8"),
    "(":    combo("Shift-9"),
    ")":    combo("Shift-0"),
    "_":    combo("Shift-Minus"),
    "+":    combo("Shift-Equal"),
    "{":    combo("Shift-Left_Brace"),
    "}":    combo("Shift-Right_Brace"),
    "|":    combo("Shift-Backslash"),
    ":":    combo("Shift-Semicolon"),
    "\"":   combo("Shift-Apostrophe"),
    "<":    combo("Shift-Comma"),
    ">":    combo("Shift-Dot"),
    "?":    combo("Shift-Slash")
}


# ─── MARKS ──────────────────────────────────────────────────────────────────


_mark_set = False


def with_mark(combo):
    if isinstance(combo, Key):
        combo = Combo(None, combo)

    def _with_mark():
        return combo.with_modifier(Modifier.SHIFT) if _mark_set else combo

    return _with_mark


def set_mark(mark_set):
    def _set_mark():
        global _mark_set
        _mark_set = mark_set

    return _set_mark


def with_or_set_mark(combo):
    if isinstance(combo, Key):
        combo = Combo(None, combo)

    def _with_or_set_mark():
        global _mark_set
        _mark_set = True
        return combo.with_modifier(Modifier.SHIFT)

    return _with_or_set_mark


# ─── STANDARD API ───────────────────────────────────────────────────────────


def include(file):
    config_globals = inspect.stack()[1][0].f_globals
    dirname = os.path.dirname(config_globals["__config__"])
    name = os.path.join(dirname, file)
    with open(name, "rb") as file:
        code = file.read()
    exec(compile(code, name, "exec"), config_globals)  # nosec


def timeouts(multipurpose: float = 1.0, suspend: float = 1.0):
    global _TIMEOUTS
    _TIMEOUTS = {"multipurpose": multipurpose, "suspend": suspend}


def add_modifier(name, aliases, key=None, keys=None):
    """
    Creates a new modifier and binds it to a key (or keys)

    After creation this modifier can be used in combos by using
    it's alias just like any of the built-in modifiers.

    add_modifier("HYPER", aliases = ["Hyper"], key = Key.F24)
    """
    return Modifier(name, aliases, key=key, keys=keys)


def wm_class_match(re_str):
    rgx = re.compile(re_str)

    def cond(ctx: KeyContext):
        return rgx.search(ctx.wm_class)

    return cond


def not_wm_class_match(re_str):
    rgx = re.compile(re_str)

    def cond(ctx: KeyContext):
        return not rgx.search(ctx.wm_class)

    return cond


# ─── HYPER MODIFIER SETUP ──────────────────────────────────────


_HYPER_WHEN_ALWAYS = lambda _: True

# Pending Hyper expansion configs, finalized by get_configuration()
_PENDING_HYPER_EXPANSIONS = []


def setup_hyper(trigger_key, tap_output=None,
                add_unshifted_layer=False,
                when=_HYPER_WHEN_ALWAYS):
    """
    Set up a Hyper modifier key scheme with a single call.

    Creates the HYPER modifier on the V_HYPER virtual carrier keycode,
    binds the trigger key via modmap or multipurpose_modmap, and queues
    the expansion keymap. The expansion keymap is auto-appended as the
    very last keymap by get_configuration(), so any user keymaps
    referencing Hyper combos automatically take priority.

    Parameters:
        trigger_key:            Physical Key to use as the Hyper key
                                (e.g., Key.CAPSLOCK)
        tap_output:             Optional Key to output on tap
                                (e.g., Key.ESC). Omit for pure modifier.
        add_unshifted_layer:    If False (default), single layer:
                                    Hyper-X → Shift+Ctrl+Alt+Super+X
                                If True, two layers:
                                    Hyper-X       → Ctrl+Alt+Super+X
                                    Shift+Hyper-X → Shift+Ctrl+Alt+Super+X
        when:                   Callable receiving KeyContext, controlling
                                when the Hyper modmap and expansion keymap
                                are active. Defaults to always active.
    """
    if not isinstance(trigger_key, Key):
        raise TypeError(
            f"setup_hyper: 'trigger_key' must be a Key, "
            f"got {type(trigger_key).__name__}"
        )

    if tap_output is not None and not isinstance(tap_output, Key):
        raise TypeError(
            f"setup_hyper: 'tap_output' must be a Key or None, "
            f"got {type(tap_output).__name__}"
        )

    if not isinstance(add_unshifted_layer, bool):
        raise TypeError(
            f"setup_hyper: 'add_unshifted_layer' must be True or False, "
            f"got {type(add_unshifted_layer).__name__}"
        )

    if not callable(when):
        raise TypeError(
            f"setup_hyper: 'when' must be callable, "
            f"got {type(when).__name__}"
        )

    if _PENDING_HYPER_EXPANSIONS:
        raise RuntimeError(
            "setup_hyper() has already been called. "
            "Only one Hyper modifier setup is supported."
        )

    # Create the HYPER modifier on the V_HYPER virtual carrier keycode
    Modifier("HYPER", aliases=["Hyper", "LHyper"], key=Key.V_HYPER)

    # Bind the physical trigger key to the virtual carrier
    if tap_output is not None:
        multipurpose_modmap("Hyper modifier (multipurpose)", {
            trigger_key: [tap_output, Key.V_HYPER],
        }, when=when)
        debug(
            f"setup_hyper: "
            f"{trigger_key.name} → tap: {tap_output.name}, hold: V_HYPER"
        )
    else:
        modmap("Hyper modifier", {
            trigger_key: Key.V_HYPER,
        }, when=when)
        debug(f"setup_hyper: {trigger_key.name} → V_HYPER")

    # Stash expansion config for get_configuration() to finalize
    _PENDING_HYPER_EXPANSIONS.append({
        "add_unshifted_layer":  add_unshifted_layer,
        "when":                 when,
    })

    if add_unshifted_layer:
        layer_desc = (
            "two layers: "
            "Hyper → C-Alt-Super, Shift-Hyper → Shift-C-Alt-Super"
        )
    else:
        layer_desc = "single layer: Hyper → Shift-C-Alt-Super"

    debug(f"setup_hyper: expansion mode: {layer_desc}")
    debug("setup_hyper: expansion keymap will be auto-appended after all user keymaps")


def _generate_hyper_expansion(pending):
    """
    Generate the Hyper expansion keymap dict from a pending configuration.

    Iterates all non-modifier keys and builds combo pairs mapping
    Hyper-modified input to the real multi-modifier expansion output.
    V_HYPER is automatically excluded because it was registered as a
    modifier key by the Modifier constructor.
    """
    add_unshifted_layer         = pending["add_unshifted_layer"]
    non_modifier_keys           = [key for key in Key if not Modifier.is_key_modifier(key)]

    expansion_dict              = {}

    if add_unshifted_layer:
        # Two layers:
        #   Hyper-X       → Ctrl+Alt+Super+X
        #   Shift-Hyper-X → Shift+Ctrl+Alt+Super+X
        for key in non_modifier_keys:
            expanded_l1_combo   = combo(f"C-Alt-Super-{key.name}")
            expanded_l2_combo   = combo(f"Shift-C-Alt-Super-{key.name}")
            expansion_dict[combo(f"Hyper-{key.name}")]          = expanded_l1_combo
            expansion_dict[combo(f"Shift-Hyper-{key.name}")]    = expanded_l2_combo
    else:
        # Single layer:
        #   Hyper-X → Shift+Ctrl+Alt+Super+X
        for key in non_modifier_keys:
            expanded_combo      = combo(f"Shift-C-Alt-Super-{key.name}")
            expansion_dict[combo(f"Hyper-{key.name}")]          = expanded_combo

    entry_count = len(expansion_dict)
    debug(f"_generate_hyper_expansion: generated {entry_count} expansion entries")

    return expansion_dict


# ─── LEVEL3-VIA-LEFT-ALT SETUP ─────────────────────────────────


_LEVEL3_WHEN_ALWAYS = lambda _: True

# Character-block key names (map directly to Key enum members; see
# models/key.py). These are the positions that can carry level3/level4
# glyphs on AltGr layouts. Space and all non-character keys are excluded —
# no level3 glyph, and/or they belong to motion/editing remaps.
_LEVEL3_KEY_NAMES = (
    "1", "2", "3", "4", "5", "6", "7", "8", "9", "0",
    "Minus", "Equal",
    "Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P",
    "Left_Brace", "Right_Brace",
    "A", "S", "D", "F", "G", "H", "J", "K", "L",
    "Semicolon", "Apostrophe", "Grave",
    "Backslash",
    "Z", "X", "C", "V", "B", "N", "M",
    "Comma", "Dot", "Slash",
)


def setup_level3_combos_via_left_alt(when=_LEVEL3_WHEN_ALWAYS):
    """
    Route left-Alt character combos to right-Alt, so the left Alt key can
    reach the level3 (AltGr/Option) and level4 (Shift+AltGr) glyph layers
    on layouts that place ISO_Level3_Shift on the right-Alt position — the
    Mac variants, AZERTY, and most non-US layouts.

    Left Alt keeps its real Mod1 identity for bare presses and mouse combos
    (Alt+click survives); only LAlt + a character key is rewritten, to RAlt
    + that key, which XKB then resolves to the level3 glyph. The Shift layer
    (Shift+LAlt -> Shift+RAlt) reaches level4.

    Input modifier is the specific LAlt, so right Alt is never touched.
    Exact combo matching means any combo also carrying Cmd/Ctrl/Super (e.g.
    Cmd+Option+X) does not match and passes through unchanged.

    The keymap is registered immediately, so its precedence is simply where
    this is called in the config — place the call where the character layer
    should win. 'when' gates the whole generated keymap and is evaluated
    live per event, so an overlay flag in the condition gives on-the-fly
    enable/disable.
    """
    if not callable(when):
        raise TypeError(
            f"setup_level3_combos_via_left_alt: 'when' must be callable, "
            f"got {type(when).__name__}"
        )

    level3_dict = {}
    for key_name in _LEVEL3_KEY_NAMES:
        level3_dict[combo(f"LAlt-{key_name}")]       = combo(f"RAlt-{key_name}")
        level3_dict[combo(f"Shift-LAlt-{key_name}")] = combo(f"Shift-RAlt-{key_name}")

    keymap("Level3 combos via Left Alt (auto-gen)", level3_dict, when=when)

    debug(
        f"setup_level3_combos_via_left_alt: generated {len(level3_dict)} "
        f"entries over {len(_LEVEL3_KEY_NAMES)} keys"
    )


# ─── WINDOW CONTEXT MATCHING ───────────────────────────────────


class _MatchProps:
    """Callable class implementing matchProps() window context matching."""

    _total_iterations       = 0
    _max_iterations         = 1000
    _max_reached            = False
    _full_debug             = False
    _startup_timestamp      = 0.0

    # Correct syntax to reject all positional parameters: put `*,` at beginning
    def __call__(self, *,
        # string parameters (positive matching)
        clas: str = None, name: str = None, devn: str = None,
        # string parameters (negative matching)
        not_clas: str = None, not_name: str = None, not_devn: str = None,
        # bool parameters
        numlk: bool = None, capslk: bool = None, cse: bool = None,
        # list of dicts of parameters (positive)
        lst: 'list[dict[str, str | bool]]' = None,
        # list of dicts of parameters (negative)
        not_lst: 'list[dict[str, str | bool]]' = None,
        dbg: str = None,    # debugging info (such as: which modmap/keymap?)
    ):  # returns Callable[[KeyContext], bool]
        """
        ### Match all given properties to current window context.       \n
        - Parameters must be _named_, no positional arguments.          \n
        - All parameters optional, but at least one must be given.      \n
        - Defaults to case insensitive matching of:                     \n
            - WM_CLASS, WM_NAME, device_name                            \n
        - To negate/invert regex pattern match use:                     \n
            - `not_clas` `not_name` `not_devn` params or...             \n
            - "^(?:(?!^pattern$).)*$"                                   \n
        - To force case insensitive pattern match use:                  \n
            - "^(?i:pattern)$" or...                                    \n
            - "^(?i)pattern$"                                           \n

        ### Accepted Parameters:                                        \n
        `clas` = WM_CLASS    (regex/string) [xprop WM_CLASS]            \n
        `name` = WM_NAME     (regex/string) [xprop _NET_WM_NAME]       \n
        `devn` = Device Name (regex/string) [xwaykeyz --list-devices]   \n
        `not_clas` = `clas` but inverted, matches when "not"            \n
        `not_name` = `name` but inverted, matches when "not"            \n
        `not_devn` = `devn` but inverted, matches when "not"            \n
        `numlk`    = Num Lock LED state         (bool)                  \n
        `capslk`   = Caps Lock LED state        (bool)                  \n
        `cse`      = Case Sensitive matching    (bool)                  \n
        `lst`      = List of dicts of the above arguments               \n
        `not_lst`  = `lst` but inverted, matches when "not"             \n
        `dbg`      = Debugging info             (string)                \n

        ### Negative match parameters:
        - `not_clas`|`not_name`|`not_devn`                              \n
        Parameters take same regex patterns as `clas`|`name`|`devn`     \n
        but result in a True condition only if pattern is NOT found.    \n
        Negative parameters cannot be used together with the normal     \n
        positive matching equivalent parameter in same instance.        \n

        ### List of Dicts parameter: `lst`|`not_lst`
        A [list] of {dicts} with each dict containing 1 to 6 of the    \n
        named parameters above, to be processed recursively as args.    \n
        A dict can also contain a single `lst` or `not_lst` argument.   \n

        ### Debugging info parameter: `dbg`
        A string that will print as part of logging output. Use to      \n
        help identify origin of logging output.                         \n
        -                                                               \n
        """
        # Reference for successful negative lookahead pattern, and
        # explanation of why it works:
        # https://stackoverflow.com/questions/406230/\
            # regular-expression-to-match-a-line-that-doesnt-contain-a-word

        cls = type(self)

        if cls._max_reached:
            bypass_guard_clauses = True
        elif cls._total_iterations >= cls._max_iterations:
            cls._max_reached = True
            bypass_guard_clauses = True
        else:
            cls._total_iterations += 1
            current_timestamp = time.time()

            time_elapsed = current_timestamp - cls._startup_timestamp

            # Bypass all guard clauses if more than a few seconds have passed since keymapper
            # started and loaded the config file. Inputs never change until keymapper
            # restarts and reloads the config file, so we don't need to keep checking.
            bypass_guard_clauses = time_elapsed > 6

        logging_enabled = False

        allowed_params  = (clas, name, devn, not_clas, not_name, not_devn,
                            numlk, capslk, cse, lst, not_lst, dbg)
        lst_dct_params  = (clas, name, devn, not_clas, not_name, not_devn,
                            numlk, capslk, cse)
        string_params   = (clas, name, devn, not_clas, not_name, not_devn, dbg)

        # This was using up a lot of CPU time, actually. Bad idea.
        # dct_param_strs  = list(inspect.signature(matchProps).parameters.keys())

        # Static list of parameter names. Using this instead of `inspect` cuts CPU
        # usage considerably, for reasons I don't yet understand. Apparently the
        # keymapper is actually running the entire function again on each key
        # press and release, rather than just re-evaluating the inner closure.
        dct_param_strs = [
            'clas', 'name', 'devn', 'not_clas', 'not_name', 'not_devn',
            'numlk', 'capslk', 'cse', 'lst', 'not_lst', 'dbg'
        ]

        # De Morgan's Law requires this to use "and" unless using parentheses to combine.
        # Ugly and confusing either way, if the negation is involved.
        # if not cls._max_reached and not bypass_guard_clauses:

        # Reversing the action order to use more understandable positive boolean logic
        if cls._max_reached or bypass_guard_clauses:
            pass            # guards already validated during warmup
        else:
            if all([x is None for x in allowed_params]):
                raise ValueError(
                    f"\n\n(EE) matchProps(): Received no valid argument\n")
            if any([x not in (True, False, None) for x in (numlk, capslk, cse)]):
                raise TypeError(
                    f"\n\n(EE) matchProps(): Params 'numlk|capslk|cse' are bools\n")
            if any([x is not None and not isinstance(x, str) for x in string_params]):
                raise TypeError(
                    f"\n\n(EE) matchProps(): These parameters must be strings:"
                    f"\n\t'clas|name|devn|not_clas|not_name|not_devn|dbg'\n")
            if clas and not_clas or name and not_name or devn and not_devn or lst and not_lst:
                raise ValueError(
                    f"\n\n(EE) matchProps(): Do not mix positive and "
                    f"negative match params for same property\n")

        # consolidate positive and negative matching params into new vars
        # only one should be in use at a time (checked above)
        _lst = not_lst if lst is None else lst
        _clas = not_clas if clas is None else clas
        _name = not_name if name is None else name
        _devn = not_devn if devn is None else devn

        # process lists of conditions
        if _lst is not None:

            # De Morgan's Law requires this to use "and" unless using parentheses to combine.
            # Ugly and confusing either way, if the negation is involved.
            # if not cls._max_reached and not bypass_guard_clauses:

            # Reversing the action order to use more understandable positive boolean logic
            if cls._max_reached or bypass_guard_clauses:
                pass            # guards already validated during warmup
            else:
                if any([x is not None for x in lst_dct_params]):
                    raise TypeError(
                        f"\n\n(EE) matchProps(): Param 'lst|not_lst' must be used alone\n")
                if not isinstance(_lst, list) or not all(isinstance(item, dict) for item in _lst):
                    raise TypeError(
                        f"\n\n(EE) matchProps(): Param 'lst|not_lst' wants a "
                        f"[list] of {{dicts}}\n")
                # verify that every {dict} in [list of dicts] only contains valid param names
                for dct in _lst:
                    for param in list(dct.keys()):
                        if param not in dct_param_strs:
                            error(f"matchProps(): Invalid parameter: '{param}'")
                            error(f"Invalid parameter is in this dict: \n\t{dct}")
                            error(f"Dict is in this list:")
                            for item in _lst:
                                print(f"\t{item}")
                            raise ValueError(
                                f"\n(EE) matchProps(): Invalid parameter found in "
                                f"dict in list. See log output before traceback.\n")

            def _matchProps_Lst(ctx: KeyContext):
                if not_lst is not None:
                    if logging_enabled:
                        print(f"## _matchProps_Lst()[not_lst] ## {dbg=}")
                    return not any(matchProps(**dct)(ctx) for dct in not_lst)
                else:
                    if logging_enabled:
                        print(f"## _matchProps_Lst()[lst] ## {dbg=}")
                    return any(matchProps(**dct)(ctx) for dct in lst)

            return _matchProps_Lst      # outer function returning inner function

        # compile case insensitive regex object for given params, unless cse=True
        if _clas is not None: clas_rgx = re.compile(_clas, 0 if cse else re.I)
        if _name is not None: name_rgx = re.compile(_name, 0 if cse else re.I)
        if _devn is not None: devn_rgx = re.compile(_devn, 0 if cse else re.I)

        # Capture cls for use in inner closure (avoids type(self) lookup per keystroke)
        _full_debug = cls._full_debug

        def _matchProps(ctx: KeyContext):
            nt_err = 'ERR: matchProps: NoneType in ctx.'

            # Full debug mode: use original cond_list approach for complete visibility
            if _full_debug:
                cond_list = []
                if numlk is not None:
                    cond_list.append(numlk is ctx.numlock_on)
                if capslk is not None:
                    cond_list.append(capslk is ctx.capslock_on)
                if _devn is not None:
                    devn_match = re.search(
                        devn_rgx, ctx.device_name or nt_err + 'device_name')
                    cond_list.append(
                        not devn_match if not_devn is not None else devn_match)
                if _clas is not None:
                    clas_match = re.search(
                        clas_rgx, ctx.wm_class or nt_err + 'wm_class')
                    cond_list.append(
                        not clas_match if not_clas is not None else clas_match)
                if _name is not None:
                    name_match = re.search(
                        name_rgx, ctx.wm_name or nt_err + 'wm_name')
                    cond_list.append(
                        not name_match if not_name is not None else name_match)
                print(f'####  CND_LST ({all(cond_list)})  ####  {dbg=}')
                for elem in cond_list:
                    print('##', re.sub(
                        r'^.*span=.*\), ', '', str(elem)).replace('>',''))
                print(
                    '-------------------------------------------------------------------')
                return all(cond_list)

            # Optimized path: short-circuit on first failure
            # Order: cheapest checks first, then most selective (devn), then clas, then name

            # Bool checks - nearly free (identity comparison)
            if numlk is not None and numlk is not ctx.numlock_on:
                return False
            if capslk is not None and capslk is not ctx.capslock_on:
                return False

            # Device check - most selective, eliminates most keystrokes from other devices
            if _devn is not None:
                devn_match = re.search(
                    devn_rgx, ctx.device_name or nt_err + 'device_name')
                # XOR: fail if (negative match requested) == (match found)
                if (not_devn is not None) == bool(devn_match):
                    return False

            # Class check - moderately selective, often complex regex patterns
            if _clas is not None:
                clas_match = re.search(
                    clas_rgx, ctx.wm_class or nt_err + 'wm_class')
                if (not_clas is not None) == bool(clas_match):
                    return False

            # Name check - least commonly used
            if _name is not None:
                name_match = re.search(
                    name_rgx, ctx.wm_name or nt_err + 'wm_name')
                if (not_name is not None) == bool(name_match):
                    return False

            return True

        return _matchProps      # outer function returning inner function


# Let the _MatchProps() class be used in place of original matchProps() function
matchProps = _MatchProps()
# Initiate the startup time
matchProps._startup_timestamp   = time.time()


def conditional(fn, what):
    """apply a conditional function to a keymap or modmap"""
    # TODO: check that fn is a valid conditional
    what.conditional = fn
    return what


# new API, requires name
def modmap(name, mappings, when=None):
    """Defines modmap (keycode translation)

    Example:

    define_modmap({
        Key.CAPSLOCK: Key.LEFT_CTRL
    })
    """
    mm = Modmap(name, mappings, when=when)
    _MODMAPS.append(mm)
    return mm


def multipurpose_modmap(name, mappings, when=None):
    """new API for declaring multipurpose modmaps"""
    for _, value in mappings.items():
        # TODO: why, we don't use this anywhere???
        value.append(Action.RELEASE)
    mmm = MultiModmap(name, mappings, when=when)
    _MULTI_MODMAPS.append(mmm)
    return mmm


# ─── KEYMAPS ────────────────────────────────────────────────────────────────


def keymap(name, mappings, when=None):
    """define and register a new keymap"""

    def expand(target):
        # Expand not L/R-specified modifiers
        # Suppose a nesting is not so deep
        # {K("C-a"): Key.A,
        #  K("C-b"): {
        #      K("LC-c"): Key.B,
        #      K("C-d"): Key.C}}
        # ->
        # {K("LC-a"): Key.A, K("RC-a"): Key.A,
        #  K("LC-b"): {
        #      K("LC-c"): Key.B,
        #      K("LC-d"): Key.C,
        #      K("RC-d"): Key.C},
        #  K("RC-b"): {
        #      K("LC-c"): Key.B,
        #      K("LC-d"): Key.C,
        #      K("RC-d"): Key.C}}
        if not isinstance(target, dict):
            return None
        expanded_mappings = {}
        keys_for_deletion = []
        for k, v in target.items():
            # Expand children
            expand(v)

            if isinstance(k, Combo):
                expanded_modifiers = []
                for modifier in k.modifiers:
                    if not modifier.is_specific():
                        variants = [modifier.to_left(), modifier.to_right()]
                        expanded_modifiers.append(variants)
                    else:
                        expanded_modifiers.append([modifier])

                # Create a Cartesian product of expanded modifiers
                expanded_modifier_lists = itertools.product(*expanded_modifiers)
                # Create expanded mappings
                for modifiers in expanded_modifier_lists:
                    expanded_mappings[Combo(modifiers, k.key)] = v
                keys_for_deletion.append(k)

        # Delete original keys that were expanded into expanded_mappings
        for key in keys_for_deletion:
            del target[key]
        # Merge expanded mappings into original mappings
        target.update(expanded_mappings)

    def wrap_keymap(name, mappings, depth=0):
        """convert naked dict objects into proper named keymaps"""
        if depth > 0:
            name = f"{name} (" * depth + " nested" + ")" * depth
        for k, v in mappings.items():
            if isinstance(v, dict):
                mappings[k] = wrap_keymap(name, v, depth + 1)
        return Keymap(name, mappings)

    expand(mappings)

    km = wrap_keymap(name, mappings)
    km.conditional = when
    _KEYMAPS.append(km)
    return km


# ─── OLD DEPRECATED API ─────────────────────────────────────────────────────


def define_timeout(seconds=1):
    """define timeout for suspending keys and resolving multimods"""
    global _TIMEOUTS
    _TIMEOUTS["multipurpose"] = seconds


# old API, takes name as an optional param
def define_modmap(mappings, name="anonymous modmap"):
    """old style API for defining modmaps"""
    return modmap(name, mappings)


def define_keymap(condition, mappings, name="anonymous keymap"):
    """old API for defining keymaps"""
    condition_fn = old_style_condition_to_fn(condition)
    return conditional(condition_fn, keymap(name, mappings))


def define_multipurpose_modmap(mappings):
    """Defines multipurpose modmap (multi-key translations)

    Give a key two different meanings. One when pressed and released alone and
    one when it's held down together with another key (making it a modifier
    key).

    Example:

    define_multipurpose_modmap(
        {Key.CAPSLOCK: [Key.ESC, Key.LEFT_CTRL]
    })
    """
    return multipurpose_modmap("default", mappings)


def define_conditional_multipurpose_modmap(condition, mappings):
    """Defines conditional multipurpose modmap (multi-key translation)

    Example:

    define_conditional_multipurpose_modmap(
        lambda wm_class, device_name: device_name.startswith("Microsoft"
    ), {
        {Key.CAPSLOCK: [Key.ESC, Key.LEFT_CTRL]
    })
    """
    condition_fn = old_style_condition_to_fn(condition)
    if not callable(condition_fn):
        raise ValueError("condition must be a function or compiled regexp")

    name = "anonymous multipurpose map (old API)"
    return conditional(condition_fn, multipurpose_modmap(name, mappings))


def old_style_condition_to_fn(condition):
    """converts old API style condition into a new style conditional"""
    condition_fn = None

    def re_search(regex: re.Pattern):
        def fn(ctx: KeyContext):
            return regex.search(ctx.wm_class)

        return fn

    def wm_class(wm_class_fn):
        def fn(ctx: KeyContext):
            return wm_class_fn(ctx.wm_class)

        return fn

    def wm_class_and_device(cond_fn):
        def fn(ctx: KeyContext):
            return cond_fn(ctx.wm_class, ctx.device_name)

        return fn

    if hasattr(condition, "search"):
        condition_fn = re_search(condition)
    elif callable(condition):
        if len(signature(condition).parameters) == 1:
            condition_fn = wm_class(condition)
        elif len(signature(condition).parameters) == 2:
            condition_fn = wm_class_and_device(condition)

    return condition_fn


def define_conditional_modmap(condition, mappings):
    """Defines conditional modmap (keycode translation)

    Example:

    define_conditional_modmap(re.compile(r'Emacs'), {
        Key.CAPSLOCK: Key.LEFT_CTRL
    })
    """

    condition_fn = old_style_condition_to_fn(condition)
    name = "define_conditional_modmap (old API)"

    if not callable(condition_fn):
        raise ValueError("condition must be a function or compiled regexp")

    return conditional(condition_fn, modmap(name, mappings))
    # _conditional_mod_map.append((condition, mod_remappings))


# End of File #
