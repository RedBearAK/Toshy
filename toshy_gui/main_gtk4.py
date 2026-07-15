#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__version__ = '20260715'

# Preferences app for Toshy, using GTK-4 and Adwaita
TOSHY_PART      = 'gui-gtk4'  # Different from tkinter version to avoid lockfile conflicts
TOSHY_PART_NAME = 'Toshy Preferences app (GTK-4)'
APP_VERSION     = __version__

# Basic imports for accessibility check
import os
import subprocess

gtk4_config = os.path.expanduser("~/.config/gtk-4.0/settings.ini")
if os.path.exists(gtk4_config):
    try:
        with open(gtk4_config, 'r') as f:
            content = f.read()
            if 'gtk-modules=' in content:
                print()
                print("The 'gtk-modules' key in ~/.config/gtk-4.0/settings.ini causes a GTK warning.")
                print("To prevent the warning, comment out or delete that line in 'settings.ini'.")
                print()
    except:
        pass

# Check for accessibility support before importing GTK (to suppress a warning)
def is_a11y_available():
    try:
        # D-Bus query to check whether a11y support is present:
        # gdbus introspect --session --dest org.a11y.Bus --object-path /org/a11y/bus
        result = subprocess.run([
            'gdbus', 'introspect', '--session',
            '--dest', 'org.a11y.Bus',
            '--object-path', '/org/a11y/bus'
        ], capture_output=True, timeout=2)
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


# Suppress an innocuous warning in the terminal about a11y support
if not is_a11y_available():
    os.environ['GTK_A11Y'] = 'none'


# GTK-4 imports
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib


# Suppress GTK warnings about config file issues
def null_log_handler(domain, level, message, user_data):
    # Suppress specific annoying warnings that are config-related
    if any(phrase in message for phrase in [
        "Unknown key gtk-modules",
        "gtk-application-prefer-dark-theme with libadwaita is unsupported"
    ]):
        return  # Suppress these
    # Let other messages through (optional - remove this to suppress all)
    print(f"({domain}): {message}")


# Install the log handler for GTK and Adwaita domains, to suppress 
# unimportant terminal warnings ('gtk-modules' can't be suppressed)
GLib.log_set_handler("Gtk", GLib.LogLevelFlags.LEVEL_WARNING, null_log_handler, None)
GLib.log_set_handler("Adwaita", GLib.LogLevelFlags.LEVEL_WARNING, null_log_handler, None)

# Initialize Toshy runtime before other imports
from toshy_common.runtime_utils import initialize_toshy_runtime
runtime = initialize_toshy_runtime()

# Business logic imports (unchanged from tkinter version)
from toshy_common import logger
from toshy_common.logger import *
from toshy_common.env_context import EnvironmentInfo
from toshy_common.settings_class import Settings
from toshy_common.notification_manager import NotificationManager
from toshy_common.process_manager import ProcessManager
from toshy_common.service_manager import ServiceManager
from toshy_common.monitoring import SettingsMonitor, ServiceMonitor

# Local GUI components
from toshy_gui.gui.service_panel_gtk4 import ServicePanel
from toshy_gui.gui.settings_panel_gtk4 import SettingsPanel
from toshy_gui.gui.tools_panel import ToolsPanel
from toshy_gui.gui.bottom_panel_gtk4 import BottomPanel

# Make process manager global
process_mgr = None

logger.FLUSH        = True
logger.VERBOSE      = False


