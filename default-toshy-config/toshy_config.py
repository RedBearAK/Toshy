# -*- coding: utf-8 -*-
__version__ = '20260101'
###############################################################################
############################   Welcome to Toshy!   ############################
###
###  This is a highly customized fork of the config file that powers
###  Kinto.sh, by Ben Reaves
###      (https://kinto.sh)
###
###  All credit for the basis of this config goes to Ben Reaves.
###      (https://github.com/rbreaves/kinto/)
###
###  Much assistance was provided by Josh Goebel, the developer of the
###  `xkeysnail` fork `keyszer`, which is now forked into `xwaykeyz` to
###  provide support for some (most?) Wayland environments.
###      (http://github.com/joshgoebel/keyszer)
###
###############################################################################

import re
import os
import sys
import time
import shutil
import asyncio
import inspect
import subprocess

from subprocess import DEVNULL
from typing import Any, Callable, Optional, Union, List, Dict, Tuple

from xwaykeyz.config_api import *
from xwaykeyz.lib.key_context import KeyContext
from xwaykeyz.lib.logger import debug, error
from xwaykeyz.models.modifier import Modifier


###################################################################################################
###  SLICE_MARK_START: keymapper_api  ###  EDITS OUTSIDE THESE MARKS WILL BE LOST ON UPGRADE

# Keymapper-specific config settings - REMOVE OR SET TO DEFAULTS FOR DISTRIBUTION
dump_diagnostics_key(Key.F15)   # default key: F15
emergency_eject_key(Key.F16)    # default key: F16

timeouts(
    multipurpose        = 1,        # default: 1 sec
    suspend             = 1,        # default: 1 sec, try 0.1 sec for touchpads/trackpads
)

# Delays often needed for Wayland and/or virtual machines or slow systems
throttle_delays(
    key_pre_delay_ms    = 8,      # default: 0 ms, range: 0-150 ms, suggested: 1-50 ms
    key_post_delay_ms   = 12,      # default: 0 ms, range: 0-150 ms, suggested: 1-100 ms
)

devices_api(
    # Only the specified devices will be "grabbed" and watched for during
    # device connections/disconnections.
    only_devices = [
        # 'Example Disconnected Keyboard',
        # 'Example Connected Keyboard',
    ]
)

###########################################################
# Use this ONLY if you want near zero CPU usage for held,
# repeating keys. This will bypass the new repeating keys
# cache mechanism that reduces CPU usage for repeats to
# very low levels (but not zero), in xwaykeyz>=1.11.0.
#
# This override will BREAK shortcuts like Emacs-style
# cursor movement, which will not be able to repeat.
#
# A warning will appear in verbose debug logging.
###########################################################
# ignore_repeating_keys(True)


###  SLICE_MARK_END: keymapper_api  ###  EDITS OUTSIDE THESE MARKS WILL BE LOST ON UPGRADE
###################################################################################################



###################################################################################################
# How to add an alias to an existing modifier definition (VERY EXPERIMENTAL!!!)
# Some of these are disabled because I'm not sure they would apply correctly
# to all of the different keyboard types. But virtualized Command and Left Ctrl,
# Left Option aliases should make sense for all keyboard types.
# WARNING: It is not advisable to start using these in actual input
# combos in keymaps. These aliases may be removed in the future.
try:
    ###########################################################################
    # # Virtualized (left) Control key (in Terminals)

    LC_aliases: List[str]           = Modifier.L_CONTROL.aliases
    LC_keys: List[Key]              = Modifier.L_CONTROL.keys
    # use slice assignment instead of insert()
    LC_aliases[:0]                  = ['VLCtrl', 'VirtLCtrl']
    # debug(f"{LC_aliases             = }")
    # debug(f"{LC_keys                = }")

    ###########################################################################
    # # Virtualized (left/right) Control keys (in GUI apps)

    # L_META_aliases: List[str]       = Modifier.L_META.aliases
    # L_META_keys: List[Key]          = Modifier.L_META.keys
    # # use slice assignment instead of insert()
    # L_META_aliases[:0]              = ['VLCtrl', 'Virt_LCtrl']
    # debug(f"{L_META_aliases         = }")
    # debug(f"{L_META_keys            = }")

    # R_META_aliases: List[str]       = Modifier.R_META.aliases
    # R_META_keys: List[Key]          = Modifier.R_META.keys
    # # use slice assignment instead of insert()
    # R_META_aliases[:0]              = ['VRCtrl', 'Virt_RCtrl']
    # debug(f"{R_META_aliases         = }")
    # debug(f"{R_META_keys            = }")

    ###########################################################################
    # Virtualized Option/Alt keys (left/right)

    LA_aliases: List[str]           = Modifier.L_ALT.aliases
    LA_keys: List[Key]              = Modifier.L_ALT.keys
    # use slice assignment instead of insert()
    LA_aliases[:0]                  = ['VLOpt', 'VirtLOpt']
    # debug(f"{LA_aliases             = }")
    # debug(f"{LA_keys                = }")

    # RA_aliases: List[str]       = Modifier.R_ALT.aliases
    # RA_keys: List[Key]          = Modifier.R_ALT.keys
    # # use slice assignment instead of insert()
    # RA_aliases[:0]              = ['VROpt', 'VirtROpt']
    # debug(f"{RA_aliases         = }")
    # debug(f"{RA_keys            = }")

    ###########################################################################
    # Virtualized Command key (all keyboard types)

    R_CONTROL_aliases: List[str]    = Modifier.R_CONTROL.aliases
    R_CONTROL_keys: List[Key]       = Modifier.R_CONTROL.keys
    # use slice assignment instead of insert()
    R_CONTROL_aliases[:0]           = ['VCmd', 'VirtCmd']
    # debug(f"{R_CONTROL_aliases      = }")
    # debug(f"{R_CONTROL_keys         = }")

except AttributeError as e:
    error(f"Problem adding alias to modifier:\n\t{e}")
###################################################################################################



###################################################################################################
# Some important setup work necessary to make custom preferences,
# notifications and Synergy log monitoring work.
home_dir = os.path.expanduser('~')
icons_dir = os.path.join(home_dir, '.local', 'share', 'icons')

# get the path of this file (not the main module loading it)
config_globals = inspect.stack()[1][0].f_globals
current_folder_path = os.path.dirname(os.path.abspath(config_globals["__config__"]))
sys.path.insert(0, current_folder_path)

# Local imports after path has been set
from toshy_common.env_context import EnvironmentInfo
from toshy_common.machine_context import get_machine_id_hash
from toshy_common.notification_manager import NotificationManager
from toshy_common.settings_class import Settings

assets_path         = os.path.join(current_folder_path, 'assets')
icon_file_active    = os.path.join(assets_path, "toshy_app_icon_rainbow.svg")
icon_file_grayscale = os.path.join(assets_path, "toshy_app_icon_rainbow_inverse_grayscale.svg")
icon_file_inverse   = os.path.join(assets_path, "toshy_app_icon_rainbow_inverse.svg")

# Toshy config file
TOSHY_PART      = 'config'   # CUSTOMIZE TO SPECIFIC TOSHY COMPONENT! (gui, tray, config)
TOSHY_PART_NAME = 'Toshy Config file'
APP_VERSION     = __version__

# Settings object used to tweak preferences "live" between gui, tray and config.
cnfg = Settings(current_folder_path)
cnfg.watch_database()           # activate watchdog observer on the sqlite3 db file
cnfg.watch_shared_devices()     # Look for network KVM apps and watch logs (on server only)
# debug("")
debug(cnfg, ctx="CG")



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

###################################################################################################
###  SLICE_MARK_START: env_overrides  ###  EDITS OUTSIDE THESE MARKS WILL BE LOST ON UPGRADE

# MANUALLY set any environment information if the auto-identification isn't working:
OVERRIDE_DISTRO_ID              = None
OVERRIDE_DISTRO_VER             = None
OVERRIDE_VARIANT_ID             = None
OVERRIDE_SESSION_TYPE           = None
OVERRIDE_DESKTOP_ENV            = None
OVERRIDE_DE_MAJ_VER             = None
OVERRIDE_WINDOW_MGR             = None

wlroots_compositors             = [
    # Comma-separated list of Wayland desktop environments or window managers
    # that should try to use the 'wlroots' window context provider. Use the
    # 'WINDOW_MGR' name that appears when running `toshy-env`, or 'DESKTOP_ENV'
    # if the window manager name is not identified.
    # 'obscurewm',
    # 'unknown-wm',

]

###  SLICE_MARK_END: env_overrides  ###  EDITS OUTSIDE THESE MARKS WILL BE LOST ON UPGRADE
###################################################################################################

# Leave all of this alone! Don't try to override values here.
DISTRO_ID                       = None
DISTRO_VER                      = None
VARIANT_ID                      = None
SESSION_TYPE                    = None
DESKTOP_ENV                     = None
DE_MAJ_VER                      = None
WINDOW_MGR                      = None

env_ctxt_getter = EnvironmentInfo()
env_ctxt: Dict[str, str] = env_ctxt_getter.get_env_info()

DISTRO_ID       = locals().get('OVERRIDE_DISTRO_ID')    or env_ctxt.get('DISTRO_ID',    'keymissing')
DISTRO_VER      = locals().get('OVERRIDE_DISTRO_VER')   or env_ctxt.get('DISTRO_VER',   'keymissing')
VARIANT_ID      = locals().get('OVERRIDE_VARIANT_ID')   or env_ctxt.get('VARIANT_ID',   'keymissing')
SESSION_TYPE    = locals().get('OVERRIDE_SESSION_TYPE') or env_ctxt.get('SESSION_TYPE', 'keymissing')
DESKTOP_ENV     = locals().get('OVERRIDE_DESKTOP_ENV')  or env_ctxt.get('DESKTOP_ENV',  'keymissing')
DE_MAJ_VER      = locals().get('OVERRIDE_DE_MAJ_VER')   or env_ctxt.get('DE_MAJ_VER',   'keymissing')
WINDOW_MGR      = locals().get('OVERRIDE_WINDOW_MGR')   or env_ctxt.get('WINDOW_MGR',   'keymissing')

# debug("")
debug(  f'Toshy config sees this environment:'
        f'\n\t{DISTRO_ID        = }'
        f'\n\t{DISTRO_VER       = }'
        f'\n\t{VARIANT_ID       = }'
        f'\n\t{SESSION_TYPE     = }'
        f'\n\t{DESKTOP_ENV      = }'
        f'\n\t{DE_MAJ_VER       = }'
        f'\n\t{WINDOW_MGR       = }', ctx="CG")


# NOTE: List kind of stabilized, so moved all into keymapper wlroots window context method
# during the transition from using "desktop environment" to using "window manager".
known_wlroots_compositors = [
    # 'hyprland',
    # 'labwc',
    # 'miracle-wm',
    # 'miriway',
    # 'miriway-shell',    # actual process name for 'miriway' compositor?
    # 'niri',
    # 'qtile',
    # 'river',
    # 'sway',
    # 'wayfire',
]

# Make sure the 'wlroots_compositors' list variable exists before checking it.
# Older config files won't have it in the 'env_overrides' slice.
wlroots_compositors = locals().get('wlroots_compositors', [])

all_wlroots_compositors = known_wlroots_compositors + wlroots_compositors

# Direct the keymapper to try to use `wlroots` window context for
# all DEs/WMs in user list, if list is not empty.
if wlroots_compositors and WINDOW_MGR in wlroots_compositors:
    debug(f"Will use 'wlroots' context provider for '{WINDOW_MGR}' WM", ctx="CG")
    debug("File an issue on GitHub repo if this works for your WM.", ctx="CG")
    _wl_compositor = 'wlroots'
elif wlroots_compositors and DESKTOP_ENV in wlroots_compositors:
    debug(f"Will use 'wlroots' context provider for '{DESKTOP_ENV}' DE", ctx="CG")
    debug("File an issue on GitHub repo if this works for your DE.", ctx="CG")
    _wl_compositor = 'wlroots'
elif WINDOW_MGR in known_wlroots_compositors:
    debug(f"WM '{WINDOW_MGR}' is in known 'wlroots' compositor list.", ctx="CG")
    _wl_compositor = 'wlroots'
elif DESKTOP_ENV in known_wlroots_compositors:
    debug(f"DE '{DESKTOP_ENV}' is in known 'wlroots' compositor list.", ctx="CG")
    _wl_compositor = 'wlroots'
# elif (SESSION_TYPE, DESKTOP_ENV) == ('wayland', 'lxqt') and WINDOW_MGR == 'kwin_wayland':
#     # The Toshy KWin script must be installed in the LXQt/KWin environment for this to work!
#     debug(f"DE is LXQt, WM is '{WINDOW_MGR}', using 'kwin_wayland' window context method.", ctx="CG")
#     _desktop_env = 'kde'
# elif (SESSION_TYPE, DESKTOP_ENV) == ('wayland', 'lxqt') and WINDOW_MGR in all_wlroots_compositors:
#     debug(f"DE is LXQt, WM is '{WINDOW_MGR}', using 'wlroots' window context method.", ctx="CG")
#     _desktop_env = 'wlroots'
else:
    _wl_compositor = WINDOW_MGR

try:
    # Help the keymapper select the correct window context provider object
    environ_api(session_type = SESSION_TYPE, wl_compositor = _wl_compositor) # type: ignore
except NameError:
    error(f"The API function 'environ_api' is not defined yet. Wrong keymapper branch?")
    pass


# Global variable to store the local machine ID at runtime, for machine-specific keymaps.
# Allows syncing a single config file between different machines without overlapping the
# hardware/media key overrides, or any other machine-specific customization.
# Get the ID for each machine with the `toshy-machine-id` command, for use in `if` conditions.
MACHINE_ID = get_machine_id_hash()



#################  VARIABLES  ####################
###                                            ###
###                                            ###
###      ██    ██  █████  ██████  ███████      ###
###      ██    ██ ██   ██ ██   ██ ██           ###
###      ██    ██ ███████ ██████  ███████      ###
###       ██  ██  ██   ██ ██   ██      ██      ###
###        ████   ██   ██ ██   ██ ███████      ###
###                                            ###
###                                            ###
##################################################
# Establish important global variables here


STARTUP_TIMESTAMP = time.time()     # only gets evaluated once for each run of keymapper

# Variable to hold the keyboard type
KBTYPE = None

# Short names for the `xwaykeyz/keyszer` string and Unicode processing helper functions
ST = to_US_keystrokes           # was 'to_keystrokes' originally
UC = unicode_keystrokes
ignore_combo = ComboHint.IGNORE

###############################################################################
# This is a "trick" to negate the need to put quotes around all the key labels
# inside the "lists of dicts" to be given to the matchProps() function.
# Makes the variables evaluate to equivalent strings inside the dicts.
# Provides for nice syntax highlighting and visual separation of key:value.
clas        = 'clas'        # key label for matchProps() arg to match: wm_class
name        = 'name'        # key label for matchProps() arg to match: wm_name
devn        = 'devn'        # key label for matchProps() arg to match: device_name
not_clas    = 'not_clas'    # key label for matchProps() arg to NEGATIVE match: wm_class
not_name    = 'not_name'    # key label for matchProps() arg to NEGATIVE match: wm_name
not_devn    = 'not_devn'    # key label for matchProps() arg to NEGATIVE match: device_name
numlk       = 'numlk'       # key label for matchProps() arg to match: numlock_on
capslk      = 'capslk'      # key label for matchProps() arg to match: capslock_on
cse         = 'cse'         # key label for matchProps() arg to enable: case sensitivity
lst         = 'lst'         # key label for matchProps() arg to pass in a [list] of {dicts}
dbg         = 'dbg'         # key label for matchProps() arg to set debugging info string

# global variables for the isDoubleTap() function
tapTime1 = time.time()
tapInterval = 0.24
tapCount = 0
last_dt_combo = None

# Set this variable to False to disable the alert that appears
# when using Apple logo shortcut (Shift+Option+K)
applelogoalert_enabled = True   # Default: True




######################  LISTS  #######################
###                                                ###
###                                                ###
###      ██      ██ ███████ ████████ ███████       ###
###      ██      ██ ██         ██    ██            ###
###      ██      ██ ███████    ██    ███████       ###
###      ██      ██      ██    ██         ██       ###
###      ███████ ██ ███████    ██    ███████       ###
###                                                ###
###                                                ###
######################################################


def toRgxStr(lst_of_str) -> str:
    """
    Convert a list of strings into single casefolded regex pattern string.
    """
    def raise_TypeError(): raise TypeError(f"\n\n###  toRgxStr wants a list of strings  ###\n")
    if not isinstance(lst_of_str, list): raise_TypeError()
    if any([not isinstance(x, str) for x in lst_of_str]): raise_TypeError()
    lst_of_str_clean = [str(x).replace('^','').replace('$','') for x in lst_of_str]
    return "|".join('^'+x.casefold()+'$' for x in lst_of_str_clean)


def negRgx(rgx_str):
    """
    Convert positive match regex pattern into negative lookahead regex pattern.
    """
    # remove any ^$
    rgx_str_strip = str(rgx_str).replace('^','').replace('$','')
    # add back ^$, but only around ENTIRE STRING (ignore any vertical bars/pipes)
    rgx_str_add = str('^'+rgx_str_strip+'$')
    # convert ^$ to complicated negative lookahead pattern that actually works
    neg_rgx_str = str(rgx_str_add).replace('^','^(?:(?!^').replace('$','$).)*$')
    return neg_rgx_str


def create_list_of_dicts(lst: List[str]):
    """
    Convert a simple list of class names into a list of dictionaries,
    each dictionary containing a single key 'clas' with the regex pattern
    for exact match. Strips any leading '^' or trailing '$' from each item
    in the list to ensure clean, standardized entries.
    """
    cleaned_list = [name.strip('^$') for name in lst]  # Remove any leading '^' or trailing '$'
    return [{'clas': f"^{item}$"} for item in cleaned_list]


terminals = [
    "alacritty",
    # "com.mitchellh.ghostty",          # Replaced with double-wildcard ghostty pattern
    "com.raggesilver.BlackBox",
    "com.system76.CosmicTerm",
    "contour",
    "cutefish-terminal",
    "deepin-terminal",
    "dev.warp.Warp",
    "eterm",
    ".*ghostty.*",
    # "ghostty",                        # Replaced with double-wildcard ghostty pattern
    # "ghostty-debug",                  # Replaced with double-wildcard ghostty pattern
    "gnome-terminal",
    "gnome-terminal-server",
    "guake",
    "hyper",
    "io.elementary.terminal",
    "kinto-gui.py",
    "kitty",
    "Kgx",
    "konsole",
    "lxterminal",
    "mate-terminal",
    "MateTerminal",
    "org.codeberg.dnkl.foot.desktop",
    "org.gnome.Console",
    # "org.gnome.Ptyxis.*",             # Replaced by double-wildcard Ptyxis pattern
    "org.gnome.Terminal",
    "org.kde.konsole",
    "org.kde.yakuake",
    "org.wezfurlong.wezterm",
    ".*Ptyxis.*",
    "roxterm",
    "qterminal",
    "st",
    "sakura",
    "station",
    "tabby",
    "terminator",
    "terminology",
    "termite",
    "Termius",
    "tilda",
    "tilix",
    "urxvt",
    "Wave",
    "wezterm",
    "wezterm-gui",
    "xfce4-terminal",
    "xterm",
    "yakuake",
]
terminals                       = [x.casefold() for x in terminals]
termStr                         = toRgxStr(terminals)

# DEPRECATED
# This is only for use with 'remotes_lod', otherwise regex pattern string is used.
terminals_lod = create_list_of_dicts(terminals)

vscodes = [
    "code",
    "code - oss",
    "code-oss",
    "cursor",           # New VSCode variant with A.I.
    "vscodium",
]
vscodes                         = [x.casefold() for x in vscodes]
vscodeStr                       = toRgxStr(vscodes)

# DEPRECATED: Converted back to simple list
# This is only for use with 'vscodes_and_remotes_lod', otherwise regex pattern string is used.
vscodes_lod = create_list_of_dicts(vscodes)

sublimes = [
    "sublime_text",
    "subl",
]
sublimes                        = [x.casefold() for x in sublimes]
sublimeStr                      = toRgxStr(sublimes)

JDownloader_lod = [
    {clas: "^.*jdownloader.*$"},
    {clas: "^java-lang-Thread$", name: "^JDownloader.*$"}   # Happens after auto-update of app
]

# Transmission app can have several different app class strings
transmissions = [
    'Transmission-gtk',
    'Transmission-qt',
    'com.transmissionbt.Transmission.*',    # Flatpak has a stupid random app class suffix
]
transmissions                   = [x.casefold() for x in transmissions]
transmissionStr                 = toRgxStr(transmissions)


# Add remote desktop clients & VM software here
# Ideally we'd only exclude the client window,
# but that may not be easily done.
# (Can be done now with `keyszer`, as long as main window has a
# different WM_NAME than client windows. See `remotes_lod` below.)
remotes = [
    "Anydesk",
    "Gnome-boxes",
    "gnome-connections",
    "org.gnome.Boxes",
    "org.remmina.Remmina",
    "Nxplayer.bin",
    "remmina",
    "qemu-system-.*",
    "qemu",
    "Spicy",
    "Virt-manager",
    "VirtualBox",
    "VirtualBox Machine",
    "xfreerdp",
    "Wfica",
]
remotes = [x.casefold() for x in remotes]
remoteStr = toRgxStr(remotes)

# DEPRECATED: Converted back to simple list format
# Add remote desktop clients & VM software here
remotes_lod = [
    {clas: "^Anydesk$"                       },
    {clas: "^Gnome-boxes$"                   },
    {clas: "^gnome-connections$"             },
    {clas: "^org.remmina.Remmina$",
        not_name: "^Remmina Remote Desktop Client$|^Remote Connection Profile$"},
    {clas: "^Nxplayer.bin$"                  },
    {clas: "^remmina$"                       },
    {clas: "^qemu-system-.*$"                },
    {clas: "^qemu$"                          },
    {clas: "^Spicy$"                         },
    {clas: "^Virt-manager$"                  },
    {clas: "^VirtualBox$"                    },
    {clas: "^VirtualBox Machine$"            },
    {clas: "^xfreerdp$"                      },
    {clas: "^Wfica$"                         },
]

terms_and_remotes_lst = terminals + remotes
terms_and_remotes_Str = toRgxStr(terms_and_remotes_lst)

# DEPRECATED: Converted back to simple list
terminals_and_remotes_lod = [
    {lst: terminals_lod                  },
    {lst: remotes_lod                    },
]

# DEPRECATED by 'vscodes_and_remotes_lod' "list of dicts" below
# vscodes.extend(remotes)
# vscodeStr_ext = toRgxStr(vscodes)

vscodes_and_remotes_lst = vscodes + remotes
vscodes_and_remotes_Str = toRgxStr(vscodes_and_remotes_lst)

# DEPRECATED: Converted back to simple list
vscodes_and_remotes_lod = [
    {lst: vscodes_lod                    },
    {lst: remotes_lod                    },
]

browsers_chrome = [
    "Brave-browser",
    "Chromium",
    "Chromium-browser",
    "Falkon",
    "Google-chrome",
    "Io.github.ungoogled_software.ungoogled_chromium",
    "microsoft-edge",
    "microsoft-edge-dev",
    "org.deepin.browser",
    "org.kde.falkon",
    ".*ungoogled_chromium",
    "Vivaldi.*",
]
browsers_chrome         = [x.casefold() for x in browsers_chrome]
browsers_chromeStr      = "|".join('^'+x+'$' for x in browsers_chrome)

browsers_firefox = [
    "firedragon",               # Garuda Firefox fork
    "Firefox",
    "firefox_.*",   # Catch "firefox_firefox" (WTF?), seen on Ubuntu Cinnamon 25.10 in X11 session
    "firefox-esr",
    "Firefox Developer Edition",
    "firefoxdeveloperedition",
    "firefox-nightly.*",
    "floorp",
    "LibreWolf",
    "Mullvad Browser",
    "Navigator",
    "org.mozilla.firefox",
    "Waterfox",
    "zen-browser",
    "zen",
    "zen-alpha",
    "zen-beta",
    "zen-bin",
    "zen-twilight",
]
browsers_firefox        = [x.casefold() for x in browsers_firefox]
browsers_firefoxStr     = "|".join('^'+x+'$' for x in browsers_firefox)

browsers_all = [
    # unpack Chrome and Firefox lists into this general browser list
    *browsers_chrome,
    *browsers_firefox,
    "Discord",
    "Epiphany",
    "org.gnome.Epiphany",
]
browsers_all            = [x.casefold() for x in browsers_all]
browsers_allStr         = "|".join('^'+x+'$' for x in browsers_all)


# NOTE: Do not be tempted to convert simple app class lists into a "list of dicts"
# If the list contains only app classes, the regex pattern string is much faster.
filemanagers = [
    "caja",
    "com.system76.CosmicFiles",
    "dde-file-manager",
    "dolphin",
    "io.elementary.files",
    "krusader",
    "nautilus",
    "nemo",
    "org.gnome.nautilus",
    "org.kde.dolphin",
    "org.kde.krusader",
    "pcmanfm",
    "pcmanfm-qt",
    "peony-qt",
    "spacefm",
    "thunar",
]
filemanagers = [x.casefold() for x in filemanagers]
filemanagerStr = "|".join('^'+x+'$' for x in filemanagers)


### dialogs_Escape_lod = send these windows the Escape key for Cmd+W
dialogs_Escape_lod = [
    {clas: "^Angry.*IP.*Scanner$",
        name: "^IP.*address.*details.*$|^Preferences.*$|^Scan.*Statistics.*$|^Edit.*openers.*$"},
    # TODO: add or change Atoms class to "pm.mirko.Atoms" if the app gets updated
    # TODO: remove "atoms" from "name: " entry patterns if "Shortcuts" dialog gets updated
    # Reference: https://github.com/AtomsDevs/Atoms/issues/61
    {clas: "^atoms$", name: "^Preferences$|^Shortcuts$|^About$|^atoms$"},
    {clas: "^com.github.rafostar.Clapper$", name: "^Preferences$"},
    {clas: "^epiphany$|^org.gnome.Epiphany$", name: "^Preferences$"},
    {clas: "^gnome-text-editor$|^org.gnome.TextEditor$", name: "^Preferences$"},
    {clas: "^io.github.celluloid_player.Celluloid$", name: "^Preferences$"},
    {clas: "^konsole$|^org.kde.konsole$", name: "^Configure.*Konsole$|^Edit Profile.*Konsole$"},
    {clas: "^krusader$|^org.kde.krusader$", name: "^Properties.*Krusader$"},
    {clas: "^.*nautilus$", name: "^.*Properties$|^Preferences$|^Create Archive$|^Rename.*Files$"},
    # {clas: "^org.gnome.Ptyxis.*$", name: "^Preferences$"},
    {clas: "^.*Ptyxis.*$", name: "^Preferences$"},
    {clas: "^org.gnome.Shell.Extensions$"},
    {clas: "^org.kde.Dolphin$", name: "^Configure.*Dolphin$|^Properties.*Dolphin$"},
    {clas: "^org.kde.falkon$|^Falkon$", name: "^Preferences.*Falkon$"},
    {clas: "^org.kde.kdialog$"},
    {clas: "^org.kde.KWrite$", name: "^Configure.*KWrite$"},
    {clas: "^org.gnome.Software$", not_name: "^Software$"},
    {clas: transmissionStr, not_name: "^Transmission$"},
    {clas: "^xfce4-terminal$", name: "^Terminal Preferences$"},
    {clas: "^zenity$|^qarma$"}
]

### dialogs_CloseWin_lod = send these windows the "Close window" combo for Cmd+W
dialogs_CloseWin_lod = [
    {clas: "^Angry.*IP.*Scanner$", name: "^Fetchers.*$|^Edit.*favorites.*$"},
    {clas: "^com.mattjakeman.ExtensionManager$|^extension-manager$", not_name: "^Extension Manager$"},
    {clas: "^fr.handbrake.ghb$", not_name: "^HandBrake$"},
    {clas: "^Gnome-control-center$", not_name: "^Settings$"},
    {clas: "^gnome-terminal.*$", name: "^Preferences.*$"},
    {clas: "^gnome-terminal-pref.*$", name: "^Preferences.*$"},
    {clas: "^org.kde.kate$", name: "^Configure.*Kate$"},
    {clas: "^pcloud$"},
    {clas: "^systemsettings$", name: "^Download New.*System Settings$"},
    {clas: "^Totem$", not_name: "^Videos$"},
]


###################################################################################################
###  SLICE_MARK_START: kbtype_override  ###  EDITS OUTSIDE THESE MARKS WILL BE LOST ON UPGRADE

keyboards_UserCustom_dct = {
    # Add your keyboard device here if its type is misidentified.
    # Valid types to map device to: Apple, Windows, IBM, Chromebook (case sensitive)
    # Example:
    'My Keyboard Device Name': 'Apple',
}

###  SLICE_MARK_END: kbtype_override  ###  EDITS OUTSIDE THESE MARKS WILL BE LOST ON UPGRADE
###################################################################################################

# Create a "UserCustom" keyboard dictionary with casefolded keys
kbds_UserCustom_dct_cf = {k.casefold(): v for k, v in keyboards_UserCustom_dct.items()}


# Lists of keyboard device names, to match keyboard type
keyboards_IBM = [
    # Add specific IBM-style keyboard device names to this list
    'IBM Enhanced (101/102-key) Keyboard',
    'IBM Rapid Access Keyboard',
    'IBM Space Saver II',
    'IBM Model M',
    'IBM Model F',
]
keyboards_Chromebook = [
    # Add specific Chromebook keyboard device names to this list
    'Google.*Keyboard',
]
keyboards_Windows = [
    # Add specific Windows/PC keyboard device names to this list
    'AT Translated Set 2 keyboard',
]
keyboards_Apple = [
    # Add specific Apple/Mac keyboard device names to this list
    'HP TouchPad Wireless Keyboard',    # Missing some keys, but Apple type probably best default
    'Magic Keyboard with Numeric Keypad',
    'Magic Keyboard',
    'Mitsumi Electric Apple Extended USB Keyboard',
    'MX Keys Mac Keyboard',
    'Griffin Technology, Inc. iMate, USB To ADB Adaptor',
    '.*USB to ADB Adapt.*'  # ADB device is pretty much guaranteed to be an Apple (or NeXT) keyboard
]

kbtype_lists = {
    'IBM':          keyboards_IBM,
    'Chromebook':   keyboards_Chromebook,
    'Windows':      keyboards_Windows,
    'Apple':        keyboards_Apple
}

# List of all known keyboard devices from all lists
all_keyboards       = [kb for kbtype in kbtype_lists.values() for kb in kbtype]

# keyboard lists compiled to regex objects (replacing spaces with wildcards)
kbds_IBM_rgx        = [re.compile(kb.replace(" ", ".*"), re.I) for kb in keyboards_IBM]
kbds_Chromebook_rgx = [re.compile(kb.replace(" ", ".*"), re.I) for kb in keyboards_Chromebook]
kbds_Windows_rgx    = [re.compile(kb.replace(" ", ".*"), re.I) for kb in keyboards_Windows]
kbds_Apple_rgx      = [re.compile(kb.replace(" ", ".*"), re.I) for kb in keyboards_Apple]

# Dict mapping keyboard type keywords onto
kbtype_lists_rgx    = {
    'IBM':          kbds_IBM_rgx,
    'Chromebook':   kbds_Chromebook_rgx,
    'Windows':      kbds_Windows_rgx,
    'Apple':        kbds_Apple_rgx
}

# List of all known keyboard devices from all lists
all_kbds_rgx        = re.compile(toRgxStr(all_keyboards), re.I)

not_win_type_rgx    = re.compile("IBM|Chromebook|Apple", re.I)


# Suggested location for customizing lists and variables for use with the "when" conditions.
###################################################################################################
###  SLICE_MARK_START: user_custom_lists  ###  EDITS OUTSIDE THESE MARKS WILL BE LOST ON UPGRADE



###  SLICE_MARK_END: user_custom_lists  ###  EDITS OUTSIDE THESE MARKS WILL BE LOST ON UPGRADE
###################################################################################################



###################################  CUSTOM FUNCTIONS  ####################################
###                                                                                     ###
###                                                                                     ###
###      ███████ ██    ██ ███    ██  ██████ ████████ ██  ██████  ███    ██ ███████      ###
###      ██      ██    ██ ████   ██ ██         ██    ██ ██    ██ ████   ██ ██           ###
###      █████   ██    ██ ██ ██  ██ ██         ██    ██ ██    ██ ██ ██  ██ ███████      ###
###      ██      ██    ██ ██  ██ ██ ██         ██    ██ ██    ██ ██  ██ ██      ██      ###
###      ██       ██████  ██   ████  ██████    ██    ██  ██████  ██   ████ ███████      ###
###                                                                                     ###
###                                                                                     ###
###########################################################################################


# Instantiate a useful notification object class instance, to make notifications easier
ntfy = NotificationManager(icon_file_active, title='Toshy Alert (Config)')


def isKBtype(kbtype: str, map=None):
    # guard against failure to give valid type arg (we don't need to casefold anything with this)
    if kbtype not in ['IBM', 'Chromebook', 'Windows', 'Apple']:
        raise ValueError(f"Invalid type given to isKBtype() function: '{kbtype}'"
                f'\n\t Valid keyboard types (case sensitive): IBM | Chromebook | Windows | Apple')
    def _isKBtype(ctx: KeyContext):
        # debug(f"KBTYPE: '{KBTYPE}' | isKBtype check from map: '{map}'")
        return kbtype == KBTYPE
    return _isKBtype


kbtype_cache_dct = {}


def getKBtype():
    """
    ### Get the keyboard type string for the current device

    #### Valid Types

    - IBM | Chromebook | Windows | Apple

    #### Hierarchy of validations:

    - Check if a forced override of keyboard type is applied by user preference.
    - Check cache dictionary for device name stored from previous run of function.
    - Check if the device name is in the keyboards_UserCustom_dct dictionary.
    - Check if the device name matches any keyboard type list.
    - Check if any keyboard type string is found in the device name string.
    - Check if the device name indicates a "Windows" keyboard by excluding other types.
    """

    valid_kbtypes = ['IBM', 'Chromebook', 'Windows', 'Apple']

    def _getKBtype(ctx: KeyContext):
        # debug(f"Entering getKBtype with override value: '{cnfg.override_kbtype}'")
        global KBTYPE
        kbd_dev_name = ctx.device_name

        def log_kbtype(msg, cache_dev):
            debug(f"KBTYPE: '{KBTYPE}' | {msg}: '{kbd_dev_name}'")
            if cache_dev:
                kbtype_cache_dct[kbd_dev_name] = (KBTYPE, msg)

        # If user wants to override, apply override and return.
        # Breaks per-device adaptatation capability while engaged!
        if cnfg.override_kbtype in valid_kbtypes:
            KBTYPE = cnfg.override_kbtype
            log_kbtype(f"WARNING: Override applied! Dev", cache_dev=False)
            return

        # Check in the kbtype cache dict for the device
        if kbd_dev_name in kbtype_cache_dct:
            KBTYPE, cached_msg = kbtype_cache_dct[kbd_dev_name]
            log_kbtype(f'(CACHED) {cached_msg}', cache_dev=False)
            return

        kbd_dev_name_cf = ctx.device_name.casefold()

        # Check if there is a custom type for the device
        custom_kbtype = kbds_UserCustom_dct_cf.get(kbd_dev_name_cf, '')
        if custom_kbtype and custom_kbtype in valid_kbtypes:
            KBTYPE = custom_kbtype
            log_kbtype('Custom type for dev', cache_dev=True)
            return

        # Check against the keyboard type lists
        for kbtype, regex_lst in kbtype_lists_rgx.items():
            for rgx in regex_lst:
                if rgx.search(kbd_dev_name_cf):
                    KBTYPE = kbtype
                    log_kbtype('Rgx matched on dev', cache_dev=True)
                    return

        # Check if any keyboard type string is found in the device name
        for kbtype in ['IBM', 'Chromebook', 'Windows', 'Apple']:
            if kbtype.casefold() in kbd_dev_name_cf:
                KBTYPE = kbtype
                log_kbtype('Type in dev name', cache_dev=True)
                return

        # Check if the device name indicates a "Windows" keyboard
        if ('windows' not in kbd_dev_name_cf
            and not not_win_type_rgx.search(kbd_dev_name_cf)
            and not all_kbds_rgx.search(kbd_dev_name_cf) ):
            KBTYPE = 'Windows'
            log_kbtype('Default type for dev', cache_dev=True)
            return

        # Default to None if no matching keyboard type is found
        KBTYPE = 'unidentified'
        error(f"KBTYPE: '{KBTYPE}' | Dev fell through all checks: '{kbd_dev_name}'")

    return _getKBtype  # Return the inner function


def isDoubleTap(dt_combo):
    """
    VERY EXPERIMENTAL!!!

    Simplistic detection of double-tap of a key or combo.

    BLOCKS single-tap function, if used with a single key as the input, but the
    'normal' (non-modifier) key of a combo will still be usable when used by
    itself as a non-double-tapped key press.

    Example: 'RC-CapsLock' will respond when "Cmd" key (under Toshy remapping)
    is held and CapsLock key is double-tapped. Nothing will happen if
    Cmd+CapsLock is pressed without double-tapping CapsLock key within the
    configured time interval. But the CapsLock key will still work by itself.

    If double-tap input "combo" is just 'CapsLock', the functioning of a single-tap
    CapsLock key press will be BLOCKED. Nothing will happen unless the key is
    double-tapped within the configured time interval.

    Only cares about the 'real' key in a combo of Mods+key, like in the example
    above with 'RC-CapsLock'.

    The proper way to do this would be inside the keymapper, in the async event loop
    that deals with input/output functions.
    """
    def _isDoubleTap():
        global tapTime1
        global tapInterval
        global tapCount
        global last_dt_combo
        _tapTime = time.time()
        # This first "if" block has a logic defect, if a different key in the
        # same keymap is also set up to send the same "dt_combo" value.
        if tapCount == 1 and last_dt_combo != dt_combo:
            debug(f'## isDoubleTap: \n\tDifferent combo: \n\t{last_dt_combo, dt_combo=}')
            last_dt_combo = None
            tapCount = 0
        # 2nd tap beyond time interval? Treat as new double-tap cycle.
        if tapCount == 1 and _tapTime - tapTime1 >= tapInterval:
            debug(f'## isDoubleTap: \n\tTime diff (too long): \n\t{_tapTime - tapTime1=}')
            tapCount = 0
        # Try to keep held key from producing repeats of dt_combo.
        # If repeat rate very slow or delay very short, this won't work well.
        if tapCount == 1 and _tapTime - tapTime1 < 0.07:
            debug(f'## isDoubleTap: \n\tTime diff (too short): \n\t{_tapTime - tapTime1=}')
            tapCount = 0
            return None
        # 2nd tap within interval window? Reset cycle & send dt_combo.
        if tapCount == 1 and _tapTime - tapTime1 < tapInterval:
            debug(f'## isDoubleTap: \n\tTime diff (just right): \n\t{_tapTime - tapTime1=}')
            tapCount = 0
            tapTime1 = 0.0
            return dt_combo
        # New cycle? Set count = 1, tapTime1 = now. Send nothing.
        if tapCount == 0:
            debug(f'## isDoubleTap: \n\tTime diff (1st cycle): \n\t{_tapTime - tapTime1=}')
            last_dt_combo = dt_combo
            tapCount = 1
            tapTime1 = _tapTime
            return None
    return _isDoubleTap


total_matchProps_iterations = 0
MAX_MATCHPROPS_ITERATIONS = 1000
MAX_MATCHPROPS_ITERATIONS_REACHED = False
MATCHPROPS_FULL_DEBUG = False  # Set True to disable short-circuits and enable full debug logging


# Correct syntax to reject all positional parameters: put `*,` at beginning
def matchProps(*,
    # string parameters (positive matching)
    clas: str = None, name: str = None, devn: str = None,
    # string parameters (negative matching)
    not_clas: str = None, not_name: str = None, not_devn: str = None,
    # bool parameters
    numlk: bool = None, capslk: bool = None, cse: bool = None,
    # list of dicts of parameters (positive)
    lst: List[Dict[str, Union[str, bool]]] = None,
    # list of dicts of parameters (negative)
    not_lst: List[Dict[str, Union[str, bool]]] = None,
    dbg: str = None,    # debugging info (such as: which modmap/keymap?)
) -> Callable[[KeyContext], bool]:
    """
    ### Match all given properties to current window context.       \n
    - Parameters must be _named_, no positional arguments.          \n
    - All parameters optional, but at least one must be given.      \n
    - Defaults to case insensitive matching of:                     \n
        - WM_CLASS, WM_NAME, device_name                            \n
    - To negate/invert regex pattern match use:                     \n
        - `not_clas` `not_name` `not_devn` params or...             \n
        - "^(?:(?!^pattern$).)*$"                                   \n
    - To force case insensitive pattern match use:                  \n
        - "^(?i:pattern)$" or...                                    \n
        - "^(?i)pattern$"                                           \n

    ### Accepted Parameters:                                        \n
    `clas` = WM_CLASS    (regex/string) [xprop WM_CLASS]            \n
    `name` = WM_NAME     (regex/string) [xprop _NET_WM_NAME]        \n
    `devn` = Device Name (regex/string) [xwaykeyz --list-devices]   \n
    `not_clas` = `clas` but inverted, matches when "not"            \n
    `not_name` = `name` but inverted, matches when "not"            \n
    `not_devn` = `devn` but inverted, matches when "not"            \n
    `numlk`    = Num Lock LED state         (bool)                  \n
    `capslk`   = Caps Lock LED state        (bool)                  \n
    `cse`      = Case Sensitive matching    (bool)                  \n
    `lst`      = List of dicts of the above arguments               \n
    `not_lst`  = `lst` but inverted, matches when "not"             \n
    `dbg`      = Debugging info             (string)                \n

    ### Negative match parameters:
    - `not_clas`|`not_name`|`not_devn`                              \n
    Parameters take same regex patterns as `clas`|`name`|`devn`     \n
    but result in a True condition only if pattern is NOT found.    \n
    Negative parameters cannot be used together with the normal     \n
    positive matching equivalent parameter in same instance.        \n

    ### List of Dicts parameter: `lst`|`not_lst`
    A [list] of {dicts} with each dict containing 1 to 6 of the     \n
    named parameters above, to be processed recursively as args.    \n
    A dict can also contain a single `lst` or `not_lst` argument.   \n

    ### Debugging info parameter: `dbg`
    A string that will print as part of logging output. Use to      \n
    help identify origin of logging output.                         \n
    -                                                               \n
    """
    # Reference for successful negative lookahead pattern, and
    # explanation of why it works:
    # https://stackoverflow.com/questions/406230/\
        # regular-expression-to-match-a-line-that-doesnt-contain-a-word

    global MAX_MATCHPROPS_ITERATIONS_REACHED
    global total_matchProps_iterations

    # Return `False` immediately if screen does not have focus (e.g. Synergy),
    # but only after the guard clauses have had a chance to evaluate on
    # all possible uses of the function that may exist in the config.
    if MAX_MATCHPROPS_ITERATIONS_REACHED and not cnfg.screen_has_focus:
        # return False    # Returning a boolean here causes as exception. Must return a callable!
        return lambda _: False

    if total_matchProps_iterations >= MAX_MATCHPROPS_ITERATIONS:
        MAX_MATCHPROPS_ITERATIONS_REACHED = True
        bypass_guard_clauses = True
    else:
        total_matchProps_iterations += 1
        current_timestamp = time.time()

        # 'STARTUP_TIMESTAMP' is a global variable, set when config is executed
        time_elapsed = current_timestamp - STARTUP_TIMESTAMP

        # Bypass all guard clauses if more than a few seconds have passed since keymapper
        # started and loaded the config file. Inputs never change until keymapper
        # restarts and reloads the config file, so we don't need to keep checking.
        bypass_guard_clauses = time_elapsed > 6

    logging_enabled = False

    allowed_params  = (clas, name, devn, not_clas, not_name, not_devn,
                        numlk, capslk, cse, lst, not_lst, dbg)
    lst_dct_params  = (clas, name, devn, not_clas, not_name, not_devn,
                        numlk, capslk, cse)
    string_params   = (clas, name, devn, not_clas, not_name, not_devn, dbg)

    # This was using up a lot of CPU time, actually. Bad idea.
    # dct_param_strs  = list(inspect.signature(matchProps).parameters.keys())

    # Static list of parameter names. Using this instead of `inspect` cuts CPU
    # usage considerably, for reasons I don't yet understand. Apparently the
    # keymapper is actually running the entire function again on each key
    # press and release, rather than just re-evaluating the inner closure.
    dct_param_strs = [
        'clas', 'name', 'devn', 'not_clas', 'not_name', 'not_devn',
        'numlk', 'capslk', 'cse', 'lst', 'not_lst', 'dbg'
    ]

    if not MAX_MATCHPROPS_ITERATIONS_REACHED or not bypass_guard_clauses:
        if all([x is None for x in allowed_params]):
            raise ValueError(f"\n\n(EE) matchProps(): Received no valid argument\n")
        if any([x not in (True, False, None) for x in (numlk, capslk, cse)]):
            raise TypeError(f"\n\n(EE) matchProps(): Params 'numlk|capslk|cse' are bools\n")
        if any([x is not None and not isinstance(x, str) for x in string_params]):
            raise TypeError(    f"\n\n(EE) matchProps(): These parameters must be strings:"
                                f"\n\t'clas|name|devn|not_clas|not_name|not_devn|dbg'\n")
        if clas and not_clas or name and not_name or devn and not_devn or lst and not_lst:
            raise ValueError(   f"\n\n(EE) matchProps(): Do not mix positive and "
                                f"negative match params for same property\n")

    # consolidate positive and negative matching params into new vars
    # only one should be in use at a time (checked above)
    _lst = not_lst if lst is None else lst
    _clas = not_clas if clas is None else clas
    _name = not_name if name is None else name
    _devn = not_devn if devn is None else devn

    # process lists of conditions
    if _lst is not None:

        if not MAX_MATCHPROPS_ITERATIONS_REACHED or not bypass_guard_clauses:
            if any([x is not None for x in lst_dct_params]):
                raise TypeError(f"\n\n(EE) matchProps(): Param 'lst|not_lst' must be used alone\n")
            if not isinstance(_lst, list) or not all(isinstance(item, dict) for item in _lst):
                raise TypeError(
                    f"\n\n(EE) matchProps(): Param 'lst|not_lst' wants a [list] of {{dicts}}\n")
            # verify that every {dict} in [list of dicts] only contains valid parameter names
            for dct in _lst:
                for param in list(dct.keys()):
                    if param not in dct_param_strs:
                        error(f"matchProps(): Invalid parameter: '{param}'")
                        error(f"Invalid parameter is in this dict: \n\t{dct}")
                        error(f"Dict is in this list:")
                        for item in _lst:
                            print(f"\t{item}")
                        raise ValueError(
                            f"\n(EE) matchProps(): Invalid parameter found in dict in list. "
                            f"See log output before traceback.\n")

        def _matchProps_Lst(ctx: KeyContext):
            if not cnfg.screen_has_focus:
                return False
            if not_lst is not None:
                if logging_enabled: print(f"## _matchProps_Lst()[not_lst] ## {dbg=}")
                return not any(matchProps(**dct)(ctx) for dct in not_lst)
            else:
                if logging_enabled: print(f"## _matchProps_Lst()[lst] ## {dbg=}")
                return any(matchProps(**dct)(ctx) for dct in lst)

        return _matchProps_Lst      # outer function returning inner function

    # compile case insensitive regex object for given params, unless cse=True
    if _clas is not None: clas_rgx = re.compile(_clas, 0 if cse else re.I)
    if _name is not None: name_rgx = re.compile(_name, 0 if cse else re.I)
    if _devn is not None: devn_rgx = re.compile(_devn, 0 if cse else re.I)

    def _matchProps(ctx: KeyContext):
        if not cnfg.screen_has_focus:
            return False

        nt_err = 'ERR: matchProps: NoneType in ctx.'

        # Full debug mode: use original cond_list approach for complete visibility
        if MATCHPROPS_FULL_DEBUG:
            cond_list = []
            if numlk is not None:
                cond_list.append(numlk is ctx.numlock_on)
            if capslk is not None:
                cond_list.append(capslk is ctx.capslock_on)
            if _devn is not None:
                devn_match = re.search(devn_rgx, ctx.device_name or nt_err + 'device_name')
                cond_list.append(not devn_match if not_devn is not None else devn_match)
            if _clas is not None:
                clas_match = re.search(clas_rgx, ctx.wm_class or nt_err + 'wm_class')
                cond_list.append(not clas_match if not_clas is not None else clas_match)
            if _name is not None:
                name_match = re.search(name_rgx, ctx.wm_name or nt_err + 'wm_name')
                cond_list.append(not name_match if not_name is not None else name_match)
            print(f'####  CND_LST ({all(cond_list)})  ####  {dbg=}')
            for elem in cond_list:
                print('##', re.sub(r'^.*span=.*\), ', '', str(elem)).replace('>',''))
            print('-------------------------------------------------------------------')
            return all(cond_list)

        # Optimized path: short-circuit on first failure
        # Order: cheapest checks first, then most selective (devn), then clas, then name

        # Bool checks - nearly free (identity comparison)
        if numlk is not None and numlk is not ctx.numlock_on:
            return False
        if capslk is not None and capslk is not ctx.capslock_on:
            return False

        # Device check - most selective, eliminates most keystrokes from other devices
        if _devn is not None:
            devn_match = re.search(devn_rgx, ctx.device_name or nt_err + 'device_name')
            # XOR: fail if (negative match requested) == (match found)
            if (not_devn is not None) == bool(devn_match):
                return False

        # Class check - moderately selective, often complex regex patterns
        if _clas is not None:
            clas_match = re.search(clas_rgx, ctx.wm_class or nt_err + 'wm_class')
            if (not_clas is not None) == bool(clas_match):
                return False

        # Name check - least commonly used
        if _name is not None:
            name_match = re.search(name_rgx, ctx.wm_name or nt_err + 'wm_name')
            if (not_name is not None) == bool(name_match):
                return False

        return True

    return _matchProps      # outer function returning inner function


# Boolean variable to toggle Enter key state between F2 and Enter
# True = Enter key sends F2, False = Enter key sends Enter
_enter_is_F2 = True                 # DON'T CHANGE THIS! Must be set to True here.
_enter_F2_last_app_class = None     # Track which app set the state to be False


def iEF2(combo_if_true, latch_or_combo_if_false,
                keep_value_if_true=False, keep_value_if_false=False):
    """
    Formerly 'is_Enter_F2'
    Send a different combo for the Enter key based on the state of the `_enter_is_F2` variable,
    or latch the variable to True or False to control the Enter key output on the next use.

    Store the app class of the file manager that sets the state variable to be False, and
    reset the state variable to True if the current app class does not match.

    Args:
        combo_if_true:              The combo to send if _enter_is_F2 is True.
        latch_or_combo_if_false:    The combo to send if _enter_is_F2 is False, or
                                    a Boolean to latch _enter_is_F2 to a specific value.
        keep_value_if_true (opt.):  If True, _enter_is_F2 will be kept True if it is currently True.
                                    If False, _enter_is_F2 will be set to False if it is currently True.
        keep_value_if_false (opt.): If True, _enter_is_F2 will be kept False if it is currently False.
                                    If False, _enter_is_F2 will be set to True if it is currently False.

    Returns:
        A function that, when called, returns the appropriate combo based on the current
        state of _enter_is_F2 and the provided parameters, and updates _enter_is_F2
        based on the provided parameters. The current app class is obtained by checking
        the context object.

    This enables a simulation of the macOS Finder's "Enter to rename" capability, allowing
    for complex control over the Enter key's behavior in various scenarios.
    """
    def _is_Enter_F2(ctx: KeyContext):
        global _enter_is_F2, _enter_F2_last_app_class

        # If last app class that set state to False is not None, and does not match current
        # app, reset the state var to True for initial behavior in new file manager windows.
        if _enter_F2_last_app_class and _enter_F2_last_app_class != ctx.wm_class:
            _enter_is_F2 = True
            _enter_F2_last_app_class = None

        combo_list = [combo_if_true]
        if latch_or_combo_if_false in (True, False):    # Latch variable to the provided bool value
            _enter_is_F2 = latch_or_combo_if_false
        elif _enter_is_F2:                              # If Enter is F2 now, set to be Enter next
            if keep_value_if_true is False:
                _enter_is_F2 = False
        else:                                           # If Enter is Enter now, set to be F2 next
            combo_list = [latch_or_combo_if_false]
            if keep_value_if_false is False:
                _enter_is_F2 = True

        # At this point we know whether the state var was set to True or False
        if not _enter_is_F2:
            # Record which app set state var to False
            _enter_F2_last_app_class = ctx.wm_class

        # If state var is currently True, clear last app.
        elif _enter_is_F2:
            _enter_F2_last_app_class = None

        debug(f"_is_Enter_F2:               {combo_list      = }")
        debug(f"_is_Enter_F2:               {_enter_is_F2    = }")
        debug(f"_enter_F2_last_app_class:   {_enter_F2_last_app_class = }")

        return combo_list
    return _is_Enter_F2


def iEF2NT():
    """Feed `is_Enter_F2` function `None` and `True` as arguments, with short name"""
    return iEF2(None, True)


def macro_tester():
    """Type out a macro with useful info and a Unicode test.
        WARNING: Safe only for use in apps that accept text blocks/typing of many characters."""
    def _macro_tester(ctx: KeyContext):
        return [
                    C("Enter"),
                    ST(f"Class: '{ctx.wm_class}'"), C("Enter"),
                    ST(f"Title: '{ctx.wm_name}'"), C("Enter"),
                    ST(f"Keybd: '{ctx.device_name}'"), C("Enter"),
                    ST(f"Keyboard type: '{KBTYPE}'"), C("Enter"),
                    ST("Next test should come out on ONE LINE!"), C("Enter"),
                    ST("Unicode and Shift Test: 🌹—€—\u2021—ÿ—\U00002021 12345 !@#$% |\\ !!!!!!"),
                    C("Enter"), C("Enter"),
        ]
    return _macro_tester


def is_valid_command(command):
    """Check if the command path is valid and executable"""
    return command and os.path.isfile(command) and os.access(command, os.X_OK)


# Result will be None if DE is not in list OR if 'kdialog' not available.
# kdialog_cmd = shutil.which('kdialog') if DESKTOP_ENV.casefold() in ['kde', 'lxqt'] else None
# DISABLING KDIALOG BECAUSE IT KIND OF SUCKS QUITE A BIT COMPARED TO ZENITY/QARMA
kdialog_cmd = shutil.which('kdialog') if DESKTOP_ENV.casefold() in ['kdialog_is_lame'] else None


zenity_is_qarma = False

zenity_cmd = shutil.which('zenity-gtk')
if not zenity_cmd:
    zenity_cmd = shutil.which('qarma')
    if zenity_cmd:
        zenity_is_qarma = True
if not zenity_cmd:
    zenity_cmd = shutil.which('zenity')

debug(f"Zenity command path: '{zenity_cmd}'")

zenity_icon_option = None

if zenity_cmd:
    try:
        zenity_help_output = subprocess.check_output([zenity_cmd, '--help-info'])
        help_text = str(zenity_help_output)
        if '--icon=' in help_text:
            zenity_icon_option = '--icon=toshy_app_icon_rainbow'
        elif '--icon-name=' in help_text:
            zenity_icon_option = '--icon-name=toshy_app_icon_rainbow'
    except subprocess.CalledProcessError:
        pass  # zenity --help-info failed, assume icon is not supported
else:
    error('ERR: Zenity command is missing! Diagnostic dialog not available!')


def notify_context():
    """pop up a dialog with context info"""
    def _notify_context(ctx: KeyContext):

        dialog_cmd              = None
        nwln_str                = '\n'

        if kdialog_cmd:
            dialog_cmd          = kdialog_cmd
            nwln_str            = '<br>'
        elif zenity_cmd:
            dialog_cmd          = zenity_cmd
            nwln_str            = '<br>' if zenity_is_qarma else '\n'
        elif not zenity_cmd and not kdialog_cmd:
            error('ERR: Diagnostic dialog not available. Necessary commands missing.')
            return

        if not is_valid_command(dialog_cmd):
            error(f"ERR: Dialog command not valid: '{dialog_cmd}'")
            return

        # fix a problem with zenity and <tags> in text
        def escape_markup(text: str):
            return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

        ctx_clas        = ctx.wm_class
        ctx_name        = ctx.wm_name
        ctx_devn        = ctx.device_name

        # ------ following are all True/False
        ctx_term        = matchProps(clas=termStr           )(ctx)
        ctx_rmte        = matchProps(clas=remoteStr         )(ctx)
        ctx_fmgr        = matchProps(clas=filemanagerStr    )(ctx)
        ctx_brws        = matchProps(clas=browsers_allStr   )(ctx)
        ctx_vscd        = matchProps(clas=vscodeStr         )(ctx)

        if matchProps(lst=dialogs_CloseWin_lod)(ctx) or matchProps(lst=dialogs_Escape_lod)(ctx):
            ctx_dlgs        = True
        else:
            ctx_dlgs        = False

        message         = (
            f"<tt>"
            f"<b>Class:</b> '{escape_markup(ctx_clas)}' {nwln_str}"
            f"<b>Title:</b> '{escape_markup(ctx_name)}' {nwln_str}"
            f"{nwln_str}"
            f"<b>Input keyboard name:</b> '{ctx_devn}' {nwln_str}"
            f"<b>Device seen as type:</b> '{KBTYPE}' {nwln_str}"
            f"{nwln_str}"
            f"<b>Toshy config file sees this environment:</b>  {nwln_str}"
            f"<b> • DISTRO_ID ____________</b> '{DISTRO_ID      }' {nwln_str}"
            f"<b> • DISTRO_VER ___________</b> '{DISTRO_VER     }' {nwln_str}"
            f"<b> • VARIANT_ID ___________</b> '{VARIANT_ID     }' {nwln_str}"
            f"<b> • SESSION_TYPE _________</b> '{SESSION_TYPE   }' {nwln_str}"
            f"<b> • DESKTOP_ENV __________</b> '{DESKTOP_ENV    }' {nwln_str}"
            f"<b> • DE_MAJ_VER ___________</b> '{DE_MAJ_VER     }' {nwln_str}"
            f"<b> • WINDOW_MGR ___________</b> '{WINDOW_MGR     }' {nwln_str}"
            f"{nwln_str}"
            f"<b>Do any app class groups match on this window?:</b>  {nwln_str}"
            f"<b> • Terminals ____________</b> '{ctx_term}' {nwln_str}"
            f"<b> • Remotes/VMs __________</b> '{ctx_rmte}' {nwln_str}"
            f"<b> • File Managers ________</b> '{ctx_fmgr}' {nwln_str}"
            f"<b> • Web Browsers _________</b> '{ctx_brws}' {nwln_str}"
            f"<b> • VSCode(s) ____________</b> '{ctx_vscd}' {nwln_str}"
            f"<b> • Dialogs ______________</b> '{ctx_dlgs}' {nwln_str}"
            f"{nwln_str}"
            f"<b> __________________________________________________ </b>{nwln_str}"
            f"<i>Keyboard shortcuts (Ctrl+C/Cmd+C) may not work here.</i>{nwln_str}"
            f"<i>Select text with mouse. Triple-click to select all. </i>{nwln_str}"
            f"<i>Right-click with mouse and choose 'Copy' from menu. </i>{nwln_str}"
            f"</tt>"
        )

        zenity_cmd_lst = [  zenity_cmd, '--info', '--no-wrap',
                            '--title=Toshy Context Info',
                            '--text=' + message ]

        # insert the icon argument if it's supported
        if zenity_icon_option is not None:
            zenity_cmd_lst.insert(3, zenity_icon_option)

        kdialog_cmd_lst = [kdialog_cmd, '--msgbox', message, '--title', 'Toshy Context Info']
        # Add icon if needed: kdialog_cmd_lst += ['--icon', '/path/to/icon']
        # Figure out why icon argument doesn't work. Need a proper icon theme folder?
        # DONE: Figured out that Kdialog does not support custom icons at all!
        kdialog_cmd_lst += ['--icon', 'toshy_app_icon_rainbow']

        if dialog_cmd == kdialog_cmd:
            subprocess.Popen(kdialog_cmd_lst, cwd=icons_dir, stderr=DEVNULL, stdout=DEVNULL)
        elif dialog_cmd == zenity_cmd:
            subprocess.Popen(zenity_cmd_lst, cwd=icons_dir, stderr=DEVNULL, stdout=DEVNULL)

        # Optionally, also send a system notification:
        # ntfy.send_notification(message)
    return _notify_context


def is_pre_GNOME_45(de_ver):
    """Utility function to check if GNOME version is older than GNOME 45"""
    if DESKTOP_ENV != 'gnome':
        # No need to go further if we aren't even in GNOME
        return False
    pre_G45_ver_lst = [44, 43, 42, 41, 40, 3]
    return str(de_ver).isdigit() and int(de_ver) in pre_G45_ver_lst


def toggle_and_show_capslock_state(ctx: KeyContext):
    """
    Show the (coming) state of CapsLock LED in a notification pop-up dialog.
    Then return the CapsLock key combo to toggle the CapsLock LED state.

    No need to return inner closure because not used in conditionals.
    Do not use () to 'call' the function from output macro. Not needed.

    Example usage:
    C("CapsLock"): toggle_and_show_capslock_state, # Toggle CapsLock, show notification
    """

    # Logic reversed because notification is constructed before combo is returned.
    message = 'CapsLock is ON' if not ctx.capslock_on else 'CapsLock is OFF'
    icon = 'input-caps-on-symbolic' if not ctx.capslock_on else 'window-close'
    ntfy.send_notification(message, icon, 'low', False)
    return C("CapsLock")


def toggle_and_show_numlock_state(ctx: KeyContext):
    """
    Show the (coming) state of NumLock LED in a notification pop-up dialog.
    Then return the NumLock key combo to toggle the NumLock LED state.

    Only shows notification and toggles if 'Forced Numpad' pref is disabled.
    Like the isNumlockClearKey() function, returns Escape combo if 'Forced
    Numpad' feature is enabled. 'Forced Numpad' must be disabled to use
    NumLock key normally and see the notifications.

    No need to return inner closure because not used in conditionals.
    Do not use () to 'call' the function from output macro. Not needed.

    Example usage:
    C("NumLock"): toggle_and_show_numlock_state, # Toggle NumLock, show notification
    """

    if cnfg.forced_numpad:
        debug(f'Force Numpad is ON: NumLock key is "Clear" (sends Escape)')
        return C("Esc")
    else:
        # Logic reversed because notification is constructed before combo is returned.
        message = 'NumLock is ON' if not ctx.numlock_on else 'NumLock is OFF'
        icon = 'input-num-on' if not ctx.numlock_on else 'window-close'
        ntfy.send_notification(message, icon, 'low', False)
        return C("NumLock")



# Suggested location for adding custom functions for personal use.
###################################################################################################
###  SLICE_MARK_START: user_custom_functions  ###  EDITS OUTSIDE THESE MARKS WILL BE LOST ON UPGRADE



###  SLICE_MARK_END: user_custom_functions  ###  EDITS OUTSIDE THESE MARKS WILL BE LOST ON UPGRADE
###################################################################################################



###################################  MULTI-TAP  ####################################
###                                                                              ###
###                                                                              ###
###    ███    ███ ██    ██ ██      ████████ ██       ████████  █████  ██████     ###
###    ████  ████ ██    ██ ██         ██    ██          ██    ██   ██ ██   ██    ###
###    ██ ████ ██ ██    ██ ██         ██    ██ █████    ██    ███████ ██████     ###
###    ██  ██  ██ ██    ██ ██         ██    ██          ██    ██   ██ ██         ###
###    ██      ██  ██████  ███████    ██    ██          ██    ██   ██ ██         ###
###                                                                              ###
###                                                                              ###
####################################################################################
# Functions to support proper asyncio time-based multi-tap actions, without
# blocking the single-tap usage of the same combo (unless desired).
#
# Until this EXPERIMENTAL feature moves into the keymapper, the API function
# `multitap_config()` will need to be called from a section lower down, like
# the "user_apps" editable slice, if user wants custom multi-tap timings.


# Multi-tap configuration storage
_MULTITAP_CONFIG = {
    'tap_interval': 0.25,     # Default: 250ms between taps
    'min_tap_delay': 0.07,    # Default: 70ms repeat protection
}


def get_output():
    """Get the main keymapper's output instance"""
    try:
        # Access the transform module's _output at runtime
        if 'xwaykeyz.transform' in sys.modules:
            transform_module = sys.modules['xwaykeyz.transform']
            if hasattr(transform_module, '_output'):
                debug("## multitap: Using main keymapper's _output instance")
                return transform_module._output
    except Exception as e:
        debug(f"## multitap: Error accessing output: {e}")
    return None


def process_multitap_command(command, ctx):
    """Simplified recursive command processor based on handle_commands logic"""
    debug(f"## multitap: Processing command: {type(command)}")

    if callable(command):
        # Handle functions like ST(), notify_context, etc.
        cmd_param_cnt = len(inspect.signature(command).parameters)
        debug(f"## multitap: Callable with {cmd_param_cnt} parameters")

        if cmd_param_cnt == 0:
            result = command()
        else:
            result = command(ctx)

        debug(f"## multitap: Callable returned: {type(result)}")

        # Recursively process the result
        if result is not None:
            process_multitap_command(result, ctx)

    elif isinstance(command, list):
        # Recursively process each item in the list
        debug(f"## multitap: Processing list with {len(command)} items")
        for i, item in enumerate(command):
            debug(f"## multitap: Processing list item {i+1}: {type(item)}")
            process_multitap_command(item, ctx)

    else:
        # Handle direct objects (Combo, Key, etc.)
        output = get_output()
        if output and hasattr(command, '__class__'):
            class_name = command.__class__.__name__
            debug(f"## multitap: Direct object class: {class_name}")

            if 'Combo' in class_name:
                output.send_combo(command)
                debug(f"## multitap: Sent Combo object")
            elif 'Key' in class_name:
                output.send_key(command)
                debug(f"## multitap: Sent Key object")
            elif command is not None:
                debug(f"## multitap: Unknown command type: {class_name}")
        elif not output:
            debug(f"## multitap: No output available for command: {type(command)}")
        else:
            debug(f"## multitap: Command has no __class__: {command}")


# Per-combo state tracking using action tuple as key
tap_states: Dict[tuple, Dict[str, Any]] = {}

event_loop: Optional[asyncio.AbstractEventLoop] = None


def get_loop() -> Optional[asyncio.AbstractEventLoop]:
    global event_loop
    if event_loop is None or event_loop.is_closed():
        try:
            event_loop = asyncio.get_running_loop()
        except RuntimeError:
            event_loop = None
    return event_loop


def multitap_config(tap_interval=None, min_tap_delay=None):
    """
    Configure global multi-tap timing settings.

    Args:
        tap_interval: Maximum time between taps in seconds (0.15 to 1.5)
        min_tap_delay: Minimum time between taps to avoid repeats (0.05 to 0.5)

    Example:
        multitap_config(
            tap_interval=0.3,    # 300ms between taps
            min_tap_delay=0.10   # 100ms repeat protection
        )
    """
    global _MULTITAP_CONFIG

    if tap_interval is not None:
        if isinstance(tap_interval, (int, float)) and 0.15 <= tap_interval <= 1.5:
            _MULTITAP_CONFIG['tap_interval'] = float(tap_interval)
            debug(f"## multitap_config: Set tap_interval to {tap_interval}s")
        else:
            debug(f"## multitap_config: Invalid tap_interval {tap_interval}, must be 0.15-1.5 sec")

    if min_tap_delay is not None:
        if isinstance(min_tap_delay, (int, float)) and 0.05 <= min_tap_delay <= 0.5:
            _MULTITAP_CONFIG['min_tap_delay'] = float(min_tap_delay)
            debug(f"## multitap_config: Set min_tap_delay to {min_tap_delay}s")
        else:
            debug(f"## multitap_config: Invalid min_tap_delay {min_tap_delay}, must be 0.05-0.5 sec")

    # Ensure ignore time is less than interval time
    if _MULTITAP_CONFIG['min_tap_delay'] >= _MULTITAP_CONFIG['tap_interval']:
        original_delay = _MULTITAP_CONFIG['min_tap_delay']
        _MULTITAP_CONFIG['min_tap_delay'] = _MULTITAP_CONFIG['tap_interval'] * 0.25
        debug(f"## multitap_config: min_tap_delay ({original_delay}s) >= tap_interval, "
                f"adjusted to {_MULTITAP_CONFIG['min_tap_delay']:.3f}s")


def isMultiTap( tap_1_action: Optional[Callable] = None,
                tap_2_action: Optional[Callable] = None,
                tap_3_action: Optional[Callable] = None,
                tap_4_action: Optional[Callable] = None,
                tap_5_action: Optional[Callable] = None,
                tap_interval: float = None,
                min_tap_delay: float = None) -> Callable:
    """
    Multi-tap handler that supports 1-5 taps with asyncio.

    Args:
        tap_1_action: Function to call on single tap (can be None to block single-tap)
        tap_2_action: Function to call on double tap
        tap_3_action: Function to call on triple tap
        tap_4_action: Function to call on quadruple tap
        tap_5_action: Function to call on quintuple tap
        tap_interval: Max time between taps (None = use global config)
        min_tap_delay: Min time between taps to avoid key repeat (None = use global config)

    Returns:
        Function that handles the tap detection
    """

    # Use global config values if not explicitly provided
    if tap_interval is None:
        tap_interval = _MULTITAP_CONFIG['tap_interval']
    if min_tap_delay is None:
        min_tap_delay = _MULTITAP_CONFIG['min_tap_delay']

    # Use action tuple as unique identifier, converting lists to tuples for hashability
    def make_hashable(action):
        if isinstance(action, list):
            return tuple(make_hashable(item) for item in action)
        return action

    action_key = (
        make_hashable(tap_1_action),
        make_hashable(tap_2_action),
        make_hashable(tap_3_action),
        make_hashable(tap_4_action),
        make_hashable(tap_5_action)
    )

    def execute_action_for_tap_count(   tap_count: int,
                                        captured_ctx,
                                        tap_1_action,
                                        tap_2_action,
                                        tap_3_action,
                                        tap_4_action,
                                        tap_5_action):
        """Execute the appropriate action based on tap count."""
        actions = {
            1: tap_1_action,
            2: tap_2_action,
            3: tap_3_action,
            4: tap_4_action,
            5: tap_5_action
        }

        action = actions.get(tap_count)
        if action is not None:
            try:
                debug(f"## isMultiTap: Executing {tap_count}-tap action for {action_key}")
                process_multitap_command(action, captured_ctx)
                debug(f"## isMultiTap: Completed {tap_count}-tap action for {action_key}")
            except Exception as e:
                debug(f"## isMultiTap: Error executing {tap_count}-tap action: {e}")
        else:
            debug(f"## isMultiTap: No action defined for {tap_count} taps on {action_key}")

    def finalize_taps(action_key: tuple, captured_ctx):
        """Called when tap sequence is finalized."""
        if action_key in tap_states:
            state = tap_states[action_key]
            tap_count = state['count']
            debug(f"## isMultiTap: Finalizing {tap_count} taps for {action_key}")

            # Get the actions before cleaning up state
            stored_tap_1_action = state['tap_1_action']
            stored_tap_2_action = state['tap_2_action']
            stored_tap_3_action = state['tap_3_action']
            stored_tap_4_action = state['tap_4_action']
            stored_tap_5_action = state['tap_5_action']

            # Clean up state
            del tap_states[action_key]

            # Execute appropriate action with captured context
            execute_action_for_tap_count(   tap_count,
                                            captured_ctx,
                                            stored_tap_1_action,
                                            stored_tap_2_action,
                                            stored_tap_3_action,
                                            stored_tap_4_action,
                                            stored_tap_5_action)

    def _isMultiTap(ctx) -> None:
        loop = get_loop()
        if loop is None:
            debug(f"## isMultiTap: No event loop available for {action_key}")
            return None

        current_time = time.time()

        # Initialize or get existing state
        if action_key not in tap_states:
            tap_states[action_key] = {
                'count': 0,
                'last_tap_time': 0.0,
                'finalize_handle': None,
                'captured_ctx': ctx,
                # Store the individual actions in the state
                'tap_1_action': tap_1_action,
                'tap_2_action': tap_2_action,
                'tap_3_action': tap_3_action,
                'tap_4_action': tap_4_action,
                'tap_5_action': tap_5_action,
            }

        state = tap_states[action_key]
        time_since_last = current_time - state['last_tap_time']

        # Check if this tap is too soon (key repeat protection)
        if state['count'] > 0 and time_since_last < min_tap_delay:
            debug(  f"## isMultiTap: Ignoring repeat for {action_key} "
                    f"(too soon: {time_since_last:.3f}s)")
            return None

        # Check if this tap is too late (start new sequence)
        if state['count'] > 0 and time_since_last >= tap_interval:
            debug(  f"## isMultiTap: Too late for {action_key} "
                    f"(gap: {time_since_last:.3f}s), finalizing previous")
            # Finalize the previous sequence with its captured context
            finalize_taps(action_key, state['captured_ctx'])
            # Start new sequence with current context
            tap_states[action_key] = {
                'count': 0,
                'last_tap_time': 0.0,
                'finalize_handle': None,
                'captured_ctx': ctx,
                # Store the individual actions in the state
                'tap_1_action': tap_1_action,
                'tap_2_action': tap_2_action,
                'tap_3_action': tap_3_action,
                'tap_4_action': tap_4_action,
                'tap_5_action': tap_5_action,
            }
            state = tap_states[action_key]

        # Cancel any pending finalization
        finalize_handle: Optional[asyncio.Handle] = state['finalize_handle']
        if finalize_handle is not None:
            finalize_handle.cancel()
            state['finalize_handle'] = None

        # Increment tap count
        state['count'] += 1
        state['last_tap_time'] = current_time

        debug(f"## isMultiTap: Tap #{state['count']} for {action_key}")

        # If we've exceeded max taps (5), ignore subsequent taps
        if state['count'] > 5:
            debug(f"## isMultiTap: Ignoring tap beyond maximum (tap #{state['count']})")
            return None

        # Schedule finalization after the interval for all tap counts
        if state['tap_1_action'] or state['count'] > 1:
            captured_ctx = state['captured_ctx']
            handle: asyncio.Handle = loop.call_later(
                tap_interval,
                lambda: finalize_taps(action_key, captured_ctx)  # Pass captured context
            )
            state['finalize_handle'] = handle
            debug(f"## isMultiTap: Scheduled finalization for {action_key} in {tap_interval}s")

        # Return None since we're handling actions asynchronously
        return None

    return _isMultiTap



#################################  MODMAPS  ####################################
###                                                                          ###
###                                                                          ###
###      ███    ███  ██████  ██████  ███    ███  █████  ██████  ███████      ###
###      ████  ████ ██    ██ ██   ██ ████  ████ ██   ██ ██   ██ ██           ###
###      ██ ████ ██ ██    ██ ██   ██ ██ ████ ██ ███████ ██████  ███████      ###
###      ██  ██  ██ ██    ██ ██   ██ ██  ██  ██ ██   ██ ██           ██      ###
###      ██      ██  ██████  ██████  ██      ██ ██   ██ ██      ███████      ###
###                                                                          ###
###                                                                          ###
################################################################################
### Modmaps turn a key into a different key as long as the modmap is active
### The modified key can be used in shortcut combos as the new key


# DO NOT REMOVE THIS MODMAP AND KEYMAP!
# Special modmap to trigger the evaluation of the keyboard type when
# any modifier key is pressed
modmap("Trigger Modmap: Keyboard Type", {
    # This modmap must have all modifier keys inside it, so they will
    # all trigger the re-evaluation of the keyboard type.
    # The accompanying keymap can be empty and still accomplish
    # the same purpose of triggering a re-evaluation of the
    # keyboard type when any non-modifier key is pressed.
    Key.LEFT_META:              Key.LEFT_META,
    Key.RIGHT_META:             Key.RIGHT_META,
    Key.LEFT_ALT:               Key.LEFT_ALT,
    Key.RIGHT_ALT:              Key.RIGHT_ALT,
    Key.LEFT_CTRL:              Key.LEFT_CTRL,
    Key.RIGHT_CTRL:             Key.RIGHT_CTRL,
    Key.LEFT_SHIFT:             Key.LEFT_SHIFT,
    Key.RIGHT_SHIFT:            Key.RIGHT_SHIFT,
}, when = lambda ctx: getKBtype()(ctx) )    # THIS CONDITIONAL MUST NEVER EVALUATE TO TRUE!
# Special keymap to trigger the evaluation of the keyboard type when
# any non-modifier key is pressed
keymap("Trigger Keymap: Keyboard Type", {
    # Nothing needed here.
}, when = lambda ctx: getKBtype()(ctx) )


def get_iEF2_context():
    """Reset Enter-to-rename state variable to True, if the current
        application does not match on the file manager app class string"""
    def _get_iEF2_context(ctx: KeyContext):
        global _enter_is_F2, _enter_F2_last_app_class
        if not _enter_is_F2 and not matchProps(clas=filemanagerStr)(ctx):
            debug("Resetting Enter-to-rename state variable to True.")
            _enter_is_F2 = True
            _enter_F2_last_app_class = None

        return False

    return _get_iEF2_context


# DO NOT REMOVE THIS MODMAP AND KEYMAP!
# Special modmap to trigger the evaluation of the window context when
# any modifier key is pressed
modmap("Trigger Modmap: Enter-to-Rename Context", {
    # This modmap must have all modifier keys inside it, so they will
    # all trigger the re-evaluation of the window context.
    # The accompanying keymap can be empty and still accomplish
    # the same purpose of triggering a re-evaluation of the
    # window context when any non-modifier key is pressed.
    Key.LEFT_META:              Key.LEFT_META,
    Key.RIGHT_META:             Key.RIGHT_META,
    Key.LEFT_ALT:               Key.LEFT_ALT,
    Key.RIGHT_ALT:              Key.RIGHT_ALT,
    Key.LEFT_CTRL:              Key.LEFT_CTRL,
    Key.RIGHT_CTRL:             Key.RIGHT_CTRL,
    Key.LEFT_SHIFT:             Key.LEFT_SHIFT,
    Key.RIGHT_SHIFT:            Key.RIGHT_SHIFT,
}, when = lambda ctx: get_iEF2_context()(ctx) )    # THIS CONDITIONAL MUST NEVER EVALUATE TO TRUE!
# Special keymap to trigger the evaluation of the window context when
# any non-modifier key is pressed
keymap("Trigger Keymap: Enter-to-Rename Context", {
    # Nothing needed here.
}, when = lambda ctx: get_iEF2_context()(ctx) )


modmap("Cond modmap - Media Arrows Fix",{
    # Fix arrow keys with media functions instead of PgUp/PgDn/Home/End
    Key.PLAYPAUSE:              Key.PAGE_UP,
    Key.STOPCD:                 Key.PAGE_DOWN,
    Key.PREVIOUSSONG:           Key.HOME,
    Key.NEXTSONG:               Key.END,
}, when = lambda ctx:
    cnfg.media_arrows_fix and
    cnfg.screen_has_focus and
    matchProps(not_clas=remoteStr)(ctx)
)


###################################################################################################
###  SLICE_MARK_START: exclude_kpad_devs  ###  EDITS OUTSIDE THESE MARKS WILL BE LOST ON UPGRADE

# List of devices to add to the device exclusion list below this slice

exclude_kpad_devs_UserCustom_lst = [
    # Example syntax:
    # 'My Keyboard Device',

]

###  SLICE_MARK_END: exclude_kpad_devs  ###  EDITS OUTSIDE THESE MARKS WILL BE LOST ON UPGRADE
###################################################################################################


# DEPRECATED in favor of simple list:
# # List of devices with keypads to exclude from Forced Numpad and GTK3 fix modmaps
# exclude_kpad_devs_lod = [
#     {devn: 'Razer Razer Naga X'},
#     *exclude_kpad_devs_UserCustom_lod,
# ]

# Ensure the DEPRECATED variable exists and is a list before attempting to access it
# (New users WILL NOT have it in the marked slice above)
exclude_kpad_devs_UserCustom_lod = locals().get('exclude_kpad_devs_UserCustom_lod', [])

# Ensure the NEW variable exists and is a list before attempting to access it
# (Existing users MIGHT NOT have it in the marked slice above)
exclude_kpad_devs_UserCustom_lst = locals().get('exclude_kpad_devs_UserCustom_lod', [])

DEPRECATED_exclude_kpad_devs_UserCustom_lst = [
    device['devn'] for device in exclude_kpad_devs_UserCustom_lod
    if isinstance(exclude_kpad_devs_UserCustom_lod, list)
]

# List of devices with keypads to exclude from Forced Numpad and GTK3 fix modmaps
exclude_kpad_devs_lst = [
    'Razer Razer Naga X',
    *DEPRECATED_exclude_kpad_devs_UserCustom_lst,
    *exclude_kpad_devs_UserCustom_lst,
]
exclude_kpad_devs_Str = toRgxStr(exclude_kpad_devs_lst)

modmap("Cond modmap - Forced Numpad feature",{
    # Make numpad be a numpad regardless of Numlock state (like an Apple keyboard in macOS)
    Key.KP1:                    Key.KEY_1,
    Key.KP2:                    Key.KEY_2,
    Key.KP3:                    Key.KEY_3,
    Key.KP4:                    Key.KEY_4,
    Key.KP5:                    Key.KEY_5,
    Key.KP6:                    Key.KEY_6,
    Key.KP7:                    Key.KEY_7,
    Key.KP8:                    Key.KEY_8,
    Key.KP9:                    Key.KEY_9,
    Key.KP0:                    Key.KEY_0,
    Key.KPDOT:                  Key.DOT,
    Key.KPENTER:                Key.ENTER,
}, when = lambda ctx:
    cnfg.forced_numpad and
    cnfg.screen_has_focus and
    matchProps(not_devn=exclude_kpad_devs_Str)(ctx) and
    matchProps(not_clas=remoteStr)(ctx)
)


modmap("Cond modmap - GTK3 numpad nav keys fix", {
    # Make numpad nav keys work correctly in GTK3 apps
    # Key.KP5:                    Key.X,                # GTK3 numpad fix - TEST TO SEE IF WORKING
    # Numpad PgUp/PgDn/Home/End keys
    Key.KP9:                    Key.PAGE_UP,
    Key.KP3:                    Key.PAGE_DOWN,
    Key.KP7:                    Key.HOME,
    Key.KP1:                    Key.END,
    # Numpad arrow keys
    Key.KP8:                    Key.UP,
    Key.KP2:                    Key.DOWN,
    Key.KP4:                    Key.LEFT,
    Key.KP6:                    Key.RIGHT,
    # Numpad Insert/Delete/Enter keys
    Key.KP0:                    Key.INSERT,
    Key.KPDOT:                  Key.DELETE,
    Key.KPENTER:                Key.ENTER,
}, when = lambda ctx:
    not cnfg.forced_numpad and
    cnfg.screen_has_focus and
    matchProps(numlk=False)(ctx) and
    matchProps(not_devn=exclude_kpad_devs_Str)(ctx) and
    matchProps(not_clas=remoteStr)(ctx)
)


# multipurpose_modmap("Optional Tweaks",
#     # {Key.ENTER:                 [Key.ENTER, Key.RIGHT_CTRL]     # Enter2Cmd
#     # {Key.CAPSLOCK:              [Key.ESC, Key.RIGHT_CTRL]       # Caps2Esc
#     # {Key.LEFT_META:             [Key.ESC, Key.RIGHT_CTRL]       # Caps2Esc - Chromebook
#     {                                                             # Placeholder
# })

multipurpose_modmap("Enter2Cmd", {
    Key.ENTER:                  [Key.ENTER, Key.RIGHT_CTRL]     # Enter2Cmd
}, when = lambda ctx:
    cnfg.Enter2Ent_Cmd and
    cnfg.screen_has_focus and
    matchProps(not_clas=remoteStr)(ctx)
)

multipurpose_modmap("Caps2Esc - not Chromebook kbd", {
    Key.CAPSLOCK:               [Key.ESC, Key.RIGHT_CTRL]       # Caps2Esc - not Chromebook
}, when = lambda ctx:
    cnfg.Caps2Esc_Cmd and
    cnfg.screen_has_focus and
    not isKBtype('Chromebook')(ctx) and
    matchProps(not_clas=remoteStr)(ctx)
)

multipurpose_modmap("Caps2Esc - Chromebook kbd", {
    Key.LEFT_META:               [Key.ESC, Key.RIGHT_CTRL]       # Caps2Esc - Chromebook
}, when = lambda ctx:
    cnfg.Caps2Esc_Cmd and
    cnfg.screen_has_focus and
    isKBtype('Chromebook')(ctx) and
    matchProps(not_clas=remoteStr)(ctx)
)


# THIS IS ALL SUPERCEDED BY THE NEW SOLUTION OF MONITORING THE SYNERGY LOG FILE!
# Fix for avoiding modmapping when using Synergy keyboard/mouse sharing.
# Synergy doesn't set a wm_class, so this may cause issues with other
# applications that also don't set the wm_class.
# Enable only if you use Synergy. (This is only for use with xkeysnail.)
# define_conditional_modmap(lambda wm_class: wm_class == '', {})
###########################
# Suggestion (untested):
# For use with keyszer, to avoid catching GNOME Shell task switcher (which has
# an empty WM_CLASS but sets a WM_NAME):
# modmap("Synergy fix", {}, when = lambda ctx: ctx.wm_class == '' and ctx.wm_name == '')
# If Synergy actually sets a WM_NAME like GNOME Shell does, you'd need to use
# one of these alternatives:
# modmap("Synergy fix", {}, when = lambda ctx: ctx.wm_class == '' and ctx.wm_name == 'SYNERGY_WM_NAME')
# Or:
# modmap("Synergy fix", {}, when = lambda ctx: ctx.wm_class == '' and not ctx.wm_name == 'gnome-shell')
# PROBLEM: When GNOME desktop has focus, it sets no window info at all (no class, no name/title)


# [Global GUI conditional modmaps] Change modifier keys as in xmodmap
modmap("Cond modmap - GUI - Caps2Cmd - not Cbk kdb", {
    Key.CAPSLOCK:               Key.RIGHT_CTRL,                 # Caps2Cmd
}, when = lambda ctx:
    cnfg.Caps2Cmd and
    cnfg.screen_has_focus and
    not isKBtype('Chromebook')(ctx) and
    matchProps(not_clas=terms_and_remotes_Str)(ctx)
)
modmap("Cond modmap - GUI - Caps2Cmd - Cbk kdb", {
    Key.LEFT_META:              Key.RIGHT_CTRL,                 # Caps2Cmd - Chromebook
}, when = lambda ctx:
    cnfg.Caps2Cmd and
    cnfg.screen_has_focus and
    isKBtype('Chromebook')(ctx) and
    matchProps(not_clas=terms_and_remotes_Str)(ctx)
)
modmap("Cond modmap - GUI - IBM kbd - multi_lang OFF", {
    # - IBM
    Key.RIGHT_ALT:              Key.RIGHT_CTRL,                 # IBM - Multi-language (Remove)
    Key.RIGHT_CTRL:             Key.RIGHT_ALT,                  # IBM - Multi-language (Remove)
}, when = lambda ctx:
    not cnfg.multi_lang and
    cnfg.screen_has_focus and
    isKBtype('IBM', map='mmap GUI IBM ML-OFF')(ctx) and
    matchProps(not_clas=terms_and_remotes_Str)(ctx)
)
modmap("Cond modmap - GUI - IBM kbd", {
    # - IBM
    Key.CAPSLOCK:               Key.LEFT_META,                  # IBM
    Key.LEFT_CTRL:              Key.LEFT_ALT,                   # IBM
    Key.LEFT_ALT:               Key.RIGHT_CTRL,                 # IBM
}, when = lambda ctx:
    cnfg.screen_has_focus and
    isKBtype('IBM', map='mmap GUI IBM')(ctx) and
    matchProps(not_clas=terms_and_remotes_Str)(ctx)
)
modmap("Cond modmap - GUI - Cbk kbd - multi_lang OFF", {
    # - Chromebook
    Key.RIGHT_ALT:              Key.RIGHT_CTRL,                 # Chromebook - Multi-language (Remove)
    Key.RIGHT_CTRL:             Key.RIGHT_ALT,                  # Chromebook - Multi-language (Remove)
}, when = lambda ctx:
    not cnfg.multi_lang and
    cnfg.screen_has_focus and
    isKBtype('Chromebook', map='mmap GUI Cbk ML-OFF')(ctx) and
    matchProps(not_clas=terms_and_remotes_Str)(ctx)
)
modmap("Cond modmap - GUI - Cbk kbd", {
    # - Chromebook
    Key.LEFT_CTRL:              Key.LEFT_ALT,                   # Chromebook
    Key.LEFT_ALT:               Key.RIGHT_CTRL,                 # Chromebook
}, when = lambda ctx:
    cnfg.screen_has_focus and
    isKBtype('Chromebook', map='mmap GUI Cbk')(ctx) and
    matchProps(not_clas=terms_and_remotes_Str)(ctx)
)
modmap("Cond modmap - GUI - Win kbd - multi_lang OFF", {
    # - Default Mac/Win
    # - Default Win
    Key.RIGHT_ALT:              Key.RIGHT_CTRL,                 # WinMac - Multi-language (Remove)
    Key.RIGHT_META:             Key.RIGHT_ALT,                  # WinMac - Multi-language (Remove)
    Key.RIGHT_CTRL:             Key.RIGHT_META,                 # WinMac - Multi-language (Remove)
}, when = lambda ctx:
    not cnfg.multi_lang and
    cnfg.screen_has_focus and
    isKBtype('Windows', map='mmap GUI Win ML-OFF')(ctx) and
    matchProps(not_clas=terms_and_remotes_Str)(ctx)
)
modmap("Cond modmap - GUI - Win kbd", {
    # - Default Mac/Win
    # - Default Win
    Key.LEFT_CTRL:              Key.LEFT_META,                  # WinMac
    Key.LEFT_META:              Key.LEFT_ALT,                   # WinMac
    Key.LEFT_ALT:               Key.RIGHT_CTRL,                 # WinMac
}, when = lambda ctx:
    cnfg.screen_has_focus and
    isKBtype('Windows', map='mmap GUI Win')(ctx) and
    matchProps(not_clas=terms_and_remotes_Str)(ctx)
)
modmap("Cond modmap - GUI - Mac kbd - multi_lang OFF", {
    # - Mac Only
    Key.RIGHT_META:             Key.RIGHT_CTRL,                 # Mac - Multi-language (Remove)
    Key.RIGHT_CTRL:             Key.RIGHT_META,                 # Mac - Multi-language (Remove)
}, when = lambda ctx:
    not cnfg.multi_lang and
    cnfg.screen_has_focus and
    isKBtype('Apple', map='mmap GUI Apple ML-OFF')(ctx) and
    matchProps(not_clas=terms_and_remotes_Str)(ctx)
)
modmap("Cond modmap - GUI - Mac kbd", {
    # - Mac Only
    Key.LEFT_CTRL:              Key.LEFT_META,                  # Mac
    Key.LEFT_META:              Key.RIGHT_CTRL,                 # Mac
}, when = lambda ctx:
    cnfg.screen_has_focus and
    isKBtype('Apple', map='mmap GUI Apple')(ctx) and
    matchProps(not_clas=terms_and_remotes_Str)(ctx)
)


# [Global Terminals conditional modmaps] Change modifier keys in certain applications
modmap("Cond modmap - Terms - IBM kbd - multi_lang OFF", {
    # - IBM - Multi-language
    Key.RIGHT_ALT:              Key.RIGHT_CTRL,                 # IBM - Multi-language (Remove)
}, when = lambda ctx:
    not cnfg.multi_lang and
    cnfg.screen_has_focus and
    isKBtype('IBM', map='mmap terms IBM ML-OFF')(ctx) and
    matchProps(clas=termStr)(ctx)
)
modmap("Cond modmap - Terms - IBM kbd", {
    # - IBM
    Key.CAPSLOCK:               Key.LEFT_ALT,                   # IBM
    # Left Ctrl stays Left Ctrl
    Key.LEFT_ALT:               Key.RIGHT_CTRL,                 # IBM
    # Right Meta does not exist on IBM keyboards
    Key.RIGHT_CTRL:             Key.RIGHT_ALT,                  # IBM
}, when = lambda ctx:
    cnfg.screen_has_focus and
    isKBtype('IBM', map='mmap terms IBM')(ctx) and
    matchProps(clas=termStr)(ctx)
)
modmap("Cond modmap - Terms - Cbk kbd - multi_lang OFF", {
    # - Chromebook
    Key.RIGHT_ALT:              Key.RIGHT_CTRL,                 # Chromebook - Multi-language (Remove)
}, when = lambda ctx:
    not cnfg.multi_lang and
    cnfg.screen_has_focus and
    isKBtype('Chromebook', map='mmap terms Cbk ML-OFF')(ctx) and
    matchProps(clas=termStr)(ctx)
)
modmap("Cond modmap - Terms - Cbk kbd", {
    # - Chromebook
    # Left Ctrl Stays Left Ctrl
    Key.LEFT_META:              Key.LEFT_ALT,                   # Chromebook
    Key.LEFT_ALT:               Key.RIGHT_CTRL,                 # Chromebook
    # Right Meta does not exist on chromebooks
    Key.RIGHT_CTRL:             Key.RIGHT_ALT,                  # Chromebook
}, when = lambda ctx:
    cnfg.screen_has_focus and
    isKBtype('Chromebook', map='mmap terms Cbk')(ctx) and
    matchProps(clas=termStr)(ctx)
)
modmap("Cond modmap - Terms - Win kbd - multi_lang OFF", {
    # - Default Mac/Win
    # - Default Win
    Key.RIGHT_ALT:              Key.RIGHT_CTRL,                 # WinMac - Multi-language (Remove)
    Key.RIGHT_META:             Key.RIGHT_ALT,                  # WinMac - Multi-language (Remove)
    Key.RIGHT_CTRL:             Key.LEFT_CTRL,                  # WinMac - Multi-language (Remove)
}, when = lambda ctx:
    not cnfg.multi_lang and
    cnfg.screen_has_focus and
    isKBtype('Windows', map='mmap terms Win ML-OFF')(ctx) and
    matchProps(clas=termStr)(ctx)
)
modmap("Cond modmap - Terms - Win kbd", {
    # - Default Mac/Win
    # - Default Win
    Key.LEFT_CTRL:              Key.LEFT_CTRL,                  # WinMac
    Key.LEFT_META:              Key.LEFT_ALT,                   # WinMac
    Key.LEFT_ALT:               Key.RIGHT_CTRL,                 # WinMac
}, when = lambda ctx:
    cnfg.screen_has_focus and
    isKBtype('Windows', map='mmap terms Win')(ctx) and
    matchProps(clas=termStr)(ctx)
)
modmap("Cond modmap - Terms - Mac kbd - multi_lang OFF", {
    # - Mac Only
    # Left Ctrl Stays Left Ctrl
    Key.RIGHT_META:             Key.RIGHT_CTRL,                 # Mac - Multi-language (Remove)
    Key.RIGHT_CTRL:             Key.LEFT_CTRL,                  # Mac - Multi-language (Remove)
}, when = lambda ctx:
    not cnfg.multi_lang and
    cnfg.screen_has_focus and
    isKBtype('Apple', map='mmap terms Apple ML-OFF')(ctx) and
    matchProps(clas=termStr)(ctx)
)
modmap("Cond modmap - Terms - Mac kbd", {
    # - Mac Only
    # Left Ctrl Stays Left Ctrl
    Key.LEFT_CTRL:              Key.LEFT_CTRL,                  # Mac (self-modmap)
    Key.LEFT_ALT:               Key.LEFT_ALT,                   # Mac (self-modmap)
    Key.LEFT_META:              Key.RIGHT_CTRL,                 # Mac
    Key.RIGHT_ALT:              Key.RIGHT_ALT,                  # Mac (self-modmap)
}, when = lambda ctx:
    cnfg.screen_has_focus and
    isKBtype('Apple', map='mmap terms Apple')(ctx) and
    matchProps(clas=termStr)(ctx)
)



# Suggested location for adding custom modmaps for personal use.
###################################################################################################
###  SLICE_MARK_START: user_custom_modmaps  ###  EDITS OUTSIDE THESE MARKS WILL BE LOST ON UPGRADE



###  SLICE_MARK_END: user_custom_modmaps  ###  EDITS OUTSIDE THESE MARKS WILL BE LOST ON UPGRADE
###################################################################################################



##########################  FORCED NUMPAD  ############################
###                                                                 ###
###                                                                 ###
###      ███    ██ ██    ██ ███    ███ ██████   █████  ██████       ###
###      ████   ██ ██    ██ ████  ████ ██   ██ ██   ██ ██   ██      ###
###      ██ ██  ██ ██    ██ ██ ████ ██ ██████  ███████ ██   ██      ###
###      ██  ██ ██ ██    ██ ██  ██  ██ ██      ██   ██ ██   ██      ###
###      ██   ████  ██████  ██      ██ ██      ██   ██ ██████       ###
###                                                                 ###
###                                                                 ###
#######################################################################

# Force the numpad to always be a numpad, like a Mac keyboard on macOS
# Numlock key becomes "Clear" key for use with calculator (sends Escape)
# Toggle feature on/off with Option+Numlock (Fn+Numlock might work on
# Apple keyboards that have Fn key)


def toggle_forced_numpad():
    """Toggle the Forced Numpad feature on or off."""
    cnfg.forced_numpad = not cnfg.forced_numpad
    cnfg.save_settings()
    ntfy.forced_numpad(cnfg.forced_numpad)


def isNumlockClearKey():
    """NumLock key is Clear (Esc) if Forced Numpad feature is enabled."""
    return C("Esc") if cnfg.forced_numpad else C("Numlock")



###########################  OPTSPECIALCHARS  ##############################
###                                                                      ###
###                                                                      ###
###       ██████  ██████  ████████ ███████ ██████  ███████  ██████       ###
###      ██    ██ ██   ██    ██    ██      ██   ██ ██      ██            ###
###      ██    ██ ██████     ██    ███████ ██████  █████   ██            ###
###      ██    ██ ██         ██         ██ ██      ██      ██            ###
###       ██████  ██         ██    ███████ ██      ███████  ██████       ###
###                                                                      ###
###                                                                      ###
############################################################################

###########   START OF OPTION KEY SPECIAL CHARACTER ENTRY SCHEME    #############
#################################################################################
### Full list of special characters on Apple US and ABC Extended keyboard layouts:
### https://github.org/RedBearAK/optspecialchars


def apple_logo_alert():
    """Show a notification about needing Baskerville Old Face font for displaying Apple logo"""
    if applelogoalert_enabled:
        ntfy.apple_logo()



######################################################################################
###                                                                                ###
###                                                                                ###
###      ██████  ███████  █████  ██████      ██   ██ ███████ ██    ██ ███████      ###
###      ██   ██ ██      ██   ██ ██   ██     ██  ██  ██       ██  ██  ██           ###
###      ██   ██ █████   ███████ ██   ██     █████   █████     ████   ███████      ###
###      ██   ██ ██      ██   ██ ██   ██     ██  ██  ██         ██         ██      ###
###      ██████  ███████ ██   ██ ██████      ██   ██ ███████    ██    ███████      ###
###                                                                                ###
###                                                                                ###
######################################################################################

# variables to store dead keys diacritic accent character Unicode address
ac_Chr_main = None
_ac_Chr_copy = None


def set_dead_key_char(hex_unicode_addr):
    """
    Set the value of the dead keys accent character
    variable, and its alternate. Does not clear the
    value of the alternate variable if input is
    falsy (such as None or 0x0000 or 0). This allows
    the value to be used after the tripwire keymap
    clears the main variable value.
    """
    def _set_dead_key_char():
        global ac_Chr_main
        global _ac_Chr_copy
        # if hex_unicode_addr is None or hex_unicode_addr == 0x0000:
        #     pass
        # else:
        if hex_unicode_addr:
            _ac_Chr_copy = hex_unicode_addr
        ac_Chr_main = hex_unicode_addr
    #
    return _set_dead_key_char


def get_dead_key_char():
    """Get the value of the alternate dead key accent character
        variable, and print/type the resulting Unicode character."""
    def _get_dead_key_char():
        global _ac_Chr_copy
        return UC(_ac_Chr_copy)
    #
    return _get_dead_key_char


def setDK(*args, **kwargs):
    """wrapper for `set_dead_key_char` function, to provide shorter name"""
    return set_dead_key_char(*args, **kwargs)


def getDK():
    """wrapper for `get_dead_key_char` function, to provide shorter name"""
    return get_dead_key_char()


# setDK = set_dead_key_char
# getDK = get_dead_key_char

deadkeys_ABC = [
    # Dead keys on ABC Extended keyboard layout (25, plus substitutes for problematic chars)
    0x0060,                     # Dead Keys Accent: Grave
    0x02C6,                     # Dead Keys Accent: Circumflex
    0x02D9,                     # Dead Keys Accent: Dot Above
    0x00B4,                     # Dead Keys Accent: Acute

    ###  Combining Double Grave has issues (spacing behavior) - substituting {U+02F5}
    0x030F,                     # Dead Keys Accent: Combining Double Grave
    ###  Substitute for Double Grave: Modifier Letter Middle Double Grave Accent
    0x02F5,                     # Dead Keys Accent: Double Grave - substitute for {U+030F}

    0x00A8,                     # Dead Keys Accent: Umlaut/Diaeresis
    0x02BC,                     # Dead Keys Accent: Apostrophe/Horn
    0x002C,                     # Dead Keys Accent: Comma Below
    0x00AF,                     # Dead Keys Accent: Macron/Line Above

    ###  Combining Inverted Breve has issues (spacing behavior) - substituting {U+1D16}
    0x0311,                     # Dead Keys Accent: Combining Inverted Breve
    ###  Substitute for Inverted Breve: Latin Small Letter Top Half O
    0x1D16,                     # Dead Keys Accent: Inverted Breve - substitute for {U+0311}

    ###  Combining Tilde Below has issues (spacing behavior) - substituting {U+02F7}
    0x0330,                     # Dead Keys Accent: Combining Tilde Below
    ###  Substitute for Tilde Below: Modifier Letter Low Tilde

    0x02F7,                     # Dead Keys Accent: Tilde Below
    0x2038,                     # Dead Keys Accent: Caret/Circumflex Below
    0x02CD,                     # Dead Keys Accent: Low Macron/Line Below
    0x02DD,                     # Dead Keys Accent: Double Acute
    0x02DA,                     # Dead Keys Accent: Ring Above
    0x002D,                     # Dead Keys Accent: Stroke/Hyphen-Minus
    0x2116,                     # Dead Keys Accent: Numero Sign
    0x02C0,                     # Dead Keys Accent: Hook Above/Glottal Stop
    0x002E,                     # Dead Keys Accent: Dot Below
    0x00B8,                     # Dead Keys Accent: Cedilla/Cedille
    0x02C7,                     # Dead Keys Accent: Caron/hacek
    0x02D8,                     # Dead Keys Accent: Breve
    0x02DC,                     # Dead Keys Accent: Tilde
    0x02DB,                     # Dead Keys Accent: Ogonek
    0x0294,                     # Dead Keys Accent: Hook
]

deadkeys_US = [
    # Dead keys on standard US keyboard layout (5)
    0x0060,                     # Dead Keys Accent: Grave
    0x00B4,                     # Dead Keys Accent: Acute
    0x00A8,                     # Dead Keys Accent: Umlaut/Diaeresis
    0x02C6,                     # Dead Keys Accent: Circumflex
    0x02DC,                     # Dead Keys Accent: Tilde
]

# Join the two dead keys lists together
deadkeys_list = []
deadkeys_list.extend(deadkeys_ABC)
deadkeys_list.extend(deadkeys_US)


#####################################
###   DEAD KEYS KEYMAPS - START   ###
#####################################
# Dead Keys conditional keymaps
# only active when the dead key variable matches
# and the layout variable matches (US or ABC)

#################################################
###  DEAD KEYS KEYMAPS - ABC EXTENDED LAYOUT  ###
#################################################

keymap("DK-ABC - Grave", {
    # Option+Grave              {U+0060}
    # Valid keys:
    # a e i n o u v w y
    # A E I N O U V W Y
    C("A"):                     UC(0x00E0),                     # à Latin Small Letter A with Grave
    C("E"):                     UC(0x00E8),                     # è Latin Small Letter E with Grave
    C("I"):                     UC(0x00EC),                     # ì Latin Small Letter I with Grave
    C("N"):                     UC(0x01F9),                     # ǹ Latin Small Letter N with Grave
    C("O"):                     UC(0x00F2),                     # ò Latin Small Letter O with Grave
    C("U"):                     UC(0x00F9),                     # ù Latin Small Letter U with Grave
    C("V"):                     UC(0x01DC),                     # ǜ Latin Small Letter U w/Diaeresis and Grave
    C("W"):                     UC(0x1E81),                     # ẁ Latin Small Letter W with Grave
    C("Y"):                     UC(0x1EF3),                     # ỳ Latin Small Letter Y with Grave
    C("Shift-A"):               UC(0x00C0),                     # À Latin Capital Letter A with Grave
    C("Shift-E"):               UC(0x00C8),                     # È Latin Capital Letter E with Grave
    C("Shift-I"):               UC(0x00CC),                     # Ì Latin Capital Letter I with Grave
    C("Shift-N"):               UC(0x01F8),                     # Ǹ Latin Capital Letter N with Grave
    C("Shift-O"):               UC(0x00D2),                     # Ò Latin Capital Letter O with Grave
    C("Shift-U"):               UC(0x00D9),                     # Ù Latin Capital Letter U with Grave
    C("Shift-V"):               UC(0x01DB),                     # Ǜ Latin Capital Letter U w/Diaeresis and Grave
    C("Shift-W"):               UC(0x1E80),                     # Ẁ Latin Capital Letter W with Grave
    C("Shift-Y"):               UC(0x1EF2),                     # Ỳ Latin Capital Letter Y with Grave
}, when = lambda _: ac_Chr_main == 0x0060 and cnfg.optspec_layout == 'ABC')

keymap("DK-ABC - Circumflex", {
    # Option+6                  {U+02C6}
    # Valid keys:
    # a c e g h i j m n o s u w y z
    # A C E G H I J M N O S U W Y Z
    C("A"):                     UC(0x00E2),                     # â Latin Small Letter A with Circumflex
    C("C"):                     UC(0x0109),                     # ĉ Latin Small Letter C with Circumflex
    C("E"):                     UC(0x00EA),                     # ê Latin Small Letter E with Circumflex
    C("G"):                     UC(0x011D),                     # ĝ Latin Small Letter G with Circumflex
    C("H"):                     UC(0x0125),                     # ĥ Latin Small Letter H with Circumflex
    C("I"):                     UC(0x00EE),                     # î Latin Small Letter I with Circumflex
    C("J"):                     UC(0x0135),                     # ĵ Latin Small Letter J with Circumflex
    C("M"):                    [UC(0x006D),UC(0x0302)],         # m̂ Latin Small Letter M with Circumflex
    C("N"):                    [UC(0x006E),UC(0x0302)],         # n̂ Latin Small Letter N with Circumflex
    C("O"):                     UC(0x00F4),                     # ô Latin Small Letter O with Circumflex
    C("S"):                     UC(0x015D),                     # ŝ Latin Small Letter S with Circumflex
    C("U"):                     UC(0x00FB),                     # û Latin Small Letter U with Circumflex
    C("W"):                     UC(0x0175),                     # ŵ Latin Small Letter W with Circumflex
    C("Y"):                     UC(0x0177),                     # ŷ Latin Small Letter Y with Circumflex
    C("Z"):                     UC(0x1E91),                     # ẑ Latin Small Letter Z with Circumflex
    C("Shift-A"):               UC(0x00C2),                     # Â Latin Capital Letter A with Circumflex
    C("Shift-C"):               UC(0x0108),                     # Ĉ Latin Capital Letter C with Circumflex
    C("Shift-E"):               UC(0x00CA),                     # Ê Latin Capital Letter E with Circumflex
    C("Shift-G"):               UC(0x011C),                     # Ĝ Latin Capital Letter G with Circumflex
    C("Shift-H"):               UC(0x0124),                     # Ĥ Latin Capital Letter H with Circumflex
    C("Shift-I"):               UC(0x00CE),                     # Î Latin Capital Letter I with Circumflex
    C("Shift-J"):               UC(0x0134),                     # Ĵ Latin Capital Letter J with Circumflex
    C("Shift-M"):              [UC(0x004D),UC(0x0302)],         # M̂ Latin Capital Letter M with Circumflex
    C("Shift-N"):              [UC(0x004E),UC(0x0302)],         # N̂ Latin Capital Letter N with Circumflex
    C("Shift-O"):               UC(0x00D4),                     # Ô Latin Capital Letter O with Circumflex
    C("Shift-S"):               UC(0x015C),                     # Ŝ Latin Capital Letter S with Circumflex
    C("Shift-U"):               UC(0x00DB),                     # Û Latin Capital Letter U with Circumflex
    C("Shift-W"):               UC(0x0174),                     # Ŵ Latin Capital Letter W with Circumflex
    C("Shift-Y"):               UC(0x0176),                     # Ŷ Latin Capital Letter Y with Circumflex
    C("Shift-Z"):               UC(0x1E90),                     # Ẑ Latin Capital Letter Z with Circumflex
}, when = lambda _: ac_Chr_main == 0x02C6 and cnfg.optspec_layout == 'ABC')

keymap("DK-ABC - Dot Above", {
    # Option+W                  {U+02D9}
    # Valid keys:
    # a b c d e f g h i m n o p r s t w x y z
    # A B C D E F G H I M N O P R S T W X Y Z
    C("A"):                     UC(0x0227),                     # ȧ Latin Small Letter A with Dot Above
    C("B"):                     UC(0x1E03),                     # ḃ Latin Small Letter B with Dot Above
    C("C"):                     UC(0x010B),                     # ċ Latin Small Letter C with Dot Above
    C("D"):                     UC(0x1E0B),                     # ḋ Latin Small Letter D with Dot Above
    C("E"):                     UC(0x0117),                     # ė Latin Small Letter E with Dot Above
    C("F"):                     UC(0x1E1F),                     # ḟ Latin Small Letter F with Dot Above
    C("G"):                     UC(0x0121),                     # ġ Latin Small Letter G with Dot Above
    C("H"):                     UC(0x1E23),                     # ḣ Latin Small Letter H with Dot Above
    C("I"):                     UC(0x0131),                     # ı Latin Small Letter Dotless I
    C("M"):                     UC(0x1E41),                     # ṁ Latin Small Letter M with Dot Above
    C("N"):                     UC(0x1E45),                     # ṅ Latin Small Letter N with Dot Above
    C("O"):                     UC(0x022F),                     # ȯ Latin Small Letter O with Dot Above
    C("P"):                     UC(0x1E57),                     # ṗ Latin Small Letter P with Dot Above
    C("R"):                     UC(0x1E59),                     # ṙ Latin Small Letter R with Dot Above
    C("S"):                     UC(0x1E61),                     # ṡ Latin Small Letter S with Dot Above
    C("T"):                     UC(0x1E6B),                     # ṫ Latin Small Letter T with Dot Above
    C("W"):                     UC(0x1E87),                     # ẇ Latin Small Letter W with Dot Above
    C("X"):                     UC(0x1E8B),                     # ẋ Latin Small Letter X with Dot Above
    C("Y"):                     UC(0x1E8F),                     # ẏ Latin Small Letter Y with Dot Above
    C("Z"):                     UC(0x017C),                     # ż Latin Small Letter Z with Dot Above
    C("Shift-A"):               UC(0x0226),                     # Ȧ Latin Capital Letter A with Dot Above
    C("Shift-B"):               UC(0x1E02),                     # Ḃ Latin Capital Letter B with Dot Above
    C("Shift-C"):               UC(0x010A),                     # Ċ Latin Capital Letter C with Dot Above
    C("Shift-D"):               UC(0x1E0A),                     # Ḋ Latin Capital Letter D with Dot Above
    C("Shift-E"):               UC(0x0116),                     # Ė Latin Capital Letter E with Dot Above
    C("Shift-F"):               UC(0x1E1E),                     # Ḟ Latin Capital Letter F with Dot Above
    C("Shift-G"):               UC(0x0120),                     # Ġ Latin Capital Letter G with Dot Above
    C("Shift-H"):               UC(0x1E22),                     # Ḣ Latin Capital Letter H with Dot Above
    C("Shift-I"):               UC(0x0130),                     # İ Latin Capital Letter I with Dot Above
    C("Shift-M"):               UC(0x1E40),                     # Ṁ Latin Capital Letter M with Dot Above
    C("Shift-N"):               UC(0x1E44),                     # Ṅ Latin Capital Letter N with Dot Above
    C("Shift-O"):               UC(0x022E),                     # Ȯ Latin Capital Letter O with Dot Above
    C("Shift-P"):               UC(0x1E56),                     # Ṗ Latin Capital Letter P with Dot Above
    C("Shift-R"):               UC(0x1E58),                     # Ṙ Latin Capital Letter R with Dot Above
    C("Shift-S"):               UC(0x1E60),                     # Ṡ Latin Capital Letter S with Dot Above
    C("Shift-T"):               UC(0x1E6A),                     # Ṫ Latin Capital Letter T with Dot Above
    C("Shift-W"):               UC(0x1E86),                     # Ẇ Latin Capital Letter W with Dot Above
    C("Shift-X"):               UC(0x1E8A),                     # Ẋ Latin Capital Letter X with Dot Above
    C("Shift-Y"):               UC(0x1E8E),                     # Ẏ Latin Capital Letter Y with Dot Above
    C("Shift-Z"):               UC(0x017B),                     # Ż Latin Capital Letter Z with Dot Above
}, when = lambda _: ac_Chr_main == 0x02D9 and cnfg.optspec_layout == 'ABC')

keymap("DK-ABC - Acute", {
    # Option+E                  {U+00B4}
    # Valid keys:
    # a c e g i m n o p r s w y z
    # A C E G I M N O P R S W Y Z
    C("A"):                     UC(0x00E1),                     # á Latin Small Letter A with Acute
    C("C"):                     UC(0x0107),                     # ć Latin Small Letter C with Acute
    C("E"):                     UC(0x00E9),                     # é Latin Small Letter E with Acute
    C("G"):                     UC(0x01F5),                     # ǵ Latin Small Letter G with Acute
    C("I"):                     UC(0x00ED),                     # í Latin Small Letter I with Acute
    C("M"):                     UC(0x1E3F),                     # ḿ Latin Small Letter M with Acute
    C("N"):                     UC(0x0144),                     # ń Latin Small Letter N with Acute
    C("O"):                     UC(0x00F3),                     # ó Latin Small Letter O with Acute
    C("P"):                     UC(0x1E55),                     # ṕ Latin Small Letter P with Acute
    C("R"):                     UC(0x0155),                     # ŕ Latin Small Letter R with Acute
    C("S"):                     UC(0x015B),                     # ś Latin Small Letter S with Acute
    C("W"):                     UC(0x1E83),                     # ẃ Latin Small Letter W with Acute
    C("Y"):                     UC(0x00FD),                     # ý Latin Small Letter Y with Acute
    C("Z"):                     UC(0x017A),                     # ź Latin Small Letter Z with Acute
    C("Shift-A"):               UC(0x00C1),                     # Á Latin Capital Letter A with Acute
    C("Shift-C"):               UC(0x0106),                     # Ć Latin Capital Letter C with Acute
    C("Shift-E"):               UC(0x00C9),                     # É Latin Capital Letter E with Acute
    C("Shift-G"):               UC(0x01F4),                     # Ǵ Latin Capital Letter G with Acute
    C("Shift-I"):               UC(0x00CD),                     # Í Latin Capital Letter I with Acute
    C("Shift-M"):               UC(0x1E3E),                     # Ḿ Latin Capital Letter M with Acute
    C("Shift-N"):               UC(0x0143),                     # Ń Latin Capital Letter N with Acute
    C("Shift-O"):               UC(0x00D3),                     # Ó Latin Capital Letter O with Acute
    C("Shift-P"):               UC(0x1E54),                     # Ṕ Latin Capital Letter P with Acute
    C("Shift-R"):               UC(0x0154),                     # Ŕ Latin Capital Letter R with Acute
    C("Shift-S"):               UC(0x015A),                     # Ś Latin Capital Letter S with Acute
    C("Shift-W"):               UC(0x1E82),                     # Ẃ Latin Capital Letter W with Acute
    C("Shift-Y"):               UC(0x00DD),                     # Ý Latin Capital Letter Y with Acute
    C("Shift-Z"):               UC(0x0179),                     # Ź Latin Capital Letter Z with Acute
}, when = lambda _: ac_Chr_main == 0x00B4 and cnfg.optspec_layout == 'ABC')

keymap("DK-ABC - Double Grave", {
    # Shift+Option+Y            {U+030F} [uses {U+02F5} Modifier Letter Middle Double Grave Accent]
    # Valid keys:
    # a e i o r u
    # A E I O R U
    C("A"):                     UC(0x0201),                     # ȁ Latin Small Letter A with Double Grave
    C("E"):                     UC(0x0205),                     # ȅ Latin Small Letter E with Double Grave
    C("I"):                     UC(0x0209),                     # ȉ Latin Small Letter I with Double Grave
    C("O"):                     UC(0x020D),                     # ȍ Latin Small Letter O with Double Grave
    C("R"):                     UC(0x0211),                     # ȑ Latin Small Letter R with Double Grave
    C("U"):                     UC(0x0215),                     # ȕ Latin Small Letter U with Double Grave
    C("Shift-A"):               UC(0x0200),                     # Ȁ Latin Capital Letter A with Double Grave
    C("Shift-E"):               UC(0x0204),                     # Ȅ Latin Capital Letter E with Double Grave
    C("Shift-I"):               UC(0x0208),                     # Ȉ Latin Capital Letter I with Double Grave
    C("Shift-O"):               UC(0x020C),                     # Ȍ Latin Capital Letter O with Double Grave
    C("Shift-R"):               UC(0x0210),                     # Ȑ Latin Capital Letter R with Double Grave
    C("Shift-U"):               UC(0x0214),                     # Ȕ Latin Capital Letter U with Double Grave
}, when=lambda _: ac_Chr_main in [0x030F, 0x02F5] and cnfg.optspec_layout == 'ABC')

keymap("DK-ABC - Umlaut/Diaeresis", {
    # Option+U                  {U+00A8}
    # Valid keys:
    # a e h i o t u w x y
    # A E H I O T U W X Y
    C("A"):                     UC(0x00E4),                     # ä Latin Small Letter A with Diaeresis
    C("E"):                     UC(0x00EB),                     # ë Latin Small Letter E with Diaeresis
    C("H"):                     UC(0x1E27),                     # ḧ Latin Small Letter H with Diaeresis
    C("I"):                     UC(0x00EF),                     # ï Latin Small Letter I with Diaeresis
    C("O"):                     UC(0x00F6),                     # ö Latin Small Letter O with Diaeresis
    C("T"):                     UC(0x1E97),                     # ẗ Latin Small Letter T with Diaeresis
    C("U"):                     UC(0x00FC),                     # ü Latin Small Letter U with Diaeresis
    C("W"):                     UC(0x1E85),                     # ẅ Latin Small Letter W with Diaeresis
    C("X"):                     UC(0x1E8D),                     # ẍ Latin Small Letter X with Diaeresis
    C("Y"):                     UC(0x00FF),                     # ÿ Latin Small Letter Y with Diaeresis
    C("Shift-A"):               UC(0x00C4),                     # Ä Latin Capital Letter A with Diaeresis
    C("Shift-E"):               UC(0x00CB),                     # Ë Latin Capital Letter E with Diaeresis
    C("Shift-H"):               UC(0x1E26),                     # Ḧ Latin Capital Letter H with Diaeresis
    C("Shift-I"):               UC(0x00CF),                     # Ï Latin Capital Letter I with Diaeresis
    C("Shift-O"):               UC(0x00D6),                     # Ö Latin Capital Letter O with Diaeresis
    C("Shift-T"):              [UC(0x0054),UC(0x0308)],         # T̈ Latin Capital Letter T with Diaeresis
    C("Shift-U"):               UC(0x00DC),                     # Ü Latin Capital Letter U with Diaeresis
    C("Shift-W"):               UC(0x1E84),                     # Ẅ Latin Capital Letter W with Diaeresis
    C("Shift-X"):               UC(0x1E8C),                     # Ẍ Latin Capital Letter X with Diaeresis
    C("Shift-Y"):               UC(0x0178),                     # Ÿ Latin Capital Letter Y with Diaeresis
}, when = lambda _: ac_Chr_main == 0x00A8 and cnfg.optspec_layout == 'ABC')

keymap("DK-ABC - Apostrophe/Horn", {
    # Option+I                  {U+02BC}
    # Valid keys:
    # o u
    # O U
    C("O"):                     UC(0x01A1),                     # ơ Latin Small Letter O with Horn
    C("U"):                     UC(0x01B0),                     # ư Latin Small Letter U with Horn
    C("Shift-O"):               UC(0x01A0),                     # Ơ Latin Capital Letter O with Horn
    C("Shift-U"):               UC(0x01AF),                     # Ư Latin Capital Letter U with Horn
}, when = lambda _: ac_Chr_main == 0x02BC and cnfg.optspec_layout == 'ABC')

keymap("DK-ABC - Comma Below", {
    # Option+P                  {U+002C}
    # Valid keys:
    # s t
    # S T
    C("S"):                     UC(0x0219),                     # ș Latin Small Letter S with Comma Below
    C("T"):                     UC(0x021B),                     # ț Latin Small Letter T with Comma Below
    C("Shift-S"):               UC(0x0218),                     # Ș Latin Capital Letter S with Comma Below
    C("Shift-T"):               UC(0x021A),                     # Ț Latin Capital Letter T with Comma Below
}, when = lambda _: ac_Chr_main == 0x002C and cnfg.optspec_layout == 'ABC')

keymap("DK-ABC - Macron/Line Above", {
    # Option+A                  {U+00AF}
    # Valid keys:
    # a e g i l o r s v y z
    # A E G I L O R S V Y Z
    C("A"):                     UC(0x0101),                     # ā Latin Small Letter A with Macron
    C("E"):                     UC(0x0113),                     # ē Latin Small Letter E with Macron
    C("G"):                     UC(0x1E21),                     # ḡ Latin Small Letter G with Macron
    C("I"):                     UC(0x012B),                     # ī Latin Small Letter I with Macron
    C("L"):         [UC(0x006C),UC(0x0304),UC(0x0323)],         # ḹ Latin Small Letter L w/Macron and Dot Below
    C("O"):                     UC(0x014D),                     # ō Latin Small Letter O with Macron
    C("R"):         [UC(0x0072),UC(0x0304),UC(0x0323)],         # ṝ Latin Small Letter R w/Macron and Dot Below
    C("S"):                    [UC(0x0073),UC(0x0304)],         # s̄ Latin Small Letter S with Macron
    C("V"):                     UC(0x01D6),                     # ǖ Latin Small Letter U with Diaeresis and Macron
    C("Y"):                     UC(0x0233),                     # ȳ Latin Small Letter Y with Macron
    C("Z"):                    [UC(0x007A),UC(0x0304)],         # z̄ Latin Small Letter Z with Macron
    C("Shift-A"):               UC(0x0100),                     # Ā Latin Capital Letter A with Macron
    C("Shift-E"):               UC(0x0112),                     # Ē Latin Capital Letter E with Macron
    C("Shift-G"):               UC(0x1E20),                     # Ḡ Latin Capital Letter G with Macron
    C("Shift-I"):               UC(0x012A),                     # Ī Latin Capital Letter I with Macron
    C("Shift-L"):   [UC(0x004C),UC(0x0304),UC(0x0323)],         # Ḹ Latin Capital Letter L w/Macron and Dot Below
    C("Shift-O"):               UC(0x014C),                     # Ō Latin Capital Letter O with Macron
    C("Shift-R"):   [UC(0x0052),UC(0x0304),UC(0x0323)],         # Ṝ Latin Capital Letter R w/Macron and Dot Below
    C("Shift-S"):              [UC(0x0053),UC(0x0304)],         # S̄ Latin Capital Letter S with Macron
    C("Shift-V"):               UC(0x01D5),                     # Ǖ Latin Capital Letter U with Diaeresis and Macron
    C("Shift-Y"):               UC(0x0232),                     # Ȳ Latin Capital Letter Y with Macron
    C("Shift-Z"):              [UC(0x005A),UC(0x0304)],         # Z̄ Latin Capital Letter Z with Macron
}, when = lambda _: ac_Chr_main == 0x00AF and cnfg.optspec_layout == 'ABC')

keymap("DK-ABC - Inverted Breve", {
    # Shift+Option+S            {U+0311}    [uses {U+1D16} as a substitute]
    # Valid keys:
    # a e i o r u
    # A E I O R U
    C("A"):                     UC(0x0203),                     # ȃ Latin Small Letter A with Inverted Breve
    C("E"):                     UC(0x0207),                     # ȇ Latin Small Letter E with Inverted Breve
    C("I"):                     UC(0x020B),                     # ȋ Latin Small Letter I with Inverted Breve
    C("O"):                     UC(0x020F),                     # ȏ Latin Small Letter O with Inverted Breve
    C("R"):                     UC(0x0213),                     # ȓ Latin Small Letter R with Inverted Breve
    C("U"):                     UC(0x0217),                     # ȗ Latin Small Letter U with Inverted Breve
    C("Shift-A"):               UC(0x0202),                     # Ȃ Latin Capital Letter A with Inverted Breve
    C("Shift-E"):               UC(0x0206),                     # Ȇ Latin Capital Letter E with Inverted Breve
    C("Shift-I"):               UC(0x020A),                     # Ȋ Latin Capital Letter I with Inverted Breve
    C("Shift-O"):               UC(0x020E),                     # Ȏ Latin Capital Letter O with Inverted Breve
    C("Shift-R"):               UC(0x0212),                     # Ȓ Latin Capital Letter R with Inverted Breve
    C("Shift-U"):               UC(0x0216),                     # Ȗ Latin Capital Letter U with Inverted Breve
}, when = lambda _: ac_Chr_main in [0x0311, 0x1D16] and cnfg.optspec_layout == 'ABC')

keymap("DK-ABC - Tilde Below", {
    # Shift+Option+F            {U+0330}    [uses {U+02F7} as a substitute]
    # Valid keys:
    # e i u
    # E I U
    C("E"):                     UC(0x1E1B),                     # ḛ Latin Small Letter E with Tilde Below
    C("I"):                     UC(0x1E2D),                     # ḭ Latin Small Letter I with Tilde Below
    C("U"):                     UC(0x1E75),                     # ṵ Latin Small Letter U with Tilde Below
    C("Shift-E"):               UC(0x1E1A),                     # Ḛ Latin Capital Letter E with Tilde Below
    C("Shift-I"):               UC(0x1E2C),                     # Ḭ Latin Capital Letter I with Tilde Below
    C("Shift-U"):               UC(0x1E74),                     # Ṵ Latin Capital Letter U with Tilde Below
}, when = lambda _: ac_Chr_main in [0x0330, 0x02F7] and cnfg.optspec_layout == 'ABC')

keymap("DK-ABC - Caret/Circumflex Below", {
    # Shift+Option+G            {U+2038}
    # Valid keys:
    # d e l n t u
    # D E L N T U
    C("D"):                     UC(0x1E13),                     # ḓ Latin Small Letter D with Circumflex Below
    C("E"):                     UC(0x1E19),                     # ḙ Latin Small Letter E with Circumflex Below
    C("L"):                     UC(0x1E3D),                     # ḽ Latin Small Letter L with Circumflex Below
    C("N"):                     UC(0x1E4B),                     # ṋ Latin Small Letter N with Circumflex Below
    C("T"):                     UC(0x1E71),                     # ṱ Latin Small Letter T with Circumflex Below
    C("U"):                     UC(0x1E77),                     # ṷ Latin Small Letter U with Circumflex Below
    C("Shift-D"):               UC(0x1E12),                     # Ḓ Latin Capital Letter D with Circumflex Below
    C("Shift-E"):               UC(0x1E18),                     # Ḙ Latin Capital Letter E with Circumflex Below
    C("Shift-L"):               UC(0x1E3C),                     # Ḽ Latin Capital Letter L with Circumflex Below
    C("Shift-N"):               UC(0x1E4A),                     # Ṋ Latin Capital Letter N with Circumflex Below
    C("Shift-T"):               UC(0x1E70),                     # Ṱ Latin Capital Letter T with Circumflex Below
    C("Shift-U"):               UC(0x1E76),                     # Ṷ Latin Capital Letter U with Circumflex Below
}, when = lambda _: ac_Chr_main == 0x2038 and cnfg.optspec_layout == 'ABC')

keymap("DK-ABC - Low Macron/Line Below", {
    # Option+H                  {U+02CD}
    # Valid keys:
    # b d h k l n r t z
    # B D H K L N R T Z
    C("B"):                     UC(0x1E07),                     # ḇ Latin Small Letter B with Line Below
    C("D"):                     UC(0x1E0F),                     # ḏ Latin Small Letter D with Line Below
    C("H"):                     UC(0x1E96),                     # ẖ Latin Small Letter H with Line Below
    C("K"):                     UC(0x1E35),                     # ḵ Latin Small Letter K with Line Below
    C("L"):                     UC(0x1E3B),                     # ḻ Latin Small Letter L with Line Below
    C("N"):                     UC(0x1E49),                     # ṉ Latin Small Letter N with Line Below
    C("R"):                     UC(0x1E5F),                     # ṟ Latin Small Letter R with Line Below
    C("T"):                     UC(0x1E6F),                     # ṯ Latin Small Letter T with Line Below
    C("Z"):                     UC(0x1E95),                     # ẕ Latin Small Letter Z with Line Below
    C("Shift-B"):               UC(0x1E06),                     # Ḇ Latin Capital Letter B with Line Below
    C("Shift-D"):               UC(0x1E0E),                     # Ḏ Latin Capital Letter D with Line Below
    C("Shift-H"):              [UC(0x0048),UC(0x0331)],         # H̱ Latin Capital Letter H with Line Below
    C("Shift-K"):               UC(0x1E34),                     # Ḵ Latin Capital Letter K with Line Below
    C("Shift-L"):               UC(0x1E3A),                     # Ḻ Latin Capital Letter L with Line Below
    C("Shift-N"):               UC(0x1E48),                     # Ṉ Latin Capital Letter N with Line Below
    C("Shift-R"):               UC(0x1E5E),                     # Ṟ Latin Capital Letter R with Line Below
    C("Shift-T"):               UC(0x1E6E),                     # Ṯ Latin Capital Letter T with Line Below
    C("Shift-Z"):               UC(0x1E94),                     # Ẕ Latin Capital Letter Z with Line Below
}, when = lambda _: ac_Chr_main == 0x02CD and cnfg.optspec_layout == 'ABC')

keymap("DK-ABC - Double Acute", {
    # Option+J                  {U+02DD}
    # Valid keys:
    # o u
    # O U
    C("O"):                     UC(0x0151),                     # ő Latin Small Letter O with Double Acute
    C("U"):                     UC(0x0171),                     # ű Latin Small Letter U with Double Acute
    C("Shift-O"):               UC(0x0150),                     # Ő Latin Capital Letter O with Double Acute
    C("Shift-U"):               UC(0x0170),                     # Ű Latin Capital Letter U with Double Acute
}, when = lambda _: ac_Chr_main == 0x02DD and cnfg.optspec_layout == 'ABC')

keymap("DK-ABC - Ring Above", {
    # Option+K                  {U+02DA}
    # Valid keys:
    # a e o u w y
    # A E O U W Y
    C("A"):                     UC(0x00E5),                     # å Latin Small Letter A with Ring Above
    C("E"):                    [UC(0x0065),UC(0x030A)],         # e̊ Latin Small Letter E with Ring Above
    C("O"):                    [UC(0x006F),UC(0x030A)],         # o̊ Latin Small Letter O with Ring Above
    C("U"):                     UC(0x016F),                     # ů Latin Small Letter U with Ring Above
    C("W"):                     UC(0x1E98),                     # ẘ Latin Small Letter W with Ring Above
    C("Y"):                     UC(0x1E99),                     # ẙ Latin Small Letter Y with Ring Above
    C("Shift-A"):               UC(0x00C5),                     # Å Latin Capital Letter A with Ring Above
    C("Shift-E"):              [UC(0x0045),UC(0x030A)],         # E̊ Latin Capital Letter E with Ring Above
    C("Shift-O"):              [UC(0x004F),UC(0x030A)],         # O̊ Latin Capital Letter O with Ring Above
    C("Shift-U"):               UC(0x016E),                     # Ů Latin Capital Letter U with Ring Above
    C("Shift-W"):              [UC(0x0057),UC(0x030A)],         # W̊ Latin Capital Letter W with Ring Above
    C("Shift-Y"):              [UC(0x0059),UC(0x030A)],         # Y̊ Latin Capital Letter Y with Ring Above
}, when = lambda _: ac_Chr_main == 0x02DA and cnfg.optspec_layout == 'ABC')

keymap("DK-ABC - Stroke/Hyphen-Minus", {
    # Option+L                  {U+002D}
    # Valid keys:
    # b d g h i l o t u z
    #   D G H I L O T   Z
    C("B"):                     UC(0x0180),                     # ƀ Latin Small Letter B with Stroke
    C("D"):                     UC(0x0111),                     # đ Latin Small Letter D with Stroke
    C("G"):                     UC(0x01E5),                     # ǥ Latin Small Letter G with Stroke
    C("H"):                     UC(0x0127),                     # ħ Latin Small Letter H with Stroke
    C("I"):                     UC(0x0268),                     # ɨ Latin Small Letter I with Stroke
    C("L"):                     UC(0x0142),                     # ł Latin Small Letter L with Stroke
    C("O"):                     UC(0x0275),                     # ɵ Latin Small Letter Barred O
    C("T"):                     UC(0x0167),                     # ŧ Latin Small Letter T with Stroke
    C("U"):                     UC(0x0289),                     # ʉ Latin Small Letter U Bar
    C("Z"):                     UC(0x01B6),                     # ƶ Latin Small Letter Z with Stroke
    C("Shift-D"):               UC(0x0110),                     # Đ Latin Capital Letter D with Stroke
    C("Shift-G"):               UC(0x01E4),                     # Ǥ Latin Capital Letter G with Stroke
    C("Shift-H"):               UC(0x0126),                     # Ħ Latin Capital Letter H with Stroke
    C("Shift-I"):               UC(0x0197),                     # Ɨ Latin Capital Letter I with Stroke
    C("Shift-L"):               UC(0x0141),                     # Ł Latin Capital Letter L with Stroke
    C("Shift-O"):               UC(0x019F),                     # Ɵ Latin Capital Letter O with Middle Tilde
    C("Shift-T"):               UC(0x0166),                     # Ŧ Latin Capital Letter T with Stroke
    C("Shift-Z"):               UC(0x01B5),                     # Ƶ Latin Capital Letter Z with Stroke
}, when = lambda _: ac_Chr_main == 0x002D and cnfg.optspec_layout == 'ABC')

keymap("DK-ABC - Numero Sign", {
    # Shift+Option+Semicolon    {U+2116}
    # Valid keys:
    # 2 3 5 6 7 8 (digits with Option)
    # 2 3 5 6   8 (digits with Shift+Option)
    # a c e g h j k m n q r s u v w y z (letters with Option)
    # A C E G H J K M N Q R   U   W Y Z (letters with Shift+Option)
    C("3"):                     UC(0x025B),                     # ɛ  Latin Small Letter Open E
    C("5"):                     UC(0x01BD),                     # ƽ  Latin Small Letter Tone Five
    C("2"):                     UC(0x01A8),                     # ƨ  Latin Small Letter Tone Two
    C("6"):                     UC(0x0185),                     # ƅ  Latin Small Letter Tone Six
    C("7"):                     UC(0x204A),                     # ⁊  Tironian Sign Et
    C("8"):                     UC(0x0223),                     # ȣ  Latin Small Letter Ou
    C("Shift-2"):               UC(0x01A7),                     # Ƨ  Latin Capital Letter Tone Two
    C("Shift-3"):               UC(0x0190),                     # Ɛ  Latin Capital Letter Open E
    C("Shift-5"):               UC(0x01BC),                     # Ƽ  Latin Capital Letter Tone Five
    C("Shift-6"):               UC(0x0184),                     # Ƅ  Latin Capital Letter Tone Six
    C("Shift-8"):               UC(0x0222),                     # Ȣ  Latin Capital Letter Ou
    C("a"):                     UC(0x0259),                     # ə  Latin Small Letter Schwa
    C("c"):                     UC(0x0254),                     # ɔ  Latin Small Letter Open O
    C("e"):                     UC(0x01DD),                     # ǝ  Latin Small Letter Turned E
    C("g"):                     UC(0x0263),                     # ɣ  Latin Small Letter Gamma
    C("h"):                     UC(0x0195),                     # ƕ  Latin Small Letter Hv
    C("j"):                     UC(0x019E),                     # ƞ  Latin Small Letter N with Long Right Leg
    C("k"):                     UC(0x0138),                     # ĸ  Latin Small Letter Kra
    C("m"):                     UC(0x026F),                     # ɯ  Latin Small Letter Turned M
    C("n"):                     UC(0x014B),                     # ŋ  Latin Small Letter Eng
    C("q"):                     UC(0x01A3),                     # ƣ  Latin Small Letter Oi
    C("r"):                     UC(0x0280),                     # ʀ  Latin Letter Small Capital R
    C("s"):                     UC(0x017F),                     # ſ  Latin Small Letter Long S
    C("u"):                     UC(0x028A),                     # ʊ  Latin Small Letter Upsilon
    C("v"):                     UC(0x028C),                     # ʌ  Latin Small Letter Turned V
    C("w"):                     UC(0x01BF),                     # ƿ  Latin Letter Wynn
    C("y"):                     UC(0x021D),                     # ȝ  Latin Small Letter Yogh
    C("z"):                     UC(0x0292),                     # ʒ  Latin Small Letter Ezh
    C("Shift-A"):               UC(0x018F),                     # Ə  Latin Capital Letter Schwa
    C("Shift-C"):               UC(0x0186),                     # Ɔ  Latin Capital Letter Open O
    C("Shift-E"):               UC(0x018E),                     # Ǝ  Latin Capital Letter Reversed E
    C("Shift-G"):               UC(0x0194),                     # Ɣ  Latin Capital Letter Gamma
    C("Shift-H"):               UC(0x01F6),                     # Ƕ  Latin Capital Letter Hwair
    C("Shift-J"):               UC(0x0220),                     # Ƞ  Latin Capital Letter N with Long Right Leg
    C("Shift-K"):              [UC(0x004B),UC(0x2019)],         # K’ Latin Capital Letter K with Apostrophe
    C("Shift-M"):               UC(0x019C),                     # Ɯ  Latin Capital Letter Turned M
    C("Shift-N"):               UC(0x014A),                     # Ŋ  Latin Capital Letter Eng
    C("Shift-Q"):               UC(0x01A2),                     # Ƣ  Latin Capital Letter Oi
    C("Shift-R"):               UC(0x01A6),                     # Ʀ  Latin Letter Yr
    C("Shift-U"):               UC(0x01B1),                     # Ʊ  Latin Capital Letter Upsilon
    C("Shift-W"):               UC(0x01F7),                     # Ƿ  Latin Capital Letter Wynn
    C("Shift-Y"):               UC(0x021C),                     # Ȝ  Latin Capital Letter Yogh
    C("Shift-Z"):               UC(0x01B7),                     # Ʒ  Latin Capital Letter Ezh
}, when = lambda _: ac_Chr_main == 0x2116 and cnfg.optspec_layout == 'ABC')

keymap("DK-ABC - Hook Above/Glottal Stop", {
    # Option+Z                  {U+02C0}
    # Valid keys:
    # a e i o u y
    # A E I O U Y
    C("A"):                     UC(0x1EA3),                     # ả  Latin Small Letter A with Hook Above
    C("E"):                     UC(0x1EBB),                     # ẻ  Latin Small Letter E with Hook Above
    C("I"):                     UC(0x1EC9),                     # ỉ  Latin Small Letter I with Hook Above
    C("O"):                     UC(0x1ECF),                     # ỏ  Latin Small Letter O with Hook Above
    C("U"):                     UC(0x1EE7),                     # ủ  Latin Small Letter U with Hook Above
    C("Y"):                     UC(0x1EF7),                     # ỷ  Latin Small Letter Y with Hook Above
    C("Shift-A"):               UC(0x1EA2),                     # Ả  Latin Small Letter A with Hook Above
    C("Shift-E"):               UC(0x1EBA),                     # Ẻ  Latin Small Letter E with Hook Above
    C("Shift-I"):               UC(0x1EC8),                     # Ỉ  Latin Small Letter I with Hook Above
    C("Shift-O"):               UC(0x1ECE),                     # Ỏ  Latin Small Letter O with Hook Above
    C("Shift-U"):               UC(0x1EE6),                     # Ủ  Latin Small Letter U with Hook Above
    C("Shift-Y"):               UC(0x1EF6),                     # Ỷ  Latin Small Letter Y with Hook Above
}, when = lambda _: ac_Chr_main == 0x02C0 and cnfg.optspec_layout == 'ABC')

keymap("DK-ABC - Dot Below", {
    # Option+X                  {U+002E}
    # Valid keys:
    # a b d e h i k l m n o r s t u v w y z
    # A B D E H I K L M N O R S T U V W Y Z
    C("A"):                     UC(0x1EA1),                     # ạ Latin Small Letter A with Dot Below
    C("B"):                     UC(0x1E05),                     # ḅ Latin Small Letter B with Dot Below
    C("D"):                     UC(0x1E0D),                     # ḍ Latin Small Letter D with Dot Below
    C("E"):                     UC(0x1EB9),                     # ẹ Latin Small Letter E with Dot Below
    C("H"):                     UC(0x1E25),                     # ḥ Latin Small Letter H with Dot Below
    C("I"):                     UC(0x1ECB),                     # ị Latin Small Letter I with Dot Below
    C("K"):                     UC(0x1E33),                     # ḳ Latin Small Letter K with Dot Below
    C("L"):                     UC(0x1E37),                     # ḷ Latin Small Letter L with Dot Below
    C("M"):                     UC(0x1E43),                     # ṃ Latin Small Letter M with Dot Below
    C("N"):                     UC(0x1E47),                     # ṇ Latin Small Letter N with Dot Below
    C("O"):                     UC(0x1ECD),                     # ọ Latin Small Letter O with Dot Below
    C("R"):                     UC(0x1E5B),                     # ṛ Latin Small Letter R with Dot Below
    C("S"):                     UC(0x1E63),                     # ṣ Latin Small Letter S with Dot Below
    C("T"):                     UC(0x1E6D),                     # ṭ Latin Small Letter T with Dot Below
    C("U"):                     UC(0x1EE5),                     # ụ Latin Small Letter U with Dot Below
    C("V"):                     UC(0x1E7F),                     # ṿ Latin Small Letter V with Dot Below
    C("W"):                     UC(0x1E89),                     # ẉ Latin Small Letter W with Dot Below
    C("Y"):                     UC(0x1EF5),                     # ỵ Latin Small Letter Y with Dot Below
    C("Z"):                     UC(0x1E93),                     # ẓ Latin Small Letter Z with Dot Below
    C("Shift-A"):               UC(0x1EA0),                     # Ạ Latin Capital Letter A with Dot Below
    C("Shift-B"):               UC(0x1E04),                     # Ḅ Latin Capital Letter B with Dot Below
    C("Shift-D"):               UC(0x1E0C),                     # Ḍ Latin Capital Letter D with Dot Below
    C("Shift-E"):               UC(0x1EB8),                     # Ẹ Latin Capital Letter E with Dot Below
    C("Shift-H"):               UC(0x1E24),                     # Ḥ Latin Capital Letter H with Dot Below
    C("Shift-I"):               UC(0x1ECA),                     # Ị Latin Capital Letter I with Dot Below
    C("Shift-K"):               UC(0x1E32),                     # Ḳ Latin Capital Letter K with Dot Below
    C("Shift-L"):               UC(0x1E36),                     # Ḷ Latin Capital Letter L with Dot Below
    C("Shift-M"):               UC(0x1E42),                     # Ṃ Latin Capital Letter M with Dot Below
    C("Shift-N"):               UC(0x1E46),                     # Ṇ Latin Capital Letter N with Dot Below
    C("Shift-O"):               UC(0x1ECC),                     # Ọ Latin Capital Letter O with Dot Below
    C("Shift-R"):               UC(0x1E5A),                     # Ṛ Latin Capital Letter R with Dot Below
    C("Shift-S"):               UC(0x1E62),                     # Ṣ Latin Capital Letter S with Dot Below
    C("Shift-T"):               UC(0x1E6C),                     # Ṭ Latin Capital Letter T with Dot Below
    C("Shift-U"):               UC(0x1EE4),                     # Ụ Latin Capital Letter U with Dot Below
    C("Shift-V"):               UC(0x1E7E),                     # Ṿ Latin Capital Letter V with Dot Below
    C("Shift-W"):               UC(0x1E88),                     # Ẉ Latin Capital Letter W with Dot Below
    C("Shift-Y"):               UC(0x1EF4),                     # Ỵ Latin Capital Letter Y with Dot Below
    C("Shift-Z"):               UC(0x1E92),                     # Ẓ Latin Capital Letter Z with Dot Below
}, when = lambda _: ac_Chr_main == 0x002E and cnfg.optspec_layout == 'ABC')

keymap("DK-ABC - Cedilla/Cedille", {
    # Option+C                  {U+00B8}
    # Valid keys:
    # c d e g h k l n r s t z
    # C D E G H K L N R S T Z
    C("C"):                     UC(0x00E7),                     # ç Latin Small Letter C with Cedilla
    C("D"):                     UC(0x1E11),                     # ḑ Latin Small Letter D with Cedilla
    C("E"):                     UC(0x0229),                     # ȩ Latin Small Letter E with Cedilla
    C("G"):                     UC(0x0123),                     # ģ Latin Small Letter G with Cedilla
    C("H"):                     UC(0x1E29),                     # ḩ Latin Small Letter H with Cedilla
    C("K"):                     UC(0x0137),                     # ķ Latin Small Letter K with Cedilla
    C("L"):                     UC(0x013C),                     # ļ Latin Small Letter L with Cedilla
    C("N"):                     UC(0x0146),                     # ņ Latin Small Letter N with Cedilla
    C("R"):                     UC(0x0157),                     # ŗ Latin Small Letter R with Cedilla
    C("S"):                     UC(0x015F),                     # ş Latin Small Letter S with Cedilla
    C("T"):                     UC(0x0163),                     # ţ Latin Small Letter T with Cedilla
    C("Z"):                    [UC(0x007A),UC(0x0327)],         # z̧ Latin Small Letter Z with Cedilla
    C("Shift-C"):               UC(0x00C7),                     # Ç Latin Capital Letter C with Cedilla
    C("Shift-D"):               UC(0x1E10),                     # Ḑ Latin Capital Letter D with Cedilla
    C("Shift-E"):               UC(0x0228),                     # Ȩ Latin Capital Letter E with Cedilla
    C("Shift-G"):               UC(0x0122),                     # Ģ Latin Capital Letter G with Cedilla
    C("Shift-H"):               UC(0x1E28),                     # Ḩ Latin Capital Letter H with Cedilla
    C("Shift-K"):               UC(0x0136),                     # Ķ Latin Capital Letter K with Cedilla
    C("Shift-L"):               UC(0x013B),                     # Ļ Latin Capital Letter L with Cedilla
    C("Shift-N"):               UC(0x0145),                     # Ņ Latin Capital Letter N with Cedilla
    C("Shift-R"):               UC(0x0156),                     # Ŗ Latin Capital Letter R with Cedilla
    C("Shift-S"):               UC(0x015E),                     # Ş Latin Capital Letter S with Cedilla
    C("Shift-T"):               UC(0x0162),                     # Ţ Latin Capital Letter T with Cedilla
    C("Shift-Z"):              [UC(0x005A),UC(0x0327)],         # Z̧ Latin Capital Letter Z with Cedilla
}, when = lambda _: ac_Chr_main == 0x00B8 and cnfg.optspec_layout == 'ABC')

keymap("DK-ABC - Caron/hacek", {
    # Option+V                  {U+02C7}
    # Valid keys:
    # a c d e g h i j k l n o r s t u v x z
    # A C D E G H I J K L N O R S T U V X Z
    C("A"):                     UC(0x01CE),                     # ǎ Latin Small Letter A with Caron
    C("C"):                     UC(0x010D),                     # č Latin Small Letter C with Caron
    C("D"):                     UC(0x010F),                     # ď Latin Small Letter D with Caron
    C("E"):                     UC(0x011B),                     # ě Latin Small Letter E with Caron
    C("G"):                     UC(0x01E7),                     # ǧ Latin Small Letter G with Caron
    C("H"):                     UC(0x021F),                     # ȟ Latin Small Letter H with Caron
    C("I"):                     UC(0x01D0),                     # ǐ Latin Small Letter I with Caron
    C("J"):                     UC(0x01F0),                     # ǰ Latin Small Letter J with Caron
    C("K"):                     UC(0x01E9),                     # ǩ Latin Small Letter K with Caron
    C("L"):                     UC(0x013E),                     # ľ Latin Small Letter L with Caron
    C("N"):                     UC(0x0148),                     # ň Latin Small Letter N with Caron
    C("O"):                     UC(0x01D2),                     # ǒ Latin Small Letter O with Caron
    C("R"):                     UC(0x0159),                     # ř Latin Small Letter R with Caron
    C("S"):                     UC(0x0161),                     # š Latin Small Letter S with Caron
    C("T"):                     UC(0x0165),                     # ť Latin Small Letter T with Caron
    C("U"):                     UC(0x01D4),                     # ǔ Latin Small Letter U with Caron
    C("V"):                     UC(0x01DA),                     # ǚ Latin Small Letter U w/Diaeresis and Caron
    C("X"):                    [UC(0x0292),UC(0x030C)],         # ǯ Latin Small Letter Ezh with Caron
    C("Z"):                     UC(0x017E),                     # ž Latin Small Letter Z with Caron
    C("Shift-A"):               UC(0x01CD),                     # Ǎ Latin Capital Letter A with Caron
    C("Shift-C"):               UC(0x010C),                     # Č Latin Capital Letter C with Caron
    C("Shift-D"):               UC(0x010E),                     # Ď Latin Capital Letter D with Caron
    C("Shift-E"):               UC(0x011A),                     # Ě Latin Capital Letter E with Caron
    C("Shift-G"):               UC(0x01E6),                     # Ǧ Latin Capital Letter G with Caron
    C("Shift-H"):               UC(0x021E),                     # Ȟ Latin Capital Letter H with Caron
    C("Shift-I"):               UC(0x01CF),                     # Ǐ Latin Capital Letter I with Caron
    C("Shift-J"):              [UC(0x004A),UC(0x030C)],         # J̌ Latin Capital Letter J with Caron
    C("Shift-K"):               UC(0x01E8),                     # Ǩ Latin Capital Letter K with Caron
    C("Shift-L"):               UC(0x013D),                     # Ľ Latin Capital Letter L with Caron
    C("Shift-N"):               UC(0x0147),                     # Ň Latin Capital Letter N with Caron
    C("Shift-O"):               UC(0x01D1),                     # Ǒ Latin Capital Letter O with Caron
    C("Shift-R"):               UC(0x0158),                     # Ř Latin Capital Letter R with Caron
    C("Shift-S"):               UC(0x0160),                     # Š Latin Capital Letter S with Caron
    C("Shift-T"):               UC(0x0164),                     # Ť Latin Capital Letter T with Caron
    C("Shift-U"):               UC(0x01D3),                     # Ǔ Latin Capital Letter U with Caron
    C("Shift-V"):               UC(0x01D9),                     # Ǚ Latin Capital Letter U w/Diaeresis and Caron
    C("Shift-X"):              [UC(0x01B7),UC(0x030C)],         # Ǯ Latin Capital Letter Ezh with Caron
    C("Shift-Z"):               UC(0x017D),                     # Ž Latin Capital Letter Z with Caron
}, when = lambda _: ac_Chr_main == 0x02C7 and cnfg.optspec_layout == 'ABC')

keymap("DK-ABC - Breve", {
    # Option+B                  {U+02D8}
    # Valid keys:
    # a e g h i o u
    # A E G H I O U
    C("A"):                     UC(0x0103),                     # ă Latin Small Letter A with Breve
    C("E"):                     UC(0x0115),                     # ĕ Latin Small Letter E with Breve
    C("G"):                     UC(0x011F),                     # ğ Latin Small Letter G with Breve
    C("H"):                     UC(0x1E2B),                     # ḫ Latin Small Letter H with Breve Below
    C("I"):                     UC(0x012D),                     # ĭ Latin Small Letter I with Breve
    C("O"):                     UC(0x014F),                     # ŏ Latin Small Letter O with Breve
    C("U"):                     UC(0x016D),                     # ŭ Latin Small Letter U with Breve
    C("Shift-A"):               UC(0x0102),                     # Ă Latin Capital Letter A with Breve
    C("Shift-E"):               UC(0x0114),                     # Ĕ Latin Capital Letter E with Breve
    C("Shift-G"):               UC(0x011E),                     # Ğ Latin Capital Letter G with Breve
    C("Shift-H"):               UC(0x1E2A),                     # Ḫ Latin Capital Letter H with Breve Below
    C("Shift-I"):               UC(0x012C),                     # Ĭ Latin Capital Letter I with Breve
    C("Shift-O"):               UC(0x014E),                     # Ŏ Latin Capital Letter O with Breve
    C("Shift-U"):               UC(0x016C),                     # Ŭ Latin Capital Letter U with Breve
}, when = lambda _: ac_Chr_main == 0x02D8 and cnfg.optspec_layout == 'ABC')

keymap("DK-ABC - Tilde", {
    # Option+N                  {U+02DC}
    # Valid keys:
    # a e i n o u v y
    # A E I N O U V Y
    C("A"):                     UC(0x00E3),                     # ã Latin Small Letter A with Tilde
    C("E"):                     UC(0x1EBD),                     # ẽ Latin Small Letter E with Tilde
    C("I"):                     UC(0x0129),                     # ĩ Latin Small Letter I with Tilde
    C("N"):                     UC(0x00F1),                     # ñ Latin Small Letter N with Tilde
    C("O"):                     UC(0x00F5),                     # õ Latin Small Letter O with Tilde
    C("U"):                     UC(0x0169),                     # ũ Latin Small Letter U with Tilde
    C("V"):                     UC(0x1E7D),                     # ṽ Latin Small Letter V with Tilde
    C("Y"):                     UC(0x1EF9),                     # ỹ Latin Small Letter Y with Tilde
    C("Shift-A"):               UC(0x00C3),                     # Ã Latin Capital Letter A with Tilde
    C("Shift-E"):               UC(0x1EBC),                     # Ẽ Latin Capital Letter E with Tilde
    C("Shift-I"):               UC(0x0128),                     # Ĩ Latin Capital Letter I with Tilde
    C("Shift-N"):               UC(0x00D1),                     # Ñ Latin Capital Letter N with Tilde
    C("Shift-O"):               UC(0x00D5),                     # Õ Latin Capital Letter O with Tilde
    C("Shift-U"):               UC(0x0168),                     # Ũ Latin Capital Letter U with Tilde
    C("Shift-V"):               UC(0x1E7C),                     # Ṽ Latin Capital Letter V with Tilde
    C("Shift-Y"):               UC(0x1EF8),                     # Ỹ Latin Capital Letter Y with Tilde
}, when = lambda _: ac_Chr_main == 0x02DC and cnfg.optspec_layout == 'ABC')

keymap("DK-ABC - Ogonek", {
    # Option+M                  {U+02DB}
    # Valid keys:
    # a e i o u
    # A E I O U
    C("A"):                     UC(0x0105),                     # ą Latin Small Letter A with Ogonek
    C("E"):                     UC(0x0119),                     # ę Latin Small Letter E with Ogonek
    C("I"):                     UC(0x012F),                     # į Latin Small Letter I with Ogonek
    C("O"):                     UC(0x01EB),                     # ǫ Latin Small Letter O with Ogonek
    C("U"):                     UC(0x0173),                     # ų Latin Small Letter U with Ogonek
    C("Shift-A"):               UC(0x0104),                     # Ą Latin Capital Letter A with Ogonek
    C("Shift-E"):               UC(0x0118),                     # Ę Latin Capital Letter E with Ogonek
    C("Shift-I"):               UC(0x012E),                     # Į Latin Capital Letter I with Ogonek
    C("Shift-O"):               UC(0x01EA),                     # Ǫ Latin Capital Letter O with Ogonek
    C("Shift-U"):               UC(0x0172),                     # Ų Latin Capital Letter U with Ogonek
}, when = lambda _: ac_Chr_main == 0x02DB and cnfg.optspec_layout == 'ABC')

keymap("DK-ABC - Hook", {
    # Shift+Option+Dot          {U+0294}
    # Valid keys:
    # b c d f g h i k n p q r s t u x y z
    # B C D F G   I K N P   R S T U X Y Z
    C("B"):                     UC(0x0253),                     # ɓ Latin Small Letter B with Hook
    C("C"):                     UC(0x0188),                     # ƈ Latin Small Letter C with Hook
    C("D"):                     UC(0x0257),                     # ɗ Latin Small Letter D with Hook
    C("F"):                     UC(0x0192),                     # ƒ Latin Small Letter F with Hook (function symbol)
    C("G"):                     UC(0x0260),                     # ɠ Latin Small Letter G with Hook
    C("H"):                     UC(0x0266),                     # ɦ Latin Small Letter H with Hook
    C("I"):                     UC(0x0269),                     # ɩ Latin Small Letter Iota
    C("K"):                     UC(0x0199),                     # ƙ Latin Small Letter K with Hook
    C("N"):                     UC(0x0272),                     # ɲ Latin Small Letter N with Left Hook
    C("P"):                     UC(0x01A5),                     # ƥ Latin Small Letter P with Hook
    C("Q"):                     UC(0x02A0),                     # ʠ Latin Small Letter Q with Hook
    C("R"):                     UC(0x0288),                     # ʈ Latin Small Letter T with Retroflex Hook
    C("S"):                     UC(0x0283),                     # ʃ Latin Small Letter Esh
    C("T"):                     UC(0x01AD),                     # ƭ Latin Small Letter T with Hook
    C("U"):                     UC(0x028B),                     # ʋ Latin Small Letter V with Hook
    C("X"):                     UC(0x0256),                     # ɖ Latin Small Letter D with Tail
    C("Y"):                     UC(0x01B4),                     # ƴ Latin Small Letter Y with Hook
    C("Z"):                     UC(0x0225),                     # ȥ Latin Small Letter Z with Hook
    C("Shift-B"):               UC(0x0181),                     # Ɓ Latin Capital Letter B with Hook
    C("Shift-C"):               UC(0x0187),                     # Ƈ Latin Capital Letter C with Hook
    C("Shift-D"):               UC(0x018A),                     # Ɗ Latin Capital Letter D with Hook
    C("Shift-F"):               UC(0x0191),                     # Ƒ Latin Capital Letter F with Hook
    C("Shift-G"):               UC(0x0193),                     # Ɠ Latin Capital Letter G with Hook
    C("Shift-I"):               UC(0x0196),                     # Ɩ Latin Capital Letter Iota
    C("Shift-K"):               UC(0x0198),                     # Ƙ Latin Capital Letter K with Hook
    C("Shift-N"):               UC(0x019D),                     # Ɲ Latin Capital Letter N with Left Hook
    C("Shift-P"):               UC(0x01A4),                     # Ƥ Latin Capital Letter P with Hook
    C("Shift-R"):               UC(0x01AE),                     # Ʈ Latin Capital Letter T with Retroflex Hook
    C("Shift-S"):               UC(0x01A9),                     # Ʃ Latin Capital Letter Esh
    C("Shift-T"):               UC(0x01AC),                     # Ƭ Latin Capital Letter T with Hook
    C("Shift-U"):               UC(0x01B2),                     # Ʋ Latin Capital Letter V with Hook
    C("Shift-X"):               UC(0x0189),                     # Ɖ Latin Capital Letter African D
    C("Shift-Y"):               UC(0x01B3),                     # Ƴ Latin Capital Letter Y with Hook
    C("Shift-Z"):               UC(0x0224),                     # Ȥ Latin Capital Letter Z with Hook
}, when = lambda _: ac_Chr_main == 0x0294 and cnfg.optspec_layout == 'ABC')


#######################################
###  DEAD KEYS KEYMAPS - US LAYOUT  ###
#######################################
keymap("DK-US - Grave", {
    # Valid keys:
    # a e i o u
    # A E I O U
    C("A"):                     UC(0x00E0),                     # à Latin Small a with Grave
    C("E"):                     UC(0x00E8),                     # è Latin Small e with Grave
    C("I"):                     UC(0x00EC),                     # ì Latin Small i with Grave
    C("O"):                     UC(0x00F2),                     # ò Latin Small o with Grave
    C("U"):                     UC(0x00F9),                     # ù Latin Small u with Grave
    C("Shift-A"):               UC(0x00C0),                     # À Latin Capital A with Grave
    C("Shift-E"):               UC(0x00C8),                     # È Latin Capital E with Grave
    C("Shift-I"):               UC(0x00CC),                     # Ì Latin Capital I with Grave
    C("Shift-O"):               UC(0x00D2),                     # Ò Latin Capital O with Grave
    C("Shift-U"):               UC(0x00D9),                     # Ù Latin Capital U with Grave
}, when = lambda _: ac_Chr_main == 0x0060 and cnfg.optspec_layout == 'US')

keymap("DK-US - Acute", {
    # Valid keys:
    # a e i o u
    # A E I O U
    C("A"):                     UC(0x00E1),                     # á Latin Small a with Acute
    C("E"):                     UC(0x00E9),                     # é Latin Small e with Acute
    C("I"):                     UC(0x00ED),                     # í Latin Small i with Acute
    C("O"):                     UC(0x00F3),                     # ó Latin Small o with Acute
    C("U"):                     UC(0x00FA),                     # ú Latin Small u with Acute
    C("Shift-A"):               UC(0x00C1),                     # Á Latin Capital A with Acute
    C("Shift-E"):               UC(0x00C9),                     # É Latin Capital E with Acute
    C("Shift-I"):               UC(0x00CD),                     # Í Latin Capital I with Acute
    C("Shift-O"):               UC(0x00D3),                     # Ó Latin Capital O with Acute
    C("Shift-U"):               UC(0x00DA),                     # Ú Latin Capital U with Acute
}, when = lambda _: ac_Chr_main == 0x00B4 and cnfg.optspec_layout == 'US')

keymap("DK-US - Umlaut", {
    # Valid keys:
    # a e i o u y
    # A E I O U Y
    C("A"):                     UC(0x00E4),                     # ä Latin Small a with Umlaut
    C("E"):                     UC(0x00EB),                     # ë Latin Small e with Umlaut
    C("I"):                     UC(0x00EF),                     # ï Latin Small i with Umlaut
    C("O"):                     UC(0x00F6),                     # ö Latin Small o with Umlaut
    C("U"):                     UC(0x00FC),                     # ü Latin Small u with Umlaut
    C("Y"):                     UC(0x00FF),                     # ÿ Latin Small y with Umlaut
    C("Shift-A"):               UC(0x00C4),                     # Ä Latin Capital A with Umlaut
    C("Shift-E"):               UC(0x00CB),                     # Ë Latin Capital E with Umlaut
    C("Shift-I"):               UC(0x00CF),                     # Ï Latin Capital I with Umlaut
    C("Shift-O"):               UC(0x00D6),                     # Ö Latin Capital O with Umlaut
    C("Shift-U"):               UC(0x00DC),                     # Ü Latin Capital U with Umlaut
    C("Shift-Y"):               UC(0x0178),                     # Ÿ Latin Capital Y with Umlaut
}, when = lambda _: ac_Chr_main == 0x00A8 and cnfg.optspec_layout == 'US')

keymap("DK-US - Circumflex", {
    # Valid keys:
    # a e i o u
    # A E I O U
    C("A"):                     UC(0x00E2),                     # â Latin Small a with Circumflex
    C("E"):                     UC(0x00EA),                     # ê Latin Small e with Circumflex
    C("I"):                     UC(0x00EE),                     # î Latin Small i with Circumflex
    C("O"):                     UC(0x00F4),                     # ô Latin Small o with Circumflex
    C("U"):                     UC(0x00FB),                     # û Latin Small u with Circumflex
    C("Shift-A"):               UC(0x00C2),                     # Â Latin Capital A with Circumflex
    C("Shift-E"):               UC(0x00CA),                     # Ê Latin Capital E with Circumflex
    C("Shift-I"):               UC(0x00CE),                     # Î Latin Capital I with Circumflex
    C("Shift-O"):               UC(0x00D4),                     # Ô Latin Capital O with Circumflex
    C("Shift-U"):               UC(0x00DB),                     # Û Latin Capital U with Circumflex
}, when = lambda _: ac_Chr_main == 0x02C6 and cnfg.optspec_layout == 'US')

keymap("DK-US - Tilde", {
    # Valid keys:
    # a n o
    # A N O
    C("A"):                     UC(0x00E3),                     # ã Latin Small a with Tilde
    C("N"):                     UC(0x00F1),                     # ñ Latin Small n with Tilde
    C("O"):                     UC(0x00F5),                     # õ Latin Small o with Tilde
    C("Shift-A"):               UC(0x00C3),                     # Ã Latin Capital A with Tilde
    C("Shift-N"):               UC(0x00D1),                     # Ñ Latin Capital N with Tilde
    C("Shift-O"):               UC(0x00D5),                     # Õ Latin Capital O with Tilde
}, when = lambda _: ac_Chr_main == 0x02DC and cnfg.optspec_layout == 'US')



#################################################################
###                                                           ###
###                                                           ###
###      ███████ ███████  ██████  █████  ██████  ███████      ###
###      ██      ██      ██      ██   ██ ██   ██ ██           ###
###      █████   ███████ ██      ███████ ██████  █████        ###
###      ██           ██ ██      ██   ██ ██      ██           ###
###      ███████ ███████  ██████ ██   ██ ██      ███████      ###
###                                                           ###
###                                                           ###
#################################################################
keymap("Escape actions for dead keys - Overrides for ABC Extended", {

    ###  activate other dead keys correctly while one is active

    # US layout dead keys (not here, see keymap below)

    # ABC Extended layout dead keys
    C("Alt-Grave"):     [getDK(),UC(0x0060),C("Shift-Left"),setDK(0x0060)], # Dead Key Accent: Grave
    C("Alt-6"):         [getDK(),UC(0x02C6),C("Shift-Left"),setDK(0x02C6)], # Dead Key Accent: Circumflex
    C("Alt-W"):         [getDK(),UC(0x02D9),C("Shift-Left"),setDK(0x02D9)], # Dead Key Accent: Dot Above
    C("Alt-E"):         [getDK(),UC(0x00B4),C("Shift-Left"),setDK(0x00B4)], # Dead Key Accent: Acute

    # C("Shift-Alt-Y"):   [getDK(),UC(0x030F),C("Shift-Left"),setDK(0x030F)], # Dead Key Accent: Combining Double Grave
    # Double Grave accent acts odd when using the Combining Double Grave {U+030F}
    # Substituting {U+02F5}: ˵ Modifier Letter Middle Double Grave Accent
    C("Shift-Alt-Y"):   [getDK(),UC(0x02F5),C("Shift-Left"),setDK(0x02F5)], # Dead Key Accent: Double Grave (substitute)

    C("Alt-U"):         [getDK(),UC(0x00A8),C("Shift-Left"),setDK(0x00A8)], # Dead Key Accent: Umlaut/Diaeresis
    C("Alt-I"):         [getDK(),UC(0x02BC),C("Shift-Left"),setDK(0x02BC)], # Dead Key Accent: Apostrophe/Horn
    C("Alt-P"):         [getDK(),UC(0x002C),C("Shift-Left"),setDK(0x002C)], # Dead Key Accent: Comma Below
    C("Alt-A"):         [getDK(),UC(0x00AF),C("Shift-Left"),setDK(0x00AF)], # Dead Key Accent: Macron/Line Above

    # C("Shift-Alt-S"):   [getDK(),UC(0x0311),C("Shift-Left"),setDK(0x0311)], # Dead Key Accent: Combining Inverted Breve
    C("Shift-Alt-S"):   [getDK(),UC(0x1D16),C("Shift-Left"),setDK(0x1D16)], # Dead Key Accent: Combining Inverted Breve

    # C("Shift-Alt-F"):   [getDK(),UC(0x0330),C("Shift-Left"),setDK(0x0330)], # Dead Key Accent: Combining Tilde Below
    # Tilde Below accent acts odd when using the Combining Tilde Below {U+0330}
    # Substituting {U+02F7}: ˷ Modifier Letter Low Tilde
    C("Shift-Alt-F"):   [getDK(),UC(0x02F7),C("Shift-Left"),setDK(0x02F7)], # Dead Key Accent: Tilde Below
    C("Shift-Alt-G"):   [getDK(),UC(0x2038),C("Shift-Left"),setDK(0x2038)], # Dead Key Accent: Caret/Circumflex Below

    C("Alt-H"):         [getDK(),UC(0x02CD),C("Shift-Left"),setDK(0x02CD)], # Dead Key Accent: Low Macron/Line Below
    C("Alt-J"):         [getDK(),UC(0x02DD),C("Shift-Left"),setDK(0x02DD)], # Dead Key Accent: Double Acute
    C("Alt-K"):         [getDK(),UC(0x02DA),C("Shift-Left"),setDK(0x02DA)], # Dead Key Accent: Ring Above
    C("Alt-L"):         [getDK(),UC(0x002D),C("Shift-Left"),setDK(0x002D)], # Dead Key Accent: Stroke/Hyphen-Minus

    C("Shift-Alt-Semicolon"): [getDK(),UC(0x2116),C("Shift-Left"),setDK(0x2116)], # Dead Key Accent: Numero Sign

    C("Alt-Z"):         [getDK(),UC(0x02C0),C("Shift-Left"),setDK(0x02C0)], # Dead Key Accent: Hook Above/Glottal Stop
    C("Alt-X"):         [getDK(),UC(0x002E),C("Shift-Left"),setDK(0x002E)], # Dead Key Accent: Dot Below
    C("Alt-C"):         [getDK(),UC(0x00B8),C("Shift-Left"),setDK(0x00B8)], # Dead Key Accent: Cedilla/Cedille
    C("Alt-V"):         [getDK(),UC(0x02C7),C("Shift-Left"),setDK(0x02C7)], # Dead Key Accent: Caron/hacek
    C("Alt-B"):         [getDK(),UC(0x02D8),C("Shift-Left"),setDK(0x02D8)], # Dead Key Accent: Breve
    C("Alt-N"):         [getDK(),UC(0x02DC),C("Shift-Left"),setDK(0x02DC)], # Dead Key Accent: Tilde
    C("Alt-M"):         [getDK(),UC(0x02DB),C("Shift-Left"),setDK(0x02DB)], # Dead Key Accent: Ogonek

    C("Shift-Alt-Dot"): [getDK(),UC(0x0294),C("Shift-Left"),setDK(0x0294)], # Dead Key Accent: Hook

}, when = lambda _: ac_Chr_main in deadkeys_list and cnfg.optspec_layout == 'ABC')

keymap("Escape actions for dead keys", {
    # special case shortcuts that should cancel dead keys
    C("Esc"):           [getDK(),setDK(None)],                              # Leave accent char if dead keys Escaped
    C("Space"):         [getDK(),setDK(None)],                              # Leave accent char if user hits Space
    C("Delete"):        [getDK(),setDK(None)],                              # Leave accent char if user hits Delete
    C("Backspace"):     [getDK(),C("Backspace"),setDK(None)],               # Delete character if user hits Backspace
    C("Tab"):           [getDK(),C("Tab"),setDK(None)],                     # Leave accent char, insert Tab
    C("Enter"):         [getDK(),C("Enter"),setDK(None)],                   # Leave accent char, Enter key
    C("Up"):            [getDK(),C("Up"),setDK(None)],                      # Leave accent char, up arrow
    C("Down"):          [getDK(),C("Down"),setDK(None)],                    # Leave accent char, down arrow
    C("Left"):          [getDK(),C("Left"),setDK(None)],                    # Leave accent char, left arrow
    C("Right"):         [getDK(),C("Right"),setDK(None)],                   # Leave accent char, right arrow
    C("RC-Tab"):        [getDK(),bind,C("Alt-Tab"),setDK(None)],            # Leave accent char, task switch
    C("Shift-RC-Tab"):  [getDK(),bind,C("Shift-Alt-Tab"),setDK(None)],      # Leave accent char, task switch (reverse)
    C("RC-Grave"):      [getDK(),bind,C("Alt-Grave"),setDK(None)],          # Leave accent char, in-app window switch
    C("Shift-RC-Tab"):  [getDK(),bind,C("Shift-Alt-Grave"),setDK(None)],    # Leave accent char, in-app window switch (reverse)

    # common shortcuts that should also cancel dead keys
    C("RC-a"):                  [getDK(),C("C-a"),setDK(None)],             # Leave accent char, select all
    C("RC-z"):                  [getDK(),C("C-z"),setDK(None)],             # Leave accent char, undo
    C("RC-x"):                  [getDK(),C("C-x"),setDK(None)],             # Leave accent char, cut
    C("RC-c"):                  [getDK(),C("C-c"),setDK(None)],             # Leave accent char, copy
    C("RC-v"):                  [getDK(),C("C-v"),setDK(None)],             # Leave accent char, paste

    ###  activate other dead keys correctly while one is active

    # US layout dead keys
    C("Alt-Grave"):     [getDK(),UC(0x0060),C("Shift-Left"),setDK(0x0060)], # Dead Key Accent: Grave
    C("Alt-E"):         [getDK(),UC(0x00B4),C("Shift-Left"),setDK(0x00B4)], # Dead Key Accent: Acute
    C("Alt-U"):         [getDK(),UC(0x00A8),C("Shift-Left"),setDK(0x00A8)], # Dead Key Accent: Umlaut/Diaeresis
    C("Alt-I"):         [getDK(),UC(0x02C6),C("Shift-Left"),setDK(0x02C6)], # Dead Key Accent: Circumflex
    C("Alt-N"):         [getDK(),UC(0x02DC),C("Shift-Left"),setDK(0x02DC)], # Dead Key Accent: Tilde

    # ABC Extended layout dead keys (not here, see keymap above)


    # cancel dead keys with number keys row
    C("Grave"):                 [getDK(),C("Grave"),setDK(None)],
    C("Key_1"):                 [getDK(),C("Key_1"),setDK(None)],
    C("Key_2"):                 [getDK(),C("Key_2"),setDK(None)],
    C("Key_3"):                 [getDK(),C("Key_3"),setDK(None)],
    C("Key_4"):                 [getDK(),C("Key_4"),setDK(None)],
    C("Key_5"):                 [getDK(),C("Key_5"),setDK(None)],
    C("Key_6"):                 [getDK(),C("Key_6"),setDK(None)],
    C("Key_7"):                 [getDK(),C("Key_7"),setDK(None)],
    C("Key_8"):                 [getDK(),C("Key_8"),setDK(None)],
    C("Key_9"):                 [getDK(),C("Key_9"),setDK(None)],
    C("Key_0"):                 [getDK(),C("Key_0"),setDK(None)],
    C("Minus"):                 [getDK(),C("Minus"),setDK(None)],
    C("Equal"):                 [getDK(),C("Equal"),setDK(None)],
    C("Shift-Grave"):           [getDK(),C("Shift-Grave"),setDK(None)],
    C("Shift-Key_1"):           [getDK(),C("Shift-Key_1"),setDK(None)],
    C("Shift-Key_2"):           [getDK(),C("Shift-Key_2"),setDK(None)],
    C("Shift-Key_3"):           [getDK(),C("Shift-Key_3"),setDK(None)],
    C("Shift-Key_4"):           [getDK(),C("Shift-Key_4"),setDK(None)],
    C("Shift-Key_5"):           [getDK(),C("Shift-Key_5"),setDK(None)],
    C("Shift-Key_6"):           [getDK(),C("Shift-Key_6"),setDK(None)],
    C("Shift-Key_7"):           [getDK(),C("Shift-Key_7"),setDK(None)],
    C("Shift-Key_8"):           [getDK(),C("Shift-Key_8"),setDK(None)],
    C("Shift-Key_9"):           [getDK(),C("Shift-Key_9"),setDK(None)],
    C("Shift-Key_0"):           [getDK(),C("Shift-Key_0"),setDK(None)],
    C("Shift-Minus"):           [getDK(),C("Shift-Minus"),setDK(None)],
    C("Shift-Equal"):           [getDK(),C("Shift-Equal"),setDK(None)],

    # cancel dead keys with any letter on the keyboard that isn't supported by the dead key
    C("A"):                     [getDK(),C("A"),setDK(None)],
    C("B"):                     [getDK(),C("B"),setDK(None)],
    C("C"):                     [getDK(),C("C"),setDK(None)],
    C("D"):                     [getDK(),C("D"),setDK(None)],
    C("E"):                     [getDK(),C("E"),setDK(None)],
    C("F"):                     [getDK(),C("F"),setDK(None)],
    C("G"):                     [getDK(),C("G"),setDK(None)],
    C("H"):                     [getDK(),C("H"),setDK(None)],
    C("I"):                     [getDK(),C("I"),setDK(None)],
    C("J"):                     [getDK(),C("J"),setDK(None)],
    C("K"):                     [getDK(),C("K"),setDK(None)],
    C("L"):                     [getDK(),C("L"),setDK(None)],
    C("M"):                     [getDK(),C("M"),setDK(None)],
    C("N"):                     [getDK(),C("N"),setDK(None)],
    C("O"):                     [getDK(),C("O"),setDK(None)],
    C("P"):                     [getDK(),C("P"),setDK(None)],
    C("Q"):                     [getDK(),C("Q"),setDK(None)],
    C("R"):                     [getDK(),C("R"),setDK(None)],
    C("S"):                     [getDK(),C("S"),setDK(None)],
    C("T"):                     [getDK(),C("T"),setDK(None)],
    C("U"):                     [getDK(),C("U"),setDK(None)],
    C("V"):                     [getDK(),C("V"),setDK(None)],
    C("W"):                     [getDK(),C("W"),setDK(None)],
    C("X"):                     [getDK(),C("X"),setDK(None)],
    C("Y"):                     [getDK(),C("Y"),setDK(None)],
    C("Z"):                     [getDK(),C("Z"),setDK(None)],
    C("Shift-A"):               [getDK(),C("Shift-A"),setDK(None)],
    C("Shift-B"):               [getDK(),C("Shift-B"),setDK(None)],
    C("Shift-C"):               [getDK(),C("Shift-C"),setDK(None)],
    C("Shift-D"):               [getDK(),C("Shift-D"),setDK(None)],
    C("Shift-E"):               [getDK(),C("Shift-E"),setDK(None)],
    C("Shift-F"):               [getDK(),C("Shift-F"),setDK(None)],
    C("Shift-G"):               [getDK(),C("Shift-G"),setDK(None)],
    C("Shift-H"):               [getDK(),C("Shift-H"),setDK(None)],
    C("Shift-I"):               [getDK(),C("Shift-I"),setDK(None)],
    C("Shift-J"):               [getDK(),C("Shift-J"),setDK(None)],
    C("Shift-K"):               [getDK(),C("Shift-K"),setDK(None)],
    C("Shift-L"):               [getDK(),C("Shift-L"),setDK(None)],
    C("Shift-M"):               [getDK(),C("Shift-M"),setDK(None)],
    C("Shift-N"):               [getDK(),C("Shift-N"),setDK(None)],
    C("Shift-O"):               [getDK(),C("Shift-O"),setDK(None)],
    C("Shift-P"):               [getDK(),C("Shift-P"),setDK(None)],
    C("Shift-Q"):               [getDK(),C("Shift-Q"),setDK(None)],
    C("Shift-R"):               [getDK(),C("Shift-R"),setDK(None)],
    C("Shift-S"):               [getDK(),C("Shift-S"),setDK(None)],
    C("Shift-T"):               [getDK(),C("Shift-T"),setDK(None)],
    C("Shift-U"):               [getDK(),C("Shift-U"),setDK(None)],
    C("Shift-V"):               [getDK(),C("Shift-V"),setDK(None)],
    C("Shift-W"):               [getDK(),C("Shift-W"),setDK(None)],
    C("Shift-X"):               [getDK(),C("Shift-X"),setDK(None)],
    C("Shift-Y"):               [getDK(),C("Shift-Y"),setDK(None)],
    C("Shift-Z"):               [getDK(),C("Shift-Z"),setDK(None)],

    # cancel dead keys with other punctuation keys
    C("Left_Brace"):            [getDK(),C("Left_Brace"),setDK(None)],
    C("Right_Brace"):           [getDK(),C("Right_Brace"),setDK(None)],
    C("Backslash"):             [getDK(),C("Backslash"),setDK(None)],
    C("Semicolon"):             [getDK(),C("Semicolon"),setDK(None)],
    C("Apostrophe"):            [getDK(),C("Apostrophe"),setDK(None)],
    C("Comma"):                 [getDK(),C("Comma"),setDK(None)],
    C("Dot"):                   [getDK(),C("Dot"),setDK(None)],
    C("Slash"):                 [getDK(),C("Slash"),setDK(None)],
    C("Shift-Left_Brace"):      [getDK(),C("Shift-Left_Brace"),setDK(None)],
    C("Shift-Right_Brace"):     [getDK(),C("Shift-Right_Brace"),setDK(None)],
    C("Shift-Backslash"):       [getDK(),C("Shift-Backslash"),setDK(None)],
    C("Shift-Semicolon"):       [getDK(),C("Shift-Semicolon"),setDK(None)],
    C("Shift-Apostrophe"):      [getDK(),C("Shift-Apostrophe"),setDK(None)],
    C("Shift-Comma"):           [getDK(),C("Shift-Comma"),setDK(None)],
    C("Shift-Dot"):             [getDK(),C("Shift-Dot"),setDK(None)],
    C("Shift-Slash"):           [getDK(),C("Shift-Slash"),setDK(None)],

}, when = lambda _: ac_Chr_main in deadkeys_list)

keymap("Disable Dead Keys Tripwire",{
    # Nothing needs to be here. Tripwire keymap to disable active dead keys keymap(s)
}, when = lambda _: setDK(None)())



##############################################################################
###                                                                        ###
###                                                                        ###
###       █████  ██████   ██████     ███    ███  █████  ██ ███    ██       ###
###      ██   ██ ██   ██ ██          ████  ████ ██   ██ ██ ████   ██       ###
###      ███████ ██████  ██          ██ ████ ██ ███████ ██ ██ ██  ██       ###
###      ██   ██ ██   ██ ██          ██  ██  ██ ██   ██ ██ ██  ██ ██       ###
###      ██   ██ ██████   ██████     ██      ██ ██   ██ ██ ██   ████       ###
###                                                                        ###
###                                                                        ###
##############################################################################
# Main keymap for special characters on the ABC Extended layout
keymap("OptSpecialChars - ABC", {

    # Number keys row with Option
    ######################################################
    C("Alt-Grave"):     [UC(0x0060),C("Shift-Left"),setDK(0x0060)],     # Dead Key Accent: Grave

    C("Alt-1"):                 UC(0x00A1),                     # ¡ Inverted Exclamation Mark
    C("Alt-2"):                 UC(0x2122),                     # ™ Trade Mark Sign Emoji
    C("Alt-3"):                 UC(0x00A3),                     # £ British Pound currency symbol
    C("Alt-4"):                 UC(0x00A2),                     # ¢ Cent currency symbol
    C("Alt-5"):                 UC(0x00A7),                     # § Section symbol

    C("Alt-6"):         [UC(0x02C6),C("Shift-Left"),setDK(0x02C6)],     # Dead Key Accent: Circumflex

    C("Alt-7"):                 UC(0x00B6),                     # ¶ Paragraph mark (Pilcrow) symbol
    C("Alt-8"):                 UC(0x2022),                     # • Bullet Point symbol (solid)
    C("Alt-9"):                 UC(0x00AA),                     # ª Feminine Ordinal Indicator
    C("Alt-0"):                 UC(0x00BA),                     # º Masculine Ordinal Indicator
    C("Alt-Minus"):             UC(0x2013),                     # – En Dash punctuation mark
    C("Alt-Equal"):             UC(0x2260),                     # ≠ Not Equal To symbol

    # Number keys row with Shift+Option
    ######################################################
    C("Shift-Alt-Grave"):       UC(0x0300),                     # ` Combining Grave Accent
    C("Shift-Alt-1"):           UC(0x2044),                     # ⁄ Fraction Slash
    C("Shift-Alt-2"):           UC(0x20AC),                     # € Euro currency symbol
    C("Shift-Alt-3"):           UC(0x2039),                     # ‹ Single Left-Pointing Angle Quotation mark
    C("Shift-Alt-4"):           UC(0x203A),                     # › Single Right-Pointing Angle Quotation mark
    C("Shift-Alt-5"):           UC(0x2020),                     # † Simple dagger (cross) symbol
    C("Shift-Alt-6"):           UC(0x0302),                     #  ̂ Combining Circumflex Accent
    C("Shift-Alt-7"):           UC(0x2021),                     # ‡ Double dagger (cross) symbol
    C("Shift-Alt-8"):           UC(0x00B0),                     # ° Degree Sign
    C("Shift-Alt-9"):           UC(0x00B7),                     # · Middle Dot (interpunct/middot)
    C("Shift-Alt-0"):           UC(0x201A),                     # ‚ Single low-9 quotation mark
    C("Shift-Alt-Minus"):       UC(0x2014),                     # — Em Dash punctuation mark
    C("Shift-Alt-Equal"):       UC(0x00B1),                     # ± Plus Minus mathematical symbol

    # Tab key row with Option
    ######################################################
    C("Alt-Q"):                 UC(0x0153),                     # œ Small oe (oethel) ligature

    C("Alt-W"):         [UC(0x02D9),C("Shift-Left"),setDK(0x02D9)],     # Dead Key Accent: Dot Above
    C("Alt-E"):         [UC(0x00B4),C("Shift-Left"),setDK(0x00B4)],     # Dead Key Accent: Acute

    C("Alt-R"):                 UC(0x00AE),                     # ® Registered Trade Mark Sign
    C("Alt-T"):                 UC(0x00FE),                     # þ Latin Small Letter Thorn
    C("Alt-Y"):                 UC(0x00A5),                     # ¥ Japanese Yen currency symbol

    C("Alt-U"):         [UC(0x00A8),C("Shift-Left"),setDK(0x00A8)],     # Dead Key Accent: Umlaut/Diaeresis
    C("Alt-I"):         [UC(0x02BC),C("Shift-Left"),setDK(0x02BC)],     # Dead Key Accent: Apostrophe/Horn

    C("Alt-O"):                 UC(0x00F8),                     # ø Latin Small Letter o with Stroke

    C("Alt-P"):         [UC(0x002C),C("Shift-Left"),setDK(0x002C)],     # Dead Key Accent: Comma Below

    C("Alt-Left_Brace"):        UC(0x201C),                     # “ Left Double Quotation Mark
    C("Alt-Right_Brace"):       UC(0x2018),                     # ‘ Left Single Quotation Mark
    C("Alt-Backslash"):         UC(0x00AB),                     # « Left-Pointing Double Angle Quotation Mark

    # Tab key row with Shift+Option
    ######################################################
    C("Shift-Alt-Q"):           UC(0x0152),                     # Œ Capital OE (Oethel) ligature
    C("Shift-Alt-W"):           UC(0x0307),                     # ˙ Combining Dot Above
    C("Shift-Alt-E"):           UC(0x0301),                     #  ́ Combining Acute Accent
    C("Shift-Alt-R"):           UC(0x2030),                     # ‰ Per mille symbol (zero over zero-zero)
    C("Shift-Alt-T"):           UC(0x00DE),                     # Þ Latin Capital Letter Thorn

    # C("Shift-Alt-Y"):           UC(0x02F5), # UC(0x030F),       # ̏  Combining Double Grave Accent
    # Spacing issues when using Combining Double Grave {U+030F}
    # Substituting {U+02F5}: ˵ Modifier Letter Middle Double Grave Accent for initial presentation
    C("Shift-Alt-Y"):   [UC(0x02F5),C("Shift-Left"),setDK(0x02F5)],     # Dead Key Accent: Double Grave

    C("Shift-Alt-U"):           UC(0x0308),                     #  ̈ Combining Diaeresis/Umlaut
    C("Shift-Alt-I"):           UC(0x031B),                     # ̛ Combining Horn (Apostrophe)
    C("Shift-Alt-O"):           UC(0x00D8),                     # Ø Latin Capital Letter O with Stroke
    C("Shift-Alt-P"):           UC(0x0326),                     #  ̦ Combining Comma Below
    C("Shift-Alt-Left_Brace"):  UC(0x201D),                     # ” Right Double Quotation Mark
    C("Shift-Alt-Right_Brace"): UC(0x2019),                     # ’ Right Single Quotation Mark
    C("Shift-Alt-Backslash"):   UC(0x00BB),                     # » Right-Pointing Double Angle Quotation Mark

    # CapsLock key row with Option
    ######################################################

    C("Alt-A"):         [UC(0x00AF),C("Shift-Left"),setDK(0x00AF)],     # Dead Key Accent: Macron/Line Above

    C("Alt-S"):                 UC(0x00DF),                     # ß German Eszett/beta (Sharfes/Sharp S)
    C("Alt-D"):                 UC(0x00F0),                     # ð Latin Small Letter Eth
    C("Alt-F"):                 UC(0x0192),                     # ƒ Function/florin currency symbol
    C("Alt-G"):                 UC(0x00A9),                     # © Copyright Sign

    C("Alt-H"):         [UC(0x02CD),C("Shift-Left"),setDK(0x02CD)],     # Dead Key Accent: Low Macron/Line Below
    C("Alt-J"):         [UC(0x02DD),C("Shift-Left"),setDK(0x02DD)],     # Dead Key Accent: Double Acute
    C("Alt-K"):         [UC(0x02DA),C("Shift-Left"),setDK(0x02DA)],     # Dead Key Accent: Ring Above
    C("Alt-L"):         [UC(0x002D),C("Shift-Left"),setDK(0x002D)],     # Dead Key Accent: Stroke/Hyphen-Minus

    C("Alt-Semicolon"):         UC(0x2026),                     # … Horizontal ellipsis
    C("Alt-Apostrophe"):        UC(0x00E6),                     # æ Small ae ligature

    # CapsLock key row with Shift+Option
    ######################################################
    C("Shift-Alt-A"):           UC(0x0304),                     #  ̄ Combining Macron/Line Below

    # C("Shift-Alt-S"): [UC(0x0311),C("Shift-Left"),setDK(0x0311)],   # Dead Key Accent: Combining Inverted Breve
    # Combining Inverted Breve has spacing problems
    # Substituting {U+1D16}: ᴖ Latin Small Letter Top Half O
    C("Shift-Alt-S"):   [UC(0x1D16),C("Shift-Left"),setDK(0x1D16)],     # Dead Key Accent: Inverted Breve

    C("Shift-Alt-D"):           UC(0x00D0),                     # Ð Latin Capital Letter Eth

    # C("Shift-Alt-F"):   [UC(0x0330),C("Shift-Left"),setDK(0x0330)],     # Dead Key Accent: Tilde Below
    # Combining Tilde Below has spacing problems
    # Substituting {U+02F7}: ˷ Modifier Letter Low Tilde
    C("Shift-Alt-F"):   [UC(0x02F7),C("Shift-Left"),setDK(0x02F7)],     # Dead Key Accent: Tilde Below
    C("Shift-Alt-G"):   [UC(0x2038),C("Shift-Left"),setDK(0x2038)],     # Dead Key Accent: Caret/Circumflex Below

    C("Shift-Alt-H"):           UC(0x0331),                     # ̱  Combining Macron/Line Below
    C("Shift-Alt-J"):           UC(0x030B),                     #  ̋ Combining Double Acute Accent
    C("Shift-Alt-K"):           UC(0x030A),                     #  ̊ Combining Ring Above
    C("Shift-Alt-L"):           UC(0x0335),                     #  ̵ Combining Short Stroke Overlay

    C("Shift-Alt-Semicolon"):  [UC(0x2116),C("Shift-Left"),setDK(0x2116)],      # Dead Key Accent: Numero Sign

    C("Shift-Alt-Apostrophe"):  UC(0x00C6),                     # Æ Capital AE ligature

    # Shift keys row with Option
    ######################################################

    C("Alt-Z"): [UC(0x02C0),C("Shift-Left"),setDK(0x02C0)],     # Dead Key Accent: Hook Above/Glottal Stop
    C("Alt-X"): [UC(0x002E),C("Shift-Left"),setDK(0x002E)],     # Dead Key Accent: Dot Below
    C("Alt-C"): [UC(0x00B8),C("Shift-Left"),setDK(0x00B8)],     # Dead Key Accent: Cedilla/Cedille
    C("Alt-V"): [UC(0x02C7),C("Shift-Left"),setDK(0x02C7)],     # Dead Key Accent: Caron/hacek
    C("Alt-B"): [UC(0x02D8),C("Shift-Left"),setDK(0x02D8)],     # Dead Key Accent: Breve
    C("Alt-N"): [UC(0x02DC),C("Shift-Left"),setDK(0x02DC)],     # Dead Key Accent: Tilde
    C("Alt-M"): [UC(0x02DB),C("Shift-Left"),setDK(0x02DB)],     # Dead Key Accent: Ogonek

    C("Alt-Comma"):             UC(0x2264),                     # ≤ Less Than or Equal To symbol
    C("Alt-Dot"):               UC(0x2265),                     # ≥ Greater Than or Equal To symbol
    C("Alt-Slash"):             UC(0x00F7),                     # ÷ Obelus/Division symbol

    # Shift keys row with Shift+Option
    ######################################################
    C("Shift-Alt-Z"):           UC(0x0309),                     # ̉  Combining Hook Above (hoi)
    C("Shift-Alt-X"):           UC(0x0323),                     # ̣  Combining Dot Below (nang)
    C("Shift-Alt-C"):           UC(0x0327),                     #  ̧ Combining Cedilla
    C("Shift-Alt-V"):           UC(0x030C),                     #  ̌ Combining Caron/hacek
    C("Shift-Alt-B"):           UC(0x0306),                     #  ̆ Combining Breve
    C("Shift-Alt-N"):           UC(0x0303),                     #  ̃ Combining Tilde
    C("Shift-Alt-M"):           UC(0x0328),                     #  ̨ Combining Ogonek (nasal hook)
    C("Shift-Alt-Comma"):       UC(0x201E),                     # „ Double Low-9 Quotation Mark

    C("Shift-Alt-Dot"): [UC(0x0294),C("Shift-Left"),setDK(0x0294)],     # Dead Key Accent: Hook

    C("Shift-Alt-Slash"):       UC(0x00BF),                     # ¿ Inverted Question mark

}, when = lambda ctx:
    cnfg.screen_has_focus and
    cnfg.optspec_layout == 'ABC' and
    matchProps(not_clas=terms_and_remotes_Str)(ctx)
)



######################################################################
###                                                                ###
###                                                                ###
###      ██    ██ ███████     ███    ███  █████  ██ ███    ██      ###
###      ██    ██ ██          ████  ████ ██   ██ ██ ████   ██      ###
###      ██    ██ ███████     ██ ████ ██ ███████ ██ ██ ██  ██      ###
###      ██    ██      ██     ██  ██  ██ ██   ██ ██ ██  ██ ██      ###
###       ██████  ███████     ██      ██ ██   ██ ██ ██   ████      ###
###                                                                ###
###                                                                ###
######################################################################
# Main keymap for special characters on the standard US layout
keymap("OptSpecialChars - US", {

    # Number keys row with Option
    ######################################################
    C("Alt-Grave"): [UC(0x0060), C("Shift-Left"), setDK(0x0060)],       # Dead Key Accent: Grave

    C("Alt-1"):                 UC(0x00A1),                     # ¡ Inverted Exclamation Mark
    C("Alt-2"):                 UC(0x2122),                     # ™ Trade Mark Sign Emoji
    C("Alt-3"):                 UC(0x00A3),                     # £ British Pound currency symbol
    C("Alt-4"):                 UC(0x00A2),                     # ¢ Cent currency symbol
    C("Alt-5"):                 UC(0x221E),                     # ∞ Infinity mathematical symbol
    C("Alt-6"):                 UC(0x00A7),                     # § Section symbol
    C("Alt-7"):                 UC(0x00B6),                     # ¶ Paragraph mark (Pilcrow) symbol
    C("Alt-8"):                 UC(0x2022),                     # • Bullet Point symbol (solid)
    C("Alt-9"):                 UC(0x00AA),                     # ª Feminine Ordinal Indicator
    C("Alt-0"):                 UC(0x00BA),                     # º Masculine Ordinal Indicator
    C("Alt-Minus"):             UC(0x2013),                     # – En Dash punctuation mark
    C("Alt-Equal"):             UC(0x2260),                     # ≠ Not Equal To symbol

    # Number keys row with Shift+Option
    ######################################################
    C("Shift-Alt-Grave"):       UC(0x0060),                     # ` Grave Accent (non-combining)
    C("Shift-Alt-1"):           UC(0x2044),                     # ⁄ Fraction Slash
    C("Shift-Alt-2"):           UC(0x20AC),                     # € Euro currency symbol
    C("Shift-Alt-3"):           UC(0x2039),                     # ‹ Single Left-Pointing Angle Quotation mark
    C("Shift-Alt-4"):           UC(0x203A),                     # › Single Right-Pointing Angle Quotation mark
    C("Shift-Alt-5"):           UC(0xFB01),                     # ﬁ Latin Small Ligature Fi
    C("Shift-Alt-6"):           UC(0xFB02),                     # ﬂ Latin Small Ligature Fl
    C("Shift-Alt-7"):           UC(0x2021),                     # ‡ Double dagger (cross) symbol
    C("Shift-Alt-8"):           UC(0x00B0),                     # ° Degree Sign
    C("Shift-Alt-9"):           UC(0x00B7),                     # · Middle Dot (interpunct/middot)
    C("Shift-Alt-0"):           UC(0x201A),                     # ‚ Single low-9 quotation mark
    C("Shift-Alt-Minus"):       UC(0x2014),                     # — Em Dash punctuation mark
    C("Shift-Alt-Equal"):       UC(0x00B1),                     # ± Plus Minus mathematical symbol

    # Tab key row with Option
    ######################################################
    C("Alt-Q"):                 UC(0x0153),                     # œ Small oe (oethel) ligature
    C("Alt-W"):                 UC(0x2211),                     # ∑ N-Ary Summation (sigma) notation

    C("Alt-E"):         [UC(0x00B4), C("Shift-Left"), setDK(0x00B4)],   # Dead Key Accent: Acute

    C("Alt-R"):                 UC(0x00AE),                     # ® Registered Trade Mark Sign
    C("Alt-T"):                 UC(0x2020),                     # † Simple dagger (cross) symbol
    C("Alt-Y"):                 UC(0x00A5),                     # ¥ Japanese Yen currency symbol

    C("Alt-U"):         [UC(0x00A8), C("Shift-Left"), setDK(0x00A8)],   # Dead Key Accent: Umlaut/Diaeresis

    C("Alt-I"):         [UC(0x02C6), C("Shift-Left"), setDK(0x02C6)],   # Dead Key Accent: Circumflex

    C("Alt-O"):                 UC(0x00F8),                     # ø Latin Small Letter o with Stroke
    C("Alt-P"):                 UC(0x03C0),                     # π Greek Small Letter Pi
    C("Alt-Left_Brace"):        UC(0x201C),                     # “ Left Double Quotation Mark
    C("Alt-Right_Brace"):       UC(0x2018),                     # ‘ Left Single Quotation Mark
    C("Alt-Backslash"):         UC(0x00AB),                     # « Left-Pointing Double Angle Quotation Mark

    # Tab key row with Shift+Option
    ######################################################
    C("Shift-Alt-Q"):           UC(0x0152),                     # Œ Capital OE (Oethel) ligature
    C("Shift-Alt-W"):           UC(0x201E),                     # „ Double Low-9 Quotation mark
    C("Shift-Alt-E"):           UC(0x00B4),                     # ´ Acute Accent diacritic (non-combining)
    C("Shift-Alt-R"):           UC(0x2030),                     # ‰ Per mille symbol (zero over zero-zero)
    C("Shift-Alt-T"):           UC(0x02C7),                     # ˇ Caron/hacek diacritic (non-combining)
    C("Shift-Alt-Y"):           UC(0x00C1),                     # Á Latin Capital Letter A with Acute
    C("Shift-Alt-U"):           UC(0x00A8),                     # ¨ Diaeresis/Umlaut (non-combining)
    C("Shift-Alt-I"):           UC(0x02C6),                     # ˆ Circumflex Accent (non-combining)
    C("Shift-Alt-O"):           UC(0x00D8),                     # Ø Latin Capital Letter O with Stroke
    C("Shift-Alt-P"):           UC(0x220F),                     # ∏ N-Ary Product mathematical symbol
    C("Shift-Alt-Left_Brace"):  UC(0x201D),                     # ” Right Double Quotation Mark
    C("Shift-Alt-Right_Brace"): UC(0x2019),                     # ’ Right Single Quotation Mark
    C("Shift-Alt-Backslash"):   UC(0x00BB),                     # » Right-Pointing Double Angle Quotation Mark

    # CapsLock key row with Option
    ######################################################
    C("Alt-A"):                 UC(0x00E5),                     # å Small Letter a with Ring Above
    C("Alt-S"):                 UC(0x00DF),                     # ß German Eszett/beta (Sharfes/Sharp S)
    C("Alt-D"):                 UC(0x2202),                     # ∂ Partial Differential
    C("Alt-F"):                 UC(0x0192),                     # ƒ Function/florin currency symbol
    C("Alt-G"):                 UC(0x00A9),                     # © Copyright Sign
    C("Alt-H"):                 UC(0x02D9),                     # ˙ Dot Above diacritic (non-combining)
    C("Alt-J"):                 UC(0x2206),                     # ∆ Increment, laplace operator symbol
    C("Alt-K"):                 UC(0x02DA),                     # ˚ Ring Above diacritic (non-combining)
    C("Alt-L"):                 UC(0x00AC),                     # ¬ Not Sign angled dash symbol
    C("Alt-Semicolon"):         UC(0x2026),                     # … Horizontal ellipsis
    C("Alt-Apostrophe"):        UC(0x00E6),                     # æ Small ae ligature

    # CapsLock key row with Shift+Option
    ######################################################
    C("Shift-Alt-A"):           UC(0x00C5),                     # Å Capital Letter A with Ring Above
    C("Shift-Alt-S"):           UC(0x00CD),                     # Í Latin Capital Letter I with Acute
    C("Shift-Alt-D"):           UC(0x00CE),                     # Î Latin Capital Letter I with Circumflex
    C("Shift-Alt-F"):           UC(0x00CF),                     # Ï Latin Capital Letter I with Diaeresis
    C("Shift-Alt-G"):           UC(0x02DD),                     # ˝ Double Acute Accent (non-combining)
    C("Shift-Alt-H"):           UC(0x00D3),                     # Ó Latin Capital Letter O with Acute
    C("Shift-Alt-J"):           UC(0x00D4),                     # Ô Latin Capital Letter O with Circumflex
    #########################################################################################################
    # The Apple logo is at {U+F8FF} in a Unicode Private Use Area. Only at that location in Mac fonts.
    # Symbol exists at {U+F000} in Baskerville Old Face font.
    C("Shift-Alt-K"):   [apple_logo_alert,UC(0xF000)],          #  Apple logo [req's Baskerville Old Face font]
    C("Shift-Alt-L"):           UC(0x00D2),                     # Ò Latin Capital Letter O with Grave
    C("Shift-Alt-Semicolon"):   UC(0x00DA),                     # Ú Latin Capital Letter U with Acute
    C("Shift-Alt-Apostrophe"):  UC(0x00C6),                     # Æ Capital AE ligature

    # Shift keys row with Option
    ######################################################
    C("Alt-Z"):                 UC(0x03A9),                     # Ω Greek Capital Letter Omega
    C("Alt-X"):                 UC(0x2248),                     # ≈ Almost Equal To symbol
    C("Alt-C"):                 UC(0x00E7),                     # ç Small Letter c with Cedilla
    C("Alt-V"):                 UC(0x221A),                     # √ Square Root radical sign
    C("Alt-B"):                 UC(0x222B),                     # ∫ Integral mathematical symbol

    C("Alt-N"): [UC(0x02DC), C("Shift-Left"), setDK(0x02DC)],   # Dead Key Accent: Tilde

    C("Alt-M"):                 UC(0x00B5),                     # µ Micro (mu) symbol
    C("Alt-Comma"):             UC(0x2264),                     # ≤ Less Than or Equal To symbol
    C("Alt-Dot"):               UC(0x2265),                     # ≥ Greater Than or Equal To symbol
    C("Alt-Slash"):             UC(0x00F7),                     # ÷ Obelus/Division symbol

    # Shift keys row with Shift+Option
    ######################################################
    C("Shift-Alt-Z"):           UC(0x00B8),                     # ¸ Spacing Cedilla diacritic (non-combining)
    C("Shift-Alt-X"):           UC(0x02DB),                     # ˛ Ogonek diacritic (non-combining)
    C("Shift-Alt-C"):           UC(0x00C7),                     # Ç Capital Letter C with Cedilla
    C("Shift-Alt-V"):           UC(0x25CA),                     # ◊ Lozenge (diamond) shape symbol
    C("Shift-Alt-B"):           UC(0x0131),                     # ı Latin Small Letter Dotless i
    C("Shift-Alt-N"):           UC(0x02DC),                     # ˜ Small Tilde character
    C("Shift-Alt-M"):           UC(0x00C2),                     # Â Latin Capital Letter A with Circumflex
    C("Shift-Alt-Comma"):       UC(0x00AF),                     # ¯ Macron/overline/overbar (non-combining)
    C("Shift-Alt-Dot"):         UC(0x02D8),                     # ˘ Breve diacritic (non-combining)
    C("Shift-Alt-Slash"):       UC(0x00BF),                     # ¿ Inverted Question mark

}, when = lambda ctx:
    cnfg.screen_has_focus and
    cnfg.optspec_layout == 'US' and
    matchProps(not_clas=terms_and_remotes_Str)(ctx)
)



####################################  USER APPS  #####################################
###                                                                                ###
###                                                                                ###
###      ██    ██ ███████ ███████ ██████       █████  ██████  ██████  ███████      ###
###      ██    ██ ██      ██      ██   ██     ██   ██ ██   ██ ██   ██ ██           ###
###      ██    ██ ███████ █████   ██████      ███████ ██████  ██████  ███████      ###
###      ██    ██      ██ ██      ██   ██     ██   ██ ██      ██           ██      ###
###       ██████  ███████ ███████ ██   ██     ██   ██ ██      ██      ███████      ###
###                                                                                ###
###                                                                                ###
######################################################################################
### This is a good location in the config file for adding new custom keymaps for
### user applications and custom function keys. Watch out that you don't override
### any "general" shortcuts like Cmd+Z/X/C/V that may be defined below this section.
### Changes made between the "slice" marks will be retained by the Toshy installer
### if you reinstall and it finds matching start/end markers for each section.

###################################################################################################
###  SLICE_MARK_START: user_apps  ###  EDITS OUTSIDE THESE MARKS WILL BE LOST ON UPGRADE


keymap("User hardware keys", {
    # PUT UNIVERSAL REMAPS FOR HARDWARE KEYS HERE
    # KEYMAP WILL BE ACTIVE IN ALL DESKTOP ENVIRONMENTS/DISTROS


}, when = lambda ctx:
    cnfg.screen_has_focus and
    matchProps(not_clas=remoteStr)(ctx)
)

###  SLICE_MARK_END: user_apps  ###  EDITS OUTSIDE THESE MARKS WILL BE LOST ON UPGRADE
###################################################################################################


# HOW TO SWAP CMD+SPACE AND CTRL+SPACE (SPOTLIGHT EQUIVALENT VS INPUT SWITCHING)
# Copy this entire block into the "user_apps" editable slice markers, and
# uncomment everything below this text. Fix the output shortcuts to work on your
# chosen desktop environment.
#
# keymap("User overrides terminals", {
#     C("LC-Space"):              [iEF2NT(),C("THE-REAL-COMBO-FOR-SOME-LAUNCHER")],    # Spotlight equivalent
#     C("Shift-LC-Space"):        None,    # block the default general terminals shortcut for input switching
# }, when = lambda ctx:
#       cnfg.screen_has_focus and
#       matchProps(clas=termStr)(ctx)
# )
# keymap("User overrides general", {
#     C("Super-Space"):           [iEF2NT(),C("THE-REAL-COMBO-FOR-SOME-LAUNCHER")],    # Spotlight equivalent
#     C("Shift-Super-Space"):     None,    # block the default general GUI shortcut for reverse input switching
#     ### Keyboard input source (language/layout) switching
#     C("RC-Space"):              [bind,C("THE-REAL-COMBO-FOR-INPUT-SWITCHING")],    # input switch forward
#     C("Shift-RC-Space"):        [bind,C("THE-REAL-COMBO-FOR-REVERSE-INPUT-SWITCHING")],    # input switch reverse (OPTIONAL)
# }, when = lambda ctx:
#       cnfg.screen_has_focus and
#       matchProps(clas=remoteStr)(ctx)
# )



#################################  MISC APPS  #####################################
###                                                                             ###
###                                                                             ###
###      ███    ███ ██ ███████  ██████      █████  ██████  ██████  ███████      ###
###      ████  ████ ██ ██      ██          ██   ██ ██   ██ ██   ██ ██           ###
###      ██ ████ ██ ██ ███████ ██          ███████ ██████  ██████  ███████      ###
###      ██  ██  ██ ██      ██ ██          ██   ██ ██      ██           ██      ###
###      ██      ██ ██ ███████  ██████     ██   ██ ██      ██      ███████      ###
###                                                                             ###
###                                                                             ###
###################################################################################
# Miscellaneous apps that need a few fixes

keymap("Thunderbird email client", {
    C("Alt-RC-I"):              C("Shift-C-I"),                 # Dev tools
    # Enable Cmd+Option+Left/Right for tab navigation
    C("RC-Alt-Left"):          [bind,C("C-Page_Up")],           # Go to prior tab (macOS Thunderbird tab nav shortcut)
    C("RC-Alt-Right"):         [bind,C("C-Page_Down")],         # Go to next tab (macOS Thunderbird tab nav shortcut)
}, when = lambda ctx:
    cnfg.screen_has_focus and
    matchProps(clas="^thunderbird.*$|^org.mozilla.thunderbird$")(ctx) )

keymap("Angry IP Scanner", {
    C("RC-comma"):              C("Shift-C-P"),                 # Open preferences
    C("RC-i"):                  C("Alt-Enter"),                 # Get info (details)
    C("RC-h"):                  C("C-h"),                       # Go to next live host (override hide window)
    C("Shift-RC-i"):            C("C-i"),                       # Invert selection
}, when = lambda ctx:
    cnfg.screen_has_focus and
    matchProps(clas="^Angry.*IP.*Scanner$")(ctx) )

keymap("Transmission bittorrent client", {
    C("RC-i"):                  C("Alt-Enter"),                 # Open properties (Get Info) dialog
    C("RC-comma"):             [C("Alt-e"),C("p")],             # Open preferences (settings) dialog
}, when = lambda ctx:
    cnfg.screen_has_focus and
    matchProps(clas=transmissionStr)(ctx) )

keymap("JDownloader", {
    # Fixes for tab navigation done here instead of in the main tab nav fix keymaps,
    # because we have to use a "list of dicts" to match some  JDownloader windows.
    C("Shift-RC-Left_Brace"):  [bind,C("C-Shift-Tab")],         # Tab nav: Go to prior tab (left)
    C("Shift-RC-Right_Brace"): [bind,C("C-Tab")],               # Tab nav: Go to next tab (right)
    C("Shift-RC-Left"):        [bind,C("C-Shift-Tab")],         # Tab nav: Go to prior tab (left)
    C("Shift-RC-Right"):       [bind,C("C-Tab")],               # Tab nav: Go to next tab (right)

    C("RC-i"):                  C("Alt-Enter"),                 # Open properties
    C("RC-Backspace"):          C("Delete"),                    # Remove download from list
    C("RC-Comma"):              C("C-P"),                       # Open preferences (settings)
}, when = lambda ctx:
    cnfg.screen_has_focus and
    matchProps(lst=JDownloader_lod)(ctx) )

keymap("Totem video player", {
    C("RC-dot"):                C("C-q"),                       # Stop (quit player, there is no "Stop" function)
}, when = lambda ctx:
    cnfg.screen_has_focus and
    matchProps(clas="^totem$")(ctx) )

keymap("GNOME image viewer", {
    C("RC-i"):                  C("Alt-Enter"),                 # Image properties
}, when = lambda ctx:
    cnfg.screen_has_focus and
    matchProps(clas="^eog$")(ctx) )

keymap("LibreOffice Writer", {
    C("RC-comma"):              C("Alt-F12"),                   # Tools > Options (preferences dialog)
}, when = lambda ctx:
    cnfg.screen_has_focus and
    matchProps(clas="^libreoffice-writer$")(ctx) )



########################################  FINDER MODS  #############################################
###                                                                                              ###
###                                                                                              ###
###     ███████ ██ ███    ██ ██████  ███████ ██████      ███    ███  ██████  ██████  ███████     ###
###     ██      ██ ████   ██ ██   ██ ██      ██   ██     ████  ████ ██    ██ ██   ██ ██          ###
###     █████   ██ ██ ██  ██ ██   ██ █████   ██████      ██ ████ ██ ██    ██ ██   ██ ███████     ###
###     ██      ██ ██  ██ ██ ██   ██ ██      ██   ██     ██  ██  ██ ██    ██ ██   ██      ██     ###
###     ██      ██ ██   ████ ██████  ███████ ██   ██     ██      ██  ██████  ██████  ███████     ###
###                                                                                              ###
###                                                                                              ###
####################################################################################################

###  START OF FILE MANAGER GROUP OF KEYMAPS - FINDER MODS  ###

# Keybindings overrides for Caja
# (overrides some bindings from general file manager code block below)
keymap("Overrides for Caja - Finder Mods", {
    C("RC-Super-o"):            C("Shift-C-Enter"),             # Open in new tab
    # C("RC-Super-o"):            C("Shift-C-W"),                 # Open in new window
}, when = lambda ctx:
    cnfg.screen_has_focus and
    matchProps(clas="^caja$")(ctx) )

# Keybindings overrides for COSMIC Files
# (overrides some bindings from general file manager code block below)
keymap("Overrides for COSMIC Files - Finder Mods", {
    # No shortcuts yet to change the view modes?
    # TODO: Add Grid/List view mode shortcuts when available (if different from general FMs)
    # Tab nav uses Ctrl+Tab/Shift+Ctrl+Tab
    C("Shift-RC-Left_Brace"):  [bind,C("Shift-C-Tab")],         # Go to prior tab (left)
    C("Shift-RC-Right_Brace"): [bind,C("C-Tab")],               # Go to next tab (right)
    C("Shift-RC-Left"):        [bind,C("Shift-C-Tab")],         # Go to prior tab (left)
    C("Shift-RC-Right"):       [bind,C("C-Tab")],               # Go to next tab (right)
    # COSMIC uses nonstandard shortcut (Space) for file/folder Properties dialog
    C("RC-i"):                  C("Space"),                     # Get info (properties) [MacOS shortcut]
    C("Alt-Enter"):             C("Space"),                     # Get info (properties) [Linux shortcut]
}, when = lambda ctx:
    cnfg.screen_has_focus and
    matchProps(clas="^com.system76.CosmicFiles$")(ctx) )

# Keybindings overrides for DDE (Deepin) File Manager
# (overrides some bindings from general file manager code block below)
keymap("Overrides for DDE File Manager - Finder Mods", {
    C("RC-i"):                  C("C-i"),                       # File properties dialog (Get Info)
    C("RC-comma"):              None,                           # Disable preferences shortcut (no shortcut available)
    C("RC-Up"):                 C("C-Up"),                      # Go Up dir
    C("Shift-RC-Left_Brace"):  [bind,C("C-Shift-Tab")],         # Go to prior tab
    C("Shift-RC-Right_Brace"): [bind,C("C-Tab")],               # Go to next tab
    C("Shift-RC-Left"):        [bind,C("C-Shift-Tab")],         # Go to prior tab
    C("Shift-RC-Right"):       [bind,C("C-Tab")],               # Go to next tab
}, when = lambda ctx:
    cnfg.screen_has_focus and
    matchProps(clas="^dde-file-manager$")(ctx) )

##########################  DOLPHIN KEYMAPS - BEGIN  ##########################
# Keybindings overrides for Dolphin (KDE file manager)
# (overrides some bindings from general file manager code block below)

keymap("Overrides for Dolphin - Finder Mods pre-KF6", {
    # KDE Frameworks 6 assigns F10 to "Open Main Manu" so this is only valid for KF5 now
    # (Reference https://planet.kde.org/felix-ernst-2023-10-13-f10-for-accessibility-in-kf6/)
    C("Shift-RC-n"):            iEF2(C("F10"), False),          # Create new folder (F10), toggle Enter to be Enter (pre-KF6!)
}, when = lambda ctx:
    cnfg.screen_has_focus and
    DESKTOP_ENV == 'kde' and DE_MAJ_VER in ['5', '4', '3'] and
    matchProps(clas="^dolphin$|^org.kde.dolphin$")(ctx)
)

# Dolphin dialog names where Enter should always be Enter (not F2/Enter toggle)
dlgs_Dolphin_Enter_is_Enter = [
    "Edit Places Entry.*",
    "Create New File.*",
    "Folder Already Exists.*",
    "File Already Exists.*",
]
# Convert list to regex pattern string
dlgs_Dolphin_Enter_is_Enter_Str = toRgxStr(dlgs_Dolphin_Enter_is_Enter)

keymap("Overrides for Dolphin dialogs - Finder Mods", {
    C("Enter"):                 C("Enter"),                     # Override Enter to be Enter (never F2) for dialogs
}, when = lambda ctx:
    cnfg.screen_has_focus and
    matchProps(clas="^dolphin$|^org.kde.dolphin$", name=dlgs_Dolphin_Enter_is_Enter_Str)(ctx)
)

keymap("Overrides for Dolphin - Finder Mods", {
    C("RC-r"):                  C("F5"),                        # Refresh folder view with Cmd+R (like browsers)
    C("RC-KEY_2"):              C("C-KEY_3"),                   # View as List (Detailed)
    C("RC-KEY_3"):              C("C-KEY_2"),                   # View as List (Compact)
    ##########################################################################################
    ### "Open in new window" (or new tab) requires manually setting custom shortcut of Ctrl+Shift+o
    ### in Dolphin's keyboard shortcuts. There is no default shortcut set for this function.
    ##########################################################################################
    C("RC-Super-o"):            C("Shift-C-o"),                 # Open in new window (or new tab, user's choice, see above)
    C("Shift-RC-n"):            iEF2(C("Shift-C-n"), False),    # Create new folder, toggle Enter to be Enter (KF6 and later)
    C("RC-comma"):              C("Shift-C-comma"),             # Open preferences dialog
}, when = lambda ctx:
    cnfg.screen_has_focus and
    matchProps(clas="^dolphin$|^org.kde.dolphin$")(ctx) )

#
###########################  DOLPHIN KEYMAPS - END  ###########################


# Keybindings overrides for elementary OS Files (Pantheon)
# (overrides some bindings from general file manager code block below)
keymap("Overrides for Pantheon - Finder Mods", {
    C("RC-Super-o"):            C("Shift-Enter"),               # Open folder in new tab
    C("RC-comma"):              None,                           # Disable preferences shortcut since none available
}, when = lambda ctx:
    cnfg.screen_has_focus and
    matchProps(clas="^io.elementary.files$")(ctx) )

# Keybindings overrides for Krusader (alternative/old KDE file manager)
# (overrides some bindings from general file manager code block below)
keymap("Overrides for Krusader - Finder Mods", {
    C("Shift-RC-Dot"):          C("Alt-Dot"),                   # Toggle hidden files visibility ("dot" files)
    # C("RC-n"):                  None,                           # Enable this to block Cmd+N (new window is not possible?)
    C("RC-Shift-n"):            iEF2(C("F7"), False),           # New folder (F7)
    C("RC-KEY_1"):              None,                           # View as Icons [Not available, blocked]
    C("RC-KEY_2"):              C("Alt-Shift-D"),               # View as List (Detailed)
    C("RC-KEY_3"):              C("Alt-Shift-B"),               # View as List (Compact)
    C("RC-KEY_4"):              None,                           # View as Gallery [Not available, blocked]
    C("RC-Backspace"):         [C("Delete"), sleep(0.5), C("Tab"), sleep(0.5), C("Enter")],    # Delete file/folder (auto-confirm)
    # C("RC-Backspace"):          C("Delete"),                    # Delete file/folder (no auto-confirm)
}, when = lambda ctx:
    cnfg.screen_has_focus and
    matchProps(clas="^org.kde.krusader$|^krusader$")(ctx) )

# Keybindings overrides for Nautilus
# (overrides some bindings from general file manager code block below)
keymap("Overrides for Nautilus Create Archive dialog - Finder Mods", {
    C("Enter"):                 C("Enter"),                     # Use Enter as Enter in the Create Archive dialog
}, when = lambda ctx:
    cnfg.screen_has_focus and
    matchProps(clas="^org.gnome.nautilus$|^nautilus$", name="Create Archive")(ctx) )

keymap("Overrides for Nautilus - Finder Mods", {
    # Optional "new window at home folder" in Nautilus
    # C("RC-N"):                  C("C-Alt-Space"),               # macOS Finder search window shortcut Cmd+Option+Space
    # For the above shortcut to work, a custom shortcut bound to Ctrl+Alt+Space must be set up in the
    # Settings app in GNOME to run command: "nautilus --new-window /home/USER" [ replace "USER" ]
    C("RC-KEY_1"):              C("C-KEY_2"),                   # View as Icons
    C("RC-KEY_2"):              C("C-KEY_1"),                   # View as List (Detailed)
    # C("RC-Super-o"):            C("Shift-Enter"),               # Open in new window (disable line below)
    C("RC-Super-o"):            C("C-Enter"),                   # Open in new tab (disable line above)
    C("RC-comma"):              C("C-comma"),                   # Overrides "Open preferences dialog" shortcut below
    C("RC-F"):                  C("C-F"),                       # Don't toggle Enter key, pass Cmd+F
}, when = lambda ctx:
    cnfg.screen_has_focus and
    matchProps(clas="^org.gnome.nautilus$|^nautilus$")(ctx) )

# Keybindings overrides for Nemo
# (overrides some bindings from general file manager code block below)
keymap("Overrides for Nemo - Finder Mods", {
    C("RC-Backspace"):          iEF2(C("Delete"), False),       # Set Enter to Enter for Cmd+Delete confirmation
}, when = lambda ctx:
    cnfg.screen_has_focus and
    matchProps(clas="^nemo$")(ctx) )

# Keybindings overrides for PCManFM and PCManFM-Qt
# (overrides some bindings from general file manager code block below)
keymap("Overrides for PCManFM-Qt - Finder Mods - LXQt desktop", {
    C("Enter"):                 C("Enter"),                     # Use Enter as Enter on the LXQt desktop
}, when = lambda ctx:
    cnfg.screen_has_focus and
    matchProps(clas="^pcmanfm-qt$", name="^pcmanfm-desktop.*$")(ctx) )
keymap("Overrides for PCManFM-Qt - Finder Mods", {
    C("RC-Backspace"):          C("Delete"),                    # Move to Trash (delete, bypass dialog)
    # Change folder view
    C("RC-KEY_1"):  [C("Alt-V"), sleep(0.1), C("V"), sleep(0.1), C("I")],   # View as Icons
    C("RC-KEY_2"):  [C("Alt-V"), sleep(0.1), C("V"), sleep(0.1), C("D")],   # View as List (Detailed)
    C("RC-KEY_3"):  [C("Alt-V"), sleep(0.1), C("V"), sleep(0.1), C("C")],   # View as List (Compact)
    C("RC-KEY_4"):  [C("Alt-V"), sleep(0.1), C("V"), sleep(0.1), C("T")],   # View as Thumbnails
}, when = lambda ctx:
    cnfg.screen_has_focus and
    matchProps(clas="^pcmanfm-qt$")(ctx) )

keymap("Overrides for PCManFM - Finder Mods", {
    C("RC-KEY_2"):              C("C-KEY_4"),                   # View as List (Detailed) [Not in PCManFM-Qt]
    C("RC-Backspace"):         [C("Delete"),C("Space")],        # Move to Trash (delete, bypass dialog)
    C("RC-F"):                  C("C-F"),                       # Don't toggle Enter key state, pass Cmd+F (Ctrl+F)
}, when = lambda ctx:
    cnfg.screen_has_focus and
    matchProps(clas="^pcmanfm$|^pcmanfm-qt$")(ctx) )

keymap("Overrides for Peony-Qt - Finder Mods", {
    C("RC-Comma"):              None,                           # Block Cmd+Comma (doesn't work in Peony)
    C("RC-Equal"):              C("Shift-C-Equal"),             # Enlarge icons
    C("Shift-RC-Left_Brace"):  [bind,C("C-Shift-Tab")],         # Go to prior tab
    C("Shift-RC-Right_Brace"): [bind,C("C-Tab")],               # Go to next tab
    C("Shift-RC-Left"):        [bind,C("C-Shift-Tab")],         # Go to prior tab
    C("Shift-RC-Right"):       [bind,C("C-Tab")],               # Go to next tab
}, when = lambda ctx:
    cnfg.screen_has_focus and
    matchProps(clas="^peony-qt$")(ctx) )

# Keybindings overrides for SpaceFM
# (overrides some bindings from general file manager code block below)
keymap("Overrides for SpaceFM Find Files dialog - Finder Mods", {
    C("Enter"):                 C("Enter"),                     # Use Enter as Enter in the Find dialog
    C("Esc"):                   C("Alt-F4"),                    # Close Find Files dialog with Escape
    C("RC-W"):                  C("Alt-F4"),                    # Close Find Files dialog with Cmd+W
}, when = lambda ctx:
    cnfg.screen_has_focus and
    matchProps(clas="^SpaceFM$", name="Find Files")(ctx) )

keymap("Overrides for SpaceFM - Finder Mods", {
    C("RC-Page_Up"):           [bind,C("C-Shift-Tab")],         # Go to prior tab
    C("RC-Page_Down"):         [bind,C("C-Tab")],               # Go to next tab
    C("Shift-RC-Left_Brace"):  [bind,C("C-Shift-Tab")],         # Go to prior tab
    C("Shift-RC-Right_Brace"): [bind,C("C-Tab")],               # Go to next tab
    C("Shift-RC-Left"):        [bind,C("C-Shift-Tab")],         # Go to prior tab
    C("Shift-RC-Right"):       [bind,C("C-Tab")],               # Go to next tab
    C("Shift-RC-N"):            iEF2(C("C-F"), False),          # Switch Enter to Enter. New folder is Ctrl+F(???)
    # Need to catch WM_NAME of "Find Files" and override Enter key state back to being Enter. See above keymap.
    C("RC-F"):                  None,                           # No direct shortcut available and menu macros don't work in SpaceFM.
    C("RC-Backspace"):         [C("Delete"),C("Space")],        # Move to Trash (delete, bypass dialog)
    C("RC-comma"):             [C("Alt-V"),C("p")],             # Overrides "Open preferences dialog" shortcut below
    # This shortcut ^^^^^^^^^^^^^^^ is not fully working in SpaceFM. Opens "View" menu but not Preferences.
    # SpaceFM is doing some nasty binding that blocks all shortcuts, including Alt+Tab, while any menu is open.
}, when = lambda ctx:
    cnfg.screen_has_focus and
    matchProps(clas="^spacefm$")(ctx) )

# Keybindings overrides for Thunar
# (overrides some bindings from general file manager code block below)
keymap("Overrides for Thunar - Finder Mods", {
    C("RC-Super-o"):            C("Shift-C-P"),                 # Open in new tab
    C("RC-comma"):             [C("Alt-E"),C("E")],             # Overrides "Open preferences dialog" shortcut below
    C("RC-F"):                  C("C-F"),                       # Don't toggle Enter key, pass Cmd+F (Ctrl+F)
}, when = lambda ctx:
    cnfg.screen_has_focus and
    matchProps(clas="^thunar$")(ctx) )

# Keybindings overrides for GNOME XDG "Save As" and "Open File" dialogs
file_open_save_dialogs = [
    {
        clas: "^xdg-desktop-portal-gnome$|^Firefox.*$|^LibreWolf$|^Waterfox$|^zen.*$",
        name: "^Open File$|^Save As$"
    },
]
keymap("XDG file dialogs", {
    C("RC-Left"):               C("Alt-Left"),                  # Go Back
    C("RC-Right"):              C("Alt-Right"),                 # Go Forward
    C("RC-Up"):                 C("Alt-Up"),                    # Go Up dir
    C("RC-Down"):               C("Enter"),                     # Go Down dir (open folder/file) [universal]
}, when = lambda ctx:
    cnfg.screen_has_focus and
    matchProps(lst=file_open_save_dialogs)(ctx)
)

####################################################################################################
##  Keybindings for Linux general file managers group:
##
##  Currently supported Linux file managers (file browsers):
##
##  Caja File Browser       (MATE file manager, fork of Nautilus)
##  COSMIC Files            (Pop!_OS COSMIC desktop environment file manager)
##  DDE File Manager        (Deepin Linux file manager)
##  Dolphin                 (KDE file manager)
##  Krusader                (Alternative/old KDE file manager)
##  Nautilus                (GNOME file manager, may be named "Files")
##  Nemo                    (Cinnamon file manager, fork of Nautilus, may be named "Files")
##  Pantheon Files          (elementary OS file manager, may be named "Files")
##  PCManFM                 (LXDE file manager)
##  PCManFM-Qt              (LXQt file manager)
##  Peony-Qt                (UKUI file manager, found in Ubuntu Kylin)
##  SpaceFM                 (Fork of PCManFM file manager)
##  Thunar File Manager     (Xfce file manager)
##
##  GNOME XDG file dialogs ("Open File" and "Save As" windows in apps like Firefox)
##
####################################################################################################

keymap("General File Managers - Finder Mods", {
    ###########################################################################################################
    ###  Show Properties (Get Info) | Open Settings/Preferences | Toggle hidden files visibility            ###
    ###########################################################################################################
    C("RC-i"):                  C("Alt-Enter"),                 # File properties dialog (Get Info)
    C("RC-comma"):             [C("Alt-E"),C("N")],             # Open preferences dialog
    C("Shift-RC-dot"):          C("C-H"),                       # Toggle hidden files visibility ("dot" files)
    ###########################################################################################################
    ###  Navigation                                                                                         ###
    ###########################################################################################################

    # C("Shift-RC-Left_Brace"):   C("C-Page_Up"),                 # Go to prior tab
    # C("Shift-RC-Right_Brace"):  C("C-Page_Down"),               # Go to next tab

    C("Shift-RC-Left_Brace"):   [bind,C("C-Page_Up")],          # Go to prior tab
    C("Shift-RC-Right_Brace"):  [bind,C("C-Page_Down")],        # Go to next tab

    # C("Shift-RC-Left"):         C("C-Page_Up"),                 # Go to prior tab
    # C("Shift-RC-Right"):        C("C-Page_Down"),               # Go to next tab

    C("Shift-RC-Left"):         [bind,C("C-Page_Up")],          # Go to prior tab
    C("Shift-RC-Right"):        [bind,C("C-Page_Down")],        # Go to next tab

    C("RC-Left_Brace"):         C("Alt-Left"),                  # Go Back
    C("RC-Right_Brace"):        C("Alt-Right"),                 # Go Forward

    # C("RC-Left"):               C("Alt-Left"),                  # Go Back
    # C("RC-Right"):              C("Alt-Right"),                 # Go Forward
    # C("RC-Up"):                 C("Alt-Up"),                    # Go Up dir
    # C("RC-Down"):               C("Enter"),                     # Go Down dir (open folder/file) [universal]
    # EXPERIMENTAL: Attempt to get wordwise Cmd+Left/Right to work while renaming, but otherwise be navigation
    C("RC-Left"):           iEF2(C("Alt-Left"), C("Home"), True, True),      # Go Back
    C("RC-Right"):          iEF2(C("Alt-Right"), C("End"), True, True),      # Go Forward
    C("RC-Up"):             iEF2(C("Alt-Up"), True),            # Go Up dir
    C("RC-Down"):           iEF2(C("Enter"), True),             # Go Down dir (open folder/file) [universal]

    # C("RC-Down"):               C("Alt-Down"),                  # Go Down dir (only works on folders) [not universal]
    # C("RC-Down"):               C("C-O"),                       # Go Down dir (open folder/file) [not universal]
    ###########################################################################################################
    ###  Open in New Window | Move to Trash                                                                 ###
    ###########################################################################################################
    C("RC-Super-o"):            C("Shift-C-o"),                 # Open in new window (or tab, depends) [not universal]
    C("RC-Backspace"):          C("Delete"),	                # Move to Trash (delete)
    C("RC-Delete"):             None,                           # Block Ctrl+Delete from performing any action (error in macOS)
    ###########################################################################################################
    ###  ENTER-KEY-TO-RENAME CUSTOM FUNCTION SHORTCUTS                                                      ###
    ###########################################################################################################
    C("Enter"):             iEF2(C("F2"),C("Enter")),           # Send F2 to rename files, unless var is False
    C("Shift-RC-N"):        iEF2(C("Shift-C-N"), False),        # New folder, set Enter to Enter
    C("RC-L"):              iEF2(C("C-L"), False),              # Set Enter to Enter for Location field
    C("RC-F"):              iEF2(C("C-F"), False),              # Set Enter to Enter for Find field
    C("Esc"):               iEF2(C("Esc"), True),               # Send Escape, set Enter to be F2 next
    # C("Tab"):               iEF2(C("Tab"), C("Tab"), True, True),       # Set Enter to Enter after using Tab key
    C("Shift-RC-Space"):    iEF2(C("Shift-C-Space"), False),    # Set Enter to Enter for alternate overview shortcut
    C("Shift-RC-Enter"):        C("Enter"),                             # alternative "Enter" key for unusual cases
}, when = lambda ctx:
    cnfg.screen_has_focus and
    matchProps(clas=filemanagerStr)(ctx) )



###################################  BROWSERS  #####################################
###                                                                              ###
###                                                                              ###
###      ██████  ██████   ██████  ██     ██ ███████ ███████ ██████  ███████      ###
###      ██   ██ ██   ██ ██    ██ ██     ██ ██      ██      ██   ██ ██           ###
###      ██████  ██████  ██    ██ ██  █  ██ ███████ █████   ██████  ███████      ###
###      ██   ██ ██   ██ ██    ██ ██ ███ ██      ██ ██      ██   ██      ██      ###
###      ██████  ██   ██  ██████   ███ ███  ███████ ███████ ██   ██ ███████      ###
###                                                                              ###
###                                                                              ###
####################################################################################

keymap("Firefox Browsers Overrides", {

    C("C-comma"):              [C("C-t"), sleep(0.2),
                                ST("about:preferences"),
                                sleep(0.2), C("Enter")],        # Open preferences (Settings)

    # Open private window with Cmd+Shift+N like other browsers
    C("Shift-RC-N"):            C("Shift-C-P"),

    # Wordwise shortcuts (overrides of general wordwise)
    C("RC-Backspace"):         [C("Shift-Home"),
                                C("Backspace")],                # Delete Line Left of Cursor
    C("RC-Delete"):            [C("Shift-End"), C("Delete")],   # Delete Line Right of Cursor

    # Specific numbered tab navigation - removed from general browsers keymap
    C("RC-1"):                  C("Alt-1"),                     # Jump to Tab #1
    C("RC-2"):                  C("Alt-2"),                     # Jump to Tab #2
    C("RC-3"):                  C("Alt-3"),                     # Jump to Tab #3
    C("RC-4"):                  C("Alt-4"),                     # Jump to Tab #4
    C("RC-5"):                  C("Alt-5"),                     # Jump to Tab #5
    C("RC-6"):                  C("Alt-6"),                     # Jump to Tab #6
    C("RC-7"):                  C("Alt-7"),                     # Jump to Tab #7
    C("RC-8"):                  C("Alt-8"),                     # Jump to Tab #8
    C("RC-9"):                  C("Alt-9"),                     # Jump to last tab

    # Block shortcuts that might get confused with Shift+Cmd+[Left/Right]_Brace
    C("Shift-RC-Minus"):        ignore_combo,                   # Ignore alternate zoom out shortcut
    C("Shift-RC-Equal"):        ignore_combo,                   # Ignore alternate zoom in shortcut

}, when = lambda ctx:
    cnfg.screen_has_focus and
    matchProps(clas=browsers_firefoxStr)(ctx) )

# Zotero is a Firefox based research app
keymap("Zotero", {
    # (override the Shift+Opt+Cmd+I,I diagnostic dialog shortcut in Zotero)
    C("Shift-Alt-RC-i"):        C("Shift-Alt-C-i"),             # Import from clipboard
}, when = lambda ctx:
    cnfg.screen_has_focus and
    matchProps(clas="^.*Zotero.*$")(ctx) )

keymap("Vivaldi browser - Settings dialog", {
    C("Esc"):                   C("Alt-F4"),                    # Close Settings dialog with Escape
}, when = lambda ctx:
    cnfg.screen_has_focus and
    matchProps(clas="^Vivaldi.*$", name="^Vivaldi Settings:.*Vivaldi$")(ctx) )

# Vivaldi is a Chromium based web browser
keymap("Overrides for Vivaldi browser", {

    # These get caught by the shell in KDE Plasma!!! (Show Desktop and Go to Desktop 1 shortcuts):
    # C("RC-comma"):              C("C-F12"),                     # Open preferences (Settings)
    # C("RC-Slash"):              C("C-F1"),                      # Keyboard Cheat Sheet (shortcuts)

    # This only opens the normal Chrome-like settings page, not the special Vivaldi settings dialog:
    # C("C-comma"):              [C("C-t"), sleep(0.1),
    #                             ST("chrome://settings"),
    #                             sleep(0.1), C("Enter")],        # Open preferences (Settings)

    # Alternatives using macros to avoid issues with KDE Plasma global shortcuts (see above):
    C("RC-Slash"):             [C("F10"),
                                sleep(0.2), C("H"),
                                sleep(0.2), C("K")],            # Keyboard Cheat Sheet (shortcuts)

    C("C-comma"):              [C("F10"),
                                sleep(0.2), C("S")],            # Open preferences (Settings)

}, when = lambda ctx:
    cnfg.screen_has_focus and
    matchProps(clas="^Vivaldi.*$")(ctx) )

# Falkon is a Chromium based web browser
keymap("Overrides for Falkon browser", {
    C("RC-comma"):              C("Shift-C-comma"),             # Open preferences (Settings)
}, when = lambda ctx:
    cnfg.screen_has_focus and
    matchProps(clas="^org.kde.falkon$|^Falkon$")(ctx) )

keymap("Chrome Browsers Overrides", {
    # C("C-comma"):              [C("Alt-e"), C("s"),C("Enter")], # Open preferences (Settings)
    C("C-comma"):              [C("C-t"), sleep(0.2),
                                ST("chrome://settings"),
                                sleep(0.2), C("Enter")],        # Open preferences (Settings)
    C("RC-q"):                  C("Alt-F4"),                    # Quit Chrome(s) browsers with Cmd+Q
    # C("RC-Left"):               C("Alt-Left"),                  # Page nav: Back to prior page in history (conflict with wordwise)
    # C("RC-Right"):              C("Alt-Right"),                 # Page nav: Forward to next page in history (conflict with wordwise)
    C("RC-Left_Brace"):         C("Alt-Left"),                  # Page nav: Back to prior page in history
    C("RC-Right_Brace"):        C("Alt-Right"),                 # Page nav: Forward to next page in history

    C("RC-y"):                  C("C-H"),                       # Browser History
    C("Alt-RC-u"):              C("C-U"),                       # View Page Source
    C("Shift-RC-j"):            C("C-J"),                       # Show Downloads view
}, when = lambda ctx:
    cnfg.screen_has_focus and
    matchProps(clas=browsers_chromeStr)(ctx) )

# Keybindings for General Web Browsers
keymap("General Web Browsers", {

    C("RC-Q"):                  C("C-Q"),                       # Close all browsers Instances
    C("Alt-RC-I"):              C("Shift-C-I"),                 # Dev tools
    C("Alt-RC-J"):              C("Shift-C-J"),                 # Dev tools

    # Enable Cmd+Shift+Braces for tab navigation (redundant with General GUI)
    # C("Shift-RC-Left_Brace"):   C("C-Page_Up"),                 # Go to prior tab
    # C("Shift-RC-Right_Brace"):  C("C-Page_Down"),               # Go to next tab

    # Enable Cmd+Option+Left/Right for tab navigation
    C("RC-Alt-Left"):           C("C-Page_Up"),                 # Go to prior tab
    C("RC-Alt-Right"):          C("C-Page_Down"),               # Go to next tab

    # Enable Ctrl+PgUp/PgDn for tab navigation
    C("Super-Page_Up"):         C("C-Page_Up"),                 # Go to prior tab
    C("Super-Page_Down"):       C("C-Page_Down"),               # Go to next tab

    # Use Cmd+Braces keys for tab navigation instead of page navigation
    # C("C-Left_Brace"):        C("C-Page_Up"),
    # C("C-Right_Brace"):       C("C-Page_Down"),

}, when = lambda ctx:
    cnfg.screen_has_focus and
    matchProps(clas=browsers_allStr)(ctx) )



############################################  CODE EDITORS  ##############################################
###                                                                                                    ###
###                                                                                                    ###
###       ██████  ██████  ██████  ███████     ███████ ██████  ██ ████████  ██████  ██████  ███████     ###
###      ██      ██    ██ ██   ██ ██          ██      ██   ██ ██    ██    ██    ██ ██   ██ ██          ###
###      ██      ██    ██ ██   ██ █████       █████   ██   ██ ██    ██    ██    ██ ██████  ███████     ###
###      ██      ██    ██ ██   ██ ██          ██      ██   ██ ██    ██    ██    ██ ██   ██      ██     ###
###       ██████  ██████  ██████  ███████     ███████ ██████  ██    ██     ██████  ██   ██ ███████     ###
###                                                                                                    ###
###                                                                                                    ###
##########################################################################################################


# Keybindings for IntelliJ
keymap("Jetbrains", {
    # General
    C("C-Key_0"):               C("Alt-Key_0"),                 # Open corresponding tool window
    C("C-Key_1"):               C("Alt-Key_1"),                 # Open corresponding tool window
    C("C-Key_2"):               C("Alt-Key_2"),                 # Open corresponding tool window
    C("C-Key_3"):               C("Alt-Key_3"),                 # Open corresponding tool window
    C("C-Key_4"):               C("Alt-Key_4"),                 # Open corresponding tool window
    C("C-Key_5"):               C("Alt-Key_5"),                 # Open corresponding tool window
    C("C-Key_6"):               C("Alt-Key_6"),                 # Open corresponding tool window
    C("C-Key_7"):               C("Alt-Key_7"),                 # Open corresponding tool window
    C("C-Key_8"):               C("Alt-Key_8"),                 # Open corresponding tool window
    C("C-Key_9"):               C("Alt-Key_9"),                 # Open corresponding tool window
    C("Super-Grave"):           C("C-Grave"),                   # Quick switch current scheme
    C("C-Comma"):               C("C-Alt-s"),                   # Open Settings dialog
    C("C-Semicolon"):           C("C-Alt-Shift-s"),             # Open Project Structure dialog
    # Debugging
    C("C-Alt-r"):               C("F9"),                        # Resume program
    # Search/Replace
    C("C-g"):                   C("F3"),                        # Find next
    C("C-Shift-F3"):            C("Shift-F3"),                  # Find previous
    C("Super-g"):               C("Alt-j"),                     # Select next occurrence
    C("C-Super-g"):             C("C-Alt-Shift-j"),             # Select all occurrences
    C("Super-Shift-g"):         C("Alt-Shift-j"),               # Unselect occurrence
    # Editing
    # C("Super-Space"):           C("C-Space"),                   # Basic code completion (conflicts with input switching)
    # C("Super-Shift-Space"):     C("Shift-C-Space"),             # Smart code completion (conflicts with input switching)
    C("Super-j"):               C("C-q"),                       # Quick documentation lookup
    C("C-n"):                   C("Alt-Insert"),                # Generate code...
    C("Super-o"):               C("C-o"),                       # Override methods
    C("Super-i"):               C("C-i"),                       # Implement methods
    C("Alt-Up"):                C("C-w"),                       # Extend selection
    C("Alt-Down"):              C("C-Shift-w"),                 # Shrink selection
    C("Super-Shift-q"):         C("Alt-q"),                     # Context info
    C("Super-Alt-o"):           C("C-Alt-o"),                   # Optimize imports
    C("Super-Alt-i"):           C("C-Alt-i"),                   # Auto-indent line(s)
    C("C-Backspace"):           C("C-y"),                       # Delete line at caret
    C("Super-Shift-j"):         C("C-Shift-j"),                 # Smart line join
    C("Alt-Delete"):            C("C-Delete"),                  # Delete to word end
    C("Alt-Backspace"):         C("C-Backspace"),               # Delete to word start
    C("C-Shift-Equal"):         C("C-KPPLUS"),                  # Expand code block
    C("C-Minus"):               C("C-KPMINUS"),                 # Collapse code block
    C("C-Shift-Equal"):         C("C-Shift-KPPLUS"),            # Expand all
    C("C-Shift-Minus"):         C("C-Shift-KPMINUS"),           # Collapse all
    C("C-w"):                   C("C-F4"),                      # Close active editor tab
    # Refactoring
    C("C-Delete"):              C("Alt-Delete"),                # Safe Delete
    C("C-T"):                   C("C-Alt-Shift-t"),             # Refactor this
    # Navigation
    C("C-o"):                   C("C-n"),                       # Go to class
    C("C-Shift-o"):             C("C-Shift-n"),                 # Go to file
    C("C-Alt-o"):               C("C-Alt-Shift-n"),             # Go to symbol
    C("Super-Right"):           C("Alt-Right"),                 # Go to next editor tab
    C("Super-Left"):            C("Alt-Left"),                  # Go to previous editor tab
    C("C-l"):                   C("C-g"),                       # Go to line
    C("Alt-Space"):             C("C-Shift-i"),                 # Open quick definition lookup
    C("C-Y"):                   C("C-Shift-i"),                 # Open quick definition lookup
    C("Super-Shift-b"):         C("C-Shift-b"),                 # Go to type declaration
    C("Super-Up"):              C("Alt-Up"),                    # Go to previous
    C("Super-Down"):            C("Alt-Down"),                  # Go to next method
    C("C-Left_Brace"):          C("Alt-Shift-Left"),            # Go back
    C("C-Right_Brace"):         C("Alt-Shift-Right"),           # Go forward
    C("Super-h"):               C("C-h"),                       # Type hierarchy
    C("Super-Alt-h"):           C("C-Alt-h"),                   # Call hierarchy
    C("C-Down"):                C("C-Enter"),                   # Edit source/View source
    C("Alt-Home"):              C("Alt-Home"),                  # Show navigation bar
    C("F2"):                    C("F11"),                       # Toggle bookmark
    C("Super-F3"):              C("C-F11"),                     # Toggle bookmark with mnemonic
    C("Super-Key_0"):           C("C-Key_0"),                   # Go to numbered bookmark
    C("Super-Key_1"):           C("C-Key_1"),                   # Go to numbered bookmark
    C("Super-Key_2"):           C("C-Key_2"),                   # Go to numbered bookmark
    C("Super-Key_3"):           C("C-Key_3"),                   # Go to numbered bookmark
    C("Super-Key_4"):           C("C-Key_4"),                   # Go to numbered bookmark
    C("Super-Key_5"):           C("C-Key_5"),                   # Go to numbered bookmark
    C("Super-Key_6"):           C("C-Key_6"),                   # Go to numbered bookmark
    C("Super-Key_7"):           C("C-Key_7"),                   # Go to numbered bookmark
    C("Super-Key_8"):           C("C-Key_8"),                   # Go to numbered bookmark
    C("Super-Key_9"):           C("C-Key_9"),                   # Go to numbered bookmark
    C("C-F3"):                  C("Shift-F11"),                 # Show bookmarks
    # Compile and Run
    C("Super-Alt-r"):           C("Alt-Shift-F10"),             # Select configuration and run
    C("Super-Alt-d"):           C("Alt-Shift-F9"),              # Select configuration and debug
    C("Super-r"):               C("Shift-F10"),                 # Run
    C("Super-d"):               C("Shift-F9"),                  # Debug
    C("Super-Shift-r"):         C("C-Shift-F10"),               # Run context configuration from editor
    C("Super-Shift-d"):         C("C-Shift-F9"),                # Debug context configuration from editor
    # VCS/Local History
    C("Super-v"):               C("Alt-Grave"),                 # VCS quick popup
    C("Super-c"):               C("C-c"),                       # Sigints - interrupt
}, when = lambda ctx:
    cnfg.screen_has_focus and
    matchProps(clas="^jetbrains-(?!.*toolbox).*$")(ctx) )

keymap("Wordwise - not vscode", {
    # Wordwise remaining - for Everything but VS Code
    C("Alt-Left"):              C("C-Left"),                    # Left of Word
    C("Alt-Shift-Left"):        C("C-Shift-Left"),              # Select Left of Word
    C("Alt-Right"):             C("C-Right"),                   # Right of Word
    C("Alt-Shift-Right"):       C("C-Shift-Right"),             # Select Right of Word
    C("Alt-Shift-g"):           C("C-Shift-g"),                 # View source control
    # ** VS Code fix **
    #   Electron issue precludes normal keybinding fix.
    #   Alt menu auto-focus/toggle gets in the way.
    #
    #   refer to ./xkeysnail-config/vscode_keybindings.json
    # **
    #
    # ** Firefox fix **
    #   User will need to set "ui.key.menuAccessKeyFocuses"
    #   under about:config to false.
    #
    #   https://superuser.com/questions/770301/pentadactyl-how-to-disable-menu-bar-toggle-by-alt
    # **
    #
}, when = lambda ctx:
    cnfg.screen_has_focus and
    matchProps(not_clas=vscodes_and_remotes_Str)(ctx)
)

# Keybindings for VS Code and variants
keymap("VSCodes overrides for Chromebook/IBM - Sublime", {
    C("C-Alt-g"):               C("C-f2"),                      # Chromebook/IBM - Sublime - find_all_under
}, when = lambda ctx:
    cnfg.screen_has_focus and
    cnfg.ST3_in_VSCode and
    (   isKBtype('Chromebook', map="vscodes ovr cbook - sublime")(ctx) or
        isKBtype('IBM', map="vscodes ovr ibm - sublime")(ctx) ) and
    matchProps(clas=vscodeStr)(ctx)
)
keymap("VSCodes overrides for not Chromebook/IBM - Sublime", {
    C("Super-C-g"):             C("C-f2"),                      # Default - Sublime - find_all_under
}, when = lambda ctx:
    cnfg.screen_has_focus and
    cnfg.ST3_in_VSCode and
    not ( isKBtype('Chromebook', map="vscodes ovr not cbook - sublime")(ctx) or
    isKBtype('IBM', map="vscodes ovr not ibm - sublime")(ctx) ) and
    matchProps(clas=vscodeStr)(ctx)
)
keymap("VSCodes overrides for Chromebook/IBM", {
    C("Alt-c"):                 C("C-c"),                       #  Chromebook/IBM - Terminal - Sigint
    C("Alt-x"):                 C("C-x"),                       #  Chromebook/IBM - Terminal - Exit nano
}, when = lambda ctx:
    cnfg.screen_has_focus and
    (   isKBtype('Chromebook', map="vscodes ovr cbook")(ctx) or
        isKBtype('IBM', map="vscodes ovr ibm")(ctx) ) and
    matchProps(clas=vscodeStr)(ctx)
)
keymap("VSCodes overrides for not Chromebook/IBM", {
    C("Super-c"):               C("C-c"),                       # Default - Terminal - Sigint
    C("Super-x"):               C("C-x"),                       # Default - Terminal - Exit nano
}, when = lambda ctx:
    cnfg.screen_has_focus and
    not (   isKBtype('Chromebook', map="vscodes ovr not cbook")(ctx) or
            isKBtype('IBM', map="vscodes ovr not ibm")(ctx) ) and
    matchProps(clas=vscodeStr)(ctx)
)
keymap("VSCodes", {
    # C("Super-Space"):           C("C-Space"),                  # Basic code completion (conflicts with input switching)

    # Override the global Cmd+Dot (Escape/cancel) shortcut for QuickFix in VSCode(s)
    C("RC-Dot"):                C("C-Dot"),                     # QuickFix, overriding global shortcut

    # Override the global copy shortcut, to allow Cmd+C to work properly in the embedded
    # VSCode terminal, without an internal VSCode keyboard shortcut remap.
    C("RC-C"):                 C("C-Insert"),                   # Copy

    # This override unfortunately seems to paste from the "wrong" clipboard. Only pastes content
    # that was copied from within the VSCode window, not content copied from other app windows:
    # C("RC-V"):                 C("Shift-Insert"),               # Paste

    # In-app terminal operations (Cmd+J is "Toggle Panel Visibility" for problems/output/debug/terminal panel)
    C("Super-Grave"):           C("C-Grave"),                   # Terminal: Toggle Terminal
    C("Shift-Super-Grave"):     C("Shift-C-Grave"),             # Terminal: Create New Terminal

    # Find dialog options
    C("Alt-RC-C"):              C("Alt-C"),                     # Find: toggle "Match Case"
    C("Alt-RC-W"):              C("Alt-W"),                     # Find: toggle "Match Whole Word"
    C("Alt-RC-R"):              C("Alt-R"),                     # Find: toggle "Use Regular Expression"
    C("Alt-RC-L"):              C("Alt-L"),                     # Find: toggle "Find in Selection"
    C("Alt-RC-P"):              C("Alt-P"),                     # Replace: toggle "Preserve Case"
    C("RC-Enter"):              C("C-Alt-Enter"),               # Find: Replace All

    C("Alt-RC-Z"):              C("Alt-Z"),                     # View: toggle "Word Wrap"

    C("Alt-RC-Up"):             C("Shift-Alt-Up"),              # Insert cursor above
    C("Alt-RC-Down"):           C("Shift-Alt-Down"),            # Insert cursor below

    C("Shift-Super-Right"):     C("Shift-Alt-Right"),           # Expand Selection (increase logical scope of smart selection)
    C("Shift-Super-Left"):      C("Shift-Alt-Left"),            # Shrink Selection (reduce logical scope of smart selection)

    C("Shift-Super-RC-Right"):  C("Shift-Alt-Right"),           # Expand Selection (increase logical scope of smart selection) [alt]
    C("Shift-Super-RC-Left"):   C("Shift-Alt-Left"),            # Shrink Selection (reduce logical scope of smart selection) [alt]

    # On Mac, Cmd+G and Shift+Cmd+G are for Find Next/Previous.
    # Correct combo on Mac for Source Control sidebar panel is physical Shift+Ctrl+G
    C("Shift-Super-g"):         C("Shift-C-g"),                 # Show Source Control

    # Wordwise remaining - for VS Code
    # Alt-F19 hack fixes Alt menu activation
    C("Alt-Left"):             [C("Alt-F19"),C("C-Left")],          # Left of Word
    C("Alt-Right"):            [C("Alt-F19"),C("C-Right")],         # Right of Word
    C("Alt-Shift-Left"):       [C("Alt-F19"),C("C-Shift-Left")],    # Select Left of Word
    C("Alt-Shift-Right"):      [C("Alt-F19"),C("C-Shift-Right")],   # Select Right of Word

    # To make this work, assign these shortcuts to "deleteWordPartLeft" and "deleteWordPartRight" shortcuts
    C("Shift-Alt-Backspace"):   C("Shift-Alt-Backspace"),        # Delete word left of cursor (override GenGUI)
    C("Shift-Alt-Delete"):      C("Shift-Alt-Delete"),           # Delete word right of cursor (override GenGUI)
    C("RC-Backspace"):         [C("Shift-Home"), C("Delete")],  # Delete entire line left of cursor
    C("RC-Delete"):            [C("Shift-End"), C("Delete")],   # Delete entire line right of cursor

    # C("C-PAGE_DOWN"):           ignore_combo,                   # cancel next_view
    # C("C-PAGE_UP"):             ignore_combo,                   # cancel prev_view
    C("C-Alt-Left"):            C("C-PAGE_UP"),                 # next_view
    C("C-Alt-Right"):           C("C-PAGE_DOWN"),               # prev_view
    C("Shift-RC-Left_Brace"):   C("C-PAGE_UP"),                 # next_view
    C("Shift-RC-Right_Brace"):  C("C-PAGE_DOWN"),               # prev_view

    # VS Code Shortcuts
    C("C-g"):                   ignore_combo,                   # cancel Go to Line...
    C("Super-g"):               C("C-g"),                       # Go to Line...
    C("F3"):                    ignore_combo,                   # cancel Find next
    C("C-h"):                   ignore_combo,                   # cancel replace
    C("C-Alt-f"):               C("C-h"),                       # replace
    C("C-Shift-h"):             ignore_combo,                   # cancel replace_next
    C("C-Alt-e"):               C("C-Shift-h"),                 # replace_next
    C("f3"):                    ignore_combo,                   # cancel find_next
    C("C-g"):                   C("f3"),                        # find_next
    C("Shift-f3"):              ignore_combo,                   # cancel find_prev
    C("C-Shift-g"):             C("Shift-f3"),                  # find_prev
}, when = lambda ctx:
    cnfg.screen_has_focus and
    matchProps(clas=vscodeStr)(ctx)
)

# Keybindings for Sublime Text
keymap("Sublime Text overrides for Chromebook/IBM", {
    C("Alt-c"):                 C("C-c"),                       #  Chromebook/IBM - Terminal - Sigint
    C("Alt-x"):                 C("C-x"),                       #  Chromebook/IBM - Terminal - Exit nano
    C("Alt-Refresh"):           ignore_combo,                   # Chromebook/IBM - cancel find_all_under
    C("Alt-C-g"):               C("Alt-Refresh"),               # Chromebook/IBM - find_all_under
}, when = lambda ctx:
    cnfg.screen_has_focus and
    (   isKBtype('Chromebook', map="sublime ovr cbook")(ctx) or
        isKBtype('IBM', map="sublime ovr ibm")(ctx) ) and
    matchProps(clas=sublimeStr)(ctx)
)
keymap("Sublime Text overrides for not Chromebook/IBM", {
    # C("Super-c"):               C("C-c"),                       # Default - Terminal - Sigint
    # C("Super-x"):               C("C-x"),                       # Default - Terminal - Exit nano
    C("Alt-f3"):                ignore_combo,                   # Default - cancel find_all_under
    C("Super-C-g"):             C("Alt-f3"),                    # Default - find_all_under
}, when = lambda ctx:
    cnfg.screen_has_focus and
    not (   isKBtype('Chromebook', map="sublime ovr not cbook")(ctx) or
            isKBtype('IBM', map="sublime ovr not ibm")(ctx) ) and
    matchProps(clas=sublimeStr)(ctx)
)
keymap("Sublime Text", {
    # C("Super-c"):               C("C-c"),                       # Default - Terminal - Sigint
    # C("Super-x"):               C("C-x"),                       # Default - Terminal - Exit nano
    # C("Alt-c"):                 C("C-c"),                       #  Chromebook/IBM - Terminal - Sigint
    # C("Alt-x"):                 C("C-x"),                       #  Chromebook/IBM - Terminal - Exit nano
    # C("Super-Space"):           C("C-Space"),                   # Basic code completion (conflicts with input switching)
    C("C-Super-up"):            C("Alt-o"),                     # Switch file
    C("Super-RC-f"):            C("f11"),                       # toggle_full_screen
    C("C-Alt-v"):              [C("C-k"), C("C-v")],            # paste_from_history
    # C("C-up"):                  ignore_combo,                   # cancel scroll_lines up
    C("C-Alt-up"):              C("C-up"),                      # scroll_lines up
    # C("C-down"):                ignore_combo,                   # cancel scroll_lines down
    C("C-Alt-down"):            C("C-down"),                    # scroll_lines down
    C("Super-Shift-up"):        C("Alt-Shift-up"),              # multi-cursor up
    C("Super-Shift-down"):      C("Alt-Shift-down"),            # multi-cursor down
    C("C-PAGE_DOWN"):           ignore_combo,                   # cancel next_view
    C("C-PAGE_UP"):             ignore_combo,                   # cancel prev_view
    C("C-Shift-left_brace"):    C("C-PAGE_DOWN"),               # next_view
    C("C-Shift-right_brace"):   C("C-PAGE_UP"),                 # prev_view
    C("C-Alt-right"):           C("C-PAGE_DOWN"),               # next_view
    C("C-Alt-left"):            C("C-PAGE_UP"),                 # prev_view
    C("insert"):                ignore_combo,                   # cancel toggle_overwrite
    C("C-Alt-o"):               C("insert"),                    # toggle_overwrite
    C("Alt-c"):                 ignore_combo,                   # cancel toggle_case_sensitive
    C("C-Alt-c"):               C("Alt-c"),                     # toggle_case_sensitive
    C("C-h"):                   ignore_combo,                   # cancel replace
    C("C-Alt-f"):               C("C-h"),                       # replace
    C("C-Shift-h"):             ignore_combo,                   # cancel replace_next
    C("C-Alt-e"):               C("C-Shift-h"),                 # replace_next
    C("f3"):                    ignore_combo,                   # cancel find_next
    C("C-g"):                   C("f3"),                        # find_next
    C("Shift-f3"):              ignore_combo,                   # cancel find_prev
    C("C-Shift-g"):             C("Shift-f3"),                  # find_prev
    C("C-f3"):                  ignore_combo,                   # cancel find_under
    C("Super-Alt-g"):           C("C-f3"),                      # find_under
    C("C-Shift-f3"):            ignore_combo,                   # cancel find_under_prev
    C("Super-Alt-Shift-g"):     C("C-Shift-f3"),                # find_under_prev
    C("Alt-f3"):                ignore_combo,                   # Default - cancel find_all_under
    C("Super-C-g"):             C("Alt-f3"),                    # Default - find_all_under
    # C("Alt-Refresh"):           ignore_combo,                   # Chromebook/IBM - cancel find_all_under
    # C("Alt-C-g"):               C("Alt-Refresh"),               # Chromebook/IBM - find_all_under
    C("C-Shift-up"):            ignore_combo,                   # cancel swap_line_up
    C("Super-Alt-up"):          C("C-Shift-up"),                # swap_line_up
    C("C-Shift-down"):          ignore_combo,                   # cancel swap_line_down
    C("Super-Alt-down"):        C("C-Shift-down"),              # swap_line_down
    C("C-Pause"):               ignore_combo,                   # cancel cancel_build
    C("Super-c"):               C("C-Pause"),                   # cancel_build
    C("f9"):                    ignore_combo,                   # cancel sort_lines case_s false
    C("f5"):                    C("f9"),                        # sort_lines case_s false
    C("Super-f9"):              ignore_combo,                   # cancel sort_lines case_s true
    C("Super-f5"):              C("Super-f9"),                  # sort_lines case_s true
    C("Alt-Shift-Key_1"):       ignore_combo,                   # cancel set_layout
    C("C-Alt-Key_1"):           C("Alt-Shift-Key_1"),           # set_layout
    C("Alt-Shift-Key_2"):       ignore_combo,                   # cancel set_layout
    C("C-Alt-Key_2"):           C("Alt-Shift-Key_2"),           # set_layout
    C("Alt-Shift-Key_3"):       ignore_combo,                   # cancel set_layout
    C("C-Alt-Key_3"):           C("Alt-Shift-Key_3"),           # set_layout
    C("Alt-Shift-Key_4"):       ignore_combo,                   # cancel set_layout
    C("C-Alt-Key_4"):           C("Alt-Shift-Key_4"),           # set_layout
    C("Alt-Shift-Key_8"):       ignore_combo,                   # cancel set_layout
    C("C-Alt-Shift-Key_2"):     C("Alt-Shift-Key_8"),           # set_layout
    C("Alt-Shift-Key_9"):       ignore_combo,                   # cancel set_layout
    C("C-Alt-Shift-Key_3"):     C("Alt-Shift-Key_9"),           # set_layout
    C("Alt-Shift-Key_5"):       ignore_combo,                   # cancel set_layout
    C("C-Alt-Shift-Key_5"):     C("Alt-Shift-Key_5"),           # set_layout
    # C(""):                    ignore_combo,                   # cancel
    # C(""):                    C(""),                          #
}, when = lambda ctx:
    cnfg.screen_has_focus and
    matchProps(clas=sublimeStr)(ctx) )

keymap("Kate Advanced Text Editor", {
    C("RC-Comma"):              C("Shift-C-Comma"),             # Open settings/preferences
    C("RC-g"):                  C("F3"),                        # Find next
    C("Super-g"):               C("C-g"),                       # Go to line
}, when = lambda ctx:
    cnfg.screen_has_focus and
    matchProps(clas="^org.kde.kate$")(ctx) )

keymap("Linux Mint xed text editor", {
    C("RC-T"):                  C("C-N"),                       # Open new tab (new file)
}, when = lambda ctx:
    cnfg.screen_has_focus and
    matchProps(clas="^xed$")(ctx) )

keymap("KWrite text editor - Close Document dialog", {
    C("RC-d"):                  C("Alt-d"),                     # [D]iscard file without saving (from Close Document dialog)
    C("RC-s"):                  C("Alt-s"),                     # Save file (from Close Document dialog)
}, when = lambda ctx:
    cnfg.screen_has_focus and
    matchProps(clas="^kwrite$|^org.kde.Kwrite$", name="^Close Document.*KWrite$")(ctx) )
keymap("KWrite text editor", {
    C("RC-comma"):              C("Shift-C-comma"),             # Open preferences dialog
    C("RC-t"):                  C("C-n"),                       # New tab (new document appears in tab)
    C("Super-g"):               C("C-g"),                       # Go to line with physical Ctrl+G
    C("RC-g"):                  C("F3"),                        # Find next instance (Cmd+G)
    C("Shift-RC-g"):            C("Shift-F3"),                  # Find previous instance (Shift+Cmd+G)
    # wordwise shortcuts
    C("RC-Backspace"):          C("C-k"),                       # Delete line (Cmd+Delete)
}, when = lambda ctx:
    cnfg.screen_has_focus and
    matchProps(clas="^kwrite$|^org.kde.Kwrite$")(ctx) )

keymap("GNOME Text Editor", {
    C("RC-Slash"):              None,                           # Block Cmd+Slash from doing "Select All"
    C("RC-Alt-f"):              C("C-h"),                       # Search and replace within the document
}, when = lambda ctx:
    cnfg.screen_has_focus and
    matchProps(clas="^gnome-text-editor$|^org.gnome.TextEditor$")(ctx) )


###########################  DIALOG FIXES  ###########################
###                                                                ###
###                                                                ###
###      ██████  ██  █████  ██       ██████   ██████  ███████      ###
###      ██   ██ ██ ██   ██ ██      ██    ██ ██       ██           ###
###      ██   ██ ██ ███████ ██      ██    ██ ██   ███ ███████      ###
###      ██   ██ ██ ██   ██ ██      ██    ██ ██    ██      ██      ###
###      ██████  ██ ██   ██ ███████  ██████   ██████  ███████      ###
###                                                                ###
###                                                                ###
######################################################################
### Fixes for the problem of modal dialogs and other "child"
### windows failing to close with Cmd+W.
### Many dialogs respond to the Escape key, others may require the
### "Close window" shortcut (normally Alt+F4 but not always) to close.
###
### Cmd+W can't just be always mapped to the "Close window" shortcut for all apps
### because some apps will "quit" rather than just closing a tab.
###
### To add window conditions to the list, search for the list names in
### the "LISTS" section near the top of this config file.
### dialogs_Escape_lod = send these windows the Escape key for Cmd+W
### dialogs_CloseWin_lod = send these windows the "Close window" shortcut for Cmd+W

keymap("Cmd+W dialog fix - send Escape", {
    C("RC-W"):                  iEF2(C("Esc"), True),
}, when = lambda ctx:
    cnfg.screen_has_focus and
    matchProps(lst=dialogs_Escape_lod)(ctx)
)

# This keymap for Manjaro GNOME will override the same shortcut from the keymap just below it,
# sending Super+Q to close the dialogs in the matchProps list, instead of sending Alt+F4.
if DISTRO_ID == 'manjaro'  and DESKTOP_ENV == 'gnome':
    keymap("Cmd+W dialog fix - Super+Q Manjaro GNOME", {
        C("RC-W"):                  iEF2(C("Super-Q"), True),
    }, when = lambda ctx:
        cnfg.screen_has_focus and
        matchProps(lst=dialogs_CloseWin_lod)(ctx)
    )

keymap("Cmd+W dialog fix - Alt+F4", {
    C("RC-W"):                  iEF2(C("Alt-F4"), True),
}, when = lambda ctx:
    cnfg.screen_has_focus and
    matchProps(lst=dialogs_CloseWin_lod)(ctx)
)



###########################  TAB NAV FIXES  #############################
###                                                                   ###
###                                                                   ###
###      ████████  █████  ██████      ███    ██  █████  ██    ██      ###
###         ██    ██   ██ ██   ██     ████   ██ ██   ██ ██    ██      ###
###         ██    ███████ ██████      ██ ██  ██ ███████ ██    ██      ###
###         ██    ██   ██ ██   ██     ██  ██ ██ ██   ██  ██  ██       ###
###         ██    ██   ██ ██████      ██   ████ ██   ██   ████        ###
###                                                                   ###
###                                                                   ###
#########################################################################
### Various fixes for supporting tab navigation shortcuts like Shift+Cmd+Braces


tab_UI_fix_CtrlShiftTab_lst = [
    "com.raggesilver.BlackBox",
    "com.system76.CosmicTerm",
    "org.gnome.Console|Console",
    "deepin-terminal",
    "hyper",
    "kitty",
    "Kgx",
]
tab_UI_fix_CtrlShiftTab_Str = toRgxStr(tab_UI_fix_CtrlShiftTab_lst)

tab_UI_fix_CtrlAltPgUp_lst = [
    "gedit",
    "xed",
]
tab_UI_fix_CtrlAltPgUp_Str = toRgxStr(tab_UI_fix_CtrlAltPgUp_lst)

# Tab navigation overrides for tabbed UI apps that use Ctrl+Shift+Tab/Ctrl+Tab instead of Ctrl+PgUp/PgDn
keymap("Tab Nav fix for apps that use Ctrl+Shift+Tab/Ctrl+Tab", {
    C("Shift-RC-Left_Brace"):  [bind,C("C-Shift-Tab")],         # Tab nav: Go to prior tab (left)
    C("Shift-RC-Right_Brace"): [bind,C("C-Tab")],               # Tab nav: Go to next tab (right)
    C("Shift-RC-Left"):        [bind,C("C-Shift-Tab")],         # Tab nav: Go to prior tab (left)
    C("Shift-RC-Right"):       [bind,C("C-Tab")],               # Tab nav: Go to next tab (right)
}, when = lambda ctx:
    cnfg.screen_has_focus and
    matchProps(clas=tab_UI_fix_CtrlShiftTab_Str)(ctx)
)

# Tab navigation overrides for tabbed UI apps that use Ctrl+Alt+PgUp/PgDn instead of Ctrl+PgUp/PgDn
keymap("Tab Nav fix for apps that use Ctrl+Alt+PgUp/PgDn", {
    C("Shift-RC-Left_Brace"):  [bind,C("C-Alt-Page_Up")],       # Go to prior tab (Left)
    C("Shift-RC-Right_Brace"): [bind,C("C-Alt-Page_Down")],     # Go to next tab (Right)
}, when = lambda ctx:
    cnfg.screen_has_focus and
    matchProps(clas=tab_UI_fix_CtrlAltPgUp_Str)(ctx)
)

keymap("Konsole tab switching", {
    # Ctrl Tab - In App Tab Switching
    C("Shift-LC-Tab") :        [bind,C("Shift-Left")],
    C("LC-Tab") :              [bind,C("Shift-Right")],
    C("LC-Grave") :            [bind,C("Shift-Left")],
    # Konsole tab switching in KDE4 (not needed in KDE5)
    C("Shift-RC-Left_Brace"):  [bind,C("Shift-Left")],          # Go to prior tab (Left)
    C("Shift-RC-Right_Brace"): [bind,C("Shift-Right")],         # Go to next tab (Right)
}, when = lambda ctx:
    cnfg.screen_has_focus and
    matchProps(clas="^konsole$|^org.kde.Konsole$")(ctx) )

keymap("Elementary Terminal tab switching", {
    # Ctrl Tab - In App Tab Switching
    C("Shift-LC-Tab") :        [bind,C("Shift-C-Left")],        # Go to prior tab (Left)
    C("LC-Grave") :            [bind,C("Shift-C-Left")],        # Go to prior tab (Left)
    C("LC-Tab") :              [bind,C("Shift-C-Right")],       # Go to next tab (Right)
}, when = lambda ctx:
    cnfg.screen_has_focus and
    matchProps(clas="^Io.elementary.terminal$|^kitty$")(ctx) )



######################################  TERMINALS  #######################################
###                                                                                    ###
###                                                                                    ###
###      ████████ ███████ ██████  ███    ███ ██ ███    ██  █████  ██      ███████      ###
###         ██    ██      ██   ██ ████  ████ ██ ████   ██ ██   ██ ██      ██           ###
###         ██    █████   ██████  ██ ████ ██ ██ ██ ██  ██ ███████ ██      ███████      ###
###         ██    ██      ██   ██ ██  ██  ██ ██ ██  ██ ██ ██   ██ ██           ██      ###
###         ██    ███████ ██   ██ ██      ██ ██ ██   ████ ██   ██ ███████ ███████      ###
###                                                                                    ###
###                                                                                    ###
##########################################################################################

keymap("Alacritty terminal", {
    C("RC-K"):                  C("C-L"),                       # clear log
}, when = lambda ctx:
    cnfg.screen_has_focus and
    matchProps(clas="^alacritty$")(ctx) )


keymap("Contour terminal overrides", {
    C("RC-minus"):              C("Shift-C-minus"),             # Decrease font size (override general terminals remap)
}, when = lambda ctx:
    cnfg.screen_has_focus and
    matchProps(clas="^contour$")(ctx) )


keymap("COSMIC Terminal overrides", {
    # There are already tab nav fixes in the usual place.
    C("RC-equal"):              C("C-equal"),                   # Increase font size (override general terminals remap)
}, when = lambda ctx:
    cnfg.screen_has_focus and
    matchProps(clas="^com.system76.CosmicTerm$")(ctx) )


keymap("Deepin Terminal overrides", {
    C("RC-w"):                  C("Alt-w"),                     # Close only current tab, instead of all other tabs
    C("RC-j"):                  None,                           # Block Cmd+J from remapping to vertical split (Ctrl+Shift+J)
    C("RC-minus"):              C("C-minus"),                   # Decrease font size/zoom out
    C("RC-equal"):              C("C-equal"),                   # Increase font size/zoom in
}, when = lambda ctx:
    cnfg.screen_has_focus and
    matchProps(clas="^deepin-terminal$")(ctx) )

keymap("Ghostty terminal overrides", {
    C("RC-Equal"): C(
        "C-Equal"
    ),              # Increase font size [override general terminals remap]
    C("RC-D"):                  C("RC-Shift-O"),                # Open right split
    C("RC-Shift-D"):            C("RC-Shift-E"),                # Open down split
    C("RC-Alt-I"):              C("RC-Shift-I"),                # Open inspector
    C("RC-K"):                  C("C-L"),                       # clear log
}, when = lambda ctx:
    cnfg.screen_has_focus and
    matchProps(clas="^.*ghostty.*$")(ctx)
)

keymap("Hyper terminal tab switching", {
    C("RC-Equal"):              C("C-Equal"),                   # Increase font size [override general terminals remap]
    C("Shift-LC-Tab"):         [bind,C("Shift-C-Tab")],         # Tab nav: Go to prior tab (left) [override general remap]
    C("LC-Tab"):               [bind,C("C-Tab")],               # Tab nav: Go to next tab (right) [override general remap]
}, when = lambda ctx:
    cnfg.screen_has_focus and
    matchProps(clas="^hyper$")(ctx) )

keymap("Kitty terminal - not tab nav", {
    C("RC-L"):                  C("C-L"),                       # Clear log
    C("RC-K"):                  C("C-L"),                       # Clear log (macOS)
}, when = lambda ctx:
    cnfg.screen_has_focus and
    matchProps(clas="^kitty$")(ctx) )

keymap("Konsole terminal - not tab nav", {
    C("RC-comma"):              C("Shift-C-comma"),             # Open Preferences dialog
    C("RC-0"):                  C("C-Alt-0"),                   # Reset font size
    C("RC-K"):                  C("Shift-C-K"),                 # Clear Scrollback and Reset
}, when = lambda ctx:
    cnfg.screen_has_focus and
    matchProps(clas="^Konsole$|^org.kde.Konsole$")(ctx) )

keymap("Terminology terminal", {
    C("RC-w"):                  C("Shift-C-End"),               # Close focused tab
    C("RC-c"):                  C("Alt-w"),                     # Copy selection to primary buffer
    C("RC-v"):                  C("Alt-Enter"),                 # Paste primary buffer
    C("RC-0"):                  C("C-Alt-0"),                   # Reset font size
    C("RC-Minus"):              C("C-Alt-Minus"),               # Decrease font size
    C("RC-Equal"):              C("C-Alt-Equal"),               # Increase font size
}, when = lambda ctx:
    cnfg.screen_has_focus and
    matchProps(clas="^terminology$")(ctx) )

keymap("Wave terminal", {
    C("RC-t"):                  C("Alt-t"),                     # Open a new tab
    C("RC-n"):                  C("Alt-n"),                     # Open a new terminal block
    C("Shift-RC-n"):            C("Shift-Alt-n"),               # Open a new window
    C("RC-w"):                  C("Alt-w"),                     # Close the current block
    C("Shift-RC-w"):            C("Shift-Alt-w"),               # Close the current tab
}, when = lambda ctx:
    cnfg.screen_has_focus and
    matchProps(clas="^Wave$")(ctx) )

keymap("Xfce4 terminal", {
    C("RC-comma"):      [C("Alt-e"), sleep(0.1), C("e")],       # Open Preferences dialog
}, when = lambda ctx:
    cnfg.screen_has_focus and
    matchProps(clas="^xfce4-terminal$")(ctx) )


# Overrides to General Terminals shortcuts for specific distros (or are they really just desktop environments?)

if DISTRO_ID in ['fedora', 'almalinux'] and DESKTOP_ENV == 'gnome':
    keymap("GenTerms overrides: Fedora GNOME", {
        C("RC-H"):                  C("Super-h"),                   # Hide Window/Minimize app (gnome/fedora)
    }, when = lambda ctx:
        cnfg.screen_has_focus and
        matchProps(clas=termStr)(ctx)
    )

if DISTRO_ID == 'pop':
    keymap("GenTerms overrides: Pop!_OS", {
        C("LC-Right"):              [bind,C("Super-C-Up")],         # SL - Change workspace (pop)
        C("LC-Left"):               [bind,C("Super-C-Down")],       # SL - Change workspace (pop)
    }, when = lambda ctx:
        cnfg.screen_has_focus and
        matchProps(clas=termStr)(ctx)
    )

if DISTRO_ID in ['ubuntu', 'fedora'] and DESKTOP_ENV == 'gnome':
    keymap("GenTerms overrides: Ubuntu/Fedora", {
        C("LC-RC-Q"):               C("Super-L"),                   # Lock screen (ubuntu/fedora)
        C("LC-Right"):              [bind,C("Super-Page_Up")],      # SL - Change workspace (ubuntu/fedora)
        C("LC-Left"):               [bind,C("Super-Page_Down")],    # SL - Change workspace (ubuntu/fedora)
    }, when = lambda ctx:
        cnfg.screen_has_focus and
        matchProps(clas=termStr)(ctx)
    )


# Overrides to General Terminals shortcuts for specific desktop environments

if DESKTOP_ENV == 'budgie':
    keymap("GenTerms overrides: Budgie", {
        C("LC-Right"):              [bind,C("C-Alt-Right")],        # Default SL - Change workspace (budgie)
        C("LC-Left"):               [bind,C("C-Alt-Left")],         # Default SL - Change workspace (budgie)
    }, when = lambda ctx:
        cnfg.screen_has_focus and
        matchProps(clas=termStr)(ctx)
    )

# On Pop!_OS 22.04, System76 seems to have changed the name of the DE from 'cosmic' to 'pop'.
# Probably to avoid overlapping with the new COSMIC desktop environment in Pop!_OS 24.04 and later.
if DESKTOP_ENV in ['cosmic', 'pop']:
    keymap("GenTerms overrides: COSMIC", {
        C("LC-RC-F"):               C("Super-M"),                   # Maximize window toggle (overrides General terminals)
    }, when = lambda ctx:
        cnfg.screen_has_focus and
        matchProps(clas=termStr)(ctx)
    )

if DESKTOP_ENV == 'gnome':
    keymap("GenTerms overrides: GNOME", {
        ### Keyboard input source (language/layout) switching in GNOME
        C("LC-Space"):             [bind,C("Super-Space")],         # keyboard input source (layout) switching (gnome)
        C("Shift-LC-Space"):       [bind,C("Super-Shift-Space")],   # keyboard input source (layout) switching (reverse) (gnome)
    }, when = lambda ctx:
        cnfg.screen_has_focus and
        matchProps(clas=termStr)(ctx)
    )

if DESKTOP_ENV == 'kde':
    keymap("GenTerms overrides: KDE", {
        ### Keyboard input source (language/layout) switching in KDE Plasma
        C("LC-Space"):              [bind,C("Super-Alt-L")],        # keyboard input source (layout) switching (Last-Used) (kde)
        C("Shift-LC-Space"):        [bind,C("Super-Alt-K")],        # keyboard input source (layout) switching (Next) (kde)
        C("RC-H"):                  C("Super-Page_Down"),           # Hide Window/Minimize app (KDE Plasma)

        # C("LC-RC-f"):               C("Alt-F10"),                   # Toggle window maximized state (pre-Plasma 6)
        # F10 key was designated an accessibility key for opening the window/app menu in KDE.
        # The shortcut for toggling window maximization state is now Meta+PgUp (so, Super-Page_Up).
        C("LC-RC-f"):               C("Super-Page_Up"),             # Toggle window maximized state

        # Workspace (virtual desktop) navigation
        C("LC-Left"):               C("C-Super-Left"),              # Switch one desktop to the left
        C("LC-Right"):              C("C-Super-Right"),             # Switch one desktop to the right

    }, when = lambda ctx:
        cnfg.screen_has_focus and
        matchProps(clas=termStr)(ctx)
    )

if DESKTOP_ENV == 'pantheon':
    keymap("GenTerms overrides: elementary OS", {
        C("LC-Right"):              [bind,C("Super-Right")],        # SL - Change workspace (elementary)
        C("LC-Left"):               [bind,C("Super-Left")],         # SL - Change workspace (elementary)
    }, when = lambda ctx:
        cnfg.screen_has_focus and
        matchProps(clas=termStr)(ctx)
    )

if DESKTOP_ENV == 'sway':
    keymap("GenTerms overrides: swaywm", {
        C("RC-Q"):                  C("Shift-C-Q"),                 # Override sway GenGUI Cmd+Q
    }, when = lambda ctx:
        cnfg.screen_has_focus and
        matchProps(clas=termStr)(ctx)
    )

if DESKTOP_ENV == 'xfce':
    keymap("GenTerms overrides: Xfce4", {
        C("RC-Grave"):             [bind,C("Super-Tab")],           # xfce4 Switch within app group
        C("Shift-RC-Grave"):       [bind,C("Super-Shift-Tab")],     # xfce4 Switch within app group
        C("LC-Right"):             [bind,C("C-Alt-Home")],          # SL - Change workspace xfce4
        C("LC-Left"):              [bind,C("C-Alt-End")],           # SL - Change workspace xfce4
    }, when = lambda ctx:
        cnfg.screen_has_focus and
        matchProps(clas=termStr)(ctx)
    )


# Active in all apps in the terminals list
keymap("General Terminals", {

    ### wordwise overrides of general GUI block
    C("Alt-Backspace"):         C("C-w"),                       # Wordwise delete word left of cursor in terminals
    # C("Alt-Backspace"):         C("Alt-Shift-Backspace"),       # Wordwise delete word left of cursor in terminals
    C("Alt-Delete"):           [C("Esc"),C("d")],               # Wordwise delete word right of cursor in terminals
    C("RC-Backspace"):          C("C-u"),                       # Wordwise delete line left of cursor in terminals
    C("RC-Delete"):             C("C-k"),                       # Wordwise delete line right of cursor in terminals

    ### Tab navigation
    C("Shift-RC-Left"):        [bind,C("C-Page_Up")],           # Tab nav: Go to prior tab (Left)
    C("Shift-RC-Right"):       [bind,C("C-Page_Down")],         # Tab nav: Go to next tab (Right)

    C("LC-RC-f"):               C("Alt-F10"),                   # Toggle window maximized state (gnome?)

    # Ctrl Tab - In App Tab Switching
    C("LC-Tab") :               C("C-PAGE_DOWN"),
    C("Shift-LC-Tab") :         C("C-PAGE_UP"),
    C("LC-Grave") :             C("C-PAGE_UP"),
    # C("Alt-Tab"):               ignore_combo,                   # Default - Cmd Tab - App Switching Default
    # C("RC-Tab"):                C("Alt-Tab"),                   # Default - Cmd Tab - App Switching Default
    # C("Shift-RC-Tab"):          C("Alt-Shift-Tab"),             # Default - Cmd Tab - App Switching Default

    # Converts Cmd to use Ctrl-Shift
    C("RC-MINUS"):              C("C-MINUS"),                   # Reduce font size
    C("RC-EQUAL"):              C("C-Shift-EQUAL"),             # Increase font size
    # C("RC-BACKSPACE"):          C("C-Shift-BACKSPACE"),         # Conflicts with wordwise shortcut above
    C("RC-W"):                  C("C-Shift-W"),                 # Close tab/window
    # C("RC-E"):                  C("C-Shift-E"),                 # No function - RE-ENABLE IF SOMEONE REPORTS
    # C("RC-R"):                  C("C-Shift-R"),                 # No function - RE-ENABLE IF SOMEONE REPORTS
    C("RC-T"):                  C("C-Shift-t"),                 # Open new tab in many terminals
    # C("RC-Y"):                  C("C-Shift-Y"),                 # No function - RE-ENABLE IF SOMEONE REPORTS
    # C("RC-U"):                  C("C-Shift-U"),                 # No function - RE-ENABLE IF SOMEONE REPORTS
    # C("RC-I"):                  C("C-Shift-I"),                 # No function - RE-ENABLE IF SOMEONE REPORTS
    # C("RC-O"):                  C("C-Shift-O"),                 # No function - RE-ENABLE IF SOMEONE REPORTS
    # C("RC-P"):                  C("C-Shift-P"),                 # No function - RE-ENABLE IF SOMEONE REPORTS
    C("RC-LEFT_BRACE"):         C("C-Shift-LEFT_BRACE"),
    C("RC-RIGHT_BRACE"):        C("C-Shift-RIGHT_BRACE"),
    # If focused app is terminal, this stops Cmd+A from working in GNOME overview search field
    # C("RC-A"):                  C("C-Shift-A"),                 # No function - RE-ENABLE IF SOMEONE REPORTS
    C("RC-S"):                  C("C-Shift-S"),                 # Save file in some terminals
    C("RC-D"):                  C("C-Shift-D"),                 # Split horizontal in some terminals
    C("RC-F"):                  C("C-Shift-F"),                 # Find text in some terminals
    # C("RC-G"):                  C("C-Shift-G"),                 # No function - RE-ENABLE IF SOMEONE REPORTS
    # C("RC-H"):                  C("C-Shift-H"),                 # No function - RE-ENABLE IF SOMEONE REPORTS
    # C("RC-J"):                  C("C-Shift-J"),                 # No function - RE-ENABLE IF SOMEONE REPORTS
    # C("RC-K"):                  C("C-Shift-K"),                 # No function - RE-ENABLE IF SOMEONE REPORTS
    C("RC-L"):                  C("C-Shift-L"),                 # Clear screen in some terminals
    # C("RC-SEMICOLON"):          C("C-Shift-SEMICOLON"),         # No function - RE-ENABLE IF SOMEONE REPORTS
    # C("RC-APOSTROPHE"):         C("C-Shift-APOSTROPHE"),        # No function - RE-ENABLE IF SOMEONE REPORTS
    # C("RC-GRAVE"):              C("C-Shift-GRAVE"),             # Conflicts with General GUI window switching
    # C("RC-Z"):                  C("C-Shift-Z"),                 # No function - RE-ENABLE IF SOMEONE REPORTS
    # C("RC-X"):                  C("C-Shift-X"),                 # No function - RE-ENABLE IF SOMEONE REPORTS
    C("RC-C"):                  C("C-Shift-C"),                 # Copy text in many terminals
    C("RC-V"):                  C("C-Shift-V"),                 # Paste text in many terminals
    # C("RC-B"):                  C("C-Shift-B"),                 # No function - RE-ENABLE IF SOMEONE REPORTS
    C("RC-N"):                  C("C-Shift-N"),                 # Open new window in many terminals
    # C("RC-M"):                  C("C-Shift-M"),                 # No function - RE-ENABLE IF SOMEONE REPORTS
    # C("RC-COMMA"):              C("C-Shift-COMMA"),             # Open Preferences (Replaced by per-app remaps if needed)
    C("RC-Dot"):                C("C-c"),                       # Mimic macOS Cmd+Dot to cancel command
    # C("RC-SLASH"):              C("C-Shift-SLASH"),             # No function - RE-ENABLE IF SOMEONE REPORTS
    # C("RC-KPASTERISK"):         C("C-Shift-KPASTERISK"),        # No function - RE-ENABLE IF SOMEONE REPORTS

    # Allow access to Linux TTY virtual consoles with the usual physical key locations (General Terminals)
    C("LC-RC-F1"):              C("C-Alt-F1"),                  # Go to TTY virtual console 1
    C("LC-RC-F2"):              C("C-Alt-F2"),                  # Go to TTY virtual console 2
    C("LC-RC-F3"):              C("C-Alt-F3"),                  # Go to TTY virtual console 3
    C("LC-RC-F4"):              C("C-Alt-F4"),                  # Go to TTY virtual console 4
    C("LC-RC-F5"):              C("C-Alt-F5"),                  # Go to TTY virtual console 5
    C("LC-RC-F6"):              C("C-Alt-F6"),                  # Go to TTY virtual console 6
    C("LC-RC-F7"):              C("C-Alt-F7"),                  # Go to TTY virtual console 7

}, when = lambda ctx:
    cnfg.screen_has_focus and
    matchProps(clas=termStr)(ctx)
)



#############################  GENERAL GUI  ################################
###                                                                      ###
###                                                                      ###
###       ██████  ███████ ███    ██ ███████ ██████   █████  ██           ###
###      ██       ██      ████   ██ ██      ██   ██ ██   ██ ██           ###
###      ██   ███ █████   ██ ██  ██ █████   ██████  ███████ ██           ###
###      ██    ██ ██      ██  ██ ██ ██      ██   ██ ██   ██ ██           ###
###       ██████  ███████ ██   ████ ███████ ██   ██ ██   ██ ███████      ###
###                                                                      ###
###                                                                      ###
############################################################################

# Note: terminals extends to remotes as well
keymap("Cmd+Dot not in terminals", {
    C("RC-Dot"):                C("Esc"),                       # Mimic macOS Cmd+dot = Escape key (not in terminals)
}, when = lambda ctx:
    cnfg.screen_has_focus and
    matchProps(not_clas=terms_and_remotes_Str)(ctx)
)


# Overrides to General GUI shortcuts for specific keyboard types
keymap("GenGUI overrides: Chromebook/IBM", {
    # In-App Tab switching
    C("Alt-Tab"):              [iEF2NT(),bind,C("C-Tab")],          # Chromebook/IBM - In-App Tab switching
    C("Alt-Shift-Tab"):        [iEF2NT(),bind,C("C-Shift-Tab")],    # Chromebook/IBM - In-App Tab switching
    C("Alt-Grave") :           [iEF2NT(),bind,C("C-Shift-Tab")],    # Chromebook/IBM - In-App Tab switching
    C("RAlt-Backspace"):        C("Delete"),                        # Chromebook/IBM - Delete
    C("LAlt-Backspace"):        C("C-Backspace"),                   # Chromebook/IBM - Delete Left Word of Cursor
}, when = lambda ctx:
    cnfg.screen_has_focus and
    (   isKBtype('Chromebook', map="gengui ovr cbook")(ctx) or
        isKBtype('IBM', map="gengui ovr ibm")(ctx) ) and
    matchProps(not_clas=remoteStr)(ctx)
)
keymap("GenGUI overrides: not Chromebook", {
    # In-App Tab switching
    C("Super-Tab"):            [iEF2NT(),bind,C("C-Tab")],          # Default not-chromebook
    C("Super-Shift-Tab"):      [iEF2NT(),bind,C("Shift-C-Tab")],    # Default not-chromebook
    C("Alt-Backspace"):         C("C-Backspace"),                   # Default not-chromebook
}, when = lambda ctx:
    cnfg.screen_has_focus and
    not isKBtype('Chromebook', map="gengui ovr not cbook")(ctx) and
    matchProps(not_clas=remoteStr)(ctx)
)


# Overrides to General GUI shortcuts for specific distros

if DISTRO_ID in ['almalinux', 'rhel', 'rocky'] and DESKTOP_ENV == 'xfce':
    keymap("GenGUI overrides: Alma/Rocky Xfce4", {
        C("RC-Space"):             [iEF2NT(),C("Alt-F3")],       # Launch App Finder xfce4 (AlmaLinux/Rocky)
    }, when = lambda ctx:
        cnfg.screen_has_focus and
        matchProps(not_clas=remoteStr)(ctx)
    )

if DISTRO_ID == 'debian' and DESKTOP_ENV == 'xfce':
    keymap("GenGUI overrides: Debian Xfce4", {
        C("RC-Space"):             [iEF2NT(),C("Alt-F1")],     # Launch Application Menu xfce4 (Debian)
    }, when = lambda ctx:
        cnfg.screen_has_focus and
        matchProps(not_clas=remoteStr)(ctx)
    )

if DISTRO_ID in ['fedora', 'almalinux'] and DESKTOP_ENV == 'gnome':
    keymap("GenGUI overrides: Fedora GNOME", {
        C("Super-RC-Q"):            C("Super-L"),                   # Lock screen (fedora)
        C("RC-H"):                  C("Super-h"),                   # Default SL - Minimize app (gnome/budgie/popos/fedora) not-deepin
        C("Super-Right"):          [bind,C("Super-Page_Up")],       # SL - Change workspace (ubuntu/fedora)
        C("Super-Left"):           [bind,C("Super-Page_Down")],     # SL - Change workspace (ubuntu/fedora)
    }, when = lambda ctx:
        cnfg.screen_has_focus and
        matchProps(not_clas=remoteStr)(ctx)
    )

if DISTRO_ID == 'manjaro' and DESKTOP_ENV == 'gnome':
    keymap("GenGUI overrides: Manjaro GNOME", {
        C("RC-Q"):              C("Super-Q"),                       # Close window
    }, when = lambda ctx:
        cnfg.screen_has_focus and
        matchProps(not_clas=remoteStr)(ctx)
    )

if DISTRO_ID == 'manjaro' and DESKTOP_ENV == 'xfce':
    keymap("GenGUI overrides: Manjaro Xfce", {
        C("RC-Space"):             [iEF2NT(),C("Alt-F1")],          # Open Whisker Menu with Cmd+Space
    }, when = lambda ctx:
        cnfg.screen_has_focus and
        matchProps(not_clas=remoteStr)(ctx)
    )

if DISTRO_ID == 'manjaro':
    keymap("GenGUI overrides: Manjaro", {
        C("Super-RC-f"):              C("Super-PAGE_UP"),             # SL- Maximize app manjaro
    }, when = lambda ctx:
        cnfg.screen_has_focus and
        matchProps(not_clas=remoteStr)(ctx)
    )

if DISTRO_ID == 'mint' and DESKTOP_ENV == 'xfce':
    keymap("GenGUI overrides: Mint Xfce4", {
        C("RC-Space"):             [iEF2NT(),C("Super-Space")],     # Launch Application Menu xfce4 (Linux Mint)
    }, when = lambda ctx:
        cnfg.screen_has_focus and
        matchProps(not_clas=remoteStr)(ctx)
    )

if DISTRO_ID == 'neon':
    keymap("GenGUI overrides: KDE Neon", {
        C("RC-Super-f"):            C("Super-Page_Up"),             # SL - Toggle maximized window state (kde_neon)
        C("RC-H"):                  C("Super-Page_Down"),           # SL - Minimize app (kde_neon)
                                                                    # SL - Default SL - Change workspace (kde_neon)
    }, when = lambda ctx:
        cnfg.screen_has_focus and
        matchProps(not_clas=remoteStr)(ctx)
    )

if DISTRO_ID == 'pop':
    keymap("GenGUI overrides: Pop!_OS", {
        C("RC-Space"):             [iEF2NT(),C("Super-slash")],     # "Launch and switch applications" (pop)
        C("RC-H"):                  C("Super-h"),                   # Default SL - Minimize app (gnome/budgie/popos/fedora) not-deepin
        C("Super-Right"):          [bind,C("Super-C-Up")],          # SL - Change workspace (pop)
        C("Super-Left"):           [bind,C("Super-C-Down")],        # SL - Change workspace (pop)
        C("RC-Q"):                  C("Super-q"),                   # SL - Close Apps (pop)
    }, when = lambda ctx:
        cnfg.screen_has_focus and
        matchProps(not_clas=remoteStr)(ctx)
    )

if DISTRO_ID == 'ubuntu':
    keymap("GenGUI overrides: Ubuntu", {
        C("Super-RC-Q"):            C("Super-L"),                   # Lock screen (ubuntu)
        C("Super-Right"):          [bind,C("Super-Page_Up")],       # SL - Change workspace (ubuntu)
        C("Super-Left"):           [bind,C("Super-Page_Down")],     # SL - Change workspace (ubuntu)
    }, when = lambda ctx:
        cnfg.screen_has_focus and
        matchProps(not_clas=remoteStr)(ctx)
    )


# Overrides to General GUI shortcuts for specific desktop environments

if DESKTOP_ENV == 'budgie':
    keymap("GenGUI overrides: Budgie", {
        C("RC-Space"):             [iEF2NT(),Key.LEFT_META],        # Open panel-main-menu (Budgie menu)
        C("Super-Right"):           C("C-Alt-Right"),               # Change workspace (budgie)
        C("Super-Left"):            C("C-Alt-Left"),                # Change workspace (budgie)
        C("RC-H"):                  C("Super-h"),                   # Minimize app (gnome/budgie/popos/fedora) not-deepin
    }, when = lambda ctx:
        cnfg.screen_has_focus and
        matchProps(not_clas=remoteStr)(ctx)
    )

if DESKTOP_ENV == 'cinnamon':
    keymap("GenGUI overrides: Cinnamon", {
        C("RC-Space"):             [iEF2NT(),C("C-Esc")],           # Right click, configure Mint menu shortcut to Ctrl+Esc
    }, when = lambda ctx:
        cnfg.screen_has_focus and
        matchProps(not_clas=remoteStr)(ctx)
    )

# On Pop!_OS 22.04, System76 seems to have changed the name of the DE from 'cosmic' to 'pop'.
# Probably to avoid overlapping with the new COSMIC desktop environment in Pop!_OS 24.04 and later.
if DESKTOP_ENV in ['cosmic', 'pop']:
    keymap("GenGUI overrides: COSMIC", {
        # No shortcuts settings panel seems to be available at this time (July 30, 2024),
        # so we can't "fix" this during Toshy install to not use the Meta/Super key.
        C("RC-Space"):             [Key.LEFT_META,iEF2NT()],        # Launcher or Workspaces or Applications (user choice)
        C("RC-Q"):                  C("Super-Q"),                   # Close window/Quit (overrides Alt+F4 from General GUI)
        C("Super-RC-F"):            C("Super-M"),                   # Maximize window toggle (overrides General GUI)
    }, when = lambda ctx:
        cnfg.screen_has_focus and
        matchProps(not_clas=remoteStr)(ctx)
    )

if DESKTOP_ENV == 'dde':
    keymap("GenGUI overrides: DDE", {
        C("RC-Space"):             [iEF2NT(),Key.LEFT_META],        # Open Launcher menu (Deeping Desktop Environment)
    }, when = lambda ctx:
        cnfg.screen_has_focus and
        matchProps(not_clas=remoteStr)(ctx)
    )

if DESKTOP_ENV == 'deepin':
    keymap("GenGUI overrides: Deepin", {
        C("RC-H"):                  C("Super-n"),                   # Minimize app (deepin)
        C("Alt-RC-Space"):          C("Super-e"),                   # Open Finder - (deepin)
    }, when = lambda ctx:
        cnfg.screen_has_focus and
        matchProps(not_clas=remoteStr)(ctx)
    )

if DESKTOP_ENV == 'enlightenment':
    keymap("GenGUI overrides: Enlightenment", {
        C("RC-q"):                  C("C-Alt-x"),                   # Close window (Cmd+Q)
        # C("RC-Space"):             [iEF2NT(),C("C-Alt-m")],         # enlightenment main menu (override in "User Apps" slice if necessary)
        C("RC-Space"):             [iEF2NT(),C("C-Alt-Space")],     # enlightenment main menu (override in "User Apps" slice if necessary)
    }, when = lambda ctx:
        cnfg.screen_has_focus and
        matchProps(not_clas=remoteStr)(ctx)
    )

if DESKTOP_ENV == 'gnome':
    if is_pre_GNOME_45(DE_MAJ_VER):
        # This keymap, if invoked, must come before the other GNOME overrides in the next keymap, not after.
        keymap("GenGUI overrides: pre-GNOME 45 fix", {
            C("RC-Space"):             [iEF2NT(),C("Super-s")],         # Override GNOME 45+ Shift+Ctrl+Space remap
        }, when = lambda ctx:
            cnfg.screen_has_focus and
            matchProps(not_clas=remoteStr)(ctx)
        )
    keymap("GenGUI overrides: GNOME", {
        C("RC-Space"):             [iEF2NT(),C("Shift-C-Space")],   # Show GNOME overview/app launcher
        C("RC-F3"):                 C("Super-d"),                   # Default SL - Show Desktop (gnome/kde,elementary)
        C("RC-Super-f"):            C("Alt-F10"),                   # Default SL - Maximize app (gnome/kde)
        C("RC-H"):                  C("Super-h"),                   # Default SL - Minimize app (gnome/budgie/popos/fedora) not-deepin
        # Screenshot shortcuts for GNOME 42+
        C("RC-Shift-Key_3"):        C("Shift-Print"),               # Take a screenshot immediately (gnome)
        C("RC-Shift-Key_4"):        C("Alt-Print"),                 # Take a screenshot of a window (gnome)
        C("RC-Shift-Key_5"):        C("Print"),                     # Take a screenshot interactively (gnome)
    }, when = lambda ctx:
        cnfg.screen_has_focus and
        matchProps(not_clas=remoteStr)(ctx)
    )

if DESKTOP_ENV == 'hyprland':
    keymap("GenGUI overrides: Hyprland", {
        # C("RC-Space"):             [iEF2NT(),Key.LEFT_META],        # Open Launcher with Cmd+Space
        C("RC-Space"):             [C("Super-d"), iEF2NT()],        # Open Launcher with Cmd+Space
    }, when = lambda ctx:
        cnfg.screen_has_focus and
        matchProps(not_clas=remoteStr)(ctx)
    )

if DESKTOP_ENV == 'icewm':
    keymap("GenGUI overrides: IceWM", {
        C("RC-Space"):             [iEF2NT(),Key.LEFT_META],        # IceWM: Win95Keys=1 (Meta shows menu)
    }, when = lambda ctx:
        cnfg.screen_has_focus and
        matchProps(not_clas=remoteStr)(ctx)
    )

if DESKTOP_ENV == 'kde':
    keymap("GenGUI overrides: KDE", {

        # Application launcher menu remap
        # C("RC-Space"):             [iEF2NT(),C("Alt-F1")],          # Application Launcher Menu

        # krunner drop-down (similar to Spotlight) remap
        C("RC-Space"):             [iEF2NT(),C("Alt-Space")],          # Invoke krunner drop-down

        C("RC-F3"):                 C("Super-d"),                   # Show Desktop (gnome/kde,elementary)
        C("RC-H"):                  C("Super-Page_Down"),           # Minimize app (KDE Plasma)

        # Workspace (virtual desktop) navigation
        C("Super-Left"):            C("C-Super-Left"),              # Switch one desktop to the left
        C("Super-Right"):           C("C-Super-Right"),             # Switch one desktop to the right

        # C("Super-RC-f"):            C("Alt-F10"),                   # Toggle window maximized state (pre-Plasma 6)
        # F10 key was designated an accessibility key for opening the window/app menu in KDE.
        # The shortcut for toggling window maximization state is now Meta+PgUp (so, Super-Page_Up).
        C("Super-RC-f"):            C("Super-Page_Up"),             # Toggle window maximized state

        # Screenshot shortcuts for KDE Plasma desktops (Spectacle app)
        C("RC-Shift-Key_3"):        C("Shift-Print"),               # Take a screenshot immediately (kde)
        C("RC-Shift-Key_4"):        C("Alt-Print"),                 # Take a screenshot of a window (kde)
        C("RC-Shift-Key_5"):        C("Print"),                     # Take a screenshot interactively (kde)

        ### Keyboard input source (language/layout) switching in KDE Plasma
        C("Super-Space"):          [bind,C("Super-Alt-L")],         # keyboard input source (layout) switching (Last-Used) (kde)
        C("Shift-Super-Space"):    [bind,C("Super-Alt-K")],         # keyboard input source (layout) switching (Next) (kde)

    }, when = lambda ctx:
        cnfg.screen_has_focus and
        matchProps(not_clas=remoteStr)(ctx)
    )

if DESKTOP_ENV == 'mate' and DISTRO_ID == 'mint':
    keymap("GenGUI overrides: MATE on Mint", {
        # Right click, configure Mint menu shortcut to match `Alt+Space` shortcut to make this work
        C("RC-Space"):             [iEF2NT(), C("Alt-Space")],       # Open Mint app menu
    }, when = lambda ctx:
        cnfg.screen_has_focus and
        matchProps(not_clas=remoteStr)(ctx)
    )

if DESKTOP_ENV == 'mate' and DISTRO_ID == 'ubuntu':
    keymap("GenGUI overrides: MATE on Ubuntu", {
        # No way to reconfigure the shortcut for Brisk Menu Launcher?
        C("RC-Space"):             [iEF2NT(), Key.LEFT_META],       # Open Brisk Menu Launcher
    }, when = lambda ctx:
        cnfg.screen_has_focus and
        matchProps(not_clas=remoteStr)(ctx)
    )

if DESKTOP_ENV == 'miracle-wm':
    keymap("GenGUI overrides: MiracleWM", {
        # C("RC-Space"):             [iEF2NT(),Key.LEFT_META],        # Open Launcher with Cmd+Space
        C("RC-Space"):             [C("Super-d"), iEF2NT()],        # Open Launcher with Cmd+Space
    }, when = lambda ctx:
        cnfg.screen_has_focus and
        matchProps(not_clas=remoteStr)(ctx)
    )

if DESKTOP_ENV == 'pantheon':
    keymap("GenGUI overrides: Pantheon", {
        C("RC-F3"):                 C("Super-d"),                   # Show Desktop (gnome/kde,elementary)
        # C("RC-Space"):             [iEF2NT(),C("Super-Space")],     # Launch Application Menu (elementary)
        C("RC-Space"):             [iEF2NT(),C("Alt-F2")],          # Launch Application Menu (elementary OS 8)
        C("Super-RC-f"):            C("Super-Up"),                  # Maximize app elementary
    }, when = lambda ctx:
        cnfg.screen_has_focus and
        matchProps(not_clas=remoteStr)(ctx)
    )

if DESKTOP_ENV == 'sway':
    keymap("GenGUI overrides: swaywm", {
        C("RC-Space"):             [iEF2NT(),C("Super-d")],         # Open sway launcher
        C("RC-Q"):                  C("C-Q"),                       # Override General GUI Alt+F4 remap
    }, when = lambda ctx:
        cnfg.screen_has_focus and
        matchProps(not_clas=remoteStr)(ctx)
    )

if DESKTOP_ENV == 'trinity':
    keymap("GenGUI overrides: Trinity desktop", {
        C("RC-Space"):             [iEF2NT(),Key.LEFT_META],        # Trinity desktop (Q4OS)
    }, when = lambda ctx:
        cnfg.screen_has_focus and
        matchProps(not_clas=remoteStr)(ctx)
    )

if DESKTOP_ENV == 'unity':
    keymap("GenGUI overrides: Unity desktop", {
        C("RC-Space"):             [iEF2NT(),Key.LEFT_META],        # Trinity desktop (Q4OS)
    }, when = lambda ctx:
        cnfg.screen_has_focus and
        matchProps(not_clas=remoteStr)(ctx)
    )

if DESKTOP_ENV == 'xfce' and DISTRO_ID == 'zorin':
    keymap("GenGUI overrides: Zorin Xfce", {
        C("RC-Space"):             [iEF2NT(),C("Alt-Pause")],     # "Launch and switch applications" (Xfce on Zorin)
    }, when = lambda ctx:
        cnfg.screen_has_focus and
        matchProps(not_clas=remoteStr)(ctx)
    )

if DESKTOP_ENV == 'xfce':
    keymap("GenGUI overrides: Xfce4", {
        C("RC-Grave"):             [bind,C("Super-Tab")],           # xfce4 Switch within app group
        C("Shift-RC-Grave"):       [bind,C("Super-Shift-Tab")],     # xfce4 Switch within app group
        C("RC-Space"):             [iEF2NT(),C("C-Esc")],           # Launch Application Menu xfce4 (Xubuntu)
        C("RC-F3"):                 C("C-Alt-d"),                   # SL- Show Desktop xfce4
        C("RC-H"):                  C("Alt-F9"),                    # SL - Minimize app xfce4
        # Screenshot shortcuts for Xfce desktops (xfce4-screenshooter app)
        C("RC-Shift-Key_3"):        C("Print"),                     # Take a screenshot immediately (xfce4)
        C("RC-Shift-Key_4"):        C("Alt-Print"),                 # Take a screenshot of a window (xfce4)
        C("RC-Shift-Key_5"):        C("Shift-Print"),               # Take a screenshot interactively (xfce4)
    }, when = lambda ctx:
        cnfg.screen_has_focus and
        matchProps(not_clas=remoteStr)(ctx)
    )


# None referenced here originally
# - but remote clients and VM software ought to be set here
# These are the typical remaps for ALL GUI based apps
keymap("General GUI", {

    C("Alt-Numlock"):           toggle_forced_numpad,           # Turn the Forced Numpad feature on and off
    C("Fn-Numlock"):            toggle_forced_numpad,           # Turn the Forced Numpad feature on and off
    C("Numlock"):               isNumlockClearKey,              # Numlock key is "Clear" (Esc) if cnfg.forced_numpad is True

    C("Shift-RC-Left_Brace"):   C("C-Page_Up"),                 # Tab navigation: Go to prior (left) tab
    C("Shift-RC-Right_Brace"):  C("C-Page_Down"),               # Tab navigation: Go to next (right) tab
    C("RC-Space"):             [iEF2NT(),C("Alt-F1")],          # Default SL - Launch Application Menu (gnome/kde)
    C("RC-F3"):                 C("Super-d"),                   # Default SL - Show Desktop (gnome/kde,elementary)
    C("RC-Super-f"):            C("Alt-F10"),                   # Default SL - Maximize app (gnome/kde)
    C("RC-Q"):                  C("Alt-F4"),                    # Default SL - not-popos
    C("Alt-Tab"):               ignore_combo,                   # Default - Cmd Tab - App Switching Default

    C("RC-Tab"):            [iEF2NT(),bind, C("Alt-Tab")],           # Default - Cmd Tab - App Switching Default
    C("Shift-RC-Tab"):      [iEF2NT(),bind, C("Alt-Shift-Tab")],     # Default - Cmd Tab - App Switching Default

    C("RC-Grave"):          [iEF2NT(),bind, C("Alt-Grave")],         # Default not-xfce4 - Cmd ` - Same App Switching
    C("Shift-RC-Grave"):    [iEF2NT(),bind, C("Alt-Shift-Grave")],   # Default not-xfce4 - Cmd ` - Same App Switching

    # Fn to Alt style remaps
    C("RAlt-Enter"):            C("insert"),                    # Insert

    # emacs style
    C("Super-a"):               C("Home"),                      # Beginning of Line
    C("Super-e"):               C("End"),                       # End of Line
    C("Super-b"):               C("Left"),
    C("Super-f"):               C("Right"),
    C("Super-n"):               C("Down"),
    C("Super-p"):               C("Up"),
    C("Super-k"):              [C("Shift-End"), C("Backspace")],
    C("Super-d"):               C("Delete"),

    # This is better done with a native custom shortcut in each DE
    # C("Alt-RC-Space"):          C(""),                          # Open Finder - Placeholder not-deepin

    # Wordwise
    C("RC-Left"):               C("Home"),                      # Beginning of Line
    C("Shift-RC-Left"):         C("Shift-Home"),                # Select all to Beginning of Line
    C("RC-Right"):              C("End"),                       # End of Line
    C("Shift-RC-Right"):        C("Shift-End"),                 # Select all to End of Line
    C("RC-Up"):                 C("C-Home"),                    # Beginning of File
    C("Shift-RC-Up"):           C("C-Shift-Home"),              # Select all to Beginning of File
    C("RC-Down"):               C("C-End"),                     # End of File
    C("Shift-RC-Down"):         C("C-Shift-End"),               # Select all to End of File
    C("Super-Backspace"):       C("C-Backspace"),               # Delete Left Word of Cursor
    C("Super-Delete"):          C("C-Delete"),                  # Delete Right Word of Cursor
    C("RC-Backspace"):          C("C-Shift-Backspace"),         # Delete Entire Line Left of Cursor
    C("Alt-Delete"):            C("C-Delete"),                  # Delete Right Word of Cursor
    C("Shift-Alt-Backspace"):   C("C-Backspace"),               # Delete word left of cursor
    C("Shift-Alt-Delete"):      C("C-Delete"),                  # Delete word right of cursor

    # Allow access to Linux TTY virtual consoles with the usual physical key locations (General GUI)
    C("Super-RC-F1"):           C("C-Alt-F1"),                  # Go to TTY virtual console 1
    C("Super-RC-F2"):           C("C-Alt-F2"),                  # Go to TTY virtual console 2
    C("Super-RC-F3"):           C("C-Alt-F3"),                  # Go to TTY virtual console 3
    C("Super-RC-F4"):           C("C-Alt-F4"),                  # Go to TTY virtual console 4
    C("Super-RC-F5"):           C("C-Alt-F5"),                  # Go to TTY virtual console 5
    C("Super-RC-F6"):           C("C-Alt-F6"),                  # Go to TTY virtual console 6
    C("Super-RC-F7"):           C("C-Alt-F7"),                  # Go to TTY virtual console 7

    # C("RC-Left"):               C("C-LEFT_BRACE"),              # Firefox-nw - Back
    # C("RC-Right"):              C("C-RIGHT_BRACE"),             # Firefox-nw - Forward
    # C("RC-Left"):               C("Alt-LEFT"),                  # Chrome-nw - Back
    # C("RC-Right"):              C("Alt-RIGHT"),                 # Chrome-nw - Forward
    # C(""):                      ignore_combo,                   # cancel
    # C(""):                      C(""),                          #

}, when = lambda ctx:
    cnfg.screen_has_focus and
    matchProps(not_clas=remoteStr)(ctx)
)


keymap("Diagnostics (isMultiTap)", {

    C("Shift-Alt-RC-i"): isMultiTap(
                            # tap_1_action=None,  # Block single tap
                            tap_1_action=C("Shift-Alt-C-i"),    # Keep original single-tap combo
                            tap_2_action=notify_context,
                        ),

    C("Shift-Alt-RC-h"): isMultiTap(
                            tap_1_action=C("Shift-Alt-RC-h"),   # Keep original single-tap combo
                            tap_2_action=notify_context,
                            tap_3_action=lambda: print("\nTriple tap!\n"),  # Shows in terminal
                        ),

    C("Shift-Alt-RC-t"): isMultiTap(
                            tap_1_action=C("C-n"),          # Test single-tap by opening new window
                            tap_2_action=macro_tester,      # Types out a long test macro text
                            tap_3_action=[
                                ST("You tapped Shift-Alt-C-t 3 times!!!"),
                                C("Enter"), C("Enter")],
                            tap_4_action=[
                                ST("You tapped Shift-Alt-C-t 4 times!!!!"),
                                C("Enter"), C("Enter")],
                            tap_5_action=[
                                ST("You tapped Shift-Alt-C-t 5 times!!!!!"),
                                C("Enter"), C("Enter")],
                        ),

}, when = lambda ctx: ctx is ctx)


# keymap("Diagnostics (isDoubleTap)", {
#     C("Shift-Alt-RC-i"):        isDoubleTap(notify_context),    # Diagnostic dialog (primary)
#     C("Shift-Alt-RC-h"):        isDoubleTap(notify_context),    # Diagnostic dialog (alternate)
#     C("Shift-Alt-RC-t"):        isDoubleTap(macro_tester),      # Type out test macro
# }, when = lambda ctx: ctx is ctx )
