"""
Terminal state control for the Toshy terminal menu.

toshy_common/terminal_menu/tmenu_term.py

Owns every piece of terminal state the menu changes, and guarantees it
all gets restored: termios raw mode, the alternate screen buffer, SGR
mouse reporting, and cursor visibility. Mouse reporting left enabled
after a crash makes the user's terminal unable to select text, which
looks like the tool broke their terminal — so cleanup is registered
with atexit AND run from the signal/exception paths in tmenu_main, and
restore() is safe to call any number of times.

Color output is disabled when stdout is not a TTY or NO_COLOR is set,
matching the convention in toshy_common/keycheck.py.
"""

__version__ = '20260804'

import os
import sys
import tty
import atexit
import shutil
import termios


_ALT_SCREEN_ON      = '\x1b[?1049h'
_ALT_SCREEN_OFF     = '\x1b[?1049l'
_CURSOR_HIDE        = '\x1b[?25l'
_CURSOR_SHOW        = '\x1b[?25h'
_MOUSE_ON           = '\x1b[?1000h\x1b[?1006h'
_MOUSE_OFF          = '\x1b[?1006l\x1b[?1000l'

CURSOR_HOME         = '\x1b[H'
CLEAR_TO_EOL        = '\x1b[K'
CLEAR_BELOW         = '\x1b[J'

_use_color          = sys.stdout.isatty() and not os.environ.get('NO_COLOR')

BOLD                = '\x1b[1m'     if _use_color else ''
DIM                 = '\x1b[2m'     if _use_color else ''
REVERSE             = '\x1b[7m'     if _use_color else ''
RED                 = '\x1b[31m'    if _use_color else ''
GREEN               = '\x1b[32m'    if _use_color else ''
YELLOW              = '\x1b[33m'    if _use_color else ''
CYAN                = '\x1b[36m'    if _use_color else ''
RESET               = '\x1b[0m'     if _use_color else ''


class TerminalController:
    """Enter/exit the menu's terminal modes with idempotent restore."""

    def __init__(self):
        self.saved_termios      = None
        self.entered            = False

    def enter(self):
        """Switch to raw mode, alt screen, hidden cursor, mouse reporting."""
        if self.entered:
            return
        stdin_fd = sys.stdin.fileno()
        self.saved_termios = termios.tcgetattr(stdin_fd)
        tty.setraw(stdin_fd)
        sys.stdout.write(_ALT_SCREEN_ON + _CURSOR_HIDE + _MOUSE_ON)
        sys.stdout.flush()
        self.entered = True
        atexit.register(self.restore)

    def restore(self):
        """Undo everything enter() did. Safe to call repeatedly."""
        if not self.entered:
            return
        self.entered = False
        try:
            sys.stdout.write(_MOUSE_OFF + _CURSOR_SHOW + _ALT_SCREEN_OFF)
            sys.stdout.flush()
        except (OSError, ValueError):
            pass
        if self.saved_termios is None:
            return
        try:
            termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, self.saved_termios)
        except (OSError, ValueError, termios.error):
            pass

    def suspend(self):
        """Temporarily restore the terminal (e.g. around a child process)."""
        self.restore()

    def resume(self):
        """Re-enter menu terminal modes after suspend()."""
        self.enter()


def get_terminal_size():
    """Return (columns, rows), tolerant of odd environments."""
    size = shutil.get_terminal_size(fallback=(80, 24))
    return size.columns, size.lines

# End of file #
