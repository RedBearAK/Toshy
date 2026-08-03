#!/usr/bin/env python3
"""
tests/test_screenshot_kde_reader.py

Focused tests for the KDE kglobalshortcutsrc reader and the resolution
tiering in screenshot_shortcuts (live settings vs defaults table vs user
overrides, and disabled-shortcut handling).

Uses a temp directory as XDG_CONFIG_HOME with fixture file content shaped
like real kglobalshortcutsrc data.

Runnable standalone (accumulates a score in main) and collectable by
pytest (bool-returning test functions).
"""
__version__ = '20260803'


import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

# Stub out proc_launcher BEFORE package imports: the screenshots package
# __init__ transitively imports it, and it pulls in the xwaykeyz logger
# at module level, which isn't needed (or importable) in isolated tests.
import types as _types

_fake_proc_launcher = _types.ModuleType('toshy_common.proc_launcher')
_fake_proc_launcher.launch_detached = lambda args, **kwargs: False
sys.modules['toshy_common.proc_launcher'] = _fake_proc_launcher

from toshy_common.screenshots import sshot_resolver as screenshot_shortcuts
from toshy_common.screenshots.sshot_defaults import (
    KDE_DEFAULTS_DCT,
    SLOT_AREA_TO_CLIPBOARD,
    SLOT_AREA_TO_FILE,
    SLOT_FULLSCREEN_TO_FILE,
    SLOT_INTERACTIVE_UI,
    SLOT_WINDOW_TO_FILE,
    STATUS_DISABLED,
    STATUS_RESOLVED,
)
from toshy_common.screenshots.sshot_readers import read_kde


# Fixture shaped like a real kglobalshortcutsrc where the user has changed
# some Spectacle shortcuts: fullscreen disabled, region shortcut at
# default via empty current field, window shortcut with an alternate.
_FIXTURE_WITH_SECTION = '''[kwin]
Expose=Ctrl+F9,Ctrl+F9\\tMeta+F9,Toggle Present Windows (Current desktop)

[org.kde.spectacle.desktop]
_k_friendly_name=Spectacle
_launch=Print,Print,Launch Spectacle
FullScreenScreenShot=none,Shift+Print,Capture Entire Desktop
RectangularRegionScreenShot=,Meta+Shift+Print,Capture Rectangular Region
WindowUnderCursorScreenShot=Meta+Ctrl+Print\\tAlt+P,Meta+Ctrl+Print,Capture Window Under Cursor

[plasmashell]
activate task manager entry 1=Meta+1,Meta+1,Activate Task Manager Entry 1
'''

# Fixture with no Spectacle section at all (stock install, component
# never persisted by kglobalaccel).
_FIXTURE_NO_SECTION = '''[kwin]
Expose=Ctrl+F9,Ctrl+F9\\tMeta+F9,Toggle Present Windows (Current desktop)
'''


def _with_fixture_config(fixture_str: 'str | None', test_fn) -> bool:
    """Run test_fn with XDG_CONFIG_HOME pointing at a temp dir containing
    the fixture (or an empty dir when fixture_str is None)."""
    saved_xdg = os.environ.get('XDG_CONFIG_HOME')
    with tempfile.TemporaryDirectory() as temp_dir:
        os.environ['XDG_CONFIG_HOME'] = temp_dir
        if fixture_str is not None:
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


