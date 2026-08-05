"""
Shared preference-item metadata for the Toshy preference UIs.

toshy_common/preference_items.py

Single source of truth for the boolean preference toggles and the
radio-style choice groups presented by every Toshy preference UI (tray
icon menu, GTK4 Preferences app, terminal menu). Each UI renders these
items in its own way, but none of them re-declares the settings
attribute names, labels, or help texts.

Only the flat item DATA lives here. Menu STRUCTURE (submenu nesting,
column layout, section ordering) stays in each UI, because the
presentations have genuinely different shapes and a shared tree would
fight all of them.

Two label widths are provided per toggle because the UIs need different
ones: `label_short` for the tray icon menu, where a long label makes the
menu unusably wide, and `label_long` for the GTK4 app and the terminal
menu, which have room for more descriptive wording. Trailing '*' on a
label marks a default-enabled item (or default choice), following the
existing convention; the marker lives in the label text itself, and the
GTK4 app currently only marks the long labels, so short and long labels
may legitimately differ on the marker.

Canonical `capslock_mode` data still lives in toshy_common/modifier_modes.py,
because the Toshy config file imports it to validate the setting on every
load. CAPSLOCK_MODE_GROUP below only wraps those constants so that UIs can
iterate all three choice groups uniformly; it does not copy them.

Overlay flags are deliberately absent: toshy_common/overlay_context.py
already provides OVL_METADATA for exactly this purpose.
"""

__version__ = '20260804'

from dataclasses import dataclass, field

from toshy_common.modifier_modes import (
    CAPSLOCK_MODES,
    CAPSLOCK_MODE_HELP,
    CAPSLOCK_MODE_LABELS,
    CAPSLOCK_MODE_DEFAULT,
)


# Section headings used to group toggles. An empty group is the main block,
# shown without any heading. UIs that cannot render a heading (or choose not
# to) can simply ignore the field and present a flat list.
PREF_GROUP_MAIN         = ''
PREF_GROUP_SUPER_TAP    = 'Super Tap Passthru'

# Group-level help, keyed by group heading, for UIs that can attach help to
# a section header (GTK4 app; the terminal menu can show it for a heading
# row). The main group has no heading and therefore no group help.
PREF_GROUP_HELP = {
    PREF_GROUP_SUPER_TAP: (
        'Makes a modifier key do double duty: a quick tap sends a Super '
        '(Meta/Win) key tap, useful for opening app launchers or the '
        'GNOME/KDE overview, while holding it keeps its normal Toshy '
        'role for shortcut combos.\n\nEnable for the Left Option '
        'position key, the Left Command position key, or both.'),
}


@dataclass
class PrefToggle:
    """One boolean preference, as presented by the preference UIs.

    attr_name is both the Settings class attribute and the key stored in
    the preferences database, so UIs can round-trip a value with
    getattr()/setattr() without a lookup table.
    """

    attr_name:      str
    label_short:    str
    label_long:     str
    help_title:     str
    help_text:      str
    group:          str = PREF_GROUP_MAIN


@dataclass
class PrefChoiceGroup:
    """One radio-style preference with a fixed set of valid values.

    `values` is ordered, and UIs present the choices in that order. Do not
    reorder existing entries casually. `value_labels` and `value_help` are
    keyed by the value strings; a UI that cannot show per-value help just
    ignores `value_help`.
    """

    attr_name:      str
    group_label:    str
    values:         tuple
    value_labels:   dict
    default:        str
    help_title:     str
    help_text:      str
    value_help:     dict = field(default_factory=dict)


# ---- Boolean preference toggles ---------------------------------------------
# Order matches the tray icon menu's Preferences submenu, which is the most
# constrained presentation. Other UIs are free to re-order or split into
# columns; they just must not invent labels or attribute names.

