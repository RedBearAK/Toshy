import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GLib

from toshy_common.logger import debug
from toshy_common.settings_class import CAPS_LOCK_EXCLUSIVE_FLAGS

# Configuration for help button appearance
HELP_BUTTON_SIZE = 18   # Width and height in pixels - change here to resize all help buttons
COLUMN_SPACING   = 8    # Vertical gap (px) between rows within each column - lower = more compact
PANEL_MARGIN     = 12   # Outer top/bottom margin (px) of the whole panel

class SettingsPanel(Gtk.Box):
    """
    Settings controls panel for GTK-4 Toshy Preferences.
    
    Contains all the switches and radio buttons for configuring
    Toshy behavior, organized in a two-column layout.
    """
    
    def __init__(self, cnfg, runtime, parent_window=None):
        debug("=== SettingsPanel.__init__ called ===")
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=40)
        
        self.cnfg = cnfg  # Settings object
        self.runtime = runtime  # Runtime configuration
        self.parent_window = parent_window  # For help dialogs
        
        debug(f"SettingsPanel initialized with parent_window: {parent_window is not None}")
        debug(f"Barebones config: {runtime.barebones_config}")
        
        # Set up the panel layout
        self.setup_ui()
        
        # Add margins
        self.set_margin_top(PANEL_MARGIN)
        self.set_margin_bottom(PANEL_MARGIN)
        
        # Connect to realize signal to set up CSS when widget is ready
        self.connect('realize', self.on_realize)
        
        debug("=== SettingsPanel.__init__ completed ===")
        
    def on_realize(self, widget):
        """Set up CSS when widget is realized and has a display"""
        css_provider = Gtk.CssProvider()
        
        css_data = f"""
        .control-group-header {{
            font-size: 14px;
            font-weight: bold;
            color: alpha(currentColor, 0.7);
        }}
        .settings-help-button {{
            min-width: {HELP_BUTTON_SIZE}px;
            min-height: {HELP_BUTTON_SIZE}px;
            padding: 0px;
            font-size: 14px;
            font-weight: bold;
        }}
        .switch-control {{
            margin-right: 8px;
        }}
        .radio-control {{
            margin-right: 8px;
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
        """Set up the settings panel user interface"""
        debug("=== SettingsPanel.setup_ui called ===")
        
        # Left column - modifier key settings
        left_column = self.create_left_column()
        left_column.set_size_request(400, -1)  # Fixed width
        left_column.set_hexpand(False)  # Don't expand
        self.append(left_column)
        
        # Right column - numpad, media, option keys
        right_column = self.create_right_column()
        right_column.set_size_request(400, -1)  # Fixed width
        right_column.set_hexpand(False)  # Don't expand
        self.append(right_column)
        
        debug("=== SettingsPanel.setup_ui completed ===")
        
    def create_left_column(self):
        """Create the left column with modifier key settings"""
        debug("Creating left column...")

        column = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=COLUMN_SPACING)

        # Don't show these controls if using barebones config
        if self.runtime.barebones_config:
            debug("Barebones config - skipping left column controls")
            placeholder = Gtk.Label(label="Barebones configuration")
            placeholder.add_css_class("dim-label")
            column.append(placeholder)
            return column

        # Alt_Gr on Menu key switch
        altgr_menu_control = self.create_switch_with_help(
            "Alt_Gr on Menu key*",
            "altgr_on_menu_key",
            "Alt_Gr on Menu key",
            "Maps the PC laptop context menu key to act as Right Alt (Alt_Gr), recovering Alt_Gr where the keyboard's modifier layout would otherwise lose it"
        )
        column.append(altgr_menu_control)

        # Multi-language support switch
        multi_lang_control = self.create_switch_with_help(
            "Alt_Gr on Right Cmd key",
            "multi_lang",
            "Alt_Gr on Right Cmd key",
            "Restores access to the Level3/4 additional characters on non-US keyboards/layouts"
        )
        column.append(multi_lang_control)

        # CapsLock as Cmd switch
        caps_cmd_control = self.create_switch_with_help(
            "CapsLock is Cmd key",
            "Caps2Cmd",
            "CapsLock is Cmd key",
            "Modmap CapsLock to be Command key"
        )
        column.append(caps_cmd_control)

        # Multipurpose CapsLock switch
        caps_esc_control = self.create_switch_with_help(
            "Multipurpose CapsLock: Esc, Cmd",
            "Caps2Esc_Cmd",
            "Multipurpose CapsLock: Esc, Cmd",
            "Modmap CapsLock key to be:\n• Escape when tapped\n• Command key for hold/combo"
        )
        column.append(caps_esc_control)

        # Swap CapsLock and Control switch
        caps_ctrl_swap_control = self.create_switch_with_help(
            "Swap CapsLock and Control",
            "Caps2Ctrl_Swap",
            "Swap CapsLock and Control",
            "Swap the physical CapsLock and Left Control keys:\n"
            "• CapsLock acts as Left Control\n"
            "• Left Control acts as CapsLock\n\n"
            "Note: enabling this removes physical Left Control from Toshy's Cmd/Super scheme."
        )
        column.append(caps_ctrl_swap_control)

        # Multipurpose Enter switch
        enter_cmd_control = self.create_switch_with_help(
            "Multipurpose Enter: Enter, Cmd",
            "Enter2Ent_Cmd",
            "Multipurpose Enter: Enter, Cmd",
            "Modmap Enter key to be:\n• Enter when tapped\n• Command key for hold/combo"
        )
        column.append(enter_cmd_control)

        # Sublime Text 3 in VSCode switch
        st3_control = self.create_switch_with_help(
            "ST3 shortcuts in VSCode(s)",
            "ST3_in_VSCode",
            "ST3 shortcuts in VSCode(s)",
            "Use shortcuts from Sublime Text 3 in Visual Studio Code (and variants)"
        )
        column.append(st3_control)

        # Forced Numpad switch
        numpad_control = self.create_switch_with_help(
            "Forced Numpad*",
            "forced_numpad",
            "Forced Numpad",
            "Makes the numeric keypad always act like a Numpad, ignoring actual NumLock LED state.\n"
            "• NumLock key becomes \"Clear\" key (Escape)\n"
            "• Option+NumLock toggles NumLock OFF/ON\n\n"
            "(Fn+NumLock will also toggle NumLock state, but only on real Apple keyboards)\n\n"
            "Feature is enabled by default."
        )
        column.append(numpad_control)

        # Media Arrows Fix switch
        media_control = self.create_switch_with_help(
            "Media Arrows Fix",
            "media_arrows_fix",
            "Media Arrows Fix",
            "Converts arrow keys that have \"media\" functions when used with Fn key, into PgUp/PgDn/Home/End keys"
        )
        column.append(media_control)

        debug("Left column created")
        return column

    def create_right_column(self):
        """Create the right column with numpad, media, and option keys"""
        debug("Creating right column...")

        column = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=COLUMN_SPACING)

        # Don't show controls if using barebones config
        if self.runtime.barebones_config:
            debug("Barebones config - skipping right column controls")
            placeholder = Gtk.Label(label="Barebones configuration")
            placeholder.add_css_class("dim-label")
            column.append(placeholder)
            return column

        # Option-key special characters radio group
        optspec_control = self.create_optspec_radio_group()
        column.append(optspec_control)

        # Super Tap Passthru section header
        super_tap_header = Gtk.Label(label="Super Tap Passthru")
        super_tap_header.add_css_class("control-group-header")
        super_tap_header.set_halign(Gtk.Align.START)
        column.append(super_tap_header)

        # Multipurpose Left Opt switch
        l_opt_control = self.create_switch_with_help(
            "Multipurpose Left Opt: Super, Opt",
            "l_opt_is_sup_and_opt",
            "Multipurpose Left Opt: Super, Opt",
            "Modmap Left Option position key to be:\n• Super/Meta when tapped\n• Option key for hold/combo"
        )
        column.append(l_opt_control)

        # Multipurpose Left Cmd switch
        l_cmd_control = self.create_switch_with_help(
            "Multipurpose Left Cmd: Super, Cmd",
            "l_cmd_is_sup_and_cmd",
            "Multipurpose Left Cmd: Super, Cmd",
            "Modmap Left Command positionkey to be:\n• Super/Meta when tapped\n• Command key for hold/combo"
        )
        column.append(l_cmd_control)

        debug("Right column created")
        return column

    def create_bottom_section(self):
        """Create the bottom section with version info and theme control"""
        debug("Creating bottom section...")
        
        bottom_container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)
        bottom_container.set_margin_top(10)
        
        # Left side - Version and app info
        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        info_box.set_halign(Gtk.Align.START)
        info_box.set_valign(Gtk.Align.END)
        
        # Get version from the module's __version__ if available
        try:
            import toshy_gui.main_gtk4 as main_module
            version = getattr(main_module, 'APP_VERSION', 'Unknown')
        except:
            version = 'Unknown'
            
        version_label = Gtk.Label(label=f"Version {version}")
        version_label.add_css_class("version-info")
        info_box.append(version_label)
        
        # Additional info
        info_label = Gtk.Label(label="Settings changes take effect immediately")
        info_label.add_css_class("info-text")
        info_box.append(info_label)
        
        bottom_container.append(info_box)
        
        # Spacer to push theme control to the right
        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        bottom_container.append(spacer)
        
        # Right side - Theme control
        theme_control = self.create_theme_control()
        theme_control.set_halign(Gtk.Align.END)
        theme_control.set_valign(Gtk.Align.END)
        bottom_container.append(theme_control)
        
        debug("Bottom section created")
        return bottom_container
        
    def create_theme_control(self):
        """Create the theme selection control (Auto/Light/Dark)"""
        debug("Creating theme control...")
        
        # Container for theme control with help button
        container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        
        # Theme selection container
        theme_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        
        # Label
        theme_label = Gtk.Label(label="Theme:")
        theme_label.add_css_class("control-label")
        theme_box.append(theme_label)
        
        # Dropdown for theme selection
        self.theme_dropdown = Gtk.DropDown()
        
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
            help_button.set_tooltip_text("Show help for theme selection")
            help_button.add_css_class("settings-help-button")
            
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
        
    def create_switch_with_help(self, label_text, setting_key, help_title, help_text):
        """Create a switch control with help button"""
        # Container for switch and help button
        container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        
        # The switch itself
        switch = Gtk.CheckButton(label=label_text)
        switch.add_css_class("switch-control")
        
        # Store setting key for callbacks
        switch.setting_key = setting_key
        
        # Connect to settings save
        switch.connect('toggled', self.on_switch_toggled)
        
        # Load initial value
        initial_value = getattr(self.cnfg, setting_key, False)
        switch.set_active(initial_value)
        
        # Store reference for external updates
        setattr(self, f"{setting_key}_switch", switch)
        
        container.append(switch)
        
        # Add expandable spacer to push help button to the right
        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        container.append(spacer)
        
        # Add help button if parent window available
        if self.parent_window:
            help_button = Gtk.Button(label="?")
            help_button.set_size_request(HELP_BUTTON_SIZE, HELP_BUTTON_SIZE)
            help_button.set_tooltip_text(f"Show help for {help_title}")
            help_button.add_css_class("settings-help-button")
            help_button.connect('clicked', lambda btn: self.show_help_dialog(help_title, help_text))
            container.append(help_button)
        
        return container
        
    def create_optspec_radio_group(self):
        """Create the Option-key special characters radio button group"""
        debug("Creating option-key radio group...")
        
        # Container for the whole group
        group_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        
        # Header with help button
        header_container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        
        header_label = Gtk.Label(label="Option-key Special Characters")
        header_label.add_css_class("control-group-header")
        header_container.append(header_label)
        
        # Add expandable spacer to push help button to the right
        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        header_container.append(spacer)
        
        # Help button for the group
        if self.parent_window:
            help_title = "Option-key Special Characters"
            help_text = (
                "Option-key special characters are available on all regular keys and "
                "punctuation keys when holding Option or Shift+Option. Choices are "
                "standard US layout, ABC Extended layout, or disabled. \n\nDefault is disabled."
            )
            
            help_button = Gtk.Button(label="?")
            help_button.set_size_request(HELP_BUTTON_SIZE, HELP_BUTTON_SIZE)
            help_button.set_tooltip_text("Show help for Option-key characters")
            help_button.add_css_class("settings-help-button")
            help_button.connect('clicked', lambda btn: self.show_help_dialog(help_title, help_text))
            header_container.append(help_button)
        
        group_container.append(header_container)
        
        # Radio buttons
        radio_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        radio_container.set_margin_start(20)  # Indent radio buttons
        
        # First radio button (creates the group)
        self.optspec_us_radio = Gtk.CheckButton(label="Option-key Special Characters (US)")
        self.optspec_us_radio.add_css_class("radio-control")
        self.optspec_us_radio.setting_value = "US"
        self.optspec_us_radio.connect('toggled', self.on_optspec_toggled)
        radio_container.append(self.optspec_us_radio)
        
        # Second radio button (part of same group)
        self.optspec_abc_radio = Gtk.CheckButton(label="Option-key Special Characters (ABC Extended)")
        self.optspec_abc_radio.add_css_class("radio-control")
        self.optspec_abc_radio.set_group(self.optspec_us_radio)  # Join the group
        self.optspec_abc_radio.setting_value = "ABC"
        self.optspec_abc_radio.connect('toggled', self.on_optspec_toggled)
        radio_container.append(self.optspec_abc_radio)
        
        # Third radio button (part of same group)
        self.optspec_disabled_radio = Gtk.CheckButton(label="Disable Option-key Special Characters*")
        self.optspec_disabled_radio.add_css_class("radio-control")
        self.optspec_disabled_radio.set_group(self.optspec_us_radio)  # Join the group
        self.optspec_disabled_radio.setting_value = "Disabled"
        self.optspec_disabled_radio.connect('toggled', self.on_optspec_toggled)
        radio_container.append(self.optspec_disabled_radio)
        
        # Load initial value
        current_value = getattr(self.cnfg, 'optspec_layout', 'US')
        if current_value == 'US':
            self.optspec_us_radio.set_active(True)
        elif current_value == 'ABC':
            self.optspec_abc_radio.set_active(True)
        elif current_value == 'Disabled':
            self.optspec_disabled_radio.set_active(True)
        
        group_container.append(radio_container)
        
        debug("Option-key radio group created")
        return group_container
        
    def on_switch_toggled(self, switch):
        """Handle switch toggle events"""
        setting_key = switch.setting_key
        new_value = switch.get_active()
        
        debug(f"Switch toggled: {setting_key} = {new_value}")

        # Save to settings
        setattr(self.cnfg, setting_key, new_value)

        # Caps Lock options are mutually exclusive: enabling one clears the others
        if new_value and setting_key in CAPS_LOCK_EXCLUSIVE_FLAGS:
            self.cnfg.clear_other_caps_flags(setting_key)
            for flag in CAPS_LOCK_EXCLUSIVE_FLAGS:
                if flag == setting_key:
                    continue
                other_switch = getattr(self, f"{flag}_switch", None)
                if other_switch is not None and other_switch.get_active():
                    other_switch.set_active(False)

        self.cnfg.save_settings()
            
    def on_optspec_toggled(self, radio):
        """Handle option-key radio button toggle events"""
        if radio.get_active():  # Only respond to the button being activated
            new_value = radio.setting_value
            debug(f"Option-key layout changed to: {new_value}")
            
            # Save to settings
            setattr(self.cnfg, 'optspec_layout', new_value)
            self.cnfg.save_settings()
            
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
        """Legacy method - now redirects to apply_theme"""
        # Get current theme setting and apply it
        current_theme = getattr(self.cnfg, 'gui_theme_mode', 'auto')
        self.apply_theme(current_theme)
            
    def update_theme(self):
        """Update the application theme"""
        # Import here to avoid circular imports
        import sv_ttk
        
        if self.cnfg.gui_dark_theme:
            sv_ttk.set_theme('dark')
            debug("Theme switched to dark")
        else:
            sv_ttk.set_theme('light')
            debug("Theme switched to light")
            
    def load_settings(self):
        """Load all settings from config and update controls"""
        debug("Loading settings into controls...")
        
        # Don't update during barebones config
        if self.runtime.barebones_config:
            debug("Barebones config - no settings to load")
            return
            
        # Update all switches using stored references
        switch_settings = [
            'altgr_on_menu_key', 'multi_lang', 'ST3_in_VSCode', 'Caps2Cmd', 'Caps2Esc_Cmd',
            'Caps2Ctrl_Swap', 'Enter2Ent_Cmd', 'forced_numpad', 'media_arrows_fix',
            'l_opt_is_sup_and_opt', 'l_cmd_is_sup_and_cmd'
        ]
        
        for setting_key in switch_settings:
            switch_attr = f"{setting_key}_switch"
            if hasattr(self, switch_attr):
                switch = getattr(self, switch_attr)
                current_value = getattr(self.cnfg, setting_key, False)
                # Only update if different to avoid triggering callbacks
                if switch.get_active() != current_value:
                    debug(f"Updating {setting_key} switch to {current_value}")
                    switch.set_active(current_value)
        
        # Update option-key radio buttons
        current_optspec = getattr(self.cnfg, 'optspec_layout', 'US')
        
        # Determine which radio should be active
        target_radio = None
        if current_optspec == 'US':
            target_radio = self.optspec_us_radio
        elif current_optspec == 'ABC':
            target_radio = self.optspec_abc_radio
        elif current_optspec == 'Disabled':
            target_radio = self.optspec_disabled_radio
            
        # Only update if different
        if target_radio and not target_radio.get_active():
            debug(f"Updating optspec radio to {current_optspec}")
            target_radio.set_active(True)
                
        debug("Settings loaded into controls")
        

    def show_help_dialog(self, title, text):
        """Show help dialog using centralized HelpDialog class"""
        if not self.parent_window:
            return
        
        from toshy_gui.gui.help_dialog_gtk4 import HelpDialog
        dialog = HelpDialog(self.parent_window, title, text)
        dialog.present()

# End of File #
