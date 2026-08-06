#!/usr/bin/env python3
__version__ = '20260805'


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


# Hand-rolled arg handling — intentionally NOT argparse. argparse defaults to
# allow_abbrev=True, which would silently accept '--al' as an abbreviation of
# '--all', which is the exact typo we want to reject. It would also restyle all
# of the usage output. For a script this small an explicit known-flag check is
# clearer and does exactly what we want.
known_flags         = {'--all', '-a', '--help', '-h'}
user_args           = sys.argv[1:]
unknown_args_lst    = [arg for arg in user_args if arg not in known_flags]


def _print_usage(out_file=sys.stdout):
    print('Usage: toshy_versions.py [--all]', file=out_file)
    print('  --all   also show detector package sub-modules and other detailed entries',
            file=out_file)


if '--help' in user_args or '-h' in user_args:
    _print_usage()
    sys.exit(0)

if unknown_args_lst:
    print(f"Error: unknown option(s): {', '.join(unknown_args_lst)}", file=sys.stderr)
    print(file=sys.stderr)
    _print_usage(sys.stderr)
    sys.exit(2)

show_all_modules    = '--all' in user_args or '-a' in user_args


# Files to parse for version info:

# ~/.config/toshy/toshy_config.py
# ~/.config/toshy/toshy_gui/main_gtk4.py
# ~/.config/toshy/toshy_gui/main_tkinter.py

    # ~/.config/toshy/toshy_common/terminal_menu/__init__.py
    # ~/.config/toshy/toshy_common/terminal_menu/tmenu_input.py
    # ~/.config/toshy/toshy_common/terminal_menu/tmenu_main.py
    # ~/.config/toshy/toshy_common/terminal_menu/tmenu_model.py
    # ~/.config/toshy/toshy_common/terminal_menu/tmenu_render.py
    # ~/.config/toshy/toshy_common/terminal_menu/tmenu_rgx.py
    # ~/.config/toshy/toshy_common/terminal_menu/tmenu_term.py

# ~/.config/toshy/toshy_tray.py

# ~/.config/toshy/toshy_common/env_context.py
# ~/.config/toshy/toshy_common/machine_context.py
# ~/.config/toshy/toshy_common/modifier_modes.py
# ~/.config/toshy/toshy_common/monitoring.py            # Monitors settings and services
# ~/.config/toshy/toshy_common/notification_manager.py
# ~/.config/toshy/toshy_common/overlay_context.py
# ~/.config/toshy/toshy_common/preference_items.py
# ~/.config/toshy/toshy_common/proc_launcher.py
# ~/.config/toshy/toshy_common/process_manager.py
# ~/.config/toshy/toshy_common/runtime_utils.py
# ~/.config/toshy/toshy_common/service_manager.py
# ~/.config/toshy/toshy_common/settings_class.py
# ~/.config/toshy/toshy_common/shared_device_context.py
# ~/.config/toshy/toshy_common/terminal_utils.py
# ~/.config/toshy/toshy_common/xkb_check.py

# ~/.config/toshy/toshy_common/kblayout_analyze.py
# ~/.config/toshy/toshy_common/kblayout_common.py
# ~/.config/toshy/toshy_common/kblayout_context.py

    # ~/.config/toshy/toshy_common/kblayout_detect/__init__.py
    # ~/.config/toshy/toshy_common/kblayout_detect/__main__.py
    # ~/.config/toshy/toshy_common/kblayout_detect/kbld_backend_base.py
    # ~/.config/toshy/toshy_common/kblayout_detect/kbld_registry.py
    # ~/.config/toshy/toshy_common/kblayout_detect/kbld_backend_cinnamon.py
    # ~/.config/toshy/toshy_common/kblayout_detect/kbld_backend_cosmic.py
    # ~/.config/toshy/toshy_common/kblayout_detect/kbld_backend_gnome.py
    # ~/.config/toshy/toshy_common/kblayout_detect/kbld_backend_kde.py
    # ~/.config/toshy/toshy_common/kblayout_detect/kbld_backend_wl_generic.py
    # ~/.config/toshy/toshy_common/kblayout_detect/kbld_backend_x11.py

# ~/.config/toshy/toshy_common/kblayout_setup.py
# ~/.config/toshy/toshy_common/kblayout_symtable.py

# These are shell scripts, not Python scripts
# ~/.config/toshy/scripts/tshysvc-config
# ~/.config/toshy/scripts/tshysvc-sessmon
# ~/.config/toshy/scripts/toshy-runtime-env.sh

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
terminal_menu_path      = os.path.join(toshy_dir_path,
                            'toshy_common', 'terminal_menu')        # package dir
