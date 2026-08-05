"""
Menu model for the Toshy terminal menu.

toshy_common/terminal_menu/tmenu_model.py

Builds the flat, ordered list of menu items from the shared metadata
modules — toshy_common/preference_items.py for the preference toggles
and choice groups, toshy_common/overlay_context.py for overlay flags —
plus the service/tool action items. This module declares WHAT the menu
contains; it performs no I/O and never touches the terminal, settings
database, or subprocesses. Activation is described by an `action` string
that tmenu_main dispatches, keeping all side effects in one place.

Sections are collapsible. Choice groups that live nested inside the
tray's Preferences submenu (CapsLock Mode) are hoisted to their own
top-level section here, because one level of collapse is enough state
for a terminal menu, and nested expansion would complicate both the
rendering and the mouse hit-testing for no real gain.

Items get stable string ids so the selection can survive a rebuild
(settings monitor refreshes rebuild the visible list every time).
"""

__version__ = '20260804'

import os

from dataclasses import dataclass, field

from toshy_common.overlay_context import (
    OVL_METADATA,
    OVL_PRESET_FULL,
    OVL_PRESET_NONE,
    OVL_PRESET_MINIMAL,
    get_flag_parent,
)
from toshy_common.preference_items import (
    PREF_TOGGLES,
    KBTYPE_GROUP,
    PREF_GROUP_HELP,
    PREF_GROUP_MAIN,
    CAPSLOCK_MODE_GROUP,
    OPTSPEC_LAYOUT_GROUP,
)


KIND_HEADING    = 'heading'
KIND_TOGGLE     = 'toggle'
KIND_RADIO      = 'radio'
KIND_ACTION     = 'action'
KIND_LABEL      = 'label'

SECTION_SERVICES    = 'services'
SECTION_PREFS       = 'prefs'
SECTION_CAPSLOCK    = 'capslock'
SECTION_OPTSPEC     = 'optspec'
SECTION_KBTYPE      = 'kbtype'
SECTION_OVERLAYS    = 'overlays'
SECTION_TOOLS       = 'tools'

# Sections expanded when the menu first opens. Services stay visible
# because service control is the primary job of a fallback tool.
DEFAULT_EXPANDED = {SECTION_SERVICES, SECTION_TOOLS}

_OVERLAY_PRESETS = (
    ('ovl_preset_full',     'Preset: Full (all built-ins on)',  OVL_PRESET_FULL),
    ('ovl_preset_minimal',  'Preset: Minimal (terminal only)',  OVL_PRESET_MINIMAL),
    ('ovl_preset_none',     'Preset: None (everything off)',    OVL_PRESET_NONE),
)


@dataclass
class MenuItem:
    """One visible row of the menu.

    `action` names an operation for tmenu_main's dispatch table; `payload`
    carries its argument (settings attribute, choice value, overlay flag,
    preset mask). `checked` is None for rows with no check/radio state.
    `enabled` False dims the row; `disabled_reason` is shown in the footer
    if the user tries to activate it anyway (explicit over silent).
    """

    item_id:            str
    kind:               str
    text:               str
    section:            str
    action:             str = ''
    payload:            object = None
    checked:            'bool | None' = None
    enabled:            bool = True
    disabled_reason:    str = ''
    indent:             int = 0
    help_title:         str = ''
    help_text:          str = ''
    expanded:           'bool | None' = None    # headings only


@dataclass
class MenuContext:
    """Everything the model needs to decide item states, gathered by
    tmenu_main. Keeps this module free of environment probing."""

    is_systemd:         bool
    barebones_config:   bool
    has_gui_display:    bool
    busy:               bool = False
    expanded:           set = field(default_factory=lambda: set(DEFAULT_EXPANDED))


def build_visible_items(cnfg, menu_ctx: MenuContext):
    """Return the ordered list of currently visible MenuItem rows."""

    items_lst = []
    items_lst.extend(_build_services_section(menu_ctx))

    if not menu_ctx.barebones_config:
        items_lst.extend(_build_prefs_section(cnfg, menu_ctx))
        items_lst.extend(_build_choice_section(
            cnfg, menu_ctx, SECTION_CAPSLOCK, CAPSLOCK_MODE_GROUP))
        items_lst.extend(_build_choice_section(
            cnfg, menu_ctx, SECTION_OPTSPEC, OPTSPEC_LAYOUT_GROUP))
        items_lst.extend(_build_choice_section(
            cnfg, menu_ctx, SECTION_KBTYPE, KBTYPE_GROUP))
        items_lst.extend(_build_overlays_section(cnfg, menu_ctx))

    items_lst.extend(_build_tools_section(menu_ctx))
    return items_lst


