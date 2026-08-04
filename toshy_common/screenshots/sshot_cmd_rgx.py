#!/usr/bin/env python3
"""
toshy_common/screenshots/sshot_cmd_rgx.py

Compiled regex patterns for classifying screenshot tool commands found
in XFCE keyboard shortcut definitions.

Patterns are kept in this dedicated module (imported into the consumer
modules) so that pattern editing never happens inside larger modules.
Generic accelerator-parsing patterns live in
toshy_common/shortcut_detect/sc_det_accel_rgx.py.
"""
__version__ = '20260803'

import re


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
