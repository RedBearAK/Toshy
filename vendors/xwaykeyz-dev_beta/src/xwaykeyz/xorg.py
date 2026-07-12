from Xlib.xobject.drawable import Window
from Xlib.display import Display
from Xlib.error import (
    ConnectionClosedError,
    DisplayConnectionError,
    DisplayNameError,
)

from .lib.logger import error

# https://github.com/python-xlib/python-xlib/blob/master/Xlib/display.py#L153
# https://stackoverflow.com/questions/23786289/how-to-correctly-detect-application-name-when-changing-focus-event-occurs-with

# TODO: keep tabs on active window vs constant querying?


NO_CONTEXT_WAS_ERROR = {"wm_class": "", "wm_name": "", "wndw_ctxt_error": True}
_display = None


def get_xorg_context():
    """
    Get window context from Xorg, window name, class,
    whether there is an X error or not
    """
    global _display
    try:
        _display = _display or Display()
        wm_class = ""
        wm_name  = ""

        input_focus = _display.get_input_focus().focus
        window      = get_actual_window(input_focus)
        if window:
            # use _NET_WM_NAME string instead of WM_NAME to bypass (COMPOUND_TEXT) encoding problems
            wm_name = window.get_full_text_property(_display.get_atom("_NET_WM_NAME"))
            pair    = window.get_wm_class()
            if pair:
                wm_class = str(pair[1])

        return {"wm_class": wm_class, "wm_name": wm_name, "wndw_ctxt_error": False}

    except ConnectionClosedError as xerror:
        error(xerror)
        _display = None
        return NO_CONTEXT_WAS_ERROR
    # most likely DISPLAY env isn't even set
    except DisplayNameError as xerror:
        error(xerror)
        _display = None
        return NO_CONTEXT_WAS_ERROR
    # seen when we don't have permission to the X display
    except DisplayConnectionError as xerror:
        error(xerror)
        _display = None
        return NO_CONTEXT_WAS_ERROR


def get_actual_window(window):
    if not isinstance(window, Window):
        return None

    # use _NET_WM_NAME string instead of WM_NAME to bypass (COMPOUND_TEXT) encoding problems
    wmname  = window.get_full_text_property(_display.get_atom("_NET_WM_NAME"))
    wmclass = window.get_wm_class()
    # workaround for Java app
    # https://github.com/JetBrains/jdk8u_jdk/blob/master/src/solaris/classes/sun/awt/X11/XFocusProxyWindow.java#L35
    if (wmclass is None and wmname is None) or "FocusProxy" in (wmclass or ""):
        parent_window = window.query_tree().parent
        if parent_window:
            return get_actual_window(parent_window)
        return None

    return window
