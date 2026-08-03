#!/usr/bin/env python3
"""
toshy_common/screenshots/__main__.py

CLI diagnostic for the screenshot shortcut detection system. Shows the
per-slot resolution table (status, source, output combo, raw accelerator)
and a preview of the keymaps that setup_screenshot_keymaps() would build
from the default input combos.

Run as:
    python3 -m toshy_common.screenshots
    python3 -m toshy_common.screenshots --de kde --de-ver 6

Without --de, the desktop environment comes from Toshy's canonical
EnvironmentInfo detector (same as the kblayout_detect package does).
"""
__version__ = '20260802'

import os
import sys
import argparse

from toshy_common.screenshots.sshot_defaults import (
    CMD_FALLBACKS_DCT,
    SLOT_NAMES,
    STATUS_RESOLVED,
)
from toshy_common.screenshots.sshot_keymaps import (
    DEFAULT_INPUT_COMBOS_DCT,
    _ESC_FIRST_DELAY_SEC,
    _ESC_FIRST_DESKTOP_ENVS,
    _WINDOW_SHIFT_PAIRS_LST,
)
from toshy_common.screenshots.sshot_resolver import resolve_outputs


def _detect_environment() -> 'tuple[str, str | None]':
    """Get DESKTOP_ENV and DE_MAJ_VER from Toshy's canonical detector."""
    try:
        from toshy_common.env_context import EnvironmentInfo
    except ImportError as import_err:
        print(f'Could not import Toshy environment detection: {import_err}')
        print("Pass the desktop environment explicitly, e.g.: --de kde --de-ver 6")
        sys.exit(1)

    env_info_dct = EnvironmentInfo().get_env_info()
    return (env_info_dct.get('DESKTOP_ENV'), env_info_dct.get('DE_MAJ_VER'))


def _print_slot_table(results_dct: dict):
    name_width      = max(len(slot) for slot in SLOT_NAMES) + 2
    status_width    = 12
    source_width    = 20
    combo_width     = 22

    header_str = (f'  {"slot".ljust(name_width)}{"status".ljust(status_width)}'
                    f'{"source".ljust(source_width)}{"combo".ljust(combo_width)}raw')
    print(header_str)
    print('  ' + '-' * (len(header_str) + 8))

    for slot_name in SLOT_NAMES:
        result = results_dct[slot_name]
        combo_str   = result.combo if result.combo else '-'
        raw_str     = result.raw if result.raw else '-'
        print(f'  {slot_name.ljust(name_width)}{result.status.ljust(status_width)}'
                f'{(result.source or "-").ljust(source_width)}'
                f'{combo_str.ljust(combo_width)}{raw_str}')
        if result.note:
            print(f'  {"".ljust(name_width)}note: {result.note}')


def _print_keymap_preview(results_dct: dict, desktop_env: str):
    esc_first = (desktop_env or '').strip().lower() in _ESC_FIRST_DESKTOP_ENVS

    def resolved_combo(slot_name: str) -> 'str | None':
        result = results_dct.get(slot_name)
        if result is None or result.status != STATUS_RESOLVED:
            return None
        return result.combo

    shifted_slots_lst = []
    print("  4-then-Space window shift keymap(s):")
    for area_slot, window_slot in _WINDOW_SHIFT_PAIRS_LST:
        input_combo     = DEFAULT_INPUT_COMBOS_DCT.get(area_slot)
        area_combo      = resolved_combo(area_slot)
        window_combo    = resolved_combo(window_slot)
        if not input_combo or not area_combo or not window_combo:
            print(f'    (not built for {area_slot}: '
                    f'{"no input combo" if not input_combo else ""}'
                    f'{"area leg unresolved" if input_combo and not area_combo else ""}'
                    f'{"window leg unresolved" if input_combo and area_combo else ""})')
            continue
        shifted_slots_lst.append(area_slot)
        if esc_first:
            continuation_str = (f'Esc, {_ESC_FIRST_DELAY_SEC}s pause, '
                                f'{window_combo}')
        else:
            continuation_str = window_combo
        print(f'    {input_combo.ljust(24)}-> {area_combo}   '
                f'(then Space -> {continuation_str}; Esc/Enter pass through)')

    print("  Flat keymap ('Screenshots: detected shortcuts'):")
    flat_cnt = 0
    for slot_name, input_combo in DEFAULT_INPUT_COMBOS_DCT.items():
        if slot_name in shifted_slots_lst:
            continue
        output_combo = resolved_combo(slot_name)
        if output_combo is None:
            de_norm = (desktop_env or '').strip().lower()
            cmd_candidates_lst = CMD_FALLBACKS_DCT.get(de_norm, {}).get(slot_name)
            if cmd_candidates_lst:
                flat_cnt += 1
                cmds_str = ' | '.join(' '.join(cmd_lst) for cmd_lst in cmd_candidates_lst)
                print(f'    {input_combo.ljust(24)}-> [run first found: {cmds_str}]'
                        f'   ({slot_name}, command fallback)')
                continue
            print(f'    {input_combo.ljust(24)}   (skipped: {slot_name} not resolved)')
            continue
        flat_cnt += 1
        print(f'    {input_combo.ljust(24)}-> {output_combo.ljust(22)}({slot_name})')
    if not flat_cnt:
        print('    (no entries)')


def main() -> int:
    # Launcher stubs export TOSHY_LAUNCHER_NAME so --help shows the command
    # the user actually typed; direct module launch shows the module form.
    prog_str = os.environ.get('TOSHY_LAUNCHER_NAME') or 'python3 -m toshy_common.screenshots'
    parser = argparse.ArgumentParser(
        prog=prog_str,
        description='Show detected screenshot shortcuts and the keymaps '
                    'Toshy would build from them.')
    parser.add_argument('--de', metavar='DESKTOP_ENV',
        help="desktop environment override (e.g. 'kde', 'gnome', 'xfce')")
    parser.add_argument('--de-ver', metavar='DE_MAJ_VER',
        help='desktop environment major version override (e.g. 6, 42)')
    args = parser.parse_args()

    if args.de:
        desktop_env, de_maj_ver = (args.de, args.de_ver)
        env_source_str = 'command-line override'
    else:
        desktop_env, de_maj_ver = _detect_environment()
        if args.de_ver:
            de_maj_ver = args.de_ver
        env_source_str = 'EnvironmentInfo detection'

    print()
    print('Toshy screenshot shortcut discovery')
    print(f"  Environment: DESKTOP_ENV='{desktop_env}'  DE_MAJ_VER='{de_maj_ver}'"
            f'  ({env_source_str})')
    print()

    results_dct = resolve_outputs(desktop_env, de_maj_ver)
    print()
    print('Slot resolution:')
    _print_slot_table(results_dct)
    print()
    print('Keymap preview (default input combos):')
    _print_keymap_preview(results_dct, desktop_env)
    print()
    return 0


if __name__ == '__main__':
    sys.exit(main())

# End of file #
