"""Regex patterns for toshy_common/xkb_check.py

toshy_common/xkb_check_patterns.py
"""

import re


# Pattern to extract XKB options from COSMIC's RON-format xkb_config file.
# Matches:  options: Some("compose:rctrl, grp:toggle")
# Captures the contents inside the quotes.
cosmic_xkb_options_rgx = re.compile(
    r'options\s*:\s*Some\(\s*"([^"]*)"\s*\)'
)

# Pattern to extract XKBOPTIONS value from /etc/default/keyboard.
# Matches:  XKBOPTIONS=compose:rctrl,ctrl:nocaps
# Also handles optional quoting (single or double).
etc_default_kb_options_rgx = re.compile(
    r'^XKBOPTIONS\s*=\s*["\']?([^"\'#\n]*)["\']?',
    re.MULTILINE,
)

# Pattern to extract xkb-options array from gsettings output.
# gsettings outputs like: ['compose:rctrl', 'grp:toggle']
# Capture the entire bracketed list contents.
gsettings_xkb_options_rgx = re.compile(
    r"\[([^\]]*)\]"
)

# Pattern to extract individual option strings from a gsettings list.
# Matches each quoted string like 'compose:rctrl' inside the brackets.
gsettings_option_item_rgx = re.compile(
    r"'([^']*)'"
)

# End of file #
