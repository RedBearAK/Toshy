# toshy_common/kblayout_detect/__init__.py
"""Keyboard-layout detection package.

The public API is unchanged from the former single-module form, so existing
imports such as

    from toshy_common.kblayout_detect import KeyboardLayoutDetector

keep resolving exactly as before. Internally the implementation is split into
one module per backend (kbld_backend_*.py) plus a registry (kbld_registry.py)
that selects among them; consumers never need to know which backend ran.
"""

__version__ = '20260608'

from toshy_common.kblayout_detect.kbld_registry import (
    KeyboardLayoutDetector,
    select_backend,
)


__all__ = [
    'KeyboardLayoutDetector',
    'select_backend',
]


# End of file #
