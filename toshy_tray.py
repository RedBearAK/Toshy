#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__version__ = '20260101'

# Indicator tray icon menu app for Toshy, using pygobject/gi
TOSHY_PART      = 'tray'   # CUSTOMIZE TO SPECIFIC TOSHY COMPONENT! (gui, tray, config)
TOSHY_PART_NAME = 'Toshy Tray Icon App'
APP_VERSION     = __version__

# -------- COMMON COMPONENTS --------------------------------------------------

import os
import sys
import time
import shutil
import threading
import subprocess

from subprocess import DEVNULL, PIPE


# Check for accessibility support before importing GTK
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


if not is_a11y_available():
    os.environ['GTK_A11Y'] = 'none'
    os.environ['NO_AT_BRIDGE'] = '1'

# Initialize Toshy runtime before other imports
from toshy_common.runtime_utils import initialize_toshy_runtime
runtime = initialize_toshy_runtime()

# Local imports
import toshy_common.terminal_utils as term_utils
from toshy_common import logger
from toshy_common.logger import *
from toshy_common.env_context import EnvironmentInfo
from toshy_common.settings_class import Settings
from toshy_common.process_manager import ProcessManager
from toshy_common.service_manager import ServiceManager
from toshy_common.monitoring import SettingsMonitor, ServiceMonitor

# Make process manager global
process_mgr = None

logger.FLUSH        = True
logger.VERBOSE      = False



###############################################################################
# -------- TOSHY TRAY SPECIFIC COMPONENTS -------------------------------------
###############################################################################

# What we need for the indicator tray icon and menu
import gi.repository
gi.require_version('Gtk', '3.0')

try:
    gi.require_version('AyatanaAppIndicator3', '0.1')
    from gi.repository import AyatanaAppIndicator3 as AppIndicator3
except (ValueError, ImportError) as e:
    # debug(f'ImportError: Falling back on AppIndicator3 instead of AyatanaAppIndicator3.')
    gi.require_version('AppIndicator3', '0.1')
    from gi.repository import AppIndicator3

from gi.repository import Gtk, GLib


# Define some globals for the commands run by menu items

# assets_path         = os.path.join(current_folder_path, 'assets')
# icon_file_active    = os.path.join(assets_path, "toshy_app_icon_rainbow.svg")
# icon_file_grayscale = os.path.join(assets_path, "toshy_app_icon_rainbow_inverse_grayscale.svg")
# icon_file_inverse   = os.path.join(assets_path, "toshy_app_icon_rainbow_inverse.svg")

# Fix for Solus Budgie failing to show proper icons when using full path. Use base file name string.
# Icon files will all be copied into the local-share-icons location to make this work. 
icon_file_active                = "toshy_app_icon_rainbow"
icon_file_grayscale             = "toshy_app_icon_rainbow_inverse_grayscale"
icon_file_inverse               = "toshy_app_icon_rainbow_inverse"


DISTRO_ID       = None
DISTRO_VER      = None
VARIANT_ID      = None
SESSION_TYPE    = None
DESKTOP_ENV     = None
DE_MAJ_VER      = None
WINDOW_MGR      = None


def check_environment():
    """Retrieve the current environment from EnvironmentInfo class"""
    global DISTRO_ID, DISTRO_VER, VARIANT_ID, SESSION_TYPE, DESKTOP_ENV, DE_MAJ_VER, WINDOW_MGR

    env_ctxt_getter = EnvironmentInfo()
    env_info_dct    = env_ctxt_getter.get_env_info()

    DISTRO_ID       = str(env_info_dct.get('DISTRO_ID',      'keymissing')).casefold()
    DISTRO_VER      = str(env_info_dct.get('DISTRO_VER',     'keymissing')).casefold()
    VARIANT_ID      = str(env_info_dct.get('VARIANT_ID',     'keymissing')).casefold()
    SESSION_TYPE    = str(env_info_dct.get('SESSION_TYPE',   'keymissing')).casefold()
    DESKTOP_ENV     = str(env_info_dct.get('DESKTOP_ENV',    'keymissing')).casefold()
    DE_MAJ_VER      = str(env_info_dct.get('DE_MAJ_VER',     'keymissing')).casefold()
    WINDOW_MGR      = str(env_info_dct.get('WINDOW_MGR',     'keymissing')).casefold()


