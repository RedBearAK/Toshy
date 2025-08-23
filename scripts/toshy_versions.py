#!/usr/bin/env python3
__version__ = '20250822'


# Script to get and print out the versions of various Toshy components. 

# Version info in modules is updated sporadically when relatively large
# changes are made to a component. 

import os
import sys
from xwaykeyz.version import __version__ as xwaykeyz_ver

home_dir                = os.path.expanduser('~')
toshy_dir_path          = os.path.join(home_dir, '.config', 'toshy')
toshy_common_dir_path   = os.path.join(toshy_dir_path, 'toshy_common')

if not os.path.exists(toshy_dir_path):
    print(f"Looks like you haven't installed Toshy yet. This won't work.")
    sys.exit(0)

this_file_path          = os.path.realpath(__file__)
this_file_dir           = os.path.dirname(this_file_path)
this_file_name          = os.path.basename(__file__)
parent_folder_path      = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

home_local_bin          = os.path.join(home_dir, '.local', 'bin')
run_tmp_dir             = os.environ.get('XDG_RUNTIME_DIR') or '/tmp'

sys.path.insert(0, toshy_dir_path)
sys.path.insert(0, toshy_common_dir_path)
# print(sys.path)


# Files to parse for version info:

# ~/.config/toshy/toshy_config.py
# ~/.config/toshy/toshy_gui/main_gtk4.py
# ~/.config/toshy/toshy_gui/main_tkinter.py
# ~/.config/toshy/toshy_tray.py

# ~/.config/toshy/toshy_common/env_context.py
# ~/.config/toshy/toshy_common/machine_context.py
# ~/.config/toshy/toshy_common/monitoring.py            # Monitors settings and services
# ~/.config/toshy/toshy_common/notification_manager.py
# ~/.config/toshy/toshy_common/process_manager.py
# ~/.config/toshy/toshy_common/runtime_utils.py
# ~/.config/toshy/toshy_common/service_manager.py
# ~/.config/toshy/toshy_common/settings_class.py
# ~/.config/toshy/toshy_common/shared_device_context.py

# These two are shell scripts, not Python scrips
# ~/.config/toshy/scripts/tshysvc-config
# ~/.config/toshy/scripts/tshysvc-sessmon

# ~/.config/toshy/cosmic-dbus-service/toshy_cosmic_dbus_service.py
# ~/.config/toshy/kwin-dbus-service/toshy_kwin_dbus_service.py
# ~/.config/toshy/wlroots-dbus-service/toshy_wlroots_dbus_service.py

# ~/.config/toshy/kwin-dbus-service/toshy_kwin_script_setup.py
# ~/.config/toshy/scripts/toshy_versions.py



# Define all file paths as variables
config_file_path        = os.path.join(toshy_dir_path,
                            'toshy_config.py')
preferences_app_gtk4    = os.path.join(toshy_dir_path,
                            'toshy_gui', 'main_gtk4.py')
preferences_app_tk      = os.path.join(toshy_dir_path,
                            'toshy_gui', 'main_tkinter.py')
tray_indicator_path     = os.path.join(toshy_dir_path,
                            'toshy_tray.py')

env_context_path        = os.path.join(toshy_dir_path,
                            'toshy_common', 'env_context.py')
machine_context_path    = os.path.join(toshy_dir_path,
                            'toshy_common', 'machine_context.py')
notification_mgr_path   = os.path.join(toshy_dir_path,
                            'toshy_common', 'notification_manager.py')
process_mgr_path        = os.path.join(toshy_dir_path,
                            'toshy_common', 'process_manager.py')
runtime_utils_path      = os.path.join(toshy_dir_path,
                            'toshy_common', 'runtime_utils.py')
service_mgr_path        = os.path.join(toshy_dir_path,
                            'toshy_common', 'service_manager.py')
settings_mgr_path       = os.path.join(toshy_dir_path,
                            'toshy_common', 'settings_class.py')
svc_settings_mon        = os.path.join(toshy_dir_path,
                            'toshy_common', 'monitoring.py')
shared_device_path      = os.path.join(toshy_dir_path,
                            'toshy_common', 'shared_device_context.py')
