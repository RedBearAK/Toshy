import os
import abc
try:
    import dbus
except ModuleNotFoundError:
    dbus = None
import json
import time
import i3ipc
import shutil
import socket
import subprocess

from random import randint
from subprocess import PIPE
from i3ipc import Con

# Removing the typing import to avoid trouble with Python 3.15+
# from typing import Dict, Optional

from .logger import error, debug

# Provider classes for window context info


NO_CONTEXT_WAS_ERROR = {"wm_class": "", "wm_name": "", "wndw_ctxt_error": True}


class WindowContextProviderInterface(abc.ABC):
    """Abstract base class for all window context provider classes."""

    _environment_registry:  'dict[tuple, type]' = {}
    _instantiation_used:    bool = False

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if 'get_supported_environments' not in cls.__dict__:
            return
        if cls.__name__.startswith('Example'):
            return
        for env in cls.get_supported_environments():
            WindowContextProviderInterface._environment_registry[env] = cls

    @classmethod
    def make_provider(cls, session_type, wl_compositor):
        """Construct the window context provider for this session.
        Raises RuntimeError on a second call — only one per process."""
        if WindowContextProviderInterface._instantiation_used:
            raise RuntimeError(
                "make_provider() has already been called this session. "
                "Reuse the existing instance from transform.window_context "
                "instead of constructing a new one."
            )

        env = (session_type, wl_compositor)
        if env not in cls._environment_registry:
            raise ValueError(f"Unsupported environment: {env}")

        WindowContextProviderInterface._instantiation_used = True
        return cls._environment_registry[env]()

    @classmethod
    def get_all_supported_environments(cls):
        """Return the list of all (session_type, window_manager) tuples
        that have a registered provider class."""
        return list(cls._environment_registry.keys())

    @classmethod
    @abc.abstractmethod
    def get_supported_environments(cls):
        """
        This method should return a list of environments that the subclass 
        supports, in the form [('session_type', 'window_manager')]. In Wayland
        the window manager is often referred to as the Wayland compositor.
        For this reason the environ_api function has the `wl_compositor`
        argument, to accept the detected window manager process name and
        target the window context provider that advertises a matching
        environment tuple.

        Each environment should be represented as a tuple. For example, the
        X11/Xorg provider subclass returns:

            [('x11', None)]

        ... meaning it supports any Linux X11/Xorg window manager. 

        Wayland methods are usually going to be specific to a certain compositor,
        until more universal standards evolve. (This may never happen.)

        If an environment is specific to a certain window manager, the 
        window manager should be included in the tuple. For example, if 
        a subclass supports the 'wayland' session specifically only for the 
        'gnome-shell' window manager, this method should return:

            [('wayland', 'gnome-shell')].

        At this time only 'x11' and 'wayland' session types are in common use. It
        is necessary to note the session type due to many window managers retaining
        the same name from X11/Xorg to their Wayland counterpart, while requiring
        completely different window context methods.

        :returns: A list of tuples, each representing an environment combination
        of session type and window manager supported by the subclass.
        """

    @abc.abstractmethod
    def get_window_context(self):
        """
        This method should return the current window's context as a dictionary.

        The returned dictionary should contain the following keys:

        - "wm_class": The class of the window.
        - "wm_name": The name of the window.
        - "wndw_ctxt_error": A boolean indicating whether there was an error 
            in obtaining the window's context.

        The "wm_class" and "wm_name" values are expected to be strings.
        The "wndw_ctxt_error" value is expected to be a boolean, which should 
        be False if the window's context was successfully obtained, 
        and True otherwise.

        Example of a successful context:

        {
            "wm_class": "ExampleClass",
            "wm_name": "ExampleName",
            "wndw_ctxt_error": False
        }

        In case of an error, the method should return NO_CONTEXT_WAS_ERROR, 
        which is a predefined global variable "constant":

        NO_CONTEXT_WAS_ERROR = {"wm_class": "", "wm_name": "", "wndw_ctxt_error": True}

        :returns: A dictionary containing window context information.
        """


# An example class to copy and paste to start supporting a new environment
class Example_WindowContext(WindowContextProviderInterface):
    """Window context provider object for [Example] environments"""

    def __init__(self):
        """Set up whatever the whole class instance needs here"""
        pass

    @classmethod
    def get_supported_environments(cls):
        """This class supports the [example environment] on [session type]"""
        return [
            ('wayland', 'example-environment'),
        ]

    def get_window_context(self):
        """Return window context to KeyContext"""
        pass


