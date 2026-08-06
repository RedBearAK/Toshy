#!/usr/bin/env python3
"""
toshy_common/screenshots/sshot_readers.py

Per-desktop-environment readers that extract the currently active native
screenshot shortcuts from each DE's settings storage. Thin domain
wrappers: the storage-format mechanics and accelerator normalization
live in toshy_common.shortcut_detect; this module supplies the
screenshot-specific section names, schema/key maps, command
classification, and KDE clipboard mirroring.

Reader return contract: each reader returns a dict mapping slot name to
(status, combo_or_None, raw_accel_str, note_str). Slots absent from the
returned dict mean "this reader could not determine anything"; the
caller falls through to static defaults for those slots. STATUS_DISABLED
is a *successful* read of an explicitly disabled shortcut and must NOT
fall through to defaults.
"""
__version__ = '20260803'

from toshy_common.logger import error
from toshy_common.screenshots.sshot_cmd_rgx import (
    _rgx_sshooter_clipboard,
    _rgx_sshooter_cmd,
    _rgx_sshooter_fullscreen,
    _rgx_sshooter_region,
    _rgx_sshooter_window,
)
from toshy_common.screenshots.sshot_defaults import (
    SLOT_AREA_TO_CLIPBOARD,
    SLOT_AREA_TO_FILE,
    SLOT_FULLSCREEN_TO_CLIPBOARD,
    SLOT_FULLSCREEN_TO_FILE,
    SLOT_INTERACTIVE_UI,
    SLOT_WINDOW_TO_CLIPBOARD,
    SLOT_WINDOW_TO_FILE,
)
from toshy_common.shortcut_detect import (
    STATUS_RESOLVED,
    normalize_gtk_accel,
    read_gsettings_family,
    read_kde_component,
    read_merged_accel_commands,
)


###################################################################################################
###  KDE READER (Spectacle component in kglobalshortcutsrc)
###################################################################################################

_KDE_SECTION_NAMES_LST = [
    '[org.kde.spectacle.desktop]',
    '[services][org.kde.spectacle.desktop]',
]

# Spectacle action objectNames -> slot names. Verified stable across
# Spectacle v21.12.3 through master (see sshot_defaults.py provenance).
# WindowUnderCursorScreenShot (interactive "Select Window" picker) feeds
# the window slot, deliberately NOT ActiveWindowScreenShot (immediate
# capture of the focused window); see sshot_defaults.py for rationale.
_KDE_ACTION_SLOT_DCT = {
    '_launch':                      SLOT_INTERACTIVE_UI,
    'FullScreenScreenShot':         SLOT_FULLSCREEN_TO_FILE,
    'RectangularRegionScreenShot':  SLOT_AREA_TO_FILE,
    'WindowUnderCursorScreenShot':  SLOT_WINDOW_TO_FILE,
}

# Clipboard slots mirror their file siblings on KDE; Spectacle's capture
# destination is governed by Spectacle's own settings, not by a separate
# shortcut. The capture action itself is identical.
_KDE_CLIPBOARD_MIRROR_DCT = {
    SLOT_FULLSCREEN_TO_CLIPBOARD:   SLOT_FULLSCREEN_TO_FILE,
    SLOT_AREA_TO_CLIPBOARD:         SLOT_AREA_TO_FILE,
    SLOT_WINDOW_TO_CLIPBOARD:       SLOT_WINDOW_TO_FILE,
}

_KDE_MIRROR_NOTE = 'mirrors file slot; capture destination governed by Spectacle settings'


def read_kde() -> dict:
    """Read Spectacle shortcuts, mirroring clipboard slots from file slots."""
    results_dct = read_kde_component(_KDE_SECTION_NAMES_LST, _KDE_ACTION_SLOT_DCT)

    for clip_slot, file_slot in _KDE_CLIPBOARD_MIRROR_DCT.items():
        if file_slot not in results_dct:
            continue
        status, combo_str, raw_accel, _ = results_dct[file_slot]
        results_dct[clip_slot] = (status, combo_str, raw_accel, _KDE_MIRROR_NOTE)

    return results_dct


###################################################################################################
###  GSETTINGS READERS (GNOME 42+, GNOME legacy, Budgie, Cinnamon, MATE)
###################################################################################################

# Slot -> gsettings key maps per schema family. Multiple slots may map to
# the same key (GNOME 42+ area capture goes through the screenshot UI, and
# every GNOME 42+ capture lands in both file and clipboard).
_GNOME_42_SCHEMA = 'org.gnome.shell.keybindings'
_GNOME_42_SLOT_KEY_DCT = {
    SLOT_INTERACTIVE_UI:            'show-screenshot-ui',
    SLOT_FULLSCREEN_TO_FILE:        'screenshot',
    SLOT_WINDOW_TO_FILE:            'screenshot-window',
    SLOT_AREA_TO_FILE:              'show-screenshot-ui',
    SLOT_FULLSCREEN_TO_CLIPBOARD:   'screenshot',
    SLOT_WINDOW_TO_CLIPBOARD:       'screenshot-window',
    SLOT_AREA_TO_CLIPBOARD:         'show-screenshot-ui',
}
_GNOME_42_NOTES_DCT = {
    SLOT_AREA_TO_FILE:              'screenshot UI opens in area-selection mode',
    SLOT_AREA_TO_CLIPBOARD:         'screenshot UI opens in area-selection mode',
    SLOT_FULLSCREEN_TO_CLIPBOARD:   'GNOME 42+ saves file and copies to clipboard',
    SLOT_WINDOW_TO_CLIPBOARD:       'GNOME 42+ saves file and copies to clipboard',
}

