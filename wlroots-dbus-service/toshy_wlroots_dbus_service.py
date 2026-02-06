#!/usr/bin/env python3
__version__ = '20251220'

# Reference for generating the protocol modules with pywayland scanner:
# https://github.com/flacjacket/pywayland/issues/8#issuecomment-987040284

# Protocol documentation:
# https://wayland.app/protocols/wlr-foreign-toplevel-management-unstable-v1

# pywayland method had a NotImplementedError for NewId argument,
# but PR #64 was merged. 


print("(--) Starting Toshy D-Bus service to monitor 'zwlr_foreign_toplevel_manager_v1'...", flush=True)

import os
import sys
import dbus
import time
import signal
import platform
import subprocess
import dbus.service
import dbus.mainloop.glib
import xwaykeyz.lib.logger

from pywayland.client import Display
from gi.repository import GLib
from dbus.exceptions import DBusException
from subprocess import DEVNULL
from xwaykeyz.lib.logger import debug, error

xwaykeyz.lib.logger.VERBOSE = True


# Independent module/script to create a D-Bus window context service in 
# a wlroots Wayland environment, which will be notified of window 
# focus changes by the Wayland compositor, as long as the compositor 
# implements the `wlr_foreign_toplevel_management_unstable_v1` protocol.

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

from protocols.wlr_foreign_toplevel_management_unstable_v1.zwlr_foreign_toplevel_manager_v1 import (
    ZwlrForeignToplevelManagerV1,
    ZwlrForeignToplevelManagerV1Proxy,
    ZwlrForeignToplevelHandleV1
)

if os.name == 'posix' and os.geteuid() == 0:
    error("This app should not be run as root/superuser.")
    sys.exit(1)


# Establish our Wayland client global variable
wl_client = None

def signal_handler(sig, frame):
    """handle signals like Ctrl+C"""
    if sig in (signal.SIGINT, signal.SIGQUIT, signal.SIGTERM):
        # Perform any cleanup code here before exiting
        # traceback.print_stack(frame)
        debug(f'\nSIGINT or SIGQUIT received. Exiting.\n')
        clean_shutdown()

def clean_shutdown():
    if wl_client and wl_client.display:  # Check if the display is globally defined and initialized
        try:
            wl_client.display.disconnect()
        except Exception as e:
            error(f"Error disconnecting display: {e}")
    GLib.MainLoop().quit()  # Stop the GLib main loop if it's running
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
    f.write('toshy-wlr-dbus')


sep_reps        = 80
sep_char        = '='
separator       = sep_char * sep_reps

LOG_PFX = 'TOSHY_WLR_DBUS_SVC'

DISTRO_ID       = None
DISTRO_VER      = None
VARIANT_ID      = None
SESSION_TYPE    = None
DESKTOP_ENV     = None
DE_MAJ_VER      = None


def check_environment():
    """Retrieve the current environment from env module"""
    # env_info_dct   = env.get_env_info()
    env_ctxt_getter = EnvironmentInfo()
    env_info_dct   = env_ctxt_getter.get_env_info()
    global DISTRO_ID, DISTRO_VER, VARIANT_ID, SESSION_TYPE, DESKTOP_ENV, DE_MAJ_VER
    DISTRO_ID       = env_info_dct.get('DISTRO_ID')
    DISTRO_VER      = env_info_dct.get('DISTRO_VER')
    VARIANT_ID      = env_info_dct.get('VARIANT_ID')
    SESSION_TYPE    = env_info_dct.get('SESSION_TYPE')
    DESKTOP_ENV     = env_info_dct.get('DESKTOP_ENV')
    DE_MAJ_VER      = env_info_dct.get('DE_MAJ_VER')


check_environment()

# TODO: put the DE restriction back in place, find a way to identify wlroots compositors
if SESSION_TYPE == 'wayland': # and DESKTOP_ENV not in ['kde', 'plasma', 'gnome', 'cinnamon']:
    pass
else:
    debug(f'{LOG_PFX}: Probably not a wlroots environment. Exiting.')
    time.sleep(2)
    sys.exit(0)


# debug("")
# debug(  f'Toshy Wlroots D-Bus service script sees this environment:'
#         f'\n\t{DISTRO_ID        = }'
#         f'\n\t{DISTRO_VER       = }'
#         f'\n\t{VARIANT_ID       = }'
#         f'\n\t{SESSION_TYPE     = }'
#         f'\n\t{DESKTOP_ENV      = }'
#         f'\n\t{DE_MAJ_VER       = }\n', ctx="CG")