PREF_TOGGLES = (

    PrefToggle(
        attr_name='altgr_on_menu_key',
        label_short='Alt_Gr on Menu key',
        label_long='Alt_Gr on Menu key*',
        help_title='Alt_Gr on Menu key',
        help_text=(
            'Maps the PC laptop context menu key to act as Right Alt '
            "(Alt_Gr), recovering Alt_Gr where the keyboard's modifier "
            'layout would otherwise lose it'),
    ),

    PrefToggle(
        attr_name='multi_lang',
        label_short='Alt_Gr on Right Cmd',
        label_long='Alt_Gr on Right Cmd key',
        help_title='Alt_Gr on Right Cmd key',
        help_text=(
            'Restores access to the Level3/4 additional characters on '
            'non-US keyboards/layouts'),
    ),

    PrefToggle(
        attr_name='Enter2Ent_Cmd',
        label_short='Enter is Enter & Cmd',
        label_long='Multipurpose Enter: Enter, Cmd',
        help_title='Multipurpose Enter: Enter, Cmd',
        help_text=(
            'Modmap Enter key to be:\n'
            '\u2022 Enter when tapped\n'
            '\u2022 Command key for hold/combo'),
    ),

    PrefToggle(
        attr_name='forced_numpad',
        label_short='Forced Numpad',
        label_long='Forced Numpad*',
        help_title='Forced Numpad',
        help_text=(
            'Makes the numeric keypad always act like a Numpad, ignoring '
            'actual NumLock LED state.\n'
            '\u2022 NumLock key becomes "Clear" key (Escape)\n'
            '\u2022 Option+NumLock toggles NumLock OFF/ON\n\n'
            '(Fn+NumLock will also toggle NumLock state, but only on real '
            'Apple keyboards)\n\n'
            'Feature is enabled by default.'),
    ),

    PrefToggle(
        attr_name='media_arrows_fix',
        label_short='Media Arrows Fix',
        label_long='Media Arrows Fix',
        help_title='Media Arrows Fix',
        help_text=(
            'Converts arrow keys that have "media" functions when used '
            'with Fn key, into PgUp/PgDn/Home/End keys'),
    ),

    PrefToggle(
        attr_name='ST3_in_VSCode',
        label_short='Sublime3 in VSCode',
        label_long='Sublime Text 3 shortcuts in VSCode(s)',
        help_title='Sublime Text 3 shortcuts in VSCode(s)',
        help_text=(
            'Use shortcuts from Sublime Text 3 in Visual Studio Code '
            '(and variants)'),
    ),

    PrefToggle(
        attr_name='swap_spotlight_and_input',
        label_short='Swap Spotlight & Input Switch',
        label_long='Swap Spotlight & Input Switch',
        help_title='Swap Spotlight & Input Switch',
        help_text=(
            'Swaps the launcher ("Spotlight") and input source switching '
            'shortcuts:\n'
            '\u2022 Default: Cmd+Space opens the launcher, Ctrl+Space '
            'switches input source\n'
            '\u2022 Swapped: Cmd+Space switches input source, Ctrl+Space '
            'opens the launcher\n\n'
            'Before Mac OS X 10.4 "Tiger" introduced Spotlight in 2005, '
            'Cmd+Space was the input source switch on the Mac, and Tiger '
            'upgraders using multiple input sources kept that arrangement '
            '(with Spotlight on Ctrl+Space). This toggle restores the '
            'classic arrangement for long-time multilingual Mac users.\n\n'
            "Takes effect immediately when the config's Spotlight/"
            'input-switch keymaps are active.'),
    ),

    PrefToggle(
        attr_name='l_opt_is_sup_and_opt',
        label_short='L_Opt is Super & Opt',
        label_long='Multipurpose Left Opt: Super, Opt',
        help_title='Multipurpose Left Opt: Super, Opt',
        help_text=(
            'Modmap Left Option position key to be:\n'
            '\u2022 Super/Meta when tapped\n'
            '\u2022 Option key for hold/combo'),
        group=PREF_GROUP_SUPER_TAP,
    ),

    PrefToggle(
        attr_name='l_cmd_is_sup_and_cmd',
        label_short='L_Cmd is Super & Cmd',
        label_long='Multipurpose Left Cmd: Super, Cmd',
        help_title='Multipurpose Left Cmd: Super, Cmd',
        help_text=(
            'Modmap Left Command position key to be:\n'
            '\u2022 Super/Meta when tapped\n'
            '\u2022 Command key for hold/combo'),
        group=PREF_GROUP_SUPER_TAP,
    ),

)


# ---- Choice groups (radio-style preferences) --------------------------------

