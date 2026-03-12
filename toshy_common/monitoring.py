__version__ = "20260311"

import time
import threading
import subprocess
try:
    import dbus
except ModuleNotFoundError:
    dbus = None

from toshy_common.logger import debug, error


class SettingsMonitor:
    """
    Monitors settings changes and notifies via callback.
    
    Watches for changes in the Settings object and calls a callback
    when changes are detected. The callback is responsible for
    updating the UI in the appropriate way for each application.
    """
    
    def __init__(self, settings_obj, on_settings_changed_callback):
        """
        Initialize the settings monitor.
        
        Args:
            settings_obj: Settings object to monitor
            on_settings_changed_callback: Function to call when settings change
        """
        self.settings_obj = settings_obj
        self.on_settings_changed = on_settings_changed_callback
        self.last_settings_list = self._get_settings_list()
        self.monitoring_thread = None
        self.stop_monitoring = False

    def _get_settings_list(self):
        """Get all settings as a list of tuples for comparison."""
        # Get all attributes from the object
        all_attributes = [attr for attr in dir(self.settings_obj) 
                            if not callable(getattr(self.settings_obj, attr)) and 
                            not attr.startswith("__")]
        
        # Filter out attributes that are not strings, booleans, or integers
        filtered_attributes = [attr for attr in all_attributes 
                                if isinstance(getattr(self.settings_obj, attr), (str, bool, int))]
        
        # Create a list of tuples with attribute name and value pairs
        settings_list = [(attr, getattr(self.settings_obj, attr)) for attr in filtered_attributes]
        return settings_list

    def _monitor_loop(self):
        """Main monitoring loop that runs in a separate thread."""
        while not self.stop_monitoring:
            time.sleep(1)
            current_settings = self._get_settings_list()
            
            if self.last_settings_list != current_settings:
                debug("Settings change detected in monitor thread")
                
                # Show changes in debug output
                for (old_name, old_val), (new_name, new_val) in zip(self.last_settings_list, current_settings):
                    if old_val != new_val and old_name == new_name:
                        debug(f"  {old_name}: {old_val} -> {new_val}")
                
                # Notify the callback
                self.on_settings_changed()
                self.last_settings_list = current_settings

    def start_monitoring(self):
        """Start monitoring settings changes in a background thread."""
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            debug("Settings monitoring is already running")
            return
            
        self.stop_monitoring = False
        self.monitoring_thread = threading.Thread(target=self._monitor_loop)
        self.monitoring_thread.daemon = True
        self.monitoring_thread.start()
        debug("Settings monitoring started")

    def stop_monitoring_thread(self):
        """Stop the monitoring thread."""
        self.stop_monitoring = True
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=2)
        debug("Settings monitoring stopped")


