#!/usr/bin/env python3
"""
toshy_common/shortcut_detect/sc_det_cosmic_rgx.py

Compiled regex patterns for parsing COSMIC shortcut config entries
(RON format), isolated here per project convention.

Entry shapes (cosmic-comp data/keybindings.ron, verified 2026-08):
    (modifiers: [Super], key: "space"): System(InputSourceSwitch),
    (modifiers: [Super]): System(Launcher),
    (modifiers: [Super, Shift], key: "Escape"): System(LogOut),
"""
__version__ = '20260805'

import re


# Captures: 1 = modifier list contents, 2 = key (absent for
# modifier-only bindings), 3 = action text up to the trailing comma.
COSMIC_BINDING_ENTRY_rgx = re.compile(
    r'\(\s*modifiers\s*:\s*\[([^\]]*)\]\s*'
    r'(?:,\s*key\s*:\s*"([^"]*)")?'
    r'[^)]*\)\s*:\s*([^,\n]+)')

# End of file #
