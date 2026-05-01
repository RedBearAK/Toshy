# -*- coding: utf-8 -*-
__version__ = '20260404'
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

# Removing problematic types before they get deprecated:
# from typing import Any, Callable, Optional, Union, List, Dict, Tuple
from typing import Any
from subprocess import DEVNULL
from collections.abc import Callable

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


# ─── Devices API Reference ───────────────────────────────────────────────────
#
# Use `devices_api()` to control which input devices the keymapper grabs.
# Run `toshy-devices` to see all available identifiers for connected devices.
#
# Both `only_devices` and `ignore_devices` accept lists of strings.
# Each string can be any of the following match types:
#
#   'AT Translated Set 2 keyboard'                          # device name
#   '/dev/input/event3'                                     # device path (volatile across reboots)
#   '/dev/input/by-id/usb-Example_Keyboard-event-kbd'       # by-id symlink (stable, USB/BT only)
#   'b0003:v1234:p5678:e0001:nab12cd34'                     # synthetic ID (stable, any device)
#   'b0003:v1234:p5678:e0001:nab12cd34@usb-0000:00:14.0'    # synthetic ID with bus path (stable)
#   'AA:BB:CC:DD:EE:FF'                                     # device uniq (stable, rarely populated)
#
# NOTE: Device paths like /dev/input/eventN can change across reboots or
# when devices are unplugged and reconnected. Prefer device name, by-id
# path, or synthetic ID for entries that should survive across reboots.

