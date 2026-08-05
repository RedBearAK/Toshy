#!/usr/bin/env python3
"""
tests/test_sc_det_accel_parse.py

Focused tests for the shortcut_detect package: accelerator normalization
(KDE and GTK styles) and kglobalshortcutsrc value field parsing.

Runnable standalone (accumulates a score in main) and collectable by
pytest (bool-returning test functions).
"""
__version__ = '20260803'


import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

# Stub out proc_launcher BEFORE package imports: the screenshots package
# __init__ transitively imports it, and it pulls in the xwaykeyz logger
# at module level, which isn't needed (or importable) in isolated tests.
import types as _types

_fake_proc_launcher = _types.ModuleType('toshy_common.proc_launcher')
_fake_proc_launcher.launch_detached = lambda args, **kwargs: False
sys.modules['toshy_common.proc_launcher'] = _fake_proc_launcher
_fake_logger = _types.ModuleType('toshy_common.logger')
_fake_logger.debug = lambda *args, **kwargs: None
_fake_logger.error = lambda *args, **kwargs: None
_fake_logger.VERBOSE = False
sys.modules['toshy_common.logger'] = _fake_logger

from toshy_common.shortcut_detect import (
    STATUS_DISABLED,
    STATUS_RESOLVED,
    normalize_gtk_accel,
    normalize_kde_accel,
    parse_kde_shortcut_value,
)


def _check_cases(label_str: str, case_fn, cases_lst: 'list[tuple]') -> bool:
    all_ok = True
    print(f'\n--- {label_str} ---')
    for input_val, expected_val in cases_lst:
        actual_val = case_fn(input_val)
        ok = actual_val == expected_val
        all_ok = all_ok and ok
        marker = 'ok  ' if ok else 'FAIL'
        print(f'  [{marker}] {input_val!r:45} -> {actual_val!r}  (expected {expected_val!r})')
    return all_ok


def test_kde_accel_normalization() -> bool:
    cases_lst = [
        ('Print',                       'Print'),
        ('Shift+Print',                 'Shift-Print'),
        ('Meta+Print',                  'Super-Print'),
        ('Meta+Shift+Print',            'Shift-Super-Print'),
        ('Meta+Ctrl+Print',             'C-Super-Print'),
        ('Ctrl+Alt+T',                  'C-Alt-T'),
        ('Meta+Shift+S',                'Shift-Super-S'),
        ('Meta',                        'Super'),           # modifier-only shortcut
        ('Volume Down',                 None),              # multi-word key name
        ('Bogus+Print',                 None),              # unknown modifier
        ('',                            None),
    ]
    return _check_cases('KDE accel normalization', normalize_kde_accel, cases_lst)


def test_gtk_accel_normalization() -> bool:
    cases_lst = [
        ('Print',                       'Print'),
        ('<Shift>Print',                'Shift-Print'),
        ('<Alt>Print',                  'Alt-Print'),
        ('<Control><Shift>Print',       'Shift-C-Print'),
        ('<Primary>Print',              'C-Print'),
        ('<Ctrl><Alt>Print',            'C-Alt-Print'),
        ('<Super>p',                    'Super-p'),
        ('XF86MonBrightnessUp',         'XF86MonBrightnessUp'),
        ('<Bogus>Print',                None),
        ('',                            None),
    ]
    return _check_cases('GTK accel normalization', normalize_gtk_accel, cases_lst)


def test_kde_value_parsing() -> bool:
    cases_lst = [
        # Full three-field form.
        ('Print,Print,Launch Spectacle',                    (STATUS_RESOLVED, 'Print')),
        # Empty current field falls back to the default field.
        (',Shift+Print,Capture Entire Desktop',             (STATUS_RESOLVED, 'Shift+Print')),
        # Explicitly disabled.
        ('none,Meta+Print,Capture Active Window',           (STATUS_DISABLED, None)),
        # Alternates: first one wins (literal backslash-t in file data).
        ('Ctrl+F9\\tMeta+F9,Ctrl+F9,Toggle Expose',         (STATUS_RESOLVED, 'Ctrl+F9')),
        # Alternates in the default field after empty current.
        (',Ctrl+F9\\tMeta+F9,Toggle Expose',                (STATUS_RESOLVED, 'Ctrl+F9')),
        # Plasma 6 services-style single-field form.
        ('Ctrl+Alt+Space',                                  (STATUS_RESOLVED, 'Ctrl+Alt+Space')),
        # Single-field disabled and empty forms.
        ('none',                                            (STATUS_DISABLED, None)),
        ('',                                                (STATUS_DISABLED, None)),
    ]
    return _check_cases('KDE value field parsing', parse_kde_shortcut_value, cases_lst)


def main():
    results_lst = [
        test_kde_accel_normalization(),
        test_gtk_accel_normalization(),
        test_kde_value_parsing(),
    ]
    passed_cnt = sum(1 for result in results_lst if result)
    print(f'\nScore: {passed_cnt}/{len(results_lst)} test groups passed')
    return 0 if passed_cnt == len(results_lst) else 1


if __name__ == '__main__':
    sys.exit(main())

# End of file #
