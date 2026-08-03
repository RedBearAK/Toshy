#!/usr/bin/env python3
"""
toshy_common/screenshots/sshot_readers.py

Per-desktop-environment readers that extract the currently active native
screenshot shortcuts from each DE's settings storage, plus the accelerator
normalization layer that converts DE-native accelerator strings into
xwaykeyz output combo strings.

Reader return contract: each reader returns a dict mapping slot name to a
4-tuple of (status, combo_or_None, raw_accel_str, note_str). Slots absent
from the returned dict mean "this reader could not determine anything";
the caller (sshot_resolver.py) falls through to static defaults for
those slots. STATUS_DISABLED is a *successful* read of an explicitly
disabled shortcut and must NOT fall through to defaults.

Storage formats handled:
  KDE:    ~/.config/kglobalshortcutsrc (INI-like, current,default,desc)
  GNOME/Cinnamon/MATE/Budgie: gsettings (dconf binary db via subprocess)
  XFCE:   xfconf XML (user file overriding XDG_CONFIG_DIRS system files)
"""
__version__ = '20260802'


import os
import ast
import subprocess

from xml.etree import ElementTree

from toshy_common.screenshots.sshot_accel_rgx import (
    _rgx_gtk_mod_token,
    _rgx_key_token_valid,
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
    STATUS_DISABLED,
    STATUS_RESOLVED,
)


###################################################################################################
###  ACCELERATOR NORMALIZATION
###################################################################################################

# Canonical modifier emission order for output combo strings.
_MOD_ORDER_LST = ['C', 'Alt', 'Shift', 'Super']

# KDE (Qt-style) modifier token names -> xwaykeyz modifier names.
_KDE_MOD_XLAT_DCT = {
    'meta':     'Super',
    'ctrl':     'C',
    'control':  'C',
    'shift':    'Shift',
    'alt':      'Alt',
}

# GTK-style modifier token names -> xwaykeyz modifier names.
# '<Primary>' is GTK's platform-abstract name for Ctrl on Linux.
# '<Meta>' is mapped to Super, which is where Meta lands on typical
# PC layouts under GNOME-family DEs.
_GTK_MOD_XLAT_DCT = {
    'primary':  'C',
    'control':  'C',
    'ctrl':     'C',
    'ctl':      'C',
    'shift':    'Shift',
    'alt':      'Alt',
    'mod1':     'Alt',
    'meta':     'Super',
    'super':    'Super',
    'win':      'Super',
    'mod4':     'Super',
}

# Minor key name translations where DE naming differs from xwaykeyz.
_KEY_NAME_XLAT_DCT = {
    'Return':   'Enter',
    'Escape':   'Esc',
}


def _canonical_combo(mods_lst: 'list[str]', key_name: str) -> str:
    """Assemble a normalized combo string with deterministic modifier order."""
    ordered_mods_lst = [mod for mod in _MOD_ORDER_LST if mod in mods_lst]
    return '-'.join(ordered_mods_lst + [key_name])


def normalize_kde_accel(accel_str: str) -> 'str | None':
    """Convert a KDE accelerator like 'Meta+Shift+Print' to 'Shift-Super-Print'.

    Returns None if the accelerator cannot be represented (unknown modifier,
    multi-word key name, empty input)."""
    if not accel_str:
        return None

    parts_lst = [part.strip() for part in accel_str.split('+')]
    if any(not part for part in parts_lst):
        return None

    key_name = parts_lst[-1]
    mod_parts_lst = parts_lst[:-1]

    mods_lst = []
    for mod_part in mod_parts_lst:
        xlat_mod = _KDE_MOD_XLAT_DCT.get(mod_part.lower())
        if xlat_mod is None:
            return None
        if xlat_mod not in mods_lst:
            mods_lst.append(xlat_mod)

    # A trailing modifier name means a modifier-only shortcut; emit the
    # modifier itself as the "key" (xwaykeyz can emit a modifier tap).
    key_as_mod = _KDE_MOD_XLAT_DCT.get(key_name.lower())
    if key_as_mod is not None:
        key_name = key_as_mod
    else:
        key_name = _KEY_NAME_XLAT_DCT.get(key_name, key_name)
        if not _rgx_key_token_valid.match(key_name):
            return None

    return _canonical_combo(mods_lst, key_name)


def normalize_gtk_accel(accel_str: str) -> 'str | None':
    """Convert a GTK accelerator like '<Control><Shift>Print' to 'C-Shift-Print'.

    Returns None if the accelerator cannot be represented."""
    if not accel_str:
        return None

    mod_tokens_lst = _rgx_gtk_mod_token.findall(accel_str)
    key_name = _rgx_gtk_mod_token.sub('', accel_str).strip()

    mods_lst = []
    for mod_token in mod_tokens_lst:
        xlat_mod = _GTK_MOD_XLAT_DCT.get(mod_token.lower())
        if xlat_mod is None:
            return None
        if xlat_mod not in mods_lst:
            mods_lst.append(xlat_mod)

    key_name = _KEY_NAME_XLAT_DCT.get(key_name, key_name)
    if not _rgx_key_token_valid.match(key_name):
        return None

    return _canonical_combo(mods_lst, key_name)