class Wl_Pantheon_WindowContext(WindowContextProviderInterface):
    """
    Window context provider object for Wayland+Pantheon environments.
    This class interacts with Pantheon's Gala D-Bus interface to obtain
    information about the currently focused window.
    """

    def __init__(self):
        from dbus.exceptions import DBusException

        self.DBusException      = DBusException
        self.session_bus        = dbus.SessionBus()

        self.wm_class           = 'NO_DATA_YET'
        self.app_id             = 'NO_DATA_YET'
        self.title              = 'NO_DATA_YET'

        self.gala_dbus_obj      = 'org.pantheon.gala'
        self.gala_dbus_path     = '/org/pantheon/gala/DesktopInterface'
        self.dbus_svc_name      = 'Pantheon Gala D-Bus service'

        while True:
            try:
                self.proxy_gala_svc = self.session_bus.get_object(
                    self.gala_dbus_obj, self.gala_dbus_path
                )
                self.iface_gala_svc = dbus.Interface(
                    self.proxy_gala_svc, 'org.pantheon.gala.DesktopIntegration'
                )
                break
            except self.DBusException as dbus_error:
                error(f'Error getting {self.dbus_svc_name} interface.\n\t{dbus_error}')
            time.sleep(3)

    @classmethod
    def get_supported_environments(cls):
        """
        This class supports the Pantheon environment on Wayland, using
        the Pantheon Gala D-Bus interface.
        """
        return [
            # Window manager is 'gala'
            ('wayland', 'gala'),
            # TODO: Remove deprecated 'pantheon' desktop environment entry by mid-2027?
            ('wayland', 'pantheon'),
        ]

    def get_window_context(self):
        """
        Return window context to KeyContext
        Queries the Gala D-Bus service for the current window's app class and title.
        """
        try:
            # Use GetWindows method to find the focused window
            windows = self.iface_gala_svc.GetWindows()
            for window in windows:
                window_id, properties = window
                if properties.get('has-focus', False):
                    # This block only executes if the get() succeeded and did not return "False"
                    self.wm_class = properties.get('wm-class', '')
                    self.app_id = properties.get('app-id', '').rstrip('.desktop')
                    self.title = properties.get('title', '')
                    # debug(f"####  Pantheon wm-class:    '{self.wm_class}'")
                    # debug(f"####  Pantheon app-id:      '{self.app_id}'")
                    # debug(f"####  Pantheon title:       '{self.title}'")
                    break
            else:
                # return NO_CONTEXT_WAS_ERROR       # Prevents keymapping on bare desktop/workspace.

                # Pantheon Wayland session appears to suffer from a defect that affects some other
                # desktop environments. When no window is open on a workspace, the desktop itself
                # will not be considered a focused window, so nothing will be returned from the `for`
                # loop, which means some dummy info must be returned instead of NO_CONTEXT_WAS_ERROR. 
                return {
                    "wm_class": 'ERR_No_Focused_Window', 
                    "wm_name": 'ERR_No_Focused_Window', 
                    "wndw_ctxt_error": False
                }

        except self.DBusException as dbus_error:
            error(f'{self.dbus_svc_name} interface stale?:\n\t{dbus_error}')
            error(f'Trying to refresh {self.dbus_svc_name} interface...')
            try:
                self.proxy_gala_svc = self.session_bus.get_object(
                    self.gala_dbus_obj, self.gala_dbus_path
                )
                self.iface_gala_svc = dbus.Interface(
                    self.proxy_gala_svc, 'org.pantheon.gala.DesktopIntegration'
                )
            except self.DBusException as dbus_error:
                error(f'Error refreshing {self.dbus_svc_name} interface.\n\t{dbus_error}')
                return NO_CONTEXT_WAS_ERROR

        debug(f"PANTHEON_CTX: Using D-Bus interface '{self.gala_dbus_obj}' for window context", ctx='CX')

        return {"wm_class": self.wm_class or self.app_id, "wm_name": self.title, "wndw_ctxt_error": False}


class Wl_COSMIC_WindowContext(WindowContextProviderInterface):
    """
    Window context provider object for Wayland+COSMIC environments.
    Nearly identical to the Wlroots context provider class, but talks
    to a different D-Bus service object/path interface address. 
    """

    def __init__(self):
        from dbus.exceptions import DBusException

        self.DBusException      = DBusException
        self.session_bus        = dbus.SessionBus()

        self.app_id             = None
        self.title              = None

        self.toshy_dbus_obj     = 'org.toshy.Cosmic'
        self.toshy_dbus_path    = '/org/toshy/Cosmic'
        self.dbus_svc_name      = 'Toshy COSMIC D-Bus service'

        while True:
            try:
                self.proxy_toshy_svc = self.session_bus.get_object( self.toshy_dbus_obj,
                                                                    self.toshy_dbus_path)
                self.iface_toshy_svc = dbus.Interface(  self.proxy_toshy_svc,
                                                        self.toshy_dbus_obj)
                break
            except self.DBusException as dbus_error:
                error(f'Error getting {self.dbus_svc_name} interface.\n\t{dbus_error}')
            time.sleep(3)

    @classmethod
    def get_supported_environments(cls):
        """
        This class supports the COSMIC environment on Wayland, by talking
        to the Toshy COSMIC D-Bus service at 'org.toshy.Cosmic'. 
        """
        return [
            # Window manager is 'cosmic-comp'
            ('wayland', 'cosmic-comp'),
            # TODO: Remove deprecated 'cosmic' desktop environment entry by mid-2027?
            ('wayland', 'cosmic'),
        ]

    def get_window_context(self):
        """
        Return window context to KeyContext
        Gets window context info from Toshy COSMIC D-Bus service, fed by Wayland events.
        """
        try:
            # Convert to native Python dict type from 'dbus.Dictionary()' type
            window_info_dct     = dict(self.iface_toshy_svc.GetActiveWindow())
        except self.DBusException as dbus_error:
            error(f'{self.dbus_svc_name} interface stale?:\n\t{dbus_error}')
            error(f'Trying to refresh {self.dbus_svc_name} interface...')
            try:
                self.proxy_toshy_svc = self.session_bus.get_object( self.toshy_dbus_obj,
                                                                    self.toshy_dbus_path)
                self.iface_toshy_svc = dbus.Interface(  self.proxy_toshy_svc,
                                                        self.toshy_dbus_obj)
            except self.DBusException as dbus_error:
                error(f'Error refreshing {self.dbus_svc_name} interface.\n\t{dbus_error}')
            try:
                # Convert to native Python dict type from 'dbus.Dictionary()' type
                window_info_dct     = dict(self.iface_toshy_svc.GetActiveWindow())
                debug(f'{self.dbus_svc_name} interface restored!')
            except self.DBusException as dbus_error: 
                debug(f'Error returned from {self.dbus_svc_name}:\n\t{dbus_error}')
                return NO_CONTEXT_WAS_ERROR

        # native_dict = {str(key): str(value) for key, value in dbus_dict.items()}
        new_wdw_info_dct    = {str(key): str(value) for key, value in window_info_dct.items()}

        self.app_id         = new_wdw_info_dct.get('app_id', '')
        self.title          = new_wdw_info_dct.get('title', '')

        debug(f"COSMIC_DBUS_SVC: Using D-Bus interface '{self.toshy_dbus_obj}' for window context", ctx='CX')

        return {"wm_class": self.app_id, "wm_name": self.title, "wndw_ctxt_error": False}


