"""
Modmap region integrity checks (C1-C3): no-op modes, multi-null hazard,
exclusivity. Runnable standalone or via pytest (plain functions, no pytest
style). See tests/modmap_verifier_harness.py and the design docs:
docs/design/capslock_mode_matrix.md, docs/design/modmap_verifier_handoff.md

Toshy/tests/test_modmap_integrity.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from xwaykeyz.models.key import Key

from toshy_common.modifier_modes import CAPSLOCK_MODES, CAPSLOCK_MODE_DEFAULT

from tests.modmap_verifier_harness import (
    KBD_TYPES,
    build_namespace,
    resolve_cell,
    live_claimants,
    set_scenario,
    caps_position_inkey,
)


__version__ = '20260714'

# Cells where a non-default mode is EXPECTED to behave like the default,
# because IBM/Chromebook coverage is deferred (needs the base-modmap split
# described in the design matrix, section "Deferred"). When one of these is
# implemented, remove it here - the test then requires it to actually work.
KNOWN_DEFERRED_NOOP_CELLS = {
    # Bug B (multi nulled by base modmap claiming the Caps-position key):
    ('caps_is_esc_and_cmd',             'IBM',          'GUI'),
    ('caps_is_esc_and_cmd',             'IBM',          'Terminal'),
    ('caps_is_esc_and_cmd',             'Chromebook',   'Terminal'),
    ('caps_is_caps_and_cmd',            'IBM',          'GUI'),
    ('caps_is_caps_and_cmd',            'IBM',          'Terminal'),
    # Not applicable rather than deferred: Chromebook keyboards have no
    # CapsLock toggle at all (Caps position reports LEFT_META), so a
    # "Caps toggle & Cmd" mode is deliberately not registered there.
    ('caps_is_caps_and_cmd',            'Chromebook',   'GUI'),
    ('caps_is_caps_and_cmd',            'Chromebook',   'Terminal'),
    # Gap A remains on IBM/Cbk (cmd mode absent in their terminals):
    ('caps_is_cmd',                     'IBM',          'Terminal'),
    ('caps_is_cmd',                     'Chromebook',   'Terminal'),
    # New modes registered for Apple/Windows only, for now:
    ('caps_is_esc_and_lctrl',           'IBM',          'GUI'),
    ('caps_is_esc_and_lctrl',           'IBM',          'Terminal'),
    ('caps_is_esc_and_lctrl',           'Chromebook',   'GUI'),
    ('caps_is_esc_and_lctrl',           'Chromebook',   'Terminal'),
    ('caps_is_esc_and_lctrl_role_swap', 'IBM',          'GUI'),
    ('caps_is_esc_and_lctrl_role_swap', 'IBM',          'Terminal'),
    ('caps_is_esc_and_lctrl_role_swap', 'Chromebook',   'GUI'),
    ('caps_is_esc_and_lctrl_role_swap', 'Chromebook',   'Terminal'),
    ('caps_is_lctrl_role_swap',         'IBM',          'GUI'),
    ('caps_is_lctrl_role_swap',         'IBM',          'Terminal'),
    ('caps_is_lctrl_role_swap',         'Chromebook',   'GUI'),
    ('caps_is_lctrl_role_swap',         'Chromebook',   'Terminal'),
}

NON_DEFAULT_MODES = tuple(m for m in CAPSLOCK_MODES if m != CAPSLOCK_MODE_DEFAULT)


def test_no_silent_noop_modes():
    """C1: a selected non-default mode must change SOMETHING vs the default
    mode in every GUI/Terminal cell, unless the cell is a documented
    deferral. Deferred cells must in turn still BE no-ops, so the deferral
    list cannot rot. In Remote, every mode must equal raw passthrough."""
    ns, cnfg = build_namespace()
    problems = []

    for kbd_type in KBD_TYPES:
        for app_context in ('GUI', 'Terminal'):
            baseline = resolve_cell(
                ns, cnfg, CAPSLOCK_MODE_DEFAULT, kbd_type, app_context)
            base_pair = (baseline['caps'], baseline['lctrl'])
            for mode in NON_DEFAULT_MODES:
                cell = (mode, kbd_type, app_context)
                result = resolve_cell(ns, cnfg, mode, kbd_type, app_context)
                pair = (result['caps'], result['lctrl'])
                is_noop = (pair == base_pair)
                if is_noop and cell not in KNOWN_DEFERRED_NOOP_CELLS:
                    problems.append(f'SILENT NO-OP: {cell} resolves {pair}, '
                                    f'same as default mode')
                if not is_noop and cell in KNOWN_DEFERRED_NOOP_CELLS:
                    problems.append(f'STALE DEFERRAL: {cell} now resolves '
                                    f'{pair} vs baseline {base_pair} - remove '
                                    f'it from KNOWN_DEFERRED_NOOP_CELLS')

    for kbd_type in KBD_TYPES:
        for mode in CAPSLOCK_MODES:
            result = resolve_cell(ns, cnfg, mode, kbd_type, 'Remote')
            caps_inkey_name = caps_position_inkey(kbd_type).name
            if result['caps'] != caps_inkey_name or result['lctrl'] != 'LEFT_CTRL':
                problems.append(f'REMOTE NOT PASSTHROUGH: ({mode}, {kbd_type}, '
                                f"Remote) resolves Caps={result['caps']} "
                                f"LCtrl={result['lctrl']}")

    for problem in problems:
        print(f'  FAIL: {problem}')
    print(f'test_no_silent_noop_modes: '
            f'{"PASS" if not problems else f"{len(problems)} problem(s)"}')
    assert not problems
    return not problems


def test_no_nulled_multi_modmaps():
    """C2: if a live multipurpose modmap claims the Caps-position inkey, the
    resolved keystate must actually be multi. A plain modmap rewriting
    keystate.key first silently nulls the multi (selection is by inkey,
    application is by key). Known Bug B cells excepted until fixed."""
    ns, cnfg = build_namespace()
    problems = []

    for kbd_type in KBD_TYPES:
        for app_context in ('GUI', 'Terminal'):
            for mode in CAPSLOCK_MODES:
                cell = (mode, kbd_type, app_context)
                result = resolve_cell(ns, cnfg, mode, kbd_type, app_context)
                caps_inkey = caps_position_inkey(kbd_type)
                live_multis = [name for kind, name
                                in live_claimants(ns, caps_inkey)
                                if kind == 'multi']
                nulled = bool(live_multis) and not result['caps_keystate'].is_multi
                if nulled and cell not in KNOWN_DEFERRED_NOOP_CELLS:
                    problems.append(f'NULLED MULTI: {cell} selected '
                                    f'{live_multis} but result is not multi '
                                    f"(key became {result['caps']})")

    for problem in problems:
        print(f'  FAIL: {problem}')
    print(f'test_no_nulled_multi_modmaps: '
            f'{"PASS" if not problems else f"{len(problems)} problem(s)"}')
    assert not problems
    return not problems


def test_caps_block_exclusivity():
    """C3: in any single scenario, at most one Caps-block registration
    (name starts with 'Caps mode') may be live per inkey and per kind.
    A Caps-block registration beating a base registration is expected and
    not reported."""
    ns, cnfg = build_namespace()
    problems = []
    inkeys_of_interest = (Key.CAPSLOCK, Key.LEFT_CTRL, Key.LEFT_META)

    for kbd_type in KBD_TYPES:
        for app_context in ('GUI', 'Terminal', 'Remote'):
            for mode in CAPSLOCK_MODES:
                set_scenario(ns, cnfg, mode, kbd_type, app_context)
                for inkey in inkeys_of_interest:
                    caps_block_live = [
                        (kind, name) for kind, name in live_claimants(ns, inkey)
                        if name.startswith('Caps mode')]
                    plain_count = sum(1 for kind, _ in caps_block_live
                                        if kind == 'modmap')
                    multi_count = sum(1 for kind, _ in caps_block_live
                                        if kind == 'multi')
                    if plain_count > 1 or multi_count > 1:
                        problems.append(
                            f'EXCLUSIVITY: ({mode}, {kbd_type}, {app_context}) '
                            f'{inkey.name} claimed by {caps_block_live}')
                    # A plain Caps-block modmap and a Caps-block multi both
                    # live on the same inkey is the null hazard by design.
                    if plain_count and multi_count:
                        problems.append(
                            f'PLAIN+MULTI COLLISION: ({mode}, {kbd_type}, '
                            f'{app_context}) {inkey.name}: {caps_block_live}')

    for problem in problems:
        print(f'  FAIL: {problem}')
    print(f'test_caps_block_exclusivity: '
            f'{"PASS" if not problems else f"{len(problems)} problem(s)"}')
    assert not problems
    return not problems


def main():
    checks = [
        test_no_silent_noop_modes,
        test_no_nulled_multi_modmaps,
        test_caps_block_exclusivity,
    ]
    passed = 0
    for check in checks:
        try:
            if check():
                passed += 1
        except AssertionError:
            pass
    print(f'\n{passed}/{len(checks)} integrity checks passed')
    return passed == len(checks)


if __name__ == '__main__':
    sys.exit(0 if main() else 1)

# End of file #
