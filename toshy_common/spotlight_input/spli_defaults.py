#!/usr/bin/env python3
"""
toshy_common/spotlight_input/spli_defaults.py

Slot model and static default tables for the Spotlight/input-switching
feature: launcher invocation plus keyboard input source switching, with
semantic slot names so diagnostics show what each native action does.

Defaults are seeded from Toshy's long-standing static per-DE remaps in
the default config (battle-tested provenance), pending per-DE source
verification passes.
"""
__version__ = '20260804'


SLOT_LAUNCHER_UI            = 'launcher_ui'
SLOT_INPUT_SWITCH_LAST      = 'input_switch_last'       # last-used toggle (macOS primary)
SLOT_INPUT_SWITCH_NEXT      = 'input_switch_next'       # cycle forward in list
SLOT_INPUT_SWITCH_PREV      = 'input_switch_prev'       # cycle backward in list

SLOT_NAMES = (
    SLOT_LAUNCHER_UI,
    SLOT_INPUT_SWITCH_LAST,
    SLOT_INPUT_SWITCH_NEXT,
    SLOT_INPUT_SWITCH_PREV,
)

# Launcher output combos per DE (from the static config entries).
# 'Super' means a bare Super tap (Key.LEFT_META in the old entries).
LAUNCHER_DEFAULTS_DCT = {
    'kde':          'Alt-Space',        # krunner drop-down
    # GNOME entries are LAST-RESORT only (gsettings unreadable): the
    # live toggle-overview -> overlay-key chain in spli_readers is
    # authoritative, and a readable-but-unbound system resolves DISABLED
    # with a loud journal error instead of falling through to these.
    'gnome':        'Shift-C-Space',    # Toshy-setup toggle-overview binding
    'cinnamon':     'Super',            # menu applet overlay-key default Super_L
    'mate':         'Alt-Space',        # Mint menu (requires user shortcut match)
    'cosmic':       'Super',
    'pop':          'Super',
    'dde':          'Super',
    'deepin':       'Super',
    'nebide':       'Super',
    'icewm':        'Super',
    'sway':         'Super-d',
    'hyprland':     'Super-d',
    'miracle-wm':   'Super-d',
    'pantheon':     'Alt-F2',
    'enlightenment': 'C-Alt-Space',
}

# GNOME pre-45 launcher differs.
LAUNCHER_GNOME_PRE45 = 'Super-s'

# Input switching defaults per DE: slot -> combo. KDE matches macOS
# (primary = last-used); GNOME-family offers forward/backward cycling.
INPUT_DEFAULTS_DCT = {
    'kde': {
        SLOT_INPUT_SWITCH_LAST:     'Alt-Super-L',
        SLOT_INPUT_SWITCH_NEXT:     'Alt-Super-K',
    },
    'gnome': {
        SLOT_INPUT_SWITCH_NEXT:     'Super-Space',
        SLOT_INPUT_SWITCH_PREV:     'Shift-Super-Space',
    },
}

# End of file #
