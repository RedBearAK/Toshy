"""Active keyboard-layout detection for Toshy.

    toshy_common/kblayout_detect.py

Single-purpose module: report the currently active keyboard layout as a
(layout, variant) pair, and notify a consumer when it changes. This is the
input side that feeds the layout-analysis/correction module
(kblayout_context.py); it does not itself analyze keymaps.

Design notes
------------
Backends are selected by environment context (desktop environment and
session type), which the caller is expected to inject because the keymapper
already computes it. When not injected, the values come from Toshy's
EnvironmentInfo (toshy_common.env_context) — the same canonical detector the
rest of Toshy relies on — rather than a separate, less capable probe.

Each backend runs its own native watch loop (a GLib main loop for the D-Bus
and GSettings backends) inside a daemon thread, and funnels layout changes
through one callback. Threading is the integration boundary so that a
backend's loop model never has to compose with the keymapper's own loop;
the callback fires on the watcher thread, so a consumer with its own loop
should marshal back to it.

Everything here is read-only with respect to the desktop environment: the
module observes layout state, it never sets it.

The KDE backend is verified against Plasma 6 (Wayland). The GNOME backend's
mru-sources read is confirmed on a live session (the gi watch path is not yet
exercised). The X11 backend reads the live group from libX11 via ctypes, since
python-xlib has no XKB binding, and is verified on Xorg/XFCE. The generic
Wayland backend is a placeholder for a future wl_keyboard reader.
"""

__version__ = '20260603'

import os
import sys
import ctypes
import ctypes.util
import select
import signal
import threading


# Guarded PyGObject import: the module must still load (for the pure-Python
# parsers and for graceful degradation) on systems without gi.
try:
    import gi
    gi.require_version('Gio', '2.0')
    gi.require_version('GLib', '2.0')
    from gi.repository import Gio, GLib
    _HAVE_GI = True
except (ImportError, ValueError):
    _HAVE_GI = False


# Guarded python-xlib import for the X11 backend's _XKB_RULES_NAMES read.
# (python-xlib has no XKB binding, so the live group comes from libX11 via
# ctypes; python-xlib is used only for the property read it does cleanly.)
try:
    from Xlib import display as xlib_display
    _HAVE_XLIB = True
except ImportError:
    _HAVE_XLIB = False


# When run directly from inside the toshy_common/ folder, only that folder is
# on sys.path, so the 'toshy_common' package name can't resolve. Put the Toshy
# root (the parent of this file's folder) on the path before the local import.
# Idempotent and harmless when already importable (e.g. loaded by the config).
_toshy_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _toshy_root not in sys.path:
    sys.path.insert(0, _toshy_root)

from toshy_common.env_context import EnvironmentInfo
from toshy_common.kblayout_common import (
    format_layout,
    make_layout_spec,
)


# ── Constants ───────────────────────────────────────────────────────────

KDE_DBUS_SERVICE    = 'org.kde.keyboard'
KDE_DBUS_PATH       = '/Layouts'
KDE_DBUS_INTERFACE  = 'org.kde.KeyboardLayouts'
KDE_DBUS_TIMEOUT_MS = 2000
KDE_KXKBRC_PATH     = '~/.config/kxkbrc'

GNOME_GS_SCHEMA     = 'org.gnome.desktop.input-sources'
GNOME_GS_KEY_MRU    = 'mru-sources'
GNOME_GS_KEY_SOURCES = 'sources'

# X11 XKB (libX11 via ctypes). XKB state component masks from X11/extensions/XKB.h.
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


def _warn(message):
    """Emit a non-fatal warning.

    Placeholder for standalone use; on integration this should be swapped
    for Toshy's existing debug/error logger.
    """
    print(f'(kblayout_detect) WARNING: {message}', file=sys.stderr)


# ── Pure-Python parsers ─────────────────────────────────────────────────

