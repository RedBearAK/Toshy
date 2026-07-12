"""
Runtime keyboard-layout correction map storage for the keymapper.

src/xwaykeyz/layout_correction.py

Holds the flat keycode correction map that the detection/analysis subsystem
(Toshy's toshy_common.kblayout_*) injects at runtime via set_correction_map(),
plus the inverse map derived from it. The keymapper reads the forward map to
pre-correct incoming keycodes for combo matching on non-US layouts, and the
inverse map to de-correct matched output back to the active layout.

Alongside these it can hold a display-only symbol hint map (keycode -> the
symbol the active layout renders on that physical key) that the keymapper uses
purely to annotate corrected keycodes in its own logs; it is never consulted
for matching or output, so the keymapper stays symbol-blind in its logic.

It also holds the Phase 2 symbol table: a map from a target character (or short
string) to the keystroke sequence that types it on the active layout. Where the
correction map fixes shortcut MATCHING (a flat keycode swap), the symbol table
fixes string/Unicode OUTPUT — to_US_keystrokes and the Unicode path decompose a
target into keystrokes assuming a US layout, which produces garbage on any other
layout. The table lets those paths emit the right keys instead: each entry is a
sequence of (keycode, [modifier_keycodes]) presses — length 1 for a directly
typeable character, length 2 for a dead-key character (press the dead key, then
the base). Characters not in the table are unreachable on this layout and are
handled by the output path's miss policy, not here.

All keycodes here are kernel/evdev codes, matching the Key enum (which mirrors
the kernel input header). XKB keycodes are offset by +8 from these; that offset
is the analyzer's concern and is resolved before anything reaches this module,
so nothing here applies or reasons about it.

The maps are swapped wholesale on each layout change. Swaps arrive on the
detector's watcher thread while the keymapper loop reads on its own thread, so
installation is an atomic reference rebind (never an in-place mutation), which
is safe under CPython without a lock.
"""

__version__ = '20260616'

from .lib.logger import debug, warn, error
from .models.key import Key


_NO_LABEL = 'Layout name not provided'

_correction_map: 'dict[Key, Key]' = {}
_inverse_map: 'dict[Key, Key]' = {}
_symbol_hints: 'dict[Key, str]' = {}
_symbol_table: 'dict[str, list]' = {}
_correction_label: str = _NO_LABEL


# Widest repr() any Key member can produce, computed once at import so the log
# formatter can left-justify the input key into a fixed column the output side
# aligns past — stable no matter which keys a map holds. It sizes to the whole
# enum even though correction maps only ever carry typing-block keys, so the
# column is wider than any real entry needs.
_KEY_REPR_WIDTH = max(len(repr(key)) for key in Key)


def _format_correction_map(mapping: 'dict[Key, Key]') -> str:
    """Render a correction map as one 'in -> out' entry per line, tab-indented
    and sorted by keycode, with the input key left-justified to a static column
    so the output keys align regardless of input-name length."""
    if not mapping:
        return '\t(empty)'
    return '\n'.join(
        f"\t{in_key!r:<{_KEY_REPR_WIDTH}}  ->  {out_key!r}"
        for in_key, out_key in sorted(mapping.items())
    )


def _convert_symbol_table(raw_table: 'dict | None', label: str) -> 'dict[str, list]':
    """Convert a raw evdev symbol table to one keyed on Key objects.

    Input shape (from the analyzer, all ints):
        { target_string: [ (base_keycode, [modifier_keycode, ...]), ... ] }
    Output shape (Key objects, so the output hot path never calls Key()):
        { target_string: [ (Key, [Key, ...]), ... ] }

    The whole table is rejected (returns empty) if ANY entry has a keycode the
    Key enum does not define or a malformed structure — same all-or-nothing
    policy as the correction map: a partially-converted output table could emit
    wrong keystrokes, so a bad table disables symbol output entirely rather than
    half-applying. No offset is applied; the analyzer already resolved XKB's +8.
    """
    if not raw_table:
        return {}
    try:
        converted = {}
        for target, sequence in raw_table.items():
            if not isinstance(target, str) or not isinstance(sequence, (list, tuple)):
                raise TypeError(f'bad entry for {target!r}')
            steps = []
            for step in sequence:
                base_code, mod_codes = step                 # raises if not a 2-tuple
                base_key = Key(base_code)
                mod_keys = [Key(code) for code in mod_codes]
                steps.append((base_key, mod_keys))
            converted[target] = steps
        return converted
    except (ValueError, TypeError) as table_err:
        error(f"Symbol table for '{label}' is malformed ({table_err}); disabling "
                f"symbol output for this layout. {len(raw_table)} raw entries.")
        return {}


