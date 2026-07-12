# Upgrading from xkeysnail

## Briefly

### Remove preamble `imports` and `coding comments`

Remove most preamble import statements. These are no longer necessary.  The full `xwaykeyz` API as well as `re` (for regex) are available now by default, automatically.

_These lines can all be removed:_

```py
# -*- coding: utf-8 -*-
import re
from xkeysnail.transform import *
```

### `LM`, `RM`, and `M` (Alt) no longer supported

Replace these with the clearler `Alt` equivalents:

- `LM` => `LAlt`
- `RM` => `RAlt`
- `M` => `Alt`

### Remove any `launch` macros

There are questions of whether this ever worked properly and it needed to be rethought in any case to be far more reliable and secure.

If you need this functionality please see [issue 44](https://github.com/RedBearAK/xwaykeyz/issues/44) for how to implement it.

### Remove `pass_through_key`

This feature never worked and has been removed.  If you want to pass a key, just repeat the combo on both sides:

```py
keymap("default", {
	K("Alt-9"): K("Alt-9") # passing a key thru
})
```

If you want to ignore a key, simply use `None` or the new `ignore_key`:

```py
keymap("default", {
	K("Alt-0"): ignore_key,
	K("Alt-1"): None
})
```

Both `Alt-0` and `Alt-1` will now be silently ignored.


## Rewriting your config using the new xwaykeyz APIs

Key things to remember:

- Lose the verbose `define_` prefix
- Every modmap and keymap must now be named
- Conditions are optional and passed using the `when` named argument
- Conditions are now all passed a context object (see the `README`)

**timeout**

```py
# before
define_timeout(1) # multipurpose timeout

# after
timeouts(multipurpose = 1)
```

**modmaps**

```py
# before
define_modmap({
    Key.CAPSLOCK: Key.LEFT_CTRL
})

# after
modmap("caps as control", {
    Key.CAPSLOCK: Key.LEFT_CTRL
})
```

**conditional modmaps**

Now just a `modmap` with a `when` argument.

```py
# before
define_conditional_modmap(re.compile(r'Emacs'), {
    Key.RIGHT_CTRL: Key.ESC,
})

# after
modmap("Emacs", {
    Key.RIGHT_CTRL: Key.ESC,
}, when = wm_class_match(r"Emacs"))
```

**multi-purpose modmaps**

```py
# before
define_multipurpose_modmap(
    {Key.ENTER: [Key.ENTER, Key.RIGHT_CTRL]}
)

#after
multipurpose_modmap("enter as control",
    {Key.ENTER: [Key.ENTER, Key.RIGHT_CTRL]}
)
```

**conditional multipurpose modmaps**

Now just a `multipurpose_modmap` with a `when` argument.

```py
# before
define_conditional_multipurpose_modmap(
	lambda wm_class, device_name: device_name.startswith("Microsoft"), {
   	Key.LEFT_SHIFT: [Key.KPLEFTPAREN, Key.LEFT_SHIFT],
   	Key.RIGHT_SHIFT: [Key.KPRIGHTPAREN, Key.RIGHT_SHIFT]
})

# after
multipurpose_modmap("Microsoft keyboard combos", {
		Key.LEFT_SHIFT: [Key.KPLEFTPAREN, Key.LEFT_SHIFT],
		Key.RIGHT_SHIFT: [Key.KPRIGHTPAREN, Key.RIGHT_SHIFT]
	}, when = lambda ctx: ctx.device_name.startswith("Microsoft")
)
```

**keymaps**

```py
#before
define_keymap(re.compile(r"^Zeal$"), {
    K("C-s"): K("C-k"),
}, "Zeal")

#after
keymap("Zeal", {
   K("C-s"): K("C-k") },
   when = wm_class_match(r"^Zeal$")
)
```
