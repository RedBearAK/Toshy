#!/usr/bin/env python3
"""Regression tests for old and new Deskflow focus log messages.

Run with: python -m unittest discover -s tests -p test_deskflow_focus_logs.py
Requires watchdog, an existing Toshy runtime dependency.
"""

import unittest

from toshy_common.shared_device_context import DeskflowMonitor


class DeskflowFocusLogTests(unittest.TestCase):
    def setUp(self):
        self.monitor = DeskflowMonitor()

    def test_legacy_screen_messages(self):
        for message, expected in (
            ('INFO: entering screen', True),
            ('INFO: leaving screen', False),
        ):
            with self.subTest(message=message):
                self.assertIs(self.monitor.parse_log_line(message), expected)

    def test_computer_messages(self):
        for message, expected in (
            ('INFO: entering computer', True),
            ('INFO: leaving computer', False),
        ):
            with self.subTest(message=message):
                self.assertIs(self.monitor.parse_log_line(message), expected)

    def test_case_insensitive_messages_with_timestamp(self):
        for message, expected in (
            ('[2026-10-13T12:00:00] INFO: ENTERING COMPUTER', True),
            ('[2026-10-13T12:00:01] INFO: LEAVING COMPUTER', False),
            ('[2026-10-13T12:00:02] INFO: ENTERING SCREEN', True),
            ('[2026-10-13T12:00:03] INFO: LEAVING SCREEN', False),
        ):
            with self.subTest(message=message):
                self.assertIs(self.monitor.parse_log_line(message), expected)

    def test_unrelated_messages_do_not_change_focus(self):
        for message in (
            '',
            'INFO: connected to server',
            'WARNING: computer already entered',
            'WARNING: screen already entered',
        ):
            with self.subTest(message=message):
                self.assertIsNone(self.monitor.parse_log_line(message))


if __name__ == '__main__':
    unittest.main()
