#!/usr/bin/env python3
__version__ = '20260202'

import os
import re
import time
import shutil
import subprocess

from toshy_common import logger
from toshy_common.logger import *



logger.VERBOSE = True
logger.FLUSH = True



#############################  ENVIRONMENT  ##############################
###                                                                    ###
###                                                                    ###
###      ███████ ███    ██ ██    ██ ██ ██████   ██████  ███    ██      ###
###      ██      ████   ██ ██    ██ ██ ██   ██ ██    ██ ████   ██      ###
###      █████   ██ ██  ██ ██    ██ ██ ██████  ██    ██ ██ ██  ██      ###
###      ██      ██  ██ ██  ██  ██  ██ ██   ██ ██    ██ ██  ██ ██      ###
###      ███████ ██   ████   ████   ██ ██   ██  ██████  ██   ████      ###
###                                                                    ###
###                                                                    ###
##########################################################################
# Set up some useful environment variables


class EnvironmentInfo:
    def __init__(self):
        self.DISTRO_ID                      = None
        self.DISTRO_VER                     = None
        self.VARIANT_ID                     = None
        self.SESSION_TYPE                   = None
        self.DESKTOP_ENV                    = None
        self.DE_MAJ_VER                     = None
        self.WINDOW_MGR                     = None
        # self.WDW_MGR_VER                    = None        # Just in case we need it later

        # Split parts version information
        self.distro_mjr_ver                 = None
        self.distro_mnr_ver                 = None
        # self.de_major_ver                   = None        # Just in case we need it later
        # self.de_minor_ver                   = None        # Just in case we need it later

        self.env_info_dct: "dict[str, str]"   = {}
        self.release_files: "dict[str, str]"  = self.read_release_files()

    def get_env_info(self):
        """Primary method to get complete environment info"""

        # Call methods to harvest environment info and populate the instance variables.
        # As of 2024-09-04 there are seven different bits of primary info to generate.
        self._get_distro_id()
        self._get_distro_version()
        self._get_variant_id()
        self._get_session_type()
        self._get_desktop_environment()
        self._get_desktop_env_version()
        self._get_window_manager()
        # self.get_window_manager_version()                 # Just in case we need it later

        # Collect all info into a dictionary
        self.env_info_dct = {
            'DISTRO_ID':        self.DISTRO_ID,
            'DISTRO_VER':       self.DISTRO_VER,
            'VARIANT_ID':       self.VARIANT_ID,
            'SESSION_TYPE':     self.SESSION_TYPE,
            'DESKTOP_ENV':      self.DESKTOP_ENV,
            'DE_MAJ_VER':       self.DE_MAJ_VER,
            'WINDOW_MGR':       self.WINDOW_MGR,
            # 'WDW_MGR_VER':      self.WDW_MGR_VER,         # Just in case we need it later
        }

        # Add split parts version info
        self.env_info_dct.update({
            'distro_mjr_ver':   self.distro_mjr_ver,
            'distro_mnr_ver':   self.distro_mnr_ver,
            # 'de_major_ver':     self.de_major_ver,        # Just in case we need it later
            # 'de_minor_ver':     self.de_minor_ver,        # Just in case we need it later
        })

        return self.env_info_dct

    def read_release_files(self) -> "dict[str, str]":
        paths = [
            '/etc/os-release', '/etc/lsb-release', '/etc/arch-release'
        ]
        contents = {}
        for path in paths:
            if os.path.isfile(path):
                with open(path, 'r', encoding='UTF-8') as file:
                    contents[path] = file.read().splitlines()
        return contents

    def is_process_running(self, process_name):
        """
        Utility function to check if a process with a specific name is running.
        For names >15 chars, uses pgrep -f with careful pattern matching to avoid false positives.

        On NixOS, binaries are wrapped (e.g., gnome-shell → .gnome-shell-wrapped),
        and process names are truncated to 15 chars by the kernel (.gnome-shell-wr).
        This function handles both standard and NixOS wrapped process names using
        exact matching to avoid false positives.
        """
        KERNEL_COMM_LEN = 15  # Linux kernel TASK_COMM_LEN is 16, but includes null terminator
        use_pgrep_i = True

        distros_without_pgrep_i = [
            # Tuple format is (distro_id, major_version)
            ('centos', '7'),    # CentOS 7.x pgrep doesn't support -i flag
            # ('rhel', '7'),    # Add other distros as needed
        ]

        for distro_tup in distros_without_pgrep_i:
            if distro_tup == (self.DISTRO_ID, self.distro_mjr_ver):
                use_pgrep_i = False
                break

        def _get_nixos_wrapped_name(name):
            """
            Generate the NixOS-wrapped process name as it would appear in the kernel's
            process table (truncated to 15 characters).

            NixOS uses wrapProgram which creates: .{basename}-wrapped
            The kernel then truncates to TASK_COMM_LEN (15 chars).

            Args:
                process_name: Original process name (e.g., 'gnome-shell')

            Returns:
                The wrapped name truncated to 15 chars (e.g., '.gnome-shell-wr')
            """
            wrapped = f'.{name}-wrapped'
            return wrapped[:KERNEL_COMM_LEN]

        def _build_pgrep_cmd(name, use_full_match=False):
            """Build pgrep command with appropriate flags."""
            if use_full_match:
                # For long names, use -f with careful pattern matching
                pattern = f'(/|^){name}($| )'
                return ['pgrep', '-f', pattern]
            # Standard exact match for short names
            cmd = ['pgrep', '-x']
            if use_pgrep_i:
                cmd.append('-i')
            cmd.append(name)
            return cmd

        def _run_pgrep(cmd):
            """Execute pgrep command and return True if process found."""
            try:
                result = subprocess.check_output(cmd)
                return bool(result.strip())
            except subprocess.CalledProcessError:
                return False

        if len(process_name) <= KERNEL_COMM_LEN:
            # Standard exact match for short names
            cmd = _build_pgrep_cmd(process_name)
            if _run_pgrep(cmd):
                return True

            # On NixOS, try the wrapped binary pattern with exact matching
            if self.DISTRO_ID == 'nixos':
                wrapped_name = _get_nixos_wrapped_name(process_name)
                cmd = _build_pgrep_cmd(wrapped_name)
                if _run_pgrep(cmd):
                    return True

            return False

        # For long names (>15 chars), use -f with careful pattern matching
        cmd = _build_pgrep_cmd(process_name, use_full_match=True)
        return _run_pgrep(cmd)


