#!/usr/bin/env python3
"""
toshy_common/shortcut_detect/sc_det_fallback.py

Command fallback factory: builds keymap output callables that launch the
first candidate command found on PATH, for slots with no native binding
to emit. launch_detached() returns False when the executable is absent,
so an ordered candidate list doubles as version/tool detection with no
DE version logic required.
"""
__version__ = '20260803'

from subprocess import DEVNULL

from toshy_common.proc_launcher import launch_detached


def make_cmd_fallback_fn(cmd_candidates_lst: 'list[list[str]]'):
    """Build a keymap output callable trying candidates in order."""

    def _cmd_fallback(ctx):
        for cmd_lst in cmd_candidates_lst:
            if launch_detached(cmd_lst, stdout=DEVNULL, stderr=DEVNULL):
                return

    # Self-description for diagnostics (rendered by CLI check commands).
    _cmd_fallback.cmd_candidates_lst = cmd_candidates_lst
    return _cmd_fallback

# End of file #
