"""
Regex patterns for the modmap region verifier.

Toshy/tests/modmap_verifier_rgx.py

Isolated in a dedicated module (never edited in place) per project policy,
since editing regex pattern literals directly risks corruption.
"""

import re

__version__ = '20260714'

# The SCAN_MARK lines bracketing the machine-verified modmap region in the
# config file. Deliberately NOT "SLICE_MARK": the setup script harvests
# SLICE_MARK regions from a user's old config during upgrades, which must
# never happen to this region.
scan_mark_start_rgx = re.compile(
    r'^###\s+SCAN_MARK_START: modmap_region\s+###', re.MULTILINE)
scan_mark_end_rgx = re.compile(
    r'^###\s+SCAN_MARK_END: modmap_region\s+###', re.MULTILINE)

# Registration calls anywhere in the config (for the out-of-region hygiene
# check). Group 1 = call name.
modmap_call_rgx = re.compile(
    r'^(modmap|multipurpose_modmap)\(', re.MULTILINE)

# End of file #