####################################################################################################
##                                                                                                ##
##                ██████  ██ ███████ ████████ ██████   ██████      ██ ██████                      ##
##                ██   ██ ██ ██         ██    ██   ██ ██    ██     ██ ██   ██                     ##
##                ██   ██ ██ ███████    ██    ██████  ██    ██     ██ ██   ██                     ##
##                ██   ██ ██      ██    ██    ██   ██ ██    ██     ██ ██   ██                     ##
##                ██████  ██ ███████    ██    ██   ██  ██████      ██ ██████                      ##
##                                                                                                ##
####################################################################################################

    def _get_distro_id(self):
        """logic to set self.DISTRO_ID"""
        _distro_id          = ""

        if _distro_id == "" and self.release_files['/etc/os-release']:
            for prefix in ['ID=', 'NAME=', 'PRETTY_NAME=']:
                for line in self.release_files['/etc/os-release']:
                    if line.startswith(prefix):
                        _distro_id = line.split('=')[1].strip().strip('"')
                        break
                if _distro_id != "":
                    break

        if _distro_id == "" and self.release_files['/etc/lsb-release']:
            for prefix in ['DISTRIB_ID=', 'DISTRIB_DESCRIPTION=']:
                for line in self.release_files['/etc/lsb-release']:
                    if line.startswith(prefix):
                        _distro_id = line.split('=')[1].strip().strip('"')
                        break
                if _distro_id != "":
                    break

        if _distro_id == "" and self.release_files['/etc/arch-release']:
            _distro_id = 'arch'

        distro_names = {            # simplify distro names to an ID, if necessary
            'Debian.*':             'debian',
            # 'elementary':           'eos',
            'Fedora.*':             'fedora',
            'LMDE.*':               'lmde',
            'Manjaro':              'manjaro',
            'KDE.*Neon':            'neon',
            'Linux.*Mint':          'mint',
            'openSUSE.*Tumbleweed': 'opensuse-tumbleweed',
            'Peppermint.*':         'peppermint',
            'Pop!_OS':              'pop',
            'Red.*Hat.*':           'rhel',
            'Rocky.*':              'rocky',
            'Ubuntu':               'ubuntu',
            'Ultramarine.*Linux':   'ultramarine',
            'Zorin.*':              'zorin',
        }

        # if the regex string from dict key is in the distro name name retrieved, 
        # replace with corresponding simplified dict value for simpler matching
        for k, v in distro_names.items():
            # debug(f'{k = :<10} {v = :<10}')
            if re.search(k, _distro_id, re.I):
                self.DISTRO_ID = v
                break

        # If distro name not found in list, just show original name
        if not self.DISTRO_ID:
            self.DISTRO_ID = _distro_id

        # filter distro name to lower case if string (not `None`)
        if isinstance(self.DISTRO_ID, str):
            self.DISTRO_ID = self.DISTRO_ID.casefold()