TOSHY_WLR_DBUS_SVC_PATH         = '/org/toshy/Wlroots'
TOSHY_WLR_DBUS_SVC_IFACE        = 'org.toshy.Wlroots'

ERR_NO_WLR_APP_CLASS = "ERR_no_wlr_app_class"
ERR_NO_WLR_WDW_TITLE = "ERR_no_wlr_wdw_title"

COUNTDOWN_MS = 6000  # 6 seconds
countdown_timer = COUNTDOWN_MS
interface_is_bound = False
interface_is_available = True


def countdown_callback():
    global countdown_timer
    if interface_is_bound:
        return False  # Stop calling this function
    countdown_timer -= 100  # Decrement by 100ms
    if countdown_timer <= 0:
        debug("Failed to bind Wayland interface within timeout period. Wlroots exiting.")
        clean_shutdown()
    return True  # Continue calling this function


def check_interface_availability():
    global interface_is_available
    if not wl_client.toplevel_manager:  # Check if the interface is still available
        debug(f"{LOG_PFX}: The Wayland interface is not available. Exiting.")
        interface_is_available = False
        clean_shutdown()  # Perform cleanup and shutdown
    if not wl_client.check_connection():  # Check if the connection to the Wayland server is still available
        debug("Wayland interface is not available. Wlroots going dormant.")
        interface_is_available = False
        clean_shutdown()  # Perform cleanup and shutdown
    return interface_is_available  # Continue calling this function if the interface is available


class WaylandClient:
    def __init__(self):
        self.display            = None
        self.registry           = None
        self.toplevel_manager   = None
        self.wl_fd              = None

        self.wdw_handles_dct    = {}
        self.active_handle      = None
        self.active_app_class   = ERR_NO_WLR_APP_CLASS
        self.active_wdw_title   = ERR_NO_WLR_WDW_TITLE

    def connect(self):
        try:
            self.display = Display()
            self.display.connect()
            self.wl_fd = self.display.get_fd()
            self.registry = self.display.get_registry()
            self.registry.dispatcher["global"] = self.handle_registry_global
            self.display.roundtrip()
        except Exception as e:
            error(f"Failed to connect to the Wayland display: {e}")
            clean_shutdown()

    def handle_registry_global(self, registry, id_, interface_name, version):
        global interface_is_bound
        if interface_name == 'zwlr_foreign_toplevel_manager_v1':
            self.toplevel_manager = registry.bind(id_, ZwlrForeignToplevelManagerV1, version)
            self.toplevel_manager.dispatcher["toplevel"] = self.handle_toplevel_event
            interface_is_bound = True
            # run the kickstart script here to generate a KWin event (hopefully)
            kickstart_script    = 'toshy-kwin-script-kickstart.sh'
            kickstart_cmd       = os.path.join(home_dir, '.config', 'toshy', 'scripts', kickstart_script)
            try:
                subprocess.Popen([kickstart_cmd], stderr=DEVNULL, stdout=DEVNULL)
            except subprocess.CalledProcessError as proc_err:
                error(f"Problem running the kickstart script: {proc_err}")
            except FileNotFoundError as file_err:
                error(f"Kickstart script not found:\n\t{file_err}")

    def handle_toplevel_event(self, toplevel_manager, toplevel_handle):

        # Initialize the dictionary entry with default values to avoid KeyError
        self.wdw_handles_dct[toplevel_handle] = {
            'app_id': ERR_NO_WLR_APP_CLASS,
            'title': ERR_NO_WLR_WDW_TITLE
        }

        toplevel_handle.dispatcher["app_id"]            = self.handle_app_id_change
        toplevel_handle.dispatcher["title"]             = self.handle_title_change
        toplevel_handle.dispatcher['closed']            = self.handle_window_closed
        toplevel_handle.dispatcher['state']             = self.handle_state_change

    def handle_app_id_change(self, handle, app_id):
        if handle not in self.wdw_handles_dct:
            self.wdw_handles_dct[handle] = {}
        self.wdw_handles_dct[handle]['app_id'] = app_id
        # Don't rely only on state handler to set active window info in asynchronous event situations
        # Only update active window app_id if this event is for the active handle
        if handle == self.active_handle:
            self.active_app_class = app_id

    def handle_title_change(self, handle, title):
        if handle not in self.wdw_handles_dct:
            self.wdw_handles_dct[handle] = {}
        self.wdw_handles_dct[handle]['title'] = title
        # Don't rely only on state handler to set active window info in asynchronous event situations
        # Only update active window title if this event is for the active handle
        if handle == self.active_handle:
            self.active_wdw_title = title

    def handle_window_closed(self, handle):
        if handle in self.wdw_handles_dct:
            del self.wdw_handles_dct[handle]
        # print(f"Window {handle} has been closed.")

    def handle_state_change(self, handle, states_bytes):
        states = []
        if isinstance(states_bytes, bytes):
            states = list(states_bytes)
        if ZwlrForeignToplevelHandleV1.state.activated.value in states:
            self.active_handle = handle
            try:
                self.active_app_class = self.wdw_handles_dct[handle]['app_id']
            except KeyError as key_err:
                # error(f"Problem accessing app_id:\n\t{key_err}")
                self.active_app_class = 'KeyErr_accessing_app_id'
            try:
                self.active_wdw_title = self.wdw_handles_dct[handle]['title']
            except KeyError as key_err:
                # error(f"Problem accessing title:\n\t{key_err}")
                self.active_wdw_title = 'KeyErr_accessing_wdw_title'
            # print()
            # print(f"Active app class: '{self.active_app_class}'")
            # print(f"Active window title: '{self.active_wdw_title}'")
            # self.print_running_applications()

    def check_connection(self):
        try:
            ret = self.display.flush()
            if ret == -1:
                error("Wayland connection check: flush failed")
                return False
        except Exception as e:
            error(f"Wayland connection lost: {e}")
            return False
        return True

    def print_running_applications(self):
        print("\nList of running applications:")
        print(f"{'App ID':<30} {'Title':<50}")
        print("-" * 80)
        for handle, info in self.wdw_handles_dct.items():
            app_id = info.get('app_id', ERR_NO_WLR_APP_CLASS)
            title = info.get('title', ERR_NO_WLR_WDW_TITLE)
            print(f"{app_id:<30} {title:<50}")
        print()


