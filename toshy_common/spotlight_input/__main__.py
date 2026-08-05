#!/usr/bin/env python3
"""
toshy_common/spotlight_input/__main__.py

CLI diagnostic for Spotlight/input-switching shortcut discovery:
    toshy-spotlight-check [--de DE] [--de-ver VER]
Shows slot resolution and the literal keymaps for BOTH arrangements.
"""
__version__ = '20260805'

import os
import sys
import argparse

from toshy_common.shortcut_detect import RecordingAPI, print_keymap_records
from toshy_common.spotlight_input.spli_defaults import SLOT_NAMES
from toshy_common.spotlight_input.spli_keymaps import setup_spotlight_input_keymaps
from toshy_common.spotlight_input.spli_resolver import resolve_outputs


def _detect_environment() -> 'tuple[str, str | None]':
    try:
        from toshy_common.env_context import EnvironmentInfo
    except ImportError as import_err:
        print(f'Could not import Toshy environment detection: {import_err}')
        print("Pass the desktop environment explicitly, e.g.: --de kde --de-ver 6")
        sys.exit(1)
    env_info_dct = EnvironmentInfo().get_env_info()
    return (env_info_dct.get('DESKTOP_ENV'), env_info_dct.get('DE_MAJ_VER'))


class _FakeCnfg:
    swap_spotlight_and_input = False


class _ReprKeyAttr:
    """Renders as Key.<NAME> in the literal keymap output."""

    def __init__(self, name_str):
        self._name_str = name_str

    def __repr__(self):
        return f'Key.{self._name_str}'


class _FakeKey:
    """Stand-in for the xwaykeyz Key enum in the recording namespace."""

    def __getattr__(self, name_str):
        return _ReprKeyAttr(name_str)


def run_report(desktop_env, de_maj_ver, detect_note='') -> int:
    """Print the full detection report for one environment. Called by
    main() here and by the generic toshy-detector-check dispatcher
    (python3 -m toshy_common.shortcut_detect)."""
    print()
    print('Toshy Spotlight/input shortcut discovery')
    print(f"  Environment: DESKTOP_ENV={desktop_env!r}  DE_MAJ_VER={de_maj_ver!r}  ({detect_note})")
    print()

    results_dct = resolve_outputs(desktop_env, de_maj_ver)
    print('Slot resolution:')
    print(f'  {"slot".ljust(22)} {"status".ljust(11)} {"source".ljust(18)} '
            f'{"combo".ljust(20)} raw')
    print('  ' + '-' * 88)
    for slot_name in SLOT_NAMES:
        result = results_dct[slot_name]
        print(f'  {slot_name.ljust(22)} {result.status.ljust(11)} '
                f'{(result.source or "-").ljust(18)} '
                f'{(result.combo or "-").ljust(20)} {result.raw or "-"}')

    print()
    print('Generated keymaps (literal; base when= supplied by the config,')
    print('each arrangement additionally gated on cnfg.swap_spotlight_and_input):')
    api = RecordingAPI()
    ns_dct = api.namespace(
        DESKTOP_ENV=desktop_env, DE_MAJ_VER=de_maj_ver,
        iEF2NT=lambda: 'iEF2NT()', bind='bind', cnfg=_FakeCnfg(),
        Key=_FakeKey())
    setup_spotlight_input_keymaps(ns_dct, results_dct=results_dct)
    print_keymap_records(api.registered_lst)
    print()
    return 0


def main() -> int:
    prog_str = os.environ.get('TOSHY_LAUNCHER_NAME') or 'python3 -m toshy_common.spotlight_input'
    parser = argparse.ArgumentParser(
        prog=prog_str,
        description='Show detected launcher and input-switching shortcuts '
                    'and the keymaps Toshy would build from them.')
    parser.add_argument('--de', metavar='DESKTOP_ENV', default=None)
    parser.add_argument('--de-ver', metavar='DE_MAJ_VER', default=None)
    args = parser.parse_args()

    if args.de is not None:
        desktop_env, de_maj_ver = args.de, args.de_ver
        detect_note = 'command line override'
    else:
        desktop_env, de_maj_ver = _detect_environment()
        detect_note = 'EnvironmentInfo detection'

    return run_report(desktop_env, de_maj_ver, detect_note)


if __name__ == '__main__':
    sys.exit(main())

# End of file #