####################################################################################################
##                                                                                                ##
##           ██████  ██ ███████ ████████ ██████   ██████      ██    ██ ███████ ██████             ##
##           ██   ██ ██ ██         ██    ██   ██ ██    ██     ██    ██ ██      ██   ██            ##
##           ██   ██ ██ ███████    ██    ██████  ██    ██     ██    ██ █████   ██████             ##
##           ██   ██ ██      ██    ██    ██   ██ ██    ██      ██  ██  ██      ██   ██            ##
##           ██████  ██ ███████    ██    ██   ██  ██████        ████   ███████ ██   ██            ##
##                                                                                                ##
####################################################################################################

    def _get_distro_version(self):
        """logic to set self.DISTRO_VER"""

        if self.release_files['/etc/os-release']:
            for line in self.release_files['/etc/os-release']:
                line: str
                if line.startswith('VERSION_ID='):
                    self.DISTRO_VER = line.split('=')[1].strip().strip('"')
                    break
        elif self.release_files['/etc/lsb-release']:
            for line in self.release_files['/etc/lsb-release']:
                line: str
                if line.startswith('DISTRIB_RELEASE='):
                    self.DISTRO_VER = line.split('=')[1].strip().strip('"')
                    break

        arch_distros = [
            'arch',
            'arcolinux',
            'endeavouros',
            'garuda',
            'manjaro',
        ]

        if not self.DISTRO_VER:
            if self.DISTRO_ID in arch_distros:
                self.DISTRO_VER = 'arch_btw'
            else:
                self.DISTRO_VER = 'notfound'

        # Parse out major and minor distro version
        distro_ver_parts        = self.DISTRO_VER.split('.') if self.DISTRO_VER else []
        self.distro_mjr_ver     = distro_ver_parts[0] if distro_ver_parts else 'NO_VER'
        self.distro_mnr_ver     = distro_ver_parts[1] if len(distro_ver_parts) > 1 else 'no_mnr_ver'


####################################################################################################
##                                                                                                ##
##             ██    ██  █████  ██████  ██  █████  ███    ██ ████████     ██ ██████               ##
##             ██    ██ ██   ██ ██   ██ ██ ██   ██ ████   ██    ██        ██ ██   ██              ##
##             ██    ██ ███████ ██████  ██ ███████ ██ ██  ██    ██        ██ ██   ██              ##
##              ██  ██  ██   ██ ██   ██ ██ ██   ██ ██  ██ ██    ██        ██ ██   ██              ##
##               ████   ██   ██ ██   ██ ██ ██   ██ ██   ████    ██        ██ ██████               ##
##                                                                                                ##
####################################################################################################

    def _get_variant_id(self):
        """logic to set self.VARIANT_ID, if variant info available"""

        if self.release_files['/etc/os-release']:
            for line in self.release_files['/etc/os-release']:
                line: str
                if line.startswith('VARIANT_ID='):
                    self.VARIANT_ID = line.split('=')[1].strip().strip('"')
                    break
        elif self.release_files['/etc/lsb-release']:
            for line in self.release_files['/etc/lsb-release']:
                line: str
                if line.startswith('DISTRIB_DESCRIPTION='):
                    self.VARIANT_ID = line.split('=')[1].strip().strip('"')
                    break

        if not self.VARIANT_ID:
            self.VARIANT_ID = 'notfound'