def _heading(section, text, menu_ctx, help_title='', help_text=''):
    return MenuItem(
        item_id=f'heading_{section}',
        kind=KIND_HEADING,
        text=text,
        section=section,
        action='toggle_section',
        payload=section,
        help_title=help_title,
        help_text=help_text,
        expanded=(section in menu_ctx.expanded),
    )


def _build_services_section(menu_ctx: MenuContext):
    expanded = SECTION_SERVICES in menu_ctx.expanded
    items_lst = [_heading(
        SECTION_SERVICES, 'Services', menu_ctx,
        help_title='Toshy Services',
        help_text=(
            'Start, restart, or stop the Toshy systemd services, or run '
            'just the config (keymapper) process without systemd.'))]
    if not expanded:
        return items_lst

    systemd_ok      = menu_ctx.is_systemd
    systemd_reason  = '' if systemd_ok else 'Service controls need systemd (not detected).'
    busy_ok         = not menu_ctx.busy
    busy_reason     = '' if busy_ok else 'Another service action is still running.'

    def svc_item(item_id, text, action, needs_systemd=True):
        enabled = busy_ok and (systemd_ok or not needs_systemd)
        reason  = busy_reason or (systemd_reason if needs_systemd else '')
        return MenuItem(
            item_id=item_id, kind=KIND_ACTION, text=text,
            section=SECTION_SERVICES, action=action,
            enabled=enabled, disabled_reason=reason, indent=1,
            help_title=text,
            help_text=_SERVICE_HELP_DCT.get(action, ''))

    items_lst.append(svc_item(
        'svc_restart', 'Re/Start Toshy Services', 'restart_services'))
    items_lst.append(svc_item(
        'svc_stop', 'Stop Toshy Services', 'stop_services'))
    items_lst.append(svc_item(
        'cfg_restart', 'Re/Start Config-Only', 'restart_config_only', needs_systemd=False))
    items_lst.append(svc_item(
        'cfg_stop', 'Stop Config-Only', 'stop_config_only', needs_systemd=False))
    return items_lst


_SERVICE_HELP_DCT = {
    'restart_services':     ('Start or restart both the config service and the '
                             'session monitor service.'),
    'stop_services':        ('Stop both the config service and the session '
                             'monitor service.'),
    'restart_config_only':  ('Start only the config (keymapper) process, without '
                             'systemd services. Useful for testing.'),
    'stop_config_only':     'Stop the manually-run config (keymapper) process.',
}


def _build_prefs_section(cnfg, menu_ctx: MenuContext):
    items_lst = [_heading(
        SECTION_PREFS, 'Preferences', menu_ctx,
        help_title='Preferences',
        help_text='Toggles for the optional features of the Toshy config.')]
    if SECTION_PREFS not in menu_ctx.expanded:
        return items_lst

    current_group = PREF_GROUP_MAIN
    for toggle in PREF_TOGGLES:
        if toggle.group != current_group:
            current_group = toggle.group
            items_lst.append(MenuItem(
                item_id=f'group_label_{current_group}',
                kind=KIND_LABEL,
                text=f'--- {current_group} ---',
                section=SECTION_PREFS,
                indent=1,
                help_title=current_group,
                help_text=PREF_GROUP_HELP.get(current_group, '')))
        items_lst.append(MenuItem(
            item_id=f'pref_{toggle.attr_name}',
            kind=KIND_TOGGLE,
            text=toggle.label_long,
            section=SECTION_PREFS,
            action='toggle_pref',
            payload=toggle.attr_name,
            checked=bool(getattr(cnfg, toggle.attr_name)),
            enabled=not menu_ctx.busy,
            indent=1,
            help_title=toggle.help_title,
            help_text=toggle.help_text))
    return items_lst


def _build_choice_section(cnfg, menu_ctx: MenuContext, section, choice_group):
    current_value   = getattr(cnfg, choice_group.attr_name)
    current_label   = choice_group.value_labels.get(current_value, str(current_value))
    heading_text    = f'{choice_group.group_label}: {current_label}'
    items_lst = [_heading(
        section, heading_text, menu_ctx,
        help_title=choice_group.help_title,
        help_text=choice_group.help_text)]
    if section not in menu_ctx.expanded:
        return items_lst

    for value in choice_group.values:
        value_label = choice_group.value_labels.get(value, value)
        items_lst.append(MenuItem(
            item_id=f'{section}_{value}',
            kind=KIND_RADIO,
            text=value_label,
            section=section,
            action='set_choice',
            payload=(choice_group.attr_name, value),
            checked=(value == current_value),
            enabled=not menu_ctx.busy,
            indent=1,
            help_title=choice_group.help_title,
            help_text=choice_group.value_help.get(value, choice_group.help_text)))
    return items_lst


