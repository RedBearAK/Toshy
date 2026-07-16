#!/usr/bin/env python3
"""
toshy_common/keycheck.py

Interactive key identity checker for Toshy ('toshy-keycheck' command).

Launches the keymapper (xwaykeyz) directly in verbose mode as a child
process, performing the same preparation steps as the verbose-start
script (stop services, kill stray keymapper processes, start companion
D-Bus services, X11 xhost fix). It then parses the verbose log stream,
showing a single "card" in the terminal with the real hardware identity
of the last released key, its remapped identity, and which modmap or
multi-purpose modmap was responsible. The card is replaced each time a
key is released, so the tool naturally ends up showing multi-purpose
modifier keys (last released in any combo) with both of their potential
identities and how the press actually resolved (tap, second key press,
or hold timeout).

Uses the terminal's alternate screen buffer, so the original shell
contents and prompt are undisturbed after exit (Ctrl+C or Q).

NOTE: Running this tool stops the Toshy systemd services. They are NOT
restarted on exit; the user is reminded to run 'toshy-services-restart'
(or use the tray icon).

Expects to run inside the Toshy venv (the 'toshy-keycheck' launcher
script activates it), so the 'xwaykeyz' command is found on PATH.
"""

import os
import sys
import tty
import time
import shutil
import signal
import termios
import threading
import subprocess

from collections import deque


def _bootstrap_package_on_path():
    """Put the parent of the 'toshy_common' package dir on sys.path.

    The 'toshy-keycheck' launcher exports PYTHONPATH for the absolute
    import below, but this makes the module also runnable directly
    (python3 keycheck.py) from inside the package directory.
    """

    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if not os.path.isdir(os.path.join(parent_dir, 'toshy_common')):
        return
    if parent_dir in sys.path:
        return
    sys.path.insert(0, parent_dir)


_bootstrap_package_on_path()

from toshy_common.keycheck_rgx import (
    _rgx_in_key,
    _rgx_kbtype,
    _rgx_modmap,
    _rgx_on_key,
    _rgx_resolving,
    _rgx_multi_modmap,
)


__version__ = '20260715'


# ANSI bits (kept minimal; disabled when stdout is not a tty or NO_COLOR set)
_use_color = sys.stdout.isatty() and not os.environ.get('NO_COLOR')

_BOLD    = '\x1b[1m'  if _use_color else ''
_DIM     = '\x1b[2m'  if _use_color else ''
_CYAN    = '\x1b[36m' if _use_color else ''
_YELLOW  = '\x1b[33m' if _use_color else ''
_RESET   = '\x1b[0m'  if _use_color else ''

_ALT_SCREEN_ON  = '\x1b[?1049h'
_ALT_SCREEN_OFF = '\x1b[?1049l'
_CURSOR_HIDE    = '\x1b[?25l'
_CURSOR_SHOW    = '\x1b[?25h'
_CURSOR_HOME    = '\x1b[H'
_CLEAR_TO_EOL   = '\x1b[K'
_CLEAR_BELOW    = '\x1b[J'

_TAIL_LINES_ON_ERROR = 20

_LOCAL_BIN = os.path.join(os.path.expanduser('~'), '.local', 'bin')
_TOSHY_CFG_DIR = os.path.join(os.path.expanduser('~'), '.config', 'toshy')

_COMPANION_DBUS_COMMANDS = [
    'toshy-kwin-dbus-service',
    'toshy-cosmic-dbus-service',
    'toshy-wlroots-dbus-service',
]

_STALE_KEYMAPPER_PATTERNS = [
    'bin/xwaykeyz',
    'bin/keyszer',
    'bin/xkeysnail',
]


class KeyRecord:
    """Accumulated identity info for one physical key, from press to release."""

    def __init__(self, inkey: str):
        self.inkey              = inkey
        self.modmap_out         = None      # simple modmap output identity
        self.modmap_name        = None      # responsible modmap name
        self.multi_momentary    = None      # multi-purpose tap identity
        self.multi_held         = None      # multi-purpose hold identity
        self.multi_held_mod     = None      # modifier role name of hold identity
        self.multi_name         = None      # responsible multi-modmap name
        self.resolved_by_key    = None      # second key that forced resolution
        self.saw_repeat         = False