####################################################################################################
##                                                                                                ##
##  ███████ ███████ ███████ ███████ ██  ██████  ███    ██     ████████ ██    ██ ██████  ███████   ##
##  ██      ██      ██      ██      ██ ██    ██ ████   ██        ██     ██  ██  ██   ██ ██        ##
##  ███████ █████   ███████ ███████ ██ ██    ██ ██ ██  ██        ██      ████   ██████  █████     ##
##       ██ ██           ██      ██ ██ ██    ██ ██  ██ ██        ██       ██    ██      ██        ##
##  ███████ ███████ ███████ ███████ ██  ██████  ██   ████        ██       ██    ██      ███████   ##
##                                                                                                ##
####################################################################################################

    def _get_session_type(self):
        """logic to set self.SESSION_TYPE"""
        valid_session_types = ['x11', 'wayland']
        self.SESSION_TYPE   = os.environ.get("XDG_SESSION_TYPE") or None

        if not self.SESSION_TYPE:  # Why isn't XDG_SESSION_TYPE set? This shouldn't happen.
            error(f'ENV: XDG_SESSION_TYPE should really be set. Not a graphical environment?')

        if self.SESSION_TYPE not in valid_session_types or self.SESSION_TYPE == 'tty':
            # This is seen sometimes in situations like starting a window manager
            # or desktop environment session from a TTY, without using a login
            # manager like GDM or SDDM. This is not good. Treat as error. 
            error(f"ENV: XDG_SESSION_TYPE is 'tty' for some reason. Why?")

            # We need to check in some other way whether we are in Wayland or X11
            # Usually for Wayland there will be: WAYLAND_DISPLAY=wayland-[number]
            wayland_display = os.environ.get('WAYLAND_DISPLAY')
            if wayland_display and wayland_display.startswith('wayland'):
                self.SESSION_TYPE = 'wayland'

            # If the Wayland display variable was not set or not 'wayland*', 
            # then check for the usual X11 display variable.
            elif os.environ.get('DISPLAY'):
                self.SESSION_TYPE = 'x11'

        if self.SESSION_TYPE not in valid_session_types:
            # Deal with archaic distros like antiX that fail to set XDG_SESSION_TYPE
            time.sleep(3)

            xorg_check_p1 = subprocess.Popen(['ps', 'ax'], stdout=subprocess.PIPE)
            xorg_check_p2 = subprocess.Popen(
                                        ['grep', '-i', '-c', 'xorg'], 
                                        stdin=xorg_check_p1.stdout, 
                                        stdout=subprocess.PIPE)
            xorg_check_p1.stdout.close()  # Allow p1 to receive a SIGPIPE if p2 exits.
            xorg_check_output = xorg_check_p2.communicate()[0]
            xorg_count = int(xorg_check_output.decode()) - 1

            if xorg_count:
                self.SESSION_TYPE = 'x11'

            wayland_check_p1 = subprocess.Popen(['ps', 'ax'], stdout=subprocess.PIPE)
            wayland_check_p2 = subprocess.Popen(
                                            ['grep', '-i', '-c', 'wayland'], 
                                            stdin=wayland_check_p1.stdout, 
                                            stdout=subprocess.PIPE)
            wayland_check_p1.stdout.close()  # Allow p1 to receive a SIGPIPE if p2 exits.
            wayland_check_output = wayland_check_p2.communicate()[0]
            wayland_count = int(wayland_check_output.decode()) - 1

            if wayland_count:
                self.SESSION_TYPE = 'wayland'

        if self.SESSION_TYPE is None:
            raise EnvironmentError(
                f'\n\nENV: Detecting session type failed.\n')

        if isinstance(self.SESSION_TYPE, str):
            self.SESSION_TYPE = self.SESSION_TYPE.casefold()

        if self.SESSION_TYPE not in valid_session_types:
            error(f'\n\nENV: Unknown session type: {self.SESSION_TYPE}.\n')

