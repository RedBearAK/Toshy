#!/usr/bin/env python3
"""
screenshot_shortcuts_config_example.py  (reference snippet, not installed)

The entire config-side footprint for detected screenshot shortcuts,
including the 4-then-Space window shift. All the complicated parts live
in toshy_common/screenshots/sshot_keymaps.py; the config supplies only what it
alone knows: the config-API callables, the environment info, the 'when'
condition, and (by call position) the keymap registration order.

Optional user overrides still go through the resolution module:

    from toshy_common.screenshots import set_custom_output
    set_custom_output('area_to_clipboard', 'C-Shift-F12')   # flameshot etc.
"""
__version__ = '20260801'


from toshy_common.screenshots import setup_screenshot_keymaps


# Call ABOVE any keymap still binding the same input combos (first
# registered keymap containing a combo wins). The config's globals()
# carries keymap, C, immediately, sleep, DESKTOP_ENV, and DE_MAJ_VER
# into the module under their usual names.
setup_screenshot_keymaps(globals(),
    when = lambda ctx: True,            # [?] GenGUI overrides condition
    # window_shift_esc_first = True,    # if per-DE testing shows the
                                        # area overlay eats the shortcut
)

# End of file #
