#!/usr/bin/env python3
__version__ = '20250710'

# Reference for generating the protocol modules with pywayland scanner:
# https://github.com/flacjacket/pywayland/issues/8#issuecomment-987040284

# Protocol documentation (original on which COSMIC variant is based):
# https://wayland.app/protocols/wlr-foreign-toplevel-management-unstable-v1

# COSMIC protocol specification XML files:
# https://github.com/pop-os/cosmic-protocols/blob/main/unstable/cosmic-toplevel-info-unstable-v1.xml
# https://github.com/pop-os/cosmic-protocols/blob/main/unstable/cosmic-workspace-unstable-v1.xml

# pywayland method had a NotImplementedError for NewId argument,
# but PR #64 was merged. 


print("(--) Starting Toshy D-Bus service to monitor 'zcosmic_toplevel_info_v1'...", flush=True)

import os
import sys
import dbus
import time
import signal
import struct
import platform
import dbus.service
import dbus.mainloop.glib
import xwaykeyz.lib.logger

from pywayland.client import Display
from gi.repository import GLib
from dbus.exceptions import DBusException
from subprocess import DEVNULL
from typing import Dict, List
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

from protocols.cosmic_toplevel_info_unstable_v1.zcosmic_toplevel_info_v1 import (
    ZcosmicToplevelInfoV1,
    ZcosmicToplevelInfoV1Proxy,
    ZcosmicToplevelHandleV1
)

# COSMIC protocol update has shifted to involving 'ext_foreign_toplevel_list_v1' interface.
from protocols.ext_foreign_toplevel_list_v1.ext_foreign_toplevel_list_v1 import (
    ExtForeignToplevelListV1,
    ExtForeignToplevelListV1Proxy,
    ExtForeignToplevelHandleV1
)

if os.name == 'posix' and os.geteuid() == 0:
    error("This app should not be run as root/superuser.")
    sys.exit(1)


# Establish our Wayland client global variable
wl_client = None

def signal_handler(sig, frame):
    """handle signals like Ctrl+C"""
    if sig in (signal.SIGINT, signal.SIGQUIT):
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
else:
    error(f'This is only meant to run on Linux. Exiting...')
    sys.exit(1)

# Set the process name now that we know we are on Linux
with open('/proc/self/comm', 'w') as f:
    f.write('toshy-csmc-dbus')


sep_reps        = 80
sep_char        = '='
separator       = sep_char * sep_reps

LOG_PFX = 'TOSHY_COSMIC_DBUS_SVC'

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
    DISTRO_ID       = env_info_dct.get('DISTRO_ID', 'keymissing')
    DISTRO_VER      = env_info_dct.get('DISTRO_VER', 'keymissing')
    VARIANT_ID      = env_info_dct.get('VARIANT_ID', 'keymissing')
    SESSION_TYPE    = env_info_dct.get('SESSION_TYPE', 'keymissing')
    DESKTOP_ENV     = env_info_dct.get('DESKTOP_ENV', 'keymissing')
    DE_MAJ_VER      = env_info_dct.get('DE_MAJ_VER', 'keymissing')


check_environment()


if SESSION_TYPE == 'wayland' and DESKTOP_ENV in ['cosmic']:
    pass
else:
    debug(f'{LOG_PFX}: Probably not COSMIC desktop environment. Exiting.')
    time.sleep(2)
    sys.exit(0)


# debug("")
# debug(  f'Toshy COSMIC D-Bus service script sees this environment:'
#         f'\n\t{DISTRO_ID        = }'
#         f'\n\t{DISTRO_VER       = }'
#         f'\n\t{VARIANT_ID       = }'
#         f'\n\t{SESSION_TYPE     = }'
#         f'\n\t{DESKTOP_ENV      = }'
#         f'\n\t{DE_MAJ_VER       = }\n', ctx="CG")


TOSHY_COSMIC_DBUS_SVC_PATH      = '/org/toshy/Cosmic'
TOSHY_COSMIC_DBUS_SVC_IFACE     = 'org.toshy.Cosmic'

ERR_NO_COSMIC_APP_CLASS = "ERR_no_cosmic_app_class"
ERR_NO_COSMIC_WDW_TITLE = "ERR_no_cosmic_wdw_title"

# Create a mapping of state values to their names
STATE_MAP = {
    0: "maximized",
    1: "minimized",
    2: "activated",
    3: "fullscreen",
    4: "sticky"  # Since version 2
}