####################################################################################################
##                                                                                                ##
##    ██████  ███████ ███████ ██   ██ ████████  ██████  ██████      ███████ ███    ██ ██    ██    ##
##    ██   ██ ██      ██      ██  ██     ██    ██    ██ ██   ██     ██      ████   ██ ██    ██    ##
##    ██   ██ █████   ███████ █████      ██    ██    ██ ██████      █████   ██ ██  ██ ██    ██    ##
##    ██   ██ ██           ██ ██  ██     ██    ██    ██ ██          ██      ██  ██ ██  ██  ██     ##
##    ██████  ███████ ███████ ██   ██    ██     ██████  ██          ███████ ██   ████   ████      ##
##                                                                                                ##
####################################################################################################

    def _get_desktop_environment(self):
        """logic to set self.DESKTOP_ENV and self.DE_MAJ_VER"""
        _desktop_env        = ""

        _desktop_env = (
            os.environ.get("XDG_CURRENT_DESKTOP") or
            os.environ.get("XDG_SESSION_DESKTOP") or
            os.environ.get("DESKTOP_SESSION")
        )

        # If it's a colon-separated list in XDG_CURRENT_DESKTOP,
        # the first entry is the primary desktop environment
        if _desktop_env and ':' in _desktop_env:
            _desktop_env = _desktop_env.split(':')[0]

        # Check for Qtile if the environment variables were not set/empty
        if not _desktop_env and self.is_qtile_running():
            _desktop_env = 'qtile'

        if not _desktop_env:
            _desktop_env = None
            error("ERR: DE not found in XDG_SESSION_DESKTOP, XDG_CURRENT_DESKTOP or DESKTOP_SESSION.")
            error("ERR: Config file may not be able to adapt automatically to Desktop Environment.")

        # Protect '.lower()' method from NoneType error
        if _desktop_env and 'unity' in _desktop_env.lower():
            self.DESKTOP_ENV = 'unity'

        # Produce a simplified desktop environment name
        desktop_env_names = {
            'AnduinOS':                 'gnome',
            'Budgie':                   'budgie',
            'Cinnamon':                 'cinnamon',
            'COSMIC':                   'cosmic',
            'Cutefish':                 'cutefish',
            'DDE':                      'dde',
            'Deepin':                   'deepin',
            'default':                  'trinity',      # strange thing encountered on Q4OS
            'Enlightenment':            'enlightenment',
            'GNOME':                    'gnome',
            'Hyprland':                 'hyprland',
            'i3':                       'i3',
            'i3wm':                     'i3',
            'IceWM':                    'icewm',
            'KDE':                      'kde',
            'LXDE':                     'lxde',
            'LXQt':                     'lxqt',
            'MATE':                     'mate',
            'Miracle-WM':               'miracle-wm',
            'miracle-wm:mir':           'miracle-wm',
            'Miriway':                  'miriway',
            'Niri':                     'niri',
            'Pantheon':                 'pantheon',
            'Plasma':                   'kde',
            'pop':                      'pop',      # System76 changed DE name on 22.04 LTS to 'pop'?
            'qtile:wlroots':            'qtile',
            'Qtile':                    'qtile',
            'qtilewaylan':              'qtile',    # actual value in real life (typo in Qtile code?)
            'qtilewayland':             'qtile',    # might appear if they fix the typo
            'qtilex11':                 'qtile',
            'Sway':                     'sway',
            'SwayWM':                   'sway',
            'Trinity':                  'trinity',
            'UKUI':                     'ukui',     # Ubuntu Kylin desktop shell
            'Unity':                    'unity',    # keep above "Ubuntu" to always catch 'unity' first
            'Ubuntu':                   'gnome',    # "Ubuntu" in XDG_CURRENT_DESKTOP, but DE is GNOME
            'Wayfire':                  'wayfire',
            'WindowMaker':              'wmaker',
            'Xfce':                     'xfce',
            'Zorin':                    'gnome',    # Hopefully Zorin OS will only call GNOME "zorin"
        }

        if not self.DESKTOP_ENV:
            for k, v in desktop_env_names.items():
                # debug(f'{k = :<10} {v = :<10}')
                if _desktop_env is None: break  # watch out for NoneType here
                if re.search(k, _desktop_env, re.I):
                    self.DESKTOP_ENV = v
                if self.DESKTOP_ENV:
                    break

        # say DE should be added to list only if it it isn't None
        if not self.DESKTOP_ENV and _desktop_env is not None:
            error(f'DE or window manager not in desktop_env_names list! Should fix this.'
                    f'\n\t{_desktop_env}')
            self.DESKTOP_ENV = _desktop_env

        # do this only if DESKTOP_ENV is still None after the above step
        if not self.DESKTOP_ENV:
            # Doublecheck the desktop environment by checking for identifiable running processes
            def check_process(names, desktop_env):
                # nonlocal DESKTOP_ENV
                for name in names:
                    command = f"pgrep -x {name}"
                    try:
                        subprocess.check_output(command, shell=True)
                        if self.DESKTOP_ENV != desktop_env:
                            error(  f"Desktop may be misidentified: '{self.DESKTOP_ENV}'\n"
                                    f"'{desktop_env}' was detected and will be used instead.")
                            self.DESKTOP_ENV = desktop_env
                        break  # Stop checking if any of the processes are found
                    except subprocess.CalledProcessError:
                        pass

            processes = {
                'kde':          ['plasmashell', 'kwin_ft', 'kwin_wayland', 'kwin_x11', 'kwin'],
                'gnome':        ['gnome-shell'],
                'miracle-wm':   ['miracle-wm'],
                'sway':         ['sway', 'swaywm'],
                'hyprland':     ['hyprland'],
            }

            for desktop_env, process_names in processes.items():
                if check_process(process_names, desktop_env):
                    break   # Stop this loop when some process is found by exact match

    def is_qtile_running(self):
        """Utility function to detect Qtile if the usual environment vars are not set/empty"""
        xdg_cache_home      = os.environ.get('XDG_CACHE_HOME', os.path.expanduser('~/.cache'))
        display             = os.environ.get('DISPLAY')
        wayland_display     = os.environ.get('WAYLAND_DISPLAY')
        desktop_session     = os.environ.get('DESKTOP_SESSION')

        socket_paths = []
        
        if display:
            socket_paths.append(os.path.join(xdg_cache_home, f'qtile/qtilesocket.{display}'))
        
        if wayland_display:
            socket_paths.append(os.path.join(xdg_cache_home, f'qtile/qtilesocket.{wayland_display}'))

        if desktop_session and 'qtile' in desktop_session:
            return True

        for socket_path in socket_paths:
            if os.path.exists(socket_path):
                return True

        return False