devices_api(

    # Only the specified devices will be "grabbed" and watched for
    # during device connections/disconnections. When empty or omitted,
    # the keymapper autodetects all keyboard-like devices.
    only_devices = [
        # 'Example Keyboard Name',
    ],

    # Devices to never grab, even if they match autodetection or the
    # allowlist above. Useful for combo keyboard/mouse devices that
    # cause pointer stutter when grabbed, or media control devices
    # that do not need remapping.
    ignore_devices = [
        # 'Example Wireless Receiver Mouse',
    ],
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
from toshy_common.runtime_utils import sanitize_text
from toshy_common.settings_class import Settings
from toshy_common.terminal_utils import print_pango_text

assets_path         = os.path.join(current_folder_path, 'assets')
icon_file_active    = os.path.join(assets_path, "toshy_app_icon_rainbow.svg")
icon_file_grayscale = os.path.join(assets_path, "toshy_app_icon_rainbow_inverse_grayscale.svg")
icon_file_inverse   = os.path.join(assets_path, "toshy_app_icon_rainbow_inverse.svg")

# Toshy config file
TOSHY_PART      = 'config'   # CUSTOMIZE TO SPECIFIC TOSHY COMPONENT! (gui, tray, config)
TOSHY_PART_NAME = 'Toshy Barebones Config'
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
env_ctxt: 'dict[str, str]' = env_ctxt_getter.get_env_info()

DISTRO_ID       = locals().get('OVERRIDE_DISTRO_ID')    or env_ctxt.get('DISTRO_ID',    'keymissing')
DISTRO_VER      = locals().get('OVERRIDE_DISTRO_VER')   or env_ctxt.get('DISTRO_VER',   'keymissing')
VARIANT_ID      = locals().get('OVERRIDE_VARIANT_ID')   or env_ctxt.get('VARIANT_ID',   'keymissing')
SESSION_TYPE    = locals().get('OVERRIDE_SESSION_TYPE') or env_ctxt.get('SESSION_TYPE', 'keymissing')
DESKTOP_ENV     = locals().get('OVERRIDE_DESKTOP_ENV')  or env_ctxt.get('DESKTOP_ENV',  'keymissing')
DE_MAJ_VER      = locals().get('OVERRIDE_DE_MAJ_VER')   or env_ctxt.get('DE_MAJ_VER',   'keymissing')
WINDOW_MGR      = locals().get('OVERRIDE_WINDOW_MGR')   or env_ctxt.get('WINDOW_MGR',   'keymissing')

# debug("")
debug(  f'Toshy (barebones) config sees this environment:'
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

        message         = (
            f"<tt>"
            f"<b>Class:</b> '{escape_markup(ctx_clas)}' {nwln_str}"
            f"<b>Title:</b> '{escape_markup(ctx_name)}' {nwln_str}"
            f"{nwln_str}"
            f"<b>Input keyboard name:</b> '{ctx_devn}' {nwln_str}"
            f"<b>Device seen as type:</b> '{KBTYPE}' {nwln_str}"
            f"{nwln_str}"
            f"<b>Toshy (barebones) config sees this environment:</b>  {nwln_str}"
            f"<b> • DISTRO_ID ____________</b> '{DISTRO_ID      }' {nwln_str}"
            f"<b> • DISTRO_VER ___________</b> '{DISTRO_VER     }' {nwln_str}"
            f"<b> • VARIANT_ID ___________</b> '{VARIANT_ID     }' {nwln_str}"
            f"<b> • SESSION_TYPE _________</b> '{SESSION_TYPE   }' {nwln_str}"
            f"<b> • DESKTOP_ENV __________</b> '{DESKTOP_ENV    }' {nwln_str}"
            f"<b> • DE_MAJ_VER ___________</b> '{DE_MAJ_VER     }' {nwln_str}"
            f"<b> • WINDOW_MGR ___________</b> '{WINDOW_MGR     }' {nwln_str}"
            f"{nwln_str}"
            f"<b> __________________________________________________ </b>{nwln_str}"
            f"<i>Keyboard shortcuts (Ctrl+C/Cmd+C) may not work here.</i>{nwln_str}"
            f"<i>Select text with mouse. Triple-click to select all. </i>{nwln_str}"
            f"<i>Right-click with mouse and choose 'Copy' from menu. </i>{nwln_str}"
            f"</tt>"
        )

        # Sanitize Unicode characters in dialog text if locale does not support
        sane_message = sanitize_text(message)

        zenity_cmd_lst = [  zenity_cmd, '--info', '--no-wrap',
                            '--title=Toshy Context Info',
                            '--text=' + sane_message ]

        # insert the icon argument if it's supported
        if zenity_icon_option is not None:
            zenity_cmd_lst.insert(3, zenity_icon_option)

        kdialog_cmd_lst = [kdialog_cmd, '--msgbox', sane_message, '--title', 'Toshy Context Info']
        # Add icon if needed: kdialog_cmd_lst += ['--icon', '/path/to/icon']
        # Figure out why icon argument doesn't work. Need a proper icon theme folder?
        # DONE: Figured out that Kdialog does not support custom icons at all!
        kdialog_cmd_lst += ['--icon', 'toshy_app_icon_rainbow']

        if dialog_cmd == kdialog_cmd:
            subprocess.Popen(kdialog_cmd_lst, cwd=icons_dir, stderr=DEVNULL, stdout=DEVNULL)
        elif dialog_cmd == zenity_cmd:
            subprocess.Popen(zenity_cmd_lst, cwd=icons_dir, stderr=DEVNULL, stdout=DEVNULL)

        # Also print out the diagnostics to the terminal, in case the dialog doesn't work.
        # Trim the last 4 lines (dialog-only hints) for terminal output
        term_message = nwln_str.join(message.split(nwln_str)[:-4])
        print(f"\n{'=' * 50}")
        print(f"  Toshy Context Info (diagnostic dialog content)")
        print(f"{'=' * 50}")
        print_pango_text(term_message, nwln_str)
        print()     # separate from following lines

        # Optionally, also send a system notification:
        # ntfy.send_notification(message)
    return _notify_context



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
tap_states: 'dict[tuple, dict[str, Any]]' = {}

event_loop: 'asyncio.AbstractEventLoop | None' = None


def get_loop() -> 'asyncio.AbstractEventLoop | None':
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


def isMultiTap( tap_1_action: 'Callable | None' = None,
                tap_2_action: 'Callable | None' = None,
                tap_3_action: 'Callable | None' = None,
                tap_4_action: 'Callable | None' = None,
                tap_5_action: 'Callable | None' = None,
                tap_interval: float = None,
                min_tap_delay: float = None):    # returns Callable
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
        finalize_handle: 'asyncio.Handle | None' = state['finalize_handle']
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



###################################################################################################
###  SLICE_MARK_START: barebones_user_cfg  ###  EDITS OUTSIDE THESE MARKS WILL BE LOST ON UPGRADE


# Example keymap that adds British Pound and Euro symbols to any keyboard layout.
keymap("Currency character overlay", {
    C("RAlt-Key_4"):            UC(0x00A3),                     # £ British Pound currency symbol
    C("RAlt-Key_5"):            UC(0x20AC),                     # € Euro currency symbol
}, when = lambda _: True is True)



###  SLICE_MARK_END: barebones_user_cfg  ###  EDITS OUTSIDE THESE MARKS WILL BE LOST ON UPGRADE
###################################################################################################


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

}, when = lambda _: True is True)


# keymap("Diagnostics (isDoubleTap)", {
#     C("Shift-Alt-RC-i"):        isDoubleTap(notify_context),    # Diagnostic dialog (primary)
#     C("Shift-Alt-RC-h"):        isDoubleTap(notify_context),    # Diagnostic dialog (alternate)
#     C("Shift-Alt-RC-t"):        isDoubleTap(macro_tester),      # Type out test macro
# }, when = lambda _: True is True)

