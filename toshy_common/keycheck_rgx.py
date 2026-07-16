#!/usr/bin/env python3
"""
toshy_common/keycheck_rgx.py

Regex patterns for parsing xwaykeyz verbose log lines in the 'toshy-keycheck'
diagnostic tool. Isolated in a dedicated module per project convention.

Patterns are matched against individual lines of the keymapper's verbose
output stream. Key names may appear either bare (LEFT_ALT) or with the
enum prefix (Key.LEFT_ALT) depending on which debug line produced them,
so the prefix is optionally consumed wherever a key name is captured.

The '(XX)' context markers at the start of each line come from the
xwaykeyz logger ('II' = input, 'DD' = debug, 'OO' = output, etc.).
"""

import re


__version__ = '20260715'


# (II) in CAPSLOCK (press) / (release) / (repeat)
_rgx_in_key = re.compile(
    r"^\(II\) in (?:Key\.)?(\S+) \((press|release|repeat)\)"
)

# (DD) MODMAP: Key.CAPSLOCK => Key.LEFT_META [User hardware keys]
_rgx_modmap = re.compile(
    r"^\(DD\) MODMAP: (?:Key\.)?(\S+) => (?:Key\.)?(\S+) \[(.*)\]\s*$"
)

# (DD) MULTI_MODMAP: LEFT_ALT => LEFT_META / RIGHT_CTRL (R_CONTROL mod) [name]
# The '(X mod)' suffix after the held identity is optional in the source.
_rgx_multi_modmap = re.compile(
    r"^\(DD\) MULTI_MODMAP: (?:Key\.)?(\S+) => (?:Key\.)?(\S+)"
    r" / (?:Key\.)?(\S+)(?: \((\S+) mod\))? \[(.*)\]\s*$"
)

# (DD) Resolving LEFT_ALT as RIGHT_CTRL (R_CONTROL mod) due to GRAVE press
_rgx_resolving = re.compile(
    r"^\(DD\) Resolving (?:Key\.)?(\S+) as (?:Key\.)?(\S+)"
    r"(?: \((\S+) mod\))? due to (?:Key\.)?(\S+) press\s*$"
)

# (DD) on_key RIGHT_CTRL (R_CONTROL mod) release
# (DD) on_key CAPSLOCK press
_rgx_on_key = re.compile(
    r"^\(DD\) on_key (?:Key\.)?(\S+)(?: \((\S+) mod\))? (press|release|repeat)\s*$"
)

# (DD) KBTYPE: 'Windows' | (CACHED) Default type for dev: 'Telink Wireless Receiver'
# Middle portion varies (cached vs. fresh detection), so match loosely.
_rgx_kbtype = re.compile(
    r"^\(DD\) KBTYPE: '([^']+)'.*dev: '(.*)'\s*$"
)


# End of file #
