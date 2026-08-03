#!/usr/bin/env python3
"""
tests/test_screenshot_keymap_builder.py

Focused tests for setup_screenshot_keymaps() using fake injected
config-API callables (no xwaykeyz involvement) and a KDE fixture file so
resolution is deterministic.

Runnable standalone (accumulates a score in main) and collectable by
pytest (bool-returning test functions).
"""
__version__ = '20260801'


import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from toshy_common.screenshots.sshot_defaults import (
    SLOT_AREA_TO_FILE,
    SLOT_FULLSCREEN_TO_FILE,
)
from toshy_common.screenshots.sshot_keymaps import setup_screenshot_keymaps


# Full Spectacle section so every file slot resolves from "live" data.
_FIXTURE_FULL_SECTION = '''[org.kde.spectacle.desktop]
_launch=Print,Print,Launch Spectacle
FullScreenScreenShot=Shift+Print,Shift+Print,Capture Entire Desktop
RectangularRegionScreenShot=Meta+Shift+Print,Meta+Shift+Print,Capture Rectangular Region
ActiveWindowScreenShot=Meta+Print,Meta+Print,Capture Active Window
'''


class _FakeAPI:
    """Records keymap registrations; C() wraps combo strings in a tuple
    so mapping keys stay hashable and inspectable."""

    def __init__(self):
        self.registered_lst = []
        self.immediately = object()

    def C(self, combo_str):
        return ('COMBO', combo_str)

    def keymap(self, name_str, mappings_dct, when=None):
        record_dct = {'name': name_str, 'mappings': mappings_dct, 'when': when}
        self.registered_lst.append(record_dct)
        return record_dct

    def namespace(self, **extra_dct) -> dict:
        """Mimic the config file's globals() as the injection carrier."""
        ns_dct = {
            'keymap':       self.keymap,
            'C':            self.C,
            'immediately':  self.immediately,
            'DESKTOP_ENV':  'kde',
            'DE_MAJ_VER':   None,
        }
        ns_dct.update(extra_dct)
        return ns_dct


def _with_fixture_config(fixture_str: str, test_fn) -> bool:
    saved_xdg = os.environ.get('XDG_CONFIG_HOME')
    with tempfile.TemporaryDirectory() as temp_dir:
        os.environ['XDG_CONFIG_HOME'] = temp_dir
        file_path = os.path.join(temp_dir, 'kglobalshortcutsrc')
        with open(file_path, 'w', encoding='utf-8') as file_obj:
            file_obj.write(fixture_str)
        try:
            return test_fn()
        finally:
            if saved_xdg is None:
                os.environ.pop('XDG_CONFIG_HOME', None)
            else:
                os.environ['XDG_CONFIG_HOME'] = saved_xdg


def _check(label_str: str, condition: bool) -> bool:
    marker = 'ok  ' if condition else 'FAIL'
    print(f'  [{marker}] {label_str}')
    return condition


def test_builder_registers_keymaps() -> bool:

    def inner() -> bool:
        api = _FakeAPI()
        when_marker = lambda ctx: True
        registered_lst = setup_screenshot_keymaps(api.namespace(), when=when_marker)

        names_lst = [record['name'] for record in api.registered_lst]
        all_ok = True
        all_ok &= _check('window-shift keymap registered for area_to_file',
            any(SLOT_AREA_TO_FILE in name for name in names_lst))
        all_ok &= _check('flat detected-shortcuts keymap registered',
            any(name == 'Screenshots: detected shortcuts' for name in names_lst))
        all_ok &= _check("'when' condition passed through to every keymap",
            all(record['when'] is when_marker for record in api.registered_lst))
        all_ok &= _check('return value matches registrations',
            registered_lst == api.registered_lst)
        return all_ok

    print('\n--- Builder registration ---')
    return _with_fixture_config(_FIXTURE_FULL_SECTION, inner)


def test_nested_keymap_shape() -> bool:

    def inner() -> bool:
        api = _FakeAPI()
        setup_screenshot_keymaps(api.namespace())

        shift_record = next(record for record in api.registered_lst
                            if SLOT_AREA_TO_FILE in record['name'])
        trigger_combo = ('COMBO', 'RC-Shift-Key_4')
        nested_dct = shift_record['mappings'][trigger_combo]

        all_ok = True
        all_ok &= _check('immediately entry emits area combo',
            nested_dct[api.immediately] == ('COMBO', 'Shift-Super-Print'))
        all_ok &= _check('Space continuation emits window combo',
            nested_dct[('COMBO', 'Space')] == ('COMBO', 'Super-Print'))
        all_ok &= _check('held-modifier Space variant bound',
            nested_dct[('COMBO', 'RC-Shift-Space')] == ('COMBO', 'Super-Print'))
        all_ok &= _check('Esc outlet passes through',
            nested_dct[('COMBO', 'Esc')] == ('COMBO', 'Esc'))
        all_ok &= _check('Enter outlet passes through',
            nested_dct[('COMBO', 'Enter')] == ('COMBO', 'Enter'))
        return all_ok

    print('\n--- Nested keymap shape ---')
    return _with_fixture_config(_FIXTURE_FULL_SECTION, inner)


def test_flat_keymap_exclusions_and_guards() -> bool:

    def inner() -> bool:
        api = _FakeAPI()
        setup_screenshot_keymaps(api.namespace())

        flat_record = next(record for record in api.registered_lst
                            if record['name'] == 'Screenshots: detected shortcuts')
        flat_keys_lst = list(flat_record['mappings'].keys())

        all_ok = True
        all_ok &= _check('area trigger excluded from flat keymap (owned by nested)',
            ('COMBO', 'RC-Shift-Key_4') not in flat_keys_lst)
        all_ok &= _check('fullscreen entry present in flat keymap',
            flat_record['mappings'].get(('COMBO', 'RC-Shift-Key_3')) == ('COMBO', 'Shift-Print'))
        return all_ok

    def inner_missing_api() -> bool:
        api = _FakeAPI()
        bad_ns_dct = api.namespace()
        del bad_ns_dct['keymap']
        del bad_ns_dct['immediately']
        try:
            setup_screenshot_keymaps(bad_ns_dct)
        except ValueError as err:
            names_named = 'keymap' in str(err) and 'immediately' in str(err)
            return _check('missing names raise ValueError naming them', names_named)
        return _check('missing names raise ValueError naming them', False)

    print('\n--- Flat keymap exclusions and guards ---')
    all_ok = True
    all_ok &= _with_fixture_config(_FIXTURE_FULL_SECTION, inner)
    all_ok &= inner_missing_api()
    return all_ok


def main():
    results_lst = [
        test_builder_registers_keymaps(),
        test_nested_keymap_shape(),
        test_flat_keymap_exclusions_and_guards(),
    ]
    passed_cnt = sum(1 for result in results_lst if result)
    print(f'\nScore: {passed_cnt}/{len(results_lst)} test groups passed')
    return 0 if passed_cnt == len(results_lst) else 1


if __name__ == '__main__':
    sys.exit(main())

# End of file #