# Populate environment globals at module load time
check_environment()



# =============================================================================
# ENVIRONMENT-SPECIFIC ADJUSTMENTS
# =============================================================================

def show_cinnamon_wayland_warning():
    """
    Show async warning dialog about Cinnamon Wayland tray menu bugs.
    
    Uses zenity in a non-blocking subprocess so it doesn't delay app startup.
    """
    zenity_cmd = shutil.which('zenity')
    if not zenity_cmd:
        # Fall back to just logging if zenity isn't available
        error("Cinnamon Wayland has known bugs affecting tray icon menus.")
        return

    warning_title = "Cinnamon Wayland: Known Tray Menu Bugs"

    warning_text = (
        "Cinnamon's Wayland session has bugs affecting tray icon menus:\n\n"
        "• Menu appears in wrong location (top-left instead of near icon)\n"
        "• Menu stops appearing after first use\n\n"
        "This is a Cinnamon compositor bug, not a Toshy issue.\n\n"
        "<b>Alternatives:</b>\n"
        "• Use the Toshy Preferences app instead (has all the same options)\n"
        "• Restart the tray icon via app menu: \"Toshy Tray Icon\"\n"
        "• From terminal: <tt>nohup toshy-tray &amp;</tt> (allows closing terminal)"
    )

    cmd_lst = [
        zenity_cmd,
        '--warning',
        '--title', warning_title,
        '--text', warning_text,
        '--width', '500',
        '--no-wrap',
    ]

    # Run async (non-blocking) so the tray app continues loading
    try:
        subprocess.Popen(cmd_lst, stdout=DEVNULL, stderr=DEVNULL)
    except OSError as e:
        error(f"Failed to show Cinnamon Wayland warning dialog: {e}")


# Cinnamon Wayland: Show warning about known tray menu bugs
if DESKTOP_ENV == 'cinnamon' and SESSION_TYPE == 'wayland':
    show_cinnamon_wayland_warning()


# COSMIC: Desktop environment messes with tray icon, so use 'grayscale' icon for all states
if DESKTOP_ENV == 'cosmic':
    icon_file_active    = icon_file_grayscale
    icon_file_inverse   = icon_file_grayscale


loop = None

# Settings class object setup
config_dir_path = runtime.config_dir
cnfg = Settings(config_dir_path)
cnfg.watch_database()   # start watching the preferences file for changes

# Notification handler object setup
from toshy_common.notification_manager import NotificationManager
ntfy = NotificationManager(icon_file_active, title='Toshy Alert (Tray)')

# Service manager instance
service_manager = ServiceManager(ntfy, icon_file_active, icon_file_inverse, icon_file_grayscale)


sysctl_cmd      = f"{shutil.which('systemctl')}"
user_sysctl     = f'{sysctl_cmd} --user'


# -------- CREATE MENU --------------------------------------------------------

menu = Gtk.Menu()
# Add menu items here using Gtk.MenuItem and Gtk.ImageMenuItem

tray_indicator = AppIndicator3.Indicator.new(
    "Toshy Tray Icon Undefined",
    icon_name=icon_file_grayscale,
    category=AppIndicator3.IndicatorCategory.APPLICATION_STATUS)
tray_indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
tray_indicator.set_menu(menu)
tray_indicator.set_title("Toshy Status Indicator") # try to set what might show in tooltip



# -------- MENU ACTION FUNCTIONS ----------------------------------------------


