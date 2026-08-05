__version__ = '20260805'
"""
Toshy helper: fire-and-forget subprocess launcher with auto-reap.

File: toshy_common/proc_launcher.py

subprocess.Popen() leaves children as zombies until someone calls wait().
subprocess.run() blocks until the child exits. For fire-and-forget launches
(e.g., a zenity dialog from a key-combo handler), neither is what we want.

launch_detached() runs subprocess.run() inside a daemon thread: the caller
returns immediately; the thread blocks on the child and reaps it cleanly;
the daemon thread evaporates afterward. No SIGCHLD handling, no zombies.

The child's stdout and stderr default to DEVNULL: a fire-and-forget child
has no business writing to the caller's terminal (e.g., a launched GUI
app scribbling its debug output into the terminal menu's screen). Callers
that genuinely want to see the child's output must pass stdout/stderr
explicitly. To see a launched app's own output, run it directly in a
dedicated terminal instead (e.g., 'toshy-gui', 'toshy-tray').

Exceptions raised inside the launcher thread are routed through the
xwaykeyz logger so they integrate with the rest of the verbose/journal
output instead of dumping raw to stderr.
"""


import shutil
import threading
import traceback
import subprocess

from xwaykeyz.lib.logger import error


def launch_detached(args, **kwargs):
    """
    Launch a process in the background; it auto-reaps when it exits.

    Returns True if the command was found on PATH and a launcher thread
    was started. Returns False if shutil.which() couldn't find it.

    All keyword arguments are forwarded to subprocess.run(). The child's
    stdout and stderr default to subprocess.DEVNULL unless the caller
    passes them explicitly.
    """
    if isinstance(args, (list, tuple)):
        cmd_name = args[0] if args else None
    else:
        cmd_name = args

    if not cmd_name or not shutil.which(cmd_name):
        return False

    # Quiet by default: without this, a bare call lets the child inherit
    # the parent's tty and write over it (setdefault preserves any
    # explicitly passed values, including None).
    kwargs.setdefault('stdout', subprocess.DEVNULL)
    kwargs.setdefault('stderr', subprocess.DEVNULL)

    def _run_and_reap():
        try:
            subprocess.run(args, **kwargs)
        except Exception:
            error(f"launch_detached failed:\n{traceback.format_exc()}")

    threading.Thread(target=_run_and_reap, daemon=True).start()
    return True


# End of file #
