"""
Modmap region hygiene checks (C4-C6): remote gating, mode-string coverage,
and completeness of the scan region. Runnable standalone or via pytest.
See tests/modmap_verifier_harness.py and the design docs.

Toshy/tests/test_modmap_hygiene.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from toshy_common.modifier_modes import CAPSLOCK_MODES, CAPSLOCK_MODE_DEFAULT

from tests.modmap_verifier_rgx import scan_mark_start_rgx, scan_mark_end_rgx
from tests.modmap_verifier_harness import (
    CONFIG_PATH,
    KBD_TYPES,
    build_namespace,
    set_scenario,
    all_registrations,
)


__version__ = '20260714'


def test_nothing_live_in_remote():
    """C4: with a remote app focused, NO conditional registration in the
    region may be live, for any mode and keyboard type. Toshy deliberately
    registers nothing for remote contexts."""
    ns, cnfg = build_namespace()
    problems = []

    for kbd_type in KBD_TYPES:
        for mode in CAPSLOCK_MODES:
            set_scenario(ns, cnfg, mode, kbd_type, 'Remote')
            for kind, registration in all_registrations():
                if registration.conditional(None):
                    problems.append(f'LIVE IN REMOTE: ({mode}, {kbd_type}) '
                                    f'{kind} "{registration.name}"')

    problems = sorted(set(problems))
    for problem in problems:
        print(f'  FAIL: {problem}')
    print(f'test_nothing_live_in_remote: '
            f'{"PASS" if not problems else f"{len(problems)} problem(s)"}')
    assert not problems
    return not problems


def test_every_mode_registers_something():
    """C5: every non-default mode string must activate at least one
    Caps-block registration in at least one (kbd, context) cell - a typo'd
    mode string in a `when` clause otherwise becomes a permanent silent
    no-op. The default mode must activate NONE (it is the absence of all
    Caps-block registrations, until the deferred base-modmap split lands)."""
    ns, cnfg = build_namespace()
    problems = []

    for mode in CAPSLOCK_MODES:
        live_cells = 0
        for kbd_type in KBD_TYPES:
            for app_context in ('GUI', 'Terminal'):
                set_scenario(ns, cnfg, mode, kbd_type, app_context)
                for _, registration in all_registrations():
                    if (registration.name.startswith('Caps mode')
                            and registration.conditional(None)):
                        live_cells += 1
        if mode == CAPSLOCK_MODE_DEFAULT:
            if live_cells:
                problems.append(f'DEFAULT MODE ACTIVATES: {mode} has '
                                f'{live_cells} live Caps-block registrations')
        elif not live_cells:
            problems.append(f'ORPHANED MODE: {mode} never activates any '
                            f'Caps-block registration (typo in a when clause?)')

    for problem in problems:
        print(f'  FAIL: {problem}')
    print(f'test_every_mode_registers_something: '
            f'{"PASS" if not problems else f"{len(problems)} problem(s)"}')
    assert not problems
    return not problems


def test_no_caps_keys_outside_region():
    """C6: no modmap/multipurpose_modmap registration OUTSIDE the scan region
    may claim CAPSLOCK, LEFT_CTRL, or LEFT_META as an inkey. Without this,
    the whole verification rests on an unverified extraction assumption.
    (Input position = 'Key.X:' at the start of a dict line; comments and the
    user-custom slice placeholder are ignored by requiring live code lines.)"""
    with open(CONFIG_PATH, encoding='utf-8') as config_file:
        config_source = config_file.read()

    start_match = scan_mark_start_rgx.search(config_source)
    end_match = scan_mark_end_rgx.search(config_source)
    assert start_match and end_match, 'SCAN_MARK lines missing from config'
    outside_source = (config_source[:start_match.start()]
                        + config_source[end_match.end():])

    problems = []
    in_registration = False
    registration_name = ''
    for line_text in outside_source.splitlines():
        stripped = line_text.strip()
        if stripped.startswith('#'):
            continue
        if (stripped.startswith('modmap(')
                or stripped.startswith('multipurpose_modmap(')):
            in_registration = True
            registration_name = stripped[:70]
            continue
        if in_registration and stripped.startswith('}'):
            in_registration = False
            continue
        if in_registration:
            for key_name in ('Key.CAPSLOCK:', 'Key.LEFT_CTRL:', 'Key.LEFT_META:'):
                if stripped.startswith(key_name):
                    problems.append(f'OUTSIDE REGION: {key_name[:-1]} claimed '
                                    f'by registration starting "{registration_name}"')

    for problem in problems:
        print(f'  FAIL: {problem}')
    print(f'test_no_caps_keys_outside_region: '
            f'{"PASS" if not problems else f"{len(problems)} problem(s)"}')
    assert not problems
    return not problems


def main():
    checks = [
        test_nothing_live_in_remote,
        test_every_mode_registers_something,
        test_no_caps_keys_outside_region,
    ]
    passed = 0
    for check in checks:
        try:
            if check():
                passed += 1
        except AssertionError:
            pass
    print(f'\n{passed}/{len(checks)} hygiene checks passed')
    return passed == len(checks)


if __name__ == '__main__':
    sys.exit(0 if main() else 1)

# End of file #