def parse_kxkbrc_layouts(text):
    """Parse a kxkbrc file's [Layout] section into parallel lists.

    Returns (layout_lst, variant_lst), both the same length, where a missing
    or empty variant is the empty string. Returns ([], []) if there is no
    usable [Layout] section. KDE writes LayoutList and VariantList as
    positionally-parallel, comma-separated values, e.g.

        LayoutList=us,us,fr
        VariantList=,mac-iso,azerty
    """
    layout_lst = []
    variant_lst = []
    in_layout_section = False

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#'):
            continue
        if line.startswith('['):
            in_layout_section = (line == '[Layout]')
            continue
        if not in_layout_section or '=' not in line:
            continue

        key, _, value = line.partition('=')
        key = key.strip()
        value = value.strip()

        if key == 'LayoutList':
            layout_lst = [item.strip() for item in value.split(',')] if value else []
        elif key == 'VariantList':
            variant_lst = [item.strip() for item in value.split(',')] if value else []

    # Keep the variant list aligned to the layout list length.
    while len(variant_lst) < len(layout_lst):
        variant_lst.append('')
    variant_lst = variant_lst[:len(layout_lst)]

    return layout_lst, variant_lst


def parse_gnome_source(type_str, id_str):
    """Convert a GNOME input-source (type, id) into a LayoutSpec, or None.

    Only 'xkb' sources correspond to a plain XKB layout. The id is of the
    form 'layout' or 'layout+variant' (e.g. 'us', 'us+intl', 'fr+azerty').
    Non-xkb sources (e.g. 'ibus' engines) return None.
    """
    if type_str != 'xkb' or not id_str:
        return None
    layout, _, variant = id_str.partition('+')
    layout = layout.strip()
    variant = variant.strip() or None
    if not layout:
        return None
    return make_layout_spec(layout, variant, None)


# ── Backend base ────────────────────────────────────────────────────────

class LayoutBackend:
    """Common interface and shared watch-state for layout backends."""

    name = 'base'

    def _init_watch_state(self):
        self._callback = None
        self._thread = None
        self._loop = None
        self._last = None

    def available(self):
        return False

    def get_active_layout(self):
        """One-shot query. Returns a LayoutSpec or None."""
        return None

    def start(self, callback):
        """Begin watching. callback(LayoutSpec) fires on the watcher thread."""
        return False

    def stop(self):
        pass

    def _emit(self, spec):
        """Deliver a change to the consumer, deduped by (layout, variant)."""
        if spec is None:
            return
        key = (spec.layout, spec.variant)
        if key == self._last:
            return
        self._last = key
        if self._callback:
            try:
                self._callback(spec)
            except Exception as callback_err:
                _warn(f'Layout-change callback raised: {callback_err}')

    def _stop_loop_thread(self):
        """Shared teardown for GLib-loop backends."""
        loop = self._loop
        if loop is not None:
            loop.quit()
        thread = self._thread
        if thread is not None:
            thread.join(timeout=2.0)
        self._thread = None
        self._loop = None


# ── KDE backend (D-Bus + kxkbrc) ────────────────────────────────────────

