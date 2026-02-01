#!/usr/bin/env python3
__version__ = '20260201'                        # CLI option "--version" will print this out.

import os
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'     # prevent this script from creating cache files
import re
import grp
import pwd
import sys
import glob
import random
import shutil
import signal
import string
import sqlite3
import zipfile
import argparse
import builtins
import datetime
import platform
import textwrap
import subprocess

from subprocess import DEVNULL, PIPE

# Type hints are about to become a problem due to issues between <3.9 and >3.15 Python releases.
# So we will have to remove many or most of them to retain 3.8-3.15+ compatibility.
# from typing import Dict, List, Tuple, Optional

# local imports
from toshy_common import logger
from toshy_common.env_context import EnvironmentInfo
from toshy_common.logger import debug, error, warn, info

logger.FLUSH = True

# Save the original print function
original_print = builtins.print

# Override the print function
def print(*args, **kwargs):
    # Set flush to True, to force logging to be in correct order.
    # Some terminals do weird buffering, cause out-of-order logs.
    kwargs['flush'] = True
    original_print(*args, **kwargs)  # Call the original print

# Replace the built-in print with our custom print (where flush is always True)
builtins.print = print


def is_script_running_as_root():
    """Utility function to catch the user running the entire script as superuser/root,
        which is undesirable since it is so user-oriented in nature. A simple check of
        EUID == 0 does not cover non-sudo setups well."""

    # Check environment indicators first (most reliable)
    env_indicators = [
        # Direct privilege elevation indicators
        'SUDO_USER' in os.environ,
        'DOAS_USER' in os.environ,

        # Root user indicators
        os.environ.get('USER')      == 'root',
        os.environ.get('LOGNAME')   == 'root',
        os.environ.get('HOME')      == '/root',
    ]

    if any(env_indicators):
        return True

    # Fall back to UID checks if environment doesn't indicate elevation
    return os.geteuid() == 0 or os.getuid() == 0


if is_script_running_as_root():
    print()
    error("This setup script should not be run as root/superuser. Exiting.\n")
    sys.exit(1)


def signal_handler(sig, frame):
    """Handle signals like Ctrl+C"""
    if sig in (signal.SIGINT, signal.SIGQUIT):
        # Perform any cleanup code here before exiting
        # traceback.print_stack(frame)
        print('\n')
        debug(f'SIGINT or SIGQUIT received. Exiting.\n')
        sys.exit(1)


if platform.system() != 'Windows':
    signal.signal(signal.SIGINT,    signal_handler)
    signal.signal(signal.SIGQUIT,   signal_handler)
    signal.signal(signal.SIGHUP,    signal_handler)
    signal.signal(signal.SIGUSR1,   signal_handler)
    signal.signal(signal.SIGUSR2,   signal_handler)
else:
    signal.signal(signal.SIGINT,    signal_handler)
    error(f'This is only meant to run on Linux. Exiting.')
    sys.exit(1)

original_PATH_str       = os.getenv('PATH')
if original_PATH_str is None:
    print()
    error(f"ERROR: PATH variable is not set. This is abnormal. Exiting.")
    print()
    sys.exit(1)


# TODO: Integrate this into the rest of the setup script?
def get_linux_app_dirs(app_name):
    # Default XDG directories
    def_xdg_data_home       = os.path.join(os.environ['HOME'], '.local', 'share')
    def_xdg_config_home     = os.path.join(os.environ['HOME'], '.config')
    def_xdg_cache_home      = os.path.join(os.environ['HOME'], '.cache')
    def_xdg_state_home      = os.path.join(os.environ['HOME'], '.local', 'state')

    # Actual XDG directories on system
    xdg_data_home           = os.environ.get('XDG_DATA_HOME',   def_xdg_data_home)
    xdg_config_home         = os.environ.get('XDG_CONFIG_HOME', def_xdg_config_home)
    xdg_cache_home          = os.environ.get('XDG_CACHE_HOME',  def_xdg_cache_home)
    xdg_state_home          = os.environ.get('XDG_STATE_HOME',  def_xdg_state_home)

    app_dirs = {
        'data_dir':         os.path.join(xdg_data_home,     app_name),
        'config_dir':       os.path.join(xdg_config_home,   app_name),
        'cache_dir':        os.path.join(xdg_cache_home,    app_name),
        'log_dir':          os.path.join(xdg_state_home,    app_name)
    }

    return app_dirs

# Example usage
app_name = 'toshy'
app_dirs = get_linux_app_dirs(app_name)
# print(app_dirs)


home_dir                = os.path.expanduser('~')

# This was being defined several times in different functions, for some reason. Moved to global.
autostart_dir_path      = os.path.join(home_dir, '.config', 'autostart')

trash_dir               = os.path.join(home_dir, '.local', 'share', 'Trash')
this_file_path          = os.path.realpath(__file__)
this_file_dir           = os.path.dirname(this_file_path)
this_file_name          = os.path.basename(__file__)
if trash_dir in this_file_path or '/trash/' in this_file_path.lower():
    print()
    error(f"Path to this file:\n\t{this_file_path}")
    error(f"You probably did not intend to run this from the TRASH. See path. Exiting.")
    print()
    sys.exit(1)

home_local_bin          = os.path.join(home_dir, '.local', 'bin')
run_tmp_dir             = os.environ.get('XDG_RUNTIME_DIR') or '/tmp'

good_path_tmp_file      = 'toshy_installer_says_path_is_good'
good_path_tmp_path      = os.path.join(run_tmp_dir, good_path_tmp_file)

fix_path_tmp_file       = 'toshy_installer_says_fix_path'
fix_path_tmp_path       = os.path.join(run_tmp_dir, fix_path_tmp_file)

# set a standard path for duration of script run, to avoid issues with user customized paths
os.environ['PATH']      = '/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin'

# deactivate Python virtual environment, if one is active, to avoid issues with sys.executable
if sys.prefix != sys.base_prefix:
    os.environ["VIRTUAL_ENV"] = ""
    sys.path = [p for p in sys.path if not p.startswith(sys.prefix)]
    sys.prefix = sys.base_prefix

do_not_ask_about_path = None
if home_local_bin in original_PATH_str:
    with open(good_path_tmp_path, 'a') as file:
        file.write('Nothing to see here.')
    # subprocess.run(['touch', path_good_tmp_path])
    do_not_ask_about_path = True
else:
    debug("Home user local bin not part of PATH string.")
# do the 'else' of creating 'path_fix_tmp_path' later in function that prompts user

# system Python version
py_ver_mjr, py_ver_mnr  = sys.version_info[:2]
py_interp_ver_tup       = (py_ver_mjr, py_ver_mnr)
py_pkg_ver_str          = f'{py_ver_mjr}{py_ver_mnr}'


class InstallerSettings:
    """Set up variables for necessary information to be used by all functions"""

    def __init__(self) -> None:
        sep_reps                    = 80
        self.sep_char               = '='
        self.separator              = self.sep_char * sep_reps

        self.DISTRO_ID              = None
        self.DISTRO_VER: str        = ""
        self.VARIANT_ID             = None
        self.SESSION_TYPE           = None
        self.DESKTOP_ENV            = None
        self.DE_MAJ_VER: str        = ""
        self.WINDOW_MGR             = None

        self.distro_mjr_ver: str    = ""
        self.distro_mnr_ver: str    = ""

        self.valid_KDE_vers         = ['6', '5', '4', '3']

        self.systemctl_present      = shutil.which('systemctl') is not None
        self.init_system            = None

        self.pkgs_for_distro        = None

        self.priv_elev_cmd          = None
        self.qdbus_cmd              = self.find_qdbus_command()

        # current stable Python release version (TODO: update when needed):
        # 3.11 Release Date: Oct. 24, 2022
        self.curr_py_rel_ver_mjr    = 3
        self.curr_py_rel_ver_mnr    = 11
        self.curr_py_rel_ver_tup    = (self.curr_py_rel_ver_mjr, self.curr_py_rel_ver_mnr)
        self.curr_py_rel_ver_str    = f'{self.curr_py_rel_ver_mjr}.{self.curr_py_rel_ver_mnr}'

        self.py_interp_ver_str      = f'{py_ver_mjr}.{py_ver_mnr}'
        self.py_interp_path         = shutil.which('python3')

        self.toshy_dir_path         = os.path.join(home_dir, '.config', 'toshy')
        self.db_file_name           = 'toshy_user_preferences.sqlite'
        self.db_file_path           = os.path.join(self.toshy_dir_path, self.db_file_name)
        self.backup_succeeded       = None
        self.existing_cfg_data      = None
        self.existing_cfg_slices    = None
        self.venv_path              = os.path.join(self.toshy_dir_path, '.venv')
        # This was changed to a property method that re-evaluates on each access:
        # self.venv_cmd_lst           = [self.py_interp_path, '-m', 'venv', self.venv_path]

        self.keymapper_tmp_path     = os.path.join(this_file_dir, 'keymapper-temp')

        self.keymapper_branch       = 'main'        # new branch when switched to 'xwaykeyz'
        self.keymapper_dev_branch   = 'dev_beta'    # branch to test new keymapper features
        self.keymapper_cust_branch  = None          # Branch name provided by CLI flag argument

        self.keymapper_url          = 'https://github.com/RedBearAK/xwaykeyz.git'

        # This was changed to a property method that re-evaluates on each access:
        # self.keymapper_clone_cmd    = f'git clone -b {self.keymapper_branch} {self.keymapper_url}'

        self.input_group            = 'input'
        self.user_name              = pwd.getpwuid(os.getuid()).pw_name

        self.autostart_tray_icon    = True
        self.unprivileged_user      = False

        self.prep_only              = None

        # option flags for the "install" command:
        self.override_distro        = None      # will be a string if not None
        self.barebones_config       = None
        self.skip_native            = None
        self.fancy_pants            = None
        self.no_dbus_python         = None
        self.use_dev_keymapper      = None

        self.app_switcher           = None      # Install/upgrade Application Switcher KWin script

        self.tweak_applied          = None
        self.remind_extensions      = None
        self.enabled_gnome_exts     = None
        self.should_reboot          = None

        self.run_tmp_dir            = run_tmp_dir
        self.reboot_tmp_file        = f"{self.run_tmp_dir}/toshy_installer_says_reboot"
        self.reboot_ascii_art       = textwrap.dedent("""
            ██████      ███████     ██████       ██████       ██████      ████████     ██ 
            ██   ██     ██          ██   ██     ██    ██     ██    ██        ██        ██ 
            ██████      █████       ██████      ██    ██     ██    ██        ██        ██ 
            ██   ██     ██          ██   ██     ██    ██     ██    ██        ██           
            ██   ██     ███████     ██████       ██████       ██████         ██        ██ 
            """)

    @property
    def venv_cmd_lst(self):
        # Originally a class instance attribute variable:
        # self.venv_cmd_lst           = [self.py_interp_path, '-m', 'venv', self.venv_path]
        # Needs to re-evaluate itself when accessed, in case Python interpreter path changed:

        is_AerynOS_based     = cnfg.DISTRO_ID in distro_groups_map['aerynos-based']

        # Add '--copies' flag to avoid using symlinks to system Python interpreter, and
        # hopefully prevent Toshy from breaking when user does a dist-upgrade. 
        # (Didn't work for that purpose, but still a good idea for other reasons.)

        if is_AerynOS_based:
            # Use 'virtualenv' on AerynOS (formerly Serpent OS) because 'ensurepip' missing,
            # which is a dependency for the 'venv' module. 
            return [self.py_interp_path, '-m', 'virtualenv', '--copies', self.venv_path]

        return [self.py_interp_path, '-m', 'venv', '--copies', self.venv_path]

    @property
    def keymapper_clone_cmd(self):
        # Originally a class instance attribute variable:
        # self.keymapper_clone_cmd    = f'git clone -b {self.keymapper_branch} {self.keymapper_url}'

        if self.use_dev_keymapper:
            if self.keymapper_cust_branch:
                _km_branch = self.keymapper_cust_branch
            else:
                _km_branch = self.keymapper_dev_branch
        else:
            _km_branch = self.keymapper_branch

        _clone_cmd = f'git clone -b {_km_branch} {self.keymapper_url}'
        print(f"Keymapper clone command:\n  {_clone_cmd}")
        return _clone_cmd

    def detect_elevation_command(self):
        """Detect the appropriate privilege elevation command"""
        # Order of preference for elevation commands
        known_privilege_elevation_cmds = ["sudo", "doas", "run0", "sudo-rs"]
        print()
        print(f"Checking for the following commands:\n  {known_privilege_elevation_cmds}")

        for cmd in known_privilege_elevation_cmds:
            if shutil.which(cmd):
                cnfg.priv_elev_cmd = cmd
                print(f"Using the '{cmd}' command for privilege elevation (if needed).")
                return

        # If no elevation command found
        error("No known privilege elevation command found. Cannot continue.")
        safe_shutdown(1)

    def find_qdbus_command(self):
        # List of qdbus command names by preference
        commands = ['qdbus6', 'qdbus-qt6', 'qdbus-qt5', 'qdbus']
        for command in commands:
            if shutil.which(command):
                return command

        # Fallback to 'qdbus' if none of the preferred options are found
        return 'qdbus'


def safe_shutdown(exit_code: int):
    """do some stuff on the way out"""
    # good place to do some file cleanup?

    # Only sudo has a standard way to invalidate tickets
    if cnfg.priv_elev_cmd in ['sudo', 'sudo-rs']:
        # invalidate the sudo ticket, don't leave system in "superuser" state
        subprocess.run([cnfg.priv_elev_cmd, '-k'])
    print()                         # avoid crowding the prompt on exit
    sys.exit(exit_code)


# Limit script to operating on Python 3.6 or later (e.g. CentOS 7, Leap, RHEL 8, etc.)
if py_interp_ver_tup < (3, 6):
    print()
    error(f"Python version is older than 3.6. This is untested and probably will not work.")
    safe_shutdown(1)


def show_reboot_prompt():
    """show the big ASCII reboot prompt"""
    print()
    print()
    print()
    print(cnfg.separator)
    print(cnfg.separator)
    print(cnfg.reboot_ascii_art)
    print(cnfg.separator)
    print(cnfg.separator)


def get_environment_info():
    """Get the necessary info from the environment evaluation module"""
    print(f'\n§  Getting environment information...\n{cnfg.separator}')

    known_init_systems = {
        'systemd':              'Systemd',
        'init':                 'SysVinit',
        'upstart':              'Upstart',
        'openrc':               'OpenRC',
        'runit':                'Runit',
        'dinit':                'Dinit',
        'initng':               'Initng',
    }

    try:
        with open('/proc/1/comm', 'r') as f:
            cnfg.init_system = f.read().strip()
    except (PermissionError, FileNotFoundError, OSError) as init_check_err:
        error(f'ERROR: Problem when checking init system:\n\t{init_check_err}')

    if cnfg.init_system:
        if cnfg.init_system in known_init_systems:
            init_sys_full_name = known_init_systems[cnfg.init_system]
            print(f"The active init system is: '{cnfg.init_system}' ({init_sys_full_name})")
        else:
            print(f"Init system process unknown: '{cnfg.init_system}'")
    else:
        error("ERROR: Init system (process 1) could not be determined. (See above error.)")
    print()   # blank line after init system message

    if cnfg.prep_only and not os.environ.get('XDG_SESSION_DESKTOP'):
        # su-ing to an admin user will show no graphical environment info
        # we don't care what it is, just that it is set to avoid errors in get_env_info()
        os.environ['XDG_SESSION_DESKTOP'] = 'gnome'

    if cnfg.prep_only and not os.environ.get('XDG_SESSION_TYPE'):
        # su-ing to an admin user will show no graphical environment info
        # we don't care what it is, just that it is set to avoid errors in get_env_info()
        os.environ['XDG_SESSION_TYPE'] = 'x11'

    # env_info_dct   = env.get_env_info()
    env_ctxt_getter = EnvironmentInfo()
    env_info_dct   = env_ctxt_getter.get_env_info()

    # Avoid casefold() errors by converting all to strings
    if cnfg.override_distro:
        cnfg.DISTRO_ID    = str(cnfg.override_distro).casefold()
    else:
        cnfg.DISTRO_ID    = str(env_info_dct.get('DISTRO_ID',     'keymissing')).casefold()
    cnfg.DISTRO_VER     = str(env_info_dct.get('DISTRO_VER',    'keymissing')).casefold()
    cnfg.VARIANT_ID     = str(env_info_dct.get('VARIANT_ID',    'keymissing')).casefold()
    cnfg.SESSION_TYPE   = str(env_info_dct.get('SESSION_TYPE',  'keymissing')).casefold()
    cnfg.DESKTOP_ENV    = str(env_info_dct.get('DESKTOP_ENV',   'keymissing')).casefold()
    cnfg.DE_MAJ_VER     = str(env_info_dct.get('DE_MAJ_VER',    'keymissing')).casefold()
    cnfg.WINDOW_MGR     = str(env_info_dct.get('WINDOW_MGR',    'keymissing')).casefold()

    # split out the major version from the minor version, if there is one
    distro_ver_parts            = cnfg.DISTRO_VER.split('.') if cnfg.DISTRO_VER else []
    cnfg.distro_mjr_ver         = distro_ver_parts[0] if distro_ver_parts else 'NO_VER'
    cnfg.distro_mnr_ver         = distro_ver_parts[1] if len(distro_ver_parts) > 1 else 'no_mnr_ver'

    debug('Toshy installer sees this environment:'
        f"\n\t DISTRO_ID        = '{cnfg.DISTRO_ID}'"
        f"\n\t DISTRO_VER       = '{cnfg.DISTRO_VER}'"
        f"\n\t VARIANT_ID       = '{cnfg.VARIANT_ID}'"
        f"\n\t SESSION_TYPE     = '{cnfg.SESSION_TYPE}'"
        f"\n\t DESKTOP_ENV      = '{cnfg.DESKTOP_ENV}'"
        f"\n\t DE_MAJ_VER       = '{cnfg.DE_MAJ_VER}'"
        f"\n\t WINDOW_MGR       = '{cnfg.WINDOW_MGR}'"
        '', ctx='EV')


def md_wrap(text: str, width: int = 80):
    """
    Process and wrap text as if written in Markdown style, where double newlines signify
    paragraph breaks. Single newlines are treated as a space for better formatting, unless
    they are part of a paragraph break. Text is wrapped to the specified width (characters).

    Text blocks can be indented like the surrounding code. The indenting will be removed.

    Args:
        text (str):     The input text to wrap and print.
        width (int):    The maximum width of the wrapped text, default is 80.
    """
    # Dedent the text to remove any common leading whitespace
    text = textwrap.dedent(text)

    # Detect and store any trailing spaces preceding the final newline
    trailing_spaces = re.findall(r' +\n$', text)
    if trailing_spaces:
        # Extract the spaces from the list (only one element expected)
        trailing_spaces = trailing_spaces[0][:-1]  # Remove the newline character
    else:
        trailing_spaces = ''

    # Replace explicit double newlines with a placeholder to preserve them
    text = text.replace('\n\n', '\uffff')
    # Replace single newlines (which are for code readability) with a space
    text = text.replace('\n', ' ')
    # Convert the placeholders back to double newlines
    text = text.replace('\uffff', '\n\n')

    # Wrap each paragraph separately to maintain intended formatting
    paragraphs = text.split('\n\n')

    # Join the string back together, applying wrap width.
    wrapped_text = '\n\n'.join(textwrap.fill(paragraph, width=width) for paragraph in paragraphs)
    # Clean up space inserted inappropriately beginning of joined string.
    wrapped_text = re.sub(r'^[ ]+', '', wrapped_text)
    # Clean up doubled spaces from a space being left at the end of a line.
    wrapped_text = re.sub(' +', ' ', wrapped_text)

    # Append any trailing spaces that were initially present
    wrapped_text += trailing_spaces

    # Return the wrapped_text string.
    return wrapped_text


def check_term_color_code_support():
    """
    Determine if the terminal supports ANSI color codes.
    :return: True if color is probably supported, False otherwise.
    """
    color_term_checks = [
        bool(os.getenv('LS_COLORS', '')),                    # Most common - set on most Linux/Unix
        "color" in os.getenv('TERM', '').lower(),            # Very common - xterm-256color, etc.
        bool(os.getenv('COLORTERM', '')),                    # Modern terminals
        "256" in os.getenv('TERM', '').lower(),              # 256-color terminals
        os.getenv('TERM', '').lower().startswith("xterm")    # xterm variants
    ]

    return any(color_term_checks)


# Global variable to indicate that terminal supports ANSI color codes
term_supports_color_codes = check_term_color_code_support()


def fancy_str(text, color_name, *, bold=False, color_supported=term_supports_color_codes):
    """
    Return text wrapped in the specified color code.
    :param text: Text to be colorized.
    :param color_name: Natural name of the color.
    :param bold: Boolean to indicate if text should be bold.
    :return: Colorized string if terminal likely supports it, otherwise the original string.
    """
    color_codes = { 'red': '31', 'green': '32', 'yellow': '33', 'blue': '34', 
                    'magenta': '35', 'cyan': '36', 'white': '37', 'default': '0'}

    if color_supported and color_name in color_codes:
        bold_code = '1;' if bold else ''
        return f"\033[{bold_code}{color_codes[color_name]}m{text}\033[0m"
    else:
        return text


def call_attn_to_pwd_prompt_if_needed():
    """Utility function to emphasize the admin/superuser password prompt"""

    if cnfg.priv_elev_cmd is None or cnfg.unprivileged_user:
        error("Attention function was called with no elevation command, or unprivileged user.")
        return  # Skip if no elevation command or in unprivileged mode (should never happen)

    if cnfg.priv_elev_cmd in ['sudo', 'doas', 'sudo-rs']:
        try:
            subprocess.run( [cnfg.priv_elev_cmd, '-n', 'true'],
                            stdout=DEVNULL, stderr=DEVNULL, check=True)
            return
        except subprocess.CalledProcessError:
            # Password is needed, show the alert
            pass

    elif cnfg.priv_elev_cmd == 'run0':
        try:
            subprocess.run( [cnfg.priv_elev_cmd, '--no-ask-password', 'true'],
                            stdout=DEVNULL, stderr=DEVNULL, check=True)
            return
        except subprocess.CalledProcessError:
            # Password is needed, show the alert
            pass

    else:
        print()
        error(f"Privilege elevation command '{cnfg.priv_elev_cmd}' is not handled in the\n"
                "      attention function. Please notify the dev to fix this error.\n")
        return

    # Get user attention if there is a password needed (prompt will appear after this)
    main_clr = 'blue'
    alt_clr = 'magenta'
    print()
    print(fancy_str('  -----------------------------------------  ', main_clr, bold=True))
    print(
        fancy_str('  -- ', main_clr, bold=True) +
        fancy_str('   PASSWORD REQUIRED TO CONTINUE   ', alt_clr, bold=True) +
        fancy_str(' --  ', main_clr, bold=True)
    )
    print(fancy_str('  -----------------------------------------  ', main_clr, bold=True))
    print()


def enable_prompt_for_reboot():
    """Utility function to make sure user is reminded to reboot if necessary"""
    cnfg.should_reboot = True
    if not os.path.exists(cnfg.reboot_tmp_file):
        os.mknod(cnfg.reboot_tmp_file)


def verify_device_permissions():
    """
    Check if current user can access the devices the keymapper needs.
    Returns (success: bool, error_message: str | None)
    """
    uinput_path = '/dev/uinput'
    input_dir = '/dev/input'

    # Check /dev/uinput write access
    if not os.path.exists(uinput_path):
        return False, f"'{uinput_path}' does not exist"

    if not os.access(uinput_path, os.W_OK):
        return False, f"No write permission on '{uinput_path}'"

    # Check /dev/input/event* read/write access
    if not os.path.isdir(input_dir):
        return False, f"'{input_dir}' directory does not exist"

    for filename in os.listdir(input_dir):
        if not filename.startswith('event'):
            continue
        event_path = os.path.join(input_dir, filename)
        if os.access(event_path, os.R_OK | os.W_OK):
            return True, None

    return False, f"No accessible event devices in '{input_dir}'"


