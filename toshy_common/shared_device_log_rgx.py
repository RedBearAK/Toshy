#!/usr/bin/env python3
"""
toshy_common/shared_device_log_rgx.py

Regex patterns for pulling timestamps out of shared-device (KVM) software
log lines in shared_device_context. Isolated in a dedicated module per
project convention.

Legacy plain-text logs (Synergy < 3.9, Deskflow, Input Leap, Barrier)
carry a bracketed local-time stamp, e.g.:

    core       [2026-02-01T13:24:35] - INFO    - entering screen

Synergy 3.9+ writes JSON Lines whose 'ts' field is an ISO-8601 UTC string:

    {"ts":"2026-10-28T17:36:20.041Z","source":"core","level":"INFO","msg":"entering screen"}

Both patterns tolerate the common ISO-8601 / RFC 3339 variations so that a
change of mind upstream (fractional seconds, a zone offset instead of 'Z',
a space instead of 'T') does not silently break focus tracking.
"""

import re


__version__ = '20261029'


# Finds a date-time stamp anywhere in a legacy log line, with or without the
# surrounding '[...]'. The captured group is the whole stamp, including any
# fractional seconds and zone designator that happen to be attached, so the
# caller can hand it straight to the ISO parser below. The lookahead keeps a
# word that merely starts with 'Z' (or a longer digit run) from being read as
# a zone designator.
log_timestamp_rgx = re.compile(
    r'(?:.*\[|\[)?'
    r'(\d{4}-\d{2}-\d{2}[Tt ]\d{2}:\d{2}:\d{2}'
    r'(?:[.,]\d+)?'
    r'(?:(?:[Zz]|[+-]\d{2}(?::?\d{2})?)(?![A-Za-z0-9]))?)'
    r'(?:\])?'
)

# Decomposes one complete ISO-8601-ish date-time string into its parts.
# Groups: year, month, day, hour, minute, second, fraction (digits only, may
# be None), zulu ('Z'/'z' or None), offset sign, offset hours, offset minutes
# (the last three None when no numeric offset is present). Accepts 'T', 't'
# or a space as the date/time separator, '.' or ',' as the decimal mark, and
# optional whitespace before the zone designator.
iso_timestamp_rgx = re.compile(
    r'\s*(\d{4})-(\d{2})-(\d{2})[Tt ](\d{2}):(\d{2}):(\d{2})'
    r'(?:[.,](\d+))?'
    r'\s*(?:([Zz])|([+-])(\d{2})(?::?(\d{2}))?)?\s*'
)

# End of file #
