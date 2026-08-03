#!/usr/bin/env python3
"""
toshy_common/screenshots/sshot_accel_rgx.py

Compiled regex patterns for parsing keyboard shortcut accelerator strings
from desktop environment settings storage, and for classifying screenshot
tool commands found in XFCE keyboard shortcut definitions.

Patterns are kept in this dedicated module (imported into the consumer
modules) so that pattern editing never happens inside larger modules.
"""
__version__ = '20260801'


import re


# Matches one GTK-style modifier token, e.g. '<Shift>' or '<Primary>'.
# Used with .findall() to extract all modifier tokens from an accelerator
# string like '<Control><Shift>Print'.
_rgx_gtk_mod_token          = re.compile(r'<([A-Za-z0-9]+)>')

# Validates a single key name token after modifier extraction.
# Multi-word key names like 'Volume Down' (seen in kglobalshortcutsrc)
# intentionally fail this check and cause the slot to be unresolved.
_rgx_key_token_valid        = re.compile(r'^[A-Za-z0-9_]+$')

# Validates a fully normalized xwaykeyz-style combo string,
# e.g. 'C-Shift-Print' or 'Print'. Used to sanity-check both parser
# output and user-supplied custom output combos.
_rgx_combo_valid            = re.compile(r'^[A-Za-z0-9_]+(?:-[A-Za-z0-9_]+)*$')

# Detects an xfce4-screenshooter invocation in an XFCE shortcut command
# string, whether bare or with a leading path.
_rgx_sshooter_cmd           = re.compile(r'(?:^|[/\s])xfce4-screenshooter(?:\s|$)')

# Flag classification for xfce4-screenshooter commands. Short and long
# option spellings verified against xfce4-screenshooter src/main.c
# GOptionEntry table (xfce-mirror/xfce4-screenshooter, master, 2026-08):
#   -f / --fullscreen    -w / --window    -r / --region    -c / --clipboard
_rgx_sshooter_fullscreen    = re.compile(r'(?:^|\s)(?:-f|--fullscreen)(?:\s|$)')
_rgx_sshooter_window        = re.compile(r'(?:^|\s)(?:-w|--window)(?:\s|$)')
_rgx_sshooter_region        = re.compile(r'(?:^|\s)(?:-r|--region)(?:\s|$)')
_rgx_sshooter_clipboard     = re.compile(r'(?:^|\s)(?:-c|--clipboard)(?:\s|$)')

# End of file #