class WaylandClient:
    def __init__(self):
        self.display                            = None
        self.wl_fd                              = None
        self.registry                           = None
        self.cosmic_protocol_ver                = None

        self.cosmic_toplvl_mgr: ZcosmicToplevelInfoV1Proxy      = None
        self.foreign_toplvl_mgr: ExtForeignToplevelListV1Proxy  = None

        self.wdw_handles_dct                    = {}
        self.cosmic_to_foreign_map              = {}
        self.active_foreign_handle              = None
        self.active_app_class                   = ERR_NO_COSMIC_APP_CLASS
        self.active_wdw_title                   = ERR_NO_COSMIC_WDW_TITLE

    def print_running_applications(self):
        """Print a complete list of running applications."""
        print("\nFull list of running application classes (not windows):")
        print(f"{'App ID':<30} {'Title':<50}")
        print("-" * 80)
        for handle, info in self.wdw_handles_dct.items():
            app_id = info.get('app_id', ERR_NO_COSMIC_APP_CLASS)
            title  = info.get('title', ERR_NO_COSMIC_WDW_TITLE)
            # print(f"{handle}")
            print(f"{app_id:<30} {title:<50}")
        print()

    def connect(self):
        try:
            self.display = Display()
            self.display.connect()
            self.wl_fd = self.display.get_fd()
            self.registry = self.display.get_registry()
            self.registry.dispatcher['global'] = self.handle_registry_global
            self.display.roundtrip()
        except Exception as e:
            debug(f"Failed to connect to the Wayland display: {e}")
            clean_shutdown()

    def handle_registry_global(self, registry, id_, interface_name, version):
        # COSMIC is using their own namespace instead of 'zwlr_foreign_toplevel_manager_v1'
        if interface_name == 'zcosmic_toplevel_info_v1':
            self.cosmic_protocol_ver = version
            self.cosmic_toplvl_mgr = registry.bind(id_, ZcosmicToplevelInfoV1, version)
            if version == 1:
                # Generated protocol modules are no longer compatible with this version
                self.cosmic_toplvl_mgr.dispatcher["toplevel"] = self.handle_toplevel_event_v1
            elif version >= 2:
                # This updated version of the protocol will be handled when the 
                # 'ext_foreign_toplevel_list_v1' event appears and gets processed. 
                pass
        if interface_name == 'ext_foreign_toplevel_list_v1':
            print(f"Subscribing to 'toplevel' events from foreign toplevel manager...")
            self.foreign_toplvl_mgr = registry.bind(id_, ExtForeignToplevelListV1, version)
            self.foreign_toplvl_mgr.dispatcher['toplevel'] = self.handle_toplevel_event_v2
        self.display.roundtrip()

    def handle_toplevel_event_v2(self,
                foreign_toplvl_mgr: ExtForeignToplevelListV1Proxy,
                foreign_toplvl_handle: ExtForeignToplevelHandleV1):
        """Request a new v2 cosmic toplevel handle for a foreign toplevel handle."""
        try:
            cosmic_toplvl_handle: ZcosmicToplevelHandleV1 = None
            cosmic_toplvl_handle = self.cosmic_toplvl_mgr.get_cosmic_toplevel(foreign_toplvl_handle)

            # Ensure the dictionary entry is initialized with the foreign handle as the primary key
            if foreign_toplvl_handle not in self.wdw_handles_dct:
                self.wdw_handles_dct[foreign_toplvl_handle] = {
                    'cosmic_handle':    cosmic_toplvl_handle,
                    'app_id':           None,
                    'title':            None,
                    'state':            None,
                    'ready':            False,  # Mark as false until all properties are received
                }

            # Store a reverse mapping from COSMIC handle to foreign handle
            # (We are dealing with two different handles for each toplevel window.)
            self.cosmic_to_foreign_map[cosmic_toplvl_handle] = foreign_toplvl_handle

            # Event listeners for the foreign toplevel handle
            # (cosmic toplevel handle will never emit these events now, they are deprecated since v2)
            foreign_toplvl_handle.dispatcher['title']       = self.handle_title_change
            foreign_toplvl_handle.dispatcher['app_id']      = self.handle_app_id_change
            foreign_toplvl_handle.dispatcher['closed']      = self.handle_window_closed

            # Event listeners for v2 cosmic toplevel handle
            # (foreign toplevel handle does not have the state events)
            cosmic_toplvl_handle.dispatcher['state']        = self.handle_state_change

            # self.display.roundtrip()      # Not sure if this is necessary or helpful here

        except KeyError as e:
            print(f"Error sending get_cosmic_toplevel request: {e}")

    def handle_toplevel_event_v1(self,
                                toplevel_manager: ZcosmicToplevelInfoV1Proxy,
                                toplevel_handle: ZcosmicToplevelHandleV1):
        toplevel_handle.dispatcher['app_id']    = self.handle_app_id_change
        toplevel_handle.dispatcher['title']     = self.handle_title_change
        toplevel_handle.dispatcher['closed']    = self.handle_window_closed
        toplevel_handle.dispatcher['state']     = self.handle_state_change

    def handle_app_id_change(self, handle, app_id):
        if handle not in self.wdw_handles_dct:
            self.wdw_handles_dct[handle] = {}
        self.wdw_handles_dct[handle]['app_id'] = app_id
        # Deal with possible out-of-order Wayland events
        if handle == self.active_foreign_handle:
            self.active_app_class = app_id

    def handle_title_change(self, handle, title):
        if handle not in self.wdw_handles_dct:
            self.wdw_handles_dct[handle] = {}
        self.wdw_handles_dct[handle]['title'] = title
        # Deal with possible out-of-order Wayland events
        if handle == self.active_foreign_handle:
            self.active_wdw_title = title

    def handle_window_closed(self, handle):
        """Remove window from local state."""

        if self.cosmic_protocol_ver >= 2:
            # Using list() as a wrapper creates a copy of dictionary.items() (which 
            # produces a dynamic "view object") to iterate over without risking an 
            # iteration error from modifying the dictionary underlying the items() 
            # view object.
            for cosmic_handle, foreign_handle in list(self.cosmic_to_foreign_map.items()):
                if foreign_handle is handle:
                    del self.cosmic_to_foreign_map[cosmic_handle]
                    break
            if handle and handle in self.wdw_handles_dct:
                del self.wdw_handles_dct[handle]
                print(f"Window has been closed:\n  {handle}")

        elif self.cosmic_protocol_ver == 1:
            if handle and handle in self.wdw_handles_dct:
                del self.wdw_handles_dct[handle]
                print(f"Window has been closed:\n  {handle}")

    def handle_state_change(self, handle, states_bytes):
        """Track active window app class and title based on state changes."""

        # Filter out empty state updates (why do these even happen?)
        # Filter out the all-zeroes state (reset event?) before converting
        if not states_bytes or states_bytes == b'\x00\x00\x00\x00':
            # print()
            # print("Received empty bytes value or all-zeroes 4-byte state event, ignoring.")
            return

        # Process states_bytes as an array of 4-byte (32-bit) integers
        # Interpret 4 bytes as an integer (little-endian arrays?)
        if isinstance(states_bytes, bytes):
            state_values = list(struct.unpack(f'{len(states_bytes)//4}I', states_bytes))

        # Convert state values to their corresponding names
        state_names = [STATE_MAP.get(state, f"Unknown state: {state}") for state in state_values]

        # print()
        # print(f"{'State change event (bytes):':<30}",   f"{states_bytes}")
        # print(f"{'State change event (values):':<30}",  f"{state_values}")
        # print(f"{'State change event (names):':<30}",   f"{state_names}")

        foreign_handle: ExtForeignToplevelHandleV1 = None

        if self.cosmic_protocol_ver >= 2:
            if handle in self.cosmic_to_foreign_map:
                foreign_handle = self.cosmic_to_foreign_map[handle]
        else:
            # print("Error: Foreign handle not found for the cosmic toplevel.")
            return

        if ZcosmicToplevelHandleV1.state.activated.value in state_values:

            if self.cosmic_protocol_ver >= 2:
                self.active_foreign_handle = foreign_handle
                self.active_app_class = self.wdw_handles_dct[foreign_handle]['app_id']
                self.active_wdw_title = self.wdw_handles_dct[foreign_handle]['title']

            elif self.cosmic_protocol_ver == 1:
                self.active_app_class = self.wdw_handles_dct[handle]['app_id']
                self.active_wdw_title = self.wdw_handles_dct[handle]['title']

            # self.print_running_applications()  # Print the list of running applications
            # print()
            # print("#" * 80)
            # print(f"{'Active app class:':<30}", f"'{self.active_app_class}'")
            # print(f"{'Active window title:':<30}", f"'{self.active_wdw_title}'")
            # print("#" * 80)