class Wl_Wlroots_WindowContext(WindowContextProviderInterface):
    """Window context provider object for Wayland+Wlroots environments"""

    def __init__(self):
        from dbus.exceptions import DBusException

        self.DBusException      = DBusException
        self.session_bus        = dbus.SessionBus()

        self.app_id             = None
        self.title              = None

        self.toshy_dbus_obj     = 'org.toshy.Wlroots'
        self.toshy_dbus_path    = '/org/toshy/Wlroots'
        self.dbus_svc_name      = 'Toshy Wlroots D-Bus service'

        while True:
            try:
                self.proxy_toshy_svc = self.session_bus.get_object( self.toshy_dbus_obj,
                                                                    self.toshy_dbus_path)
                self.iface_toshy_svc = dbus.Interface(  self.proxy_toshy_svc,
                                                        self.toshy_dbus_obj)
                break
            except self.DBusException as dbus_error:
                error(f'Error getting {self.dbus_svc_name} interface.\n\t{dbus_error}')
            time.sleep(3)

    @classmethod
    def get_supported_environments(cls):
        """
        This class supports the Wlroots environment on Wayland, as long as the 
        'wlr_foreign_toplevel_management_unstable_v1' protocol is implemented in 
        the Wayland compositor, and the version 3 'zwlr_foreign_toplevel_manager_v1'
        interface is available to bind to in the registry.
        """
        return [
            # There's no actual "wlroots" probably, it's generic. Leave at top of list.
            ('wayland', 'wlroots'),
            # Specific DEs/WMs that should work with "wlroots" provider (list may get long):
            ('wayland', 'hypr'),
            ('wayland', 'hyprland'),
            ('wayland', 'labwc'),
            ('wayland', 'miracle-wm'),
            ('wayland', 'miriway'),
            ('wayland', 'miriway-shell'),    # actual process name for 'miriway' compositor?
            ('wayland', 'niri'),
            ('wayland', 'qtile'),
            ('wayland', 'river'),
            ('wayland', 'sway'),
            ('wayland', 'wayfire'),
        ]

    def get_window_context(self):
        """
        Return window context to KeyContext
        Gets window context info from D-Bus service fed by Wlroots Wayland events, 
        from 'wlr_foreign_toplevel_management_unstable_v1' protocol.
        """
        try:
            # Convert to native Python dict type from 'dbus.Dictionary()' type
            window_info_dct     = dict(self.iface_toshy_svc.GetActiveWindow())
        except self.DBusException as dbus_error:
            error(f'{self.dbus_svc_name} interface stale?:\n\t{dbus_error}')
            error(f'Trying to refresh {self.dbus_svc_name} interface...')
            try:
                self.proxy_toshy_svc = self.session_bus.get_object( self.toshy_dbus_obj,
                                                                    self.toshy_dbus_path)
                self.iface_toshy_svc = dbus.Interface(  self.proxy_toshy_svc,
                                                        self.toshy_dbus_obj)
            except self.DBusException as dbus_error:
                error(f'Error refreshing {self.dbus_svc_name} interface.\n\t{dbus_error}')
            try:
                # Convert to native Python dict type from 'dbus.Dictionary()' type
                window_info_dct     = dict(self.iface_toshy_svc.GetActiveWindow())
                debug(f'{self.dbus_svc_name} interface restored!')
            except self.DBusException as dbus_error: 
                debug(f'Error returned from {self.dbus_svc_name}:\n\t{dbus_error}')
                return NO_CONTEXT_WAS_ERROR

        # native_dict = {str(key): str(value) for key, value in dbus_dict.items()}
        new_wdw_info_dct    = {str(key): str(value) for key, value in window_info_dct.items()}

        self.app_id         = new_wdw_info_dct.get('app_id', '')
        self.title          = new_wdw_info_dct.get('title', '')

        debug(f"WLR_DBUS_SVC: Using D-Bus interface '{self.toshy_dbus_obj}' for window context", ctx='CX')

        return {"wm_class": self.app_id, "wm_name": self.title, "wndw_ctxt_error": False}


