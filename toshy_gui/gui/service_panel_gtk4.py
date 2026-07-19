import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GLib

from toshy_common.logger import debug
from toshy_common.runtime_utils import ToshyRuntime
from toshy_common.service_manager import ServiceManager


# Configuration for help button appearance
HELP_BUTTON_SIZE = 20  # Width and height in pixels - change here to resize all help buttons

# Import help system if available
try:
    from toshy_gui.gui.help_dialog_gtk4 import HelpButton
    # debug("Successfully imported help dialog system")
except ImportError as e:
    # Fallback if help dialog module not available yet
    debug(f"Help dialog import failed: {e}")
    HelpButton = None


class ServicePanel(Gtk.Box):
    """
    Service status and control panel for GTK-4 Toshy Preferences.
    
    Displays service status and provides buttons for:
    - Full service control (start/stop both config and session monitor)
    - Config-only control (start/stop just the config service)
    """
    
    def __init__(self, runtime: ToshyRuntime, service_manager: ServiceManager, parent_window=None):
        debug("=== ServicePanel.__init__ called ===")
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)
        self.runtime            = runtime
        self.service_manager    = service_manager
        self.parent_window      = parent_window  # Store reference for help dialogs
        
        debug(f"ServicePanel initialized with parent_window: {parent_window is not None}")
        debug(f"ServicePanel parent_window type: {type(parent_window)}")
        
        # Status tracking
        self.config_status      = "Unknown"
        self.session_status     = "Unknown"
        
        debug("About to call setup_ui()")
        # Set up the panel layout
        self.setup_ui()
        
        # No panel-level top/bottom margins here: the main window's section
        # spacing is the single source of truth for gaps between panels.
        
        debug("About to connect realize signal")
        # Connect to realize signal to set up CSS when widget is ready
        self.connect('realize', self.on_realize)
        debug("=== ServicePanel.__init__ completed ===")
        
    def on_realize(self, widget):
        """Set up CSS when widget is realized and has a display"""
        css_provider = Gtk.CssProvider()
        
        # CSS configuration variables
        font_families       = ( '"FantasqueSansMNoLigNerdFont", '
                                '"JetBrains Mono", "Fira Code", '
                                '"SF Mono", "Monaco", "Inconsolata", '
                                '"Roboto Mono", "Ubuntu Mono", '
                                '"Consolas", "DejaVu Sans Mono", monospace')
        heading_font_size = 22
        service_font_size = 18
        
        css_data = f"""
        .heading {{
            font-size: {heading_font_size}px;
            font-weight: bold;
        }}
        .control-group-header {{
            font-size: 14px;
            font-weight: bold;
            color: alpha(currentColor, 0.7);
        }}
        .service-help-button {{
            min-width: {HELP_BUTTON_SIZE}px;
            min-height: {HELP_BUTTON_SIZE}px;
            padding: 0px;
            font-size: 14px;
            font-weight: bold;
        }}
        .help-text {{
            font-size: 13px;
            line-height: 1.4;
        }}
        .service-status {{
            font-family: {font_families};
            font-size: 12px;
            font-weight: bold;
        }}
        .service-label {{
            font-family: {font_families};
            font-size: {service_font_size}px;
            font-weight: bold;
        }}
        .service-value {{
            font-family: {font_families};
            font-size: {service_font_size}px;
            font-weight: bold;
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
        """Set up the service panel user interface"""
        debug("=== ServicePanel.setup_ui called ===")
        
        debug("Creating status section...")
        # Left side - Service status
        status_box = self.create_status_section()
        status_box.set_hexpand(True)
        self.append(status_box)
        debug("Status section created and appended")
        
        debug("Creating controls section...")
        # Right side - Control buttons
        controls_box = self.create_controls_section()
        controls_box.set_hexpand(True)
        self.append(controls_box)
        debug("Controls section created and appended")
        
        debug("=== ServicePanel.setup_ui completed ===")
        
    def create_status_section(self):
        """Create the service status display section with proper alignment"""
        debug("=== create_status_section called ===")
        
        status_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        debug("Created status_box")
        
        # Service status header with help button
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        header_box.set_halign(Gtk.Align.CENTER)
        debug("Created header_box")
        
        status_header = Gtk.Label(label="Toshy Services Status")
        status_header.set_halign(Gtk.Align.CENTER)
        status_header.add_css_class("heading")
        header_box.append(status_header)
        debug("Created and appended status_header")
        
        # Add help button if parent window is available
        if self.parent_window:
            debug("Creating help button for service status")
            # Create a simple, always-visible help button for now
            help_button = Gtk.Button(label="?")
            help_button.set_size_request(HELP_BUTTON_SIZE, HELP_BUTTON_SIZE)
            help_button.set_tooltip_text("Show help for service status")
            help_button.add_css_class("service-help-button")
            
            # Help content stored locally with the control
            help_title = "Toshy Services Status"
            help_text = (
                'Shows the current status of Toshy services:\n\n'
                '• Toshy Config: The main keymapping service that handles keyboard shortcuts\n'
                '• Session Monitor: Stops keymapper if user session becomes inactive (to support '
                'a multi-user environment). Handles "switch user" scenario, login screen, '
                'and screensaver/lock screen.\n\n'
                'When Toshy is working properly in its automatic mode on a distro that uses '
                'systemd as the init system, both services should show a status of "Active". '
                'An error in determining the service states will show as "Unknown", and if '
                'the services are stopped the statuses will be "Inactive". If the "Config-Only" '
                'option is used to run just the keymapper process manually, the service status '
                'will show as "Inactive".'
            )
            
            # Connect to help dialog
            help_button.connect('clicked', lambda btn: self.show_help_dialog(help_title, help_text))
            header_box.append(help_button)
            debug("Help button appended to header_box")
        else:
            debug("No parent window provided for help buttons")
        
        status_box.append(header_box)
        debug("Header_box appended to status_box")
        
        # Create a grid for proper alignment of service status labels
        status_grid = Gtk.Grid()
        status_grid.set_halign(Gtk.Align.CENTER)
        status_grid.set_column_spacing(5)
        status_grid.set_row_spacing(4)
        
        # Config service row
        config_label = Gtk.Label(label="Toshy Config")
        config_label.set_halign(Gtk.Align.END)
        config_label.add_css_class("service-label")
        status_grid.attach(config_label, 0, 0, 1, 1)
        
        config_colon = Gtk.Label(label=":")
        config_colon.set_halign(Gtk.Align.CENTER)
        config_colon.add_css_class("service-label")
        status_grid.attach(config_colon, 1, 0, 1, 1)
        
        self.config_status_label = Gtk.Label(label=self.config_status)
        self.config_status_label.set_halign(Gtk.Align.START)
        self.config_status_label.add_css_class("service-value")
        status_grid.attach(self.config_status_label, 2, 0, 1, 1)
        
        # Session monitor row
        session_label = Gtk.Label(label="Session Monitor")
        session_label.set_halign(Gtk.Align.END)
        session_label.add_css_class("service-label")
        status_grid.attach(session_label, 0, 1, 1, 1)
        
        session_colon = Gtk.Label(label=":")
        session_colon.set_halign(Gtk.Align.CENTER)
        session_colon.add_css_class("service-label")
        status_grid.attach(session_colon, 1, 1, 1, 1)
        
        self.session_status_label = Gtk.Label(label=self.session_status)
        self.session_status_label.set_halign(Gtk.Align.START)
        self.session_status_label.add_css_class("service-value")
        status_grid.attach(self.session_status_label, 2, 1, 1, 1)
        
        status_box.append(status_grid)
        debug("Status grid appended to status_box")
        debug("=== create_status_section completed ===")
        return status_box
        
    def create_controls_section(self):
        """Create the service control buttons section with framed layout"""
        debug("=== create_controls_section called ===")
        
        # Button size configuration
        btn_size_x = 230
        btn_size_y = 40
        frame_spacing = 30  # Space between the two button frames
        button_spacing = 12  # Space between buttons within each frame
        debug(f"Button config: {btn_size_x}x{btn_size_y}, frame_spacing: {frame_spacing}")
        
        # Main container for the two button frames
        controls_container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=frame_spacing)
        controls_container.set_halign(Gtk.Align.CENTER)
        debug("Created controls_container")
        
        # Left frame: Full service controls
        service_frame = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=button_spacing)
        service_frame.set_halign(Gtk.Align.CENTER)
        
        debug("Creating service control buttons")
        
        # Full services restart button
        start_button = Gtk.Button(label="Re/Start Toshy Services")
        start_button.set_size_request(btn_size_x, btn_size_y)
        start_button.set_hexpand(False)
        start_button.set_vexpand(False)
        start_button.add_css_class("suggested-action")
        start_button.set_tooltip_text("Start or restart both config and session monitor services")
        start_button.connect('clicked', self.on_start_services)
        
        # Disable button if not using systemd
        if not self.runtime.is_systemd:
            start_button.set_sensitive(False)
            start_button.set_tooltip_text("Service controls not available (systemd not detected)")
            debug("Re/Start Services button disabled - systemd not available")

        service_frame.append(start_button)
        
        # Full services stop button
        stop_button = Gtk.Button(label="Stop Toshy Services")
        stop_button.set_size_request(btn_size_x, btn_size_y)
        stop_button.set_hexpand(False)
        stop_button.set_vexpand(False)
        stop_button.add_css_class("destructive-action")
        stop_button.set_tooltip_text("Stop both config and session monitor services")
        stop_button.connect('clicked', self.on_stop_services)

        # Disable button if not using systemd
        if not self.runtime.is_systemd:
            stop_button.set_sensitive(False)
            stop_button.set_tooltip_text("Service controls not available (systemd not detected)")
            debug("Stop Services button disabled - systemd not available")

        service_frame.append(stop_button)
        
        controls_container.append(service_frame)
        
        # Right frame: Config-only controls
        config_frame = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=button_spacing)
        config_frame.set_halign(Gtk.Align.CENTER)
        
        debug("Creating config-only control buttons")
        
        # Config-only restart button
        config_start_button = Gtk.Button(label="Re/Start Config-Only")
        config_start_button.set_size_request(btn_size_x, btn_size_y)
        config_start_button.set_hexpand(False)
        config_start_button.set_vexpand(False)
        config_start_button.add_css_class("suggested-action")
        config_start_button.set_tooltip_text("Start only the config service (for testing)")
        config_start_button.connect('clicked', self.on_start_config_only)
        config_frame.append(config_start_button)
        
        # Config-only stop button
        config_stop_button = Gtk.Button(label="Stop Config-Only")
        config_stop_button.set_size_request(btn_size_x, btn_size_y)
        config_stop_button.set_hexpand(False)
        config_stop_button.set_vexpand(False)
        config_stop_button.add_css_class("destructive-action")
        config_stop_button.set_tooltip_text("Stop only the config service")
        config_stop_button.connect('clicked', self.on_stop_config_only)
        config_frame.append(config_stop_button)
        
        controls_container.append(config_frame)
        
        debug("=== create_controls_section completed ===")
        return controls_container
        
    def on_start_services(self, button):
        """Handle full services start button click"""
        debug("GTK-4: Starting all Toshy services...")
        self.service_manager.restart_services()
        
    def on_stop_services(self, button):
        """Handle full services stop button click"""
        debug("GTK-4: Stopping all Toshy services...")
        self.service_manager.stop_services()
        
    def on_start_config_only(self, button):
        """Handle config-only start button click"""
        debug("GTK-4: Starting Toshy config-only...")
        self.service_manager.restart_config_only()
        
    def on_stop_config_only(self, button):
        """Handle config-only stop button click"""
        debug("GTK-4: Stopping Toshy config-only...")
        self.service_manager.stop_config_only()
        
    def update_service_status(self, config_status, session_status):
        """
        Update service status labels (called by monitoring system)
        
        Args:
            config_status: Current config service status ('Active', 'Inactive', 'Unknown')
            session_status: Current session monitor status ('Active', 'Inactive', 'Unknown')
        """
        self.config_status = config_status
        self.session_status = session_status
        
        # Update labels on the main thread
        def update_labels():
            self.config_status_label.set_text(config_status)
            self.session_status_label.set_text(session_status)
            return False  # Don't repeat
            
        GLib.idle_add(update_labels)

    def show_help_dialog(self, title, text):
        """Show help dialog using centralized HelpDialog class"""
        if not self.parent_window:
            return
        
        from toshy_gui.gui.help_dialog_gtk4 import HelpDialog
        dialog = HelpDialog(self.parent_window, title, text)
        dialog.present()
