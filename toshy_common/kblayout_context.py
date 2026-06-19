#!/usr/bin/env python3
"""
Keyboard-layout context coordinator for Toshy.

    toshy_common/kblayout_context.py

The thin runtime layer that ties the three building blocks together: it watches
the active layout (kblayout_detect), analyzes each new layout against a
reference (kblayout_analyze), and hands the resulting keycode->keycode
correction map — and, for Phase 2, a per-layout character->keystroke symbol
table — to the keymapper. This is the module the config/runtime wires up. The
detector and analyzer never know about each other; this coordinator is the only
thing that knows both, and it stays deliberately small.

The keymapper hand-off is an injected callback (apply_correction_map) rather
than a direct keymapper call, so this module does not depend on the keymapper's
correction-map setter and can be built and tested before that setter exists.
The callback runs on the detector's watcher thread — the same threading
contract kblayout_detect documents — so a consumer that needs the main thread
marshals there itself.

Phase 2 adds the symbol table, which the keymapper's string/Unicode output paths
use to type the right keys on a non-US layout instead of US-positional garbage.
It is built against a compose table that is locale-driven (not layout-driven),
so the compose table is compiled once for the session and reused across every
layout switch, while the symbol table itself is rebuilt per switch. A small LRU
cache keyed on (layout identity, locale, ~/.XCompose mtime) skips the rebuild
when returning to a recently seen layout; a locale or compose-file change shifts
that key, so it self-heals on the next switch with no watcher machinery.
"""

__version__ = '20260616'

import os
import sys
import signal
import threading

from collections import OrderedDict

from xkbcommon import xkb


_toshy_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _toshy_root not in sys.path:
    sys.path.insert(0, _toshy_root)

from toshy_common.kblayout_common import format_layout
from toshy_common.kblayout_detect import KeyboardLayoutDetector
from toshy_common.kblayout_analyze import KeyboardLayoutAnalyzer


# Most recent N distinct (layout, compose) identities whose built maps are kept,
# so toggling among a handful of layouts pays the ~24ms build at most once each.
_SYMBOL_TABLE_CACHE_CAP = 8


def _warn(message):
    """Emit a warning to stderr (kept simple and dependency-free)."""
    print(f'(WW) kblayout_context: {message}', file=sys.stderr)


def _error(message):
    """Emit an error to stderr (kept simple and dependency-free)."""
    print(f'(EE) kblayout_context: {message}', file=sys.stderr)


def _locale_name():
    """The locale the compose table loads from: $LC_ALL / $LC_CTYPE / $LANG in
    priority order, falling back to a UTF-8 default. This is the locale AUTHORITY
    point — change what this returns to override the compose locale."""
    for var in ('LC_ALL', 'LC_CTYPE', 'LANG'):
        value = os.environ.get(var)
        if value:
            return value
    return 'en_US.UTF-8'


def _xcompose_mtime():
    """mtime of the compose file the locale chain would actually read, or None
    when there is none. Honors $XCOMPOSEFILE, else ~/.XCompose. Part of the cache
    key so a compose-file edit invalidates cached tables. mtime, not a content
    hash: cheap, and good enough nearly all the time — a missed edit merely takes
    effect on the next switch instead of immediately, never produces wrong
    output."""
    path = os.environ.get('XCOMPOSEFILE')
    if not path:
        home = os.environ.get('HOME')
        if not home:
            return None
        path = os.path.join(home, '.XCompose')
    try:
        return os.stat(path).st_mtime
    except OSError:
        return None


