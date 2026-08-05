#!/usr/bin/env python3
"""
toshy_common/shortcut_detect/sc_det_xfconf.py

Parameterized reader mechanics for XFCE's xfconf keyboard shortcut XML
files. XFCE inverts the usual mapping: keys are accelerator strings and
values are command lines, so this module returns the merged
{accel: command} view (system files under XDG_CONFIG_DIRS first, user
file last, custom subtree over default within each file) and leaves
command classification to domain-specific callers.
"""
__version__ = '20260803'

import os

from xml.etree import ElementTree


_XFCE_SHORTCUTS_REL_PATH = os.path.join(
    'xfce4', 'xfconf', 'xfce-perchannel-xml', 'xfce4-keyboard-shortcuts.xml')


def xfce_shortcut_file_paths() -> 'list[str]':
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


def accel_commands_from_file(file_path: str) -> dict:
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


def read_merged_accel_commands() -> dict:
    """Merge all shortcut files into one {accel: command} dict; later
    files (user config) override earlier (system defaults)."""
    merged_accel_cmd_dct = {}
    for file_path in xfce_shortcut_file_paths():
        if not os.path.isfile(file_path):
            continue
        merged_accel_cmd_dct.update(accel_commands_from_file(file_path))
    return merged_accel_cmd_dct

# End of file #