class KdeBackend(LayoutBackend):
    """KDE Plasma layout detection.

    The live active index comes from org.kde.KeyboardLayouts.getLayout() and
    the layoutChanged(u) signal (focus-independent, since it is a session-bus
    broadcast). The index is resolved to (layout, variant) through kxkbrc's
    parallel LayoutList/VariantList, which carry the precise XKB variant codes
    that the D-Bus longName only describes in prose. getLayoutsList() is used
    as a cross-check (its shortName must match kxkbrc's LayoutList) and as the
    source of the human-readable label.
    """

    name = 'kde-dbus'

    def __init__(self):
        self._init_watch_state()
        self._table = []        # list of LayoutSpec, indexed by layout index
        self._sub_ids = []

    def available(self):
        if not _HAVE_GI:
            return False
        try:
            self._call_get_layout()     # liveness probe; no main loop needed
            return True
        except Exception:
            return False

    # ── synchronous D-Bus helpers (no running loop required) ──

    def _bus(self):
        return Gio.bus_get_sync(Gio.BusType.SESSION, None)

    def _call_get_layout(self):
        reply = self._bus().call_sync(
            KDE_DBUS_SERVICE, KDE_DBUS_PATH, KDE_DBUS_INTERFACE,
            'getLayout', None, GLib.VariantType.new('(u)'),
            Gio.DBusCallFlags.NONE, KDE_DBUS_TIMEOUT_MS, None,
        )
        return reply.unpack()[0]

    def _call_get_layouts_list(self):
        reply = self._bus().call_sync(
            KDE_DBUS_SERVICE, KDE_DBUS_PATH, KDE_DBUS_INTERFACE,
            'getLayoutsList', None, GLib.VariantType.new('(a(sss))'),
            Gio.DBusCallFlags.NONE, KDE_DBUS_TIMEOUT_MS, None,
        )
        # Each entry is (shortName, displayName, longName).
        return reply.unpack()[0]

    def _read_kxkbrc(self):
        path = os.path.expanduser(KDE_KXKBRC_PATH)
        if not os.path.isfile(path):
            return [], []
        try:
            with open(path, 'r') as kxkbrc_file:
                text = kxkbrc_file.read()
        except OSError as read_err:
            _warn(f'Could not read {path}: {read_err}')
            return [], []
        return parse_kxkbrc_layouts(text)

    def _build_table(self):
        """Build the index -> LayoutSpec table from kxkbrc + D-Bus list."""
        dbus_list = self._call_get_layouts_list()
        layout_lst, variant_lst = self._read_kxkbrc()

        # Preferred path: kxkbrc supplies precise variant codes. Cross-check
        # that its order matches the D-Bus list before trusting it.
        if layout_lst and len(layout_lst) == len(dbus_list):
            order_matches = all(
                dbus_list[i][0] == layout_lst[i] for i in range(len(dbus_list))
            )
            if order_matches:
                table = []
                for i, entry in enumerate(dbus_list):
                    long_name = entry[2]
                    variant = variant_lst[i] if i < len(variant_lst) else ''
                    table.append(make_layout_spec(layout_lst[i], variant, long_name or None))
                self._table = table
                return
            _warn('kxkbrc layout order does not match D-Bus list; falling back '
                  'to layout-only resolution (variants unavailable).')
        elif layout_lst:
            _warn(f'kxkbrc lists {len(layout_lst)} layouts but D-Bus reports '
                  f'{len(dbus_list)}; falling back to layout-only resolution.')

        # Degraded fallback: D-Bus shortName as the layout, no variant. Wrong
        # about the variant, but never wrong about which base layout is active.
        self._table = [
            make_layout_spec(entry[0], None, entry[2] or None) for entry in dbus_list
        ]

    def _resolve(self, index):
        if not self._table:
            self._build_table()
        if index < 0 or index >= len(self._table):
            _warn(f'Layout index {index} out of range for {len(self._table)} layouts.')
            return None
        return self._table[index]

    def get_active_layout(self):
        if not _HAVE_GI:
            return None
        try:
            self._build_table()
            index = self._call_get_layout()
        except Exception as query_err:
            _warn(f'KDE layout query failed: {query_err}')
            return None
        return self._resolve(index)

    # ── watch (GLib loop in a daemon thread) ──

    def start(self, callback):
        if not _HAVE_GI:
            _warn('PyGObject (gi) not available; cannot watch KDE layout changes.')
            return False
        if self._thread is not None:
            return True
        self._callback = callback
        self._thread = threading.Thread(
            target=self._run, name='kde-layout-watch', daemon=True)
        self._thread.start()
        return True

    def _run(self):
        ctx = GLib.MainContext.new()
        ctx.push_thread_default()
        self._loop = GLib.MainLoop.new(ctx, False)
        try:
            conn = self._bus()
            self._sub_ids = [
                conn.signal_subscribe(
                    KDE_DBUS_SERVICE, KDE_DBUS_INTERFACE, 'layoutChanged',
                    KDE_DBUS_PATH, None, Gio.DBusSignalFlags.NONE,
                    self._on_layout_changed),
                conn.signal_subscribe(
                    KDE_DBUS_SERVICE, KDE_DBUS_INTERFACE, 'layoutListChanged',
                    KDE_DBUS_PATH, None, Gio.DBusSignalFlags.NONE,
                    self._on_layout_list_changed),
            ]

            # Prime with current state so the consumer learns the start layout.
            try:
                self._build_table()
                self._emit(self._resolve(self._call_get_layout()))
            except Exception as prime_err:
                _warn(f'KDE initial layout read failed: {prime_err}')

            self._loop.run()

            for sub_id in self._sub_ids:
                conn.signal_unsubscribe(sub_id)
            self._sub_ids = []
        finally:
            ctx.pop_thread_default()

    def _on_layout_changed(self, conn, sender, path, iface, signal_name, params):
        index = params.unpack()[0]
        self._emit(self._resolve(index))

    def _on_layout_list_changed(self, conn, sender, path, iface, signal_name, params):
        # Layout set changed; rebuild the table and re-evaluate the active one,
        # since indices may have shifted. Dedup suppresses the signal's noise.
        try:
            self._build_table()
            self._emit(self._resolve(self._call_get_layout()))
        except Exception as rebuild_err:
            _warn(f'KDE layout-list rebuild failed: {rebuild_err}')

    def stop(self):
        self._stop_loop_thread()