def _build_overlays_section(cnfg, menu_ctx: MenuContext):
    mask = cnfg.overlay_mask
    active_count = sum(1 for flag, _name, _desc in OVL_METADATA if mask & flag)
    items_lst = [_heading(
        SECTION_OVERLAYS, f'Overlays: {active_count} of {len(OVL_METADATA)} active',
        menu_ctx,
        help_title='Overlays',
        help_text=(
            'Groups of remaps that can be toggled on or off, including '
            'user flags for custom keymaps in your config.'))]
    if SECTION_OVERLAYS not in menu_ctx.expanded:
        return items_lst

    for preset_id, preset_text, preset_mask in _OVERLAY_PRESETS:
        items_lst.append(MenuItem(
            item_id=preset_id,
            kind=KIND_ACTION,
            text=preset_text,
            section=SECTION_OVERLAYS,
            action='apply_overlay_preset',
            payload=preset_mask,
            enabled=not menu_ctx.busy,
            indent=1,
            help_title='Overlay Presets',
            help_text=('One-click switches that replace the entire overlay '
                       'mask. Individual flags can still be toggled after.')))

    for flag, display_name, description in OVL_METADATA:
        parent = get_flag_parent(flag)
        parent_missing = parent is not None and not (mask & parent)
        reason = ''
        if parent_missing:
            parent_entry = next(
                (entry for entry in OVL_METADATA if entry[0] == parent), None)
            parent_name = parent_entry[1] if parent_entry else 'its parent overlay'
            reason = f'Requires "{parent_name}" to be enabled first.'
        items_lst.append(MenuItem(
            item_id=f'ovl_{flag.name}',
            kind=KIND_TOGGLE,
            text=display_name,
            section=SECTION_OVERLAYS,
            action='toggle_overlay',
            payload=flag,
            checked=bool(mask & flag),
            enabled=(not menu_ctx.busy) and not parent_missing,
            disabled_reason=reason,
            indent=1,
            help_title=display_name,
            help_text=description))
    return items_lst


def _build_tools_section(menu_ctx: MenuContext):
    items_lst = [_heading(
        SECTION_TOOLS, 'Tools', menu_ctx,
        help_title='Tools',
        help_text='Open related Toshy apps, folders, and logs.')]
    if SECTION_TOOLS not in menu_ctx.expanded:
        return items_lst

    gui_ok      = menu_ctx.has_gui_display
    gui_reason  = '' if gui_ok else 'No graphical display detected (DISPLAY/WAYLAND_DISPLAY).'

    items_lst.append(MenuItem(
        item_id='open_prefs_app', kind=KIND_ACTION,
        text='Open Preferences App', section=SECTION_TOOLS,
        action='open_prefs_app',
        enabled=gui_ok, disabled_reason=gui_reason, indent=1,
        help_title='Open Preferences App',
        help_text='Launch the GTK4 Toshy Preferences application.'))
    items_lst.append(MenuItem(
        item_id='open_config_folder', kind=KIND_ACTION,
        text='Open Config Folder', section=SECTION_TOOLS,
        action='open_config_folder',
        enabled=gui_ok, disabled_reason=gui_reason, indent=1,
        help_title='Open Config Folder',
        help_text='Open ~/.config/toshy in the graphical file manager.'))
    items_lst.append(MenuItem(
        item_id='show_services_log', kind=KIND_ACTION,
        text='Show Services Log (new terminal)', section=SECTION_TOOLS,
        action='show_services_log',
        enabled=(menu_ctx.is_systemd and gui_ok),
        disabled_reason=(gui_reason or
                         'Services log needs systemd (not detected).'),
        indent=1,
        help_title='Show Services Log',
        help_text=('Follow the output of the Toshy services in a new '
                   'terminal window (this window stays on the menu).')))
    items_lst.append(MenuItem(
        item_id='quit_menu', kind=KIND_ACTION,
        text='Quit', section=SECTION_TOOLS,
        action='quit', indent=1,
        help_title='Quit',
        help_text='Exit the Toshy terminal menu. Services are not affected.'))
    return items_lst


def detect_gui_display():
    """True if a graphical session appears to be reachable."""
    return bool(os.environ.get('DISPLAY') or os.environ.get('WAYLAND_DISPLAY'))

# End of file #