def fn_open_preferences(widget):
    # First check if toshy-gui exists
    toshy_gui_cmd = shutil.which('toshy-gui')
    if not toshy_gui_cmd:
        _ntfy_icon = icon_file_inverse
        _ntfy_msg = ("The 'toshy-gui' utility is missing.\r"
                    "Please check your installation.")
        ntfy.send_notification(_ntfy_msg, _ntfy_icon, urgency='critical')
        _error_msg = ("The 'toshy-gui' utility is missing.\n"
                    "     Please check your installation.")
        error(f"{_error_msg}")
        return

    # Launch the process
    process = subprocess.Popen([toshy_gui_cmd], stdout=PIPE, stderr=PIPE)

    # Wait a short time to see if it exits immediately
    time.sleep(1)

    # Check if it's still running
    return_code = process.poll()

    if return_code is not None:
        # Process has already terminated
        stderr = process.stderr.read().decode()
        stdout = process.stdout.read().decode()

        _ntfy_icon = icon_file_inverse
        _ntfy_msg = (f"'toshy-gui' exited too quickly (code {return_code}).\r"
                    f"Error: {stderr.strip() if stderr else 'No error output'}")
        ntfy.send_notification(_ntfy_msg, _ntfy_icon, urgency='critical')

        _error_msg = (f"'toshy-gui' exited too quickly with code {return_code}.\n"
                    f"     Error: {stderr.strip() if stderr else 'No error output'}")
        error(f"{_error_msg}")
        return

    # Process is running normally
    return


def fn_open_config_folder(widget):

    xdg_open_cmd = shutil.which('xdg-open')
    if not xdg_open_cmd:
        _ntfy_icon = icon_file_inverse
        _ntfy_msg = ("The 'xdg-open' utility is missing.\r"
                        "Try installing 'xdg-utils' package.")
        ntfy.send_notification(_ntfy_msg, _ntfy_icon, urgency='critical')
        _error_msg = ("The 'xdg-open' utility is missing.\n"
                        "     Try installing 'xdg-utils' package.")
        error(f"{_error_msg}")
        return

    # Sometimes xdg-open script is unpatched for Plasma 6 (e.g., Leap 16), so use kde-open instead
    kde_open_cmd = shutil.which('kde-open')
    if DESKTOP_ENV == 'kde' and DE_MAJ_VER == '6' and kde_open_cmd:
        xdg_open_cmd = kde_open_cmd

    try:
        subprocess.Popen([xdg_open_cmd, runtime.config_dir])
    except FileNotFoundError as e:
        error('File not found. I have no idea how this error is possible.')
        error(e)


def fn_show_services_log(widget):
    try:
        term_utils.run_cmd_lst_in_terminal(['toshy-services-log'], desktop_env=DESKTOP_ENV)
    except term_utils.TerminalNotFoundError as term_err:
        # If we reach this, we failed to find a terminal app to use, so show a notification.
        _ntfy_icon_file = icon_file_inverse  # predefined path to icon file
        _ntfy_msg = term_err
        ntfy.send_notification(_ntfy_msg, _ntfy_icon_file)



def fn_remove_tray_icon(widget):
    global loop
    process_mgr.remove_lockfile()
    loop.quit()
    pkill_cmd = shutil.which('pkill')
    os.system(f'{pkill_cmd} -f "toshy_tray.py"')
    # Gtk.main_quit()
    sys.exit(0)


def set_item_active_thread_safe(menu_item, state=True):
    """Set menu item's active state (thread-safe version)"""
    
    def do_set_active():
        menu_item.set_active(state)
        return False  # Don't repeat
    
    # If we're in the main thread, set directly
    if threading.current_thread() is threading.main_thread():
        menu_item.set_active(state)
    else:
        # Schedule for main thread
        GLib.idle_add(do_set_active)


