#!/usr/bin/env python3
"""
tests/test_shared_device_context.py

Focused tests for toshy_common.shared_device_context around Synergy 3.9+
support: the 'synergy.jsonl' vs 'synergy.log' sibling preference by mtime,
UTC parsing of JSON Lines timestamps versus local parsing of legacy stamps,
tolerance for ISO-8601 variants (offsets, fractions, separators) in both,
focus-event parsing of both formats, and the once-only "ignoring" debug line.

Runnable standalone (accumulates a score in main) and collectable by
pytest (bool-returning test functions).
"""
__version__ = '20261029'

import os
import sys
import time
import types
import calendar
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

# Stub the logger BEFORE importing the module under test. Sibling test files
# install their own stubs of 'toshy_common.logger' (without 'warn'), and the
# one installed first wins when pytest collects the whole folder in one
# process, so this file carries a complete stub of its own.
_fake_logger = types.ModuleType('toshy_common.logger')
_fake_logger.debug = lambda *args, **kwargs: None
_fake_logger.error = lambda *args, **kwargs: None
_fake_logger.warn = lambda *args, **kwargs: None
_fake_logger.VERBOSE = False
sys.modules['toshy_common.logger'] = _fake_logger

from toshy_common import shared_device_context as sdc


LEGACY_LINE_ENTER = 'core       [2026-02-01T13:24:35] - INFO    - entering screen'
LEGACY_LINE_LEAVE = 'core       [2026-02-01T13:24:34] - INFO    - leaving screen'
LEGACY_LINE_SPACE = 'core       [2026-02-01 13:24:35] - INFO    - entering screen'
JSONL_LINE_ENTER = ('{"ts":"2026-10-28T17:36:20.366Z","source":"core",'
                    '"level":"INFO","msg":"entering screen"}')
JSONL_LINE_LEAVE = ('{"ts":"2026-10-28T17:36:20.041Z","source":"core",'
                    '"level":"INFO","msg":"leaving screen"}')
JSONL_LINE_SWITCH = ('{"ts":"2026-10-28T17:36:20.366Z","source":"core","level":"INFO",'
                     '"msg":"switch from \\"jmacbookpro\\" to \\"jsystem76\\" at 4723,2132"}')
JSONL_LINE_NO_ZONE = '{"ts":"2026-10-28T17:36:20","source":"core","level":"INFO","msg":"x"}'
JSONL_LINE_BROKEN = '{"ts":"2026-10-28T17:36:20.366Z","source":'

# Epoch for 2026-10-28T17:36:20Z, computed independently of the module under test.
JSONL_ENTER_EPOCH = calendar.timegm((2026, 10, 28, 17, 36, 20, 0, 0, 0))
JSONL_ENTER_EPOCH_FRAC = JSONL_ENTER_EPOCH + 0.366
LEGACY_ENTER_EPOCH_LOCAL = time.mktime(time.strptime('2026-02-01T13:24:35', '%Y-%m-%dT%H:%M:%S'))
LEGACY_ENTER_EPOCH_UTC = calendar.timegm((2026, 2, 1, 13, 24, 35, 0, 0, 0))


def _report(label_str: str, ok: bool) -> bool:
    print(f"  [{'ok  ' if ok else 'FAIL'}] {label_str}")
    return ok


def _close(actual: 'float | None', expected: float) -> bool:
    return actual is not None and abs(actual - expected) < 1e-6


def _jsonl(ts_json: str) -> str:
    """Build a JSON Lines entry whose 'ts' is the given raw JSON value text."""
    return '{"ts":' + ts_json + ',"source":"core","level":"INFO","msg":"entering screen"}'


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


def _active_paths(mon: sdc.SynergyMonitor) -> 'list[str]':
    return [path for path, _ in mon.get_active_log_file_paths()]