class Wl_sway_WindowContext(WindowContextProviderInterface):
    """Window context provider object for Wayland+sway environments"""

    def __init__(self):

        # Create the connection object
        self.cnxn_obj           = None
        self._establish_connection()

        self.wm_class           = None
        self.wm_name            = None

    @classmethod
    def get_supported_environments(cls):
        # This class supports the sway window manager environment on Wayland
        return [
            ('wayland', 'sway'),
            ('wayland', 'swaywm'),
        ]

    def _establish_connection(self):
        """Establish a connection to sway IPC via i3ipc. Retry indefinitely if unsuccessful."""
        while True:
            try:
                self.cnxn_obj = i3ipc.Connection(auto_reconnect=True)
                debug(f'CTX_SWAY: Connection object created.')
                break
            # i3ipc.Connection() class may return generic Exception, or ConnectionError
            except (ConnectionError, Exception) as cnxn_err:
                error(f'ERROR: Problem connecting to sway IPC via i3ipc:\n\t{cnxn_err}')
                time.sleep(3)

    def get_active_wdw_ctx_sway_ipc(self):
        """Get sway window context via i3ipc Python module methods."""
        try:
            tree                    = self.cnxn_obj.get_tree()
        except ConnectionResetError as cnxn_err:
            debug(f"IPC connection was reset (sway).\t\n{cnxn_err}")
            return NO_CONTEXT_WAS_ERROR
        focused_wdw             = tree.find_focused()
        if not focused_wdw:
            debug("No window is currently focused.")
            return NO_CONTEXT_WAS_ERROR

        # self.wm_class           = focused_wdw.app_id or 'sway-ctx-error' # doesn't get app class for XWayland app
        self.wm_class           = focused_wdw.app_id or focused_wdw.window_class or 'sway-ctx-error'

        self.wm_name            = focused_wdw.name or 'sway-ctx-error' # use fallback for window_title below if necessary
        # self.wm_name            = focused_wdw.name or focused_wdw.window_title or 'sway-ctx-error'

        return {"wm_class": self.wm_class, "wm_name": self.wm_name, "wndw_ctxt_error": False}

    def get_window_context(self):
        """Return window context to KeyContext"""
        return self.get_active_wdw_ctx_sway_ipc()


