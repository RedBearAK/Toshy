#!/usr/bin/env python3
"""
toshy_common/spotlight_input/__init__.py

Native-shortcut detection and keymap building for the launcher
("Spotlight") and keyboard input source switching remaps, including the
user-swappable arrangement (swap_spotlight_and_input preference).

Built on toshy_common.shortcut_detect. Historical provenance for the
swap: before Mac OS X 10.4 Tiger (2005), Cmd+Space was the input source
switch; Tiger upgraders with the Input Menu enabled kept it, with
Spotlight remapped to Ctrl+Space.

Internal module layout:
    __main__.py          CLI diagnostic (toshy-spotlight-check)
    spli_defaults.py     slot model, per-DE static default tables
    spli_readers.py      per-DE reader wrappers (KDE rc, gsettings, Spices)
    spli_resolver.py     tiering + resolution logging
    spli_keymaps.py      dual-arrangement keymap builder
"""
__version__ = '20260804'

from toshy_common.spotlight_input.spli_defaults import (
    SLOT_INPUT_SWITCH_LAST,
    SLOT_INPUT_SWITCH_NEXT,
    SLOT_INPUT_SWITCH_PREV,
    SLOT_LAUNCHER_UI,
    SLOT_NAMES,
)
from toshy_common.spotlight_input.spli_keymaps import setup_spotlight_input_keymaps
from toshy_common.spotlight_input.spli_resolver import resolve_outputs

# End of file #
