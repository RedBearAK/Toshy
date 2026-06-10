# toshy_common/kblayout_detect/kbld_registry.py
"""Backend registry, environment-based selection, and the public facade.

REGISTRY lists every backend class; select_backend filters by each backend's
claims(), orders by priority, and returns the first available one. Adding a
backend means writing its module and appending the class here - nothing else
in the package changes.
"""

__version__ = '20260608'

from toshy_common.env_context import EnvironmentInfo
from toshy_common.kblayout_detect.kbld_backend_base import (
    detected_compositor,
    _warn,
)
from toshy_common.kblayout_detect.kbld_backend_kde import KdeBackend
from toshy_common.kblayout_detect.kbld_backend_x11 import X11XkbBackend
from toshy_common.kblayout_detect.kbld_backend_gnome import GnomeBackend
from toshy_common.kblayout_detect.kbld_backend_cosmic import CosmicBackend
from toshy_common.kblayout_detect.kbld_backend_cinnamon import CinnamonBackend
from toshy_common.kblayout_detect.kbld_backend_wl_generic import WaylandGenericBackend


# Backend classes in rough environment order; selection is by claims()/priority,
# so list position only breaks ties between equal-priority claimants (which the
# mutually-exclusive desktop matches never produce in practice).
REGISTRY = [
    KdeBackend,
    GnomeBackend,
    CinnamonBackend,
    CosmicBackend,
    X11XkbBackend,
    WaylandGenericBackend,
]


def select_backend(desktop_env, session_type):
    """Return the first available backend for the environment, or None.

    Each backend self-describes via claims() (a cheap predicate) and priority.
    Candidates are those whose claims() is true for the environment; they are
    tried high priority first, and the first whose available() succeeds wins.
    Only claimants are constructed and probed, so irrelevant backends never
    open a D-Bus, X, or Wayland connection.
    """
    de = (desktop_env or '').casefold()
    st = (session_type or '').casefold()
    compositor = detected_compositor(desktop_env)

    candidates = [cls for cls in REGISTRY if cls.claims(de, st, compositor)]
    candidates.sort(key=lambda cls: cls.priority, reverse=True)

    for cls in candidates:
        backend = cls()
        # Hand the environment to the instance; only the generic Wayland reader
        # consumes it (for its compositor label), the rest ignore it.
        backend.desktop_env = desktop_env
        backend.session_type = session_type
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


# End of file #
