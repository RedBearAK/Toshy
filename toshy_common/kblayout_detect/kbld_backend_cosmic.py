# toshy_common/kblayout_detect/kbld_backend_cosmic.py
"""COSMIC (D-Bus / RON) keyboard-layout backend.

Reads the xkb_config from the COSMIC settings daemon (or its RON file) and
resolves it via parse_cosmic_xkb_config. Split out verbatim from the former
single-module kblayout_detect; behavior is unchanged.

Backends never import each other - only kbld_backend_base and the shared
kblayout_common types."""

__version__ = '20260608'

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


COSMIC_CONFIG_INTERFACE = 'com.system76.CosmicSettingsDaemon.Config'
COSMIC_XKB_OBJECT_PATH  = '/com/system76/CosmicSettingsDaemon/Config/com/system76/CosmicComp/V1'
COSMIC_XKB_CONFIG_KEY   = 'xkb_config'
COSMIC_XKB_CONFIG_PATH  = '~/.config/cosmic/com.system76.CosmicComp/v1/xkb_config'
COSMIC_DBUS_SERVICE     = 'com.system76.CosmicSettingsDaemon'
COSMIC_DBUS_PATH        = '/com/system76/CosmicSettingsDaemon'
COSMIC_DBUS_TIMEOUT_MS  = 2000
COSMIC_CONFIG_ID        = 'com.system76.CosmicComp'
COSMIC_CONFIG_VERSION   = 1


def _ron_string_field(text, key):
    """Return the quoted string value for `key:` in a RON struct, or None.

    Scans for `key:` then the next pair of double quotes. Adequate for COSMIC's
    flat xkb_config (layout/variant values never contain quotes); deliberately
    not a general RON parser, and indifferent to pretty vs compact formatting.
    """
    key_pos = text.find(key + ':')
    if key_pos == -1:
        return None
    quote_start = text.find('"', key_pos + len(key) + 1)
    if quote_start == -1:
        return None
    quote_end = text.find('"', quote_start + 1)
    if quote_end == -1:
        return None
    return text[quote_start + 1:quote_end]


def parse_cosmic_xkb_config(text):
    """Convert a COSMIC xkb_config (RON) into the active LayoutSpec, or None.

    COSMIC stores the configured layouts as parallel comma-separated lists and
    rewrites the file on every switch with the active layout rotated to the
    front, so element 0 of (layout, variant) is the active one. Empty variant
    slots are preserved positionally, e.g. variant ',mac,azerty' means the
    first layout carries no variant.
    """
    layout_csv = _ron_string_field(text, 'layout')
    if layout_csv is None:
        return None
    variant_csv = _ron_string_field(text, 'variant')

    layout_lst = layout_csv.split(',')
    variant_lst = variant_csv.split(',') if variant_csv is not None else []

    layout = layout_lst[0].strip() if layout_lst else ''
    if not layout:
        return None
    variant = variant_lst[0].strip() if variant_lst else ''
    return make_layout_spec(layout, variant, None)


