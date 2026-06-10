# toshy_common/kblayout_detect/kbld_backend_x11.py
"""Generic X11 (XKB) keyboard-layout backend.

Reads the live group index from libX11 (XkbGetState via ctypes) and resolves
it against _XKB_RULES_NAMES (read with python-xlib). Split out verbatim from
the former single-module kblayout_detect; behavior is unchanged.

Backends never import each other - only kbld_backend_base and the shared
kblayout_common types."""

__version__ = '20260608'

import os
import ctypes
import ctypes.util
import select
import threading


# Guarded python-xlib import for the X11 backend's _XKB_RULES_NAMES read.
# (python-xlib has no XKB binding, so the live group comes from libX11 via
# ctypes; python-xlib is used only for the property read it does cleanly.)
try:
    from Xlib import display as xlib_display
    _HAVE_XLIB = True
except ImportError:
    _HAVE_XLIB = False


from toshy_common.kblayout_common import make_layout_spec
from toshy_common.kblayout_detect.kbld_backend_base import (
    LayoutBackend,
    _warn,
)


XKB_USE_CORE_KBD     = 0x0100
XKB_STATE_NOTIFY     = 2
XKB_GROUP_STATE_MASK = (1 << 4)
XKB_GROUP_BASE_MASK  = (1 << 5)
XKB_GROUP_LATCH_MASK = (1 << 6)
XKB_GROUP_LOCK_MASK  = (1 << 7)
XKB_GROUP_MASKS      = (XKB_GROUP_STATE_MASK | XKB_GROUP_BASE_MASK
                        | XKB_GROUP_LATCH_MASK | XKB_GROUP_LOCK_MASK)
XKB_RULES_NAMES_PROP = '_XKB_RULES_NAMES'
XA_STRING            = 31    # predefined X11 atom for STRING (X11/Xatom.h)


class XkbStateRec(ctypes.Structure):
    """libX11 XkbStateRec. Only .group is read; laid out fully for correctness."""

    _fields_ = [
        ('group',               ctypes.c_ubyte),
        ('locked_group',        ctypes.c_ubyte),
        ('base_group',          ctypes.c_ushort),
        ('latched_group',       ctypes.c_ushort),
        ('mods',                ctypes.c_ubyte),
        ('base_mods',           ctypes.c_ubyte),
        ('latched_mods',        ctypes.c_ubyte),
        ('locked_mods',         ctypes.c_ubyte),
        ('compat_state',        ctypes.c_ubyte),
        ('grab_mods',           ctypes.c_ubyte),
        ('compat_grab_mods',    ctypes.c_ubyte),
        ('lookup_mods',         ctypes.c_ubyte),
        ('compat_lookup_mods',  ctypes.c_ubyte),
        ('ptr_buttons',         ctypes.c_ushort),
    ]


