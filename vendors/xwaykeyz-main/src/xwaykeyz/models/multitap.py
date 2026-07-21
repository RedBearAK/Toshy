# xwaykeyz/models/multitap.py
#
# Passive descriptor for multi-tap keymap actions, in the same spirit as
# Combo/Key/Keymap: constructed by the config, interpreted by transform.py.
# Holds no runtime state and touches no keymapper machinery; all counting,
# timing, and emission live in the MultiTap branch of handle_commands and
# its helpers in transform.py.
#
# Per-sequence runtime state in transform.py is keyed by descriptor object
# identity (each MultiTap call site in a keymap is one distinct object), so
# this class deliberately defines neither __eq__ nor __hash__.

__version__ = '20260721'

from collections.abc import Callable

from .key import Key
from .combo import Combo


MULTITAP_MAX_TAPS = 5


class MultiTap:
    """Multi-tap action descriptor: different actions for 1-5 rapid taps
    of the same keymap combo.

    Usage in a keymap (as the output/value side of a mapping):

        C("Shift-RC-t"): MultiTap(
            tap_1_action=C("C-n"),          # single tap (None blocks it)
            tap_2_action=some_function,     # double tap
            tap_3_action=[ST("x3!"), C("Enter")],
        ),

    Any tap level may be a Combo, a Key, a callable, a list of those, or
    None (no action at that level). Levels default to None, so gaps like
    "act only on 2 and 4 taps" work naturally. tap_1_action=None blocks
    the single-tap function of the combo.

    Timing: tap_interval (max gap between taps) and min_tap_delay (key
    repeat protection) resolve per sequence, highest priority first:
    explicit kwargs here, then any matching conditional timeouts() rule,
    then the global timeouts() values.
    """

    def __init__(self,
        tap_1_action: 'Combo | Key | list | Callable | None' = None,
        tap_2_action: 'Combo | Key | list | Callable | None' = None,
        tap_3_action: 'Combo | Key | list | Callable | None' = None,
        tap_4_action: 'Combo | Key | list | Callable | None' = None,
        tap_5_action: 'Combo | Key | list | Callable | None' = None,
        tap_interval: 'float | None' = None,
        min_tap_delay: 'float | None' = None):

        self.tap_actions: 'dict[int, Combo | Key | list | Callable | None]' = {
            1: tap_1_action,
            2: tap_2_action,
            3: tap_3_action,
            4: tap_4_action,
            5: tap_5_action,
        }

        if all(action is None for action in self.tap_actions.values()):
            raise ValueError(
                'MultiTap: all tap actions are None; define at least one '
                'of tap_1_action through tap_5_action')

        if tap_interval is not None and float(tap_interval) <= 0:
            raise ValueError(
                f'MultiTap: tap_interval must be positive, got {tap_interval}')
        if min_tap_delay is not None and float(min_tap_delay) <= 0:
            raise ValueError(
                f'MultiTap: min_tap_delay must be positive, got {min_tap_delay}')

        # None means "resolve from timeouts() at first tap of a sequence"
        self.tap_interval = None if tap_interval is None else float(tap_interval)
        self.min_tap_delay = None if min_tap_delay is None else float(min_tap_delay)

    def defined_levels(self) -> 'list[int]':
        """Tap counts that have an action defined (for debug output)."""
        return [n for n, action in self.tap_actions.items() if action is not None]

    def __repr__(self):
        levels = ','.join(str(n) for n in self.defined_levels())
        return f'MultiTap(levels=[{levels}])'


# End of file #
