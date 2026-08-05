#!/usr/bin/env python3
"""
toshy_common/screenshots/__init__.py

Detection and mapping of macOS-shape screenshot shortcuts onto native
desktop environment screenshot actions.

Curated public API, re-exported so the config file (and user custom
config snippets) can import everything from the package root:

    from toshy_common.screenshots import setup_screenshot_keymaps
    setup_screenshot_keymaps(globals(), when = lambda ctx: ...)

Storage mechanics, accelerator normalization, the SlotResult model, and
diagnostic rendering live in toshy_common.shortcut_detect; this package
supplies the screenshot domain on top of them.

Internal module layout:
    __main__.py         CLI diagnostic (python3 -m toshy_common.screenshots)
    sshot_cmd_rgx.py      compiled regex patterns (command classification)
    sshot_defaults.py     slot model, static default tables, cmd fallbacks
    sshot_readers.py      per-DE reader wrappers (maps + classification)
    sshot_resolver.py     family dispatch, tiering, resolution logging
    sshot_keymaps.py      keymap builder (injected config-API)
"""
__version__ = '20260803'


from toshy_common.screenshots.sshot_defaults import (
    SLOT_AREA_TO_CLIPBOARD,
    SLOT_AREA_TO_FILE,
    SLOT_FULLSCREEN_TO_CLIPBOARD,
    SLOT_FULLSCREEN_TO_FILE,
    SLOT_INTERACTIVE_UI,
    SLOT_NAMES,
    SLOT_WINDOW_TO_CLIPBOARD,
    SLOT_WINDOW_TO_FILE,
)
from toshy_common.shortcut_detect import (
    STATUS_DISABLED,
    STATUS_RESOLVED,
    STATUS_UNRESOLVED,
)
from toshy_common.screenshots.sshot_keymaps import (
    DEFAULT_INPUT_COMBOS_DCT,
    setup_screenshot_keymaps,
)
from toshy_common.screenshots.sshot_resolver import (
    SlotResult,
    build_keymap_entries,
    clear_custom_outputs,
    resolve_outputs,
    set_custom_output,
)

# End of file #