####################################################################################################
##                                                                                                ##
##          ██████  ███████     ██    ██ ███████ ██████  ███████ ██  ██████  ███    ██            ##
##          ██   ██ ██          ██    ██ ██      ██   ██ ██      ██ ██    ██ ████   ██            ##
##          ██   ██ █████       ██    ██ █████   ██████  ███████ ██ ██    ██ ██ ██  ██            ##
##          ██   ██ ██           ██  ██  ██      ██   ██      ██ ██ ██    ██ ██  ██ ██            ##
##          ██████  ███████       ████   ███████ ██   ██ ███████ ██  ██████  ██   ████            ##
##                                                                                                ##
####################################################################################################

    def _get_desktop_env_version(self):
        """logic to set self.DE_MAJ_VER"""
        # Desktop environments for which we need the major version:
        # - GNOME
        # - KDE Plasma

        if self.DESKTOP_ENV == 'gnome':
            self.DE_MAJ_VER = self.get_gnome_version()
        elif self.DESKTOP_ENV == 'kde':
            self.DE_MAJ_VER = self.get_kde_version()
        elif self.DESKTOP_ENV == 'lxqt':
            self.DE_MAJ_VER = self.get_lxqt_version()

        if not self.DE_MAJ_VER:
            self.DE_MAJ_VER = 'no_logic_for_DE'

    def get_gnome_version(self):
            try:
                # Run the gnome-shell command to get the version
                output = subprocess.check_output(["gnome-shell", "--version"]).decode().strip()
                # Use regular expression to extract the major version number
                match = re.search(r"GNOME Shell (\d+)\.", output)
                if match:
                    return match.group(1)
            except subprocess.CalledProcessError as proc_err:
                error(f"Error obtaining GNOME version: {proc_err}")
                return 'gnome_ver_check_err'

    def get_kde_version(self):
        KDE_session_ver = os.environ.get('KDE_SESSION_VERSION')
        if KDE_session_ver is None:
            error(f"KDE_SESSION_VERSION was not set.")
        elif KDE_session_ver in ['3', '4', '5', '6']:
            return KDE_session_ver
        else:
            error(f"KDE_SESSION_VERSION contains unrecognized value: '{KDE_session_ver}'")
        if shutil.which("kpackagetool6"): # or shutil.which("kwriteconfig6"):
            return '6'
        elif shutil.which("kpackagetool5"): # or shutil.which("kwriteconfig5"):
            return '5'
        elif shutil.which("kpackagetool"): # or shutil.which("kwriteconfig"): 
            # In KDE 4, these tools don't have a version number in their name
            # Additional check for KDE 4 versioning can be done here if necessary
            return '4'
        # no 'kpackagetool' command in KDE 3?
        return 'kde_ver_check_err'

    def get_lxqt_version(self):
        try:
            output = subprocess.check_output(["lxqt-session", "--version"]).decode().strip()
            match = re.search(r"lxqt-session (\d+\.\d+\.\d+)", output)
            if match:
                major_version = match.group(1).split('.')[0]
                return major_version
        except subprocess.CalledProcessError:
            return 'lxqt_ver_check_err'

