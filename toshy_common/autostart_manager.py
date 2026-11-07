__version__ = '20261107'

import os
import shutil
import subprocess
from subprocess import DEVNULL

from toshy_common.logger import debug, error
from toshy_common.runtime_utils import ToshyRuntime


# Names of the XDG autostart entries Toshy manages in ~/.config/autostart.
# The tray icon entry is a copy processed by the desktop apps setup script
# (the '$HOME' placeholder replaced), so its link target is the processed
# copy in ~/.local/share/applications. The config autostart entry is static
# and is linked straight from the Toshy config folder, like the kickstart.
TRAY_ICON_DT_FILE_NAME      = 'Toshy_Tray.desktop'
CONFIG_AUTOSTART_DT_FILE_NAME = 'Toshy_Config_Autostart.desktop'

# Services whose 'enabled' state stands for "Autostart Toshy" on systemd
AUTOSTART_SERVICES = [
    'toshy-config.service',
    'toshy-session-monitor.service',
]


def is_service_enabled(service_name: str, runtime: ToshyRuntime) -> bool:
    """Check if a systemd user service is enabled. False when systemd is not the init."""

    if shutil.which('systemctl') and runtime.is_systemd:
        pass
    else:
        # If either 'systemctl' is missing or init is not 'systemd', just return False
        return False

    is_enabled_cmd_lst = ["systemctl", "--user", "is-enabled"]

    try:
        subprocess.run(is_enabled_cmd_lst + [service_name],
                        check=True, stdout=DEVNULL, stderr=DEVNULL)
        return True  # is-enabled succeeds
    except subprocess.CalledProcessError:
        return False  # is-enabled fails


def are_services_enabled(runtime: ToshyRuntime) -> bool:
    """True when every service behind the "Autostart Toshy" toggle is enabled."""
    return all(is_service_enabled(svc, runtime) for svc in AUTOSTART_SERVICES)


def _set_autostart_link(enable: bool, target_path: str, link_path: str, what: str):
    """Create or remove a symlink in the XDG autostart folder."""
    if enable:
        cmd_lst = ['ln', '-sf', target_path, link_path]
    else:
        cmd_lst = ['rm', '-f', link_path]
    try:
        os.makedirs(os.path.dirname(link_path), exist_ok=True)
        subprocess.run(cmd_lst, check=True)
        debug(f"{what} autostart {'enabled' if enable else 'disabled'}: '{link_path}'")
    except (subprocess.CalledProcessError, OSError) as err:
        error(f"Problem {'enabling' if enable else 'disabling'} {what} autostart:\n\t{err}")


def set_tray_icon_autostart(enable: bool, runtime: ToshyRuntime):
    """Create or remove the tray icon autostart entry (~/.config/autostart/Toshy_Tray.desktop)."""
    target_path = os.path.join(runtime.home_dir, '.local', 'share', 'applications',
                                TRAY_ICON_DT_FILE_NAME)
    link_path   = os.path.join(runtime.home_dir, '.config', 'autostart', TRAY_ICON_DT_FILE_NAME)
    _set_autostart_link(enable, target_path, link_path, 'Tray icon')


def set_config_autostart(enable: bool, runtime: ToshyRuntime):
    """Create or remove the config autostart entry for systems without systemd
    (~/.config/autostart/Toshy_Config_Autostart.desktop)."""
    target_path = os.path.join(runtime.config_dir, 'desktop', CONFIG_AUTOSTART_DT_FILE_NAME)
    link_path   = os.path.join(runtime.home_dir, '.config', 'autostart',
                                CONFIG_AUTOSTART_DT_FILE_NAME)
    _set_autostart_link(enable, target_path, link_path, 'Config')


# End of file #
