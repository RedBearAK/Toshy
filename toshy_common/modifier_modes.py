"""
Canonical mode-string constants for special modifier-key mode settings.

toshy_common/modifier_modes.py

Single source of truth for the valid values of string-typed key mode
preferences (currently only `capslock_mode`). Imported by:

  - The Toshy config file, to validate `cnfg.capslock_mode` (loudly) and
    derive the per-event `ctx_caps_is_*` booleans in the context pre-check.
  - All three preference UIs (tray, GTK4, Tkinter), to build their radio
    groups from the same ordered tuple, display labels, and help texts.
  - The modmap region verifier test harness, to enumerate scenarios, so a
    newly added mode can never be silently untested.

Do not reorder existing entries casually: the UIs present the modes in
tuple order.
"""

__version__ = '20260715'

# Valid values for cnfg.capslock_mode, in UI display order.
CAPSLOCK_MODES = (
    'caps_is_caps',
    'caps_is_cmd',
    'caps_is_esc_and_cmd',
    'caps_is_esc_and_lctrl',
    'caps_is_esc_and_lctrl_role_swap',
    'caps_is_lctrl_role_swap',
)

CAPSLOCK_MODE_DEFAULT = 'caps_is_caps'

# Display labels for the preference UIs, keyed by mode string.
# Trailing '*' marks the default, matching the convention of other items.
CAPSLOCK_MODE_LABELS = {
    'caps_is_caps':                     'Caps is Caps*',
    'caps_is_cmd':                      'Caps is Cmd',
    'caps_is_esc_and_cmd':              'Caps is Esc & Cmd',
    'caps_is_esc_and_lctrl':            'Caps is Esc & LCtrl always',
    'caps_is_esc_and_lctrl_role_swap':  'Caps is Esc & LCtrl role swap',
    'caps_is_lctrl_role_swap':          'Caps is LCtrl role swap',
}

# Short help texts for UIs that can attach per-item help (GTK4 app).
CAPSLOCK_MODE_HELP = {
    'caps_is_caps': (
        'The Caps key keeps its normal identity: a CapsLock toggle. '
        'Physical Left Ctrl keeps its usual Toshy role (Super in GUI apps, '
        'Ctrl in terminals). This is the default.'),
    'caps_is_cmd': (
        'Held Caps acts as the Cmd key equivalent, in GUI apps and in '
        'terminals. No CapsLock toggle is available in this mode.'),
    'caps_is_esc_and_cmd': (
        'Tap Caps for Escape. Hold Caps (or use it in combos) for the Cmd '
        'key equivalent. Works in GUI apps and in terminals.'),
    'caps_is_esc_and_lctrl': (
        'Tap Caps for Escape. Hold Caps for a real (literal) Ctrl key, even '
        'in GUI apps, so native Linux Ctrl shortcuts respond (useful for '
        'Emacs in a GUI window). Physical Left Ctrl is unchanged.'),
    'caps_is_esc_and_lctrl_role_swap': (
        'Tap Caps for Escape. Hold Caps for Left Ctrl\'s usual Toshy role: '
        'Super in GUI apps, real Ctrl in terminals. The physical Left Ctrl '
        'key becomes the CapsLock toggle.'),
    'caps_is_lctrl_role_swap': (
        'Caps and Left Ctrl trade places. Caps takes over Left Ctrl\'s '
        'usual Toshy role (Super in GUI apps, real Ctrl in terminals), and '
        'the physical Left Ctrl key becomes the CapsLock toggle.'),
}

# Legacy boolean preference names replaced by capslock_mode. Used by the
# one-shot detect/notify/delete routine in the config file, and safe to
# delete (along with that routine) after a generous deprecation period.
CAPSLOCK_LEGACY_BOOL_NAMES = (
    'Caps2Cmd',
    'Caps2Esc_Cmd',
)

# End of file #
