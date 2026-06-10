# toshy_common/kblayout_detect/base.py
"""Shared base for keyboard-layout detection backends.

Every concrete backend subclasses LayoutBackend and lives in its own module
under this package; backends never import each other. The registry selects a
backend by asking each one's claims() whether it applies to the current
environment, then ordering the claimants by priority and probing available().

This module is the leaf of the package import graph: backends import from here,
and nothing here imports a backend.
"""

__version__ = '20260608'

import os
import sys


def _warn(message):
    """Emit a non-fatal warning.

    Placeholder for standalone use; on integration this should be swapped
    for Toshy's existing debug/error logger.
    """
    print(f'(kblayout_detect) WARNING: {message}', file=sys.stderr)


def detected_compositor(desktop_env=None):
    """Best-effort name of the running Wayland compositor.

    Used by the registry to route to compositor-specific backends, and by the
    generic Wayland backend for its own identity. Falls back to the desktop
    environment string (or 'unknown') when no known compositor is detected.
    """
    if os.environ.get('SWAYSOCK'):
        return 'sway'
    if os.environ.get('HYPRLAND_INSTANCE_SIGNATURE'):
        return 'hyprland'
    return desktop_env or 'unknown'


class LayoutBackend:
    """Common interface, self-description, and shared watch-state for backends.

    Self-description (consumed by the registry):
      - priority: higher is tried first; ties resolve in registry order.
      - claims(): cheap predicate deciding whether this backend is even a
        candidate for the environment. The expensive probe stays in
        available(), which the registry calls only on claimants.
    """

    name = 'base'
    priority = 0

    @classmethod
    def claims(cls, desktop_env, session_type, compositor):
        """True if this backend is a candidate for the given environment.

        Cheap string checks only (no D-Bus calls, no X/Wayland connections);
        the registry probes available() afterward, in priority order.
        """
        return False

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
        """Begin watching. callback(spec, keymap_string) fires on the watcher
        thread; keymap_string is None except on the generic Wayland path."""
        return False

    def stop(self):
        pass

    def _emit(self, spec, keymap_string=None):
        """Deliver a change to the consumer on the watcher thread.

        Backends that resolve a layout to canonical (layout, variant) codes pass
        a spec and dedup on it. The generic Wayland backend cannot recover those
        codes, so it passes the compiled keymap text as keymap_string and dedup
        keys on that text instead (its spec is only a display placeholder).
        """
        if spec is None and keymap_string is None:
            return
        if keymap_string is not None:
            key = keymap_string
        else:
            key = (spec.layout, spec.variant)
        if key == self._last:
            return
        self._last = key
        if self._callback:
            try:
                self._callback(spec, keymap_string)
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


# End of file #
