#!/usr/bin/env python3
"""
toshy_common/screenshots/sshot_defaults.py

Slot model, status constants, and static default tables for the screenshot
shortcut detection system.

The "slots" are named after the exact purpose of each macOS screenshot
shortcut. The values in the static tables are pre-normalized xwaykeyz
output combo strings (what Toshy should EMIT on each desktop environment
to trigger the equivalent native action).

Static tables are the fallback tier used when live settings cannot be
read. Every table carries provenance comments naming the upstream source
file and the version/refs it was verified against, so re-verification is
a single grep against a fresh source tarball rather than archaeology.

macOS shortcut reference (verified against Apple support docs, 2026-08):
    Shift+Cmd+3             fullscreen capture, saved to file
    Shift+Cmd+4             area (drag-select) capture, saved to file
    Shift+Cmd+4, Space      window capture, saved to file
    Shift+Cmd+5             interactive screenshot/recording toolbar
    + Control (any above)   destination becomes clipboard instead of file
"""
__version__ = '20260802'



###################################################################################################
###  SLOT MODEL
###################################################################################################

# Slot name constants. Hierarchical naming keeps related slots together
# in autocomplete, and the names describe the exact original macOS purpose.
SLOT_FULLSCREEN_TO_FILE         = 'fullscreen_to_file'
SLOT_FULLSCREEN_TO_CLIPBOARD    = 'fullscreen_to_clipboard'
SLOT_AREA_TO_FILE               = 'area_to_file'
SLOT_AREA_TO_CLIPBOARD          = 'area_to_clipboard'
SLOT_WINDOW_TO_FILE             = 'window_to_file'
SLOT_WINDOW_TO_CLIPBOARD        = 'window_to_clipboard'
SLOT_INTERACTIVE_UI             = 'interactive_ui'

SLOT_NAMES = (
    SLOT_FULLSCREEN_TO_FILE,
    SLOT_FULLSCREEN_TO_CLIPBOARD,
    SLOT_AREA_TO_FILE,
    SLOT_AREA_TO_CLIPBOARD,
    SLOT_WINDOW_TO_FILE,
    SLOT_WINDOW_TO_CLIPBOARD,
    SLOT_INTERACTIVE_UI,
)

# Per-slot resolution status values.
STATUS_RESOLVED                 = 'resolved'      # combo available for emission
STATUS_DISABLED                 = 'disabled'      # user explicitly disabled native shortcut
STATUS_UNRESOLVED               = 'unresolved'    # no binding known; slot stays unmapped

# Where a resolved combo came from (for logging/diagnostics).
SOURCE_USER_OVERRIDE            = 'user_override'
SOURCE_LIVE_SETTINGS            = 'live_settings'
SOURCE_DEFAULTS_TABLE           = 'defaults_table'
SOURCE_GENERIC_CONVENTION       = 'generic_convention'


###################################################################################################
###  STATIC DEFAULT TABLES (fallback tier when live settings are unreadable)
###################################################################################################

# KDE Plasma / Spectacle
# Source-verified against Spectacle source, KGlobalAccel registration block
# in src/SpectacleCore.cpp and action objectNames in src/ShortcutActions.cpp.
# Identical defaults across v21.12.3, v23.08.5, and master (2026-08):
#   _launch                      = Print              (interactive UI)
#   FullScreenScreenShot         = Shift+Print
#   RectangularRegionScreenShot  = Meta+Shift+Print
#   ActiveWindowScreenShot       = Meta+Print         (immediate, focused win)
#   WindowUnderCursorScreenShot  = Meta+Ctrl+Print    (interactive Select Window)
# Window slots use WindowUnderCursorScreenShot, NOT ActiveWindowScreenShot:
# live testing (2026-08) confirmed ActiveWindow captures the focused window
# immediately, while WindowUnderCursor opens Spectacle's interactive
# "Select Window" picker -- the true twin of macOS's 4-then-Space camera
# mode (any window can be chosen, including background windows).
# Spectacle has no separate clipboard-destination shortcuts; capture
# destination is governed by Spectacle's own settings. Clipboard slots
# therefore mirror the file slots (capture still happens; destination
# follows the user's Spectacle configuration).
KDE_DEFAULTS_DCT = {
    SLOT_INTERACTIVE_UI:            'Print',
    SLOT_FULLSCREEN_TO_FILE:        'Shift-Print',
    SLOT_AREA_TO_FILE:              'Shift-Super-Print',
    SLOT_WINDOW_TO_FILE:            'C-Super-Print',
    SLOT_FULLSCREEN_TO_CLIPBOARD:   'Shift-Print',
    SLOT_AREA_TO_CLIPBOARD:         'Shift-Super-Print',
    SLOT_WINDOW_TO_CLIPBOARD:       'C-Super-Print',
}

