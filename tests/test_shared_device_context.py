#!/usr/bin/env python3
"""
tests/test_shared_device_context.py

Focused tests for toshy_common.shared_device_context: the SynergyMonitor
preference for 'synergy.jsonl' (Synergy 3.9+) over a sibling legacy
'synergy.log', and focus-event parsing of both log formats.

Runnable standalone (accumulates a score in main) and collectable by
pytest (bool-returning test functions).
"""
__version__ = '20261028'


import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

# Stub out the logger BEFORE importing the module under test: it pulls in
# the xwaykeyz logger at module level, which isn't importable in isolated tests.
import types as _types

_fake_logger = _types.ModuleType('toshy_common.logger')
_fake_logger.debug = lambda *args, **kwargs: None
_fake_logger.error = lambda *args, **kwargs: None
_fake_logger.warn = lambda *args, **kwargs: None
_fake_logger.VERBOSE = False
sys.modules['toshy_common.logger'] = _fake_logger

from toshy_common import shared_device_context as sdc


LEGACY_LINE_ENTER = 'core       [2026-02-01T13:24:35] - INFO    - entering screen'
LEGACY_LINE_LEAVE = 'core       [2026-02-01T13:24:34] - INFO    - leaving screen'
JSONL_LINE_ENTER = ('{"ts":"2026-10-28T16:22:45.593Z","source":"core",'
                    '"level":"INFO","msg":"entering screen"}')
JSONL_LINE_LEAVE = ('{"ts":"2026-10-28T16:22:45.023Z","source":"core",'
                    '"level":"INFO","msg":"leaving screen"}')
JSONL_LINE_SWITCH = ('{"ts":"2026-10-28T16:22:45.023Z","source":"core","level":"INFO",'
                     '"msg":"switch from \\"jsystem76\\" to \\"jmacbookpro\\" at 772,0"}')


def _monitor_in(tmp_dir: str) -> sdc.SynergyMonitor:
    mon = sdc.SynergyMonitor()
    mon.log_paths = [
        os.path.join(tmp_dir, sdc.SynergyMonitor.LOG_NAME_JSONL),
        os.path.join(tmp_dir, sdc.SynergyMonitor.LOG_NAME_LEGACY),
    ]
    return mon


def _write(path: str, *lines: str) -> None:
    with open(path, 'w') as f:
        f.write('\n'.join(lines) + '\n')


def test_synergy_log_paths_include_both_names() -> bool:
    mon = sdc.SynergyMonitor()
    names = {os.path.basename(p) for p in mon.log_paths}
    first = os.path.basename(mon.log_paths[0])
    return names == {'synergy.jsonl', 'synergy.log'} and first == 'synergy.jsonl'


def test_synergy_prefers_jsonl_when_both_exist() -> bool:
    with tempfile.TemporaryDirectory() as tmp:
        mon = _monitor_in(tmp)
        _write(os.path.join(tmp, 'synergy.jsonl'), JSONL_LINE_ENTER)
        _write(os.path.join(tmp, 'synergy.log'), LEGACY_LINE_ENTER)
        paths = [p for p, _ in mon.get_active_log_file_paths()]
        return paths == [os.path.join(tmp, 'synergy.jsonl')]


def test_synergy_falls_back_to_legacy_log() -> bool:
    with tempfile.TemporaryDirectory() as tmp:
        mon = _monitor_in(tmp)
        _write(os.path.join(tmp, 'synergy.log'), LEGACY_LINE_ENTER)
        paths = [p for p, _ in mon.get_active_log_file_paths()]
        return paths == [os.path.join(tmp, 'synergy.log')]


def test_synergy_jsonl_alone() -> bool:
    with tempfile.TemporaryDirectory() as tmp:
        mon = _monitor_in(tmp)
        _write(os.path.join(tmp, 'synergy.jsonl'), JSONL_LINE_ENTER)
        paths = [p for p, _ in mon.get_active_log_file_paths()]
        return paths == [os.path.join(tmp, 'synergy.jsonl')]


def test_synergy_no_logs() -> bool:
    with tempfile.TemporaryDirectory() as tmp:
        mon = _monitor_in(tmp)
        return mon.get_active_log_file_paths() == [] and mon.get_log_file_path() is None


def test_synergy_parse_legacy_lines() -> bool:
    mon = sdc.SynergyMonitor()
    return (mon.parse_log_line(LEGACY_LINE_ENTER) is True
            and mon.parse_log_line(LEGACY_LINE_LEAVE) is False)


def test_synergy_parse_jsonl_lines() -> bool:
    mon = sdc.SynergyMonitor()
    return (mon.parse_log_line(JSONL_LINE_ENTER) is True
            and mon.parse_log_line(JSONL_LINE_LEAVE) is False
            and mon.parse_log_line(JSONL_LINE_SWITCH) is None)


TESTS = [
    test_synergy_log_paths_include_both_names,
    test_synergy_prefers_jsonl_when_both_exist,
    test_synergy_falls_back_to_legacy_log,
    test_synergy_jsonl_alone,
    test_synergy_no_logs,
    test_synergy_parse_legacy_lines,
    test_synergy_parse_jsonl_lines,
]


def main() -> int:
    passed = 0
    for test in TESTS:
        try:
            ok = bool(test())
        except Exception as e:
            ok = False
            print(f"  EXC  {test.__name__}: {e!r}")
        print(f"  {'PASS' if ok else 'FAIL'}  {test.__name__}")
        passed += ok
    print(f"\n{passed}/{len(TESTS)} passed")
    return 0 if passed == len(TESTS) else 1


if __name__ == '__main__':
    sys.exit(main())