class Wl_Hyprland_WindowContext(WindowContextProviderInterface):
    """Window context provider object for Wayland+Hyprland environments"""

    def __init__(self):
        from hyprpy import Hyprland
        self.hypr_inst      = Hyprland()

        self.first_run      = True
        self.sock           = None
        self.hyprctl_cmd    = shutil.which('hyprctl')
        self.wm_class       = None
        self.wm_name        = None

    @classmethod
    def get_supported_environments(cls):
        # This class supports the Hyprland window manager environment on Wayland
        return [
            ('wayland', 'hyprland'),
            ('wayland', 'hypr')
        ]

    def get_active_wdw_ctx_hyprpy(self):
        try:
            window_info         = self.hypr_inst.get_active_window()
            debug(f"CTX_HYPR: Using 'hyprpy' for window context.", ctx='CX')
            self.wm_class       = window_info.wm_class
            self.wm_name        = window_info.title
            return {"wm_class": self.wm_class, "wm_name": self.wm_name, "wndw_ctxt_error": False}
        except Exception as e:
            if "validation errors for WindowData" in str(e):
                debug('No active window found or incomplete window data.')
                return  {"wm_class": "hyprpy_no_window", "wm_name": "hyprpy_no_window", "wndw_ctxt_error": False}
            else:
                error(f"ERROR: Problem getting active window context using 'hyprpy'.\n\t{e}")
                return self.get_active_wdw_ctx_hypr_ipc()

    def _open_socket(self):
        """Utility function to open Hyprland IPC socket"""
        try:
            HIS = os.environ['HYPRLAND_INSTANCE_SIGNATURE']
        except KeyError as key_err:
            raise EnvironmentError('HYPRLAND_INSTANCE_SIGNATURE is not set. KeyError resulted.')
        if HIS is None:
            raise EnvironmentError('HYPRLAND_INSTANCE_SIGNATURE is not set.')
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.connect(f"/tmp/hypr/{HIS}/.socket.sock")

    def get_active_wdw_ctx_hypr_ipc(self):
        """Get Hyprland window context using IPC socket (faster than shell commands)."""
        try:
            if self.first_run or self.sock is None:
                try:
                    self._open_socket()
                    debug(f'CTX_HYPR: Using IPC socket for window context.', ctx='CX')
                except (socket.error, OSError, EnvironmentError) as conn_err:
                    error(f'ERROR: Problem opening Hyprland IPC socket.\n\t{conn_err}')
                    return self.get_active_wdw_ctx_hypr_shell() # Fallback to shell method
                self.first_run = False

            command = "-j activewindow"  # Replace with the actual command
            self.sock.sendall(command.encode("utf-8"))
            response: bytes     = self.sock.recv(1024)
            wdw_info_str        = response.decode('utf-8')

            # Check if the response is empty or not valid JSON
            if not wdw_info_str.strip():
                debug('No active window found or empty response from Hyprland IPC.')
                return {"wm_class": "hypr_no_window", "wm_name": "hypr_no_window", "wndw_ctxt_error": False}

            window_info: dict   = json.loads(wdw_info_str) # Type hint for VSCode "get()" highlight
            self.wm_class       = window_info.get("class", "hypr-context-error")
            self.wm_name        = window_info.get("title", "hypr-context-error")
            return {"wm_class": self.wm_class, "wm_name": self.wm_name, "wndw_ctxt_error": False}

        except json.JSONDecodeError as json_err:
            debug(f'No active window found or empty response from Hyprland IPC.\n\t{json_err}')
            return {"wm_class": "hyprIPC_no_window", "wm_name": "hyprIPC_no_window", "wndw_ctxt_error": False}
        except (socket.error, OSError) as ctx_err:
            error(f'ERROR: Problem getting window context via Hyprland IPC socket:\n\t{ctx_err}')
            # Close the socket
            if self.sock:
                self.sock.close()
                self.sock = None  # Mark it as None so it will be re-opened on the next run
            return NO_CONTEXT_WAS_ERROR

    def get_active_wdw_ctx_hypr_shell(self):
        """Get Hyprland window context using shell commands (will perform poorly)."""
        if not self.hyprctl_cmd:
            error(f'ERROR: Hyprland context fallback failed: "hyprctl" not found.')
            return NO_CONTEXT_WAS_ERROR
        try:
            cmd_lst = [self.hyprctl_cmd, '-j', 'activewindow']
            result = subprocess.run(cmd_lst, stdout=PIPE, stderr=PIPE, text=True, check=True)
            wdw_info_str        = result.stdout
            window_info: dict   = json.loads(wdw_info_str) # Type hint for VSCode "get()" highlight
            self.wm_class       = window_info.get("class", "hypr-context-error")
            self.wm_name        = window_info.get("title", "hypr-context-error")
            debug(f'CTX_HYPR: Using shell command (hyprctl) for window context (FALLBACK!).', ctx='CX')
            return {"wm_class": self.wm_class, "wm_name": self.wm_name, "wndw_ctxt_error": False}
        except json.JSONDecodeError as json_err:
            debug(f'No active window found or empty response from "hyprctl".\n\t{json_err}')
            return {"wm_class": "hyprctl_no_window", "wm_name": "hyprctl_no_window", "wndw_ctxt_error": False}
        except subprocess.CalledProcessError as proc_err:
            error(f"ERROR: Problem getting window context with hyprctl:\n\t{proc_err}")
            return NO_CONTEXT_WAS_ERROR

    def get_window_context(self):
        """Return window context to KeyContext"""
        # return self.get_active_wdw_ctx_hypr_ipc()
        return self.get_active_wdw_ctx_hyprpy()


class Wl_KWin_WindowContext(WindowContextProviderInterface):
    """Window context provider object for kwin_wayland environments, such
    as KDE Plasma, LXQt and other DEs that can use kwin_wayland."""

    def __init__(self):
        from dbus.exceptions import DBusException

        self.DBusException      = DBusException
        self.session_bus        = dbus.SessionBus()

        self.wm_class           = None
        self.wm_name            = None
        self.res_name           = None

        # Renamed the D-Bus object/path specifically for Plasma (there are others, like Wlroots)
        # TODO: Rename to reference KWin instead of Plasma? Other DEs can use kwin_wayland.
        self.toshy_dbus_obj     = 'org.toshy.Plasma'
        self.toshy_dbus_path    = '/org/toshy/Plasma'

        while True:
            try:
                self.proxy_toshy_svc = self.session_bus.get_object( self.toshy_dbus_obj,
                                                                    self.toshy_dbus_path)
                self.iface_toshy_svc = dbus.Interface(self.proxy_toshy_svc,
                                                        self.toshy_dbus_obj)
                break
            except self.DBusException as dbus_error:
                error(f'Error getting Toshy KWIN D-Bus service interface.\n\t{dbus_error}')
            time.sleep(3)

    @classmethod
    def get_supported_environments(cls):
        # This class supports the kwin_wayland environment (KDE Plasma, LXQt, etc.)
        return [
            # Window manager is 'kwin_wayland'
            ('wayland', 'kwin_wayland'),
            # TODO: Remove deprecated 'plasma' and 'kde' desktop environment entries by mid-2027?
            ('wayland', 'plasma'),
            ('wayland', 'kde'),
        ]

    def get_window_context(self):
        """
        Return window context to KeyContext
        Gets window context info from D-Bus service fed by KWin script
        """
        try:
            # Convert to native Python dict type from 'dbus.Dictionary()' type
            window_info_dct     = dict(self.iface_toshy_svc.GetActiveWindow())
        except self.DBusException as dbus_error:
            error(f'Toshy KWIN D-Bus service interface stale?:\n\t{dbus_error}')
            error(f'Trying to refresh Toshy KWIN D-Bus service interface...')
            try:
                self.proxy_toshy_svc = self.session_bus.get_object( self.toshy_dbus_obj,
                                                                    self.toshy_dbus_path)
                self.iface_toshy_svc = dbus.Interface(  self.proxy_toshy_svc,
                                                        self.toshy_dbus_obj)
            except self.DBusException as dbus_error:
                error(f'Error refreshing Toshy KWIN D-Bus service interface.\n\t{dbus_error}')
            try:
                # Convert to native Python dict type from 'dbus.Dictionary()' type
                window_info_dct     = dict(self.iface_toshy_svc.GetActiveWindow())
                debug(f'Toshy KWIN D-Bus service interface restored!')
            except self.DBusException as dbus_error: 
                debug(f'Error returned from Toshy KWIN D-Bus service:\n\t{dbus_error}')
                return NO_CONTEXT_WAS_ERROR

        # native_dict = {str(key): str(value) for key, value in dbus_dict.items()}
        new_wdw_info_dct    = {str(key): str(value) for key, value in window_info_dct.items()}
        # 'caption' is X11/Xorg WM_NAME equivalent
        self.wm_name        = new_wdw_info_dct.get('caption', '')
        # 'resourceClass' is X11/Xorg WM_CLASS equivalent
        self.wm_class       = new_wdw_info_dct.get('resource_class', '')
        # 'resourceName' has no X11/Xorg equivalent (tends to be process name?)
        self.res_name       = new_wdw_info_dct.get('resource_name', '')

        debug(f"KWIN_DBUS_CTX: Using D-Bus interface '{self.toshy_dbus_obj}' for window context", ctx='CX')

        return {"wm_class": self.wm_class, "wm_name": self.wm_name, "wndw_ctxt_error": False}