class LogStreamParser:
    """Consumes verbose log lines, maintains per-key state, triggers renders.

    The render trigger is the 'on_key ... release' line, which immediately
    follows the '(II) in X (release)' line and states the RESOLVED identity
    of the released key regardless of how resolution happened.
    """

    def __init__(self, render_fn):
        self.render_fn          = render_fn
        self.records            = {}       # inkey name -> KeyRecord
        self.device_name        = None
        self.kbd_type           = None
        self.awaiting_release   = None      # inkey name awaiting on_key release

    def feed_line(self, line: str):
        line = line.rstrip('\n')

        match = _rgx_in_key.match(line)
        if match:
            self._handle_in_key(match)
            return

        match = _rgx_on_key.match(line)
        if match:
            self._handle_on_key(match)
            return

        match = _rgx_multi_modmap.match(line)
        if match:
            self._handle_multi_modmap(match)
            return

        match = _rgx_modmap.match(line)
        if match:
            self._handle_modmap(match)
            return

        match = _rgx_resolving.match(line)
        if match:
            self._handle_resolving(match)
            return

        match = _rgx_kbtype.match(line)
        if match:
            self.kbd_type       = match.group(1)
            self.device_name    = match.group(2)
            return

    def _handle_in_key(self, match):
        inkey, action = match.group(1), match.group(2)

        if action == 'press':
            # Un-rendered release still pending from a previous key whose
            # 'on_key release' line never arrived? Render it with what we have.
            if self.awaiting_release is not None:
                self._render_release(self.awaiting_release, None, None)
            # Fresh record on every press so stale info never lingers.
            self.records[inkey] = KeyRecord(inkey)
            return

        if action == 'repeat':
            record = self.records.get(inkey)
            if record is not None:
                record.saw_repeat = True
            return

        # action == 'release': the resolved identity arrives on the very
        # next 'on_key' line; remember which input key it belongs to.
        self.awaiting_release = inkey

    def _handle_on_key(self, match):
        name, mod_role, action = match.group(1), match.group(2), match.group(3)

        if action != 'release':
            return
        if self.awaiting_release is None:
            return

        inkey = self.awaiting_release
        self._render_release(inkey, name, mod_role)

    def _handle_multi_modmap(self, match):
        inkey = match.group(1)
        record = self.records.get(inkey)
        if record is None:
            record = KeyRecord(inkey)
            self.records[inkey] = record
        record.multi_momentary  = match.group(2)
        record.multi_held       = match.group(3)
        record.multi_held_mod   = match.group(4)
        record.multi_name       = match.group(5)

    def _handle_modmap(self, match):
        inkey = match.group(1)
        record = self.records.get(inkey)
        if record is None:
            record = KeyRecord(inkey)
            self.records[inkey] = record
        record.modmap_out       = match.group(2)
        record.modmap_name      = match.group(3)

    def _handle_resolving(self, match):
        inkey = match.group(1)
        record = self.records.get(inkey)
        if record is None:
            return
        record.resolved_by_key = match.group(4)

    def _render_release(self, inkey, resolved_name, resolved_mod_role):
        self.awaiting_release = None
        record = self.records.pop(inkey, None)
        if record is None:
            record = KeyRecord(inkey)
        self.render_fn(self, record, resolved_name, resolved_mod_role)


def build_card_lines(parser, record, resolved_name, resolved_mod_role):
    """Build the display lines for one released key."""

    lines = []
    lines.append(f'{_BOLD}  TOSHY KEYCHECK{_RESET}'
                 f'{_DIM}   (Ctrl+C to quit){_RESET}')
    lines.append('')

    if parser.device_name:
        lines.append(f'  Device:    {parser.device_name}')
    if parser.kbd_type:
        lines.append(f'  Kbd type:  {parser.kbd_type}')
    if parser.device_name or parser.kbd_type:
        lines.append('')

    lines.append(f'  Key pressed:   {_BOLD}{_CYAN}{record.inkey}{_RESET}')
    lines.append('')

    if record.multi_momentary is not None:
        held_role = f'  ({record.multi_held_mod} mod)' if record.multi_held_mod else ''
        lines.append(f'  Multi-purpose key   {_DIM}[{record.multi_name}]{_RESET}')
        lines.append(f'    tap   →  {_BOLD}{record.multi_momentary}{_RESET}')
        lines.append(f'    hold  →  {_BOLD}{record.multi_held}{_RESET}{_DIM}{held_role}{_RESET}')
        lines.append('')
        lines.extend(build_multi_resolution_lines(record, resolved_name))
    elif record.modmap_out is not None:
        lines.append(f'  Modmap:   {record.inkey}  →  {_BOLD}{record.modmap_out}{_RESET}'
                     f'   {_DIM}[{record.modmap_name}]{_RESET}')
        lines.append('')
        shown = resolved_name if resolved_name else record.modmap_out
        lines.append(f'  Acting as:     {_BOLD}{_YELLOW}{shown}{_RESET}')
    else:
        shown = resolved_name if resolved_name else record.inkey
        if shown == record.inkey:
            lines.append(f'  Identity unchanged {_DIM}(no modmap matched){_RESET}')
        else:
            lines.append(f'  Acting as:     {_BOLD}{_YELLOW}{shown}{_RESET}')

    lines.append('')
    lines.append(f'{_DIM}  Card updates when a key is {_RESET}{_BOLD}RELEASED{_RESET}'
                 f'{_DIM}, not when pressed.{_RESET}')
    return lines