class DBUS_Object(dbus.service.Object):
    """Class to handle D-Bus interactions"""
    def __init__(self, session_bus, object_path, interface_name):
        super().__init__(session_bus, object_path)
        self.interface_name     = interface_name
        self.dbus_svc_bus_name  = dbus.service.BusName(interface_name, bus=session_bus)

    @dbus.service.method(TOSHY_COSMIC_DBUS_SVC_IFACE, out_signature='a{sv}')
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
        # display.dispatch()    # dispatch() fails to prompt new events to appear
        # dispatch() also seems to trigger the callback to get called many times in a loop,
        # but without any new useful events appearing, while roundtrip() just shows
        # the new events that I need to see, as they happen.
        display.roundtrip()     # gets new events to appear immediately
    return True


def main():

    # Initialize the D-Bus main loop
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

    # Connect to the session bus
    session_bus = dbus.SessionBus()

    # Create the DBUS_Object
    try:
        DBUS_Object(session_bus, TOSHY_COSMIC_DBUS_SVC_PATH, TOSHY_COSMIC_DBUS_SVC_IFACE)
    except DBusException as dbus_error:
        error(f"{LOG_PFX}: Error occurred while creating D-Bus service object:\n\t{dbus_error}")
        sys.exit(1)

    global wl_client        # Is this necessary?
    wl_client = WaylandClient()
    wl_client.connect()     # This connects display, gets registry, and also gets file descriptor

    GLib.io_add_watch(wl_client.wl_fd, GLib.IO_IN, wayland_event_callback, wl_client.display)

    wl_client.display.roundtrip() # get the event cycle started (callback never gets called without this)

    # Run the main loop
    # dbus.mainloop.glib.DBusGMainLoop().run()
    GLib.MainLoop().run()


if __name__ == "__main__":
    main()
    # After main() is done:
    clean_shutdown()