class ToshyPreferencesWindow(Gtk.ApplicationWindow):
    """Main preferences window for Toshy (GTK-4 version)"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Window properties
        self.set_title("Toshy Preferences")
        self.set_default_size(900, 650)  # Match tkinter size better
        # self.set_resizable(True)

        # Set up the window icon
        try:
            self.set_icon_name("toshy_app_icon_rainbow")
        except Exception:
            debug("Could not set window icon")

        # Set up business logic (same as tkinter version)
        self.setup_business_logic()

        # Create main content
        self.setup_ui()

        # Connect window close signal to cleanup
        self.connect('close-request', self.on_close_request)

    def setup_business_logic(self):
        """Set up the same business logic as tkinter version"""
        # Settings
        self.cnfg = Settings(runtime.config_dir)
        self.cnfg.watch_database()

        # Notification manager
        self.ntfy = NotificationManager("toshy_app_icon_rainbow", title='Toshy Alert (GTK-4)')

        # Service manager
        self.service_manager = ServiceManager(self.ntfy, "toshy_app_icon_rainbow", "toshy_app_icon_rainbow_inverse")

        # First, create service panel
        self.service_panel = ServicePanel(runtime, self.service_manager, self)

        # After creating service panel, create settings panel
        self.settings_panel = SettingsPanel(self.cnfg, runtime, self)

        # After creating settings panel, create tools panel
        self.tools_panel = ToolsPanel(self.cnfg, self.ntfy, DESKTOP_ENV, runtime, self.service_manager, self)

        # After creating settings panel, create bottom panel
        self.bottom_panel = BottomPanel(self.cnfg, self)

    def setup_ui(self):
        """Set up the user interface"""
        # Main container with some padding
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        main_box.set_margin_top(20)
        main_box.set_margin_bottom(20)
        main_box.set_margin_start(20)
        main_box.set_margin_end(20)

        # Service panel (replaces top section)
        main_box.append(self.service_panel)

        # # Middle section for settings
        # middle_section = self.create_middle_section()
        # main_box.append(middle_section)

        main_box.append(self.settings_panel)

        main_box.append(self.tools_panel)

        # Add spacer to push bottom panel to actual bottom
        spacer = Gtk.Box()
        spacer.set_vexpand(True)
        main_box.append(spacer)

        # Bottom section for version info and theme control
        main_box.append(self.bottom_panel)

        # Set the main container as the window's child
        self.set_child(main_box)

    def create_middle_section(self):
        """Create the middle section for settings"""
        return self.settings_panel

    def update_service_status(self, config_status, session_status):
        """Update service status labels (called by monitoring)"""
        self.service_panel.update_service_status(config_status, session_status)

    def on_close_request(self, window):
        """Handle window close request"""
        debug("GTK-4 window closing")
        return False  # Allow the window to close


class ToshyPreferencesApp(Adw.Application):
    """Main application class for Toshy Preferences"""

    def __init__(self):
        super().__init__(application_id='app.toshy.preferences')

        # Set application name (fixes menu bar showing "Python")
        self.set_resource_base_path('/io/github/toshy/preferences')

        # Set up proper theming - follow system preference by default
        style_manager = Adw.StyleManager.get_default()
        style_manager.set_color_scheme(Adw.ColorScheme.DEFAULT)  # Follow system

        self.window = None
        self.settings_monitor = None
        self.service_monitor = None

    def do_activate(self):
        """Called when the application is activated"""
        if not self.window:
            self.window = ToshyPreferencesWindow(application=self)
            self.setup_monitoring()
        self.window.present()

    def setup_monitoring(self):
        """Set up settings and service monitoring (same as tkinter version)"""
        def on_settings_changed():
            """Callback for when settings change"""
            debug("GTK-4: Settings changed - updating controls") 
            GLib.idle_add(self.window.settings_panel.load_settings)
            GLib.idle_add(self.window.tools_panel.load_settings)
            GLib.idle_add(self.window.bottom_panel.update_theme)

        def on_service_status_changed(config_status, session_status):
            """Callback for when service status changes"""
            debug(f"GTK-4: Service status changed - Config: {config_status}, Session: {session_status}")
            # Update the window's status labels
            GLib.idle_add(self.window.update_service_status, config_status, session_status)

        # Create monitors (same as tkinter version)
        self.settings_monitor = SettingsMonitor(self.window.cnfg, on_settings_changed)
        self.service_monitor = ServiceMonitor(on_service_status_changed)

        # Start monitoring if systemd is available
        if runtime.is_systemd:
            import shutil
            if shutil.which('systemctl'):
                # Help out the config file user service - only import existing env vars
                env_vars_to_check = [
                    "KDE_SESSION_VERSION",
                    # "PATH",               # Might be causing problem with venv injection in PATH everywhere
                    "XDG_SESSION_TYPE",
                    "XDG_SESSION_DESKTOP",
                    "XDG_CURRENT_DESKTOP", 
                    "DESKTOP_SESSION",
                    "DISPLAY",
                    "WAYLAND_DISPLAY",
                ]
                
                existing_vars = [var for var in env_vars_to_check if var in os.environ]
                
                if existing_vars:
                    cmd_lst = ["systemctl", "--user", "import-environment"] + existing_vars
                    subprocess.run(cmd_lst)
                
                self.service_monitor.start_monitoring()
                debug("GTK-4: Service monitoring started")

        self.settings_monitor.start_monitoring()
        debug("GTK-4: Settings monitoring started")


def main():
    """Main entry point for GTK-4 version"""
    global process_mgr
    global DESKTOP_ENV

    env_ctxt_getter             = EnvironmentInfo()
    env_info_dct                = env_ctxt_getter.get_env_info()
    DESKTOP_ENV                 = str(env_info_dct.get('DESKTOP_ENV', None)).casefold()

    debug("Starting Toshy Preferences (GTK-4 version)")

    # Initialize process management
    process_mgr = ProcessManager(TOSHY_PART, TOSHY_PART_NAME)
    process_mgr.initialize()

    # Set application name for better menu bar display
    import sys
    if len(sys.argv) > 0:
        sys.argv[0] = "Toshy Preferences"

    # Create and run the application
    app = ToshyPreferencesApp()

    # Set application name/title for desktop integration
    app.set_resource_base_path(None)  # Clear the resource path if it causes issues

    return app.run()


if __name__ == "__main__":
    main()