class Wl_Cinnamon_WindowContext(WindowContextProviderInterface):
    """Window context provider object for Wayland+Cinnamon environments"""

    def __init__(self):
        from dbus.exceptions import DBusException

        self.DBusException          = DBusException
        session_bus                 = dbus.SessionBus()

        path_toshy_focused_wdw      = "/app/toshy/ToshyFocusedWindow"
        obj_toshy_focused_wdw       = "app.toshy.ToshyFocusedWindow"
        proxy_toshy_focused_wdw     = None

        while proxy_toshy_focused_wdw is None:
            try:
                proxy_toshy_focused_wdw = session_bus.get_object("org.Cinnamon", path_toshy_focused_wdw)
            except DBusException as dbus_err:
                error(f"Problem getting D-Bus object: \n\t{dbus_err}")
                time.sleep(3)
        self.iface_toshy_focused_wdw = dbus.Interface(proxy_toshy_focused_wdw, obj_toshy_focused_wdw)

    @classmethod
    def get_supported_environments(cls):
        # This class supports the Cinnamon environment on Wayland
        return [
            ('wayland', 'cinnamon')
        ]

    def get_window_context(self):
        """
        This function gets the window context from the Toshy Cinnamon extension via D-Bus.
        """
        try:
            window_info_dbus = self.iface_toshy_focused_wdw.GetFocusedWindowInfo()
            window_info_dict = json.loads(window_info_dbus)

            wm_class = window_info_dict.get('appClass', '')
            wm_name = window_info_dict.get('windowTitle', '')
        except self.DBusException as dbus_err:
            print(f"Error querying Cinnamon extension: {dbus_err}")
            return NO_CONTEXT_WAS_ERROR

        debug(f"CINN_EXT: Using 'Toshy Focused Window Info' extension for window context.", ctx='CX')
        return {"wm_class": wm_class, "wm_name": wm_name, "wndw_ctxt_error": False}