CAPSLOCK_MODE_GROUP = PrefChoiceGroup(
    attr_name='capslock_mode',
    group_label='CapsLock Mode',
    values=CAPSLOCK_MODES,
    value_labels=CAPSLOCK_MODE_LABELS,
    default=CAPSLOCK_MODE_DEFAULT,
    help_title='CapsLock Mode',
    help_text=(
        'What the Caps (CapsLock) key does. Each mode has its own help '
        'text with details.'
        '\n\nIn this config, the physical Left Ctrl key\'s "role" is '
        'context-dependent: it acts as a real Ctrl key (LEFT_CTRL) in '
        'terminals, but as Super/Meta (LEFT_META) in GUI apps, where '
        'the Cmd key equivalent handles most shortcuts. "Role swap" '
        'modes give Caps that same split identity, and turn the '
        'physical Left Ctrl key into a literal CapsLock toggle.'
        '\n\nDefault (*) is for Caps to just act like CapsLock.'),
    value_help=CAPSLOCK_MODE_HELP,
)


OPTSPEC_LAYOUTS = (
    'US',
    'ABC',
    'Disabled',
)

OPTSPEC_LAYOUT_DEFAULT = 'Disabled'

# Short labels for compact UIs (tray submenu); the GTK4 app composes its own
# longer radio labels but must keep the '*' on the same (default) choice.
OPTSPEC_LAYOUT_LABELS = {
    'US':           'US',
    'ABC':          'ABC Extended',
    'Disabled':     'Disabled*',
}

OPTSPEC_LAYOUT_GROUP = PrefChoiceGroup(
    attr_name='optspec_layout',
    group_label='OptSpec Layout',
    values=OPTSPEC_LAYOUTS,
    value_labels=OPTSPEC_LAYOUT_LABELS,
    default=OPTSPEC_LAYOUT_DEFAULT,
    help_title='Option-key Special Characters',
    help_text=(
        'Option-key special characters are available on all regular keys '
        'and punctuation keys when holding Option or Shift+Option. '
        'Choices are standard US layout, ABC Extended layout, or '
        'disabled. \n\nDefault is disabled.'),
)


# 'Auto-Adapt' means no override: the config identifies each keyboard on the
# fly. The other values force every attached keyboard to be seen as that type.
KBTYPES = (
    'Auto-Adapt',
    'Apple',
    'Chromebook',
    'IBM',
    'Windows',
)

KBTYPE_DEFAULT = 'Auto-Adapt'

KBTYPE_LABELS = {
    'Auto-Adapt':   'Auto-Adapt*',
    'Apple':        'Apple',
    'Chromebook':   'Chromebook',
    'IBM':          'IBM',
    'Windows':      'Windows',
}

# The values that constitute an actual override, i.e. everything except
# 'Auto-Adapt'. UIs warn the user when one of these is selected. Derived
# rather than hand-listed so a new keyboard type cannot be added to KBTYPES
# and silently escape the warning.
KBTYPE_OVERRIDE_VALUES = tuple(kbtype for kbtype in KBTYPES if kbtype != KBTYPE_DEFAULT)

# Shown as a notification when an override is selected. Currently duplicated
# verbatim in the tray app; UIs substitute their own line separator ('\r'
# for some notification daemons).
KBTYPE_OVERRIDE_WARNING = (
    'Overriding keyboard type disables auto-adaptation.\n'
    'This is meant as a temporary fix only! See README.')

KBTYPE_GROUP = PrefChoiceGroup(
    attr_name='override_kbtype',
    group_label='Keyboard Type',
    values=KBTYPES,
    value_labels=KBTYPE_LABELS,
    default=KBTYPE_DEFAULT,
    help_title='Temporary Keyboard Type',
    help_text=(
        'Temporarily override the detected keyboard type without saving '
        'the setting.\n\n'
        'This is useful for testing different keyboard layouts or when '
        "the auto-detection doesn't work correctly for your hardware.\n\n"
        'See the FAQ page in the GitHub repo Wiki for more information '
        'about how to implement a permanent solution for a specific '
        'device.'),
)


# All choice groups, so a UI can iterate them uniformly instead of naming
# each one. Order is the tray icon menu's order (CapsLock Mode lives inside
# the tray's Preferences submenu; the other two are top-level submenus).
PREF_CHOICE_GROUPS = (
    CAPSLOCK_MODE_GROUP,
    OPTSPEC_LAYOUT_GROUP,
    KBTYPE_GROUP,
)

# End of file #
