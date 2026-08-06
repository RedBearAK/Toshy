#!/usr/bin/env python3
"""
toshy_common/screenshots/sshot_resolver.py

Public API for macOS-shape screenshot shortcut mapping.

Resolves, for each purpose-named "slot" (see sshot_defaults.py), the
output combo Toshy should emit to trigger the equivalent native screenshot
action on the current desktop environment. Resolution precedence per slot:

    1. user override        (set_custom_output(), e.g. for flameshot users)
    2. live settings        (per-DE reader: kglobalshortcutsrc, gsettings,
                             xfconf XML)
    3. static defaults      (source-verified tables in sshot_defaults.py)
    4. generic convention   (unknown DEs only: gnome-settings-daemon
                             heritage Print combos)

A slot whose native shortcut is *explicitly disabled* in live settings
stays unmapped (respecting the user's choice) rather than falling through
to defaults. This module never runs external commands and never imports
xwaykeyz; the config file is the bridge, wrapping the returned combo
strings with C() itself.

Typical config-side usage (see screenshot_shortcuts_config_example.py):

    entries_dct = build_keymap_entries(input_combos_dct, DESKTOP_ENV, DE_MAJ_VER)
    # then inside the GenGUI overrides keymap:
    # **{C(in_combo): C(out_combo) for in_combo, out_combo in entries_dct.items()},
"""
__version__ = '20260803'


from toshy_common.logger import debug
from toshy_common.shortcut_detect import (
    SOURCE_DEFAULTS_TABLE,
    SOURCE_GENERIC_CONVENTION,
    SOURCE_USER_OVERRIDE,
    STATUS_DISABLED,
    STATUS_RESOLVED,
    SlotResult,
    log_resolution,
    resolve_slot_tiers,
)
from toshy_common.shortcut_detect.sc_det_accel_rgx import _rgx_combo_valid
from toshy_common.screenshots.sshot_defaults import (
    CINNAMON_DEFAULTS_DCT,
    COSMIC_DEFAULTS_DCT,
    GENERIC_DEFAULTS_DCT,
    GNOME_42_DEFAULTS_DCT,
    GNOME_LEGACY_DEFAULTS_DCT,
    KDE_DEFAULTS_DCT,
    MATE_DEFAULTS_DCT,
    SLOT_NAMES,
    XFCE_DEFAULTS_DCT,
)
from toshy_common.screenshots.sshot_readers import (
    read_budgie,
    read_cinnamon,
    read_gnome,
    read_kde,
    read_mate,
    read_xfce,
    read_cosmic,
)


# Desktop environment identifier -> (reader description, defaults table).
# Reader callables are dispatched in _run_reader() to keep gnome's version
# hint argument explicit.
_FAMILY_TABLES_DCT = {
    'kde':          KDE_DEFAULTS_DCT,
    'plasma':       KDE_DEFAULTS_DCT,
    'gnome':        None,   # version-dependent, handled in _defaults_for()
    'budgie':       GNOME_LEGACY_DEFAULTS_DCT,
    'cinnamon':     CINNAMON_DEFAULTS_DCT,
    'cosmic':       COSMIC_DEFAULTS_DCT,
    'mate':         MATE_DEFAULTS_DCT,
    'xfce':         XFCE_DEFAULTS_DCT,
}

# User override registry: slot name -> combo string, or None to suppress.
_custom_outputs_dct = {}


def set_custom_output(slot_name: str, combo_str: 'str | None'):
    """Register a custom output combo for one slot (or None to suppress
    the slot entirely). Overrides win over all detection tiers.

    Intended for users of non-native screenshot tools (flameshot etc.) who
    have bound their own shortcuts: point the macOS-shape slot at whatever
    combo their tool listens for."""
    if slot_name not in SLOT_NAMES:
        valid_names_str = ', '.join(SLOT_NAMES)
        raise ValueError(
            f'Unknown screenshot slot name: {slot_name!r}. '
            f'Valid slot names: {valid_names_str}')

    if combo_str is not None:
        if not isinstance(combo_str, str) or not _rgx_combo_valid.match(combo_str):
            raise ValueError(
                f'Invalid combo string for slot {slot_name!r}: {combo_str!r}. '
                f"Expected xwaykeyz-style combo like 'C-Shift-Print'.")

    _custom_outputs_dct[slot_name] = combo_str