# GNOME 42 and later (gnome-shell screenshot UI)
# Source-verified against GNOME/gnome-shell main (2026-08),
# data/org.gnome.shell.gschema.xml.in, schema org.gnome.shell.keybindings:
#   show-screenshot-ui   = ['Print']
#   screenshot           = ['<Shift>Print']
#   screenshot-window    = ['<Alt>Print']
# There is no direct area-capture binding on GNOME 42+; the screenshot UI
# opens in area-selection mode, so the area slots emit the UI binding.
# GNOME 42+ saves to file AND copies to clipboard on every capture, so
# clipboard slots mirror the file slots (behavioral superset upstream).
GNOME_42_DEFAULTS_DCT = {
    SLOT_INTERACTIVE_UI:            'Print',
    SLOT_FULLSCREEN_TO_FILE:        'Shift-Print',
    SLOT_WINDOW_TO_FILE:            'Alt-Print',
    SLOT_AREA_TO_FILE:              'Print',
    SLOT_FULLSCREEN_TO_CLIPBOARD:   'Shift-Print',
    SLOT_WINDOW_TO_CLIPBOARD:       'Alt-Print',
    SLOT_AREA_TO_CLIPBOARD:         'Print',
}

# GNOME 41 and earlier, and Budgie (gnome-settings-daemon media-keys)
# Source-verified against GNOME/gnome-settings-daemon tag 41.0,
# data/org.gnome.settings-daemon.plugins.media-keys.gschema.xml.in:
#   screenshot            = 'Print'
#   window-screenshot     = '<Alt>Print'
#   area-screenshot       = '<Shift>Print'
#   screenshot-clip       = '<Ctrl>Print'
#   window-screenshot-clip = '<Ctrl><Alt>Print'
#   area-screenshot-clip  = '<Ctrl><Shift>Print'
# No interactive UI binding exists in this era.
GNOME_LEGACY_DEFAULTS_DCT = {
    SLOT_FULLSCREEN_TO_FILE:        'Print',
    SLOT_WINDOW_TO_FILE:            'Alt-Print',
    SLOT_AREA_TO_FILE:              'Shift-Print',
    SLOT_FULLSCREEN_TO_CLIPBOARD:   'C-Print',
    SLOT_WINDOW_TO_CLIPBOARD:       'C-Alt-Print',
    SLOT_AREA_TO_CLIPBOARD:         'C-Shift-Print',
}

# Cinnamon
# Source-verified against linuxmint/cinnamon-desktop master (2026-08),
# schemas/org.cinnamon.desktop.keybindings.media-keys.gschema.xml.in.
# Key names and defaults are identical to the GNOME legacy convention
# (with '<Control>' spelling in the schema).
CINNAMON_DEFAULTS_DCT = {
    SLOT_FULLSCREEN_TO_FILE:        'Print',
    SLOT_WINDOW_TO_FILE:            'Alt-Print',
    SLOT_AREA_TO_FILE:              'Shift-Print',
    SLOT_FULLSCREEN_TO_CLIPBOARD:   'C-Print',
    SLOT_WINDOW_TO_CLIPBOARD:       'C-Alt-Print',
    SLOT_AREA_TO_CLIPBOARD:         'C-Shift-Print',
}

# MATE
# Source-verified against mate-desktop/marco master (2026-08),
# src/org.mate.marco.gschema.xml, schema org.mate.Marco.global-keybindings:
#   run-command-screenshot        = 'Print'
#   run-command-window-screenshot = '<Alt>Print'
#   run-command-area-screenshot   = '<Shift>Print'
# Marco uses the special string 'disabled' as its disabled sentinel.
# MATE has no clipboard-destination or interactive UI bindings.
MATE_DEFAULTS_DCT = {
    SLOT_FULLSCREEN_TO_FILE:        'Print',
    SLOT_WINDOW_TO_FILE:            'Alt-Print',
    SLOT_AREA_TO_FILE:              'Shift-Print',
}

# XFCE
# [?] No Print bindings are shipped in xfce4-settings or xfce4-screenshooter
# source (verified 2026-08); the common Print/Alt+Print/Shift+Print trio is
# provided by DISTRO default-settings packages and varies. The live reader
# (user + /etc/xdg xfconf XML) is the reliable path for XFCE; this table is
# a soft guess matching the most widely shipped distro defaults.
XFCE_DEFAULTS_DCT = {
    SLOT_FULLSCREEN_TO_FILE:        'Print',
    SLOT_WINDOW_TO_FILE:            'Alt-Print',
    SLOT_AREA_TO_FILE:              'Shift-Print',
}

# Unknown desktop environments: the gnome-settings-daemon heritage
# convention is the closest thing Linux has to a lingua franca for
# screenshot shortcuts, so it serves as the highest-probability guess.
GENERIC_DEFAULTS_DCT = {
    SLOT_FULLSCREEN_TO_FILE:        'Print',
    SLOT_WINDOW_TO_FILE:            'Alt-Print',
    SLOT_AREA_TO_FILE:              'Shift-Print',
    SLOT_FULLSCREEN_TO_CLIPBOARD:   'C-Print',
    SLOT_WINDOW_TO_CLIPBOARD:       'C-Alt-Print',
    SLOT_AREA_TO_CLIPBOARD:         'C-Shift-Print',
}

# End of file #