def show_cinnamon_wayland_warning():
    """
    Show async warning dialog about Cinnamon Wayland tray menu bugs.
    
    Uses zenity in a non-blocking subprocess so it doesn't delay app startup.
    """
    zenity_cmd = shutil.which('zenity')
    if not zenity_cmd:
        # Fall back to just logging if zenity isn't available
        error("Cinnamon Wayland has known bugs affecting tray icon menus.")
        return

    warning_title = "Cinnamon Wayland: Known Tray Menu Bugs"

    warning_text = (
        "Cinnamon's Wayland session has bugs affecting tray icon menus:\n\n"
        "• Menu appears in wrong location (top-left instead of near icon)\n"
        "• Menu stops appearing after first use\n\n"
        "This is a Cinnamon compositor bug, not a Toshy issue.\n\n"
        "<b>Alternatives:</b>\n"
        "• Use the Toshy Preferences app instead (has all the same options)\n"
        "• Restart the tray icon via app menu: \"Toshy Tray Icon\"\n"
        "• From terminal: <tt>nohup toshy-tray &amp;</tt> (allows closing terminal)"
    )

    cmd_lst = [
        zenity_cmd,
        '--warning',
        '--title', warning_title,
        '--text', warning_text,
        '--width', '500',
        '--no-wrap',
    ]

    # Run async (non-blocking) so the tray app continues loading
    try:
        subprocess.Popen(cmd_lst, stdout=DEVNULL, stderr=DEVNULL)
    except OSError as e:
        error(f"Failed to show Cinnamon Wayland warning dialog: {e}")



# -------- MENU ITEMS --------------------------------------------------

if runtime.is_systemd:
    services_label_item = Gtk.MenuItem(label=" ---- Services Status ---- ")
    services_label_item.set_sensitive(False)
    menu.append(services_label_item)

    toshy_config_status_item = Gtk.MenuItem(    label="      Config: (?)")
    toshy_config_status_item.set_sensitive(False)
    menu.append(toshy_config_status_item)

    session_monitor_status_item = Gtk.MenuItem( label="     SessMon: (?)")
    session_monitor_status_item.set_sensitive(False)
    menu.append(session_monitor_status_item)


def is_service_enabled(service_name):
    """Check if a user service is enabled using systemctl."""

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
        return False  # is-enabled fails, service is disabled or not found


toshy_svc_config_unit_enabled   = is_service_enabled("toshy-config.service")
toshy_svc_sessmon_unit_enabled  = is_service_enabled("toshy-session-monitor.service")


def fn_toggle_toshy_svcs_autostart(widget):
    """Check the status of Toshy services, flip the status, change the menu item label"""
    global toshy_svc_config_unit_enabled, toshy_svc_sessmon_unit_enabled

    if shutil.which('systemctl') and runtime.is_systemd:
        pass
    else:
        # If either 'systemctl' is missing or init is not 'systemd', immediately return
        return

    try:
        if widget.get_active():
            service_manager.enable_services()
        else:
            service_manager.disable_services()
    except subprocess.CalledProcessError as proc_err:
        debug(f"Error toggling Toshy systemd user services: {proc_err}")

    time.sleep(0.5)


if runtime.is_systemd:

    separator_above_svcs_item = Gtk.SeparatorMenuItem()
    menu.append(separator_above_svcs_item)  #-------------------------------------#

    restart_toshy_svcs_item = Gtk.MenuItem(label="Re/Start Toshy Services")
    # restart_toshy_svcs_item.connect("activate", fn_restart_toshy_services)
    restart_toshy_svcs_item.connect("activate", lambda widget: service_manager.restart_services())
    menu.append(restart_toshy_svcs_item)

    quit_toshy_svcs_item = Gtk.MenuItem(label="Stop Toshy Services")
    # quit_toshy_svcs_item.connect("activate", fn_stop_toshy_services)
    quit_toshy_svcs_item.connect("activate", lambda widget: service_manager.stop_services())
    menu.append(quit_toshy_svcs_item)

    separator_below_svcs_item = Gtk.SeparatorMenuItem()
    menu.append(separator_below_svcs_item)  #-------------------------------------#

restart_toshy_script_item = Gtk.MenuItem(label="Re/Start Config-Only")
# restart_toshy_script_item.connect("activate", fn_restart_toshy_config_only)
restart_toshy_script_item.connect("activate", lambda widget: service_manager.restart_config_only())
menu.append(restart_toshy_script_item)

stop_toshy_script_item = Gtk.MenuItem(label="Stop Config-Only")
# stop_toshy_script_item.connect("activate", fn_stop_toshy_config_only)
stop_toshy_script_item.connect("activate", lambda widget: service_manager.stop_config_only())
menu.append(stop_toshy_script_item)