def clear_custom_outputs():
    """Remove all registered custom outputs (mainly for tests)."""
    _custom_outputs_dct.clear()


def _run_reader(desktop_env_str: str, de_maj_ver: 'int | None') -> dict:
    if desktop_env_str in ('kde', 'plasma'):
        return read_kde()
    if desktop_env_str == 'gnome':
        return read_gnome(de_maj_ver)
    if desktop_env_str == 'budgie':
        return read_budgie()
    if desktop_env_str == 'cinnamon':
        return read_cinnamon()
    if desktop_env_str == 'cosmic':
        return read_cosmic()
    if desktop_env_str == 'mate':
        return read_mate()
    if desktop_env_str == 'xfce':
        return read_xfce()
    return {}


def _defaults_for(desktop_env_str: str, de_maj_ver: 'int | None'
                    ) -> 'tuple[dict, str]':
    """Return (defaults table, source label) for the desktop environment."""
    if desktop_env_str == 'gnome':
        if de_maj_ver is not None and de_maj_ver < 42:
            return (GNOME_LEGACY_DEFAULTS_DCT, SOURCE_DEFAULTS_TABLE)
        return (GNOME_42_DEFAULTS_DCT, SOURCE_DEFAULTS_TABLE)

    table_dct = _FAMILY_TABLES_DCT.get(desktop_env_str)
    if table_dct is not None:
        return (table_dct, SOURCE_DEFAULTS_TABLE)

    return (GENERIC_DEFAULTS_DCT, SOURCE_GENERIC_CONVENTION)


def _coerce_maj_ver(de_maj_ver) -> 'int | None':
    """Accept int, digit string, or None for the DE major version hint."""
    if de_maj_ver is None:
        return None
    if isinstance(de_maj_ver, int):
        return de_maj_ver
    if isinstance(de_maj_ver, str) and de_maj_ver.strip().isdigit():
        return int(de_maj_ver.strip())
    return None


def resolve_outputs(desktop_env: str, de_maj_ver=None) -> dict:
    """Resolve all slots for the given desktop environment.

    Returns a dict mapping every slot name to a SlotResult. Callers should
    only emit combos for slots with status STATUS_RESOLVED."""
    desktop_env_str = (desktop_env or '').strip().lower()
    maj_ver = _coerce_maj_ver(de_maj_ver)

    live_dct = _run_reader(desktop_env_str, maj_ver)
    table_dct, table_source = _defaults_for(desktop_env_str, maj_ver)

    results_dct = resolve_slot_tiers(SLOT_NAMES, live_dct, table_dct, table_source)

    # User overrides (vestigial registry; keymaps are the idiomatic path)
    # win over all detection tiers.
    for slot_name, custom_combo in _custom_outputs_dct.items():
        if custom_combo is None:
            results_dct[slot_name] = SlotResult(
                STATUS_DISABLED, source=SOURCE_USER_OVERRIDE, note='suppressed by user')
        else:
            results_dct[slot_name] = SlotResult(
                STATUS_RESOLVED, combo=custom_combo, source=SOURCE_USER_OVERRIDE)

    log_resolution('SSHOT',
                    f"Screenshot shortcuts for '{desktop_env_str or 'unknown DE'}'",
                    results_dct, live_dct, table_source)
    return results_dct


def build_keymap_entries(input_combos_dct: dict, desktop_env: str, de_maj_ver=None) -> dict:
    """Build {input_combo: output_combo} for resolved slots only.

    The config file owns the input side (it knows its own modmap world);
    this module owns the output side. Unknown slot names in the input dict
    raise loudly to catch typos at config load."""
    for slot_name in input_combos_dct:
        if slot_name in SLOT_NAMES:
            continue
        valid_names_str = ', '.join(SLOT_NAMES)
        raise ValueError(
            f'Unknown screenshot slot name in input combos: {slot_name!r}. '
            f'Valid slot names: {valid_names_str}')

    results_dct = resolve_outputs(desktop_env, de_maj_ver)

    entries_dct = {}
    for slot_name, input_combo in input_combos_dct.items():
        result = results_dct[slot_name]
        if result.status != STATUS_RESOLVED:
            debug(f"SSHOT: build_keymap_entries skipping '{slot_name}' ({result.status})", ctx='DT')
            continue
        entries_dct[input_combo] = result.combo

    return entries_dct

# End of file #
