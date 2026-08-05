#!/usr/bin/env python3
"""
toshy_common/shortcut_detect/sc_det_gsettings.py

Parameterized reader mechanics for gsettings-backed shortcut schemas
(GNOME family, Cinnamon, MATE/Marco, Budgie). Values are read via the
'gsettings get' subprocess so the dconf layering and schema defaults are
resolved by the platform itself.

Callers supply the schema id and a slot-name -> key-name map; this
module knows the storage mechanics, not any feature domain.
"""
__version__ = '20260803'

import ast
import subprocess

from toshy_common.logger import error
from toshy_common.shortcut_detect.sc_det_accel import normalize_gtk_accel
from toshy_common.shortcut_detect.sc_det_result import (
    STATUS_DISABLED,
    STATUS_RESOLVED,
)


_GSETTINGS_TIMEOUT_SEC = 5


def gsettings_get(schema_str: str, key_str: str) -> 'str | None':
    """Run 'gsettings get' and return raw output, or None on any failure."""
    try:
        proc = subprocess.run(
            ['gsettings', 'get', schema_str, key_str],
            capture_output=True, text=True, timeout=_GSETTINGS_TIMEOUT_SEC
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    output_str = proc.stdout.strip()
    if not output_str:
        return None
    return output_str


def parse_gvariant_accel_value(text_str: str) -> 'tuple[str, str | None]':
    """Parse a gsettings value into (status, raw_accel_or_None).

    Handles list-typed values like "['<Shift>Print']", empty lists
    (including the '@as []' spelling), plain string values like
    "'<Alt>Print'", and the Marco 'disabled' sentinel."""
    if text_str.startswith('@as'):
        text_str = text_str[len('@as'):].strip()

    try:
        parsed_value = ast.literal_eval(text_str)
    except (ValueError, SyntaxError):
        return (STATUS_DISABLED, None)

    if isinstance(parsed_value, (list, tuple)):
        parsed_value = parsed_value[0] if parsed_value else ''

    if not isinstance(parsed_value, str):
        return (STATUS_DISABLED, None)

    parsed_value = parsed_value.strip()
    if not parsed_value or parsed_value.lower() == 'disabled':
        return (STATUS_DISABLED, None)

    return (STATUS_RESOLVED, parsed_value)


def read_gsettings_family(schema_str: str, slot_key_dct: dict,
                            notes_dct: 'dict | None' = None) -> dict:
    """Read one gsettings schema family into the reader return contract.

    Multiple slots may alias the same key; each distinct key is queried
    and parsed exactly once, then fanned out to its slots. Returns {} if
    the schema is entirely unreadable (probe on the first distinct key
    fails), so the caller can try another family or fall through."""
    notes_dct = notes_dct or {}

    distinct_keys_lst = list(dict.fromkeys(slot_key_dct.values()))
    key_results_dct = {}
    for key_idx, key_str in enumerate(distinct_keys_lst):
        raw_output = gsettings_get(schema_str, key_str)
        if raw_output is None:
            if key_idx == 0:
                # Schema/key missing on first probe: family unavailable.
                return {}
            continue

        status, raw_accel = parse_gvariant_accel_value(raw_output)
        if status == STATUS_DISABLED:
            key_results_dct[key_str] = (STATUS_DISABLED, None, raw_output)
            continue

        combo_str = normalize_gtk_accel(raw_accel)
        if combo_str is None:
            error(f"SC_DET: Could not parse '{schema_str}::{key_str}' value "
                    f'{raw_accel!r} (slot falls back to defaults)', ctx='DT')
            continue
        key_results_dct[key_str] = (STATUS_RESOLVED, combo_str, raw_accel)

    results_dct = {}
    for slot_name, key_str in slot_key_dct.items():
        key_result = key_results_dct.get(key_str)
        if key_result is None:
            continue
        status, combo_str, raw_str = key_result
        results_dct[slot_name] = (status, combo_str, raw_str, notes_dct.get(slot_name, ''))

    return results_dct

# End of file #
