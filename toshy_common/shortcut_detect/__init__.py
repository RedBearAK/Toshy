#!/usr/bin/env python3
"""
toshy_common/shortcut_detect/__init__.py

Generic machinery for detecting native desktop environment shortcuts:
reading each DE's settings storage, normalizing accelerator strings into
xwaykeyz combo spellings, and resolving per-slot results through the
standard tiers (live settings over static defaults, with explicitly
disabled shortcuts respected).

Built for shortcuts that tend to drift and differ on virtually every DE
(screenshots, launcher/Spotlight equivalents, input-source switching).
Feature packages (e.g. toshy_common.screenshots) supply the domain: slot
vocabularies, per-DE section/schema/key maps, defaults tables with
provenance, and keymap topology. This package supplies the mechanics.

Logging convention: detection operations emit under the 'DT' logging
context. Calls inside this package and the shared log_resolution()
helper carry it intrinsically; feature packages pass ctx='DT' only on
their own one-off detection-related messages.

Internal module layout:
    __main__.py          generic detection check CLI (toshy-detector-check)
    sc_det_accel_rgx.py    compiled regex patterns for accel parsing
    sc_det_accel.py        KDE/GTK accelerator -> combo normalization
    sc_det_kde_rc.py       kglobalshortcutsrc component reader mechanics
    sc_det_gsettings.py    gsettings schema family reader mechanics
    sc_det_xfconf.py       xfconf shortcut XML reader mechanics
    sc_det_result.py       SlotResult, status/source constants, tiering
    sc_det_fallback.py     command fallback output callable factory
    sc_det_diag.py         recording API + literal keymap renderer (CLI)
"""
__version__ = '20260803'

from toshy_common.shortcut_detect.sc_det_accel import (
    normalize_gtk_accel,
    normalize_kde_accel,
)
from toshy_common.shortcut_detect.sc_det_diag import (
    RecordingAPI,
    print_keymap_records,
)
from toshy_common.shortcut_detect.sc_det_fallback import make_cmd_fallback_fn
from toshy_common.shortcut_detect.sc_det_gsettings import read_gsettings_family
from toshy_common.shortcut_detect.sc_det_kde_rc import (
    parse_kde_shortcut_value,
    read_kde_component,
)
from toshy_common.shortcut_detect.sc_det_result import (
    STATUS_DISABLED,
    STATUS_RESOLVED,
    STATUS_UNRESOLVED,
    SOURCE_DEFAULTS_TABLE,
    SOURCE_GENERIC_CONVENTION,
    SOURCE_LIVE_SETTINGS,
    SOURCE_USER_OVERRIDE,
    SlotResult,
    log_resolution,
    resolve_slot_tiers,
)
from toshy_common.shortcut_detect.sc_det_xfconf import read_merged_accel_commands

# End of file #