tray_indicator_path     = os.path.join(toshy_dir_path,
                            'toshy_tray.py')

env_context_path        = os.path.join(toshy_dir_path,
                            'toshy_common', 'env_context.py')
machine_context_path    = os.path.join(toshy_dir_path,
                            'toshy_common', 'machine_context.py')
modifier_modes_path     = os.path.join(toshy_dir_path,
                            'toshy_common', 'modifier_modes.py')
notification_mgr_path   = os.path.join(toshy_dir_path,
                            'toshy_common', 'notification_manager.py')
overlay_context_path    = os.path.join(toshy_dir_path,
                            'toshy_common', 'overlay_context.py')
preference_items_path   = os.path.join(toshy_dir_path,
                            'toshy_common', 'preference_items.py')
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
kblayout_symtable_path  = os.path.join(toshy_dir_path,
                            'toshy_common', 'kblayout_symtable.py')

screenshots_pkg_path    = os.path.join(toshy_dir_path,
                            'toshy_common', 'screenshots')          # package dir

shortcut_detect_pkg_path = os.path.join(toshy_dir_path,
                            'toshy_common', 'shortcut_detect')      # package dir

spotlight_input_pkg_path = os.path.join(toshy_dir_path,
                            'toshy_common', 'spotlight_input')      # package dir

# These files are shell scripts, not Python scripts:
config_svc_path         = os.path.join(toshy_dir_path, 'scripts', 'tshysvc-config')
sessmon_svc_path        = os.path.join(toshy_dir_path, 'scripts', 'tshysvc-sessmon')
runtime_env_path        = os.path.join(toshy_dir_path, 'scripts', 'toshy-runtime-env.sh')

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


# Screenshots is a package; its per-module entries (below) show only with --all.
def _sshot_module(filename):
    return os.path.join(screenshots_pkg_path, filename)


# Shortcut Detection is a package; its per-module entries show only with --all.
def _sc_det_module(filename):
    return os.path.join(shortcut_detect_pkg_path, filename)


# Spotlight/Input is a package; its per-module entries show only with --all.
def _spli_module(filename):
    return os.path.join(spotlight_input_pkg_path, filename)


# Terminal Menu is a package; its per-module entries show only with --all.
def _tmenu_module(filename):
    return os.path.join(terminal_menu_path, filename)