class Wl_GNOME_WindowContext(WindowContextProviderInterface):
    """Window context provider object for Wayland+GNOME environments"""

    def __init__(self):
        # import dbus
        from dbus.exceptions import DBusException

        self.DBusException          = DBusException
        session_bus                 = dbus.SessionBus()

        path_focused_wdw            = "/org/gnome/shell/extensions/FocusedWindow"
        obj_focused_wdw             = "org.gnome.shell.extensions.FocusedWindow"
        proxy_focused_wdw           = session_bus.get_object("org.gnome.Shell", path_focused_wdw)
        self.iface_focused_wdw      = dbus.Interface(proxy_focused_wdw, obj_focused_wdw)

        path_windowsext             = "/org/gnome/Shell/Extensions/WindowsExt"
        obj_windowsext              = "org.gnome.Shell.Extensions.WindowsExt"
        proxy_windowsext            = session_bus.get_object("org.gnome.Shell", path_windowsext)
        self.iface_windowsext       = dbus.Interface(proxy_windowsext,obj_windowsext)

        path_xremap                 = "/com/k0kubun/Xremap"
        obj_xremap                  = "com.k0kubun.Xremap"
        proxy_xremap                = session_bus.get_object("org.gnome.Shell", path_xremap)
        self.iface_xremap           = dbus.Interface(proxy_xremap, obj_xremap)

        self.last_good_ext_uuid     = None
        self.cycle_count            = 0
        self.dbus_err_cnt           = 0
        self.max_dbus_err_cnt       = 15

        self.ext_uuid_focused_wdw   = 'focused-window-dbus@flexagoon.com'
        self.ext_uuid_windowsext    = 'window-calls-extended@hseliger.eu'
        self.ext_uuid_xremap        = 'xremap@k0kubun.com'

        self.GNOME_SHELL_EXTENSIONS = {
            self.ext_uuid_xremap:       self.get_wl_gnome_dbus_xremap_context,
            self.ext_uuid_windowsext:   self.get_wl_gnome_dbus_windowsext_context,
            self.ext_uuid_focused_wdw:  self.get_wl_gnome_dbus_focused_wdw_context,
        }

    @classmethod
    def get_supported_environments(cls):
        # This class supports the GNOME environment on Wayland
        return [
            # Window manager is 'gnome-shell'
            ('wayland', 'gnome-shell'),
            # TODO: Remove deprecated 'gnome' desktop environment entry by mid-2027? 
            ('wayland', 'gnome'),
            # 'mutter' observed as window manager process name in NixOS, in 2026-02-02
            ('wayland', 'mutter'),
        ]

    def get_window_context(self):
        """
        This function gets the window context from one of the compatible 
        GNOME Shell extensions, via D-Bus.
        
        It attempts to get the window context from the shell extension that 
        was successfully used last time.
        
        If it fails, it tries the others. If all fail, it returns an error.
        """

        # Order of the extensions
        extension_uuids = list(self.GNOME_SHELL_EXTENSIONS.keys())

        # If we have a last successful extension
        if self.last_good_ext_uuid in extension_uuids:
            starting_index = extension_uuids.index(self.last_good_ext_uuid)
        else:
            # We don't have a last successful extension, so start from the first
            starting_index = 0

        # Create a new list that starts with the last successful extension, followed by the others
        ordered_extensions = extension_uuids[starting_index:] + extension_uuids[:starting_index]

        for extension_uuid in ordered_extensions:
            try:
                # Call the function associated with the extension
                context = self.GNOME_SHELL_EXTENSIONS[extension_uuid]()
            except self.DBusException as dbus_err:
                dbus_err = str(dbus_err).replace("Object does not exist", "\n\t Object does not exist")
                debug(f"Error querying GNOME Shell extension '{extension_uuid}':\n\t{dbus_err}")
                # Continue to the next extension
                continue
            else:
                # No exceptions were thrown, so this extension is now the preferred one
                self.last_good_ext_uuid = extension_uuid
                self.dbus_err_cnt = 0
                debug(f"SHELL_EXT: Using UUID '{self.last_good_ext_uuid}' for window context", ctx='CX')
                return context

        # If we reach here, it means all extensions have failed
        self.last_good_ext_uuid = None

        if self.dbus_err_cnt >= self.max_dbus_err_cnt:
            self.dbus_err_cnt = 0
            self.max_dbus_err_cnt = randint(12, 17)
            self.show_error_all_exts_failed()
        elif self.dbus_err_cnt == 0:
            self.dbus_err_cnt += 1
            self.show_error_all_exts_failed()
        else:
            self.dbus_err_cnt += 1
            # Do not print error to avoid spamming the journal.

        return NO_CONTEXT_WAS_ERROR

    def show_error_all_exts_failed(self):
        """Print out informative error about all shell extensions failing to respond."""
        print()
        error(  f'############################################################################')
        error(  f'SHELL_EXT: No compatible GNOME Shell extension responding via D-Bus.'
                f'\n\t(Ignore this error if screen was locked/inactive at the time.)'
                f'\n\tThese shell extensions are compatible with keyszer:'
                f'\n\t  {self.ext_uuid_xremap} (supports pre-GNOME 41.x):'
                f'\n\t    (https://extensions.gnome.org/extension/5060/xremap/)'
                f'\n\t  {self.ext_uuid_windowsext}:'
                f'\n\t    (https://extensions.gnome.org/extension/4974/window-calls-extended/)'
                f'\n\t  {self.ext_uuid_focused_wdw}:'
                f'\n\t    (https://extensions.gnome.org/extension/5592/focused-window-d-bus/)')
        error(  f'Install "Extension Manager" from Flathub to manage GNOME Shell extensions')
        error(  f'############################################################################\n')

    def get_wl_gnome_dbus_focused_wdw_context(self):
        """utility function to query the 'Focused Window D-Bus' extension"""
        wm_class            = ''
        wm_name             = ''
        
        try:
            focused_wdw_dbus    = self.iface_focused_wdw.Get()
            # print(f'{focused_wdw_dbus = }')
            focused_wdw_dct     = json.loads(focused_wdw_dbus)
            # print(f'{focused_wdw_dct = }')

            wm_class            = focused_wdw_dct.get('wm_class', '')
            wm_name             = focused_wdw_dct.get('title', '')
        except self.DBusException as dbus_error:
            # This will be the error if no window info found (e.g., GNOME desktop):
            # org.gnome.gjs.JSError.Error: No window in focus
            if 'No window in focus' in str(dbus_error): pass
            else: raise   # pass on the original exception if not 'No window in focus'

        return {"wm_class": wm_class, "wm_name": wm_name, "wndw_ctxt_error": False}

    def get_wl_gnome_dbus_windowsext_context(self):
        """utility function to query the 'Window Calls Extended' extension"""
        wm_class            = ''
        wm_name             = ''

        wm_class            = str(self.iface_windowsext.FocusClass())
        wm_name             = str(self.iface_windowsext.FocusTitle())

        return {"wm_class": wm_class, "wm_name": wm_name, "wndw_ctxt_error": False}

    def get_wl_gnome_dbus_xremap_context(self):
        """utility function to query the 'Xremap' extension"""
        active_window_dbus  = ''
        active_window_dct   = ''
        wm_class            = ''
        wm_name             = ''

        active_window_dbus  = self.iface_xremap.ActiveWindow()
        active_window_dct   = json.loads(active_window_dbus)

        # use get() with default value to avoid KeyError for 
        # GNOME Shell/desktop lack of properties returned
        active_window_dct: 'dict[str, str]'
        wm_class            = active_window_dct.get('wm_class', '')
        wm_name             = active_window_dct.get('title', '')

        return {"wm_class": wm_class, "wm_name": wm_name, "wndw_ctxt_error": False}


