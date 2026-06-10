#!/usr/bin/env python3
__version__ = '20260608'


# Script to get and print out the versions of various Toshy components. 

# Version info in modules is updated sporadically when relatively large
# changes are made to a component. 

import os
import sys
import glob

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

if '--help' in sys.argv or '-h' in sys.argv:
    print('Usage: toshy_versions.py [--all]')
    print('  --all   also show detector package sub-modules and other detailed entries')
    sys.exit(0)

show_all_modules = '--all' in sys.argv or '-a' in sys.argv


# Files to parse for version info:

# ~/.config/toshy/toshy_config.py
# ~/.config/toshy/toshy_gui/main_gtk4.py
# ~/.config/toshy/toshy_gui/main_tkinter.py
# ~/.config/toshy/toshy_tray.py

# ~/.config/toshy/toshy_common/env_context.py
# ~/.config/toshy/toshy_common/machine_context.py
# ~/.config/toshy/toshy_common/monitoring.py            # Monitors settings and services
# ~/.config/toshy/toshy_common/notification_manager.py
# ~/.config/toshy/toshy_common/overlay_context.py
# ~/.config/toshy/toshy_common/proc_launcher.py
# ~/.config/toshy/toshy_common/process_manager.py
# ~/.config/toshy/toshy_common/runtime_utils.py
# ~/.config/toshy/toshy_common/service_manager.py
# ~/.config/toshy/toshy_common/settings_class.py
# ~/.config/toshy/toshy_common/shared_device_context.py
# ~/.config/toshy/toshy_common/xkb_check.py

# ~/.config/toshy/toshy_common/kblayout_analyze.py
# ~/.config/toshy/toshy_common/kblayout_common.py
# ~/.config/toshy/toshy_common/kblayout_context.py
# ~/.config/toshy/toshy_common/kblayout_detect.py
# ~/.config/toshy/toshy_common/kblayout_setup.py

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
overlay_context_path    = os.path.join(toshy_dir_path,
                            'toshy_common', 'overlay_context.py')
proc_launcher_path      = os.path.join(toshy_dir_path,
                            'toshy_common', 'proc_launcher.py')
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
xkb_check_path          = os.path.join(toshy_dir_path,
                            'toshy_common', 'xkb_check.py')

kblayout_analyze_path   = os.path.join(toshy_dir_path,
                            'toshy_common', 'kblayout_analyze.py')
kblayout_common_path    = os.path.join(toshy_dir_path,
                            'toshy_common', 'kblayout_common.py')
kblayout_context_path   = os.path.join(toshy_dir_path,
                            'toshy_common', 'kblayout_context.py')
kblayout_detect_path    = os.path.join(toshy_dir_path,
                            'toshy_common', 'kblayout_detect')      # package dir now
kblayout_setup_path     = os.path.join(toshy_dir_path,
                            'toshy_common', 'kblayout_setup.py')

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


# Detector is a package now; its per-module entries (below) show only with --all.
def _kbld_module(filename):
    return os.path.join(kblayout_detect_path, filename)