def test_reader_with_section() -> bool:

    def inner() -> bool:
        results_dct = read_kde()
        all_ok = True
        all_ok &= _check('interactive_ui resolved to Print',
            results_dct.get(SLOT_INTERACTIVE_UI, (None,))[0] == STATUS_RESOLVED
            and results_dct[SLOT_INTERACTIVE_UI][1] == 'Print')
        all_ok &= _check('fullscreen_to_file explicitly disabled',
            results_dct.get(SLOT_FULLSCREEN_TO_FILE, (None,))[0] == STATUS_DISABLED)
        all_ok &= _check('area_to_file resolved from empty-current default field',
            results_dct.get(SLOT_AREA_TO_FILE, (None,))[0] == STATUS_RESOLVED
            and results_dct[SLOT_AREA_TO_FILE][1] == 'Shift-Super-Print')
        all_ok &= _check('window_to_file takes first alternate',
            results_dct.get(SLOT_WINDOW_TO_FILE, (None,))[0] == STATUS_RESOLVED
            and results_dct[SLOT_WINDOW_TO_FILE][1] == 'C-Super-Print')
        all_ok &= _check('area_to_clipboard mirrors area_to_file',
            results_dct.get(SLOT_AREA_TO_CLIPBOARD, (None,))[0] == STATUS_RESOLVED
            and results_dct[SLOT_AREA_TO_CLIPBOARD][1] == 'Shift-Super-Print')
        return all_ok

    print('\n--- KDE reader: Spectacle section present ---')
    return _with_fixture_config(_FIXTURE_WITH_SECTION, inner)


def test_reader_without_section() -> bool:

    def inner() -> bool:
        results_dct = read_kde()
        return _check('reader returns {} when Spectacle section absent',
                        results_dct == {})

    print('\n--- KDE reader: no Spectacle section (stock install) ---')
    return _with_fixture_config(_FIXTURE_NO_SECTION, inner)


def test_resolution_tiers() -> bool:

    def inner_no_file() -> bool:
        results_dct = screenshot_shortcuts.resolve_outputs('kde')
        all_ok = True
        all_ok &= _check('defaults table fills area_to_file when no live settings',
            results_dct[SLOT_AREA_TO_FILE].status == STATUS_RESOLVED
            and results_dct[SLOT_AREA_TO_FILE].combo == KDE_DEFAULTS_DCT[SLOT_AREA_TO_FILE])
        return all_ok

    def inner_disabled_respected() -> bool:
        results_dct = screenshot_shortcuts.resolve_outputs('kde')
        all_ok = True
        all_ok &= _check('disabled native shortcut does NOT fall through to defaults',
            results_dct[SLOT_FULLSCREEN_TO_FILE].status == STATUS_DISABLED
            and results_dct[SLOT_FULLSCREEN_TO_FILE].combo is None)
        return all_ok

    def inner_override_wins() -> bool:
        screenshot_shortcuts.set_custom_output(SLOT_AREA_TO_FILE, 'C-Shift-F12')
        try:
            results_dct = screenshot_shortcuts.resolve_outputs('kde')
            entries_dct = screenshot_shortcuts.build_keymap_entries(
                {SLOT_AREA_TO_FILE: 'RC-Shift-Key_4'}, 'kde')
            all_ok = True
            all_ok &= _check('user override wins over live settings',
                results_dct[SLOT_AREA_TO_FILE].combo == 'C-Shift-F12')
            all_ok &= _check('build_keymap_entries emits override combo',
                entries_dct == {'RC-Shift-Key_4': 'C-Shift-F12'})
            return all_ok
        finally:
            screenshot_shortcuts.clear_custom_outputs()

    def inner_bad_slot_raises() -> bool:
        try:
            screenshot_shortcuts.set_custom_output('bogus_slot', 'Print')
        except ValueError:
            return _check('unknown slot name raises ValueError loudly', True)
        return _check('unknown slot name raises ValueError loudly', False)

    print('\n--- Resolution tiering ---')
    all_ok = True
    all_ok &= _with_fixture_config(None, inner_no_file)
    all_ok &= _with_fixture_config(_FIXTURE_WITH_SECTION, inner_disabled_respected)
    all_ok &= _with_fixture_config(_FIXTURE_WITH_SECTION, inner_override_wins)
    all_ok &= inner_bad_slot_raises()
    return all_ok


def main():
    results_lst = [
        test_reader_with_section(),
        test_reader_without_section(),
        test_resolution_tiers(),
    ]
    passed_cnt = sum(1 for result in results_lst if result)
    print(f'\nScore: {passed_cnt}/{len(results_lst)} test groups passed')
    return 0 if passed_cnt == len(results_lst) else 1


if __name__ == '__main__':
    sys.exit(main())

# End of file #