components = [
    ("Config File",                 config_file_path),
    ("Preferences App (GTK4)",      preferences_app_gtk4),
    ("Preferences App (Tk)",        preferences_app_tk),
    ("Terminal Menu (pkg)",         terminal_menu_path),
    (None, None, True),             # Spacing (detailed output only)
    ("  TMenu: __init__",           _tmenu_module('__init__.py'),           True),
    ("  TMenu: input",              _tmenu_module('tmenu_input.py'),        True),
    ("  TMenu: main",               _tmenu_module('tmenu_main.py'),         True),
    ("  TMenu: model",              _tmenu_module('tmenu_model.py'),        True),
    ("  TMenu: render",             _tmenu_module('tmenu_render.py'),       True),
    ("  TMenu: rgx patterns",       _tmenu_module('tmenu_rgx.py'),          True),
    ("  TMenu: terminal ctrl",      _tmenu_module('tmenu_term.py'),         True),
    (None, None, True),             # Spacing (detailed output only)
    ("Tray Indicator",              tray_indicator_path),
    (None, None),                   # Spacing
    ("Environment Context",         env_context_path),
    ("Machine Context",             machine_context_path),
    ("Modifier Modes",              modifier_modes_path),
    ("Notification Manager",        notification_mgr_path),
    ("Overlay Context",             overlay_context_path),
    ("Preference Items",            preference_items_path),
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
    ("Kbd Layout Setup",            kblayout_setup_path),
    ("Kbd Layout Symbol Table",     kblayout_symtable_path),
    (None, None),                   # Spacing
    ("Screenshot Shortcuts (pkg)",  screenshots_pkg_path),
    (None, None, True),             # Spacing (detailed output only)
    ("  Sshot: __init__",           _sshot_module('__init__.py'),           True),
    ("  Sshot: __main__",           _sshot_module('__main__.py'),           True),
    ("  Sshot: command regexes",    _sshot_module('sshot_cmd_rgx.py'),      True),
    ("  Sshot: defaults",           _sshot_module('sshot_defaults.py'),     True),
    ("  Sshot: keymaps",            _sshot_module('sshot_keymaps.py'),      True),
    ("  Sshot: readers",            _sshot_module('sshot_readers.py'),      True),
    ("  Sshot: resolver",           _sshot_module('sshot_resolver.py'),     True),
    (None, None),                   # Spacing
    ("Shortcut Detection (pkg)",    shortcut_detect_pkg_path),
    (None, None, True),             # Spacing (detailed output only)
    ("  ScDet: __init__",           _sc_det_module('__init__.py'),           True),
    ("  ScDet: __main__",           _sc_det_module('__main__.py'),           True),
    ("  ScDet: accel normalizer",   _sc_det_module('sc_det_accel.py'),        True),
    ("  ScDet: accel regexes",      _sc_det_module('sc_det_accel_rgx.py'),    True),
    ("  ScDet: cmd fallback",       _sc_det_module('sc_det_fallback.py'),     True),
    ("  ScDet: diagnostics",        _sc_det_module('sc_det_diag.py'),         True),
    ("  ScDet: gsettings reader",   _sc_det_module('sc_det_gsettings.py'),    True),
    ("  ScDet: KDE rc reader",      _sc_det_module('sc_det_kde_rc.py'),       True),
    ("  ScDet: result model",       _sc_det_module('sc_det_result.py'),       True),
    ("  ScDet: Spices reader",      _sc_det_module('sc_det_spices.py'),       True),
    ("  ScDet: COSMIC reader",      _sc_det_module('sc_det_cosmic.py'),       True),
    ("  ScDet: COSMIC regexes",     _sc_det_module('sc_det_cosmic_rgx.py'),   True),
    ("  ScDet: xfconf reader",      _sc_det_module('sc_det_xfconf.py'),       True),
    (None, None),                   # Spacing
    ("Spotlight/Input (pkg)",       spotlight_input_pkg_path),
    (None, None, True),             # Spacing (detailed output only)
    ("  SpIn: __init__",            _spli_module('__init__.py'),              True),
    ("  SpIn: __main__",            _spli_module('__main__.py'),              True),
    ("  SpIn: defaults",            _spli_module('spli_defaults.py'),         True),
    ("  SpIn: keymaps",             _spli_module('spli_keymaps.py'),          True),
    ("  SpIn: readers",             _spli_module('spli_readers.py'),          True),
    ("  SpIn: resolver",            _spli_module('spli_resolver.py'),         True),
    (None, None),                   # Spacing
    ("SysD Svc: Keymapper Config",  config_svc_path),
    ("SysD Svc: Session Monitor",   sessmon_svc_path),
    ("Runtime Env Resolver",        runtime_env_path),
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
    # Format YYYYMMDD as YYYY.MM.DD for readability; pass anything else
    # through raw. A revision tag after the 8-digit date (letter suffix,
    # 'build02', 'beta', 'patch3', with or without a '.', '-' or '_'
    # separator) becomes one more dotted component, so hypothetical
    # future version paradigms still display cleanly:
    #   '20260804a'       -> '2026.08.04.a'
    #   '20260805-beta'   -> '2026.08.05.beta'
    #   '20260805_patch3' -> '2026.08.05.patch3'
    #   '20260805build02' -> '2026.08.05.build02'
    date_part = version_raw[:8]
    if len(date_part) == 8 and date_part.isdigit() and 2020 <= int(date_part[:4]) <= 2038:
        formatted_date = f"{date_part[:4]}.{date_part[4:6]}.{date_part[6:8]}"
        suffix = version_raw[8:].lstrip('.-_')
        if suffix:
            return f"{formatted_date}.{suffix}"
        return formatted_date
    return version_raw


def _raw_version_in_file(file_path):
    with open(file_path, 'r') as file:
        for line in file:
            # Extract from the Python style variable and the shell script style
            # variables (the runtime env script uses a unique name because it
            # is sourced, and must not clobber the caller's SCRIPT_VERSION).
            if line.startswith(('__version__', 'SCRIPT_VERSION',
                                'TOSHY_RUNTIME_ENV_VERSION')):
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

runtime_interp_path = os.path.realpath(sys.executable)
runtime_dir_env     = os.environ.get('TOSHY_RUNTIME_DIR')

print()     # separate from command
# Print the keymapper info
print(f"  Keymapper version:  xwaykeyz {xwaykeyz_ver}")
# The interpreter path identifies the active runtime: the default venv on
# normal installs, or a Nix store path for externally managed runtimes.
print(f"  Python runtime:     {runtime_interp_path}")
if runtime_dir_env:
    print(f"  Resolved via:       {runtime_dir_env}")
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
