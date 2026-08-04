#!/usr/bin/env python3
"""
toshy_common/shortcut_detect/sc_det_accel.py

Accelerator normalization: converts DE-native accelerator strings (KDE
Qt-style 'Meta+Shift+Print', GTK-style '<Control><Shift>Print') into
xwaykeyz output combo strings with a canonical modifier spelling order.
"""
__version__ = '20260803'

from toshy_common.shortcut_detect.sc_det_accel_rgx import (
    _rgx_gtk_mod_token,
    _rgx_key_token_valid,
)


# Canonical modifier emission order for output combo strings, following
# the config file's macOS-style convention (Shift, Fn, Ctrl, Alt, Cmd --
# top-down, left-to-right on the left-corner modifiers), translated to
# logical identities: Shift, C, Alt, Super. Combo parsing in the engine
# is order-insensitive; this is purely for consistent, readable spelling.
_MOD_ORDER_LST = ['Shift', 'C', 'Alt', 'Super']

# KDE (Qt-style) modifier token names -> xwaykeyz modifier names.
_KDE_MOD_XLAT_DCT = {
    'meta':     'Super',
    'ctrl':     'C',
    'control':  'C',
    'shift':    'Shift',
    'alt':      'Alt',
}

# GTK-style modifier token names -> xwaykeyz modifier names.
# '<Primary>' is GTK's platform-abstract name for Ctrl on Linux.
# '<Meta>' is mapped to Super, which is where Meta lands on typical
# PC layouts under GNOME-family DEs.
_GTK_MOD_XLAT_DCT = {
    'primary':  'C',
    'control':  'C',
    'ctrl':     'C',
    'ctl':      'C',
    'shift':    'Shift',
    'alt':      'Alt',
    'mod1':     'Alt',
    'meta':     'Super',
    'super':    'Super',
    'win':      'Super',
    'mod4':     'Super',
}

# Minor key name translations where DE naming differs from xwaykeyz.
_KEY_NAME_XLAT_DCT = {
    'Return':   'Enter',
    'Escape':   'Esc',
    'Super_L':  'Super',
    'Super_R':  'RSuper',
}


def _canonical_combo(mods_lst: 'list[str]', key_name: str) -> str:
    """Assemble a normalized combo string with deterministic modifier order."""
    ordered_mods_lst = [mod for mod in _MOD_ORDER_LST if mod in mods_lst]
    return '-'.join(ordered_mods_lst + [key_name])


def normalize_kde_accel(accel_str: str) -> 'str | None':
    """Convert a KDE accelerator like 'Meta+Shift+Print' to 'Shift-Super-Print'.

    Returns None if the accelerator cannot be represented (unknown modifier,
    multi-word key name, empty input)."""
    if not accel_str:
        return None

    parts_lst = [part.strip() for part in accel_str.split('+')]
    if any(not part for part in parts_lst):
        return None

    key_name = parts_lst[-1]
    mod_parts_lst = parts_lst[:-1]

    mods_lst = []
    for mod_part in mod_parts_lst:
        xlat_mod = _KDE_MOD_XLAT_DCT.get(mod_part.lower())
        if xlat_mod is None:
            return None
        if xlat_mod not in mods_lst:
            mods_lst.append(xlat_mod)

    # A trailing modifier name means a modifier-only shortcut; emit the
    # modifier itself as the "key" (xwaykeyz can emit a modifier tap).
    key_as_mod = _KDE_MOD_XLAT_DCT.get(key_name.lower())
    if key_as_mod is not None:
        key_name = key_as_mod
    else:
        key_name = _KEY_NAME_XLAT_DCT.get(key_name, key_name)
        if not _rgx_key_token_valid.match(key_name):
            return None

    return _canonical_combo(mods_lst, key_name)


def normalize_gtk_accel(accel_str: str) -> 'str | None':
    """Convert a GTK accelerator like '<Control><Shift>Print' to 'Shift-C-Print'.

    Returns None if the accelerator cannot be represented."""
    if not accel_str:
        return None

    mod_tokens_lst = _rgx_gtk_mod_token.findall(accel_str)
    key_name = _rgx_gtk_mod_token.sub('', accel_str).strip()

    mods_lst = []
    for mod_token in mod_tokens_lst:
        xlat_mod = _GTK_MOD_XLAT_DCT.get(mod_token.lower())
        if xlat_mod is None:
            return None
        if xlat_mod not in mods_lst:
            mods_lst.append(xlat_mod)

    key_name = _KEY_NAME_XLAT_DCT.get(key_name, key_name)
    if not _rgx_key_token_valid.match(key_name):
        return None

    return _canonical_combo(mods_lst, key_name)

# End of file #