class X11XkbBackend(LayoutBackend):
    """X11/Xorg layout detection via the XKB extension.

    python-xlib ships no XKB binding, so the live group index comes from libX11
    through ctypes (XkbGetState), and group-change events arrive via
    XkbSelectEventDetails filtered to the group state only, so ordinary typing
    (which changes modifier state) never wakes the watcher. The (layout,
    variant) table comes from the _XKB_RULES_NAMES root-window property, read
    through python-xlib and re-read on each event so layout reorders/edits stay
    aligned with the index. XKB state is global on X11, so this observes
    switches regardless of which window has focus.

    The watcher blocks in select() on the X connection fd plus a self-pipe, so
    stop() can wake it immediately for a clean shutdown. Verified on Xorg/XFCE.
    """

    name = 'x11-xkb'
    priority = 50

    @classmethod
    def claims(cls, desktop_env, session_type, compositor):
        return session_type == 'x11'

    def __init__(self):
        self._init_watch_state()
        self._lib = None            # ctypes libX11 handle
        self._stop_flag = False
        self._wake_r = None
        self._wake_w = None

    # ── libX11 (ctypes) ──────────────────────────────────────────────────

    def _libx11(self):
        if self._lib is not None:
            return self._lib
        path = ctypes.util.find_library('X11') or 'libX11.so.6'
        lib = ctypes.CDLL(path)
        lib.XOpenDisplay.restype = ctypes.c_void_p
        lib.XOpenDisplay.argtypes = [ctypes.c_char_p]
        lib.XCloseDisplay.argtypes = [ctypes.c_void_p]
        lib.XConnectionNumber.restype = ctypes.c_int
        lib.XConnectionNumber.argtypes = [ctypes.c_void_p]
        lib.XPending.restype = ctypes.c_int
        lib.XPending.argtypes = [ctypes.c_void_p]
        lib.XNextEvent.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        lib.XFlush.argtypes = [ctypes.c_void_p]
        lib.XkbQueryExtension.restype = ctypes.c_int
        lib.XkbQueryExtension.argtypes = [ctypes.c_void_p] + [ctypes.POINTER(ctypes.c_int)] * 5
        lib.XkbSelectEventDetails.restype = ctypes.c_int
        lib.XkbSelectEventDetails.argtypes = [ctypes.c_void_p, ctypes.c_uint,
                                              ctypes.c_uint, ctypes.c_ulong, ctypes.c_ulong]
        lib.XkbGetState.restype = ctypes.c_int
        lib.XkbGetState.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.POINTER(XkbStateRec)]
        self._lib = lib
        return lib

    def _xkb_present(self, lib, dpy):
        op = ctypes.c_int(); ev = ctypes.c_int(); er = ctypes.c_int()
        maj = ctypes.c_int(1); minr = ctypes.c_int(0)
        return bool(lib.XkbQueryExtension(
            dpy, ctypes.byref(op), ctypes.byref(ev),
            ctypes.byref(er), ctypes.byref(maj), ctypes.byref(minr)))

    def _group(self, lib, dpy):
        state = XkbStateRec()
        lib.XkbGetState(dpy, XKB_USE_CORE_KBD, ctypes.byref(state))
        return state.group

    # ── table from _XKB_RULES_NAMES (python-xlib) ────────────────────────

    def _read_table(self, pyx_disp):
        root = pyx_disp.screen().root
        atom = pyx_disp.intern_atom(XKB_RULES_NAMES_PROP)
        prop = root.get_full_property(atom, XA_STRING)
        if prop is None:
            return []
        raw = prop.value
        text = raw if isinstance(raw, str) else bytes(raw).decode('latin-1', 'replace')
        fields_lst = text.split('\x00')   # rules, model, layout, variant, options
        layout_str = fields_lst[2] if len(fields_lst) > 2 else ''
        variant_str = fields_lst[3] if len(fields_lst) > 3 else ''
        layout_lst = [x.strip() for x in layout_str.split(',')] if layout_str else []
        variant_lst = [x.strip() for x in variant_str.split(',')] if variant_str else []

        table_lst = []
        for idx, layout in enumerate(layout_lst):
            if not layout:
                continue
            variant = variant_lst[idx] if idx < len(variant_lst) else ''
            table_lst.append(make_layout_spec(layout, variant, None))
        return table_lst

    def _resolve_current(self, lib, dpy, pyx_disp):
        table_lst = self._read_table(pyx_disp)     # fresh each time: reorder-safe
        group = self._group(lib, dpy)
        if group < 0 or group >= len(table_lst):
            return None
        return table_lst[group]

    # ── availability + one-shot query ────────────────────────────────────

    def available(self):
        if not _HAVE_XLIB:
            return False
        try:
            lib = self._libx11()
        except OSError:
            return False
        dpy = lib.XOpenDisplay(None)
        if not dpy:
            return False
        present = self._xkb_present(lib, dpy)
        lib.XCloseDisplay(dpy)
        return present

    def get_active_layout(self):
        if not _HAVE_XLIB:
            return None
        try:
            lib = self._libx11()
        except OSError:
            return None
        dpy = lib.XOpenDisplay(None)
        if not dpy:
            return None
        if not self._xkb_present(lib, dpy):
            lib.XCloseDisplay(dpy)
            return None
        try:
            pyx_disp = xlib_display.Display()
        except Exception as disp_err:
            _warn(f'X11: python-xlib display open failed: {disp_err}')
            lib.XCloseDisplay(dpy)
            return None
        try:
            return self._resolve_current(lib, dpy, pyx_disp)
        finally:
            pyx_disp.close()
            lib.XCloseDisplay(dpy)

    # ── watcher (XKB events via select() on the X fd) ────────────────────

    def start(self, callback):
        if not self.available():
            _warn('X11 XKB backend not available.')
            return False
        if self._thread is not None:
            return True
        self._callback = callback
        self._stop_flag = False
        self._wake_r, self._wake_w = os.pipe()
        self._thread = threading.Thread(
            target=self._run, name='x11-layout-watch', daemon=True)
        self._thread.start()
        return True

    def _run(self):
        lib = self._libx11()
        dpy = lib.XOpenDisplay(None)
        if not dpy:
            _warn('X11: XOpenDisplay failed in watcher.')
            return
        if not self._xkb_present(lib, dpy):
            _warn('X11: XKB not present in watcher.')
            lib.XCloseDisplay(dpy)
            return
        try:
            pyx_disp = xlib_display.Display()
        except Exception as disp_err:
            _warn(f'X11: python-xlib display open failed in watcher: {disp_err}')
            lib.XCloseDisplay(dpy)
            return

        # Subscribe to StateNotify, group details only — typing must not wake us.
        lib.XkbSelectEventDetails(dpy, XKB_USE_CORE_KBD, XKB_STATE_NOTIFY,
                                  XKB_GROUP_MASKS, XKB_GROUP_MASKS)
        lib.XFlush(dpy)
        x_fd = lib.XConnectionNumber(dpy)
        event_buf = ctypes.create_string_buffer(256)   # XEvent union scratch

        # Prime so the consumer learns the starting layout.
        self._emit(self._resolve_current(lib, dpy, pyx_disp))

        try:
            while not self._stop_flag:
                try:
                    readable, _, _ = select.select([x_fd, self._wake_r], [], [])
                except (OSError, ValueError):
                    break
                if self._wake_r in readable:
                    try:
                        os.read(self._wake_r, 64)
                    except OSError:
                        pass
                    break
                if x_fd in readable:
                    woke = False
                    while lib.XPending(dpy) > 0:
                        lib.XNextEvent(dpy, event_buf)
                        woke = True
                    if woke:
                        self._emit(self._resolve_current(lib, dpy, pyx_disp))
        finally:
            pyx_disp.close()
            lib.XCloseDisplay(dpy)

    def stop(self):
        self._stop_flag = True
        if self._wake_w is not None:
            try:
                os.write(self._wake_w, b'x')
            except OSError:
                pass
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        for fd in (self._wake_r, self._wake_w):
            if fd is not None:
                try:
                    os.close(fd)
                except OSError:
                    pass
        self._wake_r = None
        self._wake_w = None
        self._thread = None


# End of file #