components = [
    ("Config File",                 config_file_path),
    ("Preferences App (GTK4)",      preferences_app_gtk4),
    ("Preferences App (Tk)",        preferences_app_tk),
    ("Tray Indicator",              tray_indicator_path),
    (None, None),                   # Spacing
    ("Environment Context",         env_context_path),
    ("Machine Context",             machine_context_path),
    ("Notification Manager",        notification_mgr_path),
    ("Overlay Context",             overlay_context_path),
    ("Process Launcher",            proc_launcher_path),
    ("Process Manager",             process_mgr_path),
    ("Runtime Utils",               runtime_utils_path),
    ("Service Manager",             service_mgr_path),
    ("Service/Settings Monitor",    svc_settings_mon),
    ("Settings Manager",            settings_mgr_path),
    ("Shared Device Context",       shared_device_path),
    ("Terminal Utils",              terminal_utils_path),
    ("XKB Options Check",           xkb_check_path),
    (None, None),                   # Spacing
    ("Kbd Layout Analyzer",         kblayout_analyze_path),
    ("Kbd Layout Common",           kblayout_common_path),
    ("Kbd Layout Context",          kblayout_context_path),
    ("Kbd Layout Detection (pkg)",  kblayout_detect_path),
    (None, None, True),             # Spacing (detailed output only)
    ("  Detector: __init__",        _kbld_module('__init__.py'),                True),
    ("  Detector: __main__",        _kbld_module('__main__.py'),                True),
    ("  Detector: base",            _kbld_module('kbld_backend_base.py'),       True),
    ("  Detector: registry",        _kbld_module('kbld_registry.py'),           True),
    (None, None, True),             # Spacing (detailed output only)
    ("  Detector: Cinnamon",        _kbld_module('kbld_backend_cinnamon.py'),   True),
    ("  Detector: COSMIC",          _kbld_module('kbld_backend_cosmic.py'),     True),
    ("  Detector: GNOME",           _kbld_module('kbld_backend_gnome.py'),      True),
    ("  Detector: KDE",             _kbld_module('kbld_backend_kde.py'),        True),
    ("  Detector: Wayland-generic", _kbld_module('kbld_backend_wl_generic.py'), True),
    ("  Detector: X11",             _kbld_module('kbld_backend_x11.py'),        True),
    (None, None, True),             # Spacing (detailed output only)
    ("Keyboard Layout Setup",       kblayout_setup_path),
    (None, None),                   # Spacing
    ("SysD Svc: Keymapper Config",  config_svc_path),
    ("SysD Svc: Session Monitor",   sessmon_svc_path),
    (None, None),                   # Spacing
    ("D-Bus Service: COSMIC",       cosmic_dbus_path),
    ("D-Bus Service: KWin",         kwin_dbus_path),
    ("D-Bus Service: Wlroots",      wlroots_dbus_path),
    (None, None),                   # Spacing
    ("KWin Script Helper",          kwin_script_path),
    (None, None),                   # Spacing
    ("Versions Script (Me)",        versions_path),
]


# Helper function to extract version from file content
def _format_version(version_raw):
    # Format YYYYMMDD as YYYY.MM.DD for readability; pass anything else through.
    if (version_raw.isdigit() and '.' not in version_raw and
            2020 <= int(version_raw[:4]) <= 2038):
        return f"{version_raw[:4]}.{version_raw[4:6]}.{version_raw[6:]}"
    return version_raw


def _raw_version_in_file(file_path):
    with open(file_path, 'r') as file:
        for line in file:
            # Extract from both the Python style variable, and shell script style variable
            if line.startswith('__version__') or line.startswith('SCRIPT_VERSION'):
                return line.split('=')[1].strip().strip('"').strip("'")
    return None


def extract_version(file_path: str):
    try:
        # A package directory: report the newest version among its modules.
        if os.path.isdir(file_path):
            raw_lst = []
            for module_path in sorted(glob.glob(os.path.join(file_path, '*.py'))):
                raw = _raw_version_in_file(module_path)
                if raw is not None:
                    raw_lst.append(raw)
            if not raw_lst:
                return None
            return _format_version(max(raw_lst))

        raw = _raw_version_in_file(file_path)
        if raw is None:
            return None
        return _format_version(raw)
    except Exception as e:
        return f"Error reading file: {str(e)}"



# Unpack an entry into (name, path, detail_only), tolerating 2- or 3-tuples.
def _entry_fields(entry):
    name = entry[0]
    path = entry[1] if len(entry) > 1 else None
    detail_only = entry[2] if len(entry) > 2 else False
    return name, path, detail_only


def _is_shown(name, detail_only):
    return name is not None and not (detail_only and not show_all_modules)


# Width is computed over only the rows that will actually print.
max_component_name_length = max(
    len(name) for name, path, detail_only in (_entry_fields(e) for e in components)
    if _is_shown(name, detail_only)
)

print()     # separate from command
# Print the keymapper info
print(f"  Keymapper version:  xwaykeyz {xwaykeyz_ver}")
print()             # Separation from Toshy files version output
print(f"  {'Component'.ljust(max_component_name_length + 4)}Version")
print('  ' + '-' * (max_component_name_length + 14))

# Print version information
for entry in components:
    component_name, path, detail_only = _entry_fields(entry)
    if detail_only and not show_all_modules:
        continue
    if component_name is None:
        print()  # Blank line for spacing
        continue
    if not isinstance(component_name, str):        # narrow type to str for ljust() below
        raise TypeError(
            f"component_name should be str, got "
            f"{type(component_name).__name__}: {component_name!r}")

    version = extract_version(path) if path else "N/A"
    if version:
        print(f"  {component_name.ljust(max_component_name_length + 4)}{version}")
    else:
        print(f"  {component_name.ljust(max_component_name_length + 4)}"
                "No version found or error reading file.")

if not show_all_modules:
    print()
    print("  Use --all to show more detailed sub-module versions.")

print()     # separate from next command prompt

# End of File #
