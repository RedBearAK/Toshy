# toshy_common/kblayout_detect/kbld_backend_wl_generic.py
"""Generic Wayland (surfaceless pywayland) keyboard-layout backend.

Last-resort reader: a surfaceless client that watches wl_keyboard.keymap and
hands the compiled keymap text to the analyzer. Split from the former single
module; the only changes are the hoisted detected_compositor (now imported
from kbld_backend_base) and its single call site.

Backends never import each other - only kbld_backend_base and the shared
kblayout_common types."""

__version__ = '20260608'

import os
import mmap
import select
import threading


# Guarded pywayland import for the generic Wayland backend. Absent on X11-only
# systems and on Wayland sessions without it installed; the backend's
# available() then returns False and the detector falls through. 'Display' is
# aliased to avoid any confusion with an X11 display.
try:
    from pywayland.client import Display as WaylandDisplay
    from pywayland.protocol.wayland import WlSeat
    _HAVE_PYWAYLAND = True
except ImportError:
    _HAVE_PYWAYLAND = False


from toshy_common.kblayout_common import make_layout_spec
from toshy_common.kblayout_detect.kbld_backend_base import (
    LayoutBackend,
    _warn,
    detected_compositor,
)


class WaylandGenericBackend(LayoutBackend):
    """Compositor-agnostic Wayland layout reader via wl_keyboard.

    Connects as a minimal, surfaceless Wayland client — wl_registry -> wl_seat
    -> wl_keyboard, with no surface ever created — and reads the active layout
    from wl_keyboard.keymap. The compositor sends that keymap once when the
    keyboard is bound, so the startup layout is readable on any Wayland session,
    and re-sends a freshly compiled keymap on each layout switch.

    Because the client never owns a surface it can never hold focus, so any
    keymap re-send it receives is focus-independent by construction. Whether a
    compositor re-sends to unfocused clients is its own choice, not a protocol
    guarantee: confirmed on cosmic-comp (a switch rotates the active layout to
    group 0 and re-sends), where this backend live-tracks every switch. On a
    compositor that only re-sends to the focused client, this backend still
    reads the correct startup layout but then sits on it silently after a switch
    it was never told about — so it is a genuine last resort. Where a wlroots
    compositor exposes layout state through its own IPC (Sway's get_inputs,
    Hyprland's hyprctl devices), that focus-independent channel is preferable
    and would warrant its own backend.

    The identity here is the compiled keymap, not (layout, variant) codes, so it
    is emitted as keymap_string for the coordinator's load_from_string path; the
    LayoutSpec it emits alongside is only a display placeholder.
    """

    name = 'wayland-generic'
    priority = 40

    @classmethod
    def claims(cls, desktop_env, session_type, compositor):
        return session_type == 'wayland'

    def __init__(self, desktop_env=None, session_type=None):
        self._init_watch_state()
        self.desktop_env = desktop_env
        self.session_type = session_type
        self._stop_event = threading.Event()
        self._display = None
        self._seat = None
        self._keyboard = None

    def available(self):
        if not _HAVE_PYWAYLAND:
            return False
        return bool(os.environ.get('WAYLAND_DISPLAY'))

    def get_active_layout(self):
        # No usable one-shot here: the active layout's identity is the compiled
        # keymap, which arrives on the watcher thread right after bind. The
        # coordinator primes from that first _emit rather than from this query.
        return None

    def start(self, callback):
        if not self.available():
            _warn('Wayland generic backend unavailable '
                  '(no pywayland or no WAYLAND_DISPLAY).')
            return False
        self._callback = callback
        self._last = None
        self._seat = None
        self._keyboard = None
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run, name='kblayout-wayland', daemon=True)
        self._thread.start()
        return True

    def stop(self):
        self._stop_event.set()
        thread = self._thread
        if thread is not None:
            thread.join(timeout=2.0)
        self._thread = None

    def _run(self):
        """Watcher-thread body: connect, bind keyboard, dispatch keymap events.

        Owns the Wayland connection start to finish (created and torn down on
        this thread). stop() only sets the event; the select timeout bounds how
        long teardown takes.
        """
        try:
            display = WaylandDisplay()
            display.connect()
        except Exception as connect_err:
            _warn(f'Wayland generic backend could not connect: {connect_err}')
            return

        self._display = display
        try:
            registry = display.get_registry()
            registry.dispatcher['global'] = self._on_global
            display.roundtrip()     # globals -> bind seat + get_keyboard
            display.roundtrip()     # initial keymap -> first _emit (the prime)

            if self._keyboard is None:
                _warn('Wayland generic backend found no seat keyboard; '
                      'no layout watcher started.')
                return

            fd = display.get_fd()
            while not self._stop_event.is_set():
                display.flush()
                rlist, _, _ = select.select([fd], [], [], 0.5)
                if rlist:
                    display.dispatch(block=True)
        except Exception as loop_err:
            _warn(f'Wayland generic backend watch loop error: {loop_err}')
        finally:
            try:
                display.disconnect()
            except Exception:
                pass
            self._display = None

    def _on_global(self, registry, id_num, iface_name, version):
        if iface_name != 'wl_seat':
            return
        if self._keyboard is not None:
            return
        seat = registry.bind(id_num, WlSeat, version)
        keyboard = seat.get_keyboard()
        keyboard.dispatcher['keymap'] = self._on_keymap
        self._seat = seat
        self._keyboard = keyboard

    def _on_keymap(self, keyboard, keymap_format, fd, size):
        try:
            keymap_text = self._read_keymap_fd(fd, size)
        finally:
            os.close(fd)
        if not keymap_text:
            return
        # Placeholder spec for display only; the coordinator fills in the
        # description from the compiled keymap's group-0 name.
        spec = make_layout_spec(
            layout=detected_compositor(self.desktop_env),
            raw_variant=None,
            description=None,
        )
        self._emit(spec, keymap_string=keymap_text)

    def _read_keymap_fd(self, fd, size):
        """Read a wl_keyboard.keymap fd into the keymap text.

        The fd is a read-only mapping; the payload is NUL-terminated and size
        includes the terminator, so the text is everything up to the first NUL.
        """
        try:
            buf = mmap.mmap(fd, size, mmap.MAP_PRIVATE, mmap.PROT_READ)
        except (OSError, ValueError) as map_err:
            _warn(f'Wayland generic backend could not map keymap fd: {map_err}')
            return None
        try:
            raw = buf.read(size)
        finally:
            buf.close()
        return raw.split(b'\x00', 1)[0].decode('utf-8', 'replace')


# End of file #