terminal_utils_path     = os.path.join(toshy_dir_path,
                            'toshy_common', 'terminal_utils.py')

# These two files are shell scripts, not Python scripts:
config_svc_path         = os.path.join(toshy_dir_path,'scripts', 'tshysvc-config')
sessmon_svc_path        = os.path.join(toshy_dir_path, 'scripts', 'tshysvc-sessmon')

cosmic_dbus_path        = os.path.join(toshy_dir_path,
                            'cosmic-dbus-service', 'toshy_cosmic_dbus_service.py')
kwin_dbus_path          = os.path.join(toshy_dir_path,
                            'kwin-dbus-service', 'toshy_kwin_dbus_service.py')
wlroots_dbus_path       = os.path.join(toshy_dir_path,
                            'wlroots-dbus-service', 'toshy_wlroots_dbus_service.py')

kwin_script_path        = os.path.join(toshy_dir_path,
                            'kwin-dbus-service', 'toshy_kwin_script_setup.py')
versions_path           = os.path.join(toshy_dir_path,
                            'scripts', 'toshy_versions.py')


components = [
    ("Config File",                 config_file_path),
    ("Preferences App (GTK4)",      preferences_app_gtk4),
    ("Preferences App (Tk)",        preferences_app_tk),
    ("Tray Indicator",              tray_indicator_path),
    (None, None),  # Spacing
    ("Environment Context",         env_context_path),
    ("Machine Context",             machine_context_path),
    ("Notification Manager",        notification_mgr_path),
    ("Process Manager",             process_mgr_path),
    ("Runtime Utils",               runtime_utils_path),
    ("Service Manager",             service_mgr_path),
    ("Service/Settings Monitor",    svc_settings_mon),
    ("Settings Manager",            settings_mgr_path),
    ("Shared Device Context",       shared_device_path),
    ("Terminal Utils",              terminal_utils_path),
    (None, None),  # Spacing
    ("Keymapper Config Service",    config_svc_path),
    ("Session Monitor Service",     sessmon_svc_path),
    (None, None),  # Spacing
    ("D-Bus Service: COSMIC",       cosmic_dbus_path),
    ("D-Bus Service: KWin",         kwin_dbus_path),
    ("D-Bus Service: Wlroots",      wlroots_dbus_path),
    (None, None),  # Spacing
    ("KWin Script Helper",          kwin_script_path),
    (None, None),  # Spacing
    ("Versions Script (Me)",        versions_path),
]


# Helper function to extract version from file content
def extract_version(file_path: str):
    try:
        with open(file_path, 'r') as file:
            for line in file:
                # Extract from both the Python style variable, and shell script style variable
                if line.startswith('__version__') or line.startswith('SCRIPT_VERSION'):
                    version_raw = line.split('=')[1].strip().strip('"').strip("'")
                    # Check if the version is all digits, has no dots, 
                    # and starts with a year in a rational range
                    if (version_raw.isdigit() and '.' not in version_raw and 
                            2020 <= int(version_raw[:4]) <= 2038):
                        # Format the version string for readability
                        return f"{version_raw[:4]}.{version_raw[4:6]}.{version_raw[6:]}"
                    # Return the raw version if it doesn't meet the criteria
                    else:
                        return version_raw
    except Exception as e:
        return f"Error reading file: {str(e)}"



# Update the formatting logic for tuples:
max_component_name_length = max(len(name) for name, path in components if name is not None)

print()     # separate from command
# Print the keymapper info
print(f"  Keymapper version:  xwaykeyz {xwaykeyz_ver}")
print()             # Separation from Toshy files version output
print(f"  {'Component'.ljust(max_component_name_length + 4)}Version")
print('  ' + '-' * (max_component_name_length + 14))

# Print version information
for component_name, path in components:
    if component_name is None:
        print()  # Blank line for spacing
        continue
    
    version = extract_version(path) if path else "N/A"
    if version:
        print(f"  {component_name.ljust(max_component_name_length + 4)}{version}")
    else:
        print(f"  {component_name.ljust(max_component_name_length + 4)}"
                "No version found or error reading file.")

print()     # separate from next command prompt
