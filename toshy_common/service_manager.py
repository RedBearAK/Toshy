__version__ = '20260520'

import os
import time
import subprocess
from subprocess import DEVNULL

from toshy_common.logger import debug, error
from toshy_common.notification_manager import NotificationManager
from toshy_common.proc_launcher import launch_detached


class ServiceManager:
    """
    Manages Toshy systemd services and config-only operations.
    
    Provides common service control functionality shared between 
    GUI and tray applications.
    """
    
    def __init__(self, notification_manager: NotificationManager=None, 
                    icon_active=None, icon_inactive=None, icon_grayscale=None):
        """
        Initialize service manager.
        
        Args:
            notification_manager: NotificationManager instance for sending notifications
            icon_active: Icon to use for "services started" notifications
            icon_inactive: Icon to use for "services stopped" notifications
            icon_grayscale: Icon to use for "services disabled/unknown" notifications
        """
        self.ntfy               = notification_manager
        self.icon_active        = icon_active
        self.icon_inactive      = icon_inactive
        self.icon_grayscale     = icon_grayscale
        
        # Set up paths
        self.home_dir = os.path.expanduser("~")
        self.home_local_bin = os.path.join(self.home_dir, '.local', 'bin')
        
        # CLI command paths
        self.toshy_svcs_restart_cmd     = os.path.join(self.home_local_bin, 'toshy-services-restart')
        self.toshy_svcs_stop_cmd        = os.path.join(self.home_local_bin, 'toshy-services-stop')
        self.toshy_cfg_restart_cmd      = os.path.join(self.home_local_bin, 'toshy-config-restart')
        self.toshy_cfg_stop_cmd         = os.path.join(self.home_local_bin, 'toshy-config-stop')

    def restart_services(self):
        """
        (Re)Start Toshy services with CLI command.
        
        Starts both the config service and session monitor service.
        Shows notification if notification manager is available.
        """
        debug("Starting Toshy services...")

        if not launch_detached([self.toshy_svcs_restart_cmd], stdout=DEVNULL, stderr=DEVNULL):
            message = f"Failed to start Toshy services: {self.toshy_svcs_restart_cmd} not found"
            error(message)
            if self.ntfy:
                self.ntfy.send_notification(message, self.icon_grayscale)
            return

        time.sleep(3)

        message = 'Toshy systemd services (re)started.'
        if self.ntfy:
            self.ntfy.send_notification(message, self.icon_active)

        debug(message)

    def stop_services(self):
        """
        Stop Toshy services with CLI command.

        Stops both the config service and session monitor service.
        Shows notification if notification manager is available.
        """
        debug("Stopping Toshy services...")

        if not launch_detached([self.toshy_svcs_stop_cmd], stdout=DEVNULL, stderr=DEVNULL):
            message = f"Failed to stop Toshy services: {self.toshy_svcs_stop_cmd} not found"
            error(message)
            if self.ntfy:
                self.ntfy.send_notification(message, self.icon_grayscale)
            return

        time.sleep(3)

        message = 'Toshy systemd services stopped.'
        if self.ntfy:
            self.ntfy.send_notification(message, self.icon_inactive)

        debug(message)

    def restart_config_only(self):
        """
        Start the config service only (manual run mode).

        This is used for testing or when running config independently
        of the full systemd service setup.
        """
        debug("Starting Toshy config only...")

        if not launch_detached([self.toshy_cfg_restart_cmd], stdout=DEVNULL, stderr=DEVNULL):
            message = f"Failed to start Toshy config-only: {self.toshy_cfg_restart_cmd} not found"
            error(message)
            if self.ntfy:
                self.ntfy.send_notification(message, self.icon_grayscale)
            return

        time.sleep(3)

        message = 'Toshy config-only process (re)started.'
        debug(message)
        if self.ntfy:
            self.ntfy.send_notification(message, self.icon_active)

    def stop_config_only(self):
        """
        Stop the config service only (manual run mode).

        This stops the config service without affecting other services.
        """
        debug("Stopping Toshy config-only process...")

        if not launch_detached([self.toshy_cfg_stop_cmd], stdout=DEVNULL, stderr=DEVNULL):
            message = f"Failed to stop Toshy config-only: {self.toshy_cfg_stop_cmd} not found"
            error(message)
            if self.ntfy:
                self.ntfy.send_notification(message, self.icon_grayscale)
            return

        time.sleep(1)

        message = 'Toshy config-only process stopped.'
        debug(message)
        if self.ntfy:
            self.ntfy.send_notification(message, self.icon_inactive)

    def enable_services(self):
        """
        Enable all Toshy systemd services for autostart at login.
        
        Enables services in the correct order:
        1. Session monitor
        2. D-Bus services (e.g., COSMIC, KWin, Wlroots)
        3. Config service (last, as it depends on others)
        
        Raises:
            subprocess.CalledProcessError: If any systemctl command fails
        """
        # Service names (should match the tray app's service variables)
        services_to_enable = [
            'toshy-session-monitor.service',
            'toshy-cosmic-dbus.service', 
            'toshy-kwin-dbus.service',
            'toshy-wlroots-dbus.service',
            'toshy-config.service',  # Last, as it may depend on others
        ]
        
        enable_cmd_base = ["systemctl", "--user", "enable"]
        
        for service in services_to_enable:
            try:
                debug(f"Enabling service: {service}")
                subprocess.run(enable_cmd_base + [service], check=True)
            except subprocess.CalledProcessError as e:
                error(f"Failed to enable service {service}: {e}")
                raise  # Re-raise to let caller handle the error
                
        time.sleep(1)
        message = "Toshy services ENABLED. Will autostart at login."
        debug(message)
        if self.ntfy:
            self.ntfy.send_notification(message, self.icon_active)

    def disable_services(self):
        """
        Disable all Toshy systemd services from autostart at login.
        
        Disables services in reverse order (config first, then dependencies):
        1. Config service (first, as others support it)
        2. D-Bus services (e.g., COSMIC, KWin, Wlroots)
        3. Session monitor (last)
        
        Raises:
            subprocess.CalledProcessError: If any systemctl command fails
        """
        # Service names in reverse order for clean shutdown
        services_to_disable = [
            'toshy-config.service',  # First, as others support it
            'toshy-cosmic-dbus.service',
            'toshy-kwin-dbus.service', 
            'toshy-wlroots-dbus.service',
            'toshy-session-monitor.service',  # Last
        ]
        
        disable_cmd_base = ["systemctl", "--user", "disable"]
        
        for service in services_to_disable:
            try:
                debug(f"Disabling service: {service}")
                subprocess.run(disable_cmd_base + [service], check=True)
            except subprocess.CalledProcessError as e:
                error(f"Failed to disable service {service}: {e}")
                raise  # Re-raise to let caller handle the error
                
        time.sleep(1)
        message = "Toshy systemd services DISABLED. Will not autostart."
        debug(message)
        if self.ntfy:
            self.ntfy.send_notification(message, self.icon_inactive)

    def check_commands_exist(self):
        """
        Check if all required CLI commands exist.
        
        Returns:
            dict: Status of each command (True if exists, False otherwise)
        """
        commands = {
            'toshy-services-restart': self.toshy_svcs_restart_cmd,
            'toshy-services-stop': self.toshy_svcs_stop_cmd,
            'toshy-config-restart': self.toshy_cfg_restart_cmd,
            'toshy-config-stop': self.toshy_cfg_stop_cmd,
        }
        
        status = {}
        for name, path in commands.items():
            status[name] = os.path.exists(path) and os.access(path, os.X_OK)
            if not status[name]:
                debug(f"Command not found or not executable: {path}")
                
        return status
