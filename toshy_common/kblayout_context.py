#!/usr/bin/env python3
"""
Keyboard-layout context coordinator for Toshy.

    toshy_common/kblayout_context.py

The thin runtime layer that ties the three building blocks together: it watches
the active layout (kblayout_detect), analyzes each new layout against a
reference (kblayout_analyze), and hands the resulting keycode->keycode
correction map to the keymapper. This is the module the config/runtime wires
up. The detector and analyzer never know about each other; this coordinator is
the only thing that knows both, and it stays deliberately small.

The keymapper hand-off is an injected callback (apply_correction_map) rather
than a direct keymapper call, so this module does not depend on the keymapper's
correction-map setter and can be built and tested before that setter exists.
The callback runs on the detector's watcher thread — the same threading
contract kblayout_detect documents — so a consumer that needs the main thread
marshals there itself.
"""

__version__ = '20260605'

import os
import sys
import signal
import threading


_toshy_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _toshy_root not in sys.path:
    sys.path.insert(0, _toshy_root)

from toshy_common.kblayout_common import format_layout
from toshy_common.kblayout_detect import KeyboardLayoutDetector
from toshy_common.kblayout_analyze import KeyboardLayoutAnalyzer


def _warn(message):
    """Emit a warning to stderr (kept simple and dependency-free)."""
    print(f'(WW) kblayout_context: {message}', file=sys.stderr)


class KeyboardLayoutContext:
    """Maintains the active layout's correction map and keeps it in sync.

    Lifecycle:
        ctx = KeyboardLayoutContext(
            apply_correction_map=lambda spec, m: keymapper.set_correction_map(m))
        ctx.start()     # primes from the active layout, then watches for changes
        ...
        ctx.stop()

    On start() and on every subsequent layout change, the active LayoutSpec is
    loaded into the analyzer, compared against the reference layout, reduced to a
    keycode->keycode correction map, and passed — together with the spec — to
    apply_correction_map(spec, correction_map). The spec is there for observers
    (logging, a UI indicator); a keymapper consumer ignores it and applies only
    the map, so layout vocabulary never reaches the keymapper. The map is empty
    for US-like layouts (no correction needed), so applying it is always safe,
    and an unchanged layout is skipped so nothing is rebuilt needlessly.
    """

    def __init__(self, apply_correction_map, desktop_env=None,
                    session_type=None, reference_layout='us'):
        self._apply_correction_map = apply_correction_map
        self._reference_layout = reference_layout
        self._detector = KeyboardLayoutDetector(desktop_env, session_type)
        self._analyzer = KeyboardLayoutAnalyzer()
        self._current_spec = None
        self._current_keymap = None
        self._current_map = {}

    @property
    def current_layout(self):
        """The active LayoutSpec, or None before the first resolution."""
        return self._current_spec

    @property
    def current_correction_map(self):
        """The correction map currently handed to the keymapper."""
        return self._current_map

    @property
    def backend_name(self):
        """Name of the detection backend in use (for diagnostics)."""
        return self._detector.backend_name

    def start(self) -> bool:
        """Prime from the active layout, then watch for changes.

        Returns whether a live watcher started; False means no detection backend
        was available for this environment (nothing to coordinate).
        """
        # The reference (plain US) does not change, so compile it once; the
        # analyzer keeps it across reloads of the active keymap.
        if not self._analyzer.set_reference_from_names(layout=self._reference_layout):
            _warn(f'could not compile reference layout {self._reference_layout!r}; '
                    f'correction maps will be empty.')

        active = self._detector.get_active_layout()
        if active is not None:
            self._apply_for_spec(active)

        return self._detector.start(self._on_layout_change)

    def stop(self):
        """Stop watching for layout changes."""
        self._detector.stop()

    def _on_layout_change(self, spec, keymap_string=None):
        """Detector callback; runs on the watcher thread."""
        self._apply_for_spec(spec, keymap_string)

    def _apply_for_spec(self, spec, keymap_string=None):
        """Analyze one layout and hand its correction map to the keymapper.

        Two identity models share this path. Spec-based backends supply
        canonical (layout, variant) codes, are deduped on the spec, and are
        analyzed via load_from_spec. The generic Wayland backend supplies the
        compiled keymap text as keymap_string with only a placeholder spec; it
        is deduped on the keymap text and analyzed via load_from_string, and its
        display spec gets the compiled keymap's group-0 name filled in after.
        """
        if keymap_string is None:
            if spec == self._current_spec:
                return                      # same layout; nothing to rebuild
            ok = self._analyzer.load_from_spec(spec)
        else:
            if keymap_string == self._current_keymap:
                return                      # same keymap; nothing to rebuild
            ok = self._analyzer.load_from_string(keymap_string)

        if not ok:
            _warn(f'could not analyze layout {format_layout(spec)}; '
                    f'keeping the previous correction map.')
            return

        correction_map = self._analyzer.build_correction_map()

        if keymap_string is not None:
            # The backend could only supply a placeholder spec, so name it from
            # the compiled keymap for any observer (logging, a UI indicator).
            spec = spec._replace(description=self._analyzer.layout_name)
            self._current_keymap = keymap_string

        self._current_spec = spec
        self._current_map = correction_map

        # A consumer exception must not kill the detector's watcher thread.
        try:
            self._apply_correction_map(spec, correction_map)
        except Exception as apply_err:
            _warn(f'apply_correction_map raised for {format_layout(spec)}: {apply_err}')


def main():
    """Standalone harness: announce each layout and print its correction map."""
    def show(spec, correction_map):
        count = len(correction_map)
        plural = 'entry' if count == 1 else 'entries'
        print(f'\nLayout -> {format_layout(spec)}  '
                f'[layout={spec.layout} variant={spec.variant}]')
        print(f'    correction map: {count} {plural}  {correction_map}')

    context = KeyboardLayoutContext(apply_correction_map=show)

    print(f'Backend: {context.backend_name}')
    print('Starting layout coordinator (Ctrl-C to stop)...')

    stop_event = threading.Event()

    def handle_signal(signum, frame):
        stop_event.set()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    # start() primes from the active layout, so show() announces it (layout then
    # map) before the watcher takes over; every later switch prints the same way.
    if not context.start():
        print('No detection backend available; nothing to coordinate.')
        return

    print('\nWatching for layout changes...')

    try:
        stop_event.wait()
    finally:
        context.stop()
        print('\nStopped.')


if __name__ == '__main__':
    main()


# End of file #
