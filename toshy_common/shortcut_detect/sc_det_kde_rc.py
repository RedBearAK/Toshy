#!/usr/bin/env python3
"""
toshy_common/shortcut_detect/sc_det_kde_rc.py

Parameterized reader mechanics for KDE's kglobalshortcutsrc file format.

Value grammar handled (verified against real files):
  - full three-field form 'current,default,description'
  - empty current field means "use default"
  - literal 'none' means explicitly disabled
  - alternates within a field separated by a literal backslash-t escape
    (first alternate wins)
  - Plasma 6 '[services]' entries use a bare single-field form

Callers supply the section name(s) and an action-name -> slot-name map;
this module knows the file format, not any feature domain.
"""
__version__ = '20260803'

import os

from toshy_common.logger import error
from toshy_common.shortcut_detect.sc_det_accel import normalize_kde_accel
from toshy_common.shortcut_detect.sc_det_result import (
    STATUS_DISABLED,
    STATUS_RESOLVED,
)


def kde_config_file_path() -> str:
    config_home = os.environ.get('XDG_CONFIG_HOME', '')
    if not config_home:
        config_home = os.path.join(os.path.expanduser('~'), '.config')
    return os.path.join(config_home, 'kglobalshortcutsrc')


def parse_kde_shortcut_value(value_str: str) -> 'tuple[str, str | None]':
    """Parse a kglobalshortcutsrc value into (status, raw_accel_or_None)."""
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


def read_kde_component(section_names, action_slot_dct: dict) -> dict:
    """Read one component's shortcuts from kglobalshortcutsrc.

    section_names: iterable of exact section header strings to accept
    (e.g. '[org.kde.spectacle.desktop]' and its '[services][...]' twin).
    action_slot_dct: config key name -> slot name.

    Returns {slot: (status, combo, raw, note)}. Returns {} when the file
    or all sections are absent -- the common case for untouched
    components, which kglobalaccel never persists; callers fall through
    to their static defaults."""
    file_path = kde_config_file_path()
    if not os.path.isfile(file_path):
        return {}

    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as file_obj:
            lines_lst = file_obj.read().splitlines()
    except OSError:
        return {}

    section_names_set = set(section_names)
    results_dct = {}
    in_section = False
    for line in lines_lst:
        stripped_line = line.strip()
        if stripped_line.startswith('['):
            in_section = stripped_line in section_names_set
            continue
        if not in_section:
            continue
        if '=' not in stripped_line:
            continue

        action_name, _, value_str = stripped_line.partition('=')
        action_name = action_name.strip()
        if action_name == '_k_friendly_name':
            continue

        slot_name = action_slot_dct.get(action_name)
        if slot_name is None:
            continue

        status, raw_accel = parse_kde_shortcut_value(value_str.strip())
        if status == STATUS_DISABLED:
            results_dct[slot_name] = (STATUS_DISABLED, None, value_str.strip(), '')
            continue

        combo_str = normalize_kde_accel(raw_accel)
        if combo_str is None:
            error(f"SC_DET: Could not parse KDE shortcut for '{action_name}': "
                    f'{raw_accel!r} (slot falls back to defaults)', ctx='DT')
            continue
        results_dct[slot_name] = (STATUS_RESOLVED, combo_str, raw_accel, '')

    return results_dct

# End of file #
