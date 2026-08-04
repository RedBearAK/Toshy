#!/usr/bin/env python3
"""
toshy_common/spotlight_input/spli_resolver.py

Resolution for the Spotlight/input-switching slots: live readers over
static defaults via the shared tiering, with standard DT-context logging.
"""
__version__ = '20260804'

from toshy_common.shortcut_detect import (
    SOURCE_DEFAULTS_TABLE,
    log_resolution,
    resolve_slot_tiers,
)
from toshy_common.spotlight_input.spli_defaults import (
    INPUT_DEFAULTS_DCT,
    LAUNCHER_DEFAULTS_DCT,
    LAUNCHER_GNOME_PRE45,
    SLOT_LAUNCHER_UI,
    SLOT_NAMES,
)
from toshy_common.spotlight_input.spli_readers import READERS_DCT


def _defaults_for(desktop_env_str: str, de_maj_ver) -> dict:
    table_dct = dict(INPUT_DEFAULTS_DCT.get(desktop_env_str, {}))
    launcher_combo = LAUNCHER_DEFAULTS_DCT.get(desktop_env_str)
    if desktop_env_str == 'gnome':
        try:
            if de_maj_ver is not None and int(de_maj_ver) < 45:
                launcher_combo = LAUNCHER_GNOME_PRE45
        except (TypeError, ValueError):
            pass
    if launcher_combo:
        table_dct[SLOT_LAUNCHER_UI] = launcher_combo
    return table_dct


def resolve_outputs(desktop_env_str: str, de_maj_ver=None) -> dict:
    desktop_env_str = (desktop_env_str or '').strip().lower()

    reader_fn = READERS_DCT.get(desktop_env_str)
    live_dct = reader_fn(de_maj_ver) if reader_fn else {}
    table_dct = _defaults_for(desktop_env_str, de_maj_ver)

    results_dct = resolve_slot_tiers(SLOT_NAMES, live_dct, table_dct, SOURCE_DEFAULTS_TABLE)
    log_resolution('SPOTL',
                    f"Spotlight/input shortcuts for '{desktop_env_str or 'unknown DE'}'",
                    results_dct, live_dct, SOURCE_DEFAULTS_TABLE)
    return results_dct

# End of file #