separator_below_script_item = Gtk.SeparatorMenuItem()
menu.append(separator_below_script_item)  #-------------------------------------#

if not runtime.barebones_config:

    def load_prefs_submenu_settings():
        cnfg.load_settings()
        set_item_active_thread_safe(forced_numpad_item, cnfg.forced_numpad)
        set_item_active_thread_safe(media_arrows_fix_item, cnfg.media_arrows_fix)
        set_item_active_thread_safe(multi_lang_item, cnfg.multi_lang)
        set_item_active_thread_safe(ST3_in_VSCode_item, cnfg.ST3_in_VSCode)
        set_item_active_thread_safe(Caps2Cmd_item, cnfg.Caps2Cmd)
        set_item_active_thread_safe(Caps2Esc_Cmd_item, cnfg.Caps2Esc_Cmd)
        set_item_active_thread_safe(Enter2Ent_Cmd_item, cnfg.Enter2Ent_Cmd)

    def save_prefs_settings(widget):
        cnfg.forced_numpad      = forced_numpad_item.get_active()
        cnfg.media_arrows_fix   = media_arrows_fix_item.get_active()
        cnfg.multi_lang         = multi_lang_item.get_active()
        cnfg.ST3_in_VSCode      = ST3_in_VSCode_item.get_active()
        cnfg.Caps2Cmd           = Caps2Cmd_item.get_active()
        cnfg.Caps2Esc_Cmd       = Caps2Esc_Cmd_item.get_active()
        cnfg.Enter2Ent_Cmd      = Enter2Ent_Cmd_item.get_active()
        cnfg.save_settings()
        GLib.idle_add(load_prefs_submenu_settings)  # Queue the update to run in GTK's main loop

    ###############################################################
    # Preferences submenu

    prefs_submenu = Gtk.Menu()
    prefs_submenu_item = Gtk.MenuItem(label="Preferences")
    prefs_submenu_item.set_submenu(prefs_submenu)
    menu.append(prefs_submenu_item)

    multi_lang_item = Gtk.CheckMenuItem(label='Alt_Gr on Right Cmd')
    multi_lang_item.set_active(cnfg.multi_lang)
    multi_lang_item.connect('toggled', save_prefs_settings)
    prefs_submenu.append(multi_lang_item)

    Caps2Cmd_item = Gtk.CheckMenuItem(label='CapsLock is Cmd')
    Caps2Cmd_item.set_active(cnfg.Caps2Cmd)
    Caps2Cmd_item.connect('toggled', save_prefs_settings)
    prefs_submenu.append(Caps2Cmd_item)

    Caps2Esc_Cmd_item = Gtk.CheckMenuItem(label='CapsLock is Esc & Cmd')
    Caps2Esc_Cmd_item.set_active(cnfg.Caps2Esc_Cmd)
    Caps2Esc_Cmd_item.connect('toggled', save_prefs_settings)
    prefs_submenu.append(Caps2Esc_Cmd_item)

    Enter2Ent_Cmd_item = Gtk.CheckMenuItem(label='Enter is Ent & Cmd')
    Enter2Ent_Cmd_item.set_active(cnfg.Enter2Ent_Cmd)
    Enter2Ent_Cmd_item.connect('toggled', save_prefs_settings)
    prefs_submenu.append(Enter2Ent_Cmd_item)

    ST3_in_VSCode_item = Gtk.CheckMenuItem(label='Sublime3 in VSCode')
    ST3_in_VSCode_item.set_active(cnfg.ST3_in_VSCode)
    ST3_in_VSCode_item.connect('toggled', save_prefs_settings)
    prefs_submenu.append(ST3_in_VSCode_item)

    forced_numpad_item = Gtk.CheckMenuItem(label='Forced Numpad')
    forced_numpad_item.set_active(cnfg.forced_numpad)
    forced_numpad_item.connect('toggled', save_prefs_settings)
    prefs_submenu.append(forced_numpad_item)

    media_arrows_fix_item = Gtk.CheckMenuItem(label='Media Arrows Fix')
    media_arrows_fix_item.set_active(cnfg.media_arrows_fix)
    media_arrows_fix_item.connect('toggled', save_prefs_settings)
    prefs_submenu.append(media_arrows_fix_item)

    # End of Preferences submenu
    ###############################################################

    def load_optspec_layout_submenu_settings():
        cnfg.load_settings()
        layout = cnfg.optspec_layout
        if   layout == 'US':            set_item_active_thread_safe(optspec_us_item, True)
        elif layout == 'ABC':           set_item_active_thread_safe(optspec_abc_extended_item, True)
        elif layout == 'Disabled':      set_item_active_thread_safe(optspec_disabled_item, True)

    def save_optspec_layout_setting(menu_item, layout):
        if not menu_item.get_active():
            return
        
        cnfg.optspec_layout = layout
        cnfg.save_settings()
        load_optspec_layout_submenu_settings()

    # OptSpec layout submenu
    optspec_layout_submenu = Gtk.Menu()
    optspec_layout_item = Gtk.MenuItem(label='OptSpec Layout')
    optspec_layout_item.set_submenu(optspec_layout_submenu)
    menu.append(optspec_layout_item)

    # Create submenu items using RadioMenuItem
    group_optspec = None
    optspec_us_item = Gtk.RadioMenuItem.new_with_label(group_optspec, 'US')
    optspec_us_item.connect('toggled', save_optspec_layout_setting, 'US')
    optspec_layout_submenu.append(optspec_us_item)
    group_optspec = optspec_us_item.get_group()

    optspec_abc_extended_item = Gtk.RadioMenuItem.new_with_label(group_optspec, 'ABC Extended')
    optspec_abc_extended_item.connect('toggled', save_optspec_layout_setting, 'ABC')
    optspec_layout_submenu.append(optspec_abc_extended_item)

    optspec_disabled_item = Gtk.RadioMenuItem.new_with_label(group_optspec, 'Disabled*')
    optspec_disabled_item.connect('toggled', save_optspec_layout_setting, 'Disabled')
    optspec_layout_submenu.append(optspec_disabled_item)


    def load_kbtype_submenu_settings():
        cnfg.load_settings()
        kbtype = cnfg.override_kbtype
        if kbtype == 'Auto-Adapt':      set_item_active_thread_safe(kbtype_auto_adapt_item, True)
        elif kbtype == 'Apple':         set_item_active_thread_safe(kbtype_apple_item, True)
        elif kbtype == 'Chromebook':    set_item_active_thread_safe(kbtype_chromebook_item, True)
        elif kbtype == 'IBM':           set_item_active_thread_safe(kbtype_ibm_item, True)
        elif kbtype == 'Windows':       set_item_active_thread_safe(kbtype_windows_item, True)

    def save_kbtype_setting(menu_item, kbtype):
        if not menu_item.get_active():
            return
        
        cnfg.override_kbtype = kbtype
        cnfg.save_settings()

        GLib.idle_add(load_kbtype_submenu_settings)

        valid_kbtypes = ['Apple', 'Chromebook', 'IBM', 'Windows']
        if cnfg.override_kbtype in valid_kbtypes:
            message = ('Overriding keyboard type disables auto-adaptation.\r'
                    'This is meant as a temporary fix only! See README.')
            ntfy.send_notification(message, icon_file_grayscale, urgency='critical')

    ###############################################################
    # Keyboard Type submenu
    kbtype_submenu = Gtk.Menu()
    kbtype_item = Gtk.MenuItem(label='Keyboard Type')
    kbtype_item.set_submenu(kbtype_submenu)
    menu.append(kbtype_item)

    # create submenu items using RadioMenuItem
    group_kbtype = None
    kbtype_auto_adapt_item = Gtk.RadioMenuItem.new_with_label(group_kbtype, 'Auto-Adapt*')
    kbtype_auto_adapt_item.connect('toggled', save_kbtype_setting, 'Auto-Adapt')
    kbtype_submenu.append(kbtype_auto_adapt_item)
    group_kbtype = kbtype_auto_adapt_item.get_group()

    kbtype_apple_item = Gtk.RadioMenuItem.new_with_label(group_kbtype, 'Apple')
    kbtype_apple_item.connect('toggled', save_kbtype_setting, 'Apple')
    kbtype_submenu.append(kbtype_apple_item)

    kbtype_chromebook_item = Gtk.RadioMenuItem.new_with_label(group_kbtype, 'Chromebook')
    kbtype_chromebook_item.connect('toggled', save_kbtype_setting, 'Chromebook')
    kbtype_submenu.append(kbtype_chromebook_item)

    kbtype_ibm_item = Gtk.RadioMenuItem.new_with_label(group_kbtype, 'IBM')
    kbtype_ibm_item.connect('toggled', save_kbtype_setting, 'IBM')
    kbtype_submenu.append(kbtype_ibm_item)

    kbtype_windows_item = Gtk.RadioMenuItem.new_with_label(group_kbtype, 'Windows')
    kbtype_windows_item.connect('toggled', save_kbtype_setting, 'Windows')
    kbtype_submenu.append(kbtype_windows_item)

    separator_below_kbtype_submenu_item = Gtk.SeparatorMenuItem()
    menu.append(separator_below_kbtype_submenu_item)  #-------------------------------------#

    preferences_item = Gtk.MenuItem(label="Open Preferences App")
    preferences_item.connect("activate", fn_open_preferences)
    menu.append(preferences_item)

