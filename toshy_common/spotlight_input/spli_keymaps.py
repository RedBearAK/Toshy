#!/usr/bin/env python3
"""
toshy_common/spotlight_input/spli_keymaps.py

Keymap builder for the Spotlight/input-switching feature. Registers BOTH
arrangements, each gated exclusively on cnfg.swap_spotlight_and_input in
its conditional (composed with the caller's base when=), so the toggle
switches live with no config reload.

DEFAULT arrangement (swap flag False; matches Toshy's historical remaps):
    RC-Space            -> launcher            (Cmd+Space)
    Super-Space         -> input primary       (physical Ctrl+Space, GUI)
    Shift-Super-Space   -> input secondary     (GUI)
    LC-Space            -> input primary       (physical Ctrl+Space, terms)
    Shift-LC-Space      -> input secondary     (terms)

SWAPPED arrangement (flag True; pre-Tiger classic: input on Cmd+Space):
    Super-Space         -> launcher            (physical Ctrl+Space, GUI)
    LC-Space            -> launcher            (terms; takes Ctrl+Space
                                                from terminal apps -- the
                                                user's explicit trade)
    RC-Space            -> input primary
    Shift-RC-Space      -> input secondary
    Shift-Super-Space   -> None (block displaced default)
    Shift-LC-Space      -> None (block displaced default)

GUI (Super-) and terminal (LC-) spellings of physical Ctrl+Space cohabit
in one keymap per arrangement: the modmaps make them context-disjoint.
Input primary = input_switch_last where the DE offers it (KDE, matching
macOS), else input_switch_next; secondary = next-after-last, or prev.
"""
__version__ = '20260804'

from toshy_common.logger import debug
from toshy_common.spotlight_input.spli_defaults import (
    SLOT_INPUT_SWITCH_LAST,
    SLOT_INPUT_SWITCH_NEXT,
    SLOT_INPUT_SWITCH_PREV,
    SLOT_LAUNCHER_UI,
)
from toshy_common.spotlight_input.spli_resolver import resolve_outputs
from toshy_common.shortcut_detect import STATUS_RESOLVED


def _require(name_str, config_globals_dct):
    obj = config_globals_dct.get(name_str)
    if obj is None:
        raise ValueError(
            f"setup_spotlight_input_keymaps() needs '{name_str}' in the "
            'provided namespace. Pass the config globals() as the first argument.')
    return obj


def setup_spotlight_input_keymaps(config_globals_dct: dict, when=None) -> 'list':
    """Build and register both arrangements of the Spotlight/input
    keymaps from resolved native shortcuts. Pass globals() and a base
    when= conditional; the swap preference gating is composed in here."""
    keymap  = _require('keymap', config_globals_dct)
    C       = _require('C', config_globals_dct)
    iEF2NT  = _require('iEF2NT', config_globals_dct)
    bind    = _require('bind', config_globals_dct)
    cnfg    = _require('cnfg', config_globals_dct)

    desktop_env = config_globals_dct.get('DESKTOP_ENV')
    de_maj_ver  = config_globals_dct.get('DE_MAJ_VER')
    if desktop_env is None:
        raise ValueError(
            'setup_spotlight_input_keymaps() needs DESKTOP_ENV in the '
            'provided namespace. Pass the config globals() as the first argument.')

    results_dct = resolve_outputs(desktop_env, de_maj_ver)

    def _combo(slot_name):
        result = results_dct.get(slot_name)
        if result is not None and result.status == STATUS_RESOLVED:
            return result.combo
        return None

    launcher_combo = _combo(SLOT_LAUNCHER_UI)
    last_combo     = _combo(SLOT_INPUT_SWITCH_LAST)
    next_combo     = _combo(SLOT_INPUT_SWITCH_NEXT)
    prev_combo     = _combo(SLOT_INPUT_SWITCH_PREV)

    # Primary follows macOS semantics: last-used toggle where the DE has
    # one, else forward cycle. Secondary: next (after last), else prev.
    primary_combo   = last_combo or next_combo
    secondary_combo = next_combo if last_combo else prev_combo

    registered_lst = []

    if launcher_combo is None and primary_combo is None:
        debug(f"SPOTL: No launcher or input shortcuts resolved for "
                f"'{desktop_env}'; no keymaps registered.", ctx='DT')
        return registered_lst

    launcher_action = [iEF2NT(), C(launcher_combo)] if launcher_combo else None

    def _when_default(ctx):
        base_ok = when(ctx) if when is not None else True
        return base_ok and not cnfg.swap_spotlight_and_input

    def _when_swapped(ctx):
        base_ok = when(ctx) if when is not None else True
        return base_ok and cnfg.swap_spotlight_and_input

    default_dct = {}
    if launcher_action is not None:
        default_dct[C('RC-Space')] = launcher_action
    if primary_combo:
        default_dct[C('Super-Space')]   = [bind, C(primary_combo)]
        default_dct[C('LC-Space')]      = [bind, C(primary_combo)]
    if secondary_combo:
        default_dct[C('Shift-Super-Space')] = [bind, C(secondary_combo)]
        default_dct[C('Shift-LC-Space')]    = [bind, C(secondary_combo)]

    swapped_dct = {}
    if launcher_action is not None:
        swapped_dct[C('Super-Space')]   = launcher_action
        swapped_dct[C('LC-Space')]      = launcher_action
    if primary_combo:
        swapped_dct[C('RC-Space')]      = [bind, C(primary_combo)]
    if secondary_combo:
        swapped_dct[C('Shift-RC-Space')] = [bind, C(secondary_combo)]
    swapped_dct[C('Shift-Super-Space')] = None
    swapped_dct[C('Shift-LC-Space')]    = None

    registered_lst.append(keymap(
        'Spotlight/input: default arrangement', default_dct, when=_when_default))
    registered_lst.append(keymap(
        'Spotlight/input: swapped arrangement', swapped_dct, when=_when_swapped))
    return registered_lst

# End of file #