class Xorg_WindowContext(WindowContextProviderInterface):
    """Window context provider object for X11/Xorg environments"""

    def __init__(self):
        self._display = None

        # Import Xlib modules here
        from Xlib.xobject.drawable import Window
        from Xlib.display import Display
        from Xlib.error import (
                            ConnectionClosedError,
                            DisplayConnectionError,
                            DisplayNameError,
                            BadValue,
                            BadWindow
                            )
        self.Window                 = Window
        self.Display                = Display
        self.ConnectionClosedError  = ConnectionClosedError
        self.DisplayConnectionError = DisplayConnectionError
        self.DisplayNameError       = DisplayNameError
        self.BadValue               = BadValue
        self.BadWindow              = BadWindow

    @classmethod
    def get_supported_environments(cls):
        # This class supports any X11/Xorg window manager
        return [
            ('x11', None),
        ]

    def get_window_context(self):
        """
        Get window context from Xorg, window name, class,
        whether there is an X error or not
        """
        try:
            self._display = self._display or self.Display()
            wm_class    = ""
            wm_name     = ""

            input_focus = self._display.get_input_focus().focus
            window      = self.get_actual_window(input_focus)
            if window:
                # We use _NET_WM_NAME string (UTF-8) here instead of WM_NAME to 
                # bypass (COMPOUND_TEXT) encoding problems when non-ASCII
                # characters are in the window name string.
                # Xlib cannot deal with COMPOUND_TEXT encoding and ends up
                # returning an empty "bytes object": b''
                
                # Older form: 
                # wm_name = window.get_full_text_property(self._display.get_atom("_NET_WM_NAME"))
                
                # Mitigation for '_NET_WM_NAME' not being set at all(!), but WM_NAME is good:
                # (this was observed in KDE 4.x application launcher/menu)
                wm_name = window.get_full_text_property(self._display.get_atom("_NET_WM_NAME"))
                if wm_name is None:
                    error(f'Xlib _NET_WM_NAME query returned NoneType, falling back to WM_NAME')
                    wm_name = window.get_wm_name()
                    if isinstance(wm_name, bytes):
                        error(f'Xlib WM_NAME query returned bytes object, falling back to error string')
                        wm_name = "ERR: Xorg_WindowContext: Bad _NET_WM_NAME and WM_NAME"
                pair    = window.get_wm_class()
                if pair:
                    wm_class = str(pair[1])
            
            debug(f"CTX_X11: Using Xlib for window context", ctx='CX')

            return {"wm_class": wm_class, "wm_name": wm_name, "wndw_ctxt_error": False}

        except self.ConnectionClosedError as xerror:
            error(xerror)
            self._display = None
            return NO_CONTEXT_WAS_ERROR
        # most likely DISPLAY env isn't even set
        except self.DisplayNameError as xerror:
            error(xerror)
            self._display = None
            return NO_CONTEXT_WAS_ERROR
        # seen when we don't have permission to the X display
        except self.DisplayConnectionError as xerror:
            error(xerror)
            self._display = None
            return NO_CONTEXT_WAS_ERROR

    def get_actual_window(self, window):
        if not isinstance(window, self.Window):
            return None

        # # use _NET_WM_NAME string instead of WM_NAME to bypass (COMPOUND_TEXT) encoding problems
        # wmname = window.get_full_text_property(self._display.get_atom("_NET_WM_NAME"))
        # wmclass = window.get_wm_class()

        try:
            # use _NET_WM_NAME string instead of WM_NAME to bypass (COMPOUND_TEXT) encoding problems
            wmname = window.get_full_text_property(self._display.get_atom("_NET_WM_NAME"))
            wmclass = window.get_wm_class()
        except self.BadWindow as xerror:
            error(xerror)
            return None  # or do some appropriate handling here
        except self.BadValue as xerror:
            error(xerror)
            return None  # or do some appropriate handling here

        # workaround for Java app
        # https://github.com/JetBrains/jdk8u_jdk/blob/master/src/solaris/classes/sun/awt/X11/XFocusProxyWindow.java#L35
        if (wmclass is None and wmname is None) or "FocusProxy" in (wmclass or ""):
            parent_window = window.query_tree().parent
            if parent_window:
                return self.get_actual_window(parent_window)
            return None

        return window
