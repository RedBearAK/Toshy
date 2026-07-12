# define timeout for multipurpose_modmap
timeouts(
    multipurpose = 1,
    suspend = 1,
)

# [Global modemap] Change modifier keys as in xmodmap
modmap("default", {
    Key.CAPSLOCK: Key.LEFT_CTRL
})

# [Conditional modmap] Change modifier keys in certain applications
modmap("Emacs",{
    Key.RIGHT_CTRL: Key.ESC,
}, when = wm_class_match(r"Emacs"))

# [Multipurpose modmap] Give a key two meanings. A normal key when pressed and
# released, and a modifier key when held down with another key. See Xcape,
# Carabiner and caps2esc for ideas and concept.
multipurpose_modmap("default",
    # Enter is enter when pressed and released. Control when held down.
    {Key.ENTER: [Key.ENTER, Key.RIGHT_CTRL]}

    # Capslock is escape when pressed and released. Control when held down.
    # {Key.CAPSLOCK: [Key.ESC, Key.LEFT_CTRL]}
    # To use this example, you can't remap capslock with modmap.
)

# [Conditional multipurpose modmap] Multipurpose modmap in certain conditions,
# such as for a particular device.
multipurpose_modmap("Microsoft keyboard", {
    # Left shift is open paren when pressed and released.
    # Left shift when held down.
    Key.LEFT_SHIFT: [Key.KPLEFTPAREN, Key.LEFT_SHIFT],

    # Right shift is close paren when pressed and released.
    # Right shift when held down.
    Key.RIGHT_SHIFT: [Key.KPRIGHTPAREN, Key.RIGHT_SHIFT]
}, when = lambda ctx: ctx.device_name.startswith("Microsoft"))


# Keybindings for Firefox/Chrome
keymap("Firefox and Chrome", {
    # Ctrl+Alt+j/k to switch next/previous tab
    C("C-Alt-j"): C("C-TAB"),
    C("C-Alt-k"): C("C-Shift-TAB"),
    # Type C-j to focus to the content
    C("C-j"): C("C-f6")
}, when = wm_class_match(r"Firefox|Google-chrome"))

# Keybindings for Zeal https://github.com/zealdocs/zeal/
keymap("Zeal", {
    # Ctrl+s to focus search area
    C("C-s"): C("C-k"),
}, when = wm_class_match(r"Zeal"))

# Emacs-like keybindings in non-Emacs applications

keymap("Emacs-like keys", {
    # Cursor
    C("C-b"): with_mark(C("left")),
    C("C-f"): with_mark(C("right")),
    C("C-p"): with_mark(C("up")),
    C("C-n"): with_mark(C("down")),
    C("C-h"): with_mark(C("backspace")),
    # Forward/Backward word
    C("Alt-b"): with_mark(C("C-left")),
    C("Alt-f"): with_mark(C("C-right")),
    # Beginning/End of line
    C("C-a"): with_mark(C("home")),
    C("C-e"): with_mark(C("end")),
    # Page up/down
    C("Alt-v"): with_mark(C("page_up")),
    C("C-v"): with_mark(C("page_down")),
    # Beginning/End of file
    C("Alt-Shift-comma"): with_mark(C("C-home")),
    C("Alt-Shift-dot"): with_mark(C("C-end")),
    # Newline
    C("C-m"): C("enter"),
    C("C-j"): C("enter"),
    C("C-o"): [C("enter"), C("left")],
    # Copy
    C("C-w"): [C("C-x"), set_mark(False)],
    C("Alt-w"): [C("C-c"), set_mark(False)],
    C("C-y"): [C("C-v"), set_mark(False)],
    # Delete
    C("C-d"): [C("delete"), set_mark(False)],
    C("Alt-d"): [C("C-delete"), set_mark(False)],
    # Kill line
    C("C-k"): [C("Shift-end"), C("C-x"), set_mark(False)],
    # Undo
    C("C-slash"): [C("C-z"), set_mark(False)],
    C("C-Shift-ro"): C("C-z"),
    # Mark
    C("C-space"): set_mark(True),
    C("C-Alt-space"): with_or_set_mark(C("C-right")),
    # Search
    C("C-s"): C("F3"),
    C("C-r"): C("Shift-F3"),
    C("Alt-Shift-key_5"): C("C-h"),
    # Cancel
    C("C-g"): [C("esc"), set_mark(False)],
    # # Escape the next non-modifier key (held modifiers are dropped/released first)
    # # Use-case for this is unknown? Contact if you know why this would be useful.
    # C("C-q"): escape_next_key,
    # Escape the next [mod(s)]+key combo seen
    C("C-q"): escape_next_combo,
    # C-x YYY
    C("C-x"): {
        # C-x h (select all)
        C("h"): [C("C-home"), C("C-a"), set_mark(True)],
        # C-x C-f (open)
        C("C-f"): C("C-o"),
        # C-x C-s (save)
        C("C-s"): C("C-s"),
        # C-x k (kill tab)
        C("k"): C("C-f4"),
        # C-x C-c (exit)
        C("C-c"): C("C-q"),
        # cancel
        C("C-g"): ignore_key,
        # C-x u (undo)
        C("u"): [C("C-z"), set_mark(False)],
    }
}, when = lambda ctx: ctx.wm_class not in ("Emacs", "URxvt"))

