#!/usr/bin/env python3
"""
toshy_common/spotlight_input/spli_readers.py

Per-DE readers for launcher and input-source-switching shortcuts. Thin
domain wrappers over toshy_common.shortcut_detect mechanics.
"""
__version__ = '20260805'

from toshy_common.logger import error
from toshy_common.shortcut_detect import (
    STATUS_DISABLED,
    STATUS_RESOLVED,
    normalize_gtk_accel,
    read_gsettings_family,
    read_kde_component,
)
from toshy_common.shortcut_detect.sc_det_gsettings import (
    gsettings_get,
    parse_gvariant_accel_value,
)
from toshy_common.shortcut_detect.sc_det_cosmic import read_cosmic_shortcuts
from toshy_common.shortcut_detect.sc_det_spices import read_spices_setting
from toshy_common.spotlight_input.spli_defaults import (
    SLOT_INPUT_SWITCH_LAST,
    SLOT_INPUT_SWITCH_NEXT,
    SLOT_INPUT_SWITCH_PREV,
    SLOT_LAUNCHER_UI,
)


# KDE: layout switcher + krunner live in kglobalshortcutsrc.
# Section and action names confirmed against a real Plasma 6 file.
_KDE_SWITCHER_SECTIONS_LST = ['[KDE Keyboard Layout Switcher]']
_KDE_SWITCHER_ACTION_SLOT_DCT = {
    'Switch to Last-Used Keyboard Layout':  SLOT_INPUT_SWITCH_LAST,
    'Switch to Next Keyboard Layout':       SLOT_INPUT_SWITCH_NEXT,
}
_KDE_KRUNNER_SECTIONS_LST = [
    '[org.kde.krunner.desktop]',
    '[services][org.kde.krunner.desktop]',
]
_KDE_KRUNNER_ACTION_SLOT_DCT = {
    '_launch':                              SLOT_LAUNCHER_UI,
    'RunCommand':                           SLOT_LAUNCHER_UI,
}


def read_kde() -> dict:
    results_dct = read_kde_component(
        _KDE_SWITCHER_SECTIONS_LST, _KDE_SWITCHER_ACTION_SLOT_DCT)
    results_dct.update(read_kde_component(
        _KDE_KRUNNER_SECTIONS_LST, _KDE_KRUNNER_ACTION_SLOT_DCT))
    return results_dct


# GNOME: input switching in the WM keybindings schema. The launcher
# (Overview) shortcut is a two-tier chain: Toshy setup disables mutter's
# modifier-only 'overlay-key' and binds gnome-shell's 'toggle-overview'
# instead (verified: org.gnome.shell.keybindings::toggle-overview, type
# 'as', upstream default [] -- so the Toshy-set binding is what a live
# read finds). 'overlay-key' (org.gnome.mutter, type 's', upstream
# default 'Super') is the fallback for non-Toshy-configured systems.
# Both unset on a readable system is a loud error: the Overview is the
# main Spotlight equivalent on GNOME and nothing can be emitted for it.
_GNOME_WM_SCHEMA = 'org.gnome.desktop.wm.keybindings'
_GNOME_WM_SLOT_KEY_DCT = {
    SLOT_INPUT_SWITCH_NEXT:     'switch-input-source',
    SLOT_INPUT_SWITCH_PREV:     'switch-input-source-backward',
}
_GNOME_SHELL_KB_SCHEMA  = 'org.gnome.shell.keybindings'
_GNOME_MUTTER_SCHEMA    = 'org.gnome.mutter'


