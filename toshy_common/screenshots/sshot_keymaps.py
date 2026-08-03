#!/usr/bin/env python3
"""
toshy_common/screenshots/sshot_keymaps.py

Keymap construction layer for macOS-shape screenshot shortcuts.

The config file calls setup_screenshot_keymaps() once, passing in the
config-API callables (keymap, C, immediately, sleep) along with the
desktop environment info and the 'when' condition. This module resolves
the output combos (via the resolver module), builds the flat detected-
shortcut keymap plus the 4-then-Space window-shift nested keymap(s), and
registers them through the injected keymap() function.

Architecture note: toshy_common must not import xwaykeyz; the config file
is the only legitimate bridge. Injecting the config-API callables
preserves that rule while letting all the complicated parts live here
instead of in the config. The config passes its own globals() as the
injection carrier; this module extracts exactly these names from it:

    keymap, C, immediately        (required config-API objects)
    sleep                         (required only for window_shift_esc_first)
    DESKTOP_ENV, DE_MAJ_VER       (environment info)

Registration order note: keymap matching returns on the first registered
keymap containing a combo, so the config must call this function ABOVE
any keymap that still binds the same input combos (or those static
entries should be removed).

Typical config usage (the entire config-side footprint):

    from toshy_common.screenshots import setup_screenshot_keymaps

    setup_screenshot_keymaps(globals(), when = lambda ctx: ...)
"""
__version__ = '20260803'


from subprocess import DEVNULL

from toshy_common.proc_launcher import launch_detached
from toshy_common.screenshots.sshot_defaults import (
    SLOT_AREA_TO_CLIPBOARD,
    SLOT_AREA_TO_FILE,
    SLOT_FULLSCREEN_TO_CLIPBOARD,
    SLOT_FULLSCREEN_TO_FILE,
    SLOT_INTERACTIVE_UI,
    SLOT_WINDOW_TO_CLIPBOARD,
    SLOT_WINDOW_TO_FILE,
    STATUS_RESOLVED,
    CMD_FALLBACKS_DCT,
)
from toshy_common.screenshots.sshot_resolver import resolve_outputs


# Default macOS-shape input combos, expressed in the keymap's post-modmap
# world. The window slots have no direct inputs (macOS window capture is
# the 4-then-Space sequence, handled by the nested keymaps below).
#
# [?] Clipboard-variant inputs: macOS adds physical Ctrl, which lands on
# a different modifier in the GUI modmap world. 'RC-Super-...' assumed;
# verify before relying on the clipboard variants.
DEFAULT_INPUT_COMBOS_DCT = {
    SLOT_FULLSCREEN_TO_FILE:        'RC-Shift-Key_3',
    SLOT_AREA_TO_FILE:              'RC-Shift-Key_4',
    SLOT_INTERACTIVE_UI:            'RC-Shift-Key_5',
    SLOT_FULLSCREEN_TO_CLIPBOARD:   'RC-Super-Shift-Key_3',      # [?]
    SLOT_AREA_TO_CLIPBOARD:         'RC-Super-Shift-Key_4',      # [?]
}

# The 4-then-Space function shift pairs an area slot (nested keymap
# trigger, emitted immediately) with its window sibling (emitted on the
# Space continuation).
_WINDOW_SHIFT_PAIRS_LST = [
    (SLOT_AREA_TO_FILE,         SLOT_WINDOW_TO_FILE),
    (SLOT_AREA_TO_CLIPBOARD,    SLOT_WINDOW_TO_CLIPBOARD),
]

# Space continuation is bound bare and with still-held original
# modifiers, mirroring macOS where the toggle works mid-hold.
_SPACE_VARIANTS_LST = ['Space', 'Shift-Space', 'RC-Shift-Space']

# Outlets pass through to the DE overlay and disarm the nested keymap,
# so cancel (Esc) and confirm (Enter) never cost a keystroke.
_OUTLET_KEYS_LST = ['Esc', 'Enter']

_ESC_FIRST_DELAY_SEC = 0.2

# DEs whose area-capture overlay must be dismissed (Esc + pause) before
# the window shortcut can open the interactive window picker. Live-tested
# on KDE (2026-08): emitting the window shortcut with Spectacle's region
# overlay up completes/saves instead of shifting capture mode.
_ESC_FIRST_DESKTOP_ENVS = frozenset({'kde', 'plasma'})


def _log(msg_str: str):
    print(f'[SSHOT] {msg_str}', flush=True)


def _make_cmd_fallback_fn(cmd_candidates_lst: 'list[list[str]]'):
    """Build a keymap output callable that launches the first candidate
    command found on PATH. launch_detached() returns False when the
    executable is absent, so candidates double as version detection."""

    def _sshot_cmd_fallback(ctx):
        for cmd_lst in cmd_candidates_lst:
            if launch_detached(cmd_lst, stdout=DEVNULL, stderr=DEVNULL):
                return

    return _sshot_cmd_fallback


def _require_callable(name_str: str, obj):
    if callable(obj):
        return
    raise ValueError(
        f'setup_screenshot_keymaps() requires the config-API callable '
        f'{name_str!r}; got {obj!r}. Pass the config globals() in.')