def verify_config_service_running():
    """Check if toshy-config.service is active."""
    try:
        result = subprocess.run(
            ['systemctl', '--user', 'is-active', 'toshy-config.service'],
            capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip() == 'active'
    except (subprocess.SubprocessError, OSError):
        return False


def can_skip_reboot():
    """
    Determine if reboot can be skipped despite should_reboot being set.
    If permissions are working and service is running, uaccess did its job.
    """
    perms_ok, perms_msg = verify_device_permissions()
    if not perms_ok:
        debug(f"Permission check failed: {perms_msg}")
        return False

    if not verify_config_service_running():
        debug("toshy-config.service is not active")
        return False

    return True


def show_task_completed_msg():
    """Utility function to show a standard message after each major section completes"""
    print(fancy_str('   >> Task completed successfully <<   ', 'green', bold=True))


def generate_secret_code(length: int = 4) -> str:
    """Return a random upper/lower case ASCII letters string of specified length"""
    return ''.join(random.choice(string.ascii_letters) for _ in range(length))


def dot_Xmodmap_warning():
    """Check for '.Xmodmap' file in user's home folder, show warning about mod key remaps"""

    xmodmap_file_path = os.path.join(home_dir, '.Xmodmap')

    if os.path.isfile(xmodmap_file_path):
        print()
        print(f'{cnfg.separator}')
        print(f'{cnfg.separator}')
        warn_str    = "\t WARNING: You have an '.Xmodmap' file in your home folder!!!"
        print(fancy_str(warn_str, "red"))
        print(f'   This can cause confusing PROBLEMS if you are remapping any modifier keys!')
        print(f'{cnfg.separator}')
        print(f'{cnfg.separator}')
        print()

        secret_code = generate_secret_code()

        response = input(
            f"You must take responsibility for the issues an '.Xmodmap' file may cause."
            f"\n\n\t If you understand, enter the secret code '{secret_code}': "
        )

        if response == secret_code:
            print()
            info("Good code. User has taken responsibility for '.Xmodmap' file. Proceeding...\n")
        else:
            print()
            error("Code does not match! Try the installer again after dealing with '.Xmodmap'.")
            safe_shutdown(1)


def ask_is_distro_updated():
    """Ask user if the distro has recently been updated"""
    print()
    debug('NOTICE: It is ESSENTIAL to have your system completely updated.', ctx="!!")
    print()
    response = input('Have you updated your system recently? [y/N]: ')
    if response not in ['y', 'Y']:
        print()
        error("Try the installer again after you've done a full system update. Exiting.")
        safe_shutdown(1)


def ask_add_home_local_bin():
    """
    Check if `~/.local/bin` is in original PATH. Done earlier in script.
    Ask user if it is OK to add the `~/.local/bin` folder to the PATH permanently.
    Create temp file to allow bincommands script to bypass question.
    """
    if do_not_ask_about_path:
        pass
    else:
        print()
        response = input('The "~/.local/bin" folder is not in PATH. OK to add it? [Y/n]: ') or 'y'
        if response in ['y', 'Y']:
            # Let's prompt a reboot when we need to add local-bin to the PATH
            cnfg.should_reboot = True
            # create temp file that will get script to add local bin to path without asking
            with open(fix_path_tmp_path, 'a') as file:
                file.write('Nothing to see here.')


def ask_for_attn_on_info():
    """
    Utility function to request confirmation of attention before 
    moving on in the install process.
    """
    secret_code = generate_secret_code()

    print()
    response = input(
        f"To show that you read the info just above, enter the secret code '{secret_code}': "
    )

    if response == secret_code:
        print()
        info("Good code. User has acknowledged reading the info above. Proceeding...\n")
    else:
        print()
        error("Code does not match! Run the installer again and pay more attention...")
        safe_shutdown(1)


def get_enabled_gnome_extensions():
    """
    Get list of all enabled GNOME extensions (user and system).
    Caches result in cnfg.enabled_gnome_exts for reuse.
    """
    # Return cached result if already fetched
    if cnfg.enabled_gnome_exts is not None:
        return cnfg.enabled_gnome_exts
    
    gnome_ext_cmd_exists = shutil.which('gnome-extensions') is not None
    gsettings_cmd_exists = shutil.which('gsettings') is not None
    
    # Prefer gnome-extensions CLI - it sees both user and system extensions
    if gnome_ext_cmd_exists:
        try:
            cmd_lst = ['gnome-extensions', 'list', '--enabled']
            output = subprocess.check_output(cmd_lst, stderr=DEVNULL)
            cnfg.enabled_gnome_exts = output.decode().strip().splitlines()
            debug("Used 'gnome-extensions' to get enabled extensions list")
            return cnfg.enabled_gnome_exts
        except subprocess.CalledProcessError as proc_err:
            error(f"'gnome-extensions list --enabled' failed:\n\t{proc_err}")
    else:
        debug("Command 'gnome-extensions' not found", ctx="CG")
    
    # Fallback: gsettings (only sees user-enabled extensions, not system defaults)
    if gsettings_cmd_exists:
        try:
            cmd_lst = ['gsettings', 'get', 'org.gnome.shell', 'enabled-extensions']
            output = subprocess.check_output(cmd_lst, stderr=DEVNULL)
            raw_output = output.decode().strip()
            if raw_output.startswith('[') and raw_output.endswith(']'):
                raw_exts = raw_output[1:-1].split(',')
                cnfg.enabled_gnome_exts = [
                    ext.strip().strip("'") for ext in raw_exts if ext.strip()
                ]
            else:
                cnfg.enabled_gnome_exts = []
            debug("Used 'gsettings' to get enabled extensions list (user-enabled only)")
            return cnfg.enabled_gnome_exts
        except subprocess.CalledProcessError as proc_err:
            error(f"'gsettings get enabled-extensions' failed:\n\t{proc_err}")
    else:
        debug("Command 'gsettings' not found", ctx="CG")
    
    error("Unable to get enabled GNOME extensions: no suitable command available")
    cnfg.enabled_gnome_exts = []
    return cnfg.enabled_gnome_exts


def check_gnome_wayland_exts():
    """
    Check for installed/enabled shell extensions compatible with the keymapper,
    for supporting app-specific remapping in Wayland+GNOME sessions.
    """
    if cnfg.DESKTOP_ENV != 'gnome':
        return

    wayland_ctx_extensions = [
        'focused-window-dbus@flexagoon.com',
        'window-calls-extended@hseliger.eu',
        'xremap@k0kubun.com',
    ]

    # Check for installed extensions
    user_ext_dir = os.path.expanduser('~/.local/share/gnome-shell/extensions')
    sys_ext_dir = '/usr/share/gnome-shell/extensions'

    installed_exts = []
    for ext_uuid in wayland_ctx_extensions:
        user_path = os.path.join(user_ext_dir, ext_uuid)
        sys_path = os.path.join(sys_ext_dir, ext_uuid)
        if os.path.exists(user_path) or os.path.exists(sys_path):
            installed_exts.append(ext_uuid)

    # Check for enabled extensions
    all_enabled_exts = get_enabled_gnome_extensions()
    enabled_exts = [ext for ext in installed_exts if ext in all_enabled_exts]

    if enabled_exts:
        print()
        print("A compatible GNOME shell extension is enabled for GNOME Wayland support. Good.")
        print(f"Enabled extension(s) found:\n  {enabled_exts}")
    elif installed_exts:
        print()
        print(cnfg.separator)
        print()
        print("A shell extension is installed for GNOME Wayland support, but it is not enabled:")
        print(f"  {installed_exts}")
        print("Enable any of the compatible GNOME shell extensions for GNOME Wayland support.")
        print("Without this, app-specific keymapping will NOT work in a GNOME Wayland session.")
        print("  (See 'Requirements' section in the Toshy README.)")
        ask_for_attn_on_info()
    else:
        print()
        print(cnfg.separator)
        print()
        print("No compatible shell extensions for GNOME Wayland session support were found...")
        print("Install any of the compatible GNOME shell extensions for GNOME Wayland support.")
        print("Without this, app-specific keymapping will NOT work in a GNOME Wayland session.")
        print("  (See 'Requirements' section in the Toshy README.)")
        ask_for_attn_on_info()


def check_gnome_indicator_ext():
    """
    Check for an installed and enabled GNOME shell extension for supporting
    the display of app indicators in the top bar.
    """
    if cnfg.DESKTOP_ENV != 'gnome':
        return

    indicator_extensions = [
        'appindicatorsupport@rgcjonas.gmail.com',
        'ubuntu-appindicators@ubuntu.com',
        'TopIcons@phocean.net',
        'top-icons-redux@pop-planet.info',
        'trayIconsReloaded@selfmade.pl',
    ]

    # Check for installed extensions
    user_ext_dir = os.path.expanduser('~/.local/share/gnome-shell/extensions')
    sys_ext_dir = '/usr/share/gnome-shell/extensions'

    installed_exts = []
    for ext_uuid in indicator_extensions:
        user_path = os.path.join(user_ext_dir, ext_uuid)
        sys_path = os.path.join(sys_ext_dir, ext_uuid)
        if os.path.exists(user_path) or os.path.exists(sys_path):
            installed_exts.append(ext_uuid)

    # Check for enabled extensions
    all_enabled_exts = get_enabled_gnome_extensions()
    enabled_exts = [ext for ext in installed_exts if ext in all_enabled_exts]

    if enabled_exts:
        print()
        print("A compatible GNOME shell extension is enabled for system tray icons. Good.")
        print(f"Enabled extension(s) found:\n  {enabled_exts}")
    elif installed_exts:
        print()
        print(cnfg.separator)
        print()
        print("There is a system tray indicator extension installed, but it is not enabled:")
        print(f"  {installed_exts}")
        print("Without an extension enabled, the Toshy icon will NOT appear in the top bar.")
        print("  (See 'Requirements' section in the Toshy README.)")
        ask_for_attn_on_info()
    else:
        print()
        print(cnfg.separator)
        print()
        print("Install any compatible GNOME shell extension for system tray icon support.")
        print("Without an extension enabled, the Toshy icon will NOT appear in the top bar.")
        print("  (See 'Requirements' section in the Toshy README.)")
        ask_for_attn_on_info()


def check_kde_app_switcher():
    """
    Utility function to check for the Application Switcher KWin script that enables 
    grouped-application-windows task switching in KDE/KWin environments.
    """
    if not cnfg.DESKTOP_ENV == 'kde':
        return

    script_path = os.path.expanduser('~/.local/share/kwin/scripts/applicationswitcher')

    if os.path.exists(script_path):
        print()
        print("Application Switcher KWin script is installed. Good.")
        # Reinstall/upgrade the Application Switcher KWin script to make sure it is current
        cnfg.app_switcher = True
    else:
        print()
        result = input(
            "Install a KWin script that enables macOS-like grouped window switching? [Y/n]: ")
        if result.casefold() in ['y', 'yes', '']:
            cnfg.app_switcher = True
        elif result.casefold() not in ['n', 'no']:
            error("Invalid input. Run the installer and try again.")
            safe_shutdown(1)


def elevate_privileges():
    """Elevate privileges early in the installer process, or invoke unprivileged install"""

    print()     # blank line to separate
    max_attempts = 3

    # Ask politely if user is admin to avoid causing an "incident" report unnecessarily
    for _ in range(max_attempts):
        response = input(
            f'Can user "{cnfg.user_name}" run admin commands (via sudo/doas/run0)? [y/n]: ')
        if response.casefold() in ['y', 'n']:
            # response is valid, so break loop and proceed with appropriate actions below
            break
        else:
            print()
            error("Response invalid. Valid responses are 'y' or 'n'.")
            print()     # blank line for separation, then continue loop
    else:   # this "else" belongs to the "for" loop
        print()
        error('Response invalid. Max attempts reached.')
        safe_shutdown(1)

    if response.casefold() == 'y':
        cnfg.detect_elevation_command()     # Get the actual command for elevated privileges

        # Do this here, only if the privilege elevation command is 'sudo':
        # Invalidate any `sudo` ticket that might be hanging around, to maximize 
        # the length of time before `sudo` might demand the password again
        if cnfg.priv_elev_cmd == 'sudo':
            try:
                subprocess.run(['sudo', '-k'], check=True)
            except subprocess.CalledProcessError as proc_err:
                error(f"ERROR: 'sudo' found, but 'sudo -k' did not work. Very strange.\n{proc_err}")

        call_attn_to_pwd_prompt_if_needed()
        try:
            cmd_lst = [cnfg.priv_elev_cmd, 'bash', '-c', 'echo -e "\nUsing elevated privileges..."']
            subprocess.run(cmd_lst, check=True)
        except subprocess.CalledProcessError as proc_err:
            print()
            if cnfg.prep_only:
                print()
                error(f'ERROR: Problem invoking "{cnfg.priv_elev_cmd}" command. Not an admin user?')
                error(f'Only a user with "{cnfg.priv_elev_cmd}" access can use "prep-only" command.')
            error(f'Problem invoking the "{cnfg.priv_elev_cmd}" command.')
            print('Try answering "n" to admin question next time.')
            safe_shutdown(1)
    elif response.casefold() == 'n':
        secret_code = generate_secret_code()
        print('\n\n')
        print(fancy_str(
            'ALERT!  ALERT!  ALERT!  ALERT!  ALERT!  ALERT!  ALERT!  ALERT!  ALERT!  ALERT!\n',
            color_name='red', bold=True))
        md_wrapped_str = md_wrap(f"""
        The secret code for this run is "{secret_code}". You will need this.

        It is possible to install as an unprivileged user, but only after an
        admin user first runs the full install or a "prep-only" sequence.
        The admin user must install from a full desktop session, or from
        a "su --login adminuser" shell instance. The admin user can do
        just the "prep" steps with:
        
        ./{this_file_name} prep-only
        
        ... instead of using:
        
        ./{this_file_name} install
        
        Use the "prep-only" command if it is not desired that Toshy
        should also run when the admin user logs into a desktop session.
        When using "su --login adminuser", that user will also need to
        download an independent copy of the Toshy zip file to install from,
        using a "wget" or "curl" command. Or use "sudo/doas/run0" to copy
        the zip file from the unprivileged user's Downloads folder.
        See the Wiki for a better example of the full "prep-only" sequence
        with a separate admin user.
        """)
        print(md_wrapped_str)
        print()
        md_wrapped_str = md_wrap(width=55, text="""
        If you understand everything written above or already took care 
        of prepping the system and want to proceed with an unprivileged 
        install, enter the secret code: 
        """)
        response = input(md_wrapped_str)
        if response == secret_code:
            # set a flag to bypass functions that do system "prep" work with elevated privileges
            cnfg.unprivileged_user = True
            print()
            print("Good code. Continuing with an unprivileged install of Toshy user components...")
            return
        else:
            print()
            error('Code does not match! Try the installer again after installing Toshy \n'
                    '     first using an admin user that has access to "sudo/doas/run0".')
            safe_shutdown(1)


#####################################################################################################
###   START OF NATIVE PACKAGE INSTALLER SECTION
#####################################################################################################


distro_groups_map = {

    # separate references for RHEL types versus Fedora types
    'fedora-based':             ["fedora", "fedoralinux", "nobara", "ultramarine"],
    'rhel-based':               ["almalinux", "centos", "eurolinux", "oreon", "rhel", "rocky"],

    # separate references for Fedora immutables using rpm-ostree
    'fedora-immutables':        ["bazzite", "kinoite", "silverblue"],

    # separate references for Tumbleweed types, Leap types, MicroOS types
    'tumbleweed-based':         ["opensuse-tumbleweed", "tumbleweed"],
    'leap-based':               ["leap", "opensuse-leap"],
    'microos-based':            ["opensuse-aeon", "opensuse-kalpa", "opensuse-microos"],

    'mandriva-based':           ["openmandriva"],

    'mageia-based':             ["mageia"],

    'ubuntu-based':             ["elementary", "mint", "neon", "pop", "tuxedo", "ubuntu", "zorin"],

    # The 'linuxmint' distro ID will not be shown by `toshy-env`, environment module 
    # normalizes to 'mint' for matching in the config file.
    'debian-based':             ["debian", "deepin", "kali", "linuxmint", "lmde",
                                    "peppermint", "q4os"],

    'arch-based':               ["arch", "archarm", "arcolinux", "cachyos", "endeavouros",
                                    "garuda", "manjaro"],

    'solus-based':              ["solus"],

    'void-based':               ["void"],

    'chimera-based':            ["chimera"],

    'alt-based':                ["altlinux"],

    'aerynos-based':            ["aerynos"],

    'gentoo-based':             ["calculate", "gentoo", "redcore"],

    # Attempted to add and test KaOS Linux. Result:
    # KaOS is NOT compatible with this project. 
    # No packages provide "evtest", "libappindicator", "zenity". 
    # The KaOS repos seem highly restricted to only Qt/KDE related packages. 

    # Add more as needed...
}


# Checklist of distro type representatives with 
# '/usr/bin/gdbus' pre-installed in clean VM:
# 
# - AlmaLinux 8.x                               [Provided by 'glib2']
# - AlmaLinux 9.x                               [Provided by 'glib2']
# - CentOS 7                                    [Provided by 'glib2']
# - Fedora                                      [Provided by 'glib2']
# - KDE Neon User Edition (Ubuntu 22.04 LTS)    [Provided by 'libglib2.0-bin']
# - Manjaro KDE (Arch-based)                    [Provided by 'glib2']
# - OpenMandriva Lx 5.0 (Plasma Slim)           [Provided by 'glib2.0-common']
# - openSUSE Leap 15.6                          [Provided by 'glib2-tools']
# - Ubuntu 20.04 LTS                            [Provided by 'libglib2.0-bin']
# - Void Linux (rolling)                        [Provided by 'glib']
# 


pkg_groups_map = {

    # NOTE: Do not add 'gnome-shell-extension-appindicator' to Fedora/RHELs.
    #       This will install extension but requires logging out of GNOME to activate.
    #       Also, installing DE-specific packages is probably a bad idea.
    'fedora-based':        ["cairo-devel", "cairo-gobject-devel",
                            "dbus-daemon", "dbus-devel",
                            "evtest",
                            "gcc", "git", "gobject-introspection-devel",
                            "libappindicator-gtk3", "libjpeg-turbo-devel", "libnotify",
                                "libxkbcommon-devel",
                            "python3-dbus", "python3-devel", "python3-pip", "python3-tkinter",
                            "systemd-devel",
                            "wayland-devel",
                            "xset",
                            "zenity"],

    # NOTE: Do not add 'gnome-shell-extension-appindicator' to Fedora/RHELs.
    #       This will install extension but requires logging out of GNOME to activate.
    #       Also, installing DE-specific packages is probably a bad idea.
    'rhel-based':          ["cairo-devel", "cairo-gobject-devel",
                            "dbus-daemon", "dbus-devel",
                            "gcc", "git", "gobject-introspection-devel",
                            "libappindicator-gtk3", "libjpeg-turbo-devel", "libnotify",
                                "libxkbcommon-devel",
                            "python3-dbus", "python3-devel", "python3-pip", "python3-tkinter",
                            "systemd-devel",
                            "wayland-devel",
                            # The 'xdg-open' and 'xdg-mime' utils were missing on CentOS Stream 10,
                            # necessitating adding 'xdg-utils' as dependency. Very unusual.
                            "xdg-utils", "xset",
                            "zenity"],

    # NOTE: Do not add 'gnome-shell-extension-appindicator' to Fedora/RHELs.
    #       This will install extension but requires logging out of GNOME to activate.
    #       Also, installing DE-specific packages is probably a bad idea.
    'fedora-immutables':   ["cairo-devel", "cairo-gobject-devel",
                            "dbus-daemon", "dbus-devel",
                            "evtest",
                            "gcc", "git", "gobject-introspection-devel",
                            "libappindicator-gtk3", "libjpeg-turbo-devel", "libnotify",
                                "libxkbcommon-devel",
                            "python3-dbus", "python3-devel", "python3-pip", "python3-tkinter",
                            "systemd-devel",
                            "wayland-devel",
                            "xset",
                            "zenity"],

    # NOTE: for openSUSE (Tumbleweed, not applicable to Leap):
    # How to get rid of the need to use specific version numbers in packages: 
    # pkgconfig(packagename)>=N.nn (version symbols optional)
    # How to query a package to see what the equivalent pkgconfig(packagename) syntax would be:
    # rpm -q --provides packagename | grep -i pkgconfig
    'tumbleweed-based':    ["cairo-devel",
                            "dbus-1-daemon", "dbus-1-devel",
                            "gcc", "git", "gobject-introspection-devel",
                            "libappindicator3-devel", "libnotify-tools", "libxkbcommon-devel",
                            # f"python{py_pkg_ver_str}-dbus-python-devel",
                            "python3-dbus-python-devel",
                            # f"python{py_pkg_ver_str}-devel",
                            "python3-devel",
                            # f"python{py_pkg_ver_str}-tk",
                            "python3-tk",
                            "systemd-devel",
                            "tk", "typelib-1_0-AyatanaAppIndicator3-0_1",
                            "zenity"],

    # TODO: update Leap Python package versions as it makes newer Python available
    'leap-based':          ["cairo-devel",
                            "dbus-1-devel",
                            "gcc", "git", "gobject-introspection-devel",
                            "libappindicator3-devel", "libnotify-tools", "libxkbcommon-devel",
                            "python311",
                            "python311-dbus-python-devel",
                            "python311-devel",
                            "python311-tk",
                            "systemd-devel",
                            "tk", "typelib-1_0-AyatanaAppIndicator3-0_1",
                            "zenity"],

    # NOTE: This is a copy of Tumbleweed-based package list! For use with 'transactional-update'.
    # But this needs to use the versioned package names because we are checking with 'rpm -q'.
    'microos-based':       ["cairo-devel",
                            "dbus-1-daemon", "dbus-1-devel",
                            "gcc", "git", "gobject-introspection-devel",
                            "libappindicator3-devel", "libnotify-tools", "libxkbcommon-devel",
                            f"python{py_pkg_ver_str}-dbus-python-devel",
                            # "python3-dbus-python-devel",
                            f"python{py_pkg_ver_str}-devel",
                            # "python3-devel",
                            f"python{py_pkg_ver_str}-tk",
                            # "python3-tk",
                            "systemd-devel",
                            "tk", "typelib-1_0-AyatanaAppIndicator3-0_1",
                            "zenity"],

    'mandriva-based':      ["cairo-devel",
                            "dbus-daemon", "dbus-devel",
                            "git", "gobject-introspection-devel", "gtk4-devel",
                            "lib64adwaita-devel", "lib64ayatana-appindicator3_1",
                                "lib64ayatana-appindicator3-gir0.1", "lib64cairo-gobject2",
                                "lib64python-devel", "lib64systemd-devel", "lib64xkbcommon-devel",
                                "libnotify",
                            "python-dbus", "python-dbus-devel", "python-ensurepip", "python3-pip",
                            "task-devel", "tkinter",
                            "xset",
                            "zenity"],

    'mageia-based':        ["cairo-devel",
                            "dbus-devel",
                            "evtest", 
                            "gcc", "git", "gobject-introspection-devel",
                            "libappindicator-gtk3", "lib64ayatanaappindicator3-gir0.1",
                                "lib64cairo-gir1.0", "libnotify", "libxkbcommon-devel",
                            "python3-dbus", "python3-devel", "python3-pip", "python3-tkinter",
                            "systemd-devel",
                            "wayland-devel",
                            "xset", 
                            "zenity"],

    # Separately handled with distro quirks handlers for Debian and Ubuntu systems, due
    # to needing to assess availability on the system:
    # 'gir1.2-adw-1', 'gir1.2-gtk-4.0',
    # 'libgirepository1.0-dev', 'libgirepository-2.0-dev',
    'ubuntu-based':        ["curl",
                            "git", "gir1.2-ayatanaappindicator3-0.1",
                            # New Ayatana appindicator glib package will be needed at some point:
                            # Ref: https://github.com/AyatanaIndicators/libayatana-appindicator-glib
                            # "gir1.2-ayatanaappindicatorglib-2.0",
                            "input-utils",
                            "libcairo2-dev", "libdbus-1-dev", "libjpeg-dev", "libnotify-bin", 
                                "libsystemd-dev", "libwayland-dev", "libxkbcommon-dev",
                            "python3-dbus", "python3-dev", "python3-pip", "python3-tk",
                                "python3-venv",
                            "zenity"],

    # Need this KWin package for "Large Icons" task switcher UI on stock Debian.
    # Handled with a distro quirks handler for Debian-KDE systems.
    # "kwin-addons",
    # Separately handled with distro quirks handlers for Debian and Ubuntu systems, due
    # to needing to assess availability on the system:
    # 'gir1.2-adw-1', 'gir1.2-gtk-4.0',
    # 'libgirepository1.0-dev', 'libgirepository-2.0-dev',
    'debian-based':        ["curl",
                            "git", "gir1.2-ayatanaappindicator3-0.1",
                            # New Ayatana appindicator glib package will be needed at some point:
                            # Ref: https://github.com/AyatanaIndicators/libayatana-appindicator-glib
                            # "gir1.2-ayatanaappindicatorglib-2.0",
                            "input-utils",
                            "libcairo2-dev", "libdbus-1-dev", "libjpeg-dev", "libnotify-bin", 
                                "libsystemd-dev", "libwayland-dev", "libxkbcommon-dev",
                            "python3-dbus", "python3-dev", "python3-pip", "python3-tk",
                                "python3-venv",
                            "zenity"],

    'arch-based':          ["cairo",
                            "dbus",
                            "evtest",
                            "gcc", "git", "gobject-introspection",
                            "libappindicator-gtk3", "libnotify", "libxkbcommon",
                            "pkg-config", "python", "python-dbus", "python-pip",
                            "systemd",
                            "tk",
                            "zenity"],

    'solus-based':         ["gcc", "git",
                            "libayatana-appindicator", "libcairo-devel", "libnotify",
                                "libxkbcommon-devel",
                            "pip", "python3-dbus", "python3-devel", "python3-tkinter",
                            # Solus 4.8 suddenly switched to "Polaris" repo, changed
                            # package name from 'python-dbus-devel' to 'python3-dbus-devel'.
                            # Solus distro quirks handler will check for available packages.
                                "python3-dbus-devel", "python-gobject-devel",
                            "systemd-devel",
                            "zenity"],

    'void-based':          ["cairo-devel", "curl",
                            "dbus-devel",
                            "evtest",
                            "gcc", "git",
                            "libayatana-appindicator-devel", "libgirepository-devel", "libnotify",
                                "libxkbcommon-devel",
                            "pkg-config", "python3-dbus", "python3-devel", "python3-pip",
                                "python3-pkgconfig", "python3-tkinter",
                            "wayland-devel", "wget",
                            "xset",
                            "zenity"],

    'chimera-based':       ["cairo-devel", "clang", "cmake",
                            "dbus-devel", 
                            "git", "gobject-introspection-devel",
                            "libayatana-appindicator-devel", "libnotify", "libxkbcommon-devel",
                            "pkgconf", "python-dbus", "python-devel", "python-evdev", "python-pip",
                            "zenity"],

    'alt-based':           ["evtest",
                            "gcc", "git", "gobject-introspection-devel",
                            "libappindicator-gtk3", "libcairo-devel", "libcairo-gobject-devel",
                                "libdbus-devel", "libnotify", "libxkbcommon-devel",
                            "python3-dev", "python3-module-dbus", "python3-module-pip",
                                "python3-modules-tkinter",
                            "systemd-devel",
                            "xset",
                            "zenity"],

    'aerynos-based':       ["cairo-gobject-devel", "clang", "curl",
                            "git", "glib2-devel",
                            "evtest",
                            "libayatana-appindicator", "libxkbcommon-devel",
                            "python-cairo-devel", "python-dbus-devel", "python-devel",
                                "python-evdev", "python-pip", "python-pkgconfig",
                                "python-pygobject-devel", "python-setuptools", "python-virtualenv", 
                            "zenity"],

    'gentoo-based':        [
                            "dev-libs/wayland-protocols",
                            "x11-libs/libxkbcommon",
                            "libnotify",
                            "x11-apps/xset",
                            "x11-libs/libnotify",

                            ],

}

extra_pkgs_map = {
    # Add a 2-tuple (2 quoted items in parentheses, separated by a comma) with 
    # distro name (ID), major version (or None)as the dict key,  and
    # then a list (in brackets) of  packages to be added as the dict value...
    # ('distro_id', '22'):        ["pkg1", "pkg2", ...],
    # ('distro_id', None):        ["pkg1", "pkg2", ...],
}

remove_pkgs_map = {
    # Add a 2-tuple (2 quoted items in parentheses, separated by a comma) with 
    # distro name (ID), major version (or None) as the dict key, and
    # then a list (in brackets) of packages to be removed as the dict value...
    # ('distro_id', '22'): ["pkg1", "pkg2", ...],
    # ('distro_id', None): ["pkg1", "pkg2", ...],
    ('centos', '7'):            ['dbus-daemon', 'gnome-shell-extension-appindicator'],
    ('deepin', None):           ['input-utils'],
}


pip_pkgs   = [

    ############################################################################################
    # First section are packages needed directly by one or more Toshy components.

    "dbus-python",              # Python bindings for D-Bus IPC comms with desktop environments
    "lockfile",                 # Makes it easier to keep multiple apps/icons from appearing
    "psutil",                   # For checking running processes (window manager, KVM apps, ect.)

    # NOTE: 
    # Pygobject was pinned to 3.44.1 (or earlier) in Python quirks handlers, to get through
    # the install on RHEL 8.x and clones, and earlier CentOS [Stream] distros. This started
    # causing installation problems in late 2025 distro releases (Debian/Ubuntu mainly).
    # Now it needs to be pinned for some distro versions to <=3.50.0, to allow it to still
    # work with systems that do not have girepository 2.0 packages yet.
    "pygobject",                # Python bindings for GObject/GTK (for tray icon and notifications)

    # NOTE: This was too much of a sledgehammer, changing both "program" and "command" strings
    # "setproctitle",             # Allows changing how the process looks in "top" apps

    "sv_ttk",                   # Modern-ish dark/light theme for tkinter GUI preferences app
    "systemd-python",           # Provides bindings to interact with systemd services and journal
    "tk",                       # For GUI preferences app
    "watchdog",                 # For setting observers on log files, preferences db file, etc.

    # NOTE: Version 1.5 of 'xkbcommon' introduced breaking API changes: XKB_CONTEXT_NO_SECURE_GETENV
    # https://github.com/sde1000/python-xkbcommon/issues/23
    # Need to pin version to less than v1.1 to avoid errors installing 'xkbcommon' on older distros.
    # TODO: Revisit this pinning in... 2028.
    "xkbcommon<1.1",            # Python binding for libxkbcommon (keyboard mapping library)

    # NOTE: WE CANNOT USE `xkbregistry` DUE TO CONFUSION AMONG SUPPORTING NATIVE PACKAGES
    # "xkbregistry",

    ############################################################################################
    # Everything below here is just to make the keymapper (xwaykeyz) install smoother.

    "appdirs",                  # Get appropriate platform-specific directories for app data/config
    "evdev",                    # Interface with Linux input system for keyboard/mouse event handling
    "hyprpy",                   # Python binding for Hyprland Wayland compositor
    "i3ipc",                    # Interface with i3/sway window managers via their IPC protocol
    "inotify-simple",           # Monitor filesystem events
    "ordered-set",              # Set implementation that preserves insertion order (for key combos)

    # TODO: Check on 'python-xlib' project by mid-2025 to see if this bug is fixed:
    #   [AttributeError: 'BadRRModeError' object has no attribute 'sequence_number']
    # If the bug is fixed, remove pinning to v0.31 here.
    # But it does not appear that the bug is ever likely to be fixed.
    "python-xlib==0.31",        # Python interface to X11 library for X11 session support

    "pywayland",                # Python bindings for Wayland display protocol
    "six"                       # Python 2/3 compatibility library (dependency for other packages)

]


def get_supported_distro_ids_lst():
    """Helper function to return the full list of distro IDs."""
    distro_list = []

    for group in distro_groups_map.values():
        distro_list.extend(group)

    return sorted(distro_list)


def get_supported_distro_ids_idx() -> str:
    """Utility function to return list of available distro names (IDs)"""
    distro_list = []

    for group in distro_groups_map.values():
        distro_list.extend(group)

    sorted_distro_list = sorted(distro_list)
    prev_char: str = sorted_distro_list[0][0]
    # start index with the initial letter
    distro_index = "\t" + prev_char.upper() + ": "
    line_length = len(distro_index)             # initial line length

    for distro in sorted_distro_list:
        if distro[0] != prev_char:
            distro_index = distro_index[:-2]    # remove last comma and space
            line_length -= 2
            distro_index += "\n\t" + distro[0].upper() + ": "
            line_length = len(distro[0]) + 2    # reset line length
            prev_char = distro[0]
        
        next_distro_with_comma = distro + ", "
        if line_length + len(next_distro_with_comma) > 80:
            distro_index += "\n\t    "          # insert newline and tab/spaces for continuation
            line_length = len("\t    ")         # reset line length to indent size

        distro_index += next_distro_with_comma
        line_length += len(next_distro_with_comma)

    return distro_index[:-2]  # remove the last comma and space


def get_supported_distro_ids_cnt() -> int:
    """Utility function to return the total count of supported distro IDs."""
    return len(get_supported_distro_ids_lst())


def get_supported_distro_types_cnt() -> int:
    """Utility function to return the total count of supported distro types (not individual IDs)"""
    return len(distro_groups_map.keys())


def get_supported_pkg_managers_cnt() -> int:
    """Utility function to return the total count of package manager methods available."""
    return len([
        method for method in dir(PackageInstallDispatcher)
        if method.startswith('install_on_') and method.endswith('_distro')
    ])


def exit_with_invalid_distro_error(pkg_mgr_err=None):
    """Utility function to show error message and exit when distro is not valid"""
    print()
    error(f'ERROR: Installer does not know how to handle distro: "{cnfg.DISTRO_ID}"')
    if pkg_mgr_err:
        error('ERROR: No valid package manager logic was encountered for this distro.')
    # print()
    # print(f'Try some options in "./{this_file_name} --help".')
    print()
    print(
        f'Try one of these with "--override-distro" option:'
        f'\n\n{get_supported_distro_ids_idx()}'
    )
    safe_shutdown(1)


def is_dnf_repo_enabled(repo_name):
    """
    Utility function that checks if a specified DNF repository is present and enabled.
    """
    try:
        native_pkg_installer.check_for_pkg_mgr_cmd('dnf')
        cmd_lst = ["dnf", "repolist", "enabled"]
        result = subprocess.run(cmd_lst, stdout=PIPE, stderr=PIPE, 
                                universal_newlines=True, check=True)
        return repo_name.casefold() in result.stdout.casefold()
    except subprocess.CalledProcessError as proc_err:
        error(f"There was a problem checking if {repo_name} repo is enabled:\n{proc_err}")
        safe_shutdown(1)


class DistroQuirksHandler:
    """
    Utility class to contain static methods for prepping specific distro variants that
    need some additional prep work before invoking the native package installer.
    """

    @staticmethod
    def add_available_deb_pkgs(pkg_list: list, description: str = "optional packages"):
        """
        Check which packages from a list exist in repos and add them to the install list.
        Provides informative output about what was found/not found.
        
        Args:
            pkg_list: List of package names to check
            description: Description for logging (e.g., "GTK4 GUI support packages")
        """
        if not pkg_list:
            return
        
        print(f"Checking availability of {description}...")
        
        available = []
        unavailable = []
        
        for pkg in pkg_list:
            if DistroQuirksHandler.deb_pkg_exists_in_repos(pkg):
                available.append(pkg)
            else:
                unavailable.append(pkg)
        
        if available:
            print(f"  Found and adding: {', '.join(available)}")
            cnfg.pkgs_for_distro += available
        
        if unavailable:
            print(f"  Not available (skipping): {', '.join(unavailable)}")

    @staticmethod
    def deb_pkg_exists_in_repos(pkg_name: str) -> bool:
        """
        Check if a package exists in Debian/Ubuntu repositories.
        
        Args:
            pkg_name: Package name to check (e.g., 'libgirepository-2.0-dev')
        
        Returns:
            True if package exists in repos, False otherwise
        """
        deb_distros = (
            distro_groups_map.get('debian-based', []) +
            distro_groups_map.get('ubuntu-based', [])
        )
        
        if cnfg.DISTRO_ID not in deb_distros:
            return True  # Not a Debian/Ubuntu system, assume package handling is fine
        
        try:
            result = subprocess.run(
                ['apt-cache', 'show', pkg_name],
                stdout=DEVNULL, stderr=DEVNULL,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    @staticmethod
    def update_centos_repos_to_vault():
        """
        CentOS 7 was end of life on June 30, 2024
        Centos Stream 8 was end of builds on May 31, 2024
        
        https://mirrorlist.centos.org suddenly ceased to exist, making it impossible
        to install Toshy with the current setup. 
        We need to fix the repos to continue being able to 
        install on CentOS 7 and CentOS Stream 8 
        
        Online advice for fixing this issue manually:
        sed -i s/mirror.centos.org/vault.centos.org/g /etc/yum.repos.d/*.repo
        sed -i s/^#.*baseurl=http/baseurl=http/g /etc/yum.repos.d/*.repo
        sed -i s/^mirrorlist=http/#mirrorlist=http/g /etc/yum.repos.d/*.repo
        """

        print('Updating CentOS repos to use the CentOS Vault...')
        call_attn_to_pwd_prompt_if_needed()
        repo_files              = glob.glob('/etc/yum.repos.d/*.repo')
        commands                = []

        # Keep statically using 'sudo' here because this is only used on old CentOS distros
        # No need to adapt to doas/run0 or Chimera's BSD userland utilities
        commands += [
            f"sudo sed -i 's/mirror.centos.org/vault.centos.org/g' {file_path}"
            for file_path in repo_files ]
        commands += [
            f"sudo sed -i 's/^#.*baseurl=http/baseurl=http/g' {file_path}"
            for file_path in repo_files ]
        commands += [
            f"sudo sed -i 's/^\\(mirrorlist=http\\)/#\\1/' {file_path}"
            for file_path in repo_files ]
        
        for command in commands:
            try:
                subprocess.run(command, shell=True, check=True)
                # print(f"Executed: {command}")
            except subprocess.CalledProcessError as e:
                print(f"Failed to execute: {command}\nError: {e}")
                safe_shutdown(1)  # Ensure safe_shutdown is adequately defined

        print("All repository files updated successfully.")

        # Now that repo URLs have been changed, we need to clear and refresh the cache
        # Seems unlikely that 'yum' would be removed, but 'dnf' is not pre-installed on CentOS 7.
        # We'll check for both before attempting to refresh caches, just to be safe. 

        if shutil.which('yum'):
            try:
                subprocess.run([cnfg.priv_elev_cmd, 'yum', 'clean', 'all'], check=True)
                subprocess.run([cnfg.priv_elev_cmd, 'yum', 'makecache'], check=True)
                print("Yum cache has been refreshed.")
            except subprocess.CalledProcessError as e:
                error(f"Failed to refresh yum cache: \n\t{e}")
                safe_shutdown(1)

        if shutil.which('dnf'):
            try:
                subprocess.run([cnfg.priv_elev_cmd, 'dnf', 'clean', 'all'], check=True)
                subprocess.run([cnfg.priv_elev_cmd, 'dnf', 'makecache'], check=True)
                print("DNF cache has been refreshed.")
            except subprocess.CalledProcessError as e:
                error(f"Failed to refresh dnf cache: \n\t{e}")
                safe_shutdown(1)

    @staticmethod
    def handle_quirks_CentOS_7():
        print('Doing prep/checks for CentOS 7...')

        # Avoid trying to install 'python3-dbus' (native pkg) and 'dbus-python' (pip pkg)
        cnfg.pkgs_for_distro = [pkg for pkg in cnfg.pkgs_for_distro if 'dbus' not in pkg]
        cnfg.no_dbus_python = True

        native_pkg_installer.check_for_pkg_mgr_cmd('yum')
        yum_cmd_lst = [cnfg.priv_elev_cmd, 'yum', 'install', '-y']
        if py_interp_ver_tup >= (3, 8):
            print(f"Good, Python version is 3.8 or later: "
                    f"'{cnfg.py_interp_ver_str}'")
        else:
            # Check for SCL repo file presence
            scl_repo_files = [  '/etc/yum.repos.d/CentOS-SCLo-scl.repo',
                                '/etc/yum.repos.d/CentOS-SCLo-scl-rh.repo']
            scl_repo_present = all(os.path.exists(repo) for repo in scl_repo_files)

            if not scl_repo_present:
                try:
                    # This will install repo files that need to be fixed post-CentOS 7 EOL
                    scl_repo = ['centos-release-scl']
                    subprocess.run(yum_cmd_lst + scl_repo, check=True)
                    DistroQuirksHandler.update_centos_repos_to_vault()
                except subprocess.CalledProcessError as proc_err:
                    error(f'ERROR: (CentOS 7-specific) Problem installing SCL repo.\n\t')
                    safe_shutdown(1)

            try:
                py38_pkgs = [   'rh-python38',
                                'rh-python38-python-devel',
                                'rh-python38-python-tkinter',
                                'rh-python38-python-wheel-wheel'    ]
                subprocess.run(yum_cmd_lst + py38_pkgs, check=True)
                #
                # set new Python interpreter version and path to reflect what was installed
                cnfg.py_interp_path     = '/opt/rh/rh-python38/root/usr/bin/python3.8'
                cnfg.py_interp_ver_str  = '3.8'
                # avoid using systemd packages/services for CentOS 7
                cnfg.systemctl_present = False
            except subprocess.CalledProcessError as proc_err:
                print()
                error(f'ERROR: (CentOS 7-specific) Problem installing/enabling Python 3.8:'
                        f'\n\t{proc_err}')
                safe_shutdown(1)
        # use yum to install dnf package manager
        try:
            subprocess.run(yum_cmd_lst + ['dnf'], check=True)
        except subprocess.CalledProcessError as proc_err:
            print()
            error(f'ERROR: Failed to install DNF package manager.\n\t{proc_err}')
            safe_shutdown(1)

    @staticmethod
    def handle_quirks_CentOS_Stream_8():
        print('Doing prep/checks for CentOS Stream 8...')

        # Tell user to handle this with external script
        # self.update_centos_repos_to_vault()

        min_mnr_ver = cnfg.curr_py_rel_ver_mnr - 3           # check up to 2 vers before current
        max_mnr_ver = cnfg.curr_py_rel_ver_mnr + 3           # check up to 3 vers after current
        py_minor_ver_rng = range(max_mnr_ver, min_mnr_ver, -1)
        if py_interp_ver_tup < cnfg.curr_py_rel_ver_tup:
            print(f"Checking for appropriate Python version on system...")
            for check_py_minor_ver in py_minor_ver_rng:
                if shutil.which(f'python3.{check_py_minor_ver}'):
                    cnfg.py_interp_path = shutil.which(f'python3.{check_py_minor_ver}')
                    cnfg.py_interp_ver_str = f'3.{check_py_minor_ver}'
                    print(f'Found Python version {cnfg.py_interp_ver_str} available.')
                    break
            else:
                error(  f'ERROR: Did not find any appropriate Python interpreter version.')
                safe_shutdown(1)
        try:
            # for dbus-python
            subprocess.run([cnfg.priv_elev_cmd, 'dnf', 'install', '-y',
                            f'python{cnfg.py_interp_ver_str}-devel'], check=True)
            # for Toshy Preferences GUI app
            subprocess.run([cnfg.priv_elev_cmd, 'dnf', 'install', '-y',
                            f'python{cnfg.py_interp_ver_str}-tkinter'], check=True)
        except subprocess.CalledProcessError as proc_err:
            error(f'ERROR: Problem installing necessary packages on CentOS Stream 8:'
                    f'\n\t{proc_err}')
            safe_shutdown(1)

    @staticmethod
    def handle_quirks_Debian():
        print('Doing prep/checks for Debian-based distros...')

        # Make sure we only handle these quirks in the correct distros
        if cnfg.DISTRO_ID not in distro_groups_map['debian-based']:
            error('Debian quirks handler called, but this is not Debian-based?')
            safe_shutdown(1)

        # Check for and add optional packages for GTK4 GUI support
        gtk4_packages = [
            'gir1.2-adw-1',             # For Adwaita/GTK4 GUI (Debian 12+, Ubuntu 22.04+)
            'gir1.2-gtk-4.0',           # For GTK4 GUI support (Debian 11+, Ubuntu 21.10+)
            'libgirepository1.0-dev',   # For PyGObject with girepository-1.0 (Debian <13, Ubuntu <24.04)
            'libgirepository-2.0-dev',  # For PyGObject with girepository-2.0 (Debian 13+, Ubuntu 24.04+)
        ]
        DistroQuirksHandler.add_available_deb_pkgs(gtk4_packages, "GTK4 GUI support packages")

        # This quirk is just for stock Debian with KDE, so it only checks for 'debian' as
        # distro ID, instead of DISTRO_ID in "debian-based".
        if cnfg.DISTRO_ID == 'debian' and cnfg.DESKTOP_ENV == 'kde':
            # Need to add 'kwin-addons' package to get "Large Icons" task switcher UI in KDE
            cnfg.pkgs_for_distro += ['kwin-addons']

    @staticmethod
    def handle_quirks_RHEL_8_and_9():
        print('Doing prep/checks for RHEL 8/9 type distro...')

        def get_newest_python_version():
            """Utility function to find the latest Python available on RHEL 8 and 9 distro types"""
            # TODO: Add higher version if ever necessary (keep minimum 3.8)
            potential_versions = ['3.17', '3.16', '3.15', '3.14', '3.13',
                                    '3.12', '3.11', '3.10', '3.9', '3.8']

            for version in potential_versions:
                # check if the version is already installed
                if shutil.which(f'python{version}'):
                    cnfg.py_interp_path     = f'/usr/bin/python{version}'
                    cnfg.py_interp_ver_str  = version
                    break
                # try to install the corresponding packages
                cmd_lst = [cnfg.priv_elev_cmd, 'dnf', 'install', '-y']
                pkg_lst = [
                    f'python{version}',
                    f'python{version}-devel',
                    f'python{version}-pip',
                    f'python{version}-tkinter'
                ]
                try:
                    subprocess.run(cmd_lst + pkg_lst, check=True)
                    # if the installation succeeds, set the interpreter path and version
                    cnfg.py_interp_path     = f'/usr/bin/python{version}'
                    cnfg.py_interp_ver_str  = version
                    break
                except subprocess.CalledProcessError:
                    print(f'No match for potential Python version {version}.')
                    # if the installation fails, continue loop and check for next version in list
                    continue
            # NOTE: This 'else' is part of the 'for' loop above, not an 'if' condition! Don't indent!
            else:
                # if no suitable version was found, print an error message and exit
                error('ERROR: Did not find any appropriate Python interpreter version.')
                safe_shutdown(1)

            # Mitigate a RHEL 8.x problem reported by a user in these Toshy issue threads:
            # https://github.com/RedBearAK/toshy/issues/278 (Unprivileged user install on RHEL 8)
            # https://github.com/RedBearAK/toshy/issues/289 (Unable to install on RHEL 8)
            # Remove generically versioned pkgs "python3-devel", "python3-pip", "python3-tkinter",
            # but "python3-dbus" is the only "dbus" package available, so leave it.
            # Should prevent the installer from installing an older "python36-devel" package
            # alongside the newer python{version}-devel and related packages.
            # This function also used in RHEL 9, but this mitigation should be harmless.
            pkgs_to_remove = ["python3-devel", "python3-pip", "python3-tkinter"]
            cnfg.pkgs_for_distro = [pkg for pkg in cnfg.pkgs_for_distro if pkg not in pkgs_to_remove]

        is_CentOS               = cnfg.DISTRO_ID == 'centos'

        is_RHEL_8               = (cnfg.DISTRO_ID in distro_groups_map['rhel-based']
                                    and cnfg.distro_mjr_ver in ['8'])
        is_RHEL_9               = (cnfg.DISTRO_ID in distro_groups_map['rhel-based']
                                    and cnfg.distro_mjr_ver in ['9'])

        if is_RHEL_8 and not is_CentOS:

            # for libappindicator-gtk3: sudo dnf install -y epel-release
            if not is_dnf_repo_enabled("epel"):
                try:
                    cmd_lst = [cnfg.priv_elev_cmd, 'dnf', 'install', '-y', 'epel-release']
                    print("Installing and enabling EPEL repository...")
                    subprocess.run(cmd_lst, check=True)
                    cmd_lst = [cnfg.priv_elev_cmd, 'dnf', 'makecache']
                    subprocess.run(cmd_lst, check=True)
                except subprocess.CalledProcessError as proc_err:
                    print()
                    error(f'ERROR: Problem while adding "epel-release" repo.\n\t{proc_err}')
                    safe_shutdown(1)
            else:
                print("EPEL repository is already enabled.")

            # Why were we doing this AFTER the 'epel-release' install?
            # Because in RHEL 8 distros the 'epel-release' package installs '/usr/bin/crb' command!
            # Also the repo ends up being named 'powertools' for some reason. 
            print("Enabling CRB (CodeReady Builder) repo...")
            if not is_dnf_repo_enabled('powertools'):
                # enable CRB repo on RHEL 8.x distros, but not CentOS Stream 8:
                cmd_lst = [cnfg.priv_elev_cmd, '/usr/bin/crb', 'enable']
                try:
                    subprocess.run(cmd_lst, check=True)
                    print("CRB (CodeReady Builder) repo now enabled. (Repo name: 'powertools'.)")
                except subprocess.CalledProcessError as proc_err:
                    print()
                    error(f'ERROR: Problem while enabling CRB repo.\n\t{proc_err}')
                    safe_shutdown(1)
            else:
                print("CRB (CodeReady Builder) repo is already enabled. (Repo name: 'powertools'.)")

            # Get a much newer Python version than the default 3.6 currently on RHEL 8 and clones
            get_newest_python_version()

        elif is_RHEL_9:

            print("Enabling CRB (CodeReady Builder) repo...")
            if not is_dnf_repo_enabled('crb'):
                # enable "CodeReady Builder" repo for 'gobject-introspection-devel' only on 
                # RHEL 9.x and CentOS Stream 9:
                # sudo dnf config-manager --set-enabled crb
                cmd_lst = [cnfg.priv_elev_cmd, 'dnf', 'config-manager', '--set-enabled', 'crb']
                try:
                    subprocess.run(cmd_lst, check=True)
                    print("CRB (CodeReady Builder) repo now enabled.")
                except subprocess.CalledProcessError as proc_err:
                    print()
                    error(f'ERROR: Problem while enabling CRB repo:\n\t{proc_err}')
                    safe_shutdown(1)
            else:
                print("CRB (CodeReady Builder) repo is already enabled.")

            # for libappindicator-gtk3: sudo dnf install -y epel-release
            print("Installing and enabling EPEL repository...")
            if not is_dnf_repo_enabled("epel"):
                try:
                    cmd_lst = [cnfg.priv_elev_cmd, 'dnf', 'install', '-y', 'epel-release']
                    subprocess.run(cmd_lst, check=True)
                    print("EPEL repository is now enabled.")
                    cmd_lst = [cnfg.priv_elev_cmd, 'dnf', 'makecache']
                    subprocess.run(cmd_lst, check=True)
                except subprocess.CalledProcessError as proc_err:
                    print()
                    error(f'ERROR: Problem while adding "epel-release" repo.\n\t{proc_err}')
                    safe_shutdown(1)
            else:
                print("EPEL repository is already enabled.")

            # Get a much newer Python version than the default 3.9 currently on 
            # CentOS Stream 9, RHEL 9 and clones
            get_newest_python_version()

    @staticmethod
    def handle_quirks_RHEL_10():
        print('Doing prep/checks for RHEL 10 type distro...')

        print("Enabling CRB (CodeReady Builder) repo...")
        if not is_dnf_repo_enabled('crb'):
            try:
                cmd_lst = [cnfg.priv_elev_cmd, 'dnf', 'config-manager', '--set-enabled', 'crb']
                subprocess.run(cmd_lst, check=True)
                print("CRB (CodeReady Builder) repo now enabled.")
            except subprocess.CalledProcessError as proc_err:
                print()
                error(f'ERROR: Problem while enabling CRB repo:\n\t{proc_err}')
                safe_shutdown(1)
        else:
            print(f"CRB (CodeReady Builder) repo is already enabled.")

        # Command to install EPEL release package:
        # sudo dnf install https://dl.fedoraproject.org/pub/epel/epel-release-latest-10.noarch.rpm
        epel_10_rpm_url = 'https://dl.fedoraproject.org/pub/epel/epel-release-latest-10.noarch.rpm'

        # # DOES NOT WORK! The package is not found (yet)
        # # Normal 'epel-release' install command should work now on AlmaLinux 10, so
        # # we will substitute the standard package name for the URL. (Since June 2025)
        # if cnfg.DISTRO_ID in ['almalinux']:
        #     epel_10_rpm = 'epel-release'
        #     print("Using standard 'epel-release' package install command...")
        # else:
        #     epel_10_rpm = epel_10_rpm_url
        #     print("Using URL at fedoraproject.org to install 'epel-release' package...")

        print("Installing and enabling EPEL 10 repository...")
        if not is_dnf_repo_enabled("epel"):
            try:
                cmd_lst = [cnfg.priv_elev_cmd, 'dnf', 'install', '-y', epel_10_rpm_url]
                subprocess.run(cmd_lst, check=True)
                print("EPEL repository is now enabled.")
            except subprocess.CalledProcessError as proc_err:
                error(f"Problem installing the EPEL 10 repository:\n{proc_err}")
                safe_shutdown(1)
        else:
            print("EPEL repository is already enabled.")

        # The 'xset' command does not appear to be provided by any available
        # package in RHEL 10 distro types (e.g. AlmaLinux 10):
        pkgs_to_remove = ["xset"]
        cnfg.pkgs_for_distro = [pkg for pkg in cnfg.pkgs_for_distro if pkg not in pkgs_to_remove]

    @staticmethod
    def handle_quirks_Solus():
        print('Doing prep/checks for Solus-based distros...')

        result_new_pkg_name = subprocess.run(
            ['eopkg', 'search', '--no-color', 'python3-dbus-devel'],
            stdout=PIPE, stderr=PIPE, universal_newlines=True
        )

        result_old_pkg_name = subprocess.run(
            ['eopkg', 'search', '--no-color', 'python-dbus-devel'],
            stdout=PIPE, stderr=PIPE, universal_newlines=True
        )

        if result_new_pkg_name.stdout.startswith('python3-dbus-devel'):
            # New pkg name is available, no quirk to handle, so leave.
            print("Using new package name 'python3-dbus-devel'...")
            return

        elif result_old_pkg_name.stdout.startswith('python-dbus-devel'):
            # We got here because the new pkg name is not available,
            # and the older one is available, so substitute.
            print("Using old package name 'python-dbus-devel'...")
            cnfg.pkgs_for_distro = [
                'python-dbus-devel' if pkg == 'python3-dbus-devel' else pkg
                for pkg in cnfg.pkgs_for_distro
            ]
            return

        else:
            # We didn't find either pkg name and return, so we don't know what to do...
            error("Neither python3-dbus-devel nor python-dbus-devel found in Solus repos")
            print('Cannot continue due to missing package. Exiting...')
            safe_shutdown(1)

    @staticmethod
    def handle_quirks_Ubuntu():
        print('Doing prep/checks for Ubuntu-based distros...')

        # Make sure we only handle these quirks in the correct distros
        if cnfg.DISTRO_ID not in distro_groups_map['ubuntu-based']:
            error('Ubuntu distro quirks handler called, but this is not Ubuntu-based?')
            safe_shutdown(1)

        # Check for and add optional packages for GTK4 GUI support
        gtk4_packages = [
            'gir1.2-adw-1',             # For Adwaita/GTK4 GUI (Debian 12+, Ubuntu 22.04+)
            'gir1.2-gtk-4.0',           # For GTK4 GUI support (Debian 11+, Ubuntu 21.10+)
            'libgirepository1.0-dev',   # For PyGObject with girepository-1.0 (Debian <13, Ubuntu <24.04)
            'libgirepository-2.0-dev',  # For PyGObject with girepository-2.0 (Debian 13+, Ubuntu 24.04+)
        ]
        DistroQuirksHandler.add_available_deb_pkgs(gtk4_packages, "GTK4 GUI support packages")


class NativePackageInstaller:
    """Object to handle tasks related to installing native packages"""
    def __init__(self) -> None:
        pass

    def check_for_pkg_mgr_cmd(self, pkg_mgr_cmd: str):
        """Make sure native package installer command exists before using it, or exit"""
        call_attn_to_pwd_prompt_if_needed()
        if not shutil.which(pkg_mgr_cmd):
            print()
            error(f'Package manager command ({pkg_mgr_cmd}) not available. Unable to continue.')
            safe_shutdown(1)

    def exit_with_pkg_install_error(self, proc_err):
        """shutdown with error message if there is a problem with installing package list"""
        print()
        error(f'ERROR: Problem installing package list for distro type:\n\t{proc_err}')
        safe_shutdown(1)

    def show_pkg_install_success_msg(self):
        # Have something come out even if package list is empty (like Arch after initial run)
        print('All necessary native distro packages are installed.')

    def install_pkg_list(self, cmd_lst, pkg_lst):
        """Install packages using the given package manager command list and package list."""
        
        # Extract the package manager command to check
        pkg_mgr_cmd = next((cmd for cmd in cmd_lst if cmd != 'sudo'), None)
        # If we couldn't extract the command, exit with an error
        if not pkg_mgr_cmd:
            error(f'No valid package manager command in provided command list:\n\t{cmd_lst}')
            safe_shutdown(1)
        
        call_attn_to_pwd_prompt_if_needed()
        self.check_for_pkg_mgr_cmd(pkg_mgr_cmd)
        
        # Execute the package installation command
        try:
            subprocess.run(cmd_lst + pkg_lst, check=True)
            # self.show_pkg_install_success_msg()
        except subprocess.CalledProcessError as proc_err:
            self.exit_with_pkg_install_error(proc_err)


def print_skipping_installed_pkg(pkg_name):
    """
    Utility function to print a formatted terminal message about 
    skipping an already installed package. Used by multiple dispatched
    installer methods in PackageInstallDispatcher utility class.
    """
    print(fancy_str(f"  Skipping installed package: {pkg_name}", "green"))


class PackageInstallDispatcher:
    """
    Utility class to hold the static methods that will optionally invoke any necessary 
    distro quirks handling, and then proceed to prep for and finally invoke the correct 
    NativePackageInstaller command to install the appropriate support package list for 
    the detected Linux distro.
    """

    ###########################################################################
    ###  TRANSACTIONAL-UPDATE DISTROS  ########################################
    ###########################################################################
    @staticmethod
    def install_on_transupd_distro():
        """utility function that gets dispatched for distros that use Transactional-Update"""

        def print_incomplete_setup_warning():
            """utility function to print the warning about rebooting and running setup again"""
            print()
            print('###############################################################################')
            print('############       WARNING: Toshy setup is NOT yet complete!       ############')
            print('###########      This distro type uses "transactional-update".      ###########')
            print('##########   You MUST reboot now to make native packages available.  ##########')
            print('#########  After REBOOTING, run the Toshy setup script a second time. #########')
            print('###############################################################################')

        if cnfg.DISTRO_ID in distro_groups_map['microos-based']:
            print('Distro is openSUSE MicroOS/Aeon/Kalpa immutable. Using "transactional-update".')

            call_attn_to_pwd_prompt_if_needed()

            # Filter out packages that are already installed
            filtered_pkg_lst = []
            for pkg in cnfg.pkgs_for_distro:
                result = subprocess.run(["rpm", "-q", pkg], stdout=PIPE, stderr=PIPE)
                if result.returncode != 0:
                    filtered_pkg_lst.append(pkg)
                else:
                    print_skipping_installed_pkg(pkg)

            if filtered_pkg_lst:
                print(f'Packages left to install:\n{filtered_pkg_lst}')
                cmd_lst = [cnfg.priv_elev_cmd, 'transactional-update', '--non-interactive', 'pkg', 'in']
                native_pkg_installer.install_pkg_list(cmd_lst, filtered_pkg_lst)
                # might as well take care of user group and udev here, if rebooting is necessary. 
                verify_user_groups()
                install_udev_rules()
                show_reboot_prompt()
                print_incomplete_setup_warning()
                safe_shutdown(0)
            else:
                print('All needed packages are already available. Continuing setup...')

    ###########################################################################
    ###  RPM-OSTREE DISTROS  ##################################################
    ###########################################################################
    @staticmethod
    def install_on_rpmostree_distro():
        """utility function that gets dispatched for distros that use RPM-OSTree"""
        if cnfg.DISTRO_ID in distro_groups_map['fedora-immutables']:
            print('Distro is Fedora-type immutable. Using "rpm-ostree" instead of DNF.')

            call_attn_to_pwd_prompt_if_needed()

            # Filter out packages that are already installed
            filtered_pkg_lst = []
            for pkg in cnfg.pkgs_for_distro:
                result = subprocess.run(["rpm", "-q", pkg], stdout=PIPE, stderr=PIPE)
                if result.returncode != 0:
                    filtered_pkg_lst.append(pkg)
                else:
                    print_skipping_installed_pkg(pkg)

            if filtered_pkg_lst:
                cmd_lst = [cnfg.priv_elev_cmd, 'rpm-ostree', 'install', '--idempotent',
                            '--allow-inactive', '--apply-live', '-y']
                native_pkg_installer.install_pkg_list(cmd_lst, filtered_pkg_lst)

    ###########################################################################
    ###  DNF DISTROS  #########################################################
    ###########################################################################
    @staticmethod
    def install_on_dnf_distro():
        """Utility function that gets dispatched for distros that use DNF package manager."""
        call_attn_to_pwd_prompt_if_needed()

        def install_on_fedora_based():
            # TODO: insert check to see if Fedora distro is actually immutable/atomic (rpm-ostree)
            cmd_lst = [cnfg.priv_elev_cmd, 'dnf', 'install', '-y']
            native_pkg_installer.install_pkg_list(cmd_lst, cnfg.pkgs_for_distro)

        def install_on_mageia_based():
            cmd_lst = [cnfg.priv_elev_cmd, 'dnf', 'install', '-y']
            native_pkg_installer.install_pkg_list(cmd_lst, cnfg.pkgs_for_distro)

        # Define helper functions for specific distro installations
        def install_on_mandriva_based():
            cmd_lst = [cnfg.priv_elev_cmd, 'dnf', 'install', '-y']
            native_pkg_installer.install_pkg_list(cmd_lst, cnfg.pkgs_for_distro)

        def install_on_rhel_based():

            is_CentOS_7         = cnfg.DISTRO_ID == 'centos' and cnfg.distro_mjr_ver == '7'
            is_CentOS_Stream_8  = cnfg.DISTRO_ID == 'centos' and cnfg.distro_mjr_ver == '8'

            is_RHEL_8_or_9      = (cnfg.DISTRO_ID in distro_groups_map['rhel-based']
                                    and cnfg.distro_mjr_ver in ['8', '9'])
            is_RHEL_10          = (cnfg.DISTRO_ID in distro_groups_map['rhel-based']
                                    and cnfg.distro_mjr_ver in ['10'])

            # Native package install command can immediately proceed after prepping CentOS 7, so
            # this block that was all "if" layers has been changed to if/elif/elif logic. The
            # handling of CentOS Stream 8 was logically embedded in the RHEL 8/9 elif branch.
            # Changed because order-sensitive "if" layers could be broken by re-ordering. 

            if True is False: pass

            elif is_CentOS_7:
                # Do prep steps specific to CentOS 7, then proceed to native install command
                DistroQuirksHandler.handle_quirks_CentOS_7()
            elif is_RHEL_8_or_9:
                if is_CentOS_Stream_8:
                    # Special prep steps must happen on CentOS Stream 8 before general RHEL 8 prep
                    DistroQuirksHandler.handle_quirks_CentOS_Stream_8()
                # Do prep steps for general RHEL 8/9 type distros (CentOS, AlmaLinux, Rocky, etc.)
                DistroQuirksHandler.handle_quirks_RHEL_8_and_9()
            elif is_RHEL_10:
                # Do prep steps for general RHEL 10 type distros (CentOS, AlmaLinux, Rocky, etc.)
                DistroQuirksHandler.handle_quirks_RHEL_10()

            # Package version repo conflict issues on CentOS 10 made installing difficult
            if cnfg.DISTRO_ID == 'centos' and cnfg.distro_mjr_ver == '10':
                cmd_lst = [cnfg.priv_elev_cmd, 'dnf', 'install', '-y', '--nobest']
            else:
                cmd_lst = [cnfg.priv_elev_cmd, 'dnf', 'install', '-y']

            native_pkg_installer.install_pkg_list(cmd_lst, cnfg.pkgs_for_distro)

        # Dispatch installation sub-function based on DNF distro type
        if True is False:
            pass

        elif cnfg.DISTRO_ID in distro_groups_map['fedora-based']:
            print("Calling installer dispatcher sub-method:"
                    f"\n  {install_on_fedora_based.__name__}")
            install_on_fedora_based()
        elif cnfg.DISTRO_ID in distro_groups_map['mageia-based']:
            print("Calling installer dispatcher sub-method:"
                    f"\n  {install_on_mageia_based.__name__}")
            install_on_mageia_based()
        elif cnfg.DISTRO_ID in distro_groups_map['mandriva-based']:
            print("Calling installer dispatcher sub-method:"
                    f"\n  {install_on_mandriva_based.__name__}")
            install_on_mandriva_based()
        elif cnfg.DISTRO_ID in distro_groups_map['rhel-based']:
            print("Calling installer dispatcher sub-method:"
                    f"\n  {install_on_rhel_based.__name__}")
            install_on_rhel_based()

        else:
            error(f"Distro {cnfg.DISTRO_ID} is not supported by this installation script.")
            safe_shutdown(1)

    ###########################################################################
    ###  ZYPPER DISTROS  ######################################################
    ###########################################################################
    @staticmethod
    def install_on_zypper_distro():
        """utility function that gets dispatched for distros that use Zypper package manager"""
        native_pkg_installer.check_for_pkg_mgr_cmd('zypper')
        call_attn_to_pwd_prompt_if_needed()
        cmd_lst = [cnfg.priv_elev_cmd, 'zypper', '--non-interactive', 'install']
        native_pkg_installer.install_pkg_list(cmd_lst, cnfg.pkgs_for_distro)

    ###########################################################################
    ###  APT DISTROS  #########################################################
    ###########################################################################
    @staticmethod
    def install_on_apt_distro():
        """utility function that gets dispatched for distros that use APT package manager"""

        # Install has been failing on several Debian/Ubuntu distros with broken dependencies.
        # So far: Deepin 25 alpha/preview, Linux Lite 7.2, Ubuntu Kylin 23.10, Zorin OS 16.x
        # There is no safe way to overcome the issue automatically. Repos are broken.

        # 'apt' command warns about "unstable CLI interface", so let's try 'apt-get'
        pkg_mgr_cmd = 'apt-get'
        native_pkg_installer.check_for_pkg_mgr_cmd(pkg_mgr_cmd)
        call_attn_to_pwd_prompt_if_needed()

        if cnfg.DISTRO_ID in distro_groups_map['ubuntu-based']:
            DistroQuirksHandler.handle_quirks_Ubuntu()

        elif cnfg.DISTRO_ID in distro_groups_map['debian-based']:
            DistroQuirksHandler.handle_quirks_Debian()

        cmd_lst = [cnfg.priv_elev_cmd, pkg_mgr_cmd, 'install', '-y']
        native_pkg_installer.install_pkg_list(cmd_lst, cnfg.pkgs_for_distro)

    ###########################################################################
    ###  PACMAN DISTROS  ######################################################
    ###########################################################################
    @staticmethod
    def install_on_pacman_distro():
        """utility function that gets dispatched for distros that use Pacman package manager"""
        native_pkg_installer.check_for_pkg_mgr_cmd('pacman')
        call_attn_to_pwd_prompt_if_needed()

        def is_pkg_installed_pacman(package):
            """utility function to help avoid 'reinstalling' existing packages on Arch"""
            result = subprocess.run(['pacman', '-Q', package], stdout=DEVNULL, stderr=DEVNULL)
            return result.returncode == 0

        pkgs_to_install = []
        for pkg in cnfg.pkgs_for_distro:
            if not is_pkg_installed_pacman(pkg):
                pkgs_to_install.append(pkg)
            else:
                print_skipping_installed_pkg(pkg)

        if pkgs_to_install:
            cmd_lst = [cnfg.priv_elev_cmd, 'pacman', '-S', '--noconfirm']
            native_pkg_installer.install_pkg_list(cmd_lst, pkgs_to_install)

    ###########################################################################
    ###  EMERGE DISTROS  ######################################################
    ###########################################################################
    @staticmethod
    def install_on_emerge_distro():
        """utility function that gets dispatched for distros that use emerge package manager"""

        native_pkg_installer.check_for_pkg_mgr_cmd('emerge')
        call_attn_to_pwd_prompt_if_needed()

        equery_cmd              = shutil.which('equery')
        qlist_cmd               = shutil.which('qlist')

        def is_pkg_installed_emerge(package):
            """utility function to check if a package is already installed on Gentoo"""
            if equery_cmd:
                result = subprocess.run(
                    ['equery', 'list', package], stdout=DEVNULL, stderr=DEVNULL)
                return result.returncode == 0
            if qlist_cmd:
                result = subprocess.run(
                    ['qlist', '-Iv', package], stdout=DEVNULL, stderr=DEVNULL)
                return result.returncode == 0
            return False

        pkgs_to_install = []
        if equery_cmd or qlist_cmd:
            for pkg in cnfg.pkgs_for_distro:
                if not is_pkg_installed_emerge(pkg):
                    pkgs_to_install.append(pkg)
                else:
                    print_skipping_installed_pkg(pkg)
        else:
            print('Unable to check for installed packages. Commands "equery", "qlist" not found.')
            pkgs_to_install = list(cnfg.pkgs_for_distro)

        if pkgs_to_install:
            cmd_lst = [cnfg.priv_elev_cmd, 'emerge', '--ask=n', '--quiet-build']
            native_pkg_installer.install_pkg_list(cmd_lst, pkgs_to_install)

    ###########################################################################
    ###  EOPKG DISTROS  #######################################################
    ###########################################################################
    @staticmethod
    def install_on_eopkg_distro():
        """utility function that gets dispatched for distros that use Eopkg package manager"""

        # Package name shifted on Solus 4.8, to 'python3-dbus-devel',
        # in migration from "Shannon" to "Polaris" repos.
        # Quirks handler checks for both new and old package names.
        if cnfg.DISTRO_ID in distro_groups_map['solus-based']:
            DistroQuirksHandler.handle_quirks_Solus()

        native_pkg_installer.check_for_pkg_mgr_cmd('eopkg')
        call_attn_to_pwd_prompt_if_needed()

        dev_cmd_lst = [cnfg.priv_elev_cmd, 'eopkg', 'install', '-y', '-c']
        dev_pkg_lst = ['system.devel']
        print('Installing Solus system development prerequisites first...')
        native_pkg_installer.install_pkg_list(dev_cmd_lst, dev_pkg_lst)
        print('Now installing primary native package list for Solus...')
        cmd_lst = [cnfg.priv_elev_cmd, 'eopkg', 'install', '-y']
        native_pkg_installer.install_pkg_list(cmd_lst, cnfg.pkgs_for_distro)

    ###########################################################################
    ###  MOSS DISTROS  ########################################################
    ###########################################################################
    @staticmethod
    def install_on_moss_distro():
        """utility function that gets dispatched for distros that use Moss package manager"""
        native_pkg_installer.check_for_pkg_mgr_cmd('moss')
        call_attn_to_pwd_prompt_if_needed()
        cmd_lst = [cnfg.priv_elev_cmd, 'moss', 'install', '--yes-all']
        native_pkg_installer.install_pkg_list(cmd_lst, cnfg.pkgs_for_distro)

    ###########################################################################
    ###  XBPS DISTROS  ########################################################
    ###########################################################################
    @staticmethod
    def install_on_xbps_distro():
        """utility function that gets dispatched for distros that use xbps-install package manager"""
        native_pkg_installer.check_for_pkg_mgr_cmd('xbps-install')
        call_attn_to_pwd_prompt_if_needed()

        cmd_lst = [cnfg.priv_elev_cmd, 'xbps-install', '-Sy']
        native_pkg_installer.install_pkg_list(cmd_lst, cnfg.pkgs_for_distro)

    ###########################################################################
    ###  APK DISTROS  #########################################################
    ###########################################################################
    @staticmethod
    def install_on_apk_distro():
        """utility function that gets dispatched for distros that use APK package manager"""
        native_pkg_installer.check_for_pkg_mgr_cmd('apk')
        call_attn_to_pwd_prompt_if_needed()

        def get_installed_packages_apk():
            """Get set of installed package names from apk"""
            try:
                # Using universal_newlines for Python 3.6 compatibility
                result = subprocess.run(['apk', 'list', '--installed', '--manifest'], 
                                        stdout=PIPE, stderr=PIPE, universal_newlines=True, check=True)
                installed_packages = set()
                for line in result.stdout.splitlines():
                    if line.strip():
                        # With --manifest, format is: package-name version
                        pkg_name = line.split()[0]
                        installed_packages.add(pkg_name)
                return installed_packages
            except subprocess.CalledProcessError:
                return set()

        installed_packages = get_installed_packages_apk()
        pkgs_to_install = []
        
        for pkg in cnfg.pkgs_for_distro:
            if pkg not in installed_packages:
                pkgs_to_install.append(pkg)
            else:
                print_skipping_installed_pkg(pkg)
                

        if pkgs_to_install:
            # Install packages with --no-cache to avoid prompts about cache management
            cmd_lst = [cnfg.priv_elev_cmd, 'apk', 'add', '--no-cache', '--no-interactive']
            native_pkg_installer.install_pkg_list(cmd_lst, pkgs_to_install)


class PackageManagerGroups:
    """Container for package manager distro groupings and dispatch map"""
    
    def __init__(self):
        # Initialize empty package manager distro lists
        self.apk_distros        = []    # 'apk':                    Alpine/Chimera
        self.apt_distros        = []    # 'apt':                    Debian/Ubuntu
        self.dnf_distros        = []    # 'dnf':                    Fedora/Mageia/OpenMandriva/RHEL
        self.emerge_distros     = []    # 'emerge':                 Gentoo
        self.eopkg_distros      = []    # 'eopkg':                  Solus
        self.moss_distros       = []    # 'moss':                   AerynOS (was Serpent OS)
        self.pacman_distros     = []    # 'pacman':                 Arch (BTW)
        self.rpmostree_distros  = []    # 'rpm-ostree':             Fedora atomic/immutables
        self.transupd_distros   = []    # 'transactional-update':   openSUSE Aeon/Kalpa/MicroOS
        self.xbps_distros       = []    # 'xbps-install':           Void
        self.zypper_distros     = []    # 'zypper':                 openSUSE Tumbleweed/Leap
        # Initialize empty package manager dispatch map
        self.dispatch_map       = None
        # Dispatch map method ensures lists are populated before creating map
        self.create_dispatch_map()

    def populate_lists(self):
        """Populate package manager distro lists from distro_groups_map"""

        try:

            # 'apk': Alpine/Chimera
            self.apk_distros            += distro_groups_map['chimera-based']

            # 'apt': Debian/Ubuntu, ALT Linux (uses APT-RPM)
            self.apt_distros            += distro_groups_map['alt-based']
            self.apt_distros            += distro_groups_map['debian-based']
            self.apt_distros            += distro_groups_map['ubuntu-based']

            # 'dnf': Fedora/RHEL/OpenMandriva
            self.dnf_distros            += distro_groups_map['fedora-based']
            self.dnf_distros            += distro_groups_map['mageia-based']
            self.dnf_distros            += distro_groups_map['mandriva-based']
            self.dnf_distros            += distro_groups_map['rhel-based']

            # 'emerge': Gentoo
            self.emerge_distros         += distro_groups_map['gentoo-based']

            # 'eopkg': Solus
            self.eopkg_distros          += distro_groups_map['solus-based']

            # 'moss': AerynOS (was Serpent OS)
            self.moss_distros           += distro_groups_map['aerynos-based']

            # 'pacman': Arch, BTW
            self.pacman_distros         += distro_groups_map['arch-based']

            # 'rpm-ostree': Fedora atomic/immutables
            self.rpmostree_distros      += distro_groups_map['fedora-immutables']

            # 'transactional-update': openSUSE MicroOS/Aeon/Kalpa
            self.transupd_distros       += distro_groups_map['microos-based']

            # 'xbps-install': Void
            self.xbps_distros           += distro_groups_map['void-based']

            # 'zypper': openSUSE Tumbleweed/Leap
            self.zypper_distros         += distro_groups_map['leap-based']
            self.zypper_distros         += distro_groups_map['tumbleweed-based']

        except (KeyError, TypeError) as key_err:
            error(f'Problem setting up package manager distro lists:\n\t{key_err}')
            safe_shutdown(1)

    def create_dispatch_map(self):
        """Create mapping of distro lists to their installer methods"""
        self.populate_lists()       # Make sure lists contain correct info before creating map
        self.dispatch_map = {
            tuple(self.apk_distros):        PackageInstallDispatcher.install_on_apk_distro,
            tuple(self.apt_distros):        PackageInstallDispatcher.install_on_apt_distro,
            tuple(self.dnf_distros):        PackageInstallDispatcher.install_on_dnf_distro,
            tuple(self.emerge_distros):     PackageInstallDispatcher.install_on_emerge_distro,
            tuple(self.eopkg_distros):      PackageInstallDispatcher.install_on_eopkg_distro,
            tuple(self.moss_distros):       PackageInstallDispatcher.install_on_moss_distro,
            tuple(self.pacman_distros):     PackageInstallDispatcher.install_on_pacman_distro,
            tuple(self.rpmostree_distros):  PackageInstallDispatcher.install_on_rpmostree_distro,
            tuple(self.transupd_distros):   PackageInstallDispatcher.install_on_transupd_distro,
            tuple(self.xbps_distros):       PackageInstallDispatcher.install_on_xbps_distro,
            tuple(self.zypper_distros):     PackageInstallDispatcher.install_on_zypper_distro,
        }


def install_distro_pkgs():
    """Install needed packages from list for distro type"""
    print(f'\n\n§  Installing native packages for this distro type...\n{cnfg.separator}')

    pkg_group = None
    for group, distros in distro_groups_map.items():
        if cnfg.DISTRO_ID in distros:
            pkg_group = group
            break

    if pkg_group is None:
        print()
        print(f"ERROR: No list of packages found for this distro: '{cnfg.DISTRO_ID}'")
        print(f'Installation cannot proceed without a list of packages. Sorry.')
        print(f'Try some options in "./{this_file_name} --help"')
        safe_shutdown(1)

    cnfg.pkgs_for_distro = pkg_groups_map[pkg_group]

    # Add extra packages for specific distros and versions
    for version in [cnfg.distro_mjr_ver, None]:
        distro_key = (cnfg.DISTRO_ID, version)
        if distro_key in extra_pkgs_map:
            print(f"Distro key {distro_key} matched in 'extra_pkgs_map'.")
            cnfg.pkgs_for_distro.extend(extra_pkgs_map[distro_key])
            print("Added package(s) to queue:")
            for pkg in extra_pkgs_map[distro_key]:
                print(f"\t'{pkg}'")
            print("All necessary extra packages added to queue. Continuing...")

    # Remove packages for specific distros and versions
    for version in [cnfg.distro_mjr_ver, None]:
        distro_key = (cnfg.DISTRO_ID, version)
        if distro_key in remove_pkgs_map:
            print(f"Distro key {distro_key} matched in 'remove_pkgs_map'.")
            for pkg in remove_pkgs_map[distro_key]:
                if pkg in cnfg.pkgs_for_distro:
                    cnfg.pkgs_for_distro.remove(pkg)
                    print(f"Removing '{pkg}' from package list.")
            print("All incompatible packages removed from package list. Continuing...")

    # Filter out systemd packages if systemctl is not present
    cnfg.pkgs_for_distro = [
        pkg for pkg in cnfg.pkgs_for_distro 
        if cnfg.systemctl_present or 'systemd' not in pkg
    ]

    def call_installer_method(installer_method):
        """Utility function to call the installer function and handle post-call tasks."""
        if callable(installer_method):  # Ensure the passed method is callable
            print(f"Calling installer dispatcher method:\n  {installer_method.__name__}")
            installer_method()  # Call the function
            native_pkg_installer.show_pkg_install_success_msg()
            show_task_completed_msg()
        else:
            obj_name = getattr(installer_method, "__name__", str(installer_method))
            error(f"The provided installer_method argument is not a callable:\n {obj_name}")
            safe_shutdown(1)

    pkg_mgr_groups = PackageManagerGroups()

    # Determine the correct installation class method
    for distro_list, installer_method in pkg_mgr_groups.dispatch_map.items():
        if cnfg.DISTRO_ID in distro_list:
            call_installer_method(installer_method)
            return
    # exit message in case there is no package manager distro list with distro name inside
    exit_with_invalid_distro_error(pkg_mgr_err=True)


#####################################################################################################
###   END OF NATIVE PACKAGE INSTALLER SECTION
#####################################################################################################


def setup_uinput_module():
    """Load the uinput module and ensure it's persistent across reboots"""
    print(f'\n\n§  Checking status of "uinput" kernel module...\n{cnfg.separator}')

    # Step 1: Make sure uinput is loaded right now
    try:
        subprocess.check_output("lsmod | grep uinput", shell=True)
        print('The "uinput" module is already loaded.')
    except subprocess.CalledProcessError:
        print('The "uinput" module is not loaded, loading now...')
        call_attn_to_pwd_prompt_if_needed()
        try:
            subprocess.run([cnfg.priv_elev_cmd, 'modprobe', 'uinput'], check=True)
            print('Successfully loaded the "uinput" module.')
        except subprocess.CalledProcessError as proc_err:
            error(f"Failed to load the uinput module:\n\t{proc_err}")
            error(f'ERROR: Install failed.')
            safe_shutdown(1)

    # Step 2: Detect which init systems are available (not just currently running)
    # This matters for dual-init distros like MX Linux where user can choose at boot
    
    systemd_available = (
        cnfg.systemctl_present or
        os.path.exists('/lib/systemd/systemd') or
        os.path.exists('/usr/lib/systemd/systemd')
    )
    
    # Known dual-init distros that support both systemd and SysVinit
    dual_init_distros = ['mxlinux', 'antix']
    is_dual_init = cnfg.DISTRO_ID in dual_init_distros
    
    # SysVinit is relevant if /etc/modules exists OR this is a known dual-init distro
    sysvinit_relevant = os.path.isfile('/etc/modules') or is_dual_init

    # Step 3: Check existing configurations and set up persistence
    print('Checking uinput module persistence configuration...')
    
    modules_load_dir    = '/etc/modules-load.d'
    uinput_conf_path    = os.path.join(modules_load_dir, 'uinput.conf')
    etc_modules_path    = '/etc/modules'
    
    systemd_configured  = False
    sysvinit_configured = False

    call_attn_to_pwd_prompt_if_needed()

    # Helper to check if uinput is configured in a file
    def file_contains_uinput(filepath, pattern='^uinput$'):
        """Check if file contains uinput configuration"""
        if not os.path.isfile(filepath):
            return False
        try:
            check_cmd = f"{cnfg.priv_elev_cmd} grep -q '{pattern}' {filepath}"
            subprocess.run(check_cmd, shell=True, check=True)
            return True
        except subprocess.CalledProcessError:
            return False

    # Helper to write uinput to a config file
    def write_uinput_config(filepath, append=False):
        """Write uinput to config file, optionally appending"""
        tee_flag = '-a' if append else ''
        command = f"echo 'uinput' | {cnfg.priv_elev_cmd} tee {tee_flag} {filepath} >/dev/null"
        subprocess.run(command, shell=True, check=True)

    # Check and configure systemd-style persistence
    if systemd_available:
        # Create the directory if it doesn't exist (handles AerynOS and similar)
        if not os.path.isdir(modules_load_dir):
            print(f"Creating directory: '{modules_load_dir}'")
            try:
                cmd_lst = [cnfg.priv_elev_cmd, 'mkdir', '-p', modules_load_dir]
                subprocess.run(cmd_lst, check=True)
            except subprocess.CalledProcessError as proc_err:
                error(f"Problem creating {modules_load_dir} directory:\n\t{proc_err}")
                # Don't exit - try sysvinit fallback if available

        if os.path.isdir(modules_load_dir):
            if file_contains_uinput(uinput_conf_path, 'uinput'):
                print(f'Already configured for systemd/OpenRC: {uinput_conf_path}')
                systemd_configured = True
            else:
                try:
                    write_uinput_config(uinput_conf_path, append=False)
                    print(f'Configured uinput for systemd/OpenRC: {uinput_conf_path}')
                    systemd_configured = True
                except subprocess.CalledProcessError as proc_err:
                    error(f"Failed to create {uinput_conf_path}:\n\t{proc_err}")

    # Check and configure SysVinit-style persistence
    if sysvinit_relevant:
        # For dual-init distros, create /etc/modules if it doesn't exist
        if is_dual_init and not os.path.isfile(etc_modules_path):
            print(f"Creating file for dual-init compatibility: '{etc_modules_path}'")
            try:
                cmd = f"{cnfg.priv_elev_cmd} touch {etc_modules_path}"
                subprocess.run(cmd, shell=True, check=True)
            except subprocess.CalledProcessError as proc_err:
                error(f"Problem creating {etc_modules_path}:\n\t{proc_err}")

        if os.path.isfile(etc_modules_path):
            if file_contains_uinput(etc_modules_path):
                print(f'Already configured for SysVinit: {etc_modules_path}')
                sysvinit_configured = True
            else:
                try:
                    write_uinput_config(etc_modules_path, append=True)
                    print(f'Configured uinput for SysVinit: {etc_modules_path}')
                    sysvinit_configured = True
                except subprocess.CalledProcessError as proc_err:
                    error(f"Failed to update {etc_modules_path}:\n\t{proc_err}")

    # Step 4: Report final status
    if systemd_configured or sysvinit_configured:
        print("Module is available now and configured to load automatically after reboots.")
        if is_dual_init:
            configured_locations = []
            if systemd_configured:
                configured_locations.append('systemd')
            if sysvinit_configured:
                configured_locations.append('SysVinit')
            print(f"  Dual-init distro: configured for {' and '.join(configured_locations)}")
    else:
        warn("WARNING: Could not configure the uinput module to load at boot!")
        warn("You may need to manually load the uinput module after each reboot.")
        warn("You can do this with: sudo modprobe uinput")

    show_task_completed_msg()


def reload_udev_rules():
    """utility function to reload udev rules in case of changes to rules file"""
    try:
        call_attn_to_pwd_prompt_if_needed()
        cmd_lst_reload                 = [cnfg.priv_elev_cmd, 'udevadm', 'control', '--reload-rules']
        subprocess.run(cmd_lst_reload, check=True)
        cmd_lst_trigger                 = [cnfg.priv_elev_cmd, 'udevadm', 'trigger']
        subprocess.run(cmd_lst_trigger, check=True)
        print('Reloaded the "udev" rules successfully.')
    except subprocess.CalledProcessError as proc_err:
        print(f'Failed to reload "udev" rules:\n\t{proc_err}')
        enable_prompt_for_reboot()


def install_udev_rules():
    """Set up `udev` rules file to give user/keymapper process access to uinput"""
    print(f'\n\n§  Installing "udev" rules file for keymapper...\n{cnfg.separator}')

    rules_dir                   = '/etc/udev/rules.d'

    # systemd init systems can use the 'uaccess' tag to set owner of device to current user,
    # but this also requires the rules file to be lexically earlier than '73-'. Trying '70-'.
    rules_file                  = '70-toshy-keymapper-input.rules'
    rules_file_path             = os.path.join(rules_dir, rules_file)

    # older DEPRECATED '90-' rules file name, must be removed if found
    old_rules_file              = '90-toshy-keymapper-input.rules'          # DEPRECATED
    old_rules_file_path         = os.path.join(rules_dir, old_rules_file)

    # Check if the /etc/udev/rules.d directory exists, if not, create it
    if not os.path.exists(rules_dir):
        print(f"Creating directory: '{rules_dir}'")
        try:
            call_attn_to_pwd_prompt_if_needed()
            cmd_lst = [cnfg.priv_elev_cmd, 'mkdir', '-p', rules_dir]
            subprocess.run(cmd_lst, check=True)
        except subprocess.CalledProcessError as proc_err:
            error(f"Problem while creating udev rules folder:\n\t{proc_err}")
            safe_shutdown(1)

    setfacl_path                = shutil.which('setfacl')
    acl_rule                    = ''

    if setfacl_path is not None:
        acl_rule                = f', RUN+="{setfacl_path} -m g::rw /dev/uinput"'
    new_rules_content           = (
        'SUBSYSTEM=="input", GROUP="input", MODE="0660", TAG+="uaccess"\n'
        'KERNEL=="uinput", SUBSYSTEM=="misc", GROUP="input", MODE="0660", ' # No line break here!
        f'TAG+="uaccess"{acl_rule}\n'
    )

    def rules_file_missing_or_content_differs():
        if not os.path.exists(rules_file_path):
            return True
        try:
            with open(rules_file_path, 'r') as file:
                return file.read() != new_rules_content
        except PermissionError as perm_err:
            error(f"Permission denied when accessing '{rules_file_path}':\n\t{perm_err}")
            safe_shutdown(1)
        except IOError as io_err:
            error(f"Error reading file '{rules_file_path}':\n\t{io_err}")
            error("Rules file exists but cannot be read. File corrupted?")
            safe_shutdown(1)

    # Only write the file if it doesn't exist or its contents are different from current rule
    if rules_file_missing_or_content_differs():
        command_str             = f'{cnfg.priv_elev_cmd} tee {rules_file_path}'
        try:
            call_attn_to_pwd_prompt_if_needed()
            print(f'Using these "udev" rules for "uinput" device: ')
            print()
            subprocess.run(command_str, input=new_rules_content.encode(), shell=True, check=True)
            if not rules_file_missing_or_content_differs():
                print()
                print(f'Toshy "udev" rules file successfully installed.')
                reload_udev_rules()
            else:
                error(f'Toshy "udev" rules file install failed.')
                safe_shutdown(1)
        except subprocess.CalledProcessError as proc_err:
            print()
            error(f'ERROR: Problem while installing "udev" rules file for keymapper.\n')
            err_output: bytes = proc_err.output  # Type hinting the error output variable
            # Deal with possible 'NoneType' error output
            error(f'Command output:\n{err_output.decode() if err_output else "No error output"}')
            print()
            error(f'ERROR: Toshy install failed.')
            safe_shutdown(1)
    else:
        print(f'Correct "udev" rules already in place.')

    # remove older '90-' rules file (cannot use 'uaccess' tag unless processed earlier than '73-')
    if os.path.exists(old_rules_file_path):
        try:
            call_attn_to_pwd_prompt_if_needed()
            print(f'Removing old udev rules file: {old_rules_file}')
            subprocess.run([cnfg.priv_elev_cmd, 'rm', old_rules_file_path], check=True)
        except subprocess.CalledProcessError as proc_err:
            error(f'ERROR: Problem while removing old udev rules file:\n\t{proc_err}')

    show_task_completed_msg()


def group_exists_in_etc_group(group_name):
    """Utility function to check if the group exists in /etc/group file."""
    try:
        with open('/etc/group') as f:
            return re.search(rf'^{group_name}:', f.read(), re.MULTILINE) is not None
    except FileNotFoundError:
        error(f'Warning: /etc/group file not found. Cannot add "{group_name}" group.')
        safe_shutdown(1)


def create_group(group_name):
    """Utility function to create the specified group if it does not already exist."""
    if group_exists_in_etc_group(group_name):
        print(f'Group "{group_name}" already exists.')
    else:
        print(f'Creating "{group_name}" group...')
        call_attn_to_pwd_prompt_if_needed()
        if cnfg.DISTRO_ID in distro_groups_map['fedora-immutables']:
            # Special handling for Fedora immutable distributions
            with open('/etc/group') as f:
                if not re.search(rf'^{group_name}:', f.read(), re.MULTILINE):
                    # https://docs.fedoraproject.org/en-US/fedora-silverblue/troubleshooting/
                    # Special command to make Fedora Silverblue/uBlue work, or usermod will fail: 
                    # grep -E '^input:' /usr/lib/group | sudo tee -a /etc/group
                    command = (f"grep -E '^{group_name}:' /usr/lib/group | "
                                f"{cnfg.priv_elev_cmd} tee -a /etc/group >/dev/null")
                    try:
                        subprocess.run(command, shell=True, check=True)
                        print(f"Added '{group_name}' group to system.")
                    except subprocess.CalledProcessError as proc_err:
                        error(f"Problem adding '{group_name}' group to system.\n\t{proc_err}")
                        safe_shutdown(1)
        else:
            try:
                cmd_lst = [cnfg.priv_elev_cmd, 'groupadd', group_name]
                subprocess.run(cmd_lst, check=True)
                print(f'Group "{group_name}" created successfully.')
            except subprocess.CalledProcessError as proc_err:
                print()
                error(f'ERROR: Problem when trying to create "input" group.\n')
                err_output: bytes = proc_err.output  # Type hinting the error output variable
                # Deal with possible 'NoneType' error output
                error(f'Command output:\n{err_output.decode() if err_output else "No error output"}')
                safe_shutdown(1)


def add_user_to_group(group_name: str, user_name: str) -> None:
    """Utility function to add a user to a system group, handling errors appropriately."""
    try:
        call_attn_to_pwd_prompt_if_needed()
        subprocess.run([cnfg.priv_elev_cmd, 'usermod', '-aG', group_name, user_name], check=True)
    except subprocess.CalledProcessError as proc_err:
        print()
        error(f'ERROR: Problem when trying to add user "{user_name}" to '
                f'group "{group_name}".\n')
        err_output: bytes = proc_err.output
        error(f'Command output:\n{err_output.decode() if err_output else "No error output"}')
        print()
        error('ERROR: Install failed.')
        safe_shutdown(1)

    print(f'User "{user_name}" added to group "{group_name}".')
    enable_prompt_for_reboot()


def verify_user_groups():
    """
    Check if the 'input' group exists and user is in group.
    Also check other groups like 'systemd-journal' in 
    special cases, like openSUSE Tumbleweed and Leap, and Solus.
    """
    print(f'\n\n§  Checking if user is in correct group(s)...\n{cnfg.separator}')

    # Handle 'input' group
    create_group(cnfg.input_group)
    group_info = grp.getgrnam(cnfg.input_group)
    if cnfg.user_name not in group_info.gr_mem:
        add_user_to_group(cnfg.input_group, cnfg.user_name)
    else:
        print(f'User "{cnfg.user_name}" is a member of group "{cnfg.input_group}".')

    # Handle 'systemd-journal' group for specific distributions
    systemd_journal_grp_distros = [
        *distro_groups_map['debian-based'],
        *distro_groups_map['leap-based'],
        *distro_groups_map['microos-based'],
        *distro_groups_map['rhel-based'],
        *distro_groups_map['solus-based'],
        *distro_groups_map['tumbleweed-based'],
    ]

    if cnfg.DISTRO_ID in systemd_journal_grp_distros:
        sysd_jrnl_group = 'systemd-journal'
        create_group(sysd_jrnl_group)
        group_info = grp.getgrnam(sysd_jrnl_group)
        if cnfg.user_name not in group_info.gr_mem:
            add_user_to_group(sysd_jrnl_group, cnfg.user_name)
        else:
            print(f'User "{cnfg.user_name}" is a member of group "{sysd_jrnl_group}".')

    show_task_completed_msg()


def clone_keymapper_branch():
    """Clone the designated keymapper branch from GitHub"""
    print(f'\n\n§  Cloning keymapper branch...\n{cnfg.separator}')

    # Check if `git` command exists. If not, exit script with error.
    has_git = shutil.which('git')
    if not has_git:
        print(f'ERROR: "git" is not installed, for some reason. Cannot continue.')
        safe_shutdown(1)

    if os.path.exists(cnfg.keymapper_tmp_path):
        # force a fresh copy of keymapper every time script is run
        try:
            shutil.rmtree(cnfg.keymapper_tmp_path)
        except (OSError, PermissionError, FileNotFoundError) as file_err:
            error(f"Problem removing existing '{cnfg.keymapper_tmp_path}' folder:\n\t{file_err}")
    try:
        subprocess.run(cnfg.keymapper_clone_cmd.split() + [cnfg.keymapper_tmp_path], check=True)
    except subprocess.CalledProcessError as proc_err:
        print()
        error(f'Problem while cloning keymapper branch from GitHub:\n\t{proc_err}')
        safe_shutdown(1)
    show_task_completed_msg()


def is_barebones_config_file() -> bool:
    """
    Determines whether the existing Toshy configuration file is of the 
    'barebones' type by reading and checking its contents.

    :param config_directory: The directory where the configuration file is located.
    :return: True if the config is of the 'barebones' type, False otherwise.
    """
    cfg_file_name               = 'toshy_config.py'
    cfg_file_path               = os.path.join(cnfg.toshy_dir_path, cfg_file_name)

    if os.path.isfile(cfg_file_path):
        try:
            with open(cfg_file_path, 'r', encoding='UTF-8') as file:
                cnfg.existing_cfg_data = file.read()
        except (FileNotFoundError, PermissionError, OSError) as file_err:
            print(f'Problem reading config file: {file_err}')
            return False

        pattern = r'###  SLICE_MARK_(?:START|END): (\w+)  ###.*'
        matches = re.findall(pattern, cnfg.existing_cfg_data)

        if 'barebones_user_cfg' in matches:
            return True
        elif any('barebones' in slice_name for slice_name in matches):
            return True
    else:
        print(f"No existing config file found at '{cfg_file_path}'.")
        return False


def extract_slices(data: str):
    """Utility function to store user content slices from existing config file data"""
    slices_dct = {}
    pattern_start               = r'###  SLICE_MARK_START: (\w+)  ###.*'
    pattern_end                 = r'###  SLICE_MARK_END: (\w+)  ###.*'
    matches_start               = list(re.finditer(pattern_start, data))
    matches_end                 = list(re.finditer(pattern_end, data))
    if len(matches_start) != len(matches_end):
        raise ValueError(   f'Mismatched slice markers in config file:'
                            f'\n\t{matches_start}, {matches_end}')
    for begin, end in zip(matches_start, matches_end):
        slice_name = begin.group(1)
        if end.group(1) != slice_name:
            raise ValueError(f'Mismatched slice markers in config file:\n\t{slice_name}')
        slice_start             = begin.end()
        slice_end               = end.start()
        slices_dct[slice_name]  = data[slice_start:slice_end]

    # Fix some deprecated variable names here, now that slice contents are 
    # in memory, prior to merging slices back into new config file.
    # Using a List of Tuples instead of a dict to guarantee processing order.
    deprecated_object_names_ordered_LoT = [
        ('OVERRIDE_DISTRO_NAME  ', 'OVERRIDE_DISTRO_ID    '),
        ('DISTRO_NAME  ', 'DISTRO_ID    '),
        ('OVERRIDE_DISTRO_NAME', 'OVERRIDE_DISTRO_ID'),
        ('DISTRO_NAME', 'DISTRO_ID'),
        ('Keyszer-specific config settings', 'Keymapper-specific config settings'),
        # Add more tuples as needed for other deprecated object names or strings
    ]

    for slice_name, content in slices_dct.items():
        for deprecated_name, new_name in deprecated_object_names_ordered_LoT:
            content = content.replace(deprecated_name, new_name)
        slices_dct[slice_name] = content

    # Logic to update deprecated slice names using a list of tuples (for exact ordering)
    deprecated_slice_names_ordered_LoT = [
        # Make 'keyszer_api' slice name generic; 'keyszer' was replaced with 'xwaykeyz'
        ('keyszer_api', 'keymapper_api'),
        # Add more tuples as needed for other deprecated slice names
    ]

    updated_slices_dct = {}
    for slice_name, content in slices_dct.items():
        for deprecated_name, new_name in deprecated_slice_names_ordered_LoT:
            if slice_name == deprecated_name:
                slice_name = new_name
                break
        updated_slices_dct[slice_name] = content

    slices_dct = updated_slices_dct

    # Protect the barebones config file if a slice tagged with "barebones" found, 
    if 'barebones_user_cfg' in slices_dct or any('barebones' in key for key in slices_dct):
        cnfg.barebones_config = True
        print(f'Found "barebones" type config file. Will upgrade with same type.')
    # Confirm replacement of regular config file with barebones config if CLI option is used
    # and there is a non-barebones existing config file. 
    elif cnfg.barebones_config:
        for attempt in range(3):
            response = input(
                f'\n'
                f'ALERT:\n'
                f'Existing config file is not a barebones config, but the barebones CLI \n'
                f'option was specified. Do you want to proceed and replace the existing \n'
                f'config with a barebones config? This will discard all existing settings. \n'
                f'A timestamped backup of the existing config folder will still be made. \n'
                f'Enter "YES" to proceed or "N" to exit:'
            )
            if response.lower() not in ['n', 'yes']: continue
            if response.lower() == 'yes':
                # User confirmed to replace the existing config with a barebones config.
                # So, return an empty slices dictionary.
                return {}
            elif response.lower() == 'n':
                print(f'User chose to exit installer...')
                safe_shutdown(0)
        # If user didn't confirm after 3 attempts, exit the program.
        print('User input invalid. Exiting...')
        safe_shutdown(1)
    # 
    return slices_dct


def merge_slices(data: str, slices) -> str:
    """Utility function to merge stored slices into new config file data"""
    pattern_start   = r'###  SLICE_MARK_START: (\w+)  ###.*'
    pattern_end     = r'###  SLICE_MARK_END: (\w+)  ###.*'
    matches_start   = list(re.finditer(pattern_start, data))
    matches_end     = list(re.finditer(pattern_end, data))
    data_slices     = []
    previous_end    = 0
    for begin, end in zip(matches_start, matches_end):
        slice_name = begin.group(1)
        if end.group(1) != slice_name:
            raise ValueError(f'Mismatched slice markers in config file:\n\t{slice_name}')
        slice_start     = begin.end()
        slice_end       = end.start()
        # add the part of the data before the slice, and the slice itself
        data_slices.extend([data[previous_end:slice_start], 
                            slices.get(slice_name, data[slice_start:slice_end])])
        previous_end = slice_end
    # add the part of the data after the last slice
    data_slices.append(data[previous_end:])
    # 
    return "".join(data_slices)


def backup_toshy_config():
    """Backup existing Toshy config folder"""
    print(f'\n\n§  Backing up existing Toshy config folder...\n{cnfg.separator}')

    timestamp = datetime.datetime.now().strftime('_%Y%m%d_%H%M%S')
    toshy_cfg_bkups_base_dir  = os.path.join(home_dir, '.config', 'toshy_config_backups')
    toshy_cfg_bkup_timestamp_dir  = os.path.realpath(
        os.path.join(toshy_cfg_bkups_base_dir, 'toshy' + timestamp))

    if not os.path.exists(cnfg.toshy_dir_path):
        print(f'No existing Toshy folder to backup.')
        cnfg.backup_succeeded = True
    else:
        cfg_file_name           = 'toshy_config.py'
        cfg_file_path           = os.path.join(cnfg.toshy_dir_path, cfg_file_name)

        if os.path.isfile(cfg_file_path):
            try:
                with open(cfg_file_path, 'r', encoding='UTF-8') as file:
                    cnfg.existing_cfg_data = file.read()
                print(f'Prepared existing config file data for merging into new config.')
            except (FileNotFoundError, PermissionError, OSError) as file_err:
                cnfg.existing_cfg_data = None
                error(f'Problem reading existing config file contents.\n\t{file_err}')
            if cnfg.existing_cfg_data is not None:
                try:
                    cnfg.existing_cfg_slices = extract_slices(cnfg.existing_cfg_data)
                except ValueError as value_err:
                    error(f'Problem extracting marked slices from existing config.\n\t{value_err}')
        else:
            print(f"No existing config file found at '{cfg_file_path}'.")

        if os.path.isfile(cnfg.db_file_path):
            try:
                os.unlink(f'{cnfg.run_tmp_dir}/{cnfg.db_file_name}')
            except (FileNotFoundError, PermissionError, OSError): pass
            try:
                shutil.copy(cnfg.db_file_path, f'{cnfg.run_tmp_dir}/')
            except (FileNotFoundError, PermissionError, OSError) as file_err:
                error(f"Problem copying preferences db file to '{cnfg.run_tmp_dir}':\n\t{file_err}")
        else:
            print(f'No existing preferences db file found in {cnfg.toshy_dir_path}.')
        try:
            # Define the ignore function
            def ignore_venv(dirname, filenames):
                return ['.venv'] if '.venv' in filenames else []
            # Copy files recursively from source to destination
            shutil.copytree(cnfg.toshy_dir_path, toshy_cfg_bkup_timestamp_dir, ignore=ignore_venv)
        except shutil.Error as copy_error:
            print(f"Failed to copy directory: {copy_error}")
            safe_shutdown(1)
        except OSError as os_error:
            print(f"Failed to copy directory: {os_error}")
            safe_shutdown(1)
        print(f"Backup completed to '{toshy_cfg_bkup_timestamp_dir}'")
        cnfg.backup_succeeded = True
    show_task_completed_msg()


def install_toshy_files():
    """Install Toshy files"""
    print(f'\n\n§  Installing Toshy files...\n{cnfg.separator}')
    if not cnfg.backup_succeeded:
        error(f'Backup of Toshy config folder failed? Bailing out.')
        safe_shutdown(1)
    keymapper_tmp_dir           = os.path.basename(cnfg.keymapper_tmp_path)
    try:
        if os.path.exists(cnfg.toshy_dir_path):
            try:
                shutil.rmtree(cnfg.toshy_dir_path)
            except (OSError, PermissionError, FileNotFoundError) as file_err:
                error(f'Problem removing existing Toshy config folder after backup:\n\t{file_err}')
        patterns_to_ignore = [
                '.git_hooks',
                '.git_hooks_install.sh',
                '.github',
                '.gitignore',
                '__pycache__',
                'CONTRIBUTING.md',
                'DO_NOT_USE_requirements.txt',
                keymapper_tmp_dir,
                'kwin-application-switcher',
                'LICENSE',
                'packages.json',
                'prep_centos_before_setup.sh',
                'README.md',
                'requirements.txt',
                this_file_name,
        ]
        # must use list unpacking (*) ignore_patterns() requires individual pattern arguments
        ignore_fn = shutil.ignore_patterns(*patterns_to_ignore)
        # Copy files recursively from source to destination
        shutil.copytree(this_file_dir, cnfg.toshy_dir_path, ignore=ignore_fn)
    except shutil.Error as copy_error:
        error(f"Failed to copy directory: {copy_error}")
    except OSError as os_error:
        error(f"Failed to create backup directory: {os_error}")
    if cnfg.barebones_config is True:
        toshy_default_cfg_barebones = os.path.join(
            cnfg.toshy_dir_path, 'default-toshy-config', 'toshy_config_barebones.py')
        toshy_new_cfg = os.path.join(
            cnfg.toshy_dir_path, 'toshy_config.py')
        shutil.copy(toshy_default_cfg_barebones, toshy_new_cfg)
        print(f'Installed default "barebones" Toshy config file.')
    else:
        toshy_default_cfg = os.path.join(
            cnfg.toshy_dir_path, 'default-toshy-config', 'toshy_config.py')
        toshy_new_cfg = os.path.join(
            cnfg.toshy_dir_path, 'toshy_config.py')
        shutil.copy(toshy_default_cfg, toshy_new_cfg)
        print(f'Installed default Toshy config file.')
    print(f"Toshy files installed in '{cnfg.toshy_dir_path}'.")

    # Copy the existing user prefs database file
    if os.path.isfile(f'{cnfg.run_tmp_dir}/{cnfg.db_file_name}'):
        try:
            shutil.copy(f'{cnfg.run_tmp_dir}/{cnfg.db_file_name}', cnfg.toshy_dir_path)
            print(f'Copied preferences db file from existing config folder.')
        except (FileExistsError, FileNotFoundError, PermissionError, OSError) as file_err:
            error(f"Problem copying preferences db file from '{cnfg.run_tmp_dir}':\n\t{file_err}")

    # Apply user customizations to the new config file.
    new_cfg_file = os.path.join(cnfg.toshy_dir_path, 'toshy_config.py')
    if cnfg.existing_cfg_slices is not None:
        try:
            with open(new_cfg_file, 'r', encoding='UTF-8') as file:
                new_cfg_data = file.read()
        except (FileNotFoundError, PermissionError, OSError) as file_err:
            error(f'Problem reading new config file:\n\t{file_err}')
            safe_shutdown(1)
        merged_cfg_data = None
        try:
            merged_cfg_data = merge_slices(new_cfg_data, cnfg.existing_cfg_slices)
        except ValueError as value_err:
            error(f'Problem when merging user customizations with new config file:\n\t{value_err}')
        if merged_cfg_data is not None:
            try:
                with open(new_cfg_file, 'w', encoding='UTF-8') as file:
                    file.write(merged_cfg_data)
            except (FileNotFoundError, PermissionError, OSError) as file_err:
                error(f'Problem writing to new config file:\n\t{file_err}')
                safe_shutdown(1)
            print(f"Existing user customizations applied to the new config file.")
    show_task_completed_msg()


class PythonVenvQuirksHandler():
    """Object to contain methods for prepping specific distro variants that
        need some extra work while installing the Python virtual environment"""

    def update_C_INCLUDE_PATH(self):
        # Needed to make a symlink to get `xkbcommon` to install in the venv:
        # sudo ln -s /usr/include/libxkbcommon/xkbcommon /usr/include/

        # As an alternative without `sudo`, update C_INCLUDE_PATH so that the
        # `xkbcommon.h` include file can be found during build process.
        # And the `wayland-client-core.h` include file for `pywayland` build.
        include_path = "/usr/include/libxkbcommon:/usr/include/wayland"
        if 'C_INCLUDE_PATH' in os.environ:
            os.environ['C_INCLUDE_PATH'] = f"{include_path}:{os.environ['C_INCLUDE_PATH']}"
        else:
            os.environ['C_INCLUDE_PATH'] = include_path
        
        print(f"C_INCLUDE_PATH updated: {os.environ['C_INCLUDE_PATH']}")

    def get_glib_version(self):
        """
        Get installed GLib version via pkg-config.
        Returns tuple (major, minor) or None if check fails.
        """
        for cmd in ['pkg-config', 'pkgconf']:
            if not shutil.which(cmd):
                continue
            try:
                result = subprocess.run(
                    [cmd, '--modversion', 'glib-2.0'],
                    stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=5
                )
                if result.returncode == 0:
                    version_str = result.stdout.strip()
                    parts = version_str.split('.')
                    if len(parts) >= 2:
                        return (int(parts[0]), int(parts[1]))
            except (subprocess.TimeoutExpired, ValueError, OSError):
                continue
        return None

    def should_pin_pygobject(self):
        """
        Determine if PyGObject should be pinned to <=3.50.0.
        PyGObject >= 3.51.0 requires GLib >= 2.80 (girepository-2.0).
        Returns True if pinning needed, False if system supports PyGObject 3.51+.
        """

        print('Checking if PyGObject should be pinned to <=3.50.0 ...')

        # First check to see if distro-specific handler already pinned PyGObject,
        # probably to an earlier version than 3.50.0.
        pinned_pkgs = [pkg for pkg in pip_pkgs if pkg.startswith('pygobject<=')]
        if pinned_pkgs:
            print(f'  PyGObject already pinned: {pinned_pkgs}')
            return False

        glib_version = self.get_glib_version()

        if glib_version is None:
            print('  Could not determine GLib version, should pin PyGObject<=3.50.0')
            return True

        major, minor = glib_version
        if (major, minor) < (2, 80):
            print(f'  GLib {major}.{minor} < 2.80, should pin PyGObject<=3.50.0')
            return True

        print(f'  GLib {major}.{minor} >= 2.80, no PyGObject pinning needed')
        return False

    def handle_venv_quirks_CentOS_7(self):
        print('Handling Python virtual environment quirks in CentOS 7...')
        # Avoid using systemd packages/services for CentOS 7
        cnfg.systemctl_present = False
        global pip_pkgs

        # Path where Python 3.8 should have been installed by this point
        rh_python38 = '/opt/rh/rh-python38/root/usr/bin/python3.8'
        if os.path.isfile(rh_python38) and os.access(rh_python38, os.X_OK):
            print("Good, Python version 3.8 is installed.")
        else:
            error("Error: Python version 3.8 is not installed. ")
            error("Failed to install Toshy from admin user first?")
            safe_shutdown(1)

        # Pin 'evdev' pip package to version 1.6.1 for CentOS 7 to
        # deal with ImportError and undefined symbol UI_GET_SYSNAME
        pip_pkgs = [pkg if pkg != "evdev" else "evdev==1.6.1" for pkg in pip_pkgs]

        # Pin 'pygobject' to <=3.44.1 for CentOS 7 compatibility
        pip_pkgs = [pkg if pkg != "pygobject" else "pygobject<=3.44.1" for pkg in pip_pkgs]
        print('  PyGObject pinned to <=3.44.1 for compatibility with distro')

    def handle_venv_quirks_CentOS_Stream_8(self):
        print('Handling Python virtual environment quirks in CentOS Stream 8...')

        # TODO: Add higher version if ever necessary (keep minimum 3.8)
        min_mnr_ver = cnfg.curr_py_rel_ver_mnr - 3           # check up to 2 vers before current
        max_mnr_ver = cnfg.curr_py_rel_ver_mnr + 3           # check up to 3 vers after current

        py_minor_ver_rng = range(max_mnr_ver, min_mnr_ver, -1)
        if py_interp_ver_tup < cnfg.curr_py_rel_ver_tup:
            print(f"Checking for appropriate Python version on system...")
            for check_py_minor_ver in py_minor_ver_rng:
                if shutil.which(f'python3.{check_py_minor_ver}'):
                    cnfg.py_interp_path = shutil.which(f'python3.{check_py_minor_ver}')
                    cnfg.py_interp_ver_str = f'3.{check_py_minor_ver}'
                    print(f'Found Python version {cnfg.py_interp_ver_str} available.')
                    break
            else:
                error(  f'ERROR: Did not find any appropriate Python interpreter version.')
                safe_shutdown(1)

        # Pin 'pygobject' to <=3.44.1 for CentOS Stream 8 compatibility
        global pip_pkgs
        pip_pkgs = [pkg if pkg != "pygobject" else "pygobject<=3.44.1" for pkg in pip_pkgs]
        print('  PyGObject pinned to <=3.44.1 for compatibility with distro')

    def handle_venv_quirks_Leap(self):
        print('Handling Python virtual environment quirks in Leap...')
        # Change the Python interpreter path to use current release version from pkg list
        # if distro is openSUSE Leap type (instead of using old 3.6 Python version).
        if shutil.which(f'python{cnfg.curr_py_rel_ver_str}'):
            cnfg.py_interp_path = shutil.which(f'python{cnfg.curr_py_rel_ver_str}')
            cnfg.py_interp_ver_str = cnfg.curr_py_rel_ver_str
            self.update_C_INCLUDE_PATH()
        else:
            print(  f'Current stable Python release version '
                    f'({cnfg.curr_py_rel_ver_str}) not found. ')
            safe_shutdown(1)

    def handle_venv_quirks_OpenMandriva(self):
        print('Handling Python virtual environment quirks in OpenMandriva...')
        # We need to run the exact same command twice on OpenMandriva, for unknown reasons.
        # So this instance of the command is just "prep" for the seemingly duplicate
        # command that follows it in setup_python_vir_env(). 
        subprocess.run(cnfg.venv_cmd_lst, check=True)

    def handle_venv_quirks_RHEL(self):
        print('Handling Python virtual environment quirks in RHEL-type distros...')
        # TODO: Add higher version if ever necessary (keep minimum 3.8)
        potential_versions = ['3.17', '3.16', '3.15', '3.14', '3.13',
                                '3.12', '3.11', '3.10', '3.9', '3.8']
        for version in potential_versions:
            # check if the version is already installed
            if shutil.which(f'python{version}'):
                cnfg.py_interp_path     = shutil.which(f'python{version}')
                cnfg.py_interp_ver_str  = version
                break

        # Pin 'pygobject' to <=3.44.1 for RHEL 8.x compatibility
        # Only needed for RHEL 8, not 9+
        if cnfg.distro_mjr_ver == '8':
            global pip_pkgs
            pip_pkgs = [pkg if pkg != "pygobject" else "pygobject<=3.44.1" for pkg in pip_pkgs]
            print('  PyGObject pinned to <=3.44.1 for compatibility with distro')

    def handle_venv_quirks_Tumbleweed(self):
        print('Handling Python virtual environment quirks in Tumbleweed...')
        self.update_C_INCLUDE_PATH()


# This FAILED to solve the issue of venv breaking when system Python version changes. Unused.
# def create_virtualenv_with_bootstrap():
#     """Creates a virtual environment using virtualenv installed in a temporary bootstrap venv.
    
#     Args:
#         python_interpreter: Path to Python interpreter to use
#         target_venv_path: Path where the final virtualenv should be created

#     This approach uses a temporary bootstrap venv to install virtualenv, then uses
#     that to create a more robust final virtual environment with better isolation.
#     """

#     python_interpreter          = cnfg.py_interp_path
#     target_venv_path            = cnfg.venv_path
#     bootstrap_venv_path         = f"{target_venv_path}_bootstrap"

#     try:
#         # Create bootstrap venv
#         print("Creating bootstrap Python environment...")
#         bootstrap_venv_cmd      = [python_interpreter, '-m', 'venv', bootstrap_venv_path]
#         subprocess.run(bootstrap_venv_cmd, check=True)

#         # Handle OpenMandriva's odd need for double venv creation to overcome a bug where
#         # the venv is only partially populated with the necessary components.
#         if cnfg.DISTRO_ID == 'openmandriva':
#             print("Handling OpenMandriva venv creation quirk...")
#             subprocess.run(bootstrap_venv_cmd, check=True)  # Second run, same command!

#         # Install 'virtualenv' in bootstrap venv, to be used to create final venv
#         print("Installing 'virtualenv' in bootstrap environment...")
#         bootstrap_pip_cmd       = os.path.join(bootstrap_venv_path, 'bin', 'pip')
#         # Upgrading pip avoids notice about newer version of pip being available
#         subprocess.run([bootstrap_pip_cmd, 'install', '--upgrade', 'pip'], check=True)
#         subprocess.run([bootstrap_pip_cmd, 'install', '--upgrade', 'virtualenv'], check=True)

#         # Use bootstrap's virtualenv to create final venv
#         virtualenv_cmd_path     = os.path.join(bootstrap_venv_path, 'bin', 'virtualenv')
#         final_venv_cmd_lst      = [
#             virtualenv_cmd_path,
#             '--copies',                 # Use copies instead of symlinks
#             '--download',               # Download latest pip/setuptools
#             '--always-copy',            # Copy all files, never symlink
#             '--no-periodic-update',     # Prevent automatic updates
#             target_venv_path
#         ]

#         print(f'Creating final virtual environment...')
#         print(f'Full command: {" ".join(final_venv_cmd_lst)}')
#         subprocess.run(final_venv_cmd_lst, check=True)

#     except subprocess.CalledProcessError as proc_err:
#         error(f"Failed during bootstrap/virtualenv creation: {proc_err}")
#         if os.path.exists(bootstrap_venv_path):
#             shutil.rmtree(bootstrap_venv_path)
#         safe_shutdown(1)

#     finally:
#         # Clean up bootstrap venv
#         print("Cleaning up bootstrap environment...")
#         if os.path.exists(bootstrap_venv_path):
#             shutil.rmtree(bootstrap_venv_path)


def setup_python_vir_env():
    """Setup a virtual environment to install Python packages"""
    venv_quirks_handler = PythonVenvQuirksHandler()

    print(f'\n\n§  Setting up the Python virtual environment...\n{cnfg.separator}')

    # Create the virtual environment if it doesn't exist, while handling any
    # venv quirks/prep that is sometimes necessary.
    if not os.path.exists(cnfg.venv_path):

        print(f"Using Python version: '{cnfg.py_interp_ver_str}'")

        # Define clear condition variables with short names
        is_CentOS_7             = cnfg.DISTRO_ID == 'centos' and cnfg.distro_mjr_ver == '7'
        is_CentOS_8             = cnfg.DISTRO_ID == 'centos' and cnfg.distro_mjr_ver == '8'
        is_CentOS_7_or_8        = cnfg.DISTRO_ID == 'centos' and cnfg.distro_mjr_ver in ['7', '8']
        is_Leap_based           = cnfg.DISTRO_ID in distro_groups_map['leap-based']
        is_RHEL_based           = cnfg.DISTRO_ID in distro_groups_map['rhel-based']
        is_Tumbleweed_based     = cnfg.DISTRO_ID in distro_groups_map['tumbleweed-based']

        # Order of elifs is very delicate unless conditions are 100% mutually exclusive, 
        # but the venv quirks handlers are set up to be independent (unlike distro quirks).
        if True is False: pass  # Dummy 'if' to equalize all 'elif' branches below

        elif is_CentOS_7:
            venv_quirks_handler.handle_venv_quirks_CentOS_7()

        elif is_CentOS_8:
            venv_quirks_handler.handle_venv_quirks_CentOS_Stream_8()

        elif is_Leap_based:
            venv_quirks_handler.handle_venv_quirks_Leap()

        elif is_RHEL_based and not is_CentOS_7_or_8:
            venv_quirks_handler.handle_venv_quirks_RHEL()

        elif is_Tumbleweed_based:
            venv_quirks_handler.handle_venv_quirks_Tumbleweed()

        # Pin PyGObject if GLib is too old (< 2.80) for PyGObject >= 3.51.0
        # Some distros also might have venv quirks handlers that pin PyGObject if
        # they don't have appropriate girepository 2.0 support packages available.
        # RHEL 8 and related are already pinning to <=3.44.1, so we must do this
        # check after the distro-specific handlers run above, pinning only if
        # necessary, and only if not already pinned.
        if venv_quirks_handler.should_pin_pygobject():
            global pip_pkgs
            pip_pkgs = [pkg if pkg != "pygobject" else "pygobject<=3.50.0" for pkg in pip_pkgs]

        try:
            # This FAILED to solve issue of venv breaking when system Python version changes.
            # # Use a bootstrap venv with virtualenv to create final venv
            # create_virtualenv_with_bootstrap()

            print(f'Full venv command: {" ".join(cnfg.venv_cmd_lst)}')
            subprocess.run(cnfg.venv_cmd_lst, check=True)

            if cnfg.DISTRO_ID in ['openmandriva']:
                venv_quirks_handler.handle_venv_quirks_OpenMandriva()

        except subprocess.CalledProcessError as proc_err:
            error(f'ERROR: Problem creating the Python virtual environment:\n\t{proc_err}')
            safe_shutdown(1)

    # We do not need to "activate" the venv right now, just create it
    print(f'Python virtual environment setup complete.')
    print(f"Location: '{cnfg.venv_path}'")
    show_task_completed_msg()


def install_pip_packages():
    """Install `pip` packages in the prepped Python virtual environment"""
    print(f'\n\n§  Installing/upgrading Python venv packages...\n{cnfg.separator}')

    global pip_pkgs

    venv_python_cmd = os.path.join(cnfg.venv_path, 'bin', 'python')
    venv_pip_cmd    = os.path.join(cnfg.venv_path, 'bin', 'pip')

    # Configure build paths to use venv's Python
    # Will this help avoid build issues when venv Python and system Python are different versions?

    include_path = subprocess.check_output(
        [venv_python_cmd, '-c', 'import sysconfig; print(sysconfig.get_path("include"))'],
        universal_newlines=True
    ).strip()

    lib_path = subprocess.check_output(
        [venv_python_cmd, '-c', 'import sysconfig; print(sysconfig.get_config_var("LIBDIR"))'],
        universal_newlines=True
    ).strip()

    print(f"Setting PYTHONPATH to: {include_path}")
    os.environ['PYTHONPATH'] = include_path
    
    print(f"Setting CFLAGS to: -I{include_path}")
    os.environ['CFLAGS'] = f"-I{include_path}"
    
    print(f"Setting LDFLAGS to: -L{lib_path}")
    os.environ['LDFLAGS'] = f"-L{lib_path}"

    # Bypass the install of 'dbus-python' pip package if option passed to 'install' command.
    # Diminishes peripheral app functionality and disables some Wayland methods, but 
    # allows installing Toshy even when 'dbus-python' build throws errors during install.
    if cnfg.no_dbus_python:
        pip_pkgs = [pkg for pkg in pip_pkgs if pkg != "dbus-python"]

        # We also need to remove the 'dbus-python' dependency line from the keymapper's
        # 'pyproject.toml' file before proceeding with pip_pkgs install sequence.
        # File will be at: ./keymapper-temp/pyproject.toml
        # Make backup with a filename that will be ignored and edit original in place.
        toml_file_path = os.path.join(this_file_dir, cnfg.keymapper_tmp_path, 'pyproject.toml')
        backup_path = toml_file_path + ".bak"

        try:
            shutil.copyfile(toml_file_path, backup_path)

            # Read the original file and filter out the specified dependency
            with open(toml_file_path, "r") as file:
                lines = file.readlines()

            # Write the changes back to the original file
            with open(toml_file_path, "w") as file:
                for line in lines:
                    if 'dbus-python' not in line:
                        file.write(line)
        except FileNotFoundError:
            print('\n\n')
            print(f"Error: The file '{toml_file_path}' does not exist.")
            print('\n\n')
        except IOError as e:
            print('\n\n')
            print(f"IO error occurred:\n\t{str(e)}")
            print('\n\n')

    # Filter out systemd packages if no 'systemctl' present
    filtered_pip_pkgs   = [
        pkg for pkg in pip_pkgs 
        if cnfg.systemctl_present or 'systemd' not in pkg
    ]

    commands        = [
        [venv_python_cmd, '-m', 'pip', 'install', '--upgrade', 'pip'],
        [venv_pip_cmd, 'install', '--upgrade', 'wheel'],
        [venv_pip_cmd, 'install', '--upgrade', 'setuptools'],
        [venv_pip_cmd, 'install', '--upgrade', 'pillow'],
        [venv_pip_cmd, 'install', '--upgrade'] + filtered_pip_pkgs
    ]
    for command in commands:
        result = subprocess.run(command)
        if result.returncode != 0:
            error(f'Problem installing/upgrading Python packages. Installer exiting.')
            safe_shutdown(1)
    if os.path.exists(cnfg.keymapper_tmp_path):
        result = subprocess.run([venv_pip_cmd, 'install', '--upgrade', cnfg.keymapper_tmp_path])
        if result.returncode != 0:
            error(f'Problem installing/upgrading keymapper utility.')
            safe_shutdown(1)
    else:
        error(f'Temporary keymapper clone folder missing. Unable to install keymapper.')
        safe_shutdown(1)
    show_task_completed_msg()


def install_bin_commands():
    """Install the convenient terminal commands (symlinks to scripts) to manage Toshy"""
    print(f'\n\n§  Installing Toshy terminal commands...\n{cnfg.separator}')
    script_path = os.path.join(cnfg.toshy_dir_path, 'scripts', 'toshy-bincommands-setup.sh')
    try:
        subprocess.run([script_path], check=True)
    except subprocess.CalledProcessError as proc_err:
        print()
        error(f'Problem while installing terminal commands:\n\t{proc_err}')
        safe_shutdown(1)
    show_task_completed_msg()


def replace_home_in_file(filename):
    """
    Utility function to replace '$HOME' in '.desktop' files with actual home path. 
    Shell script takes care of desktop app install, but this is still used in 
    placing other '.desktop' files.
    """
    # Read in the file
    with open(filename, 'r') as file:
        file_data = file.read()
    # Replace the target string
    file_data = file_data.replace('$HOME', home_dir)
    # Write the file out again
    with open(filename, 'w') as file:
        file.write(file_data)


def install_desktop_apps():
    """
    Install the convenient desktop apps to manage Toshy. Script now also takes care of 
    installing app icons, and replacing the '$HOME' placeholder in the desktop files.
    """
    print(f'\n\n§  Installing Toshy desktop apps...\n{cnfg.separator}')
    script_path = os.path.join(cnfg.toshy_dir_path, 'scripts', 'toshy-desktopapps-setup.sh')

    try:
        subprocess.run([script_path], check=True)
    except subprocess.CalledProcessError as proc_err:
        print()
        error(f'Problem installing Toshy desktop apps:\n\t{proc_err}')
        safe_shutdown(1)

    # SHELL SCRIPT NOW TAKES CARE OF THIS INTERNALLY:
    # desktop_files_path  = os.path.join(home_dir, '.local', 'share', 'applications')
    # tray_desktop_file   = os.path.join(desktop_files_path, 'Toshy_Tray.desktop')
    # # DEPRECATED (name caused generic Wayland icon in Plasma)
    # # gui_desktop_file    = os.path.join(desktop_files_path, 'Toshy_GUI.desktop')
    # # Desktop file name must match app class for icon to work in Plasma
    # gui_desktop_file    = os.path.join(desktop_files_path, 'app.toshy.preferences.desktop')
    # replace_home_in_file(tray_desktop_file)
    # replace_home_in_file(gui_desktop_file)

    show_task_completed_msg()


def do_kwin_reconfigure():
    """Utility function to run the KWin reconfigure command"""

    commands = ['gdbus', 'dbus-send', cnfg.qdbus_cmd]

    for cmd in commands:
        if shutil.which(cmd):
            break
    else:
        error(f'No expected D-Bus command available. Cannot do KWin reconfigure.')
        return

    # gdbus call --session --dest org.kde.KWin --object-path /KWin --method org.kde.KWin.reconfigure
    if shutil.which('gdbus'):
        try:
            cmd_lst = [ 'gdbus', 'call', '--session', 
                        '--dest', 'org.kde.KWin',
                        '--object-path', '/KWin', 
                        '--method', 'org.kde.KWin.reconfigure']
            subprocess.run(cmd_lst, check=True, stderr=DEVNULL, stdout=DEVNULL)
            return
        except subprocess.CalledProcessError as proc_err:
            error(f'Problem using "gdbus" to do KWin reconfigure.\n\t{proc_err}')

    # dbus-send --type=method_call --dest=org.kde.KWin /KWin org.kde.KWin.reconfigure
    if shutil.which('dbus-send'):
        try:
            cmd_lst = [ 'dbus-send', '--type=method_call',
                        '--dest=org.kde.KWin', '/KWin',
                        'org.kde.KWin.reconfigure']
            subprocess.run(cmd_lst, check=True, stderr=DEVNULL, stdout=DEVNULL)
            return
        except subprocess.CalledProcessError as proc_err:
            error(f'Problem using "dbus-send" to do KWin reconfigure.\n\t{proc_err}')

    # qdbus org.kde.KWin /KWin reconfigure
    if shutil.which(cnfg.qdbus_cmd):
        try:
            cmd_lst = [cnfg.qdbus_cmd, 'org.kde.KWin', '/KWin', 'reconfigure']
            subprocess.run(cmd_lst, check=True, stderr=DEVNULL, stdout=DEVNULL)
            return
        except subprocess.CalledProcessError as proc_err:
            error(f'Problem using "{cnfg.qdbus_cmd}" to do KWin reconfigure.\n\t{proc_err}')

    error(f'Failed to do KWin reconfigure. No available D-Bus utility worked.')


def get_kwin_script_index(script_name):
    """Utility function to get the index of a loaded KWin script"""

    kwin_dest               = "org.kde.KWin"
    kwin_script_iface       = "org.kde.kwin.Scripting"

    qdbus_idx_cmd         = ( f"qdbus {kwin_dest} /Scripting "
                                f"{kwin_script_iface}.loadScript {script_name}")
    dbus_send_idx_cmd     = ( f"dbus-send --print-reply --dest={kwin_dest} /Scripting "
                                f"{kwin_script_iface}.loadScript string:{script_name}")
    gdbus_idx_cmd         = ( f"gdbus call --session --dest {kwin_dest} --object-path /Scripting "
                                f"--method {kwin_script_iface}.loadScript {script_name}")

    try:
        if shutil.which('qdbus'):
            return subprocess.check_output(qdbus_idx_cmd, shell=True).strip().decode('utf-8')
        elif shutil.which('dbus-send'):
            return subprocess.check_output(dbus_send_idx_cmd, shell=True).strip().decode('utf-8')
        elif shutil.which('gdbus'):
            output = subprocess.check_output(gdbus_idx_cmd, shell=True).strip().decode('utf-8')
            # Extracting the numeric part from the tuple-like string
            script_index = output.strip("()").split(',')[0]
            return script_index
        else:
            error("No suitable D-Bus utility found to get script index.")
            return None
    except subprocess.CalledProcessError as proc_err:
        error(f"An error occurred while getting the script index: {proc_err}")
        return None


def run_kwin_script(script_name):
    """Utility function to run an already loaded and enabled KWin script"""

    kwin_dest               = "org.kde.KWin"
    kwin_script_iface       = "org.kde.kwin.Script"

    script_index            = get_kwin_script_index(script_name)
    if not script_index:
        error(f"Unable to run KWin script. No index returned.")
        return

    qdbus_run_cmd           = ( f"qdbus {kwin_dest} /{script_index} {kwin_script_iface}.run")
    dbus_send_run_cmd       = ( f"dbus-send --type=method_call --dest={kwin_dest} "
                            f"/{script_index} {kwin_script_iface}.run")
    gdbus_run_cmd           = ( f"gdbus call --session --dest {kwin_dest} --object-path "
                            f"/{script_index} --method {kwin_script_iface}.run")

    try:
        if shutil.which('qdbus'):
            subprocess.run(qdbus_run_cmd, shell=True, check=True)
        elif shutil.which('dbus-send'):
            subprocess.run(dbus_send_run_cmd, shell=True, check=True)
        elif shutil.which('gdbus'):
            subprocess.run(gdbus_run_cmd, shell=True, check=True)
        else:
            error("No suitable D-Bus utility found to run KWin script.")
    except subprocess.CalledProcessError as proc_err:
        error(f"An error occurred while executing the run command: {proc_err}")


def setup_kwin_dbus_script():
    """Install the KWin script to notify D-Bus service about window focus changes"""
    print(f'\n\n§  Setting up the Toshy KWin script...\n{cnfg.separator}')

    if cnfg.DESKTOP_ENV == 'kde':
        KDE_ver = cnfg.DE_MAJ_VER
    else:
        error("ERROR: Asked to install Toshy KWin script, but DE is not KDE.")
        return

    if KDE_ver not in cnfg.valid_KDE_vers:
        error("ERROR: Toshy KWin script cannot be installed.")
        error(f"KDE major version invalid: '{KDE_ver}'")
        return

    if KDE_ver in ['4', '3']:
        print(f'KDE {KDE_ver} is not Wayland compatible. Toshy KWin script unnecessary.')
        return

    kpackagetool_cmd        = f'kpackagetool{KDE_ver}'
    kwriteconfig_cmd        = f'kwriteconfig{KDE_ver}'

    kwin_script_name        = 'toshy-dbus-notifyactivewindow'
    kwin_script_path        = os.path.join( cnfg.toshy_dir_path,
                                            'kwin-script',
                                            # f'kde{KDE_ver}',
                                            'kde5_kde6_merged',
                                            kwin_script_name)
    kwin_script_tmp_file    = f'{cnfg.run_tmp_dir}/{kwin_script_name}.kwinscript'
    curr_script_path        = os.path.join( home_dir,
                                            '.local',
                                            'share',
                                            'kwin',
                                            'scripts',
                                            kwin_script_name)

    # Create a zip file (overwrite if it exists)
    with zipfile.ZipFile(kwin_script_tmp_file, 'w') as zipf:
        # Add main.js to the kwinscript package
        zipf.write(os.path.join(kwin_script_path, 'contents', 'code', 'main.js'),
                                arcname='contents/code/main.js')
        # Add metadata.desktop to the kwinscript package
        zipf.write(os.path.join(kwin_script_path, 'metadata.json'), arcname='metadata.json')

    # Try to unload existing KWin script from memory (not the same as uninstalling script files).
    # Critical step if KWin script has changed, such as new D-Bus address.
    # gdbus call --session --dest org.kde.KWin --object-path /Scripting \
                            # --method org.kde.kwin.Scripting.unloadScript "${script_name}"
    cmd_lst = [
        'gdbus', 'call', '--session',
        '--dest', 'org.kde.KWin',
        '--object-path', '/Scripting',
        '--method', 'org.kde.kwin.Scripting.unloadScript',
        kwin_script_name
    ]
    try:
        print(f"Trying to unload existing Toshy KWin script...")
        subprocess.run(cmd_lst, check=True, stderr=DEVNULL, stdout=DEVNULL)
        print(f"Unloaded existing Toshy KWin script.")
    except subprocess.CalledProcessError as proc_err:
        error(f"Problem while trying to unload existing Toshy KWin script:\n\t{proc_err}")
        error("You may need to remove existing Toshy KWin script and restart Toshy.")

    # Try to remove existing KWin script, only if it exists
    if os.path.exists(curr_script_path):
        # Try to remove any installed KWin script entirely
        process = subprocess.Popen(
            [kpackagetool_cmd, '-t', 'KWin/Script', '-r', kwin_script_name],
            stdout=PIPE, stderr=PIPE)
        out, err = process.communicate()
        out = out.decode('utf-8')
        err = err.decode('utf-8')
        result = subprocess.CompletedProcess(   args=process.args,
                                                returncode=process.returncode,
                                                stdout=out, stderr=err)

        if result.returncode != 0:
            error("Problem while uninstalling existing Toshy KWin script.")
            try:
                shutil.rmtree(curr_script_path)
                print(f'Removed existing Toshy KWin script folder (if any).')
            except (FileNotFoundError, PermissionError) as file_err:
                error(f'Problem removing existing Toshy KWin script folder:\n\t{file_err}')
                # safe_shutdown(1)
        else:
            print("Successfully removed existing Toshy KWin script.")

    # Install the KWin script
    cmd_lst = [kpackagetool_cmd, '-t', 'KWin/Script', '-i', kwin_script_tmp_file]
    process = subprocess.Popen(cmd_lst, stdout=PIPE, stderr=PIPE)
    out, err = process.communicate()
    out = out.decode('utf-8')
    err = err.decode('utf-8')
    result = subprocess.CompletedProcess(   args=process.args,
                                            returncode=process.returncode,
                                            stdout=out, stderr=err)

    if result.returncode != 0:
        error(f"Error installing the Toshy KWin script. The error was:\n\t{result.stderr}")
        safe_shutdown(1)
    else:
        print("Successfully installed the Toshy KWin script.")

    # Remove the temporary kwinscript file
    try:
        os.remove(kwin_script_tmp_file)
    except (FileNotFoundError, PermissionError): pass

    # Enable the KWin script
    cmd_lst = [kwriteconfig_cmd, '--file', 'kwinrc', '--group', 'Plugins', '--key',
            f'{kwin_script_name}Enabled', 'true']
    process = subprocess.Popen(cmd_lst, stdout=PIPE, stderr=PIPE)
    out, err = process.communicate()
    out = out.decode('utf-8')
    err = err.decode('utf-8')
    result = subprocess.CompletedProcess(   args=process.args,
                                            returncode=process.returncode,
                                            stdout=out, stderr=err)

    if result.returncode != 0:
        error(f"Error enabling the Toshy KWin script. The error was:\n\t{result.stderr}")
    else:
        print("Successfully enabled the Toshy KWin script.")

    # Try to get KWin to notice and activate the script on its own, now that it's in RC file
    do_kwin_reconfigure()

    show_task_completed_msg()


def ensure_XDG_autostart_dir_exists():
    """Utility function to make sure XDG autostart directory exists"""
    # autostart_dir_path      = os.path.join(home_dir, '.config', 'autostart')
    if not os.path.isdir(autostart_dir_path):
        try:
            os.makedirs(autostart_dir_path, exist_ok=True)
        except (PermissionError, NotADirectoryError) as file_err:
            error(f"Problem trying to make sure '{autostart_dir_path}' exists.\n\t{file_err}")
            safe_shutdown(1)


def cleanup_legacy_kwin_dbus_autostart():
    """Clean up an older method of launching the KWin D-Bus window context service"""

    # Nothing to clean up if autostart folder doesn't exist
    if not os.path.exists(autostart_dir_path):
        return

    # try to delete old desktop entry file that would have been installed by older setup script
    autostart_dbus_dt_file = os.path.join(autostart_dir_path, 'Toshy_KWin_DBus_Service.desktop')
    if os.path.isfile(autostart_dbus_dt_file):
        try:
            os.unlink(autostart_dbus_dt_file)
            print(f'Removed older KWin D-Bus desktop entry autostart.')
        except (PermissionError, OSError) as e:
            debug(f'Problem removing old D-Bus service desktop entry autostart:\n\t{e}')


def setup_systemd_services():
    """Invoke the systemd setup script to install the systemd service units"""
    print(f'\n\n§  Setting up the Toshy systemd services...\n{cnfg.separator}')
    if cnfg.systemctl_present and cnfg.init_system == 'systemd':
        script_path = os.path.join(cnfg.toshy_dir_path, 'scripts', 'bin', 'toshy-systemd-setup.sh')
        subprocess.run([script_path])
        print(f'Finished setting up Toshy systemd services.')
    else:
        print(f'System does not seem to be using "systemd" as init system.')
    show_task_completed_msg()


def autostart_systemd_kickstarter():
    """Install the desktop file that will make sure the systemd services are restarted 
    after a short logout-login sequence, when systemd fails to stop the user services"""

    ensure_XDG_autostart_dir_exists()

    svcs_kick_dt_file_name  = 'Toshy_Systemd_Service_Kickstart.desktop'
    toshy_dt_files_path     = os.path.join(cnfg.toshy_dir_path, 'desktop')
    svcs_kick_dt_file       = os.path.join(toshy_dt_files_path, svcs_kick_dt_file_name)
    # autostart_dir_path      = os.path.join(home_dir, '.config', 'autostart')
    dest_link_file          = os.path.join(autostart_dir_path, svcs_kick_dt_file_name)

    cmd_lst                 = ['ln', '-sf', svcs_kick_dt_file, dest_link_file]
    try:
        subprocess.run(cmd_lst, check=True)
    except subprocess.CalledProcessError as proc_err:
        error(f'Problem while setting up systemd kickstarter:\n\t{proc_err}')
        safe_shutdown(1)


def autostart_tray_icon():
    """Set up the tray icon to autostart at login"""
    print(f'\n\n§  Setting up tray icon to load automatically at login...\n{cnfg.separator}')
    
    # Path to the database file
    toshy_cfg_dir_path          = os.path.join(home_dir, '.config', 'toshy')
    prefs_db_file_name          = 'toshy_user_preferences.sqlite'
    prefs_db_file_path          = os.path.join(toshy_cfg_dir_path, prefs_db_file_name)
    
    autostart_preference        = True  # Default to autostarting tray icon
    
    # Check if the database file exists
    if os.path.isfile(prefs_db_file_path):
        try:
            sql_query = "SELECT value FROM config_preferences WHERE name = 'autostart_tray_icon'"

            with sqlite3.connect(prefs_db_file_path) as cnxn:
                cursor = cnxn.cursor()
                cursor.execute(sql_query)
                row = cursor.fetchone()

            if row is not None:
                # Convert the string value to a boolean
                autostart_preference = row[0].lower() == 'true'

        except sqlite3.Error as db_err:
            error(f"Could not read tray icon autostart preference from database:\n\t{db_err}")
            print("Defaulting to enabling autostart of tray icon.")

    if autostart_preference is True:
        tray_dt_file_name       = 'Toshy_Tray.desktop'
        home_apps_path          = os.path.join(home_dir, '.local', 'share', 'applications')
        tray_dt_file_path       = os.path.join(home_apps_path, tray_dt_file_name)
        home_autostart_path     = os.path.join(home_dir, '.config', 'autostart')
        tray_link_file_path     = os.path.join(home_autostart_path, tray_dt_file_name)
        try:
            ensure_XDG_autostart_dir_exists()
            cmd_lst                 = ['ln', '-sf', tray_dt_file_path, tray_link_file_path]
            subprocess.run(cmd_lst, check=True)
            print(f'Toshy tray icon should appear in system tray at each login.')
        except subprocess.CalledProcessError as proc_err:
            error(f'Problem while setting up tray icon autostart:\n\t{proc_err}')
            safe_shutdown(1)
    else:
        cnfg.autostart_tray_icon = False    # to disable setup from starting the tray icon
        print("Toshy tray icon autostart is disabled by user preference. Skipping.")

    show_task_completed_msg()



###################################################################################################
##  TWEAKS UTILITY FUNCTIONS - START
###################################################################################################


def apply_tweaks_Cinnamon():
    """Utility function to add desktop tweaks to Cinnamon"""

    cmd_lst         = ['./install.sh']
    dir_path        = os.path.join(this_file_dir, 'cinnamon-extension')

    try:
        subprocess.run(cmd_lst, cwd=dir_path, check=True)
        print(f'Installed Cinnamon extension for window context.')
    except subprocess.CalledProcessError as proc_err:
        error(f'Problem while installing Cinnamon extension:\n\t{proc_err}')

    # Let user know how to get Cmd+Space to open the Cinnamon Menu applet
    _show_cinnamon_menu_hotkey_reminder()


def apply_tweaks_GNOME():
    """Utility function to add desktop tweaks to GNOME"""

    # TODO: Find out if toggle-overview will be dropped(!) at some point. 

    # Disable GNOME 'overlay-key' binding to Meta/Super/Win/Cmd.
    # Interferes with some Meta/Super/Win/Cmd shortcuts.
    # gsettings set org.gnome.mutter overlay-key ''
    cmd_lst = ['gsettings', 'set', 'org.gnome.mutter', 'overlay-key', '']
    subprocess.run(cmd_lst)

    print(f'Disabled Super key opening GNOME overview. (Use Cmd+Space instead.)')

    # On GNOME 45 and later 'toggle-overview' is disabled, so we need to differentiate versions.
    # GNOME 44 and earlier will remap Cmd+Space to Super+S to match default 'toggle-overview'.
    # GNOME 45 and later reassigned Super+S to the 'Quick Settings' panel.
    # So we need to set a new shortcut for 'toggle-overview' on GNOME 45 and later.
    pre_GNOME_45_vers = ['44', '43', '42', '41', '40', '3']

    if cnfg.DE_MAJ_VER not in pre_GNOME_45_vers:
        # It's unset, so we define the shortcut we want to set: Shift+Ctrl+Space
        overview_binding = "['<Shift><Control>space']"
        cmd_lst = ['gsettings', 'set', 'org.gnome.shell.keybindings',
                    'toggle-overview', overview_binding]
        try:
            subprocess.run(cmd_lst, check=True)
            print(f'Set "toggle-overview" shortcut to "{overview_binding}".')
        except subprocess.CalledProcessError as proc_err:
            error(f'Problem while setting the "toggle-overview" shortcut.\n\t{proc_err}')

    # Enable keyboard shortcut for GNOME Terminal preferences dialog
    # gsettings set org.gnome.Terminal.Legacy.Keybindings:/org/gnome/terminal/legacy/keybindings/ \
    # preferences '<Control>comma'
    cmd_path = 'org.gnome.Terminal.Legacy.Keybindings:/org/gnome/terminal/legacy/keybindings/'
    prefs_binding = '<Control>comma'
    cmd_lst = ['gsettings', 'set', cmd_path, 'preferences', prefs_binding]
    subprocess.run(cmd_lst)
    print(f'Set a keybinding for GNOME Terminal preferences.')

    # Enable "Expandable folders" in Nautilus
    # dconf write /org/gnome/nautilus/list-view/use-tree-view true
    cmd_path = '/org/gnome/nautilus/list-view/use-tree-view'
    cmd_lst = ['dconf', 'write', cmd_path, 'true']
    subprocess.run(cmd_lst)

    # Set default view option in Nautilus to "list-view"
    # dconf write /org/gnome/nautilus/preferences/default-folder-viewer "'list-view'"
    cmd_path = '/org/gnome/nautilus/preferences/default-folder-viewer'
    cmd_lst = ['dconf', 'write', cmd_path, "'list-view'"]
    subprocess.run(cmd_lst)

    print(f'Set Nautilus default to List view with "Expandable folders" enabled.')


def remove_tweaks_GNOME():
    """Utility function to remove the tweaks applied to GNOME"""
    subprocess.run(['gsettings', 'reset', 'org.gnome.mutter', 'overlay-key'])
    print(f'Removed tweak to disable GNOME "overlay-key" binding to Meta/Super.')
    
    # gsettings reset org.gnome.desktop.wm.keybindings switch-applications
    subprocess.run(['gsettings', 'reset', 'org.gnome.desktop.wm.keybindings',
                    'switch-applications'])
    # gsettings reset org.gnome.desktop.wm.keybindings switch-group
    subprocess.run(['gsettings', 'reset', 'org.gnome.desktop.wm.keybindings', 'switch-group'])
    print(f'Removed tweak to enable more Mac-like task switching')


def apply_tweaks_KDE():
    """Utility function to add desktop tweaks to KDE"""

    if cnfg.DESKTOP_ENV == 'kde':
        KDE_ver = cnfg.DE_MAJ_VER
    else:
        error("ERROR: Asked to apply KDE tweaks, but DE is not KDE.")
        return

    # check that major release ver from env module is rational
    if KDE_ver not in cnfg.valid_KDE_vers:
        error("ERROR: Desktop tweaks for KDE cannot be applied.")
        error(f"KDE major version invalid: '{KDE_ver}'")
        return

    if KDE_ver in ['4', '3']:
        print(f'No tweaks available for KDE {KDE_ver}. Skipping.')
        return

    kstart_cmd          = f'kstart{KDE_ver}'

    if not shutil.which(kstart_cmd):
        # try just 'kstart' on KDE 6 if there is no 'kstart6'
        if shutil.which('kstart'):
            kstart_cmd          = 'kstart'
        # if no 'kstart', fall back to 'kstart5' if it exists
        elif shutil.which('kstart5'):
            kstart_cmd          = 'kstart5'

    kquitapp_cmd        = f'kquitapp{KDE_ver}'
    kwriteconfig_cmd    = f'kwriteconfig{KDE_ver}'

    # Documentation on the use of Meta key in KDE:
    # https://userbase.kde.org/Plasma/Tips#Windows.2FMeta_Key
    subprocess.run([kwriteconfig_cmd, '--file', 'kwinrc',
                    '--group', 'ModifierOnlyShortcuts',
                    '--key', 'Meta', ''], check=True)
    print(f'Disabled Meta key opening application menu. (Use Cmd+Space instead.)')

    # Run reconfigure command
    do_kwin_reconfigure()

    if cnfg.fancy_pants or cnfg.app_switcher:
        print(f'Installing "Application Switcher" KWin script...')
        # How to install nclarius grouped "Application Switcher" KWin script:
        # git clone https://github.com/nclarius/kwin-application-switcher.git
        # cd kwin-application-switcher
        # ./install.sh
        # 
        # switcher_url        = 'https://github.com/nclarius/kwin-application-switcher.git'

        # TODO: Revert to main repo if/when patch for this is accepted.
        # Patched branch that fixes some issues with maintaining grouping:
        # 'https://github.com/RedBearAK/kwin-application-switcher/tree/grouping_fix'

        # switcher_branch     = 'grouping_fix'

        # TODO: Revert to nclarius repo if/when this branch is merged.
        # Patched branch that merges API variations for KDE 5 and 6:
        # 'https://github.com/RedBearAK/kwin-application-switcher/tree/kde6_kde5_merged'
        # (includes the fixes from 'grouping_fix' branch)

        switcher_branch     = 'kde6_kde5_merged'
        switcher_repo       = 'https://github.com/RedBearAK/kwin-application-switcher.git'

        switcher_dir_name   = 'kwin-application-switcher'
        switcher_dir_path   = os.path.join(this_file_dir, switcher_dir_name)
        switcher_title      = 'KWin Application Switcher'
        switcher_cloned     = False

        git_clone_cmd_lst   = ['git', 'clone', '--branch']
        branch_args_lst     = [switcher_branch, switcher_repo, switcher_dir_path]

        # git should be installed by this point? Not necessarily.
        if not shutil.which('git'):
            error(f"Unable to clone {switcher_title}. Install 'git' and try again.")
        else:
            if os.path.exists(switcher_dir_path):
                try:
                    shutil.rmtree(switcher_dir_path)
                except (FileNotFoundError, PermissionError, OSError) as file_err:
                    warn(f'Problem removing existing switcher clone folder:\n\t{file_err}')
            try:
                subprocess.run(git_clone_cmd_lst + branch_args_lst, check=True)
                switcher_cloned = True
            except subprocess.CalledProcessError as proc_err:
                warn(f'Problem while cloning the {switcher_title} branch:\n\t{proc_err}')
            if not switcher_cloned:
                warn(f'Unable to install {switcher_title}. Clone did not succeed.')
            else:
                try:
                    subprocess.run(["./install.sh"], cwd=switcher_dir_path, check=True) #,
                                    # stdout=DEVNULL, stderr=DEVNULL)
                    # print(f'Installed "{switcher_title}" KWin script.')
                except subprocess.CalledProcessError as proc_err:
                    warn(f'Something went wrong installing {switcher_title}.\n\t{proc_err}')

        do_kwin_reconfigure()

        fix_task_switcher_cmd = ['./scripts/plasma-task-switcher-fixer.sh']
        try:
            subprocess.run(fix_task_switcher_cmd, check=True)
        except subprocess.CalledProcessError as proc_err:
            error(f'Problem fixing the Plasma task switcher via script.\n\t{proc_err}')


        # Disable single click to open/launch files/folders:
        # kwriteconfig5 --file kdeglobals --group KDE --key SingleClick false
        SingleClick_cmd         = [ kwriteconfig_cmd,
                                    '--file', 'kdeglobals',
                                    '--group', 'KDE',
                                    '--key', 'SingleClick', 'false']
        subprocess.run(SingleClick_cmd, check=True)
        print('Disabled single-click to open/launch files/folders')


def remove_tweaks_KDE():
    """Utility function to remove the tweaks applied to KDE"""

    if cnfg.DESKTOP_ENV == 'kde':
        KDE_ver = cnfg.DE_MAJ_VER
    else:
        error("ERROR: Asked to remove KDE tweaks, but DE is not KDE.")
        return

    # check that major release ver from env module is rational
    if KDE_ver not in cnfg.valid_KDE_vers:
        error("ERROR: Desktop tweaks for KDE cannot be removed.")
        error(f"KDE major version invalid: '{KDE_ver}'")
        return

    if KDE_ver in ['4', '3']:
        print('No tweaks were applied for KDE 4 or 3. Nothing to remove.')
        return

    kwriteconfig_cmd    = f'kwriteconfig{KDE_ver}'

    # Re-enable Meta key opening the application menu
    subprocess.run([kwriteconfig_cmd,
                    '--file', 'kwinrc',
                    '--group', 'ModifierOnlyShortcuts',
                    '--key', 'Meta', '--delete'],
                    check=True)
    # Disable the "Only one window per application" task switcher option
    subprocess.run([kwriteconfig_cmd,
                    '--file', 'kwinrc',
                    '--group', 'TabBox', 
                    '--key', 'ApplicationsMode', '--delete'],
                    check=True)

    # Run reconfigure command
    do_kwin_reconfigure()
    print(f'Re-enabled Meta key opening application menu.')
    print(f'Disabled "Only one window per application" task switcher option.')


def install_coding_font():
    """Utility function to take care of installing the terminal/coding font"""

    print(f'Installing terminal/coding font "FantasqueSansMNoLig Nerd Font": ', flush=True)

    # Install Fantasque Sans Mono Nerd Font
    # (variant with no ligatures, large line height, no "loop K").
    # Created from spinda no-ligatures fork by processing with Nerd Font script.
    # Original repo: https://github.com/spinda/fantasque-sans-ligatures
    font_file               = 'FantasqueSansMNoLig_Nerd_Font.zip'
    font_url                = 'https://github.com/RedBearAK/FantasqueSansMNoLigNerdFont/raw/main'
    font_link               = f'{font_url}/{font_file}'
    zip_path                = f'{cnfg.run_tmp_dir}/{font_file}'

    print(f'  Downloading… ', end='', flush=True)

    cannot_download_font    = False
    if shutil.which('curl'):
        subprocess.run(['curl', '-Lo', zip_path, font_link], stdout=DEVNULL, stderr=DEVNULL)
    elif shutil.which('wget'):
        subprocess.run(['wget', '-O', zip_path, font_link], stdout=DEVNULL, stderr=DEVNULL)
    else:
        error("\nERROR: Neither the 'curl' nor 'wget' utils are available. Cannot download font.")
        cannot_download_font = True

    if not cannot_download_font and os.path.isfile(zip_path):

        print(f'Unzipping… ', end='', flush=True)

        final_folder_name       = None
        fallback_folder_name    = font_file.rsplit('.', 1)[0]
        local_fonts_dir         = os.path.join(home_dir, '.local', 'share', 'fonts')
        extract_dir             = f'{local_fonts_dir}/' # extract directly to local fonts folder

        # Open the zip file and check if it has a top-level directory
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:

            # Get the first part of each path in the zip file
            top_dirs = {name.split('/')[0] for name in zip_ref.namelist()}

            if len(top_dirs) > 1:
                # Set the final folder name to the fallback from zip file name
                final_folder_name = fallback_folder_name
                # If the zip doesn't have a consistent top-level directory, 
                # adjust extract_dir and create one
                extract_dir = os.path.join(extract_dir, fallback_folder_name)
            else:
                # Get the single top directory name
                final_folder_name = list(top_dirs)[0]

            os.makedirs(extract_dir, exist_ok=True)
            zip_ref.extractall(extract_dir)

        print(f'Refreshing font cache… ', end='', flush=True)

        # Update the font cache after putting the font files in place
        # Any open applications will still need to be restarted to see a new font
        cmd_lst = ['fc-cache', '-f', '-v']
        try:
            subprocess.run(cmd_lst, stdout=DEVNULL, stderr=DEVNULL)
            print(f'Done.', flush=True)
        except subprocess.CalledProcessError as proc_err:
            error(f"\nERROR: Problem while attempting to refresh font cache:\n  {proc_err}")

        final_folder_path = os.path.join(extract_dir, final_folder_name)
        print(f"Installed font into location:\n  '{final_folder_path}'")


def _show_cinnamon_menu_hotkey_reminder():
    """
    Show a reminder about configuring the Cinnamon menu hotkey for Cmd+Space.
    
    Checks if the menu applet is using default Super_L shortcut, and if so,
    shows instructions for manually configuring it to work with Toshy.
    """
    import json

    menu_uuid = 'menu@cinnamon.org'
    configs_dir = os.path.join(home_dir, '.cinnamon', 'configs', menu_uuid)
    needs_reminder = True  # Default to showing reminder if checks fail

    # Get enabled applets to find the menu instance ID(s)
    try:
        result = subprocess.run(
            ['gsettings', 'get', 'org.cinnamon', 'enabled-applets'],
            capture_output=True, text=True, check=True
        )
        enabled_applets_str = result.stdout.strip()
    except subprocess.CalledProcessError:
        enabled_applets_str = ''

    # Parse the applet list to find menu@cinnamon.org instance IDs
    # Format: 'panel1:left:0:menu@cinnamon.org:23'
    instance_ids = []

    if enabled_applets_str.startswith('[') and enabled_applets_str.endswith(']'):
        applet_entries = enabled_applets_str[1:-1].split(', ')
        for entry in applet_entries:
            entry = entry.strip().strip("'")
            if menu_uuid in entry:
                parts = entry.split(':')
                if len(parts) >= 5:
                    instance_ids.append(parts[-1])

    # Check if any menu applet still has default shortcut (needs configuration)
    for instance_id in instance_ids:
        config_file = os.path.join(configs_dir, f'{instance_id}.json')

        if not os.path.isfile(config_file):
            continue

        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue

        overlay_key_value = ''
        if 'overlay-key' in config:
            overlay_key_value = config['overlay-key'].get('value', '')

        # Check if already configured for Toshy (has <Control>Escape)
        if '<Control>Escape' in overlay_key_value:
            needs_reminder = False
            break

    if not needs_reminder:
        return

    reminder_text = (
        "Cinnamon Menu Hotkey Setup\n"
        "\n"
        "To make Cmd+Space open the Cinnamon app menu:\n"
        "\n"
        "1. Right-click the menu icon in the panel\n"
        "2. Select 'Configure...'\n"
        "3. Go to the 'Behavior' tab\n"
        "4. Click on one of the 'Keyboard shortcut' fields\n"
        "5. Press Cmd+Space (will display as 'Ctrl+Escape')\n"
        "6. Close the configuration window\n"
        "\n"
        "You can replace either shortcut slot, or clear one first."
    )

    print()
    print('=' * 60)
    print(reminder_text)
    print('=' * 60)
    print()

    # Show zenity dialog (non-blocking, don't wait for user)
    if shutil.which('zenity'):
        try:
            subprocess.Popen(
                ['zenity', '--info', '--title=Toshy Setup', '--text=' + reminder_text,
                    '--width=450', '--height=300'],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
        except OSError:
            pass  # zenity failed, terminal reminder is enough


###################################################################################################
##  TWEAKS UTILITY FUNCTIONS - END
###################################################################################################


def apply_desktop_tweaks():
    """
    Fix things like Meta key activating overview in GNOME or KDE Plasma
    and fix the Unicode sequences in KDE Plasma
    
    TODO: These tweaks should probably be done at startup of the config
            instead of (or in addition to) here in the installer. 
    """

    print(f'\n\n§  Applying any known desktop environment tweaks...\n{cnfg.separator}')

    if cnfg.barebones_config or is_barebones_config_file():
        print('Not applying tweaks due to barebones config flag or file.')
        show_task_completed_msg()
        return

    if cnfg.fancy_pants:
        print(f'Fancy-Pants install invoked. Additional steps will be taken.')

    if cnfg.DESKTOP_ENV == 'cinnamon':
        print(f'Applying Cinnamon desktop tweaks...')
        apply_tweaks_Cinnamon()
        cnfg.tweak_applied = True

    if cnfg.DESKTOP_ENV == 'gnome':
        print(f'Applying GNOME desktop tweaks...')
        apply_tweaks_GNOME()
        cnfg.tweak_applied = True

    if cnfg.DESKTOP_ENV == 'kde':
        print(f'Applying KDE Plasma desktop tweaks...')
        apply_tweaks_KDE()
        cnfg.tweak_applied = True

    # General (not DE specific) "fancy pants" additions:
    if cnfg.fancy_pants:
        print(f'Initiating DE-agnostic Fancy-Pants option(s)...')

        try:
            install_coding_font()
            cnfg.tweak_applied = True
        except Exception as e:
            error(f'Some problem occurred attempting to install the font: \n\t{e}')

    if not cnfg.tweak_applied:
        print(f'If nothing printed, no tweaks available for "{cnfg.DESKTOP_ENV}" yet.')

    show_task_completed_msg()


def remove_desktop_tweaks():
    """Undo the relevant desktop tweaks"""

    print(f'\n\n§  Removing any applied desktop environment tweaks...\n{cnfg.separator}')

    if cnfg.barebones_config or is_barebones_config_file():
        print('Not removing tweaks due to barebones config flag or file.')
        show_task_completed_msg()
        return

    # if GNOME, re-enable `overlay-key`
    # gsettings reset org.gnome.mutter overlay-key
    if cnfg.DESKTOP_ENV == 'gnome':
        print(f'Removing GNOME desktop tweaks...')
        remove_tweaks_GNOME()

    if cnfg.DESKTOP_ENV == 'kde':
        print(f'Removing KDE Plasma desktop tweaks...')
        remove_tweaks_KDE()
        
    print('Removed known desktop tweaks applied by installer.')
    show_task_completed_msg()


def uninstall_toshy():
    print(f'\n\n§  Uninstalling Toshy...\n{cnfg.separator}')
    
    # confirm if user really wants to uninstall
    response = input("\nThis will completely uninstall Toshy. Are you sure? [y/N]: ")
    if response not in ['y', 'Y']:
        print(f"\nToshy uninstall cancelled.")
        safe_shutdown(0)
    else:
        print(f'\nToshy uninstall proceeding...\n')
    
    get_environment_info()
    
    remove_desktop_tweaks()
    
    # stop Toshy manual script if it is running
    toshy_cfg_stop_cmd = os.path.join(home_local_bin, 'toshy-config-stop')
    subprocess.run([toshy_cfg_stop_cmd])
    
    if cnfg.systemctl_present and cnfg.init_system == 'systemd':
        # stop Toshy systemd services if they are running
        toshy_svcs_stop_cmd = os.path.join(home_local_bin, 'toshy-services-stop')
        subprocess.run([toshy_svcs_stop_cmd])
        # run the systemd-remove script
        sysd_rm_cmd = os.path.join(cnfg.toshy_dir_path, 'scripts', 'bin', 'toshy-systemd-remove.sh')
        subprocess.run([sysd_rm_cmd])
    else:
        print(f'System does not seem to be using "systemd". Skipping removal of services.')

    if cnfg.DESKTOP_ENV in ['kde', 'plasma']:
        # unload/uninstall/remove KWin script(s)
        kwin_script_name = 'toshy-dbus-notifyactivewindow'
        KDE_ver = cnfg.DE_MAJ_VER
        try:
            cmd_lst = [f'kpackagetool{KDE_ver}', '-t', 'KWin/Script', '-r', kwin_script_name]
            subprocess.run(cmd_lst, check=True)
            print("Successfully removed the Toshy D-Bus NotifyActiveWindow KWin script.")
        except subprocess.CalledProcessError as proc_err:
            error(f'Problem removing Toshy KWin script {kwin_script_name}:\n\t{proc_err}')

        # kill the KDE D-Bus service script
        try:
            cmd_lst = ['pkill', '-u', cnfg.user_name, '-f', 'toshy_kwin_dbus_service']
            subprocess.run(cmd_lst, check=True)
        except subprocess.CalledProcessError as proc_err:
            error(f'Problem terminating Toshy KWin D-Bus service script:\n\t{proc_err}')

    # try to remove the KDE D-Bus service autostart file
    # autostart_dir_path  = os.path.join(home_dir, '.config', 'autostart')
    dbus_svc_dt_file    = os.path.join(autostart_dir_path, 'Toshy_KWin_DBus_Service.desktop')
    dbus_svc_rm_cmd     = ['rm', '-f', dbus_svc_dt_file]
    try:
        # do not pass as list (brackets) since it is already a list
        subprocess.run(dbus_svc_rm_cmd, check=True)
    except subprocess.CalledProcessError as proc_err:
        error(f'Problem removing Toshy KWin D-Bus service autostart:\n\t{proc_err}')

    # try to remove the systemd services kickstart autostart file
    # autostart_dir_path  = os.path.join(home_dir, '.config', 'autostart')
    svcs_kick_dt_file   = os.path.join(autostart_dir_path, 'Toshy_Systemd_Service_Kickstart.desktop')
    svcs_kick_rm_cmd    = ['rm', '-f', svcs_kick_dt_file]
    try:
        # do not pass as list (brackets) since it is already a list
        subprocess.run(svcs_kick_rm_cmd, check=True)
    except subprocess.CalledProcessError as proc_err:
        error(f'Problem removing Toshy systemd services kickstart autostart:\n\t{proc_err}')

    # terminate the tray icon process
    stop_tray_cmd = ['pkill', '-u', cnfg.user_name, '-f', 'toshy_tray']
    try:
        # do not pass as list (brackets) since it is already a list
        subprocess.run(stop_tray_cmd, check=True)
    except subprocess.CalledProcessError as proc_err:
        print(f'Problem stopping the tray icon process:\n\t{proc_err}')

    # remove the tray icon autostart file
    old_tray_autostart_file     = os.path.join(autostart_dir_path, 'Toshy_Tray.desktop')
    tray_autostart_rm_cmd       = ['rm', '-f', old_tray_autostart_file]
    try:
        # do not pass as list (brackets) since it is already a list
        subprocess.run(tray_autostart_rm_cmd, check=True)
    except subprocess.CalledProcessError as proc_err:
        error(f'Problem removing Toshy tray icon autostart:\n\t{proc_err}')

    # run the desktopapps-remove script
    apps_rm_cmd = os.path.join(cnfg.toshy_dir_path, 'scripts', 'toshy-desktopapps-remove.sh')
    try:
        subprocess.run([apps_rm_cmd], check=True)
    except subprocess.CalledProcessError as proc_err:
        error(f'Problem removing Toshy desktop apps:\n\t{proc_err}')

    # run the bincommands-remove script
    bin_rm_cmd = os.path.join(cnfg.toshy_dir_path, 'scripts', 'toshy-bincommands-remove.sh')
    try:
        subprocess.run([bin_rm_cmd], check=True)
    except subprocess.CalledProcessError as proc_err:
        error(f'Problem removing Toshy bin commands apps:\n\t{proc_err}')

    response_rm_udev_rules = input('Remove the Toshy "udev/uinput" rules file? [y/N]: ')
    if response_rm_udev_rules.lower() == 'y':
        elevate_privileges()
        # define the udev rules file path
        udev_rules_file = '/etc/udev/rules.d/70-toshy-keymapper-input.rules'
        # remove the 'udev' rules file
        try:
            subprocess.run([cnfg.priv_elev_cmd, 'rm', '-f', udev_rules_file], check=True)
        except subprocess.CalledProcessError as proc_err:
            error(f'Problem removing Toshy udev rules file:\n\t{proc_err}')
        # refresh the active 'udev' rules
        reload_udev_rules()

    print()
    print()
    print(cnfg.separator)
    print('Toshy uninstall complete. Reboot if indicated above with ASCII banner.')
    print("The '~/.config/toshy' folder with your settings has NOT been removed.")
    print('Please report any problems or leftover files/commands on the GitHub repo:')
    print('  https://github.com/RedBearAK/toshy/issues/')
    print(cnfg.separator)
    print()


def run_install_sequence(cnfg: InstallerSettings):
    """Main installer function to call specific functions in proper sequence"""

    if not cnfg.prep_only:
        dot_Xmodmap_warning()

    ask_is_distro_updated()

    if not cnfg.prep_only:
        ask_add_home_local_bin()

    get_environment_info()

    if cnfg.DISTRO_ID not in get_supported_distro_ids_lst():
        exit_with_invalid_distro_error()

    if not cnfg.prep_only:

        if cnfg.DESKTOP_ENV == 'gnome' and cnfg.SESSION_TYPE == 'wayland':
            check_gnome_wayland_exts()

        if cnfg.DESKTOP_ENV == 'gnome':
            check_gnome_indicator_ext()

        app_switcher_kwin_compat = cnfg.DESKTOP_ENV == 'kde' and cnfg.DE_MAJ_VER in ['5', '6']
        if app_switcher_kwin_compat and not cnfg.fancy_pants:
            # Need to limit this check to the versions of KDE Plasma
            # that are actually compatible with the KWin script (5/6).
            check_kde_app_switcher()

    elevate_privileges()

    if not cnfg.skip_native and not cnfg.unprivileged_user:
        # This will also be skipped if user proceeds with 
        # "unprivileged_user" install sequence.
        install_distro_pkgs()

    if not cnfg.unprivileged_user:
        # These things require 'sudo/doas/run0' (admin user)
        # Allow them to be skipped to support non-admin users
        # (An admin user would need to first do the "prep-only" command to support this)

        # load_uinput_module()
        setup_uinput_module()

        install_udev_rules()
        if not cnfg.prep_only:
            # We don't need to check the user group for admin doing prep-only command
            verify_user_groups()

    if cnfg.prep_only:
        print()
        print('########################################################################')
        print('FINISHED with prep-only tasks. Unprivileged users can now install Toshy.')
        safe_shutdown(0)

    elif not cnfg.prep_only:
        clone_keymapper_branch()

        backup_toshy_config()
        install_toshy_files()

        setup_python_vir_env()
        install_pip_packages()

        install_bin_commands()
        install_desktop_apps()

        # Python D-Bus service script also does this, but this will refresh if script changes
        if cnfg.DESKTOP_ENV in ['kde', 'plasma']:
            setup_kwin_dbus_script()

        # Some users might still have an older KWin D-Bus service desktop autostart file
        cleanup_legacy_kwin_dbus_autostart()

        setup_systemd_services()

        autostart_systemd_kickstarter()

        autostart_tray_icon()
        apply_desktop_tweaks()

        # Removed the GNOME extensions checks, which happen earlier/elsewhere now.

        if os.path.exists(cnfg.reboot_tmp_file):
            cnfg.should_reboot = True

        # Check if we can skip the reboot notice on some systems where 'uaccess' works well
        if cnfg.should_reboot:
            if can_skip_reboot():
                print("Device permissions verified in current session.")
                if os.path.exists(cnfg.reboot_tmp_file):
                    try:
                        os.remove(cnfg.reboot_tmp_file)
                    except OSError:
                        pass
                cnfg.should_reboot = False

        if cnfg.should_reboot:
            # create reboot reminder temp file, in case installer is run again before a reboot
            if not os.path.exists(cnfg.reboot_tmp_file):
                os.mknod(cnfg.reboot_tmp_file)
            lb = cnfg.sep_char * 2      # shorter variable name for left border chars
            show_reboot_prompt()
            print(f'{lb}  Toshy install complete. Report issues on the GitHub repo.')
            print(f'{lb}  https://github.com/RedBearAK/toshy/issues/')
            print(f'{lb}  >>  ALERT: Permissions changed. You MUST reboot for Toshy to work.')
            print(cnfg.separator)
            print(cnfg.separator)
            print()
        else:

            # Do not (re)start the tray icon here unless user preference allows it
            if cnfg.autostart_tray_icon:
                # Try to start the tray icon immediately, if reboot is not indicated
                tray_icon_cmd = [os.path.join(home_dir, '.local', 'bin', 'toshy-tray')]
                # Try to launch the tray icon in a separate process not linked to current shell
                # Also, suppress output that might confuse the user
                subprocess.Popen(tray_icon_cmd, close_fds=True, stdout=DEVNULL, stderr=DEVNULL)

            lb = cnfg.sep_char * 2      # shorter variable name for left border chars

            print()
            print()
            print()
            print(cnfg.separator)
            print(cnfg.separator)
            print(f'{lb}  Toshy install complete. Rebooting should not be necessary.')
            print(f'{lb}  Report issues on the GitHub repo.')
            print(f'{lb}  https://github.com/RedBearAK/toshy/issues/')
            print(cnfg.separator)
            print(cnfg.separator)
            print()
            if cnfg.SESSION_TYPE == 'wayland' and cnfg.DESKTOP_ENV == 'kde':
                print(f'Switch to a different window ONCE to get KWin script to start working!')

        def print_gnome_extensions_alert():
            print(f'You MUST install GNOME EXTENSIONS if using Wayland+GNOME! See Toshy README.')

        if cnfg.remind_extensions:
            print_gnome_extensions_alert()
        elif cnfg.DESKTOP_ENV == 'gnome' and cnfg.SESSION_TYPE == 'wayland':
            print_gnome_extensions_alert()

    safe_shutdown(0)


def main():
    """Deal with CLI arguments given to installer script"""
    parser = argparse.ArgumentParser(
        description='Toshy Installer - commands are mutually exclusive',
        epilog=f'Check install options with "./{this_file_name} install --help"',
        allow_abbrev=False
    )

    parser.add_argument(
        '--version',
        action='version',
        version=f'%(prog)s version: {__version__}',
        help='Show the version of the installer and exit'
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')


    subparser_install           = subparsers.add_parser(
        'install',
        help='Install Toshy (see options to modify install actions)'
    )

    subparser_install.add_argument(
        '--override-distro',
        type=str,
        help=f'Override auto-detection of distro. See "list-distros" command.'
    )
    subparser_install.add_argument(
        '--barebones-config',
        action='store_true',
        help='Install with mostly empty/blank keymapper config file.'
    )
    subparser_install.add_argument(
        '--skip-native',
        action='store_true',
        help='Skip the install of native packages (for debugging installer).'
    )
    subparser_install.add_argument(
        '--no-dbus-python',
        action='store_true',
        help='Avoid installing "dbus-python" pip package (breaks some stuff).'
    )
    subparser_install.add_argument(
        '--dev-keymapper',
        nargs='?',          # Makes the argument optional
        const=True,         # Value if flag is present but no branch specified
        default=False,
        metavar='BRANCH',
        help='Install the development branch of the keymapper. '
                'Optionally specify a custom branch name.'
    )
    subparser_install.add_argument(
        '--fancy-pants',
        action='store_true',
        help='See README for more info on this option.'
    )


    subparser_list_distros      = subparsers.add_parser(
        'list-distros',
        help='Display list of distros to use with "--override-distro"'
    )

    subparser_show_env          = subparsers.add_parser(
        'show-env',
        help='Show the environment the installer detects, and exit'
    )


    subparser_apply_tweaks      = subparsers.add_parser(
        'apply-tweaks',
        help='Apply desktop environment tweaks only, no install'
    )

    subparser_apply_tweaks.add_argument(
        '--fancy-pants',
        action='store_true',
        help='See README for more info on this option.'
    )

    subparser_remove_tweaks     = subparsers.add_parser(
        'remove-tweaks',
        help='Remove desktop environment tweaks only, no install'
    )

    subparser_install_font      = subparsers.add_parser(
        'install-font',
        help='Install Fantasque Sans Mono coding/terminal font'
    )

    subparser_prep_only         = subparsers.add_parser(
        'prep-only',
        help='Do only prep steps that require admin privileges, no install'
    )

    subparser_uninstall         = subparsers.add_parser(
        'uninstall',
        help='Uninstall Toshy'
    )


    args = parser.parse_args()

    # show help output if no command given
    if args.command is None:
        parser.print_help()
        safe_shutdown(0)

    elif args.command == 'prep-only':
        cnfg.prep_only = True

        run_install_sequence(cnfg)
        safe_shutdown(0)    # redundant, but that's OK

    elif args.command == 'install':
        if args.override_distro:
            cnfg.override_distro = args.override_distro

        if args.barebones_config:
            cnfg.barebones_config = True

        if args.skip_native:
            cnfg.skip_native = True

        if args.no_dbus_python:
            cnfg.no_dbus_python = True

        if args.dev_keymapper:
            cnfg.use_dev_keymapper = True
            if isinstance(args.dev_keymapper, str):
                cnfg.keymapper_cust_branch = args.dev_keymapper

        if args.fancy_pants:
            cnfg.fancy_pants = True

        run_install_sequence(cnfg)
        safe_shutdown(0)    # redundant, but that's OK

    elif args.command == 'list-distros':
        print(
            f'Index of distro IDs known to the Toshy installer:\n'
            f'\n(These can be tried with the "--override-distro" flag on unknown variants.)\n'
            f'\n{get_supported_distro_ids_idx()}\n'
            f'\n Total supported package managers:      {get_supported_pkg_managers_cnt()}'
            f'\n Total supported basic distro types:    {get_supported_distro_types_cnt()}'
            f'\n Total supported popular distro IDs:    {get_supported_distro_ids_cnt()} *'
            f'\n'
            f'\n * Number of supported variants of base distros is higher than IDs.'
            f'\n   Many variants still use the same distro ID as their base distro.'
        )
        safe_shutdown(0)

    elif args.command == 'show-env':
        get_environment_info()
        safe_shutdown(0)

    elif args.command == 'apply-tweaks':
        if args.fancy_pants:
            cnfg.fancy_pants = True
        get_environment_info()
        apply_desktop_tweaks()
        if cnfg.should_reboot:
            lb = cnfg.sep_char * 2      # shorter variable name for left border chars
            show_reboot_prompt()
            print(f'{lb}  Tweaks application complete. Report issues on the GitHub repo.')
            print(f'{lb}  https://github.com/RedBearAK/toshy/issues/')
            print(f'{lb}  >>  ALERT: Something odd happened. You should probably reboot.')
            print(cnfg.separator)
            print(cnfg.separator)
            print()
        safe_shutdown(0)

    elif args.command == 'remove-tweaks':
        get_environment_info()
        remove_desktop_tweaks()
        safe_shutdown(0)

    elif args.command == 'install-font':
        print(f'\n§  Installing coding/terminal font...\n{cnfg.separator}')
        install_coding_font()
        show_task_completed_msg()
        safe_shutdown(0)

    elif args.command == 'uninstall':
        uninstall_toshy()
        safe_shutdown(0)


if __name__ == '__main__':

    print()   # blank line in terminal to start things off

    # create the configuration settings class instance
    cnfg                        = InstallerSettings()

    # create the native package installer class instance
    native_pkg_installer        = NativePackageInstaller()

    # main() will parse the CLI arguments and dispatch the install sequence if appropriate
    main()