class ServiceMonitor:
    """
    Monitors Toshy systemd services status via D-Bus and notifies via callback.
    
    Watches the status of Toshy config and session monitor services and calls
    a callback when status changes. The callback receives the current status
    of both services.
    """
    
    def __init__(self, on_status_changed_callback):
        """
        Initialize the service monitor.
        
        Args:
            on_status_changed_callback: Function to call when service status changes.
                                        Called with (config_status, session_monitor_status)
        """
        self.on_status_changed = on_status_changed_callback
        self.monitoring_thread = None
        self.stop_monitoring = False
        
        # Service names
        self.toshy_svc_sessmon = 'toshy-session-monitor.service'
        self.toshy_svc_config = 'toshy-config.service'
        
        # Status values
        self.svc_status_glyph_active = 'Active'
        self.svc_status_glyph_inactive = 'Inactive'
        self.svc_status_glyph_unknown = 'Unknown'

    def _monitor_loop(self):
        """Main monitoring loop that runs in a separate thread."""

        config_status = self.svc_status_glyph_unknown
        session_monitor_status = self.svc_status_glyph_unknown
        last_status_tuple = (None, None)

        # Try D-Bus approach first
        use_dbus = False
        session_bus = None
        systemd1_mgr_iface = None

        if dbus is not None:
            try:
                session_bus = dbus.SessionBus()
                systemd1_dbus_obj = session_bus.get_object(
                    'org.freedesktop.systemd1',
                    '/org/freedesktop/systemd1'
                )
                systemd1_mgr_iface = dbus.Interface(
                    systemd1_dbus_obj,
                    'org.freedesktop.systemd1.Manager'
                )
                use_dbus = True
                debug("Service monitor: using D-Bus to monitor systemd services.")
            except dbus.exceptions.DBusException as dbus_err:
                debug(f"Service monitor: D-Bus systemd1 not available, "
                        f"falling back to systemctl subprocess.\n\t{dbus_err}")
        else:
            debug("Service monitor: dbus module not available, "
                    "using systemctl subprocess.")

        config_unit_path        = None
        sessmon_unit_path       = None

        def get_service_states_via_dbus():
            """Get current service states via D-Bus."""
            nonlocal config_unit_path, sessmon_unit_path

            config_obj = session_bus.get_object(
                'org.freedesktop.systemd1', config_unit_path)
            config_iface = dbus.Interface(
                config_obj, 'org.freedesktop.DBus.Properties')
            config_state = str(config_iface.Get(
                'org.freedesktop.systemd1.Unit', 'ActiveState'))

            sessmon_obj = session_bus.get_object(
                'org.freedesktop.systemd1', sessmon_unit_path)
            sessmon_iface = dbus.Interface(
                sessmon_obj, 'org.freedesktop.DBus.Properties')
            sessmon_state = str(sessmon_iface.Get(
                'org.freedesktop.systemd1.Unit', 'ActiveState'))

            return (config_state, sessmon_state)

        def get_service_states_via_shell_cmd():
            """Get current service states via systemctl subprocess."""
            def _get_state(service_name):
                try:
                    result = subprocess.run(
                        ['systemctl', '--user', 'is-active', service_name],
                        capture_output=True, text=True, timeout=5
                    )
                    return result.stdout.strip()
                except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
                    return 'unknown'

            config_state = _get_state(self.toshy_svc_config)
            sessmon_state = _get_state(self.toshy_svc_sessmon)
            return (config_state, sessmon_state)

        time.sleep(0.6)  # Initial delay before starting monitoring

        while not self.stop_monitoring:

            if use_dbus:
                # D-Bus path: get unit paths if we don't have them
                if not config_unit_path or not sessmon_unit_path:
                    try:
                        config_unit_path = systemd1_mgr_iface.GetUnit(
                            self.toshy_svc_config)
                        sessmon_unit_path = systemd1_mgr_iface.GetUnit(
                            self.toshy_svc_sessmon)
                    except dbus.exceptions.DBusException as dbus_err:
                        debug(f'DBusException trying to get unit paths: {dbus_err}')
                        time.sleep(3)
                        continue

                try:
                    current_status_tuple = get_service_states_via_dbus()
                    config_state, sessmon_state = current_status_tuple
                except dbus.exceptions.DBusException as dbus_err:
                    debug(f'DBusException getting service states: {dbus_err}')
                    config_unit_path = None
                    sessmon_unit_path = None
                    time.sleep(2)
                    continue

            else:
                # Subprocess fallback path
                current_status_tuple = get_service_states_via_shell_cmd()
                config_state, sessmon_state = current_status_tuple

            # Convert states to status strings
            if config_state == "active":
                config_status = self.svc_status_glyph_active
            elif config_state in ("inactive", "deactivating"):
                config_status = self.svc_status_glyph_inactive
            else:
                config_status = self.svc_status_glyph_unknown

            if sessmon_state == "active":
                session_monitor_status = self.svc_status_glyph_active
            elif sessmon_state in ("inactive", "deactivating"):
                session_monitor_status = self.svc_status_glyph_inactive
            else:
                session_monitor_status = self.svc_status_glyph_unknown

            # Notify callback if status changed
            if current_status_tuple != last_status_tuple:
                debug(f"Service status changed: "
                        f"Config={config_status}, SessionMonitor={session_monitor_status}")
                self.on_status_changed(config_status, session_monitor_status)

            last_status_tuple = current_status_tuple
            time.sleep(2)  # Check every 2 seconds

    def start_monitoring(self):
        """Start monitoring service status in a background thread."""
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            debug("Service monitoring is already running")
            return
            
        self.stop_monitoring = False
        self.monitoring_thread = threading.Thread(target=self._monitor_loop)
        self.monitoring_thread.daemon = True
        self.monitoring_thread.start()
        debug("Service monitoring started")

    def stop_monitoring_thread(self):
        """Stop the monitoring thread."""
        self.stop_monitoring = True
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=2)
        debug("Service monitoring stopped")