# ── GNOME backend (GSettings) ───────────────────────────────────────────

class GnomeBackend(LayoutBackend):
    """GNOME layout detection via org.gnome.desktop.input-sources.

    The active source is mru-sources[0] (most-recently-used order; the active
    layout sits at the front and moves there on each switch). The 'current'
    key is deliberately NOT used: it is nominally an index into 'sources' but
    in practice often stays stuck (e.g. at 0) and does not track switches.
    'sources' is the stable configured catalog. Changes arrive as the
    GSettings 'changed::mru-sources' signal on a running GLib loop, which
    fires for an unfocused observer.

    Verified against the gsettings values on a live GNOME (Fedora 43) session;
    the gi code path itself has not been live-exercised here.
    """

    name = 'gnome-gsettings'

    def __init__(self):
        self._init_watch_state()
        self._settings = None

    def available(self):
        if not _HAVE_GI:
            return False
        try:
            source = Gio.SettingsSchemaSource.get_default()
            if source is None:
                return False
            return source.lookup(GNOME_GS_SCHEMA, True) is not None
        except Exception:
            return False

    def _read_active(self, settings):
        # mru-sources[0] is the active layout; it reorders to the front on
        # every switch. Prefer it over the unreliable 'current' index.
        mru_lst = settings.get_value(GNOME_GS_KEY_MRU).unpack()
        if mru_lst:
            type_str, id_str = mru_lst[0]
            return parse_gnome_source(type_str, id_str)

        # Cold-start fallback: nothing has been switched yet this session, so
        # mru-sources can be empty. Fall back to the configured list head.
        sources_lst = settings.get_value(GNOME_GS_KEY_SOURCES).unpack()
        if not sources_lst:
            return None
        type_str, id_str = sources_lst[0]
        return parse_gnome_source(type_str, id_str)

    def get_active_layout(self):
        if not self.available():
            return None
        try:
            settings = Gio.Settings.new(GNOME_GS_SCHEMA)
            return self._read_active(settings)
        except Exception as query_err:
            _warn(f'GNOME layout query failed: {query_err}')
            return None

    def start(self, callback):
        if not self.available():
            _warn('GNOME input-sources schema not available; cannot watch.')
            return False
        if self._thread is not None:
            return True
        self._callback = callback
        self._thread = threading.Thread(
            target=self._run, name='gnome-layout-watch', daemon=True)
        self._thread.start()
        return True

    def _run(self):
        ctx = GLib.MainContext.new()
        ctx.push_thread_default()
        self._loop = GLib.MainLoop.new(ctx, False)
        try:
            self._settings = Gio.Settings.new(GNOME_GS_SCHEMA)
            self._settings.connect(f'changed::{GNOME_GS_KEY_MRU}', self._on_changed)
            self._settings.connect(f'changed::{GNOME_GS_KEY_SOURCES}', self._on_changed)

            try:
                self._emit(self._read_active(self._settings))
            except Exception as prime_err:
                _warn(f'GNOME initial layout read failed: {prime_err}')

            self._loop.run()
        finally:
            self._settings = None
            ctx.pop_thread_default()

    def _on_changed(self, settings, key):
        self._emit(self._read_active(settings))

    def stop(self):
        self._stop_loop_thread()


# ── X11 backend (XKB via libX11/ctypes + python-xlib) ───────────────────

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


# ── Generic Wayland backend (placeholder) ───────────────────────────────

class WaylandGenericBackend(LayoutBackend):
    """Placeholder for a compositor-agnostic Wayland layout reader.

    The intended implementation connects as a minimal Wayland client
    (wl_registry -> wl_seat -> wl_keyboard), reads wl_keyboard.keymap for the
    active keymap, and watches wl_keyboard.modifiers for group (active-layout)
    changes. The known wrinkle is that key/modifiers events follow keyboard
    focus, so a background client may not observe group changes on every
    compositor; some compositors send a fresh keymap on switch, which
    sidesteps it. wlroots compositors also expose layout state through their
    own IPC (Sway's get_inputs, Hyprland's hyprctl devices), which may be a
    more reliable interim source.

    Not yet implemented: available() returns False, so the detector degrades
    to a one-shot query plus the manual setting.
    """

    name = 'wayland-generic'

    def __init__(self, desktop_env=None, session_type=None):
        self._init_watch_state()
        self.desktop_env = desktop_env
        self.session_type = session_type

    def detected_compositor(self):
        if os.environ.get('SWAYSOCK'):
            return 'sway'
        if os.environ.get('HYPRLAND_INSTANCE_SIGNATURE'):
            return 'hyprland'
        return self.desktop_env or 'unknown'

    def available(self):
        return False

    def get_active_layout(self):
        return None

    def start(self, callback):
        _warn(f'Wayland generic backend not implemented '
              f'(detected compositor: {self.detected_compositor()}).')
        return False

    def stop(self):
        pass