###################################################################################################
###  KDE READER (kglobalshortcutsrc file parse)
###################################################################################################

_KDE_SECTION_MAIN           = '[org.kde.spectacle.desktop]'
_KDE_SECTION_SERVICES       = '[services][org.kde.spectacle.desktop]'

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


def _kde_config_file_path() -> str:
    config_home = os.environ.get('XDG_CONFIG_HOME', '')
    if not config_home:
        config_home = os.path.join(os.path.expanduser('~'), '.config')
    return os.path.join(config_home, 'kglobalshortcutsrc')


def parse_kde_shortcut_value(value_str: str) -> 'tuple[str, str | None]':
    """Parse a kglobalshortcutsrc value into (status, raw_accel_or_None).

    Full form is 'current,default,description'. An empty current field
    means "use default". The literal 'none' means explicitly disabled.
    Alternates within a field are separated by a literal backslash-t
    escape; the first alternate wins. Plasma 6 '[services]' entries use a
    bare single-field form (just the accelerator)."""
    if not value_str:
        return (STATUS_DISABLED, None)

    if ',' not in value_str:
        # Single-field form (Plasma 6 services-style entry).
        current_field = value_str
    else:
        fields_lst = value_str.split(',', 2)
        current_field = fields_lst[0]
        if not current_field and len(fields_lst) > 1:
            current_field = fields_lst[1]

    # First alternate wins. The file stores a literal backslash + 't'.
    current_field = current_field.split('\\t')[0].strip()

    if not current_field or current_field.lower() == 'none':
        return (STATUS_DISABLED, None)

    return (STATUS_RESOLVED, current_field)


def read_kde() -> dict:
    """Read Spectacle shortcuts from kglobalshortcutsrc.

    Returns {} when the file or the Spectacle section is absent (the
    common case on stock installs, where kglobalaccel never persists
    untouched components; caller falls through to the defaults table)."""
    file_path = _kde_config_file_path()
    if not os.path.isfile(file_path):
        return {}

    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as file_obj:
            lines_lst = file_obj.read().splitlines()
    except OSError:
        return {}

    results_dct = {}
    in_section = False
    for line in lines_lst:
        stripped_line = line.strip()
        if stripped_line.startswith('['):
            in_section = stripped_line in (_KDE_SECTION_MAIN, _KDE_SECTION_SERVICES)
            continue
        if not in_section:
            continue
        if '=' not in stripped_line:
            continue

        action_name, _, value_str = stripped_line.partition('=')
        action_name = action_name.strip()
        if action_name == '_k_friendly_name':
            continue

        slot_name = _KDE_ACTION_SLOT_DCT.get(action_name)
        if slot_name is None:
            continue

        status, raw_accel = parse_kde_shortcut_value(value_str.strip())
        if status == STATUS_DISABLED:
            results_dct[slot_name] = (STATUS_DISABLED, None, value_str.strip(), '')
            continue

        combo_str = normalize_kde_accel(raw_accel)
        if combo_str is None:
            # Unparseable accelerator: leave slot out so caller can fall
            # through to defaults (loud logging happens in the caller).
            continue
        results_dct[slot_name] = (STATUS_RESOLVED, combo_str, raw_accel, '')

    for clip_slot, file_slot in _KDE_CLIPBOARD_MIRROR_DCT.items():
        if file_slot not in results_dct:
            continue
        status, combo_str, raw_accel, _ = results_dct[file_slot]
        results_dct[clip_slot] = (status, combo_str, raw_accel, _KDE_MIRROR_NOTE)

    return results_dct


###################################################################################################
###  GSETTINGS READERS (GNOME 42+, GNOME legacy, Budgie, Cinnamon, MATE)
###################################################################################################

_GSETTINGS_TIMEOUT_SEC = 5

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


