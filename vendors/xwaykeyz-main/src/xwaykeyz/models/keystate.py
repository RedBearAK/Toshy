# src/xwaykeyz/models/keystate.py

import time as _time
from dataclasses import dataclass, field, replace

from .action import Action
from .key import Key


@dataclass
class Keystate:
    # The actual REAL key pressed on input device
    inkey: Key
    # Current action state: PRESS, REPEAT, or RELEASE
    action: Action
    # Copy of previous keystate, for tracking state changes
    prior: "Keystate"           = None
    # Timestamp when keystate was created or updated
    time: float                 = field(default_factory=_time.time)
    # The key we modmapped to (may differ from inkey)
    key: Key                    = None
    # The modifier we may modmap to (multi-key) if used
    # as part of a combo or held for a certain time period
    multikey: Key               = None
    # Whether this key is currently suspended inside the
    # transform engine waiting for other input
    suspended: bool             = False
    # Whether this key is a multipurpose key (tap vs hold behavior)
    is_multi: bool              = False
    # Whether this key's press has been sent to output device
    exerted_on_output: bool     = False
    # If this keystate was spent by executing a combo
    spent: bool                 = False
    # Track if any other key was pressed while this multikey was held
    # Used for event-based tap-vs-hold decision making
    other_key_pressed_while_held: bool  = False

    def copy(self):
        return replace(self)

    # Renamed from "is_pressed" to reduce naming 
    # overlap with Action.is_pressed property.
    @property
    def key_is_pressed(self):
        # return self.action == Action.PRESS or self.action == Action.REPEAT
        # Use central "source of truth" in Action for whether key is pressed.
        return self.action.is_pressed

    def resolve_as_momentary(self):
        # self.key = self.key # NOP
        self.is_multi = False
        self.multikey = False

    def resolve_as_modifier(self):
        self.key = self.multikey
        self.is_multi = False
        self.multikey = False

# End of file #