open_config_folder_item = Gtk.MenuItem(label="Open Config Folder")
open_config_folder_item.connect("activate", fn_open_config_folder)
menu.append(open_config_folder_item)

if runtime.is_systemd:
    show_services_log_item = Gtk.MenuItem(label="Show Services Log")
    show_services_log_item.connect("activate", fn_show_services_log)
    menu.append(show_services_log_item)

separator_above_remove_icon_item = Gtk.SeparatorMenuItem()
menu.append(separator_above_remove_icon_item)  #-------------------------------------#


def load_autoload_tray_icon_setting():
    cnfg.load_settings()
    set_item_active_thread_safe(autoload_tray_icon_item, cnfg.autoload_tray_icon)


def fn_save_autoload_tray_icon_setting(widget):
    autoload_tray_icon_bool    = widget.get_active()
    # debug(f'{autoload_tray_icon_setting = }')
    cnfg.autoload_tray_icon    = autoload_tray_icon_bool
    cnfg.save_settings()
    load_autoload_tray_icon_setting()

    tray_dt_file_name           = 'Toshy_Tray.desktop'
    home_apps_path              = os.path.join(runtime.home_dir, '.local', 'share', 'applications')
    tray_dt_file_path           = os.path.join(home_apps_path, tray_dt_file_name)

    home_autostart_path         = os.path.join(runtime.home_dir, '.config', 'autostart')
    tray_link_file_path         = os.path.join(home_autostart_path, tray_dt_file_name)

    if autoload_tray_icon_bool:
        # do the enabling of tray icon autostart:
        # create symlink file ~/.config/autostart/Toshy_Tray.desktop
        #   with target file ~/.local/share/applications/Toshy_Tray.desktop
        # alternative: os.symlink(source, dest, target_is_directory=False)
        cmd_lst = ['ln', '-sf', tray_dt_file_path, tray_link_file_path]
        try:
            subprocess.run(cmd_lst, check=True) #, stdout=DEVNULL, stderr=DEVNULL)
        except subprocess.CalledProcessError as proc_err:
            error(f'Problem enabling tray icon autoload:\n\t{proc_err}')
    else:
        # do the disabling of tray icon autostart:
        # remove the symlink file ~/.config/autostart/Toshy_Tray.desktop
        # alternative: os.remove(path) or os.unlink(path)
        cmd_lst = ['rm', '-f', tray_link_file_path]
        try:
            subprocess.run(cmd_lst, check=True) # , stdout=DEVNULL, stderr=DEVNULL)
        except subprocess.CalledProcessError as proc_err:
            error(f'Problem disabling tray icon autoload:\n\t{proc_err}')


