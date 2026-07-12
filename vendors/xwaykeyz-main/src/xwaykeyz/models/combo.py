from collections.abc import Iterable
from enum import IntEnum, unique

from ordered_set import OrderedSet

from .key import Key
from .modifier import Modifier


@unique
class ComboHint(IntEnum):
    BIND = 1
    ESCAPE_NEXT_KEY = 2
    IGNORE = 3
    ESCAPE_NEXT_COMBO = 4

    def __str__(self):
        return self.__repr__()


class Combo:
    def __init__(self, modifiers, key):
        modifiers = modifiers or []

        if isinstance(modifiers, set):
            raise ValueError("modifiers needs ordered sequence, not a set")
        if isinstance(modifiers, Iterable):
            modifiers = OrderedSet(modifiers)
        elif isinstance(modifiers, Modifier):
            modifiers = OrderedSet([modifiers])
        else:
            raise ValueError("modifiers should be Iterable")

        if not isinstance(key, Key):
            raise ValueError("key should be a Key")

        self._modifiers = modifiers
        self._key = key

    @property
    def modifiers(self):
        return self._modifiers

    @property
    def key(self):
        return self._key

    def __eq__(self, other):
        if isinstance(other, Combo):
            return (
                set(self.modifiers) == set(other.modifiers)
                and self.key == other.key
            )
        else:
            return NotImplemented

    def __hash__(self):
        return hash((frozenset(self.modifiers), self.key))

    def __str__(self):
        return "-".join([str(mod) for mod in self.modifiers] + [self.key.name])

    def __repr__(self):
        return self.__str__()

    def with_modifier(self, modifiers):
        if isinstance(modifiers, Modifier):
            modifiers = {modifiers}
        return Combo(self.modifiers | modifiers, self.key)



class PreCorrectedCombo(Combo):
    """A Combo whose key is already correct for the active keyboard layout and
    must NOT be put through output de-correction again.

    The Phase 2 string/Unicode emitter builds its keystrokes from the per-layout
    symbol table, which already yields active-layout keycodes. Phase 1 output
    de-correction (`_decorrect_output_command` in transform.py) rewrites a
    matched-remap's key through the inverse correction map so XKB renders the
    intended symbol on a non-US layout. Running that over emitter output would
    double-correct it. This subclass is the marker the de-correction step checks
    for to leave such output untouched.

    It adds no behaviour: it is a plain Combo in every other respect, so it flows
    through `handle_commands` and `_output.send_combo` exactly like any Combo
    (the `isinstance(command, Combo)` branch still matches it), and it compares
    and hashes equal to a Combo with the same modifiers and key (equality is
    content-based and intentionally does not fork on pre-correction; immunity is
    decided by isinstance, not by equality)."""


# End of File #
