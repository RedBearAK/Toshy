#!/usr/bin/env python3
__version__ = '20251220'

print("(--) Starting Toshy D-Bus service to receive updates from KWin script...", flush=True)

import os
import sys
import dbus
import time
# import shutil
import signal
# import zipfile
import platform
# import subprocess
import dbus.service
import dbus.mainloop.glib
import xwaykeyz.lib.logger

from gi.repository import GLib
from dbus.exceptions import DBusException
from subprocess import DEVNULL
from xwaykeyz.lib.logger import debug, error

xwaykeyz.lib.logger.VERBOSE = True


# Independent module/script to create a D-Bus window context
# service in a KDE Plasma environment, which will be notified
# of window focus changes by the Toshy KWin script

# Add paths to avoid errors like ModuleNotFoundError or ImportError
home_dir            = os.path.expanduser("~")
run_tmp_dir         = os.environ.get('XDG_RUNTIME_DIR') or '/tmp'
parent_folder_path  = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
current_folder_path = os.path.abspath(os.path.dirname(__file__))

sys.path.insert(0, current_folder_path)
sys.path.insert(0, parent_folder_path)

existing_path = os.environ.get('PYTHONPATH', '')
os.environ['PYTHONPATH'] = f'{parent_folder_path}:{current_folder_path}:{existing_path}'

# local imports now that path is prepped
from toshy_common.env_context import EnvironmentInfo

if os.name == 'posix' and os.geteuid() == 0:
    error("This app should not be run as root/superuser.")
    sys.exit(1)

def signal_handler(sig, frame):
    """handle signals like Ctrl+C"""
    if sig in (signal.SIGINT, signal.SIGQUIT, signal.SIGTERM):
        # Perform any cleanup code here before exiting
        # traceback.print_stack(frame)
        debug(f'\nSIGINT or SIGQUIT received. Exiting.\n')
        sys.exit(0)

if platform.system() != 'Windows':
    signal.signal(signal.SIGINT,    signal_handler)
    signal.signal(signal.SIGQUIT,   signal_handler)
    signal.signal(signal.SIGTERM,   signal_handler)
else:
    error(f'This is only meant to run on Linux. Exiting...')
    sys.exit(1)

# Set the process name now that we know we are on Linux
with open('/proc/self/comm', 'w') as f:
    f.write('toshy-kwin-dbus')


sep_reps        = 80
sep_char        = '='
separator       = sep_char * sep_reps

LOG_PFX = 'TOSHY_KWIN_DBUS_SVC'

DISTRO_ID       = None
DISTRO_VER      = None
VARIANT_ID      = None
SESSION_TYPE    = None
DESKTOP_ENV     = None
DE_MAJ_VER      = None
WINDOW_MGR      = None

def check_environment():
    """Retrieve the current environment from env module"""
    global DISTRO_ID, DISTRO_VER, VARIANT_ID, SESSION_TYPE, DESKTOP_ENV, DE_MAJ_VER, WINDOW_MGR

    env_ctxt_getter     = EnvironmentInfo()
    env_info_dct        = env_ctxt_getter.get_env_info()

    DISTRO_ID           = env_info_dct.get('DISTRO_ID',     'keymissing')
    DISTRO_VER          = env_info_dct.get('DISTRO_VER',    'keymissing')
    VARIANT_ID          = env_info_dct.get('VARIANT_ID',    'keymissing')
    SESSION_TYPE        = env_info_dct.get('SESSION_TYPE',  'keymissing')
    DESKTOP_ENV         = env_info_dct.get('DESKTOP_ENV',   'keymissing')
    DE_MAJ_VER          = env_info_dct.get('DE_MAJ_VER',    'keymissing')
    WINDOW_MGR          = env_info_dct.get('WINDOW_MGR',    'keymissing')


check_environment()


# Adding 'lxqt' as a possible desktop environment where 'kwin_wayland' might be used.
# TODO: Add a way to auto-install the KWin script in LXQt? Or will it already auto-install?
# if SESSION_TYPE == 'wayland' and DESKTOP_ENV in ['kde', 'plasma', 'lxqt']:

# Switching to looking for 'kwin_wayland' as window manager, instead of desktop environment.
# This way we shouldn't have to care what the DE is, only if they are using 'kwin_wayland'.
if SESSION_TYPE == 'wayland' and WINDOW_MGR == 'kwin_wayland':
    pass
else:
    debug(f'{LOG_PFX}: Not a kwin_wayland environment. Exiting.')
    time.sleep(2)
    sys.exit(0)


# debug("")
# debug(  f'Toshy KWin D-Bus service script sees this environment:'
#         f'\n\t{DISTRO_ID        = }'
#         f'\n\t{DISTRO_VER       = }'
#         f'\n\t{VARIANT_ID       = }'
#         f'\n\t{SESSION_TYPE     = }'
#         f'\n\t{DESKTOP_ENV      = }'
#         f'\n\t{DE_MAJ_VER       = }'
#         f'\n\t{WINDOW_MGR       = }\n', ctx="CG")


# Rename the D-Bus object/path more specifically for Plasma (there are others, like Wlroots)
TOSHY_KWIN_DBUS_SVC_PATH        = '/org/toshy/Plasma'
TOSHY_KWIN_DBUS_SVC_IFACE       = 'org.toshy.Plasma'


class DBUS_Object(dbus.service.Object):
    """Class to handle D-Bus interactions"""
    def __init__(self, session_bus, object_path, interface_name):
        super().__init__(session_bus, object_path)
        self.interface_name     = interface_name
        self.dbus_svc_bus_name  = dbus.service.BusName(interface_name, bus=session_bus)
        self.caption            = "NO_DATA"
        self.resource_class     = "NO_DATA"
        self.resource_name      = "NO_DATA"

    @dbus.service.method(TOSHY_KWIN_DBUS_SVC_IFACE, in_signature='sss')
    def NotifyActiveWindow(self, caption, resource_class, resource_name):
        # debug(f'{LOG_PFX}: NotifyActiveWindow() called...')
        self.caption            = str(caption)
        self.resource_class     = str(resource_class)
        self.resource_name      = str(resource_name)
        # debug(f'{LOG_PFX}: Active window attributes:'
        #         f"\n\t caption        = '{self.caption}'"
        #         f"\n\t resource_class = '{self.resource_class}'"
        #         f"\n\t resource_name  = '{self.resource_name}'"
        # )

    @dbus.service.method(TOSHY_KWIN_DBUS_SVC_IFACE, out_signature='a{sv}')
    def GetActiveWindow(self):
        # debug(f'{LOG_PFX}: GetActiveWindow() called...')
        return {    'caption':          self.caption,
                    'resource_class':   self.resource_class,
                    'resource_name':    self.resource_name }


def main():
    # Initialize the D-Bus main loop
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

    # Connect to the session bus
    session_bus = dbus.SessionBus()

    # Create the DBUS_Object
    try:
        DBUS_Object(session_bus, TOSHY_KWIN_DBUS_SVC_PATH, TOSHY_KWIN_DBUS_SVC_IFACE)
    except DBusException as dbus_error:
        error(f"{LOG_PFX}: Error occurred while creating D-Bus service object:\n\t{dbus_error}")
        sys.exit(1)

    # Run the main loop
    # dbus.mainloop.glib.DBusGMainLoop().run()
    GLib.MainLoop().run()


if __name__ == "__main__":
    main()
