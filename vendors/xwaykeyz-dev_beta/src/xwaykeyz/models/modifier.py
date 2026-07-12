from .key import Key


class Modifier:
    """represents a keyboard combo modifier, such as Shift or Cmd"""

    _BY_KEY = {}
    _MODIFIERS = {}
    _KEY_TO_NAME = {}           # Cache for keycode -> modifier name lookups
    _IDS = iter(range(100))

    def __init__(self, name, aliases, key=None, keys=None):
        cls = type(self)
        self._id = next(cls._IDS)
        self.name = name
        self.aliases = aliases
        keys = key or keys
        if isinstance(keys, Key):
            keys = [keys]
        self.keys = keys
        if len(self.keys) == 1:
            key = self.keys[0]
            if key in cls._BY_KEY:
                raise ValueError(
                    f"modifier {name} may not be assigned {key},"
                    " already assigned to another modifier"
                )
            cls._BY_KEY[key] = self
            cls._KEY_TO_NAME[key] = self.name  # Update cache of modifier names
        if name in cls._MODIFIERS:
            raise ValueError(f"existing modifier named {name} already exists")
        cls._MODIFIERS[name] = self
        setattr(Modifier, name, self)

    def __str__(self):
        return self.aliases[0]

    def __repr__(self):
        return self.aliases[0] + f"<Key.{self.keys[0]}>"

    def __eq__(self, other):
        return self._id == other._id

    def __hash__(self):
        return self._id

    def is_specific(self):
        return len(self.keys) == 1

    def get_keys(self):
        return self.keys

    def get_key(self):
        return self.keys[0]

    def to_left(self):
        try:
            return getattr(Modifier, "L_" + self.name)
        except AttributeError:
            return None

    def to_right(self):
        try:
            return getattr(Modifier, "R_" + self.name)
        except AttributeError:
            return None

    @classmethod
    def from_key(cls, key):
        return cls._BY_KEY[key]

    @classmethod
    def all_aliases(cls):
        mods = cls._MODIFIERS.values()
        return [alias for mod in mods for alias in mod.aliases]

    @classmethod
    def is_key_modifier(cls, key):
        return key in cls._BY_KEY

    @classmethod
    def from_alias(cls, alias):
        for mod in cls._MODIFIERS.values():
            if alias in mod.aliases:
                return mod
        return None

    @classmethod
    def get_modifier_name(cls, key):
        """Get the modifier name for a key, or None if not a modifier"""
        return cls._KEY_TO_NAME.get(key)


# create all the default modifiers we ship with
Modifier("R_CONTROL", aliases=["RCtrl", "RC"], key=Key.RIGHT_CTRL)
Modifier("L_CONTROL", aliases=["LCtrl", "LC"], key=Key.LEFT_CTRL)
Modifier("CONTROL", aliases=["Ctrl", "C"], keys=[Key.LEFT_CTRL, Key.RIGHT_CTRL])
Modifier("R_ALT", aliases=["RAlt", "RA", "ROpt", "ROption"], key=Key.RIGHT_ALT)
Modifier("L_ALT", aliases=["LAlt", "LA", "LOpt", "LOption"], key=Key.LEFT_ALT)
Modifier("ALT", aliases=["Alt", "A", "Opt", "Option"], keys=[Key.LEFT_ALT, Key.RIGHT_ALT])
Modifier("R_SHIFT", aliases=["RShift"], key=Key.RIGHT_SHIFT)
Modifier("L_SHIFT", aliases=["LShift"], key=Key.LEFT_SHIFT)
Modifier("SHIFT", aliases=["Shift"], keys=[Key.LEFT_SHIFT, Key.RIGHT_SHIFT])
# purposely we do not have M, MA, or ML to give some distance from the fact
# that these use to be aliases for Alt, not Meta... they may come back in
# the future
Modifier(
    "R_META",
    aliases=["RSuper", "RWin", "RCommand", "RCmd", "RMeta"],
    key=Key.RIGHT_META,
)
Modifier(
    "L_META",
    aliases=["LSuper", "LWin", "LCommand", "LCmd", "LMeta"],
    key=Key.LEFT_META,
)
Modifier(
    "META",
    aliases=["Super", "Win", "Command", "Cmd", "Meta"],
    keys=[Key.LEFT_META, Key.RIGHT_META],
)

# Fn is either invisible to the OS (on some laptop hardware) or it's just a
# normal key, but as a normal key it likely should be flagged as a modifier
# based on how it's typically used
Modifier("FN", aliases=["Fn"], key=Key.KEY_FN)
