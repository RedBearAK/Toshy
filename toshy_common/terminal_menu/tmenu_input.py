"""
Input parsing for the Toshy terminal menu.

toshy_common/terminal_menu/tmenu_input.py

Turns raw bytes read from stdin (in raw mode) into a list of simple
event tuples. Two event shapes:

    ('key',   name)                 name: 'up', 'down', 'pgup', 'pgdn',
                                          'home', 'end', 'left', 'right',
                                          'enter', 'space', 'esc', 'quit',
                                          or a single printable character
    ('mouse', kind, column, row)    kind: 'press', 'release',
                                          'wheel_up', 'wheel_down'

Keyboard interrupt bytes (Ctrl+C) become ('key', 'quit') because raw
mode disables ISIG, so the byte arrives on stdin instead of raising
KeyboardInterrupt. A lone ESC byte at the end of a chunk is treated as
the Esc key: a real escape sequence arrives as one chunk from the
terminal, so a dangling ESC means the user pressed the key itself.

Mouse hit-testing stays out of this module on purpose; it only reports
terminal coordinates (1-based, as the terminal sends them).
"""

__version__ = '20260804'

from toshy_common.terminal_menu.tmenu_rgx import _rgx_csi_other, _rgx_sgr_mouse


# CSI sequences for keys the menu responds to. Values are key names.
_CSI_KEYS_DCT = {
    '\x1b[A':   'up',
    '\x1b[B':   'down',
    '\x1b[C':   'right',
    '\x1b[D':   'left',
    '\x1b[H':   'home',
    '\x1b[F':   'end',
    '\x1b[1~':  'home',
    '\x1b[4~':  'end',
    '\x1b[5~':  'pgup',
    '\x1b[6~':  'pgdn',
}

_MOUSE_BUTTON_WHEEL_UP      = 64
_MOUSE_BUTTON_WHEEL_DOWN    = 65


def parse_input_bytes(data: bytes):
    """Parse one chunk of raw stdin bytes into a list of event tuples."""

    events_lst = []
    text = data.decode('utf-8', errors='replace')
    position = 0

    while position < len(text):
        char = text[position]

        if char != '\x1b':
            events_lst.append(_plain_char_event(char))
            position += 1
            continue

        # Escape-introduced: try SGR mouse first (most specific pattern).
        mouse_match = _rgx_sgr_mouse.match(text, position)
        if mouse_match:
            events_lst.append(_mouse_event(mouse_match))
            position = mouse_match.end()
            continue

        # Known CSI key sequences, longest first so '\x1b[1~' wins over '\x1b[1'.
        matched_key = None
        for sequence, key_name in _CSI_KEYS_DCT.items():
            if text.startswith(sequence, position):
                if matched_key is None or len(sequence) > len(matched_key[0]):
                    matched_key = (sequence, key_name)
        if matched_key:
            events_lst.append(('key', matched_key[1]))
            position += len(matched_key[0])
            continue

        # Any other complete CSI sequence: consume silently.
        other_match = _rgx_csi_other.match(text, position)
        if other_match:
            position = other_match.end()
            continue

        # Lone ESC (nothing recognizable follows in this chunk).
        events_lst.append(('key', 'esc'))
        position += 1

    return [event for event in events_lst if event is not None]


def _plain_char_event(char: str):
    if char == '\x03':                      # Ctrl+C in raw mode
        return ('key', 'quit')
    if char in ('\r', '\n'):
        return ('key', 'enter')
    if char == ' ':
        return ('key', 'space')
    if char == '\x7f':                      # Backspace: treat as collapse/back
        return ('key', 'left')
    if char.isprintable():
        return ('key', char.lower())
    return None


def _mouse_event(mouse_match):
    button      = int(mouse_match.group(1))
    column      = int(mouse_match.group(2))
    row         = int(mouse_match.group(3))
    press_char  = mouse_match.group(4)

    if button == _MOUSE_BUTTON_WHEEL_UP:
        return ('mouse', 'wheel_up', column, row)
    if button == _MOUSE_BUTTON_WHEEL_DOWN:
        return ('mouse', 'wheel_down', column, row)
    if press_char == 'M':
        return ('mouse', 'press', column, row)
    return ('mouse', 'release', column, row)

# End of file #