def _read_gnome_launcher() -> dict:
    toggle_raw = gsettings_get(_GNOME_SHELL_KB_SCHEMA, 'toggle-overview')
    if toggle_raw is not None:
        status, raw_accel = parse_gvariant_accel_value(toggle_raw)
        if status == STATUS_RESOLVED:
            combo_str = normalize_gtk_accel(raw_accel)
            if combo_str is not None:
                return {SLOT_LAUNCHER_UI: (
                    STATUS_RESOLVED, combo_str, raw_accel,
                    'gnome-shell toggle-overview')}
            error(f'SPOTL: Could not parse toggle-overview value '
                    f'{raw_accel!r}; trying overlay-key fallback', ctx='DT')

    overlay_raw = gsettings_get(_GNOME_MUTTER_SCHEMA, 'overlay-key')
    if overlay_raw is not None:
        status, raw_accel = parse_gvariant_accel_value(overlay_raw)
        if status == STATUS_RESOLVED:
            combo_str = normalize_gtk_accel(raw_accel)
            if combo_str is not None:
                return {SLOT_LAUNCHER_UI: (
                    STATUS_RESOLVED, combo_str, overlay_raw,
                    'mutter overlay-key (fallback; toggle-overview unset)')}

    if toggle_raw is not None or overlay_raw is not None:
        # gsettings works but neither shortcut is bound: successful read
        # of "nothing", reported as DISABLED so the static defaults table
        # cannot paper over it with a combo nothing is listening for.
        error("SPOTL: Could not resolve a shortcut for the GNOME Overview: "
                "'toggle-overview' (org.gnome.shell.keybindings) and "
                "'overlay-key' (org.gnome.mutter) are both unset/disabled. "
                'Toshy setup normally binds toggle-overview; without either, '
                'the Cmd+Space launcher remap has nothing to emit.', ctx='DT')
        return {SLOT_LAUNCHER_UI: (
            STATUS_DISABLED, None, '',
            'no Overview shortcut bound; see journal')}

    return {}


def read_gnome(de_maj_ver=None) -> dict:
    results_dct = read_gsettings_family(_GNOME_WM_SCHEMA, _GNOME_WM_SLOT_KEY_DCT)
    results_dct.update(_read_gnome_launcher())
    return results_dct


# Cinnamon: input switching via Muffin WM keybindings schema (key names
# verified in cinnamon-settings KeybindingTable.py, 6.6.9); launcher via
# the menu applet's Spices 'overlay-key' setting (settings-schema.json
# default 'Super_L::Super_R', '::' separates alternate bindings).
_CINNAMON_WM_SCHEMA = 'org.cinnamon.desktop.keybindings.wm'
_CINNAMON_WM_SLOT_KEY_DCT = {
    SLOT_INPUT_SWITCH_NEXT:     'switch-input-source',
    SLOT_INPUT_SWITCH_PREV:     'switch-input-source-backward',
}
_CINNAMON_MENU_APPLET_UUID = 'menu@cinnamon.org'


def read_cinnamon() -> dict:
    results_dct = read_gsettings_family(_CINNAMON_WM_SCHEMA, _CINNAMON_WM_SLOT_KEY_DCT)

    overlay_value = read_spices_setting(_CINNAMON_MENU_APPLET_UUID, 'overlay-key')
    if overlay_value:
        for alternate_str in str(overlay_value).split('::'):
            combo_str = normalize_gtk_accel(alternate_str.strip())
            if combo_str is None:
                continue
            results_dct[SLOT_LAUNCHER_UI] = (
                STATUS_RESOLVED, combo_str, str(overlay_value),
                'menu applet overlay-key (first alternate)')
            break
    return results_dct


# COSMIC: shortcuts in cosmic-config layered RON files (no gsettings).
# The sole input-switch action is System(InputSourceSwitch), default
# Super+Space (cosmic-comp data/keybindings.ron line 102, 2026-08); a
# forward cycle, so it maps to the 'next' slot. The launcher is
# System(Launcher), default bare Super (modifier-only binding).
_COSMIC_ACTION_SLOT_DCT = {
    'InputSourceSwitch':    SLOT_INPUT_SWITCH_NEXT,
    'Launcher':             SLOT_LAUNCHER_UI,
}


def read_cosmic() -> dict:
    return read_cosmic_shortcuts(_COSMIC_ACTION_SLOT_DCT)


READERS_DCT = {
    'kde':      lambda ver: read_kde(),
    'plasma':   lambda ver: read_kde(),
    'gnome':    read_gnome,
    'cinnamon': lambda ver: read_cinnamon(),
    'cosmic':   lambda ver: read_cosmic(),
}

# End of file #