autostart_submenu_item = Gtk.MenuItem(label="Autostart Options")
autostart_submenu = Gtk.Menu()

if runtime.is_systemd:
    autostart_toshy_svcs_item = Gtk.CheckMenuItem(label="Autostart Toshy Services")
    autostart_toshy_svcs_item.set_active(   toshy_svc_sessmon_unit_enabled and 
                                            toshy_svc_config_unit_enabled       )
    autostart_toshy_svcs_item.connect("toggled", fn_toggle_toshy_svcs_autostart)
    autostart_submenu.append(autostart_toshy_svcs_item)
else:
    autostart_toshy_svcs_item = Gtk.MenuItem(label="(Non-systemd init)")
    autostart_toshy_svcs_item.set_sensitive(False)  # Makes it dimmed/disabled
    autostart_submenu.append(autostart_toshy_svcs_item)

autoload_tray_icon_item = Gtk.CheckMenuItem(label="Autoload Tray Icon")
autoload_tray_icon_item.set_active(cnfg.autoload_tray_icon)
autoload_tray_icon_item.connect("toggled", fn_save_autoload_tray_icon_setting)
autostart_submenu.append(autoload_tray_icon_item)

autostart_submenu_item.set_submenu(autostart_submenu)
menu.append(autostart_submenu_item)