def test_log_path_list_shape() -> bool:
    print('\n--- log_paths covers both names, jsonl first per directory ---')
    mon = sdc.SynergyMonitor()
    names_lst = [os.path.basename(p) for p in mon.log_paths]
    all_ok = True
    all_ok = _report('even count of candidate paths', len(names_lst) % 2 == 0) and all_ok
    all_ok = _report('alternating jsonl/log order',
                     names_lst == ['synergy.jsonl', 'synergy.log'] * (len(names_lst) // 2)) and all_ok
    return all_ok


def test_sibling_preference_by_mtime() -> bool:
    print('\n--- sibling preference: newer mtime wins, either direction ---')
    all_ok = True
    with tempfile.TemporaryDirectory() as tmp:
        mon = _monitor_in(tmp)
        jsonl_path = os.path.join(tmp, 'synergy.jsonl')
        legacy_path = os.path.join(tmp, 'synergy.log')
        _write(jsonl_path, JSONL_LINE_ENTER)
        _write(legacy_path, LEGACY_LINE_ENTER)
        now = time.time()

        os.utime(legacy_path, (now - 3600, now - 3600))
        os.utime(jsonl_path, (now, now))
        all_ok = _report('jsonl newer -> only jsonl watched',
                         _active_paths(mon) == [jsonl_path]) and all_ok

        os.utime(jsonl_path, (now - 3600, now - 3600))
        os.utime(legacy_path, (now, now))
        all_ok = _report('legacy newer (downgrade) -> only legacy watched',
                         _active_paths(mon) == [legacy_path]) and all_ok
    return all_ok


def test_single_log_and_no_log() -> bool:
    print('\n--- only one log present, or none ---')
    all_ok = True
    with tempfile.TemporaryDirectory() as tmp:
        mon = _monitor_in(tmp)
        all_ok = _report('no logs -> empty list', mon.get_active_log_file_paths() == []) and all_ok
        all_ok = _report('no logs -> get_log_file_path None', mon.get_log_file_path() is None) and all_ok

        legacy_path = os.path.join(tmp, 'synergy.log')
        _write(legacy_path, LEGACY_LINE_ENTER)
        all_ok = _report('legacy alone -> legacy watched', _active_paths(mon) == [legacy_path]) and all_ok
        os.remove(legacy_path)

        jsonl_path = os.path.join(tmp, 'synergy.jsonl')
        _write(jsonl_path, JSONL_LINE_ENTER)
        all_ok = _report('jsonl alone -> jsonl watched', _active_paths(mon) == [jsonl_path]) and all_ok
    return all_ok


def test_timestamp_extraction() -> bool:
    print('\n--- extract_line_timestamp: JSONL as UTC, legacy as local ---')
    mon = sdc.SynergyMonitor()
    all_ok = True
    all_ok = _report('jsonl Z stamp parsed as UTC epoch, fraction kept',
                     _close(mon.extract_line_timestamp(JSONL_LINE_ENTER), JSONL_ENTER_EPOCH_FRAC)) and all_ok
    all_ok = _report('legacy T stamp parsed as local epoch',
                     mon.extract_line_timestamp(LEGACY_LINE_ENTER) == LEGACY_ENTER_EPOCH_LOCAL) and all_ok
    all_ok = _report('legacy space stamp parsed as local epoch',
                     mon.extract_line_timestamp(LEGACY_LINE_SPACE) == LEGACY_ENTER_EPOCH_LOCAL) and all_ok
    all_ok = _report('jsonl stamp without zone -> read as UTC (not local)',
                     _close(mon.extract_line_timestamp(JSONL_LINE_NO_ZONE), JSONL_ENTER_EPOCH)) and all_ok
    all_ok = _report('truncated jsonl line -> None, no exception',
                     mon.extract_line_timestamp(JSONL_LINE_BROKEN) is None) and all_ok
    all_ok = _report('line with no stamp -> None',
                     mon.extract_line_timestamp('nothing to see here') is None) and all_ok
    # Other monitors keep the legacy-only behavior.
    deskflow = sdc.DeskflowMonitor()
    all_ok = _report('DeskflowMonitor still parses legacy stamp as local',
                     deskflow.extract_line_timestamp(LEGACY_LINE_ENTER) == LEGACY_ENTER_EPOCH_LOCAL) and all_ok
    return all_ok


def test_timestamp_syntax_variants() -> bool:
    print('\n--- timestamp syntax variants: offsets, fractions, separators, numbers ---')
    mon = sdc.SynergyMonitor()
    deskflow = sdc.DeskflowMonitor()
    all_ok = True

    # JSON path: every zone spelling of the same instant lands on the same epoch.
    same_instant_lst = [
        ('upper Z',             '"2026-10-28T17:36:20Z"'),
        ('lower z',             '"2026-10-28T17:36:20z"'),
        ('+00:00',              '"2026-10-28T17:36:20+00:00"'),
        ('+0000',               '"2026-10-28T17:36:20+0000"'),
        ('+00',                 '"2026-10-28T17:36:20+00"'),
        ('space before offset', '"2026-10-28 17:36:20 +0000"'),
        ('-08:00 shifted',      '"2026-10-28T09:36:20-08:00"'),
        ('+0530 shifted',       '"2026-10-28T23:06:20+0530"'),
        ('+05 shifted',         '"2026-10-28T22:36:20+05"'),
        ('space separator',     '"2026-10-28 17:36:20Z"'),
        ('lowercase t',         '"2026-10-28t17:36:20Z"'),
        ('naive = UTC in JSON', '"2026-10-28T17:36:20"'),
        ('epoch seconds int',   str(JSONL_ENTER_EPOCH)),
        ('epoch seconds float', f'{JSONL_ENTER_EPOCH}.0'),
        ('epoch milliseconds',  str(JSONL_ENTER_EPOCH * 1000)),
    ]
    for label_str, ts_json in same_instant_lst:
        all_ok = _report(f'json {label_str}',
                         _close(mon.extract_line_timestamp(_jsonl(ts_json)), JSONL_ENTER_EPOCH)) and all_ok

    # Fractional seconds: any digit count, dot or comma, kept in the result.
    fraction_lst = [
        ('1 digit',     '"2026-10-28T17:36:20.3Z"',          0.3),
        ('3 digits',    '"2026-10-28T17:36:20.366Z"',        0.366),
        ('6 digits',    '"2026-10-28T17:36:20.366123Z"',     0.366123),
        ('9 digits',    '"2026-10-28T17:36:20.366123456Z"',  0.366123456),
        ('comma mark',  '"2026-10-28T17:36:20,25Z"',         0.25),
        ('frac+offset', '"2026-10-28T09:36:20.5-08:00"',     0.5),
    ]
    for label_str, ts_json, frac in fraction_lst:
        all_ok = _report(f'json fraction {label_str}',
                         _close(mon.extract_line_timestamp(_jsonl(ts_json)),
                                JSONL_ENTER_EPOCH + frac)) and all_ok

    # Alternate key names, in case 'ts' is renamed.
    for key in ('time', 'timestamp', '@timestamp'):
        line = '{"' + key + '":"2026-10-28T17:36:20Z","msg":"entering screen"}'
        all_ok = _report(f'json key {key!r} accepted',
                         _close(mon.extract_line_timestamp(line), JSONL_ENTER_EPOCH)) and all_ok

    # Rejections: no exception, None back.
    reject_lst = [
        ('garbage string',   '"yesterday"'),
        ('month 13',         '"2026-13-01T00:00:00Z"'),
        ('offset +25:00',    '"2026-10-28T17:36:20+25:00"'),
        ('offset +05:60',    '"2026-10-28T17:36:20+05:60"'),
        ('trailing junk',    '"2026-10-28T17:36:20Zjunk"'),
        ('bool true',        'true'),
        ('null',             'null'),
        ('nested object',    '{"ts":"2026-10-28T17:36:20Z"}'),
        ('no timestamp key', '"x", "other":"2026-10-28T17:36:20Z"'),
    ]
    for label_str, ts_json in reject_lst:
        line = _jsonl(ts_json) if label_str != 'no timestamp key' else \
            '{"other":"2026-10-28T17:36:20Z","msg":"entering screen"}'
        all_ok = _report(f'json reject {label_str} -> None',
                         mon.extract_line_timestamp(line) is None) and all_ok

    # Legacy path: a stamp that carries its own offset is honored regardless
    # of the machine's zone; a bare stamp stays local as before.
    legacy_offset_line = 'core       [2026-02-01T05:24:35-08:00] - INFO    - entering screen'
    legacy_frac_line = 'core       [2026-02-01T13:24:35.250] - INFO    - entering screen'
    legacy_zulu_line = 'core       [2026-02-01T13:24:35Z] - INFO    - entering screen'
    for monitor_name, monitor in (('Synergy', mon), ('Deskflow', deskflow)):
        all_ok = _report(f'{monitor_name} legacy stamp with -08:00 -> absolute UTC epoch',
                         _close(monitor.extract_line_timestamp(legacy_offset_line),
                                LEGACY_ENTER_EPOCH_UTC)) and all_ok
        all_ok = _report(f'{monitor_name} legacy stamp with Z -> UTC epoch',
                         _close(monitor.extract_line_timestamp(legacy_zulu_line),
                                LEGACY_ENTER_EPOCH_UTC)) and all_ok
        all_ok = _report(f'{monitor_name} legacy stamp with fraction -> local epoch + fraction',
                         _close(monitor.extract_line_timestamp(legacy_frac_line),
                                LEGACY_ENTER_EPOCH_LOCAL + 0.25)) and all_ok
        all_ok = _report(f'{monitor_name} bare legacy stamp still local',
                         _close(monitor.extract_line_timestamp(LEGACY_LINE_ENTER),
                                LEGACY_ENTER_EPOCH_LOCAL)) and all_ok
    # A word starting with 'Z' right after a stamp is not a zone designator.
    all_ok = _report('legacy stamp followed by "Zoom" stays local',
                     _close(deskflow.extract_line_timestamp('2026-02-01T13:24:35Zoom call'),
                            LEGACY_ENTER_EPOCH_LOCAL)) and all_ok
    return all_ok


def test_parse_log_line_both_formats() -> bool:
    print('\n--- parse_log_line: substring match works on both formats ---')
    mon = sdc.SynergyMonitor()
    all_ok = True
    all_ok = _report('legacy entering -> True', mon.parse_log_line(LEGACY_LINE_ENTER) is True) and all_ok
    all_ok = _report('legacy leaving -> False', mon.parse_log_line(LEGACY_LINE_LEAVE) is False) and all_ok
    all_ok = _report('jsonl entering -> True', mon.parse_log_line(JSONL_LINE_ENTER) is True) and all_ok
    all_ok = _report('jsonl leaving -> False', mon.parse_log_line(JSONL_LINE_LEAVE) is False) and all_ok
    all_ok = _report('jsonl switch -> None', mon.parse_log_line(JSONL_LINE_SWITCH) is None) and all_ok
    return all_ok


def test_handler_does_not_drop_fresh_utc_events() -> bool:
    print('\n--- LogWatcherHandler keeps a just-written UTC event ---')
    seen_lst = []
    all_ok = True
    with tempfile.TemporaryDirectory() as tmp:
        mon = _monitor_in(tmp)
        jsonl_path = os.path.join(tmp, 'synergy.jsonl')
        _write(jsonl_path, JSONL_LINE_SWITCH)
        handler = sdc.LogWatcherHandler(
            log_path=jsonl_path,
            parse_func=mon.parse_log_line,
            timestamp_func=mon.extract_line_timestamp,
            on_focus_change=seen_lst.append,
        )
        handler.handle_log_file_change()
        all_ok = _report('init call defaults to focus True', seen_lst == [True]) and all_ok

        # Append a "leaving screen" line stamped a few seconds from now in UTC.
        # Before the fix, a timezone east of UTC would read this as hours old
        # and drop it as "before monitor startup".
        future_utc = time.strftime('%Y-%m-%dT%H:%M:%S', time.gmtime(time.time() + 5))
        with open(jsonl_path, 'a') as f:
            f.write('{"ts":"' + future_utc + '.000Z","source":"core","level":"INFO",'
                    '"msg":"leaving screen"}\n')
        handler.handle_log_file_change()
        all_ok = _report('fresh UTC leaving event delivered', seen_lst == [True, False]) and all_ok
    return all_ok


def test_stale_sibling_debug_once() -> bool:
    print('\n--- "ignoring" debug line emitted once per stale path ---')
    captured_lst = []
    original_debug = sdc.debug
    sdc.debug = lambda *args, **kwargs: captured_lst.append(' '.join(str(a) for a in args))
    try:
        with tempfile.TemporaryDirectory() as tmp:
            mon = _monitor_in(tmp)
            jsonl_path = os.path.join(tmp, 'synergy.jsonl')
            legacy_path = os.path.join(tmp, 'synergy.log')
            _write(jsonl_path, JSONL_LINE_ENTER)
            _write(legacy_path, LEGACY_LINE_ENTER)
            now = time.time()
            os.utime(legacy_path, (now - 3600, now - 3600))
            os.utime(jsonl_path, (now, now))
            for _ in range(3):
                mon.get_active_log_file_paths()
    finally:
        sdc.debug = original_debug
    ignoring_lst = [msg for msg in captured_lst if msg.startswith('Ignoring Synergy log file')]
    return _report('three calls, one ignoring line', len(ignoring_lst) == 1)


def main() -> int:
    results_lst = [
        test_log_path_list_shape(),
        test_sibling_preference_by_mtime(),
        test_single_log_and_no_log(),
        test_timestamp_extraction(),
        test_timestamp_syntax_variants(),
        test_parse_log_line_both_formats(),
        test_handler_does_not_drop_fresh_utc_events(),
        test_stale_sibling_debug_once(),
    ]
    passed_cnt = sum(1 for result in results_lst if result)
    print(f'\nScore: {passed_cnt}/{len(results_lst)} test groups passed')
    return 0 if passed_cnt == len(results_lst) else 1


if __name__ == '__main__':
    sys.exit(main())

# End of file #
