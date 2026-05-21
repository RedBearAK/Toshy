__version__ = '20260520'
"""
Toshy helper: fire-and-forget subprocess launcher with auto-reap.

File: toshy_common/proc_launcher.py

subprocess.Popen() leaves children as zombies until someone calls wait().
subprocess.run() blocks until the child exits. For fire-and-forget launches
(e.g., a zenity dialog from a key-combo handler), neither is what we want.

launch_detached() runs subprocess.run() inside a daemon thread: the caller
returns immediately; the thread blocks on the child and reaps it cleanly;
the daemon thread evaporates afterward. No SIGCHLD handling, no zombies.

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

    All keyword arguments are forwarded to subprocess.run().
    """
    if isinstance(args, (list, tuple)):
        cmd_name = args[0] if args else None
    else:
        cmd_name = args

    if not cmd_name or not shutil.which(cmd_name):
        return False

    def _run_and_reap():
        try:
            subprocess.run(args, **kwargs)
        except Exception:
            error(f"launch_detached failed:\n{traceback.format_exc()}")

    threading.Thread(target=_run_and_reap, daemon=True).start()
    return True


# End of file #
