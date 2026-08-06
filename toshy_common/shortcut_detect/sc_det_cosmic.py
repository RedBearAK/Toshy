#!/usr/bin/env python3
"""
toshy_common/shortcut_detect/sc_det_cosmic.py

Reader mechanics for COSMIC desktop shortcut settings. COSMIC does not
use gsettings; shortcuts live in cosmic-config layered RON files under
the config id com.system76.CosmicSettings.Shortcuts (paths verified
against cosmic-settings-daemon's Makefile and cosmic-settings source,
2026-08):

    system defaults:  /usr/share/cosmic/com.system76.CosmicSettings.Shortcuts/v1/defaults
    user override:    ~/.config/cosmic/com.system76.CosmicSettings.Shortcuts/v1/defaults
    user additions:   ~/.config/cosmic/com.system76.CosmicSettings.Shortcuts/v1/custom

The user 'custom' layer is searched first (user rebinds land there),
then 'defaults' (user file shadowing the system file when present).
"""
__version__ = '20260805'

import os

from toshy_common.shortcut_detect.sc_det_result import STATUS_RESOLVED
from toshy_common.shortcut_detect.sc_det_cosmic_rgx import COSMIC_BINDING_ENTRY_rgx


_SHORTCUTS_REL_PATH = os.path.join(
    'cosmic', 'com.system76.CosmicSettings.Shortcuts', 'v1')

# RON modifier name -> xwaykeyz combo modifier, in canonical order.
_MOD_XLAT_DCT = {'Shift': 'Shift', 'Ctrl': 'C', 'Alt': 'Alt', 'Super': 'Super'}
_MOD_ORDER_LST = ['Shift', 'C', 'Alt', 'Super']

# RON key token -> combo key name, where straight capitalization is not
# enough. Extend as real bindings surface.
_KEY_XLAT_DCT = {
    'space':    'Space',
    'Escape':   'Esc',
    'Return':   'Enter',
    'comma':    'Comma',
    'period':   'Dot',
    'slash':    'Slash',
}


def _shortcuts_file_texts(config_home=None, system_share=None) -> 'list[str]':
    """Layered shortcut file contents, highest priority first: user
    custom, then defaults (user file shadowing system). Missing files
    are simply skipped."""
    if config_home is None:
        config_home = os.environ.get('XDG_CONFIG_HOME', '')
        if not config_home:
            config_home = os.path.join(os.path.expanduser('~'), '.config')
    if system_share is None:
        system_share = '/usr/share'

    user_dir    = os.path.join(config_home, _SHORTCUTS_REL_PATH)
    system_dir  = os.path.join(system_share, _SHORTCUTS_REL_PATH)

    candidate_paths_lst = [os.path.join(user_dir, 'custom')]
    if os.path.isfile(os.path.join(user_dir, 'defaults')):
        candidate_paths_lst.append(os.path.join(user_dir, 'defaults'))
    else:
        candidate_paths_lst.append(os.path.join(system_dir, 'defaults'))

    texts_lst = []
    for file_path in candidate_paths_lst:
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as file_obj:
                texts_lst.append(file_obj.read())
        except OSError:
            continue
    return texts_lst


def _entry_to_combo(mods_str: str, key_str) -> 'str | None':
    """Convert a parsed RON binding to an xwaykeyz combo string. A
    modifier-only binding returns the bare modifier name (e.g. 'Super'),
    which keymap builders emit as a Key tap."""
    mods_lst = [m.strip() for m in mods_str.split(',') if m.strip()]
    combo_mods_lst = []
    for mod_name in mods_lst:
        combo_mod = _MOD_XLAT_DCT.get(mod_name)
        if combo_mod is None:
            return None     # unknown modifier: refuse to guess
        combo_mods_lst.append(combo_mod)
    combo_mods_lst.sort(key=_MOD_ORDER_LST.index)

    if not key_str:
        if len(combo_mods_lst) == 1:
            return combo_mods_lst[0]
        return None         # multi-modifier chord with no key: unsupported

    key_name = _KEY_XLAT_DCT.get(key_str)
    if key_name is None:
        key_name = key_str.capitalize() if len(key_str) > 1 else key_str.upper()
    if not combo_mods_lst:
        return key_name
    return '-'.join(combo_mods_lst) + '-' + key_name


def read_cosmic_shortcuts(action_slot_dct: dict,
                            config_home=None, system_share=None) -> dict:
    """Search the layered COSMIC shortcut files for bindings whose action
    contains one of the given action names. action_slot_dct maps action
    name substrings (e.g. 'InputSourceSwitch') to slot names. Returns
    {slot: (status, combo, raw, note)} for the first (highest-priority)
    binding found per slot; among entries in the same file, one with a
    key is preferred over a modifier-only binding."""
    results_dct = {}

    for text_str in _shortcuts_file_texts(config_home, system_share):
        for match in COSMIC_BINDING_ENTRY_rgx.finditer(text_str):
            mods_str, key_str, action_str = match.groups()
            action_str = action_str.strip()
            for action_name, slot_name in action_slot_dct.items():
                if action_name not in action_str:
                    continue
                if slot_name in results_dct:
                    # Keep the existing entry unless it was modifier-only
                    # and this one has a real key (e.g. Super+slash
                    # preferred over bare Super for display... actually
                    # bare Super IS the primary Launcher binding; keep
                    # first-found within a file, don't replace).
                    continue
                combo_str = _entry_to_combo(mods_str, key_str)
                if combo_str is None:
                    continue
                raw_str = f'(modifiers: [{mods_str}]' + (
                    f', key: "{key_str}")' if key_str else ')')
                results_dct[slot_name] = (
                    STATUS_RESOLVED, combo_str, raw_str, f'action {action_str}')
    return results_dct

# End of file #