def build_multi_resolution_lines(record, resolved_name):
    """Lines describing how a multi-purpose key's press actually resolved."""

    lines = []

    if resolved_name is None:
        lines.append(f'  Resolved as:   {_DIM}(not captured){_RESET}')
        return lines

    lines.append(f'  Resolved as:   {_BOLD}{_YELLOW}{resolved_name}{_RESET}')

    if resolved_name == record.multi_momentary:
        lines.append(f'  Resolved by:   quick tap (momentary identity)')
        return lines

    if record.resolved_by_key is not None:
        lines.append(f'  Resolved by:   second key press ({record.resolved_by_key})')
        return lines

    lines.append(f'  Resolved by:   hold timeout')
    return lines


def render_card(lines):
    """Redraw the card in place: home cursor, clear each line, clear below."""

    out = [_CURSOR_HOME]
    for line in lines:
        out.append(line + _CLEAR_TO_EOL + '\n')
    out.append(_CLEAR_BELOW)
    sys.stdout.write(''.join(out))
    sys.stdout.flush()


def render_waiting_card():
    lines = [
        f'{_BOLD}  TOSHY KEYCHECK{_RESET}'
        f'{_DIM}   (Ctrl+C to quit){_RESET}',
        '',
        '  Starting keymapper in verbose mode...',
        '',
        '  Waiting for the first key press.',
        '',
        f'{_DIM}  Tap a key to see its identity. For multi-purpose keys,{_RESET}',
        f'{_DIM}  hold past the timeout, or hold and tap a second key.{_RESET}',
        '',
        f'{_DIM}  Card updates when a key is {_RESET}{_BOLD}RELEASED{_RESET}'
        f'{_DIM}, not when pressed.{_RESET}',
    ]
    render_card(lines)


def confirm_launch() -> bool:
    print()
    print('  toshy-keycheck will:')
    print('    - STOP the Toshy systemd services')
    print('    - launch the keymapper in VERBOSE mode in the background')
    print('    - show the identity of each key you press')
    print()
    print('  After exiting, Toshy services will remain STOPPED.')
    print("  Restart them with 'toshy-services-restart' or from the tray icon.")
    print()
    try:
        answer = input('  Proceed? [y/N] ')
    except (EOFError, KeyboardInterrupt):
        print()
        return False
    return answer.strip().lower() in ('y', 'yes')


def stop_toshy_services():
    """Stop the Toshy systemd services (script exits harmlessly on
    non-systemd systems, mirroring the verbose-start flow)."""

    services_stop_cmd = os.path.join(_LOCAL_BIN, 'toshy-services-stop')
    if not os.path.exists(services_stop_cmd):
        return
    subprocess.run([services_stop_cmd], check=False)


def kill_stale_keymapper_processes():
    for pattern in _STALE_KEYMAPPER_PATTERNS:
        subprocess.run(['pkill', '-f', pattern], check=False)


