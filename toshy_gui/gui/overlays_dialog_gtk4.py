"""
Modal pop-up dialog for toggling overlay flags.

Module path: toshy_gui/gui/overlays_dialog_gtk4.py

Provides a standalone dialog window for managing the overlay mask. Users
toggle individual overlay flags or click preset buttons to set common
configurations. Auto-syncs with external settings changes via its own
SettingsMonitor instance (same pattern as the main window and tray).

Invoked from the main window via a button. Modal — blocks the main
window only, not other applications.
"""

__version__ = '20260503'

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GLib

from toshy_common.logger import debug
from toshy_common.monitoring import SettingsMonitor
from toshy_common.overlay_context import (
    OverlayFlag,
    OVL_METADATA,
    OVL_PRESET_FULL,
    OVL_PRESET_MINIMAL,
    OVL_PRESET_NONE,
    get_flag_parent,
)


class OverlaysDialog(Gtk.Window):
    """Modal dialog for managing overlay flag settings.

    Built dynamically from OVL_METADATA so adding a new overlay flag
    requires only updating overlay_context.py — no changes here.

    All flags appear, including user slots. Users who add custom
    overlay-tagged keymaps in their config can enable matching user
    flags from this dialog.
    """

    def __init__(self, parent, cnfg):
        super().__init__()

        self.cnfg = cnfg

        # {OverlayFlag: Gtk.Switch} for state sync after external changes
        self.overlay_switches = {}
        # {OverlayFlag: Gtk.Box} for sensitivity (parent rows + child rows)
        self.overlay_rows = {}
        # Suppress callback recursion when programmatically updating switches
        self._loading = False

        self.set_title("Toshy Overlays")
        self.set_transient_for(parent)
        self.set_modal(True)
        self.set_resizable(False)
        self.set_default_size(500, 600)

        self.setup_css()
        self.setup_ui()
        self.setup_keyboard_shortcuts()

        # Own settings monitor instance — same pattern as main window/tray.
        # Polls in a background thread, fires our callback when any setting
        # changes (whether from this dialog, the tray, or external sources).
        self.settings_monitor = SettingsMonitor(
            self.cnfg,
            self.on_external_settings_changed
        )
        self.settings_monitor.start_monitoring()

        # Stop the monitor thread when the dialog closes
        self.connect('close-request', self.on_close_request)

        # Load initial state
        self.load_overlay_settings()

    def setup_css(self):
        """Set up CSS for the dialog."""
        css_provider = Gtk.CssProvider()

        css_data = """
        .overlays-dialog-heading {
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 4px;
        }
        .overlays-dialog-subheading {
            font-size: 13px;
            color: alpha(currentColor, 0.7);
            margin-bottom: 12px;
        }
        .overlay-name {
            font-size: 14px;
            font-weight: bold;
        }
        .overlay-description {
            font-size: 12px;
            color: alpha(currentColor, 0.65);
        }
        .overlay-row-disabled {
            opacity: 0.5;
        }
        .overlay-section-header {
            font-size: 13px;
            font-weight: bold;
            color: alpha(currentColor, 0.6);
            margin-top: 8px;
        }
        """
        css_provider.load_from_data(css_data, -1)

        display = self.get_display()
        if display:
            Gtk.StyleContext.add_provider_for_display(
                display,
                css_provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )

    def setup_ui(self):
        """Build the dialog content."""
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        main_box.set_margin_top(20)
        main_box.set_margin_bottom(20)
        main_box.set_margin_start(20)
        main_box.set_margin_end(20)

        # Heading
        heading = Gtk.Label(label="Overlays")
        heading.set_halign(Gtk.Align.START)
        heading.add_css_class("overlays-dialog-heading")
        main_box.append(heading)

        subheading = Gtk.Label(
            label="Toggle which groups of Mac-style remaps are active."
        )
        subheading.set_halign(Gtk.Align.START)
        subheading.add_css_class("overlays-dialog-subheading")
        main_box.append(subheading)

        # Presets row
        main_box.append(self.create_presets_row())

        # Separator below presets
        main_box.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))

        # Scrollable area for the switches list
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_vexpand(True)
        scroll.set_min_content_height(350)

        switches_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)

        # Build a row per overlay flag, in metadata order
        first_user_flag_seen = False
        for flag, display_name, description in OVL_METADATA:
            is_user_flag = flag >= OverlayFlag.USER_FLAG_A

            # Insert a section header before the first user flag for visual
            # separation from built-ins
            if is_user_flag and not first_user_flag_seen:
                first_user_flag_seen = True
                user_header = Gtk.Label(label="User Flags")
                user_header.set_halign(Gtk.Align.START)
                user_header.add_css_class("overlay-section-header")
                switches_box.append(user_header)

            row = self.create_overlay_row(flag, display_name, description)
            switches_box.append(row)

        scroll.set_child(switches_box)
        main_box.append(scroll)

        # Bottom button row
        main_box.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))
        main_box.append(self.create_bottom_buttons())

        self.set_child(main_box)

    def create_presets_row(self):
        """Build the row of preset buttons."""
        container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        container.set_halign(Gtk.Align.CENTER)

        full_btn = Gtk.Button(label="All On")
        full_btn.set_tooltip_text("Enable all built-in overlays")
        full_btn.connect('clicked', self.on_preset_clicked, OVL_PRESET_FULL)
        container.append(full_btn)

        minimal_btn = Gtk.Button(label="Minimal")
        minimal_btn.set_tooltip_text(
            "Enable only Terminal Ergonomics; disable everything else"
        )
        minimal_btn.connect('clicked', self.on_preset_clicked, OVL_PRESET_MINIMAL)
        container.append(minimal_btn)

        none_btn = Gtk.Button(label="All Off")
        none_btn.set_tooltip_text("Disable all overlays")
        none_btn.connect('clicked', self.on_preset_clicked, OVL_PRESET_NONE)
        container.append(none_btn)

        return container

    def create_overlay_row(self, flag, display_name, description):
        """Build a single row for one overlay flag.

        Layout: switch on the left, name + description in a vertical box
        on the right. Stored in self.overlay_rows so sensitivity can be
        updated when parent state changes.
        """
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        row.set_margin_top(6)
        row.set_margin_bottom(6)

        switch = Gtk.Switch()
        switch.set_valign(Gtk.Align.CENTER)
        switch.connect('state-set', self.on_overlay_toggled, flag)
        row.append(switch)

        text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        text_box.set_hexpand(True)

        name_label = Gtk.Label(label=display_name)
        name_label.set_halign(Gtk.Align.START)
        name_label.add_css_class("overlay-name")
        text_box.append(name_label)

        desc_label = Gtk.Label(label=description)
        desc_label.set_halign(Gtk.Align.START)
        desc_label.set_wrap(True)
        desc_label.set_wrap_mode(Gtk.WrapMode.WORD)
        desc_label.set_xalign(0)
        desc_label.add_css_class("overlay-description")
        text_box.append(desc_label)

        row.append(text_box)

        self.overlay_switches[flag] = switch
        self.overlay_rows[flag] = row

        return row

    def create_bottom_buttons(self):
        """Build the bottom Close button row."""
        container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        container.set_halign(Gtk.Align.END)
        container.set_margin_top(8)

        close_btn = Gtk.Button(label="Close")
        close_btn.set_size_request(100, 35)
        close_btn.add_css_class("suggested-action")
        close_btn.connect('clicked', lambda btn: self.close())
        container.append(close_btn)

        return container

    def setup_keyboard_shortcuts(self):
        """Close on Escape, Ctrl+W, Enter."""
        key_controller = Gtk.EventControllerKey()
        key_controller.connect('key-pressed', self.on_key_pressed)
        self.add_controller(key_controller)

    def on_key_pressed(self, controller, keyval, keycode, state):
        """Keyboard shortcuts for closing the dialog."""
        if keyval == 65307:  # Escape
            self.close()
            return True
        if keyval == 119 and state & Gtk.accelerator_get_default_mod_mask() == 4:  # Ctrl+W
            self.close()
            return True
        if keyval in [65293, 65421]:  # Return / KP_Enter
            self.close()
            return True
        return False

    def on_overlay_toggled(self, switch, state, flag):
        """Handle individual overlay switch toggle.

        The state-set signal fires both for user-driven toggles and for
        programmatic set_active() calls. The _loading flag suppresses
        callback work during programmatic updates from load_overlay_settings.
        """
        if self._loading:
            return False    # Let the default handler update visual state

        debug(f"Overlay toggled: {flag.name} = {state}")

        if state:
            self.cnfg.overlay_mask = self.cnfg.overlay_mask | flag
        else:
            self.cnfg.overlay_mask = self.cnfg.overlay_mask & ~flag
        self.cnfg.save_settings()

        # Re-load to pick up dependency-driven changes (e.g. enabling
        # Finder Mods auto-enables Enter to Rename via apply_dependencies).
        GLib.idle_add(self.load_overlay_settings)

        return False    # Let the switch's default handler complete

    def on_preset_clicked(self, button, preset_value):
        """Apply a preset by replacing the entire overlay mask."""
        debug(f"Overlay preset applied: {int(preset_value):#b}")
        self.cnfg.overlay_mask = preset_value
        self.cnfg.save_settings()
        GLib.idle_add(self.load_overlay_settings)

    def load_overlay_settings(self):
        """Sync switch states and sensitivity from current settings.

        Called after every local change and after external changes
        propagated through the settings monitor.
        """
        self.cnfg.load_settings()
        self._loading = True
        try:
            for flag, switch in self.overlay_switches.items():
                target_state = bool(self.cnfg.overlay_mask & flag)
                if switch.get_active() != target_state:
                    switch.set_active(target_state)

                # Sensitivity: child rows greyed when parent is off
                parent = get_flag_parent(flag)
                if parent is not None:
                    parent_active = bool(self.cnfg.overlay_mask & parent)
                    row = self.overlay_rows[flag]
                    row.set_sensitive(parent_active)
                    if parent_active:
                        row.remove_css_class("overlay-row-disabled")
                    else:
                        row.add_css_class("overlay-row-disabled")
        finally:
            self._loading = False

    def on_external_settings_changed(self):
        """Settings monitor callback.

        Fires when settings change from outside this dialog (tray, CLI,
        direct DB edit, or this dialog's own changes — the monitor doesn't
        distinguish source). Refreshes the dialog's switch states.
        """
        debug("Overlays dialog: settings change detected by monitor")
        GLib.idle_add(self.load_overlay_settings)

    def on_close_request(self, window):
        """Stop the settings monitor thread before closing."""
        debug("Overlays dialog closing — stopping settings monitor")
        self.settings_monitor.stop_monitoring_thread()
        return False    # Allow the close to proceed


# End of file #