class DBUS_Object(dbus.service.Object):
    """Class to handle D-Bus interactions"""
    def __init__(self, session_bus, object_path, interface_name):
        super().__init__(session_bus, object_path)
        self.interface_name     = interface_name
        self.dbus_svc_bus_name  = dbus.service.BusName(interface_name, bus=session_bus)

    @dbus.service.method(TOSHY_WLR_DBUS_SVC_IFACE, out_signature='a{sv}')
    def GetActiveWindow(self):
        # debug(f'{LOG_PFX}: GetActiveWindow() called...')
        return {'app_id':           wl_client.active_app_class,
                'title':            wl_client.active_wdw_title}


def wayland_event_callback(fd, condition, display: Display):
    if condition & GLib.IO_ERR or condition & GLib.IO_HUP:
        error("Wayland display file descriptor is no longer valid.")
        clean_shutdown()  # Perform cleanup and shutdown
        return False  # Stop calling this function
    if condition & GLib.IO_IN:
        # Use read() + dispatch() instead of roundtrip() to avoid blocking loop
        # read() reads events from the FD into the queue
        # dispatch() processes queued events and returns immediately
        display.read()
        display.dispatch()
    return True


def main():

    # Initialize the D-Bus main loop
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

    # Connect to the session bus
    session_bus = dbus.SessionBus()

    # Create the DBUS_Object
    try:
        DBUS_Object(session_bus, TOSHY_WLR_DBUS_SVC_PATH, TOSHY_WLR_DBUS_SVC_IFACE)
    except DBusException as dbus_error:
        error(f"{LOG_PFX}: Error occurred while creating D-Bus service object:\n\t{dbus_error}")
        clean_shutdown()

    global wl_client        # Is this necessary?
    wl_client = WaylandClient()
    wl_client.connect()     # This connects display, gets registry, and also gets file descriptor

    GLib.io_add_watch(wl_client.wl_fd, GLib.IO_IN, wayland_event_callback, wl_client.display)

    wl_client.display.roundtrip() # get the event cycle started (callback never gets called without this)

    # Add the countdown callback to the GLib main loop with a 100ms interval
    GLib.timeout_add(100, countdown_callback)

    # Add the periodic check to the GLib main loop with a 1-second interval
    GLib.timeout_add_seconds(1, check_interface_availability)

    # Run the main loop
    # dbus.mainloop.glib.DBusGMainLoop().run()
    GLib.MainLoop().run()


if __name__ == "__main__":
    main()
    # After main() is done:
    clean_shutdown()
