#!/usr/bin/env python3
"""
toshy_common/shortcut_detect/__main__.py

Generic detection check CLI (toshy-detector-check): dispatches to the
registered detection schemes' report functions. Run bare for a numbered
menu, pass a scheme name to run one directly, or --all for every scheme
(useful for pasting complete diagnostics into issue reports).

Adding a future detection scheme means one entry in _SCHEMES_LST here
plus a run_report() function in the feature package's __main__.
"""
__version__ = '20260805'

import os
import sys
import argparse


# (key, menu label) in menu order. Feature modules are imported lazily so
# a problem in one scheme cannot break checking the others.
_SCHEMES_LST = [
    ('screenshots',     'Screenshot shortcuts'),
    ('spotlight-input', 'Spotlight / input source switching'),
]


def _run_scheme(scheme_key: str, desktop_env, de_maj_ver, detect_note: str) -> int:
    if scheme_key == 'screenshots':
        from toshy_common.screenshots.__main__ import run_report
    elif scheme_key == 'spotlight-input':
        from toshy_common.spotlight_input.__main__ import run_report
    else:
        print(f'Unknown detection scheme: {scheme_key}')
        return 1
    return run_report(desktop_env, de_maj_ver, detect_note)


def _detect_environment() -> 'tuple[str, str | None]':
    try:
        from toshy_common.env_context import EnvironmentInfo
    except ImportError as import_err:
        print(f'Could not import Toshy environment detection: {import_err}')
        print("Pass the desktop environment explicitly, e.g.: --de kde --de-ver 6")
        sys.exit(1)
    env_info_dct = EnvironmentInfo().get_env_info()
    return (env_info_dct.get('DESKTOP_ENV'), env_info_dct.get('DE_MAJ_VER'))


def _menu_choice() -> 'list[str]':
    """Interactive numbered menu; returns the chosen scheme key(s)."""
    print()
    print('Toshy shortcut detection check')
    print()
    for idx, (_, label_str) in enumerate(_SCHEMES_LST, start=1):
        print(f'  {idx}) {label_str}')
    print(f'  a) All of the above')
    print()
    try:
        choice_str = input('Check which detection scheme? ').strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(1)

    if choice_str == 'a':
        return [key for key, _ in _SCHEMES_LST]
    try:
        choice_idx = int(choice_str)
        return [_SCHEMES_LST[choice_idx - 1][0]]
    except (ValueError, IndexError):
        print(f'Not a valid choice: {choice_str!r}')
        sys.exit(1)


def main() -> int:
    prog_str = os.environ.get('TOSHY_LAUNCHER_NAME') or 'python3 -m toshy_common.shortcut_detect'
    scheme_keys_lst = [key for key, _ in _SCHEMES_LST]
    parser = argparse.ArgumentParser(
        prog=prog_str,
        description='Show detected native shortcuts and the keymaps Toshy '
                    'would build from them, per detection scheme.')
    parser.add_argument('--version', action='version',
                        version=f'{prog_str} version {__version__}')
    parser.add_argument('scheme', nargs='?', choices=scheme_keys_lst, default=None,
                        help='detection scheme to check (omit for a menu)')
    parser.add_argument('--all', action='store_true', dest='run_all',
                        help='run every detection scheme')
    parser.add_argument('--de', metavar='DESKTOP_ENV', default=None)
    parser.add_argument('--de-ver', metavar='DE_MAJ_VER', default=None)
    args = parser.parse_args()

    if args.de is not None:
        desktop_env, de_maj_ver = args.de, args.de_ver
        detect_note = 'command line override'
    else:
        desktop_env, de_maj_ver = _detect_environment()
        detect_note = 'EnvironmentInfo detection'

    if args.run_all:
        # Identify the tool version in the full dump, since --all output
        # is what lands in issue reports.
        print(f'\n{prog_str} version {__version__} (--all)')
        chosen_keys_lst = scheme_keys_lst
    elif args.scheme is not None:
        chosen_keys_lst = [args.scheme]
    else:
        chosen_keys_lst = _menu_choice()

    rc = 0
    for idx, scheme_key in enumerate(chosen_keys_lst):
        if idx:
            print()
            print('=' * 78)
        rc |= _run_scheme(scheme_key, desktop_env, de_maj_ver, detect_note)
    return rc


if __name__ == '__main__':
    sys.exit(main())

# End of file #
