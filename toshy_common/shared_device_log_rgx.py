#!/usr/bin/env python3
"""
toshy_common/shared_device_log_rgx.py

Regex patterns for pulling timestamps out of shared-device (KVM) software
log lines in shared_device_context. Isolated in a dedicated module per
project convention.

Legacy plain-text logs (Synergy < 3.9, Deskflow, Input Leap, Barrier)
carry a bracketed local-time stamp, e.g.:

    core       [2026-02-01T13:24:35] - INFO    - entering screen

Some variants use a space instead of 'T' between date and time, so the
pattern accepts either. The captured group is the bare 'YYYY-MM-DD?HH:MM:SS'
string; the caller decides whether to read it as local time or UTC.
"""

import re


__version__ = '20261029'


# Captures the date-time portion of a legacy log line timestamp. The optional
# bracket handling lets the same pattern match stamps with or without '[...]'.
log_timestamp_rgx = re.compile(
    r'(?:.*\[|\[)?(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2})(?:\])?'
)

# End of file #