remove_tray_icon_item = Gtk.MenuItem(label="Remove Icon from Tray")
remove_tray_icon_item.connect("activate", fn_remove_tray_icon)
menu.append(remove_tray_icon_item)

menu.show_all()


def main():

    global process_mgr

    process_mgr = ProcessManager(TOSHY_PART, TOSHY_PART_NAME)
    process_mgr.initialize()

    global loop

    # On distros known to not use 'systemd', use 'inverse' icon (except on COSMIC)
    if DESKTOP_ENV != 'cosmic' and not runtime.is_systemd:
        tray_indicator.set_icon_full(icon_file_inverse, "Toshy Tray Icon Inactive")

    def on_settings_changed():
        """Callback for when settings change - update GTK UI."""
        if not runtime.barebones_config:
            GLib.idle_add(load_prefs_submenu_settings)
            GLib.idle_add(load_optspec_layout_submenu_settings)
            GLib.idle_add(load_kbtype_submenu_settings)
            GLib.idle_add(load_autoload_tray_icon_setting)

    def on_service_status_changed(config_status, session_monitor_status):
        """Callback for when service status changes - update tray icon and labels."""
        # Update tray icon based on status
        if config_status == 'Active' and session_monitor_status == 'Active':
            GLib.idle_add(tray_indicator.set_icon_full, icon_file_active, "Toshy Tray Icon Active")
        elif config_status == 'Inactive' and session_monitor_status == 'Inactive':
            GLib.idle_add(tray_indicator.set_icon_full, icon_file_inverse, "Toshy Tray Icon Inactive") 
        else:
            GLib.idle_add(tray_indicator.set_icon_full, icon_file_grayscale, "Toshy Tray Icon Undefined")
        
        # Update menu labels
        config_label = f'       Config: {config_status}'
        sessmon_label = f'     SessMon: {session_monitor_status}'
        GLib.idle_add(lambda: toshy_config_status_item.set_label(config_label))
        GLib.idle_add(lambda: session_monitor_status_item.set_label(sessmon_label))

    settings_monitor = SettingsMonitor(cnfg, on_settings_changed)
    service_monitor = ServiceMonitor(on_service_status_changed)

    if shutil.which('systemctl') and runtime.is_systemd:
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
        
        service_monitor.start_monitoring()

    settings_monitor.start_monitoring()

    if not runtime.barebones_config:
        # load the settings for the preferences submenu toggle items
        load_prefs_submenu_settings()
        # load the settings for the optspec layout submenu
        load_optspec_layout_submenu_settings()
        # load the settings for the keyboard type submenu
        load_kbtype_submenu_settings()
        # load the setting for the autostart tray icon item
        load_autoload_tray_icon_setting()

    # GUI loop event
    loop = GLib.MainLoop()
    loop.run()
    # Gtk.main()


if __name__ == "__main__":
    # debug("")
    # debug(cnfg)       # prints out the __str__ method of Settings class
    main()
