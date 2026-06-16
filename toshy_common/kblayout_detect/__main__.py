# toshy_common/kblayout_detect/__main__.py
"""Standalone harness: python -m toshy_common.kblayout_detect

Prints the selected backend and active layout, then watches for changes until
interrupted. Unchanged from the former single-module form.
"""

__version__ = '20260608'

import signal
import threading

from toshy_common.kblayout_common import format_layout
from toshy_common.kblayout_detect.kbld_registry import KeyboardLayoutDetector


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

    def on_change(spec, keymap_string=None):
        via = ' (keymap)' if keymap_string is not None else ''
        print(f'  Layout changed -> {format_layout(spec)}{via}  '
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
