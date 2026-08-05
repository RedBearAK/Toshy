#!/usr/bin/env python3
"""
toshy_common/shortcut_detect/sc_det_accel_rgx.py

Compiled regex patterns for parsing keyboard shortcut accelerator strings
from desktop environment settings storage.

Patterns are kept in this dedicated module (imported into the consumer
modules) so that pattern editing never happens inside larger modules.
"""
__version__ = '20260803'

import re


# Matches one GTK-style modifier token, e.g. '<Shift>' or '<Primary>'.
# Used with .findall() to extract all modifier tokens from an accelerator
# string like '<Control><Shift>Print'.
_rgx_gtk_mod_token          = re.compile(r'<([A-Za-z0-9]+)>')

# Validates a single key name token after modifier extraction.
# Multi-word key names like 'Volume Down' (seen in kglobalshortcutsrc)
# intentionally fail this check and cause the entry to be unresolved.
_rgx_key_token_valid        = re.compile(r'^[A-Za-z0-9_]+$')

# Validates a fully normalized xwaykeyz-style combo string,
# e.g. 'Shift-C-Print' or 'Print'. Used to sanity-check both parser
# output and caller-supplied combo strings.
_rgx_combo_valid            = re.compile(r'^[A-Za-z0-9_]+(?:-[A-Za-z0-9_]+)*$')

# End of file #