_GNOME_LEGACY_SCHEMA = 'org.gnome.settings-daemon.plugins.media-keys'
_GNOME_LEGACY_SLOT_KEY_DCT = {
    SLOT_FULLSCREEN_TO_FILE:        'screenshot',
    SLOT_WINDOW_TO_FILE:            'window-screenshot',
    SLOT_AREA_TO_FILE:              'area-screenshot',
    SLOT_FULLSCREEN_TO_CLIPBOARD:   'screenshot-clip',
    SLOT_WINDOW_TO_CLIPBOARD:       'window-screenshot-clip',
    SLOT_AREA_TO_CLIPBOARD:         'area-screenshot-clip',
}

_CINNAMON_SCHEMA = 'org.cinnamon.desktop.keybindings.media-keys'
_CINNAMON_SLOT_KEY_DCT = dict(_GNOME_LEGACY_SLOT_KEY_DCT)

_MATE_SCHEMA = 'org.mate.Marco.global-keybindings'
_MATE_SLOT_KEY_DCT = {
    SLOT_FULLSCREEN_TO_FILE:        'run-command-screenshot',
    SLOT_WINDOW_TO_FILE:            'run-command-window-screenshot',
    SLOT_AREA_TO_FILE:              'run-command-area-screenshot',
}


def read_gnome(de_maj_ver: 'int | None' = None) -> dict:
    """Read GNOME screenshot shortcuts, trying the version-appropriate
    schema first and the other as fallback."""
    if de_maj_ver is not None and de_maj_ver < 42:
        family_order_lst = [
            (_GNOME_LEGACY_SCHEMA, _GNOME_LEGACY_SLOT_KEY_DCT, None),
            (_GNOME_42_SCHEMA, _GNOME_42_SLOT_KEY_DCT, _GNOME_42_NOTES_DCT),
        ]
    else:
        family_order_lst = [
            (_GNOME_42_SCHEMA, _GNOME_42_SLOT_KEY_DCT, _GNOME_42_NOTES_DCT),
            (_GNOME_LEGACY_SCHEMA, _GNOME_LEGACY_SLOT_KEY_DCT, None),
        ]

    for schema_str, slot_key_dct, notes_dct in family_order_lst:
        results_dct = read_gsettings_family(schema_str, slot_key_dct, notes_dct)
        if results_dct:
            return results_dct
    return {}


def read_budgie() -> dict:
    """Budgie uses gnome-settings-daemon media-keys (legacy convention)."""
    return read_gsettings_family(_GNOME_LEGACY_SCHEMA, _GNOME_LEGACY_SLOT_KEY_DCT)


def read_cinnamon() -> dict:
    return read_gsettings_family(_CINNAMON_SCHEMA, _CINNAMON_SLOT_KEY_DCT)


def read_mate() -> dict:
    return read_gsettings_family(_MATE_SCHEMA, _MATE_SLOT_KEY_DCT)


###################################################################################################
###  XFCE READER (screenshooter commands in xfconf shortcut XML)
###################################################################################################

def _classify_sshooter_command(command_str: str) -> 'str | None':
    """Map an xfce4-screenshooter command line to a slot name."""
    if not _rgx_sshooter_cmd.search(command_str):
        return None

    to_clipboard = bool(_rgx_sshooter_clipboard.search(command_str))

    if _rgx_sshooter_fullscreen.search(command_str):
        return SLOT_FULLSCREEN_TO_CLIPBOARD if to_clipboard else SLOT_FULLSCREEN_TO_FILE
    if _rgx_sshooter_window.search(command_str):
        return SLOT_WINDOW_TO_CLIPBOARD if to_clipboard else SLOT_WINDOW_TO_FILE
    if _rgx_sshooter_region.search(command_str):
        return SLOT_AREA_TO_CLIPBOARD if to_clipboard else SLOT_AREA_TO_FILE

    # Bare invocation opens the interactive chooser dialog.
    return SLOT_INTERACTIVE_UI


def read_xfce() -> dict:
    """Read XFCE screenshot shortcuts from merged xfconf XML files."""
    merged_accel_cmd_dct = read_merged_accel_commands()
    if not merged_accel_cmd_dct:
        return {}

    results_dct = {}
    for accel_str, command_str in merged_accel_cmd_dct.items():
        slot_name = _classify_sshooter_command(command_str)
        if slot_name is None:
            continue
        combo_str = normalize_gtk_accel(accel_str)
        if combo_str is None:
            error(f'SSHOT: Could not parse XFCE shortcut accelerator '
                    f'{accel_str!r} for command {command_str!r}', ctx='DT')
            continue
        # Later entries (user file, custom subtree) overwrite earlier ones.
        results_dct[slot_name] = (STATUS_RESOLVED, combo_str, accel_str, '')

    return results_dct

# COSMIC: sole screenshot action System(Screenshot) in cosmic-config
# layered RON files; Print by default. Reader mechanics shared with the
# spotlight package (sc_det_cosmic).
from toshy_common.shortcut_detect.sc_det_cosmic import read_cosmic_shortcuts

_COSMIC_ACTION_SLOT_DCT = {
    'Screenshot':   SLOT_INTERACTIVE_UI,
}


def read_cosmic() -> dict:
    return read_cosmic_shortcuts(_COSMIC_ACTION_SLOT_DCT)


# End of file #