def launch_companion_dbus_services():
    """Start the compositor companion D-Bus services (each stops itself
    if it is not applicable to the current session)."""

    for command_name in _COMPANION_DBUS_COMMANDS:
        command_path = os.path.join(_LOCAL_BIN, command_name)
        if not os.path.exists(command_path):
            continue
        subprocess.Popen(
            [command_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )


def apply_x11_xhost_fix():
    """Overcome a possible strange and rare problem connecting to X display."""

    if os.environ.get('XDG_SESSION_TYPE') != 'x11':
        return
    if shutil.which('xhost') is None:
        return
    subprocess.run(['xhost', '+local:'], check=False,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def spawn_keymapper_child():
    """Launch xwaykeyz in verbose mode, line-buffered, in its own session.

    Returns the Popen object, or None with an error printed if the
    keymapper command is not available.
    """

    keymapper_cmd = shutil.which('xwaykeyz')
    if keymapper_cmd is None:
        print("  Error: 'xwaykeyz' command not found on PATH.")
        print('  (Is the Toshy venv active? Use the toshy-keycheck launcher.)')
        return None

    config_path = os.path.join(_TOSHY_CFG_DIR, 'toshy_config.py')
    if not os.path.exists(config_path):
        print(f"  Error: Toshy config not found at '{config_path}'.")
        return None

    # Same flags as the verbose-start script; stdbuf forces line
    # buffering through the pipe so the display updates immediately.
    return subprocess.Popen(
        ['stdbuf', '-oL', keymapper_cmd, '--flush', '-w', '-v', '-c', config_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        text=True,
        errors='replace',
        start_new_session=True,
    )


def start_stdin_drain_thread():
    """Silently consume terminal input so probe keystrokes never scribble
    into the display or pile up for the shell after exit."""

    def drain_loop():
        while True:
            try:
                data = os.read(sys.stdin.fileno(), 4096)
            except (OSError, ValueError):
                return
            if not data:
                return

    thread = threading.Thread(target=drain_loop, daemon=True)
    thread.start()


def terminate_child(child):
    if child is None:
        return
    if child.poll() is not None:
        return
    try:
        os.killpg(child.pid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError):
        pass
    try:
        child.wait(timeout=3)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(child.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
    # Belt and suspenders, mirroring toshy-config-stop.
    subprocess.run(['pkill', '-f', 'bin/xwaykeyz'], check=False)


def main() -> int:
    if '-y' not in sys.argv and '--yes' not in sys.argv:
        if not confirm_launch():
            print('  Canceled.')
            return 0

    stdin_is_tty = sys.stdin.isatty()
    saved_termios = None
    child = None
    tail_lines = deque(maxlen=_TAIL_LINES_ON_ERROR)
    child_died = False

    # SIGTERM gets the same cleanup path as Ctrl+C.
    signal.signal(signal.SIGTERM, lambda signum, frame: (_ for _ in ()).throw(KeyboardInterrupt))

    try:
        # Same preparation steps as the verbose-start script.
        stop_toshy_services()
        kill_stale_keymapper_processes()
        launch_companion_dbus_services()
        time.sleep(1)   # pause to let D-Bus service(s) start up
        apply_x11_xhost_fix()

        child = spawn_keymapper_child()
        if child is None:
            return 1

        sys.stdout.write(_ALT_SCREEN_ON + _CURSOR_HIDE)
        sys.stdout.flush()

        if stdin_is_tty:
            saved_termios = termios.tcgetattr(sys.stdin.fileno())
            tty.setcbreak(sys.stdin.fileno())    # keeps ISIG, so Ctrl+C works
            start_stdin_drain_thread()

        def render_fn(parser, record, resolved_name, resolved_mod_role):
            render_card(build_card_lines(parser, record, resolved_name, resolved_mod_role))

        parser = LogStreamParser(render_fn)
        render_waiting_card()

        while True:
            line = child.stdout.readline()
            if line == '':
                child_died = True
                break
            tail_lines.append(line.rstrip('\n'))
            parser.feed_line(line)

    except KeyboardInterrupt:
        pass
    finally:
        terminate_child(child)
        if saved_termios is not None:
            termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, saved_termios)
        sys.stdout.write(_CURSOR_SHOW + _ALT_SCREEN_OFF)
        sys.stdout.flush()

    if child_died:
        print()
        print('  The keymapper process exited unexpectedly. Last output lines:')
        print()
        for line in tail_lines:
            print(f'    {line}')

    print()
    print('  toshy-keycheck exited. Toshy services are still STOPPED.')
    print("  Run 'toshy-services-restart' (or use the tray icon) to")
    print('  resume normal Toshy operation.')
    print()
    return 1 if child_died else 0


if __name__ == '__main__':
    sys.exit(main())


# End of file #
