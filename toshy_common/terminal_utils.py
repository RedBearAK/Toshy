__version__ = "20260201"

"""
Terminal utilities for Toshy applications.

Simple terminal emulator detection and command execution with optional
desktop environment awareness for optimal terminal selection.
"""

import os
import shutil
import subprocess

from toshy_common.logger import debug


local_bin = os.path.join(os.path.expanduser('~'), '.local', 'bin')
if local_bin not in os.environ.get('PATH', '').split(os.pathsep):
    os.environ['PATH'] = local_bin + os.pathsep + os.environ.get('PATH', '')

class TerminalNotFoundError(RuntimeError):
    """Raised when no suitable terminal emulator can be found"""
    pass


# List of common terminal emulators in descending order of preference.
# Each element is a tuple: (command_name, args_list, supported_DEs)
TERMINAL_APPS = [
    ('gnome-terminal',          ['--'],     ['gnome', 'unity', 'cinnamon']     ),
    ('ptyxis',                  ['--'],     ['gnome', 'unity', 'cinnamon']     ),
    ('konsole',                 ['-e'],     ['kde']                            ),
    ('xfce4-terminal',          ['-e'],     ['xfce']                           ),
    ('mate-terminal',           ['-e'],     ['mate']                           ),
    ('qterminal',               ['-e'],     ['lxqt']                           ),
    ('lxterminal',              ['-e'],     ['lxde']                           ),
    ('terminology',             ['-e'],     ['enlightenment']                  ),
    ('cosmic-term',             ['-e'],     ['cosmic']                         ),
    ('io.elementary.terminal',  ['-e'],     ['pantheon']                       ),
    ('kitty',                   ['-e'],     []                                 ),
    ('alacritty',               ['-e'],     []                                 ),
    ('tilix',                   ['-e'],     []                                 ),
    ('terminator',              ['-e'],     []                                 ),
    ('xterm',                   ['-e'],     []                                 ),
    ('rxvt',                    ['-e'],     []                                 ),
    ('urxvt',                   ['-e'],     []                                 ),
    ('st',                      ['-e'],     []                                 ),
    ('kgx',                     ['-e'],     []                                 ),  # GNOME Console
]


def run_cmd_lst_in_terminal(command_list, desktop_env: str=None):
    """
    Execute a command in the most appropriate terminal emulator.
    
    Tries to find a matching terminal for the desktop environment first,
    then falls back to any available terminal.
    
    Args:
        command_list: List of strings - command and arguments to execute
        desktop_env: String or None - desktop environment (e.g., 'gnome', 'kde')
                    If None, skips DE-specific terminal selection
        
    Returns:
        Boolean - True if command was successfully launched, False otherwise
    """

    # Validate input
    if not isinstance(command_list, list) or not all(isinstance(item, str) for item in command_list):
        debug('run_cmd_lst_in_terminal() expects a list of strings.')
        return False

    if not command_list:
        debug('run_cmd_lst_in_terminal() received empty command list.')
        return False

    def _try_terminal(terminal_cmd, args_list):
        """Try to run command in a specific terminal. Returns True if successful."""
        terminal_path = shutil.which(terminal_cmd)
        if not terminal_path:
            return False

        full_command = [terminal_path] + args_list + command_list
        try:

            subprocess.Popen(full_command)

            debug(f"Successfully launched command in {terminal_cmd}")
            return True
        except subprocess.SubprocessError as e:
            debug(f'Error launching {terminal_cmd}: {e}')
            return False

    # Resolve bare command names to absolute paths so terminal emulators
    # can find commands even if the launched shell lacks ~/.local/bin on PATH
    if '/' not in command_list[0]:
        resolved = shutil.which(command_list[0])
        if resolved:
            command_list = [resolved] + command_list[1:]

    # First pass: Try DE-specific terminals if desktop_env is provided
    if desktop_env:
        desktop_env = desktop_env.casefold()
        for terminal_cmd, args_list, de_list in TERMINAL_APPS:
            if desktop_env in de_list:
                if _try_terminal(terminal_cmd, args_list):
                    return True

    # Second pass: Try any available terminal
    for terminal_cmd, args_list, _ in TERMINAL_APPS:
        if _try_terminal(terminal_cmd, args_list):
            return True

    # If we reach here, no terminal was found
    message = 'No suitable terminal emulator could be found.'
    debug(f"ERROR: {message} (terminal_utils)")
    raise TerminalNotFoundError(message)
