# Using keyszer with Kinto release 1.2-13

## Uppdating your kinto.py config file

First, have a glace thru `UPGRADE_FROM_XKEYSNAIL.md`.

- TLDR, remove `imports` from the top.
- Fix `pass_through_key`, which has been removed.
- Add `bind` to tabbing key combos (for sticky tabbing).

**Replacing `pass_through_key`**

This never worked, and Kinto has been using it as an "ignore" helper.  Luckily we can patch thiswith a single line at the top:

```py
pass_through_key = ignore_key
```

**Adding `bind` for tabbing key combos**

You'll need to find any key combos used for tabbing and bind them if you want the switcher window to stay open as you hold down on `Cmd`:

```py
# before, inside `General GUI` block
K("RC-Tab"): K("Alt-Tab"),
K("RC-Shift-Tab"): K("Alt-Shift-Tab"),

# after
K("RC-Tab"): [bind, K("Alt-Tab")],
K("RC-Shift-Tab"): [bind, K("Alt-Shift-Tab")],
```

Note that you are replacing a single combo with an array of commands and adding `bind` as the first command in the sequence.


## Running as `root`

This is no longer recommended but can be enabled by passing `--very-bad-idea` to `keyszer`.  This may be required (short-term) for use with the existing release of Kinto.  See our `README` for best security practices.


## Quiet vs Verbose

`--quiet` is gone.  Quiet is now the default.  If you want verbose use `-v`.


## Updating your `xkeysnail.service`

You'll need to update this to reference the `keyszer` script and also update the arguments:

```sh
# before
ExecStart={sudo}/bin/bash -c '/usr/bin/xhost +SI:localuser:root && {homedir}/.config/kinto/killdups.sh && {xkeysnail} --quiet --watch {homedir}/.config/kinto/kinto.py'

#after
ExecStart={sudo}/bin/bash -c '/usr/bin/xhost +SI:localuser:root && {homedir}/.config/kinto/killdups.sh && {xkeysnail} --watch -c {homedir}/.config/kinto/kinto.py'
```

_This is not exact_ (since the above is from the template rather than the final file), you'll need to know what you're doing.  TLDR:

- don't pass `--quiet`
- the config file is passed with `-c` now
- replace any references to `xkeysnail` with `keyszer`
- you may need to source your `venv` if you're using Python's Venv
- you'll also need to update your `killdups.sh` script with the new executable name


Contributions to these instructions are welcome for any early adventurers.

For help: https://github.com/RedBearAK/xwaykeyz/issues/36