def setup_screenshot_keymaps(config_globals_dct: dict, *, when=None,
                                input_combos_dct=None,
                                enable_window_shift=True,
                                window_shift_esc_first=None,
                                enable_command_fallbacks=True) -> 'list':
    """Build and register screenshot keymaps for the current desktop
    environment. Returns the list of registered keymap objects.

    config_globals_dct: the config file's globals(), carrying the
    config-API objects (keymap, C, immediately, sleep) and environment
    info (DESKTOP_ENV, DE_MAJ_VER) under their usual names.
    when: conditional applied to every registered keymap.
    input_combos_dct: optional replacement for DEFAULT_INPUT_COMBOS_DCT.
    enable_window_shift: build 4-then-Space nested keymaps when both legs
    of a pair resolve.
    window_shift_esc_first: emit Esc + delay before the window shortcut
    on the Space continuation. None (default) applies the library's
    per-DE knowledge automatically; True/False forces it either way.
    enable_command_fallbacks: for slots with no native binding to emit,
    bind curated tool-launch commands from the library's per-DE table
    (e.g. Cinnamon's interactive UI). False disables all command
    execution."""
    required_names_lst = ['keymap', 'C', 'immediately']
    missing_names_lst = [name for name in required_names_lst
                            if config_globals_dct.get(name) is None]
    if missing_names_lst:
        missing_names_str = ', '.join(missing_names_lst)
        raise ValueError(
            f'setup_screenshot_keymaps() could not find required config-API '
            f'name(s) in the provided namespace: {missing_names_str}. '
            f'Pass the config globals() as the first argument.')

    keymap      = config_globals_dct['keymap']
    C           = config_globals_dct['C']
    immediately = config_globals_dct['immediately']
    sleep       = config_globals_dct.get('sleep')

    _require_callable('keymap', keymap)
    _require_callable('C', C)

    desktop_env = config_globals_dct.get('DESKTOP_ENV')
    de_maj_ver  = config_globals_dct.get('DE_MAJ_VER')
    if desktop_env is None:
        raise ValueError(
            'setup_screenshot_keymaps() needs DESKTOP_ENV in the provided '
            'namespace. Pass the config globals() as the first argument.')

    desktop_env_norm = (desktop_env or '').strip().lower()

    if window_shift_esc_first is None:
        window_shift_esc_first = desktop_env_norm in _ESC_FIRST_DESKTOP_ENVS
    if window_shift_esc_first:
        _require_callable('sleep', sleep)

    if input_combos_dct is None:
        input_combos_dct = DEFAULT_INPUT_COMBOS_DCT

    results_dct = resolve_outputs(desktop_env, de_maj_ver)

    def _resolved_combo(slot_name: str) -> 'str | None':
        result = results_dct.get(slot_name)
        if result is None or result.status != STATUS_RESOLVED:
            return None
        return result.combo

    registered_lst = []
    shifted_area_slots_lst = []

    # Nested 4-then-Space keymaps first, so their triggers win over the
    # same combos in the flat keymap (which then excludes them anyway).
    if enable_window_shift:
        for area_slot, window_slot in _WINDOW_SHIFT_PAIRS_LST:
            input_combo     = input_combos_dct.get(area_slot)
            area_combo      = _resolved_combo(area_slot)
            window_combo    = _resolved_combo(window_slot)
            if not input_combo or not area_combo or not window_combo:
                continue

            if window_shift_esc_first:
                space_action = [C('Esc'), sleep(_ESC_FIRST_DELAY_SEC), C(window_combo)]
            else:
                space_action = C(window_combo)

            nested_dct = {immediately: C(area_combo)}
            for space_variant in _SPACE_VARIANTS_LST:
                nested_dct[C(space_variant)] = space_action
            for outlet_key in _OUTLET_KEYS_LST:
                nested_dct[C(outlet_key)] = C(outlet_key)

            km = keymap(
                f'Screenshots: 4-then-Space window shift ({area_slot})',
                {C(input_combo): nested_dct},
                when=when)
            registered_lst.append(km)
            shifted_area_slots_lst.append(area_slot)

    # Flat keymap for the remaining slots with resolved outputs, plus
    # curated command fallbacks for slots with no native binding at all.
    de_cmd_fallbacks_dct = CMD_FALLBACKS_DCT.get(desktop_env_norm, {})
    flat_mappings_dct = {}
    for slot_name, input_combo in input_combos_dct.items():
        if slot_name in shifted_area_slots_lst:
            continue
        output_combo = _resolved_combo(slot_name)
        if output_combo is None:
            if not enable_command_fallbacks:
                continue
            cmd_candidates_lst = de_cmd_fallbacks_dct.get(slot_name)
            if not cmd_candidates_lst:
                continue
            flat_mappings_dct[C(input_combo)] = _make_cmd_fallback_fn(cmd_candidates_lst)
            cmds_str = ' | '.join(' '.join(cmd_lst) for cmd_lst in cmd_candidates_lst)
            _log(f"Slot '{slot_name}' has no native binding; using command "
                    f'fallback (first found on PATH): {cmds_str}')
            continue
        flat_mappings_dct[C(input_combo)] = C(output_combo)

    if flat_mappings_dct:
        km = keymap('Screenshots: detected shortcuts', flat_mappings_dct, when=when)
        registered_lst.append(km)

    return registered_lst

# End of file #
