"""
Canonical mode-string constants for special modifier-key mode settings.

toshy_common/modifier_modes.py

Single source of truth for the valid values of string-typed key mode
preferences (currently only `capslock_mode`). Imported by:

  - The Toshy config file, to validate `cnfg.capslock_mode` (loudly) and
    derive the per-event `ctx_caps_is_*` booleans in the context pre-check.
  - All three preference UIs (tray, GTK4, Tkinter), to build their radio
    groups from the same ordered tuple and display labels.
  - The modmap region verifier test harness, to enumerate scenarios, so a
    newly added mode can never be silently untested.

Do not reorder existing entries casually: the UIs present the modes in
tuple order.
"""

__version__ = '20260714'

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
CAPSLOCK_MODE_LABELS = {
    'caps_is_caps':                     'CapsLock acts as CapsLock (default)',
    'caps_is_cmd':                      'CapsLock acts as Cmd key',
    'caps_is_esc_and_cmd':              'CapsLock is Esc (tap) and Cmd (hold)',
    'caps_is_esc_and_lctrl':            'CapsLock is Esc (tap) and Ctrl (hold)',
    'caps_is_esc_and_lctrl_role_swap':  'Esc (tap), swap roles with Left Ctrl (hold)',
    'caps_is_lctrl_role_swap':          'Swap roles with Left Ctrl key',
}

# Legacy boolean preference names replaced by capslock_mode. Used by the
# one-shot detect/notify/delete routine in the config file, and safe to
# delete (along with that routine) after a generous deprecation period.
CAPSLOCK_LEGACY_BOOL_NAMES = (
    'Caps2Cmd',
    'Caps2Esc_Cmd',
)

# End of file #
