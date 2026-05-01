import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GLib
import os
import shutil
import subprocess

from toshy_common.logger import debug
from toshy_common.notification_manager import NotificationManager
from toshy_common.service_manager import ServiceManager
from toshy_common.settings_class import Settings
from toshy_common.runtime_utils import ToshyRuntime
import toshy_common.terminal_utils as term_utils

# Configuration for help button appearance
HELP_BUTTON_SIZE = 24  # Width and height in pixels - change here to resize all help buttons


class ToolsPanel(Gtk.Box):
    """
    Tools and actions panel for GTK-4 Toshy Preferences.
    
    Contains utility controls and action buttons:
    - Left: Keyboard type override and autostart settings
    - Right: Action buttons (config folder, services log)
    """
    
    def __init__(self, cnfg: Settings, ntfy: NotificationManager, desktop_env: str,
                    runtime: ToshyRuntime, service_manager: ServiceManager, parent_window=None):
        debug("=== ToolsPanel.__init__ called ===")
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=40)
        
        self.cnfg               = cnfg  # Settings object
        self.ntfy               = ntfy  # Notification manager
        self.desktop_env        = desktop_env  # Desktop environment string
        self.runtime            = runtime  # Runtime configuration
        self.service_manager    = service_manager  # Manager for systemd services
        self.parent_window      = parent_window  # For help dialogs

        self.keyboard_types     = ["Auto-Adapt", "Apple", "Chromebook", "IBM", "Windows"]
        
        debug(f"ToolsPanel initialized with parent_window: {parent_window is not None}")
        debug(f"Desktop environment: {desktop_env}")
        debug(f"Systemd available: {runtime.is_systemd}")
        
        # Set up the panel layout
        self.setup_ui()
        
        # Add margins
        self.set_margin_top(20)
        self.set_margin_bottom(20)
        
        # Connect to realize signal to set up CSS when widget is ready
        self.connect('realize', self.on_realize)
        
        debug("=== ToolsPanel.__init__ completed ===")
        
    def on_realize(self, widget):
        """Set up CSS when widget is realized and has a display"""
        css_provider = Gtk.CssProvider()
        
        css_data = f"""
        .left-column {{
            margin-top: 10px;
        }}
        .tools-help-button {{
            min-width: {HELP_BUTTON_SIZE}px;
            min-height: {HELP_BUTTON_SIZE}px;
            padding: 2px;
            font-size: 12px;
            font-weight: bold;
        }}
        .control-group-header {{
            font-size: 14px;
            font-weight: bold;
            color: alpha(currentColor, 0.7);
        }}
        .control-label {{
            font-weight: bold;
            margin-right: 8px;
        }}
        .action-button {{
            min-height: 36px;
        }}
        """
        css_provider.load_from_data(css_data, -1)
        
        # Apply CSS to the display
        display = self.get_display()
        if display:
            Gtk.StyleContext.add_provider_for_display(
                display,
                css_provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )
        
    def setup_ui(self):
        """Set up the tools panel user interface"""
        debug("=== ToolsPanel.setup_ui called ===")
        
        # Left column - settings and controls
        left_column = self.create_left_column()
        left_column.set_size_request(400, -1)  # Fixed width
        left_column.set_hexpand(False)  # Don't expand
        self.append(left_column)
        
        # Right column - action buttons  
        right_column = self.create_right_column()
        right_column.set_size_request(400, -1)  # Fixed width
        right_column.set_hexpand(False)  # Don't expand
        self.append(right_column)
        
        debug("=== ToolsPanel.setup_ui completed ===")
        
    def create_left_column(self):
        """Create the left column with keyboard type and autostart controls"""
        debug("Creating left column...")
        
        column = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        column.add_css_class("left-column")  # Add CSS class for positioning
        
        # Keyboard type override control
        keyboard_control = self.create_keyboard_type_control()
        column.append(keyboard_control)
        
        # Autostart controls
        autostart_control = self.create_autostart_controls()
        column.append(autostart_control)
        
        debug("Left column created")
        return column
        
    def create_right_column(self):
        """Create the right column with action buttons"""
        debug("Creating right column...")
        
        column = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        
        # Open config folder button
        config_button = self.create_config_folder_button()
        column.append(config_button)
        
        # Add spacer between buttons
        spacer = Gtk.Box()
        spacer.set_size_request(-1, 8)  # 8px vertical spacer
        column.append(spacer)

        # Show services log button
        log_button = self.create_services_log_button()
        column.append(log_button)
        
        debug("Right column created")
        return column
        
    def create_keyboard_type_control(self):
        """Create the keyboard type override control"""
        # Container for the whole control
        container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        
        # Header with help button
        header_container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        
        header_label = Gtk.Label(label="Keyboard Type (changes are TEMPORARY!)")
        header_label.add_css_class("control-group-header")
        header_container.append(header_label)
        
        # Add expandable spacer to push help button to the right
        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        header_container.append(spacer)
        
        # Help button
        if self.parent_window:
            help_title = "Temporary Keyboard Type"
            help_text = (
                "Temporarily override the detected keyboard type without saving the setting.\n\n"
                "This is useful for testing different keyboard layouts or when the "
                "auto-detection doesn't work correctly for your hardware.\n\n"
                "See the FAQ page in the GitHub repo Wiki for more information about "
                "how to implement a permanent solution for a specific device."
            )
            
            help_button = Gtk.Button(label="?")
            help_button.set_size_request(HELP_BUTTON_SIZE, HELP_BUTTON_SIZE)
            help_button.set_tooltip_text("Show help for keyboard type override")
            help_button.add_css_class("tools-help-button")
            help_button.connect('clicked', lambda btn: self.show_help_dialog(help_title, help_text))
            header_container.append(help_button)
        
        container.append(header_container)
        
        # Dropdown for keyboard type selection
        dropdown_container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        dropdown_container.set_margin_start(20)  # Indent the dropdown
        
        type_label = Gtk.Label(label="Type:")
        type_label.add_css_class("control-label")
        dropdown_container.append(type_label)
        
        self.keyboard_type_dropdown = Gtk.DropDown()
        self.keyboard_type_dropdown.set_size_request(200, -1)
        
        string_list = Gtk.StringList()
        for i, kb_type in enumerate(self.keyboard_types):
            # Add asterisk to the first/default item (Auto-Adapt) for display
            display_text = f"{kb_type}*" if i == 0 else kb_type
            string_list.append(display_text)
        self.keyboard_type_dropdown.set_model(string_list)
        
        # Load initial value from settings
        current_kbtype = getattr(self.cnfg, 'override_kbtype', 'Auto-Adapt')
        try:
            initial_index = self.keyboard_types.index(current_kbtype)
            self.keyboard_type_dropdown.set_selected(initial_index)
        except ValueError:
            self.keyboard_type_dropdown.set_selected(0)  # Default to Auto-Adapt

        # Connect to selection change
        self.keyboard_type_dropdown.connect('notify::selected', self.on_keyboard_type_changed)
        
        dropdown_container.append(self.keyboard_type_dropdown)
        container.append(dropdown_container)
        
        return container
        
    def create_autostart_controls(self):
        """Create the autostart checkboxes"""
        # Container for the whole control group
        container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        
        # Header with help button
        header_container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        
        header_label = Gtk.Label(label="Autostart Settings")
        header_label.add_css_class("control-group-header")
        header_container.append(header_label)
        
        # Add expandable spacer to push help button to the right
        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        header_container.append(spacer)
        
        # Help button
        if self.parent_window:
            help_title = "Autostart Settings"
            help_text = (
                "Control which Toshy components start automatically when you log in:\n\n"
                "• Autostart Services: \n"
                "    Start Toshy services in background at login\n\n"
                "• Autoload Tray Icon: \n"
                "    Show Toshy indicator app in your system tray"
            )
            
            help_button = Gtk.Button(label="?")
            help_button.set_size_request(HELP_BUTTON_SIZE, HELP_BUTTON_SIZE)
            help_button.set_tooltip_text("Show help for autostart settings")
            help_button.add_css_class("tools-help-button")
            help_button.connect('clicked', lambda btn: self.show_help_dialog(help_title, help_text))
            header_container.append(help_button)
        
        container.append(header_container)
        
        # Checkboxes container
        checkboxes_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        checkboxes_container.set_margin_start(20)  # Indent checkboxes
        
        # Services autostart checkbox
        self.autostart_services_checkbox = Gtk.CheckButton(label="Autostart Services")
        initial_services = getattr(self.cnfg, 'autostart_services', True)
        self.autostart_services_checkbox.set_active(initial_services)
        self.autostart_services_checkbox.connect('toggled', self.on_autostart_services_toggled)

        # Disable checkbox if not using systemd
        if not self.runtime.is_systemd:
            self.autostart_services_checkbox.set_sensitive(False)
            self.autostart_services_checkbox.set_active(False)  # Uncheck it too
            self.autostart_services_checkbox.set_label("Autostart Services (no systemctl/systemd)")
            self.autostart_services_checkbox.set_tooltip_text("Service autostart not available (systemd not detected)")
            debug("Autostart services checkbox disabled - systemd not available")
        else:
            self.autostart_services_checkbox.set_tooltip_text("Enable/disable Toshy services to start automatically at login")

        checkboxes_container.append(self.autostart_services_checkbox)        
        # Tray icon autostart checkbox  
        self.autoload_tray_checkbox = Gtk.CheckButton(label="Autoload Tray Icon")
        initial_tray = getattr(self.cnfg, 'autoload_tray_icon', True)
        self.autoload_tray_checkbox.set_active(initial_tray)
        self.autoload_tray_checkbox.connect('toggled', self.on_autoload_tray_toggled)
        checkboxes_container.append(self.autoload_tray_checkbox)
        
        container.append(checkboxes_container)
        
        return container
        
    def create_config_folder_button(self):
        """Create the open config folder button"""
        container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        
        button = Gtk.Button(label="Open Config Folder")
        button.add_css_class("action-button")
        button.set_hexpand(True)  # Make button expand to fill available space
        button.set_valign(Gtk.Align.CENTER)  # Center vertically in container
        button.set_tooltip_text("Open the Toshy configuration folder in your file manager")
        button.connect('clicked', self.on_open_config_folder)
        container.append(button)
        
        # Add help button
        if self.parent_window:
            help_title = "Open Config Folder"
            help_text = (
                "Opens the Toshy configuration folder in your default file manager.\n\n"
                "User config file to edit is:\n\n  ~/.config/toshy/toshy_config.py\n\n"
                "DO NOT edit the files in the `default-toshy-config` folder. "
                "Those are clean copies of the originals."
            )
            
            help_button = Gtk.Button(label="?")
            help_button.set_size_request(HELP_BUTTON_SIZE, HELP_BUTTON_SIZE)
            help_button.set_valign(Gtk.Align.CENTER)  # Center vertically in container
            help_button.set_tooltip_text("Show help for config folder")
            help_button.add_css_class("tools-help-button")
            help_button.connect('clicked', lambda btn: self.show_help_dialog(help_title, help_text))
            container.append(help_button)
        
        return container
        
    def create_services_log_button(self):
        """Create the show services log button"""
        container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        
        button = Gtk.Button(label="Show Services Log")
        button.add_css_class("action-button")
        button.set_hexpand(True)  # Make button expand to fill available space
        button.set_valign(Gtk.Align.CENTER)  # Center vertically in container
        button.set_tooltip_text("Open the Toshy systemd services log in a terminal")
        button.connect('clicked', self.on_show_services_log)
        
        # Disable button if not using systemd
        if not self.runtime.is_systemd:
            button.set_sensitive(False)
            button.set_tooltip_text("Services log not available (systemd not detected)")
            debug("Services log button disabled - systemd not available")
        
        container.append(button)
        
        # Add help button
        if self.parent_window:
            help_title = "Show Services Log"
            help_text = (
                "Opens the Toshy systemd services log in a terminal window.\n\n"
                "The log shows real-time information like:\n"
                "• Service start/stop events\n"
                "• Window context provider errors\n"
                "• Service/permission errors\n\n"
                "Note: This feature REQUIRES systemd."
            )
            
            help_button = Gtk.Button(label="?")
            help_button.set_size_request(HELP_BUTTON_SIZE, HELP_BUTTON_SIZE)
            help_button.set_valign(Gtk.Align.CENTER)  # Center vertically in container
            help_button.set_tooltip_text("Show help for services log")
            help_button.add_css_class("tools-help-button")
            help_button.connect('clicked', lambda btn: self.show_help_dialog(help_title, help_text))
            container.append(help_button)
        
        return container
        
    def on_keyboard_type_changed(self, dropdown, pspec):
        """Handle keyboard type dropdown selection change"""
        selected_index = dropdown.get_selected()
        selected_type = self.keyboard_types[selected_index] if selected_index < len(self.keyboard_types) else "Auto-Adapt"
        
        debug(f"Keyboard type changed to: {selected_type}")
        
        # Save to settings (like the tray app)
        setattr(self.cnfg, 'override_kbtype', selected_type)
        self.cnfg.save_settings()
        
        # Show notification with warning for non-Auto-Adapt types
        valid_override_types = ['Apple', 'Chromebook', 'IBM', 'Windows']
        if selected_type in valid_override_types:
            notification_msg = ('Overriding keyboard type disables auto-adaptation.\n'
                            'This is meant as a temporary fix only! See README.')
            self.ntfy.send_notification(notification_msg)
        else:
            notification_msg = "Keyboard type set to Auto-Adapt (default)"
            self.ntfy.send_notification(notification_msg)
        
    def on_autostart_services_toggled(self, checkbox):
        """Handle autostart services checkbox toggle"""
        new_value = checkbox.get_active()
        debug(f"Autostart services changed to: {new_value}")
        
        if not (shutil.which('systemctl') and self.runtime.is_systemd):
            debug("systemctl not available or not using systemd")
            return
        
        try:
            if new_value:
                self.service_manager.enable_services()  # Should handle notification internally
            else:
                self.service_manager.disable_services()  # Should handle notification internally
        except subprocess.CalledProcessError as proc_err:
            # ServiceManager already logged the error, just handle UI state
            debug(f"Service toggle failed, reverting checkbox")
            checkbox.set_active(not new_value)  # Revert checkbox state
            return
        
        import time
        time.sleep(0.5)
        
        setattr(self.cnfg, 'autostart_services', new_value)
        self.cnfg.save_settings()

    # def on_autoload_tray_toggled(self, checkbox):
    #     """Handle autoload tray icon checkbox toggle"""
    #     new_value = checkbox.get_active()
    #     debug(f"Autoload tray icon changed to: {new_value}")
        
    #     # Save to settings
    #     setattr(self.cnfg, 'autoload_tray_icon', new_value)
    #     self.cnfg.save_settings()
        
    #     # Show notification
    #     status_text = "ENABLED" if new_value else "DISABLED"
    #     self.ntfy.send_notification(f"Autoload tray icon {status_text}")
        

    def on_autoload_tray_toggled(self, checkbox):
        """Handle autoload tray icon checkbox toggle"""
        new_value = checkbox.get_active()
        debug(f"Autoload tray icon changed to: {new_value}")
        
        # Save to settings
        setattr(self.cnfg, 'autoload_tray_icon', new_value)
        self.cnfg.save_settings()
        
        # Do the actual autostart work (like the tray app does)
        self.update_tray_autostart(new_value)
        
        # Show notification
        status_text = "ENABLED" if new_value else "DISABLED"
        self.ntfy.send_notification(f"Autoload tray icon {status_text}")

    def update_tray_autostart(self, enable):
        """Create or remove tray icon autostart symlink"""
        import subprocess
        import os
        
        tray_dt_file_name = 'Toshy_Tray.desktop'
        home_apps_path = os.path.join(self.runtime.home_dir, '.local', 'share', 'applications')
        tray_dt_file_path = os.path.join(home_apps_path, tray_dt_file_name)
        
        home_autostart_path = os.path.join(self.runtime.home_dir, '.config', 'autostart')
        tray_link_file_path = os.path.join(home_autostart_path, tray_dt_file_name)
        
        try:
            if enable:
                # Create symlink
                cmd_lst = ['ln', '-sf', tray_dt_file_path, tray_link_file_path]
                subprocess.run(cmd_lst, check=True)
                debug("Tray icon autostart enabled")
            else:
                # Remove symlink
                cmd_lst = ['rm', '-f', tray_link_file_path]
                subprocess.run(cmd_lst, check=True)
                debug("Tray icon autostart disabled")
        except subprocess.CalledProcessError as e:
            debug(f"Error updating tray autostart: {e}")


    def on_open_config_folder(self, button):
        """Handle open config folder button click"""
        config_path = self.runtime.config_dir
        debug(f"Opening config folder: {config_path}")
        
        try:
            # Use xdg-open to open the folder in the default file manager
            subprocess.Popen(['xdg-open', config_path])
        except Exception as e:
            error_msg = f"Failed to open config folder: {e}"
            debug(error_msg)
            self.ntfy.send_notification(error_msg)
            
    def on_show_services_log(self, button):
        """Handle show services log button click"""
        if not self.runtime.is_systemd:
            debug("Services log requested but systemd not available")
            return
            
        try:
            term_utils.run_cmd_lst_in_terminal(['toshy-services-log'], desktop_env=self.desktop_env)
        except term_utils.TerminalNotFoundError as e:
            debug(f"Terminal error: {e}")
            self.ntfy.send_notification(str(e))
            
    def load_settings(self):
        """Load settings from config and update controls (called by external monitoring)"""
        debug("Loading tools settings...")
        
        # Update autostart checkboxes
        if hasattr(self, 'autostart_services_checkbox'):
            if self.runtime.is_systemd:
                services_value = getattr(self.cnfg, 'autostart_services', True)
                if self.autostart_services_checkbox.get_active() != services_value:
                    debug(f"Updating autostart services checkbox to {services_value}")
                    self.autostart_services_checkbox.set_active(services_value)
                
        if hasattr(self, 'autoload_tray_checkbox'):
            tray_value = getattr(self.cnfg, 'autoload_tray_icon', True)
            if self.autoload_tray_checkbox.get_active() != tray_value:
                debug(f"Updating autoload tray checkbox to {tray_value}")
                self.autoload_tray_checkbox.set_active(tray_value)
                

        # Update keyboard type dropdown
        if hasattr(self, 'keyboard_type_dropdown'):
            current_kbtype = getattr(self.cnfg, 'override_kbtype', 'Auto-Adapt')
            try:
                target_index = self.keyboard_types.index(current_kbtype)
                if self.keyboard_type_dropdown.get_selected() != target_index:
                    debug(f"Updating keyboard type dropdown to {current_kbtype}")
                    self.keyboard_type_dropdown.set_selected(target_index)
            except ValueError:
                # If unknown type, default to Auto-Adapt
                self.keyboard_type_dropdown.set_selected(0)

        debug("Tools settings loaded")
        
    def show_help_dialog(self, title, text):
        """Show help dialog using centralized HelpDialog class"""
        if not self.parent_window:
            return
        
        from toshy_gui.gui.help_dialog_gtk4 import HelpDialog
        dialog = HelpDialog(self.parent_window, title, text)
        dialog.present()