class KeyboardLayoutContext:
    """Maintains the active layout's correction map and symbol table, and keeps
    them in sync.

    Lifecycle:
        kbl_ctx = KeyboardLayoutContext(
            apply_correction_map=lambda spec, correction_map, symbol_hints, symbol_table:
                keymapper.set_correction_map(
                    correction_map,
                    symbol_hints=symbol_hints,
                    symbol_table=symbol_table))
        kbl_ctx.start()     # primes from the active layout, then watches for changes
        ...
        kbl_ctx.stop()

    On start() and on every subsequent layout change, the active LayoutSpec is
    loaded into the analyzer, compared against the reference layout, reduced to a
    keycode->keycode correction map, and passed — with the spec, a keycode->symbol
    hint map for log readability, and the per-layout symbol table — to
    apply_correction_map(spec, correction_map, symbol_hints, symbol_table). The
    spec is there for observers (logging, a UI indicator); a keymapper consumer
    applies the maps and uses the hints only as opaque display labels in its
    logs, so no layout vocabulary ever drives keymapper logic. The correction map
    is empty for US-like layouts (no correction needed), so applying it is always
    safe, and an unchanged layout is skipped so nothing is rebuilt needlessly.
    """

    def __init__(self, apply_correction_map, desktop_env=None,
                    session_type=None, reference_layout='us',
                    number_row='positional'):
        self._apply_correction_map = apply_correction_map
        self._reference_layout = reference_layout
        self._number_row = number_row
        self._detector = KeyboardLayoutDetector(desktop_env, session_type)
        self._analyzer = KeyboardLayoutAnalyzer()
        self._current_spec = None
        self._current_keymap = None
        self._current_map = {}
        # Phase 2: the compose table (built once in start(), locale-driven) and a
        # small LRU cache of (correction_map, symbol_hints, symbol_table) keyed on
        # layout-plus-compose identity, so returning to a recent layout skips the
        # rebuild.
        self._compose_table = None
        self._symbol_cache = OrderedDict()

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

        # The compose table is locale-driven, not layout-driven, so like the
        # reference it is built once and reused across every layout switch.
        self._build_compose_table_once()

        active = self._detector.get_active_layout()
        if active is not None:
            self._apply_for_spec(active)

        return self._detector.start(self._on_layout_change)

    def stop(self):
        """Stop watching for layout changes."""
        self._detector.stop()

    def _build_compose_table_once(self):
        """Build the locale's compose table once for the session.

        Loud on failure: a missing compose table silently strips every dead-key
        character from string output, so the failure is logged as an error. Then
        proceed with None — the analyzer degrades to a direct-only symbol table,
        which is the correct behaviour when nothing can compose.
        """
        locale_name = _locale_name()
        try:
            self._compose_table = self._analyzer.context.compose_table_new_from_locale(
                locale_name)
        except Exception as compose_err:        # noqa: BLE001 - any failure means absent
            _error(f'could not build compose table for locale {locale_name!r}: '
                    f'{compose_err}. Dead-key characters will be unavailable in '
                    f'string output; direct characters are unaffected.')
            self._compose_table = None

    def _on_layout_change(self, spec, keymap_string=None):
        """Detector callback; runs on the watcher thread."""
        self._apply_for_spec(spec, keymap_string)

    def _apply_for_spec(self, spec, keymap_string=None):
        """Analyze one layout and hand its correction map, symbol hints, and
        symbol table to the keymapper.

        Two identity models share this path. Spec-based backends supply
        canonical (layout, variant) codes, are deduped on the spec, and are
        analyzed via load_from_spec. The generic Wayland backend supplies the
        compiled keymap text as keymap_string with only a placeholder spec; it
        is deduped on the keymap text and analyzed via load_from_string, and its
        display spec gets the compiled keymap's group-0 name filled in after.

        The symbol table (Phase 2) is built against the session compose table and
        cached on (layout identity, locale, ~/.XCompose mtime). The layout
        identity is the SAME identity used for dedup just above — the spec, or the
        keymap string — plus the compose dimension the correction map does not
        have, so a locale or compose-file change self-heals via a cache miss.
        """
        if keymap_string is None:
            if spec == self._current_spec:
                return                      # same layout; nothing to rebuild
            cache_key = ('spec', spec, _locale_name(), _xcompose_mtime())
            ok = self._analyzer.load_from_spec(spec)
        else:
            if keymap_string == self._current_keymap:
                return                      # same keymap; nothing to rebuild
            cache_key = ('keymap', keymap_string, _locale_name(), _xcompose_mtime())
            ok = self._analyzer.load_from_string(keymap_string)

        if not ok:
            _warn(f'could not analyze layout {format_layout(spec)}; '
                    f'keeping the previous correction map.')
            return

        cached = self._symbol_cache.get(cache_key)
        if cached is not None:
            correction_map, symbol_hints, symbol_table = cached
            self._symbol_cache.move_to_end(cache_key)        # LRU touch
        else:
            correction_map = self._analyzer.build_correction_map(number_row=self._number_row)
            symbol_hints = self._analyzer.build_symbol_hints(correction_map)
            symbol_table, miss_info = self._analyzer.build_symbol_table(self._compose_table)
            if miss_info['dead_miss']:
                _warn(f'layout {format_layout(spec)}: '
                        f'{len(miss_info["dead_miss"])} dead key(s) the locale '
                        f'cannot compose: {miss_info["dead_miss"]}. Characters '
                        f'behind them are unavailable in string output.')
            self._symbol_cache[cache_key] = (correction_map, symbol_hints, symbol_table)
            while len(self._symbol_cache) > _SYMBOL_TABLE_CACHE_CAP:
                self._symbol_cache.popitem(last=False)       # evict oldest

        if keymap_string is not None:
            # The backend could only supply a placeholder spec, so name it from
            # the compiled keymap for any observer (logging, a UI indicator).
            spec = spec._replace(description=self._analyzer.layout_name)
            self._current_keymap = keymap_string

        self._current_spec = spec
        self._current_map = correction_map

        # A consumer exception must not kill the detector's watcher thread.
        try:
            self._apply_correction_map(spec, correction_map, symbol_hints, symbol_table)
        except Exception as apply_err:
            _warn(f'apply_correction_map raised for {format_layout(spec)}: {apply_err}')


def main():
    """Standalone harness: announce each layout, its correction map, and the size
    of its symbol table."""
    def show(spec, correction_map, symbol_hints, symbol_table):
        count = len(correction_map)
        plural = 'entry' if count == 1 else 'entries'
        print(f'\nLayout -> {format_layout(spec)}  '
                f'[layout={spec.layout} variant={spec.variant}]')
        print(f'    correction map: {count} {plural}  {correction_map}')
        if symbol_hints:
            print(f'    symbol hints:   {symbol_hints}')
        print(f'    symbol table:   {len(symbol_table)} entries')

    kbl_ctx = KeyboardLayoutContext(apply_correction_map=show)

    print(f'Backend: {kbl_ctx.backend_name}')
    print('Starting layout coordinator (Ctrl-C to stop)...')

    stop_event = threading.Event()

    def handle_signal(signum, frame):
        stop_event.set()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    # start() primes from the active layout, so show() announces it (layout then
    # map) before the watcher takes over; every later switch prints the same way.
    if not kbl_ctx.start():
        print('No detection backend available; nothing to coordinate.')
        return

    print('\nWatching for layout changes...')

    try:
        stop_event.wait()
    finally:
        kbl_ctx.stop()
        print('\nStopped.')


if __name__ == '__main__':
    main()


# End of file #