def _gsettings_get(schema_str: str, key_str: str) -> 'str | None':
    """Run 'gsettings get' and return raw output, or None on any failure."""
    try:
        proc = subprocess.run(
            ['gsettings', 'get', schema_str, key_str],
            capture_output=True, text=True, timeout=_GSETTINGS_TIMEOUT_SEC
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    output_str = proc.stdout.strip()
    if not output_str:
        return None
    return output_str


def _parse_gvariant_accel_value(text_str: str) -> 'tuple[str, str | None]':
    """Parse a gsettings value into (status, raw_accel_or_None).

    Handles list-typed values like "['<Shift>Print']", empty lists
    (including the '@as []' spelling), plain string values like
    "'<Alt>Print'", and the Marco 'disabled' sentinel."""
    if text_str.startswith('@as'):
        text_str = text_str[len('@as'):].strip()

    try:
        parsed_value = ast.literal_eval(text_str)
    except (ValueError, SyntaxError):
        return (STATUS_DISABLED, None)

    if isinstance(parsed_value, (list, tuple)):
        parsed_value = parsed_value[0] if parsed_value else ''

    if not isinstance(parsed_value, str):
        return (STATUS_DISABLED, None)

    parsed_value = parsed_value.strip()
    if not parsed_value or parsed_value.lower() == 'disabled':
        return (STATUS_DISABLED, None)

    return (STATUS_RESOLVED, parsed_value)


def _read_gsettings_family(schema_str: str, slot_key_dct: dict, notes_dct: 'dict | None' = None
                            ) -> dict:
    """Read one gsettings schema family into the reader return contract.

    Returns {} if the schema is entirely unreadable (probe on the first
    key fails), so the caller can try another family or fall through."""
    notes_dct = notes_dct or {}
    results_dct = {}
    probed = False

    for slot_name, key_str in slot_key_dct.items():
        raw_output = _gsettings_get(schema_str, key_str)
        if raw_output is None:
            if not probed:
                # Schema/key missing on first probe: family unavailable.
                return {}
            continue
        probed = True

        status, raw_accel = _parse_gvariant_accel_value(raw_output)
        if status == STATUS_DISABLED:
            results_dct[slot_name] = (STATUS_DISABLED, None, raw_output, notes_dct.get(slot_name, ''))
            continue

        combo_str = normalize_gtk_accel(raw_accel)
        if combo_str is None:
            continue
        results_dct[slot_name] = (STATUS_RESOLVED, combo_str, raw_accel, notes_dct.get(slot_name, ''))

    return results_dct


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
        results_dct = _read_gsettings_family(schema_str, slot_key_dct, notes_dct)
        if results_dct:
            return results_dct
    return {}


def read_budgie() -> dict:
    """Budgie uses gnome-settings-daemon media-keys (legacy convention)."""
    return _read_gsettings_family(_GNOME_LEGACY_SCHEMA, _GNOME_LEGACY_SLOT_KEY_DCT)


def read_cinnamon() -> dict:
    return _read_gsettings_family(_CINNAMON_SCHEMA, _CINNAMON_SLOT_KEY_DCT)


def read_mate() -> dict:
    return _read_gsettings_family(_MATE_SCHEMA, _MATE_SLOT_KEY_DCT)


###################################################################################################
###  XFCE READER (xfconf XML file parse)
###################################################################################################

_XFCE_SHORTCUTS_REL_PATH = os.path.join(
    'xfce4', 'xfconf', 'xfce-perchannel-xml', 'xfce4-keyboard-shortcuts.xml')


def _xfce_shortcut_file_paths() -> 'list[str]':
    """System files first (XDG_CONFIG_DIRS order reversed so higher
    priority dirs land later), user file last, so later wins on merge."""
    paths_lst = []

    config_dirs_str = os.environ.get('XDG_CONFIG_DIRS', '') or '/etc/xdg'
    system_dirs_lst = [dir_str for dir_str in config_dirs_str.split(':') if dir_str]
    for system_dir in reversed(system_dirs_lst):
        paths_lst.append(os.path.join(system_dir, _XFCE_SHORTCUTS_REL_PATH))

    config_home = os.environ.get('XDG_CONFIG_HOME', '')
    if not config_home:
        config_home = os.path.join(os.path.expanduser('~'), '.config')
    paths_lst.append(os.path.join(config_home, _XFCE_SHORTCUTS_REL_PATH))

    return paths_lst


def _xfce_accel_commands_from_file(file_path: str) -> dict:
    """Extract {accel_str: command_str} from one xfconf shortcuts XML file.

    Walks the 'commands' property's 'default' and 'custom' subtrees in that
    order, so custom entries override default entries within a file."""
    try:
        tree = ElementTree.parse(file_path)
    except (OSError, ElementTree.ParseError):
        return {}

    accel_cmd_dct = {}
    root = tree.getroot()
    for commands_prop in root.iter('property'):
        if commands_prop.get('name') != 'commands':
            continue
        for subtree_name in ('default', 'custom'):
            for subtree_prop in commands_prop:
                if subtree_prop.get('name') != subtree_name:
                    continue
                for entry_prop in subtree_prop:
                    if entry_prop.get('type') != 'string':
                        continue
                    accel_str = entry_prop.get('name', '')
                    command_str = entry_prop.get('value', '')
                    if not accel_str or not command_str:
                        continue
                    accel_cmd_dct[accel_str] = command_str
    return accel_cmd_dct


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
    merged_accel_cmd_dct = {}
    for file_path in _xfce_shortcut_file_paths():
        if not os.path.isfile(file_path):
            continue
        merged_accel_cmd_dct.update(_xfce_accel_commands_from_file(file_path))

    if not merged_accel_cmd_dct:
        return {}

    results_dct = {}
    for accel_str, command_str in merged_accel_cmd_dct.items():
        slot_name = _classify_sshooter_command(command_str)
        if slot_name is None:
            continue
        combo_str = normalize_gtk_accel(accel_str)
        if combo_str is None:
            continue
        # Later entries (user file, custom subtree) overwrite earlier ones.
        results_dct[slot_name] = (STATUS_RESOLVED, combo_str, accel_str, '')

    return results_dct

# End of file #
