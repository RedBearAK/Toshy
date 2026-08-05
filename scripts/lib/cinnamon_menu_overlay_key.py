#!/usr/bin/env python3
"""
scripts/lib/cinnamon_menu_overlay_key.py

Setup helper: rebind the Cinnamon menu applet's 'overlay-key' primary
binding from the default Super_L to <Primary>Esc (Ctrl+Esc), leaving the
secondary (Super_R) alone, so Toshy's Cmd+Space -> Ctrl+Esc launcher
remap works without prompting the user to fix it by hand.

The overlay-key setting is NOT in a gsettings schema; it lives in the
menu applet's per-instance Spices JSON:
    ~/.config/cinnamon/spices/menu@cinnamon.org/<instance-id>.json
Each key is an object; 'value' holds the live setting. Cinnamon's
AppletSettings monitors this file, so a correct write is picked up live.

Value grammar (schema type 'keybinding', default 'Super_L::Super_R'):
'::' separates alternate bindings. We replace only the FIRST alternate,
preserving any user-set secondary.

This does a read-modify-write with an atomic replace (write temp in the
same directory, then os.replace) to avoid corrupting the file if
Cinnamon writes concurrently. Idempotent: a no-op if already set.
"""
__version__ = '20260804'

import os
import json
import tempfile


TARGET_PRIMARY_BINDING = '<Primary>Escape'
DEFAULT_PRIMARY_BINDING = 'Super_L'


def _candidate_dirs() -> 'list[str]':
    """Current Spices settings dir first, legacy configs dir as fallback
    (matches Cinnamon's xlet-settings.py: settings_dir vs
    old_settings_dir). Most systems have only the current one."""
    home_dir = os.path.expanduser('~')
    config_home = os.environ.get('XDG_CONFIG_HOME', '')
    if not config_home:
        config_home = os.path.join(home_dir, '.config')
    return [
        os.path.join(config_home, 'cinnamon', 'spices', 'menu@cinnamon.org'),
        os.path.join(home_dir, '.cinnamon', 'configs', 'menu@cinnamon.org'),
    ]


def _instance_files() -> 'list[str]':
    for spices_dir in _candidate_dirs():
        if not os.path.isdir(spices_dir):
            continue
        json_files_lst = [os.path.join(spices_dir, name)
                            for name in sorted(os.listdir(spices_dir))
                            if name.endswith('.json')]
        if json_files_lst:
            return json_files_lst
    return []


def _write_atomic(file_path: str, data_dct: dict) -> bool:
    """Atomic replace of the instance JSON. Returns True on success."""
    dir_name = os.path.dirname(file_path)
    tmp_fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix='.tmp')
    try:
        with os.fdopen(tmp_fd, 'w', encoding='utf-8') as tmp_obj:
            json.dump(data_dct, tmp_obj, indent=4)
            tmp_obj.write('\n')
        os.replace(tmp_path, file_path)
        return True
    except OSError:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        return False


def _replace_primary(current_value: str, new_primary: str) -> str:
    """Replace only the first '::'-separated alternate; keep the rest."""
    alternates_lst = current_value.split('::')
    alternates_lst[0] = new_primary
    return '::'.join(alternates_lst)


def _rebind_primary(new_primary: str, only_if_primary=None) -> bool:
    """Set the overlay-key primary alternate to new_primary in every menu
    instance, preserving any secondary. If only_if_primary is given, an
    instance is changed only when its current primary equals that string
    (used by restore to avoid clobbering a user's own later choice).
    Returns True if any file was changed."""
    changed_any = False

    for file_path in _instance_files():
        try:
            with open(file_path, 'r', encoding='utf-8') as file_obj:
                data_dct = json.load(file_obj)
        except (OSError, ValueError):
            continue

        key_obj = data_dct.get('overlay-key')
        if not isinstance(key_obj, dict) or 'value' not in key_obj:
            continue

        current_value = str(key_obj['value'])
        current_primary = current_value.split('::')[0]

        if only_if_primary is not None and current_primary != only_if_primary:
            continue

        new_value = _replace_primary(current_value, new_primary)
        if new_value == current_value:
            continue        # already set; idempotent no-op

        key_obj['value'] = new_value
        if _write_atomic(file_path, data_dct):
            changed_any = True

    return changed_any


def set_menu_overlay_key_primary() -> bool:
    """Rebind the overlay-key primary to Ctrl+Escape in every menu applet
    instance, preserving any secondary. Returns True if any file changed."""
    return _rebind_primary(TARGET_PRIMARY_BINDING)


def restore_menu_overlay_key_primary() -> bool:
    """Undo set_menu_overlay_key_primary(): restore the primary to
    Super_L, but ONLY where it currently equals our Ctrl+Escape binding,
    so a user's own later choice is left untouched. Preserves any
    secondary. Returns True if any file changed."""
    return _rebind_primary(DEFAULT_PRIMARY_BINDING,
                            only_if_primary=TARGET_PRIMARY_BINDING)


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--restore':
        if restore_menu_overlay_key_primary():
            print(f"Cinnamon menu overlay-key primary restored to '{DEFAULT_PRIMARY_BINDING}'.")
        else:
            print('No change needed (not our binding, or no menu applet instances found).')
    else:
        if set_menu_overlay_key_primary():
            print(f"Cinnamon menu overlay-key primary set to '{TARGET_PRIMARY_BINDING}'.")
        else:
            print('No change needed (already set, or no menu applet instances found).')

# End of file #
