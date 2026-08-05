#!/usr/bin/env python3
"""
toshy_common/shortcut_detect/sc_det_spices.py

Reader mechanics for Cinnamon "Spices" (applet/desklet/extension)
instance settings. These live OUTSIDE the usual keybindings storage, in
per-instance JSON files:
    ~/.config/cinnamon/spices/<uuid>/<instance-id>.json
Each key maps to an object whose 'value' member holds the live setting.
Keybinding-typed values may carry '::'-separated alternate bindings.
"""
__version__ = '20260804'

import os
import json


def read_spices_setting(uuid_str: str, key_str: str) -> 'str | None':
    """Return the first found 'value' for key_str among the instance
    JSON files of the given xlet uuid, or None if unavailable."""
    config_home = os.environ.get('XDG_CONFIG_HOME', '')
    if not config_home:
        config_home = os.path.join(os.path.expanduser('~'), '.config')
    spices_dir = os.path.join(config_home, 'cinnamon', 'spices', uuid_str)
    if not os.path.isdir(spices_dir):
        return None

    for entry_name in sorted(os.listdir(spices_dir)):
        if not entry_name.endswith('.json'):
            continue
        try:
            with open(os.path.join(spices_dir, entry_name), 'r',
                        encoding='utf-8', errors='replace') as file_obj:
                data_dct = json.load(file_obj)
        except (OSError, ValueError):
            continue
        key_obj = data_dct.get(key_str)
        if isinstance(key_obj, dict) and 'value' in key_obj:
            return key_obj['value']
    return None

# End of file #
