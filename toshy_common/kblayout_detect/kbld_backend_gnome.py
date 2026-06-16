# toshy_common/kblayout_detect/kbld_backend_gnome.py
"""GNOME (GSettings) keyboard-layout backend.

Reads the active source from org.gnome.desktop.input-sources and resolves it
via parse_gnome_source. Split out verbatim from the former single-module
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


GNOME_GS_SCHEMA     = 'org.gnome.desktop.input-sources'
GNOME_GS_KEY_MRU    = 'mru-sources'
GNOME_GS_KEY_SOURCES = 'sources'


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
    priority = 100

    @classmethod
    def claims(cls, desktop_env, session_type, compositor):
        return 'gnome' in desktop_env

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


# End of file #