####################################################################################################
##                                                                                                ##
##       ██     ██ ██ ███    ██ ██████   ██████  ██     ██     ███    ███  ██████  ██████         ##
##       ██     ██ ██ ████   ██ ██   ██ ██    ██ ██     ██     ████  ████ ██       ██   ██        ##
##       ██  █  ██ ██ ██ ██  ██ ██   ██ ██    ██ ██  █  ██     ██ ████ ██ ██   ███ ██████         ##
##       ██ ███ ██ ██ ██  ██ ██ ██   ██ ██    ██ ██ ███ ██     ██  ██  ██ ██    ██ ██   ██        ##
##        ███ ███  ██ ██   ████ ██████   ██████   ███ ███      ██      ██  ██████  ██   ██        ##
##                                                                                                ##
####################################################################################################

    def _get_window_manager(self):
        """
        logic to set self.WINDOW_MGR
        Useful in environments like LXQt that can have various window managers.
        """

        # Common "desktop environments" mapped to likely actual "window manager" process names
        de_wm_map = {

            # Older KDE may just use 'kwin' process name
            'kde': [
                'kwin_wayland',
                'kwin_x11', 
                'kwin', 
            ],

            # Older GNOME may have 'mutter' integrated into 'gnome-shell' process
            # On NixOS, 'mutter' observed as window manager process in Wayland session, 2026-02-02
            'gnome': [
                'mutter',
                'gnome-shell',
            ],

            # LXQt often uses OpenBox, but can use a number of different WMs in X11 or Wayland
            'lxqt': [
                # X11/Xorg window manager
                'openbox',
                # Wayland compositors
                'labwc',
                'sway',
                'hyprland',
                'kwin_wayland',
                'wayfire',
                'river',
                'niri',
                'miriway',
                'miriway-shell',    # (actual process name for miriway)
            ],

            # Deepin Desktop Environment
            'dde': [
                'deepin-kwin_wayland',  # This might never exist (too long? over 15 characters)
                'deepin-kwin_x11',
                'deepin-kwin',
            ],

            'awesome':          ['awesome'],
            'budgie':           ['budgie-wm'],
            'cinnamon':         ['cinnamon'],
            'cosmic':           ['cosmic-comp'],
            'cutefish':         ['kwin_x11'],
            'dwm':              ['dwm'],
            'enlightenment':    ['enlightenment'],
            'hyprland':         ['Hyprland'],
            'i3':               ['i3'],
            'i3-gaps':          ['i3'],
            'icewm':            ['icewm'],
            'labwc':            ['labwc'],
            'lxde':             ['openbox'],
            'mate':             ['marco'],
            'miracle-wm':       ['miracle-wm'],
            'openbox':          ['openbox'],
            'pantheon':         ['gala'],
            'pop':              ['gnome-shell'],
            'qtile':            ['qtile'],
            'river':            ['river'],
            'sway':             ['sway'],
            'trinity':          ['twin'],
            'ukui':             ['ukwm'],
            'unity':            ['compiz'],
            'wayfire':          ['wayfire'],
            'wmaker':           ['wmaker'],
            'xfce':             ['xfwm4'],

        }

        # First try to limit search for window managers associated with desktop environment
        if self.DESKTOP_ENV and self.DESKTOP_ENV in de_wm_map:
            possible_wms = de_wm_map[self.DESKTOP_ENV]
            for wm in possible_wms:
                if self.is_process_running(wm):
                    self.WINDOW_MGR = wm
                    return

        if self.DESKTOP_ENV and self.DESKTOP_ENV == 'lxqt' and not self.WINDOW_MGR:
            self.get_lxqt_window_manager()
            if self.WINDOW_MGR:
                return

        # Iterate through whole dictionary if desktop environment not found in de_wm_map
        for DE, process_names in de_wm_map.items():
            if not isinstance(process_names, list):
                process_names = [process_names]  # Ensure we can iterate
            for process_name in process_names:
                if self.is_process_running(process_name):
                    self.WINDOW_MGR = process_name
                    return

        # If nothing found, set a default value
        if not self.WINDOW_MGR:
            self.WINDOW_MGR = 'WM_unidentified_by_logic'

    def get_lxqt_window_manager(self):
        """Further steps to identify possible LXQt window manager"""
        # If DE is LXQt and WM still not found after above search, try checking its config file:
        # cat ~/.config/lxqt/session.conf | grep WindowManager
        config_path = os.path.expanduser('~/.config/lxqt/session.conf')
        try:
            with open(config_path, 'r') as config_file:
                for line in config_file:
                    if line.startswith('window_manager=') or line.startswith('compositor='):
                        # Typically the line would be like "window_manager=openbox\n"
                        wm_name = os.path.basename(line.strip().split('=')[1])
                        if wm_name == 'miriway' and self.is_process_running('miriway-shell'):
                            self.WINDOW_MGR = 'miriway-shell'
                            return
                        elif self.is_process_running(wm_name):
                            self.WINDOW_MGR = wm_name
                            return
                        else:
                            # Fallback to checking other known WMs in case config is outdated
                            break
        except FileNotFoundError:
            # Handle cases where the config file does not exist
            print(f"Could not find LXQt config file at: {config_path}")

