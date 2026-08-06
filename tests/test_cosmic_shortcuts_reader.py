#!/usr/bin/env python3
"""
tests/test_cosmic_shortcuts_reader.py

Focused tests for the COSMIC layered RON shortcut reader: entry parsing
(keyed, modifier-only), combo conversion, layer priority (custom over
defaults), and the spotlight action mapping.
"""
__version__ = '20260805'

import os
import sys
import types
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

# Stub sibling deps BEFORE package imports (the package __init__ pulls
# sc_det_fallback -> proc_launcher -> xwaykeyz logger).
_fake_proc_launcher = types.ModuleType('toshy_common.proc_launcher')
_fake_proc_launcher.launch_detached = lambda args, **kwargs: False
sys.modules['toshy_common.proc_launcher'] = _fake_proc_launcher
_fake_logger = types.ModuleType('toshy_common.logger')
_fake_logger.debug = lambda *args, **kwargs: None
_fake_logger.error = lambda *args, **kwargs: None
_fake_logger.VERBOSE = False
sys.modules['toshy_common.logger'] = _fake_logger

from toshy_common.shortcut_detect.sc_det_cosmic import (
    _entry_to_combo,
    read_cosmic_shortcuts,
)


def _check(label_str: str, ok: bool) -> bool:
    print(f'  [{"PASS" if ok else "FAIL"}] {label_str}')
    return ok


def _write(path_str, content_str):
    os.makedirs(os.path.dirname(path_str), exist_ok=True)
    with open(path_str, 'w') as file_obj:
        file_obj.write(content_str)


_DEFAULTS_RON = '''{
    (modifiers: [Super, Alt], key: "Escape"): Terminate,
    (modifiers: [Super], key: "space"): System(InputSourceSwitch),
    (modifiers: [Super], key: "slash"): System(Launcher),
    (modifiers: [Super]): System(Launcher),
}
'''


def test_combo_conversion() -> bool:
    all_ok = True
    all_ok &= _check("Super+space -> 'Super-Space'",
        _entry_to_combo('Super', 'space') == 'Super-Space')
    all_ok &= _check("modifier-only Super -> bare 'Super'",
        _entry_to_combo('Super', None) == 'Super')
    all_ok &= _check('canonical modifier order (Shift before Super)',
        _entry_to_combo('Super, Shift', 'space') == 'Shift-Super-Space')
    all_ok &= _check('Ctrl maps to C',
        _entry_to_combo('Ctrl', 'Escape') == 'C-Esc')
    all_ok &= _check('unknown modifier refuses to guess',
        _entry_to_combo('Hyper', 'space') is None)
    print('\n--- combo conversion ---')
    return all_ok


def test_layered_read() -> bool:
    temp_dir = tempfile.mkdtemp()
    config_home = os.path.join(temp_dir, 'config')
    system_share = os.path.join(temp_dir, 'share')
    rel = os.path.join('cosmic', 'com.system76.CosmicSettings.Shortcuts', 'v1')

    _write(os.path.join(system_share, rel, 'defaults'), _DEFAULTS_RON)

    action_slot_dct = {'InputSourceSwitch': 'input_switch_next',
                        'Launcher': 'launcher_ui'}

    results_dct = read_cosmic_shortcuts(
        action_slot_dct, config_home=config_home, system_share=system_share)

    all_ok = True
    all_ok &= _check('system defaults: InputSourceSwitch -> Super-Space',
        results_dct.get('input_switch_next', (None, None))[1] == 'Super-Space')
    all_ok &= _check('launcher found (first entry wins: Super+slash)',
        results_dct.get('launcher_ui', (None, None))[1] == 'Super-Slash')

    # User custom layer takes priority for the same action.
    _write(os.path.join(config_home, rel, 'custom'),
            '{\n    (modifiers: [Ctrl, Alt], key: "space"): System(InputSourceSwitch),\n}\n')
    results_dct = read_cosmic_shortcuts(
        action_slot_dct, config_home=config_home, system_share=system_share)
    all_ok &= _check('user custom overrides defaults for the action',
        results_dct.get('input_switch_next', (None, None))[1] == 'C-Alt-Space')
    print('\n--- layered read ---')
    return all_ok


def test_screenshot_action_read() -> bool:
    """The screenshots package maps System(Screenshot) -> interactive_ui;
    bare Print must come through as combo 'Print'."""
    temp_dir = tempfile.mkdtemp()
    system_share = os.path.join(temp_dir, 'share')
    rel = os.path.join('cosmic', 'com.system76.CosmicSettings.Shortcuts', 'v1')
    _write(os.path.join(system_share, rel, 'defaults'),
            '{\n    (modifiers: [], key: "Print"): System(Screenshot),\n}\n')
    results_dct = read_cosmic_shortcuts(
        {'Screenshot': 'interactive_ui'},
        config_home=os.path.join(temp_dir, 'nope'), system_share=system_share)
    ok = _check("bare Print binding -> combo 'Print'",
        results_dct.get('interactive_ui', (None, None))[1] == 'Print')
    print('\n--- screenshot action read ---')
    return ok


def main():
    results_lst = [
        test_combo_conversion(),
        test_layered_read(),
        test_screenshot_action_read(),
    ]
    passed_cnt = sum(1 for result in results_lst if result)
    print(f'\nScore: {passed_cnt}/{len(results_lst)} test groups passed')
    return 0 if passed_cnt == len(results_lst) else 1


if __name__ == '__main__':
    sys.exit(main())

# End of file #