def set_correction_map(
    correction_map: 'dict[int, int] | None',
    label: str = _NO_LABEL,
    symbol_hints: 'dict[int, str] | None' = None,
    symbol_table: 'dict[str, list] | None' = None,
):
    """
    Install a new keycode correction map (atomic reference rebind).

    correction_map    - flat {physical_keycode: us_keycode} map of raw kernel
                        (evdev) keycodes, or empty/None for "nothing to correct"
                        (the common case on US-like layouts). The analyzer has
                        already resolved XKB's +8 keycode offset, and Key is
                        evdev-based, so the codes map straight to Key objects with
                        no adjustment here. The inverse {us: physical} is derived
                        from the forward map for output de-correction.
    label             - human-readable layout name, supplied by the detection side
                        purely so the keymapper can name the active layout in its
                        own logs. Never parsed or acted on; the keymapper does no
                        layout reasoning.
    symbol_hints      - optional {physical_keycode: active_layout_symbol} map,
                        supplied alongside the correction map purely so the
                        keymapper can annotate corrected keycodes with the symbol
                        the active layout renders (evdev 17 -> 'z' on AZERTY) in
                        its own logs. Display-only: never used for matching or
                        output, malformed hints are dropped without disabling
                        correction, and hints are cleared whenever the correction
                        map is empty or rejected.
    symbol_table      - optional Phase 2 output table, { target_string:
                        [(base_keycode, [modifier_keycode, ...]), ...] } of raw
                        evdev keycodes, telling the string/Unicode output paths
                        which keystroke sequence types each character on the
                        active layout. Empty/None on US-like layouts (ASCII is
                        reachable directly with no table). Converted to Key
                        objects here; a malformed table disables symbol output
                        for this layout without affecting correction. Independent
                        of the correction map: a layout can need one and not the
                        other, so the table is NOT cleared when the correction
                        map is empty.

    Called from the layout-detection coordinator's callback on the detector's
    watcher thread. A malformed map (a keycode not in the Key enum) is rejected
    whole and falls back to no correction, so a bad map never raises out onto
    the watcher thread.
    """
    global _correction_map
    global _inverse_map
    global _symbol_hints
    global _symbol_table
    global _correction_label
    if not label:
        label = _NO_LABEL
    raw = correction_map or {}
    try:
        # Codes are kernel/evdev (the analyzer already removed XKB's +8 offset)
        # and Key is evdev-based, so they map straight across — do NOT offset here.
        forward = {Key(in_code): Key(out_code) for in_code, out_code in raw.items()}
    except ValueError as key_err:
        error(f"Correction map for '{label}' has an undefined keycode "
                f"({key_err}); disabling correction for this layout. raw={raw}")
        forward = {}
    inverse = {out_key: in_key for in_key, out_key in forward.items()}
    if len(inverse) != len(forward):
        warn(f"Correction map for '{label}' is not one-to-one; output "
                f"de-correction may be wrong. raw={raw}")
    # Symbol hints are display-only: a malformed hint degrades logging, never the
    # correction, and hints make no sense without an active map.
    try:
        hints = {Key(code): symbol for code, symbol in (symbol_hints or {}).items()}
    except (ValueError, TypeError) as hint_err:
        warn(f"Symbol hints for '{label}' are malformed ({hint_err}); dropping "
                f"them. Correction is unaffected. raw={symbol_hints}")
        hints = {}
    if not forward:
        hints = {}
    # Symbol table is independent of correction: a layout may need output
    # correction without keycode correction (or vice versa), so it is installed
    # on its own terms and not cleared when the correction map is empty.
    table = _convert_symbol_table(symbol_table, label)
    _correction_map = forward
    _inverse_map = inverse
    _symbol_hints = hints
    _symbol_table = table
    _correction_label = label
    debug(">>>   " * int(80/6), ctx="LC")
    debug(f"Correction map installed for '{label}' ({len(forward)} entries): \n"
            f"{_format_correction_map(forward)}", ctx="LC")
    debug(f"Symbol table installed for '{label}': {len(table)} entries", ctx="LC")
    debug("<<<   " * int(80/6), ctx="LC")


def correct_key_for_match(key: Key) -> Key:
    """Forward: map a physical key to its US-positional Key for combo matching.
    Returns the key unchanged when it has no correction entry."""
    return _correction_map.get(key, key)


def decorrect_key_for_output(key: Key) -> Key:
    """Inverse: map a US-positional output key to its active-layout Key so a
    matched remap renders the intended symbol. Unchanged when not in the map."""
    return _inverse_map.get(key, key)


def xkb_symbol_for_key(key: Key) -> 'str | None':
    """The symbol the active layout renders on the given physical keycode, for
    log annotation only. None when unknown — US-like layouts (no hints), or a
    key outside the correction set. Never used for matching or any logic."""
    return _symbol_hints.get(key)


def get_correction_map() -> 'dict[Key, Key]':
    """Return the currently installed forward correction map (live reference)."""
    return _correction_map


def keystrokes_for_symbol(target: str) -> 'list | None':
    """Return the keystroke sequence that types a character on the active layout,
    or None when the character has no entry (unreachable on this layout — the
    caller applies its miss policy).

    The sequence is a list of (Key, [Key, ...]) steps: a base key plus the
    modifier keys to hold while pressing it. Length 1 for a directly typeable
    character, length 2 for a dead-key character. Empty table (US-like layouts)
    returns None for everything, so the output path falls back to its existing
    US-positional behaviour, which is already correct there."""
    return _symbol_table.get(target)


def get_symbol_table() -> 'dict[str, list]':
    """Return the currently installed symbol table (live reference)."""
    return _symbol_table


# End of file #
