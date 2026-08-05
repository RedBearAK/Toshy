"""
Compiled regex patterns for the Toshy terminal menu input parser.

toshy_common/terminal_menu/tmenu_rgx.py

Kept in a dedicated module so the escape-sequence patterns never need
to be edited inside the larger logic modules.
"""

__version__ = '20260804'

import re


# SGR extended mouse report: ESC [ < button ; column ; row (M=press, m=release)
# Enabled by DECSET 1000 (basic tracking) + 1006 (SGR encoding). The SGR
# encoding is required so coordinates beyond column/row 223 don't wrap.
_rgx_sgr_mouse = re.compile(r'\x1b\[<(\d+);(\d+);(\d+)([Mm])')

# Any complete CSI sequence that is NOT an SGR mouse report; used to consume
# unrecognized sequences (e.g. focus events, unknown keys) without letting
# their bytes leak through as spurious character keys.
_rgx_csi_other = re.compile(r'\x1b\[[0-9;<=?]*[A-Za-z~]')

# End of file #
