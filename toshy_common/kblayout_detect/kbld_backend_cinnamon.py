# toshy_common/kblayout_detect/kbld_backend_cinnamon.py
"""Cinnamon (D-Bus) keyboard-layout backend.

Resolves the active layout over the org.Cinnamon session-bus interface,
building specs inline. Split out verbatim from the former single-module
kblayout_detect; behavior is unchanged.

Backends never import each other - only kbld_backend_base and the shared
kblayout_common types."""

__version__ = '20260608'

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


CINNAMON_DBUS_SERVICE    = 'org.Cinnamon'
CINNAMON_DBUS_PATH       = '/org/Cinnamon'
CINNAMON_DBUS_INTERFACE  = 'org.Cinnamon'
CINNAMON_DBUS_TIMEOUT_MS = 2000


class CinnamonBackend(LayoutBackend):
    """Cinnamon layout detection via org.Cinnamon (Muffin Wayland and X11).

    Cinnamon does not persist the active layout to dconf; the live state lives
    in the cinnamon process and is published on the session bus. Two members
    matter: GetInputSources() returns the configured sources, each a struct
    that carries the xkb layout and variant as separate fields plus a
    human description and the joined id; and CurrentInputSourceChanged(s)
    fires on every switch with that joined id ('us', 'us+mac', 'fr+azerty').

    Because the signal payload is the id (identity), not a list index, a
    mid-session reorder cannot misidentify the active layout -- unlike the
    index-based KDE and X11 backends, which must re-read the list each event.
    InputSourcesChanged() only refreshes the id -> LayoutSpec map so added,
    removed, or renamed sources stay current; the active layout itself always
    arrives via CurrentInputSourceChanged.

    available() probes GetInputSources, so older Cinnamon without this API
    (pre-unified-keyboard) simply declines and the selector falls through to
    the X11 or generic Wayland backend. Verified against Cinnamon 6.6.7
    (LMDE 7) on Wayland via gdbus monitor and a GetInputSources call.
    """

    name = 'cinnamon-dbus'
    priority = 100

    @classmethod
    def claims(cls, desktop_env, session_type, compositor):
        return 'cinnamon' in desktop_env

    # GetInputSources() returns a(ssisssssssib); per-source field layout:
    #   [0] type ('xkb'/'ibus')   [1] id ('us+mac')       [2] activation index
    #   [3] description           [4] indicator label      [5] bare layout/lang
    #   [6] id (again)            [7] xkb layout           [8] xkb variant
    #   [9] (unused here)         [10] dupe number (→ ₁ ₂)  [11] active flag
    # Only the six below enter the logic; the rest are intentionally ignored.
    _SRC_TYPE    = 0
    _SRC_ID      = 1
    _SRC_DESC    = 3
    _SRC_LAYOUT  = 7
    _SRC_VARIANT = 8
    _SRC_ACTIVE  = 11

    def __init__(self):
        self._init_watch_state()
        self._by_id = {}        # id str -> LayoutSpec (xkb sources only)
        self._sub_ids = []

    def available(self):
        if not _HAVE_GI:
            return False
        try:
            self._call_get_input_sources()      # liveness probe; no loop needed
            return True
        except Exception:
            return False

    # ── synchronous D-Bus helpers (no running loop required) ──

    def _bus(self):
        return Gio.bus_get_sync(Gio.BusType.SESSION, None)

    def _call_get_input_sources(self):
        reply = self._bus().call_sync(
            CINNAMON_DBUS_SERVICE, CINNAMON_DBUS_PATH, CINNAMON_DBUS_INTERFACE,
            'GetInputSources', None, GLib.VariantType.new('(a(ssisssssssib))'),
            Gio.DBusCallFlags.NONE, CINNAMON_DBUS_TIMEOUT_MS, None,
        )
        return reply.unpack()[0]

    def _spec_from_source(self, source):
        """Build a LayoutSpec from one GetInputSources struct, or None if not xkb."""
        if source[self._SRC_TYPE] != 'xkb':
            return None        # ibus / non-xkb source: not a plain XKB layout
        description = source[self._SRC_DESC] or None
        return make_layout_spec(
            source[self._SRC_LAYOUT], source[self._SRC_VARIANT], description)

    def _build_map(self):
        """Refresh id -> LayoutSpec from GetInputSources; return the active spec."""
        sources = self._call_get_input_sources()
        by_id = {}
        active_spec = None
        for source in sources:
            spec = self._spec_from_source(source)
            if spec is None:
                continue
            by_id[source[self._SRC_ID]] = spec
            if source[self._SRC_ACTIVE]:
                active_spec = spec
        self._by_id = by_id
        return active_spec

    def _resolve_id(self, id_str):
        """Map a CurrentInputSourceChanged id to a LayoutSpec.

        The cached map is the fast path. A miss (an id added since the last
        refresh) triggers one rebuild; if it still misses, the layout/variant
        are derived straight from the id so an xkb source is never dropped,
        only its description is unavailable.
        """
        spec = self._by_id.get(id_str)
        if spec is not None:
            return spec
        try:
            self._build_map()
        except Exception as refresh_err:
            _warn(f'Cinnamon source refresh failed: {refresh_err}')
        spec = self._by_id.get(id_str)
        if spec is not None:
            return spec

        # Last resort: the id is itself 'layout' or 'layout+variant'.
        layout, _, variant = id_str.partition('+')
        layout = layout.strip()
        variant = variant.strip() or None
        if not layout:
            _warn(f'Cinnamon sent an unrecognized input-source id: {id_str!r}')
            return None
        return make_layout_spec(layout, variant, None)

    def get_active_layout(self):
        if not _HAVE_GI:
            return None
        try:
            return self._build_map()
        except Exception as query_err:
            _warn(f'Cinnamon layout query failed: {query_err}')
            return None

    # ── watch (GLib loop in a daemon thread) ──

    def start(self, callback):
        if not _HAVE_GI:
            _warn('PyGObject (gi) not available; cannot watch Cinnamon layout changes.')
            return False
        if self._thread is not None:
            return True
        self._callback = callback
        self._thread = threading.Thread(
            target=self._run, name='cinnamon-layout-watch', daemon=True)
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
                    CINNAMON_DBUS_SERVICE, CINNAMON_DBUS_INTERFACE,
                    'CurrentInputSourceChanged', CINNAMON_DBUS_PATH, None,
                    Gio.DBusSignalFlags.NONE, self._on_source_changed),
                conn.signal_subscribe(
                    CINNAMON_DBUS_SERVICE, CINNAMON_DBUS_INTERFACE,
                    'InputSourcesChanged', CINNAMON_DBUS_PATH, None,
                    Gio.DBusSignalFlags.NONE, self._on_sources_changed),
            ]

            # Prime with current state so the consumer learns the start layout.
            try:
                self._emit(self._build_map())
            except Exception as prime_err:
                _warn(f'Cinnamon initial layout read failed: {prime_err}')

            self._loop.run()

            for sub_id in self._sub_ids:
                conn.signal_unsubscribe(sub_id)
            self._sub_ids = []
        finally:
            ctx.pop_thread_default()

    def _on_source_changed(self, conn, sender, path, iface, signal_name, params):
        id_str = params.unpack()[0]
        self._emit(self._resolve_id(id_str))

    def _on_sources_changed(self, conn, sender, path, iface, signal_name, params):
        # The configured set changed (add/remove/reorder/rename). Refresh the
        # id -> LayoutSpec map so later ids resolve with current descriptions.
        # No emit: the active layout is reported by CurrentInputSourceChanged,
        # and a description-only change would be suppressed by dedup anyway.
        try:
            self._build_map()
        except Exception as rebuild_err:
            _warn(f'Cinnamon source-list rebuild failed: {rebuild_err}')

    def stop(self):
        self._stop_loop_thread()


# End of file #