# ── Backend selection + top-level detector ──────────────────────────────

def select_backend(desktop_env, session_type):
    """Return the first available backend for the environment, or None.

    Choice keys primarily off the desktop environment, because KDE and GNOME
    expose layout state through focus-independent channels that work on both
    X11 and Wayland. The generic XKB reader is the fallback for any other X11
    desktop, and a generic Wayland reader for other compositors. Backends are
    tried in priority order; the first whose available() is True wins.
    """
    candidates = []
    de = (desktop_env or '').casefold()
    st = (session_type or '').casefold()

    if 'kde' in de or 'plasma' in de:
        candidates.append(KdeBackend())
    elif 'gnome' in de:
        candidates.append(GnomeBackend())

    # Session-type fallbacks, tried after any DE-specific backend: KDE/GNOME on
    # X11 keep their own focus-independent channels, with the generic XKB reader
    # as the catch-all for every other X11 desktop.
    if st == 'x11':
        candidates.append(X11XkbBackend())
    elif st == 'wayland':
        candidates.append(WaylandGenericBackend(desktop_env, session_type))

    for backend in candidates:
        if backend.available():
            return backend
    return None


class KeyboardLayoutDetector:
    """Top-level facade: query the active layout and watch for changes.

    The caller should inject the desktop environment and session type (the
    keymapper already computes them); when omitted they come from Toshy's
    EnvironmentInfo. The change callback fires on the backend's watcher thread.
    """

    def __init__(self, desktop_env=None, session_type=None):
        # Injected values (passed by the keymapper, which already computed
        # them) are preferred. Otherwise defer to Toshy's canonical detector
        # rather than re-deriving the environment here.
        if desktop_env is None or session_type is None:
            env_info_dct = EnvironmentInfo().get_env_info()
            if session_type is None:
                session_type = env_info_dct.get('SESSION_TYPE')
            if desktop_env is None:
                desktop_env = env_info_dct.get('DESKTOP_ENV')
        self.session_type = session_type
        self.desktop_env = desktop_env
        self._backend = select_backend(self.desktop_env, self.session_type)

    @property
    def backend_name(self):
        return self._backend.name if self._backend else 'none'

    def available(self):
        return self._backend is not None and self._backend.available()

    def get_active_layout(self):
        if not self._backend:
            return None
        return self._backend.get_active_layout()

    def start(self, callback):
        if not self._backend:
            _warn('No layout-detection backend available for this environment.')
            return False
        return self._backend.start(callback)

    def stop(self):
        if self._backend:
            self._backend.stop()


# ── Standalone test harness ─────────────────────────────────────────────

def main():
    detector = KeyboardLayoutDetector()

    print(f'Session type:    {detector.session_type}')
    print(f'Desktop env:     {detector.desktop_env}')
    print(f'Backend:         {detector.backend_name}')
    print(f'Available:       {detector.available()}')

    active = detector.get_active_layout()
    if active is None:
        print('Active layout:   (could not determine)')
    else:
        print(f'Active layout:   {format_layout(active)}  '
              f'[layout={active.layout} variant={active.variant}]')

    if not detector.available():
        print('\nNo live watcher available in this environment. Exiting.')
        return

    print('\nWatching for layout changes (Ctrl-C to stop)...\n')

    def on_change(spec):
        print(f'  Layout changed -> {format_layout(spec)}  '
              f'[layout={spec.layout} variant={spec.variant}]')

    stop_event = threading.Event()

    def handle_signal(signum, frame):
        stop_event.set()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    detector.start(on_change)
    try:
        stop_event.wait()
    finally:
        detector.stop()
        print('\nStopped.')


if __name__ == '__main__':
    main()

# End of file #
