__name__ = "xwaykeyz"

__version__ = "1.25.0"

__description__ = "A smart, flexible key remapper for Linux/X11."

__doc__ = """
``xwaykeyz`` is a smart and flexible key remapper for Linux/X11.
Think ``xmodmap``, but new and improved!.

- Low-level library usage (`evdev` and `uinput`) allows remapping to work from
  the console all the way into X11 or Wayland (limited environment supported).
- High-level and incredibly flexible remapping mechanisms:
    - _per-application keybindings_ - bindings that change depending on the
      active X11 or Wayland application or window
    - _multiple stroke keybindings_ - `Ctrl+x Ctrl+c` could map to `Ctrl+q`
    - _very flexible output_ - `Ctrl-s` can type `:save` then hit enter
    - _stateful key combos_ - build Emacs style combos with shift/mark
    - _multipurpose bindings_ - a regular key can become a modifier when held
    - _arbitrary functions_ - a key combo can run custom Python function
"""
