import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GLib

from toshy_common.logger import debug

# Configuration for help button appearance
HELP_BUTTON_SIZE = 36  # Width and height in pixels - change here to resize all help buttons


class BottomPanel(Gtk.Box):
    """
    Bottom panel for GTK-4 Toshy Preferences.
    
    Contains version info on the left and theme control on the right.
    """
    
    def __init__(self, cnfg, parent_window=None):
        debug("=== BottomPanel.__init__ called ===")
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)
        
        # Add debug border (comment out this line to remove)
        # self.add_css_class("debug-border")
        
        self.cnfg = cnfg  # Settings object
        self.parent_window = parent_window  # For help dialogs
        
        debug(f"BottomPanel initialized with parent_window: {parent_window is not None}")
        
        # Set up the panel layout
        self.setup_ui()
        
        # Add margins (horizontal only - vertical gaps between panel sections
        # are controlled solely by the main window's section spacing)
        self.set_margin_start(20)
        self.set_margin_end(20)
        
        # Connect to realize signal to set up CSS when widget is ready
        self.connect('realize', self.on_realize)
        
        # Apply initial theme setting
        self.apply_initial_theme()
        
        debug("=== BottomPanel.__init__ completed ===")
        
    def on_realize(self, widget):
        """Set up CSS when widget is realized and has a display"""
        css_provider = Gtk.CssProvider()
        
        css_data = f"""
        .debug-border {{
            border: 2px solid red;
            background-color: alpha(red, 0.1);
        }}
        .bottom-help-button {{
            min-width: {HELP_BUTTON_SIZE}px;
            min-height: {HELP_BUTTON_SIZE}px;
            padding: 0px;
            font-size: 18px;
            font-weight: bold;
        }}
        .control-label {{
            font-size: 24px;
            font-weight: bold;
            margin-right: 8px;
        }}
        .version-info {{
            font-size: 14px;
            font-weight: bold;
            color: alpha(currentColor, 0.8);
        }}
        .info-text {{
            font-size: 20px;
            font-style: italic;
            color: alpha(currentColor, 0.6);
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
        """Set up the bottom panel user interface"""
        debug("=== BottomPanel.setup_ui called ===")
        
        # Natural height only - no forced minimum. The labels and theme
        # control define the panel height on their own.
        
        # Left side - Version and app info
        info_box = self.create_info_section()
        info_box.set_halign(Gtk.Align.START)
        info_box.set_valign(Gtk.Align.END)
        self.append(info_box)
        
        # Spacer to push theme control to the right
        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        self.append(spacer)
        
        # Right side - Theme control
        theme_control = self.create_theme_control()
        theme_control.set_halign(Gtk.Align.END)
        theme_control.set_valign(Gtk.Align.END)
        self.append(theme_control)
        
        debug("=== BottomPanel.setup_ui completed ===")
        
    def create_info_section(self):
        """Create the left side info section"""
        debug("Creating info section...")
        
        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        info_box.set_valign(Gtk.Align.END)  # Bottom-align the entire info box
        
        # Additional info
        info_label = Gtk.Label(label="Settings changes take effect immediately")
        info_label.set_halign(Gtk.Align.START)
        info_label.set_valign(Gtk.Align.END)
        info_label.add_css_class("info-text")
        info_box.append(info_label)
        
        # Get version from the module's __version__ if available
        try:
            from toshy_gui.main_gtk4 import __version__ as main_app_ver
        except:
            main_app_ver = 'Unknown'
            
        version_label = Gtk.Label(label=f"App Version {main_app_ver}")
        version_label.set_halign(Gtk.Align.START)
        version_label.set_valign(Gtk.Align.END)
        version_label.add_css_class("version-info")
        info_box.append(version_label)
        
        debug("Info section created")
        return info_box
        
    def create_theme_control(self):
        """Create the theme selection control (Auto/Light/Dark)"""
        debug("Creating theme control...")
        
        # Container for theme control with help button
        container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        container.set_valign(Gtk.Align.END)  # Bottom-align the entire theme control
        
        # Theme selection container
        theme_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        theme_box.set_valign(Gtk.Align.END)
        
        # Label
        theme_label = Gtk.Label(label="Theme:")
        theme_label.set_valign(Gtk.Align.END)
        theme_label.add_css_class("control-label")
        theme_box.append(theme_label)
        
        # Dropdown for theme selection
        self.theme_dropdown = Gtk.DropDown()
        self.theme_dropdown.set_size_request(150, -1)  # Fixed width to prevent layout shifts
        self.theme_dropdown.set_valign(Gtk.Align.END)
        
        # Create string list model for dropdown options
        theme_options = ["Auto (System)", "Light", "Dark"]
        string_list = Gtk.StringList()
        for option in theme_options:
            string_list.append(option)
        self.theme_dropdown.set_model(string_list)
        
        # Set initial selection based on current setting
        current_theme = getattr(self.cnfg, 'gui_theme_mode', 'auto')
        if current_theme == 'auto':
            self.theme_dropdown.set_selected(0)
        elif current_theme == 'light':
            self.theme_dropdown.set_selected(1)
        elif current_theme == 'dark':
            self.theme_dropdown.set_selected(2)
        else:
            self.theme_dropdown.set_selected(0)  # Default to auto
            
        # Connect to selection change
        self.theme_dropdown.connect('notify::selected', self.on_theme_changed)
        
        theme_box.append(self.theme_dropdown)
        container.append(theme_box)
        
        # Add help button
        if self.parent_window:
            help_button = Gtk.Button(label="?")
            help_button.set_size_request(HELP_BUTTON_SIZE, HELP_BUTTON_SIZE)
            help_button.set_valign(Gtk.Align.END)
            help_button.set_tooltip_text("Show help for theme selection")
            help_button.add_css_class("bottom-help-button")
            
            help_title = "Theme Selection"
            help_text = (
                "Choose how the Toshy Preferences window should appear:\n\n"
                "• Auto (System): Follow your system's light/dark mode setting\n"
                "• Light: Always use light theme\n"
                "• Dark: Always use dark theme\n\n"
                "This only affects the Toshy Preferences window, not your system theme."
            )
            
            help_button.connect('clicked', lambda btn: self.show_help_dialog(help_title, help_text))
            container.append(help_button)
            
        debug("Theme control created")
        return container
        
    def on_theme_changed(self, dropdown, pspec):
        """Handle theme dropdown selection change"""
        selected_index = dropdown.get_selected()
        
        if selected_index == 0:
            new_theme = 'auto'
        elif selected_index == 1:
            new_theme = 'light'
        elif selected_index == 2:
            new_theme = 'dark'
        else:
            new_theme = 'auto'
            
        # No-change guard: the initial set_selected at construction and
        # settings-monitor echoes fire this handler after cnfg already holds
        # the value; saving again would rewrite the DB and re-emit settings
        # in the config's verbose log.
        if getattr(self.cnfg, 'gui_theme_mode', None) == new_theme:
            return

        debug(f"Theme changed to: {new_theme}")
        
        # Save to settings
        setattr(self.cnfg, 'gui_theme_mode', new_theme)
        self.cnfg.save_settings()
        
        # Apply theme change
        self.apply_theme(new_theme)
        
    def apply_initial_theme(self):
        """Apply the initial theme setting when the panel is created"""
        current_theme = getattr(self.cnfg, 'gui_theme_mode', 'auto')
        debug(f"Applying initial theme: {current_theme}")
        self.apply_theme(current_theme)
        
    def apply_theme(self, theme_mode):
        """Apply the selected theme"""
        try:
            # Import here to avoid potential circular imports
            from gi.repository import Adw
            
            style_manager = Adw.StyleManager.get_default()
            
            if theme_mode == 'auto':
                style_manager.set_color_scheme(Adw.ColorScheme.DEFAULT)
                debug("Theme set to auto (follow system)")
            elif theme_mode == 'light':
                style_manager.set_color_scheme(Adw.ColorScheme.FORCE_LIGHT)
                debug("Theme set to light")
            elif theme_mode == 'dark':
                style_manager.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
                debug("Theme set to dark")
                
        except Exception as e:
            debug(f"Error applying theme: {e}")
            
    def update_theme(self):
        """Update theme dropdown from external settings change"""
        current_theme = getattr(self.cnfg, 'gui_theme_mode', 'auto')
        
        target_index = 0  # Default to auto
        if current_theme == 'auto':
            target_index = 0
        elif current_theme == 'light':
            target_index = 1
        elif current_theme == 'dark':
            target_index = 2
            
        # Only update if different to avoid triggering callbacks
        if self.theme_dropdown.get_selected() != target_index:
            debug(f"Updating theme dropdown to {current_theme}")
            self.theme_dropdown.set_selected(target_index)
            self.apply_theme(current_theme)
            

    def show_help_dialog(self, title, text):
        """Show help dialog using centralized HelpDialog class"""
        if not self.parent_window:
            return
        
        from toshy_gui.gui.help_dialog_gtk4 import HelpDialog
        dialog = HelpDialog(self.parent_window, title, text)
        dialog.present()
