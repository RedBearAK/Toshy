# toshy_common/kblayout_detect/kbld_backend_kde.py
"""KDE Plasma keyboard-layout backend.

Resolves the active layout via org.kde.KeyboardLayouts (getLayout plus the
layoutChanged signal) and maps the index to (layout, variant) through kxkbrc.
Split out verbatim from the former single-module kblayout_detect; behavior is
unchanged. Backends never import each other - only kbld_backend_base and the
shared kblayout_common types.
"""

__version__ = '20260613'

import os
import threading


# Guarded PyGObject import: the module must still load (for graceful
# degradation) on systems without gi.
try:
    import gi
    gi.require_version('Gio', '2.0')
    gi.require_version('GLib', '2.0')
    from gi.repository import Gio, GLib
    _HAVE_GI = True
except (ImportError, ValueError):
    _HAVE_GI = False


from toshy_common.kblayout_common import make_layout_spec
from toshy_common.kblayout_detect.kbld_backend_base import (
    LayoutBackend,
    _warn,
)


KDE_DBUS_SERVICE    = 'org.kde.keyboard'
KDE_DBUS_PATH       = '/Layouts'
KDE_DBUS_INTERFACE  = 'org.kde.KeyboardLayouts'
KDE_DBUS_TIMEOUT_MS = 2000
KDE_KXKBRC_PATH     = '~/.config/kxkbrc'


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




class KdeBackend(LayoutBackend):
    """KDE Plasma layout detection.

    The live active index comes from org.kde.KeyboardLayouts.getLayout() and
    the layoutChanged(u) signal (focus-independent, since it is a session-bus
    broadcast). The index is resolved to (layout, variant) through kxkbrc's
    parallel LayoutList/VariantList, which carry the precise XKB variant codes
    that the D-Bus longName only describes in prose. getLayoutsList() is used
    as a cross-check (its shortNames must match the leading slice of kxkbrc's
    LayoutList) and as the source of the human-readable label.
    """

    name = 'kde-dbus'
    priority = 100

    @classmethod
    def claims(cls, desktop_env, session_type, compositor):
        return 'kde' in desktop_env or 'plasma' in desktop_env

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

        # Preferred path: kxkbrc supplies precise variant codes. getLayout()
        # indexes the live (loaded) set that getLayoutsList returns, and that
        # set is the leading slice of kxkbrc: KDE loads only the first few
        # layouts as XKB groups (the "main layouts") and leaves any extras as
        # configured-but-unloaded "spares" further down kxkbrc. So kxkbrc is
        # normally *longer* than the D-Bus list, which is expected, not a
        # mismatch. Trust the variants as long as the layout codes line up with
        # the D-Bus order across that leading slice.
        if layout_lst and len(layout_lst) >= len(dbus_list):
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
            _warn('kxkbrc layout codes do not match the D-Bus order; falling '
                  'back to layout-only resolution (variants unavailable).')
        elif layout_lst:
            _warn(f'kxkbrc lists {len(layout_lst)} layouts, fewer than the '
                  f'{len(dbus_list)} reported on D-Bus; falling back to '
                  f'layout-only resolution.')

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


# End of file #