####################################################################################################
##                                                                                                ##
##    ██     ██ ██████  ██     ██     ███    ███  ██████  ██████      ██    ██ ███████ ██████     ##
##    ██     ██ ██   ██ ██     ██     ████  ████ ██       ██   ██     ██    ██ ██      ██   ██    ##
##    ██  █  ██ ██   ██ ██  █  ██     ██ ████ ██ ██   ███ ██████      ██    ██ █████   ██████     ##
##    ██ ███ ██ ██   ██ ██ ███ ██     ██  ██  ██ ██    ██ ██   ██      ██  ██  ██      ██   ██    ##
##     ███ ███  ██████   ███ ███      ██      ██  ██████  ██   ██       ████   ███████ ██   ██    ##
##                                                                                                ##
####################################################################################################

    def get_window_manager_version(self):
        """Login to set self.WDW_MGR_VER, if ever necessary"""
        if not self.WDW_MGR_VER:
            self.WDW_MGR_VER = 'no_logic_for_wdw_mgr'


if __name__ == "__main__":
    env_info_getter = EnvironmentInfo()
    _env_info = env_info_getter.get_env_info()
    print('')
    debug(  f'Toshy env_context module sees this environment:'
            f'\n\t\t DISTRO_ID       = \'{_env_info["DISTRO_ID"]}\''
            f'\n\t\t DISTRO_VER      = \'{_env_info["DISTRO_VER"]}\''
            f'\n\t\t VARIANT_ID      = \'{_env_info["VARIANT_ID"]}\''
            f'\n\t\t SESSION_TYPE    = \'{_env_info["SESSION_TYPE"]}\''
            f'\n\t\t DESKTOP_ENV     = \'{_env_info["DESKTOP_ENV"]}\''
            f'\n\t\t DE_MAJ_VER      = \'{_env_info["DE_MAJ_VER"]}\''
            f'\n\t\t WINDOW_MGR      = \'{_env_info["WINDOW_MGR"]}\''
            # f'\n\t\t WDW_MGR_VER     = \'{_env_info["WDW_MGR_VER"]}\''
            f'\n', ctx="EV")