class CosmicBackend(LayoutBackend):
    """COSMIC layout detection via cosmic-settings-daemon's config D-Bus.

    COSMIC does not expose the active layout on the bus directly; instead the
    compositor persists keyboard config to cosmic-config and, on every switch,
    atomically rewrites ~/.config/cosmic/.../xkb_config with the configured
    layouts rotated so the active one is element 0 of the parallel layout and
    variant lists. cosmic-settings-daemon broadcasts a Changed(config_id, key)
    signal on com.system76.CosmicSettingsDaemon.Config when that happens; it is
    a session-bus broadcast, so an unfocused observer hears it.

    So the watch is signal-driven (Changed where key == 'xkb_config') and the
    state read is a parse of the file's element 0. The backend self-registers
    via the daemon's WatchConfig so emission does not depend on another
    component watching the same config; it falls back to the known object path
    if that call fails. The file is read rather than the inode watched, because
    the atomic rename-into-place swaps the inode on each write and would defeat
    a plain file watch. The config carries no human description, so xkbcommon
    supplies the display name downstream.

    Verified against COSMIC 1.0.14 (cosmic-comp) on Fedora 44: the Changed
    signal fires per switch and the file rotates the active layout to front.
    """

    name = 'cosmic-dbus'
    priority = 100

    @classmethod
    def claims(cls, desktop_env, session_type, compositor):
        return 'cosmic' in desktop_env

    def __init__(self):
        self._init_watch_state()
        self._sub_id = None

    def available(self):
        if not _HAVE_GI:
            return False
        return os.path.isfile(os.path.expanduser(COSMIC_XKB_CONFIG_PATH))

    def _bus(self):
        return Gio.bus_get_sync(Gio.BusType.SESSION, None)

    def _watch_config(self, conn):
        """Register a config watch and return the object path Changed fires on.

        WatchConfig is COSMIC's intended registration call; self-registering
        means the daemon emits for us regardless of whether another component
        (cosmic-comp, the panel applet) is also watching. On any failure, fall
        back to the known path -- an existing watcher still makes the broadcast
        observable, so this never regresses below a passive subscription.
        """
        try:
            reply = conn.call_sync(
                COSMIC_DBUS_SERVICE, COSMIC_DBUS_PATH, COSMIC_DBUS_SERVICE,
                'WatchConfig',
                GLib.Variant('(st)', (COSMIC_CONFIG_ID, COSMIC_CONFIG_VERSION)),
                GLib.VariantType.new('(os)'),
                Gio.DBusCallFlags.NONE, COSMIC_DBUS_TIMEOUT_MS, None,
            )
            return reply.unpack()[0] or COSMIC_XKB_OBJECT_PATH
        except Exception as watch_err:
            _warn(f'COSMIC WatchConfig failed, using known path: {watch_err}')
            return COSMIC_XKB_OBJECT_PATH

    def _read_active(self):
        path = os.path.expanduser(COSMIC_XKB_CONFIG_PATH)
        try:
            with open(path, 'r') as config_file:
                text = config_file.read()
        except OSError as read_err:
            _warn(f'Could not read {path}: {read_err}')
            return None
        return parse_cosmic_xkb_config(text)

    def get_active_layout(self):
        if not _HAVE_GI:
            return None
        return self._read_active()

    # ── watch (GLib loop in a daemon thread) ──

    def start(self, callback):
        if not _HAVE_GI:
            _warn('PyGObject (gi) not available; cannot watch COSMIC layout changes.')
            return False
        if self._thread is not None:
            return True
        self._callback = callback
        self._thread = threading.Thread(
            target=self._run, name='cosmic-layout-watch', daemon=True)
        self._thread.start()
        return True

    def _run(self):
        ctx = GLib.MainContext.new()
        ctx.push_thread_default()
        self._loop = GLib.MainLoop.new(ctx, False)
        try:
            conn = self._bus()
            watch_path = self._watch_config(conn)
            self._sub_id = conn.signal_subscribe(
                None, COSMIC_CONFIG_INTERFACE, 'Changed', watch_path,
                None, Gio.DBusSignalFlags.NONE, self._on_config_changed)

            # Prime with current state so the consumer learns the start layout.
            try:
                self._emit(self._read_active())
            except Exception as prime_err:
                _warn(f'COSMIC initial layout read failed: {prime_err}')

            self._loop.run()

            conn.signal_unsubscribe(self._sub_id)
            self._sub_id = None
        finally:
            ctx.pop_thread_default()

    def _on_config_changed(self, conn, sender, path, iface, signal_name, params):
        # Changed(s config_id, s key). The object path already scopes this to
        # CosmicComp, so filtering on the key is enough; ignore other keys.
        unpacked = params.unpack()
        if len(unpacked) >= 2 and unpacked[1] != COSMIC_XKB_CONFIG_KEY:
            return
        self._emit(self._read_active())

    def stop(self):
        self._stop_loop_thread()


# End of file #
