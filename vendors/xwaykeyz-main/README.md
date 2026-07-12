# xwaykeyz - a smart key remapper for Linux (X11 and Wayland)

<!-- [![latest version](https://badgen.net/pypi/v/keyszer?label=beta)](https://github.com/RedBearAK/xwaykeyz/releases)
[![python 3.10](https://badgen.net/badge/python/3.10/blue)]()
[![license](https://badgen.net/badge/license/GPL3/keyszer?color=cyan)](https://github.com/RedBearAK/xwaykeyz/blob/main/LICENSE)
[![code quality](https://badgen.net/lgtm/grade/g/RedBearAK/xwaykeyz/js?label=code+quality)](https://lgtm.com/projects/g/RedBearAK/xwaykeyz/?mode=list)
[![discord](https://badgen.net/badge/icon/discord?icon=discord&label&color=pink)](https://discord.gg/nX6qSC8mer) -->

<!-- [![vulnerabilities](https://badgen.net/snyk/RedBearAK/xwaykeyz)](https://snyk.io/test/github/RedBearAK/xwaykeyz?targetFile=package.json) -->

[![open issues](https://badgen.net/github/open-issues/RedBearAK/xwaykeyz?label=issues)](https://github.com/RedBearAK/xwaykeyz/issues)
[![help welcome issues](https://badgen.net/github/label-issues/RedBearAK/xwaykeyz/help%20welcome/open)](https://github.com/RedBearAK/xwaykeyz/issues?q=is%3Aopen+is%3Aissue+label%3A%22help+welcome%22)
[![good first issue](https://badgen.net/github/label-issues/RedBearAK/xwaykeyz/good%20first%20issue/open)](https://github.com/RedBearAK/xwaykeyz/issues?q=is%3Aopen+is%3Aissue+label%3A%22good+first+issue%22)
![build and CI status](https://badgen.net/github/checks/RedBearAK/xwaykeyz)


## Forked from keyszer

The `xwaykeyz` keymapper is a smart key remapper for Linux (and X11) written in Python. It's similar to `xmodmap` but allows far more flexible remappings. Several Wayland environments are supported, but some of the Wayland environments require the assistance of Toshy, a project that uses this keymapper to provide Mac-like keyboard shortcut remapping. See the [Toshy README](https://github.com/RedBearAK/toshy#currently-working-desktop-environments-or-window-managers) for a full list of the supported Wayland environments when `xwaykeyz` is installed via Toshy. The Toshy installer will accept a special `--barebones-config` argument that will leave you with a clean config file without any of the Mac-like remapping, so Toshy can also be used as just a management interface to more easily work with the keymapper while Toshy provides some of the Wayland support components. 

This project was forked from [`keyszer`](https://github.com/joshgoebel/keyszer), which currently has no Wayland support, just like `xkeysnail`, and `keyszer` was in turn forked from [`xkeysnail`](https://github.com/mooz/xkeysnail), which no longer seems to be actively maintained. 

Most of the references in this README to `keyszer` will be updated at some point to be more relevant for `xwaykeyz`. 

Feel free to pronounce `xwaykeyz` however you want: Ex-Way-Keys, Sway-Keys, or Zway-Keyzzzzzz... (Or maybe Chewy-Keyz?!)

### How does it work?

Xwaykeyz works at quite a low level, close to the hardware.  It grabs input directly from the kernel's [`evdev`](https://www.freedesktop.org/wiki/Software/libevdev/) input devices ( `/dev/input/event*`) and then creates an emulated [`uinput`](https://www.kernel.org/doc/html/v4.12/input/uinput.html) virtual keyboard device to inject those inputs back into the kernel.  During this process the input stream is transformed on the fly as necessary to remap keys. As a side effect of how it works, the keymapper has no idea what your keyboard layout/language is, and this can cause small or large problems for non-US layout users. The only fix for this currently is modifying the `key.py` key definition file, which works fine in many cases where only a few keys need to be swapped. 

Note that the problem with non-US layouts is generally restricted to keys or shortcuts that get remapped by the config, so general typing is not affected, and if your config doesn't happen to remap a key that is different from the typical US layout, this issue may never really affect your usage of the keymapper. It is highly variable how much of a problem this is. 

Some progress has been made attempting to use `xkbcommon` to be able to change the key definitions according to the user's specified layout, but there is a lot of work still not done to make that happen. It's even more difficult to try to get the user's layout changes on-the-fly, for users who need to switch between multiple layouts. 


**Upgrading from xkeysnail**

- Some configuration changes will be needed.
- A few command line arguments have changed.
- For xkeysnail 0.4.0 see [UPGRADING_FROM_XKEYSNAIL.md](https://github.com/RedBearAK/xwaykeyz/blob/main/UPGRADE_FROM_XKEYSNAIL.md).
- For xkeysnail (Kinto variety) see [USING_WITH_KINTO.md](https://github.com/RedBearAK/xwaykeyz/blob/main/USING_WITH_KINTO.md) and [Using with Kinto v1.2-13](https://github.com/RedBearAK/keyszer/issues/36).

> [!NOTE]  
> It is highly recommended to to consider migrating from Kinto to [Toshy](https://github.com/RedBearAK/toshy), since Toshy is intrinsically designed to work with this particular fork of the original `xkeysnail` keymapper used by Kinto, and Toshy components are currently required for supporting some of the Wayland environments. 

#### Key Highlights

- Low-level library usage (`evdev` and `uinput`) allows remapping to work from the console all the way into X11 (or Wayland).
- High-level and incredibly flexible remapping mechanisms:
    - _per-application keybindings_ - bindings that change depending on the active X11 application or window
    - _multiple stroke keybindings_ - `Ctrl+x Ctrl+c` could map to `Ctrl+q`
    - _very flexible output_ - `Ctrl-s` could type out `:save`, and then hit enter
    - _stateful key combos_ - build Emacs style combos with shift/mark
    - _multipurpose bindings_ - a regular key can become a modifier when held
    - _arbitrary functions_ - a key combo can run custom Python function (as user)


**New Features (since xkeysnail 0.4.0)**

- simpler and more flexible configuration scripting APIs
- better debugging tools
  - configurable `EMERGENCY EJECT` hotkey
  - configurable `DIAGNOSTIC` hotkey
- fully supports running as semi-privileged user (using `root` is now deprecated)
- adds `include` to allow config to pull in other Python files
- adds `throttle_delays` to allow control of output speed of macros/combos
- adds `immediately` to nested keymaps (initial action)
- adds `Command` and `Cmd` aliases for Super/Meta modifier
    - `Meta` alias removed due to confusion with old refs to `Alt` key
- add `C` combo helper (eventually to replace `K`)
- supports custom modifiers via `add_modifier` (such as `Hyper`)
- supports `Fn` as a potential modifier (on hardware where it works)
- adds `bind` helper to support persistent holds across multiple combos
  - most frequently used for macOS style `Cmd-Tab` app switching
- adds `--check` for checking the config file for issues
- adds `wm_name` context for all conditionals (PR #40)
- adds `device_name` context for all conditionals (including keymaps)
- (fix) `xmodmap` cannot be used until some keys are first pressed on the emulated output
- (fix) ability to avoid unintentional Alt/Super false keypresses in many setups (suspend)
- (fix) fixes multi-combo nested keymaps (vs Kinto's `xkeysnail`)
- (fix) properly cleans up pressed keys before termination
- individually configurable timeouts (`multipurpose` and `suspend`)
- (fix) removed problematic `launch` macro
- (fix) suspend extra keys during sequential sequences to create less key "noise"
- (fix) handle X Display errors without crashing or bugging out

**New Features (since forking from `keyszer`)**

- Support for several Wayland environments when installed via [Toshy](https://github.com/RedBearAK/toshy)
- Without Toshy, `xwaykeyz` natively supports only:

    - **X11/Xorg sessions** _[works with any X window manager via `Xlib`]_
    - **Hyprland** - _[via `hyprpy`, or the `wlroots` method]_
    - **Pantheon** - _[via D-Bus queries to the Gala WM]_
    - **Sway** - _[via `i3ipc`, or the `wlroots` method]_

- With Toshy, `xwaykeyz` can support many more Wayland environments:
    - **X11/Xorg sessions** (with any desktop environment/window manager)
    - **Cinnamon 6.0 or later** - _[uses Toshy custom shell extension]_
    - **COSMIC desktop environment** - _[uses Toshy D-Bus service]_
    - **GNOME 3.38 or later** - _[needs 3rd-party shell extension]_
    - **Hyprland** - _[via `hyprpy` or the `wlroots` method]_
    - **Niri** - _[via the `wlroots` method]_
    - **Plasma 5 (KDE)** - _[uses Toshy KWin script and D-Bus service]_
    - **Plasma 6 (KDE)** - _[uses Toshy KWin script and D-Bus service]_
    - **Qtile** - _[via the `wlroots` method]_
    - **Sway** - _[via `i3ipc` or the `wlroots` method]_
    - **Wayland compositors with `zwlr_foreign_toplevel_manager_v1` interface**
        - See [Wiki article](https://github.com/RedBearAK/toshy/wiki/Wlroots-Based-Wayland-Compositors.md) on Toshy repo for usage of this method with unknown compositors that may be compatible
    - Full list and requirements kept updated in [Toshy README](https://github.com/RedBearAK/toshy#currently-working-desktop-environments-or-window-managers)

- (fix) Avoided high CPU usage while holding a key (by ignoring "repeats" by default)

- (enh) Added API to specify devices from inside the config file (instead of CLI arg)


***

## WARNING: Everything below this section may need to be updated!

This section will slowly move down the README as I update each section of the README to reflect that this is a README for `xwaykeyz` which has been forked from `keyszer` and renamed. 

***


---

## Installation

Requires **Python 3**.

### From source

Just download the source and install.

    git clone https://github.com/RedBearAK/xwaykeyz.git
    cd xwaykeyz
    pip3 install --user --upgrade .


### For testing/hacking/contributing

Using a Python `venv` might be the simplest way to get started:

    git clone https://github.com/RedBearAK/xwaykeyz.git
    cd xwaykeyz
    python -m venv .venv
    source .venv/bin/activate
    pip3 install -e .
    ./bin/xwaykeyz -c config_file


## System Requirements

Xwaykeyz requires read/write access to:

- `/dev/input/event*` - to grab input from your `evdev` input devices
- `/dev/uinput` - to provide an emulated keyboard to the kernel


### Running as a semi-privileged user

It's best to create an entirely isolated user to run the keymapper.  Group or ACL based permissions can be used to provide this user access to the necessary devices.  You'll need only a few `udev` rules to ensure that the input devices are all given correct permissions.


#### ACL based permissions (narrow, more secure)

First, lets make a new user:

    sudo useradd keymapper


...then use udev and ACL to grant our new user access:

Manually edit `/etc/udev/rules.d/90-keymapper-acl.rules` to include the following:

    KERNEL=="event*", SUBSYSTEM=="input", RUN+="/usr/bin/setfacl -m user:keymapper:rw /dev/input/%k"
    KERNEL=="uinput", SUBSYSTEM=="misc", RUN+="/usr/bin/setfacl -m user:keymapper:rw /dev/uinput"


...or do it by copypasting these lines into a shell:

    cat <<EOF | sudo tee /etc/udev/rules.d/90-keymapper-acl.rules
    KERNEL=="event*", SUBSYSTEM=="input", RUN+="/usr/bin/setfacl -m user:keymapper:rw /dev/input/%k"
    KERNEL=="uinput", SUBSYSTEM=="misc", RUN+="/usr/bin/setfacl -m user:keymapper:rw /dev/uinput"
    EOF


#### Group based permissions (slightly wider, less secure)

Many distros already have an input group; if not, you can create one.  Next, add a new user that's a member of that group:

    sudo useradd keymapper -G input


...then use udev to grant our new user access (via the `input` group):

Manually edit `/etc/udev/rules.d/90-keymapper-input.rules` to include the following:

    SUBSYSTEM=="input", GROUP="input"
    KERNEL=="uinput", SUBSYSTEM=="misc", GROUP="input"


...or do it by copypasting these lines into a shell:

    cat <<EOF | sudo tee /etc/udev/rules.d/90-keymapper-input.rules
    SUBSYSTEM=="input", GROUP="input"
    KERNEL=="uinput", SUBSYSTEM=="misc", GROUP="input"
    EOF


#### systemd

For a sample systemd service file for running Keyszer as a service please see [keyszer.service](contrib/redhat/keyszer.service).


### Running as the Active Logged in User

This may be appropriate in some limited development scenarios, but is not recommended.  Giving the active, logged in user access to `evdev` and `uinput` potentially allows all keystrokes to be logged and could allow a malicious program to take over (or destroy) your machine by injecting input into a Terminal session or other application.

It would be better to open a terminal, `su` to a dedicated `keymapper` user and then run Keyszer inside that context, as shown earlier.


### Running as `root`

_Don't do this, it's dangerous, and unnecessary._  A semi-privileged user with access to only the necessary input devices is a far better choice.


## Usage

    keyszer


A successful startup should resemble:

    xwaykeyz v1.3.1
    (--) CONFIG: /home/yourusername/.config/xwaykeyz/config.py
    (+K) Grabbing Apple, Inc Apple Keyboard (/dev/input/event3)
    (--) Ready to process input.


**Specifying the environment**

Xwaykeyz internally has multiple "window context providers", to get the application class and window title in X11/Xorg and the various Wayland environments it supports. For the keymapper to know which of the providers to use, there is an environment API function that can be used to inject the necessary information into the keymapper at startup. 

```py
environ_api(
    session_type = 'session_type', # This will be 'x11' or 'wayland'
    wl_compositor = 'a_wayland_compositor', # 'wlroots', 'kwin_wayland', 'muffin', 'mutter', etc. 
)
```

For X11/Xorg, the desktop environment argument in this API is unnecessary, and ignored if provided (set to `None` internally), and then the keymapper will use the X11/Xorg window context provider. For Wayland, it is usually essential to specify the desktop environment or window manager name in order to pick the correct window context provider inside the keymapper. There are now several different Wayland providers for specific DEs/WMs, and one (`wlroots`) that may be able to cover a dozen or more less common Wayland compositors (e.g., Niri, Qtile, and similar). 

With the [Toshy](https://github.com/RedBearAK/toshy) project that uses `xwaykeyz`, there is an environment module that the config file uses to grab all the relevant details about the user's environment. This allows Toshy to automatically adapt to moving from one DE or WM to another (on the same Linux system). The user in most cases never has to specify anything about their environment. This Toshy [environment module](https://github.com/RedBearAK/toshy/blob/main/lib/env.py) is frequently updated to identify even more DEs/WMs automatically. 

The reason the environment scraping module from Toshy is not integrated directly into the keymapper itself is primarily because the main `keyszer` dev did not want to deal with its complexity when I introduced it. Which was not entirely irrational or unwise. It was more involved than I had predicted, to make it mostly reliable on multiple Linux distros, and able to correctly detect many different desktop environments. And it is still evolving. 

If the user does not use multiple desktop environments (or window managers), it is perfectly fine to specify the environment statically with the API function call in the config file. 


**Limiting Devices**

Limit remapping to specific devices using either a command-line option (`--devices`) with one or more device path or device name arguments, or with the `devices_api()` function from inside the config file. The results will be the same. 

With `--devices` CLI option:

    keyszer --devices /dev/input/event3 'Topre Corporation HHKB Professional'

The full path or complete device name may be used.  Device name is usually better to avoid USB device numbering jumping around after a reboot, etc...

With the `devices_api()` API function in the config file:

```py
devices_api(
    only_devices = [
        'Some Device Name',
        'Other Device Name',
        '/dev/input/event3', # Path or name can be used, but paths can change
    ]
)
```


**Other CLI Options:**

- `-c`, `--config` - location of the configuration file
- `-w`, `--watch` - watch for new keyboard devices to hot-plug
- `-v` - increase verbosity greatly (to help with debugging)
- `--list-devices` - list out all available input devices


## Configuration

By default we look for the configuration in `~/.config/xwaykeyz/config.py`. You can override this location using the `-c`/`--config` switch.  The configuration file is written in Python.
For an example configuration please see [`example/config.py`](https://github.com/RedBearAK/xwaykeyz/blob/main/example/config.py).


The configuration API:

- `timeouts(multipurpose, suspend)`
- `throttle_delays(key_pre_delay_ms, key_post_delay_ms)`
- `environ_api(session_type = 'session_type', wl_compositor = 'wayland_compositor')` - See above
- `devices_api(only_devices=['List of Device Names','One or more devices'])` - See above
- `wm_class_match(re_str)`
- `not_wm_class_match(re_str)`
- `add_modifier(name, aliases, key/keys)`
- `modmap(name, map, when_conditional)`
- `multipurpose_modmap(name, map, when_conditional)`
- `keymap(name, map, when_conditional)`
- `conditional(condition_fn, map)` - used to wrap maps, applying them conditionally
- `dump_diagnostics_key(key)`
- `emergency_eject_key(key)`
- `include(relative_filename)`

### `include(relative_filename)`

Include a sub-configuration file into the existing config.  This file is loaded and executed at the point of inclusion and shares the same global scope as the existing config. These files should be present in the same directory as your main configuration.

```py
include("os.py")
include("apps.py")
include("deadkeys.py")
```

### `timeouts(...)`

Configures the timing behavior of various aspects of the keymapper.

- `multipurpose` - The number of seconds before a held multi-purpose key is assumed to be a modifier (even in the absence of other keys).
- `suspend` - The number of seconds modifiers are "suspended" and withheld from the output waiting to see whether if they are part of a combo or if they may be the actual intended output.


Defaults:

```py
timeouts(
    multipurpose = 1,
    suspend = 1,
)
```

### `throttle_delays(...)`

Configures the speed of virtual keyboard keystroke output to deal with issues that occur in various situations with the timing of modifier key presses and releases being misinterpreted. 

- `key_pre_delay_ms` - The number of milliseconds to delay the press-release keystroke of the "normal" key after pressing modifier keys. 
- `key_post_delay_ms` - The number of milliseconds to delay the next key event (modifier release) after the "normal" key press-release event.

Defaults:

```py
throttle_delays(
    key_pre_delay_ms    = 0,    # default: 0 ms, range: 0 to 150 ms, suggested: 1-50 ms
    key_post_delay_ms   = 0,    # default: 0 ms, range: 0 to 150 ms, suggested: 1-100 ms
)
```

Use the throttle delays if you are having the following kinds of problems: 

- Shortcut combos seeming to behave unreliably, sometimes as if the unmapped shortcut (or part of the unmapped shortcut) is being pressed at the same time.
- Macros of sets of keystrokes, or strings or Unicode sequences processed by the keymapper into keystrokes, having various kinds of failures, such as: 
    - Missing characters
    - Premature termination of macro
    - Shifted or uppercase characters coming out as unshifted/lowercase
    - Unshifted or lowercase characters coming out as shifted/uppercase
    - Unicode sequences failing to complete and create the desired Unicode character

Suggested values to try if you are in a virtual machine and having major problems with even common shortcut combos:  

- key_pre_delay_ms: 40
- key_post_delay_ms: 70

The post delay seems a little more effective in testing, but your situation may be different. For a bare-metal install where you are just having a few glitches in macro output, try much smaller delays: 

- key_pre_delay_ms: 0.1
- key_post_delay_ms: 0.5

These are just examples that have worked fairly well in current testing on machines that have had these issues. 


### `dump_diagnostics_key(key)`

Configures a key that when hit will dump additional diagnostic information to STDOUT.

```py
dump_diagnostics_key(Key.F15)  # default
```

### `emergency_eject_key(key)`

Configures a key that when hit will immediately terminate keyszer; useful for development, recovering from bugs, or badly broken configurations.

```py
emergency_eject_key(Key.F16)  # default
```



### `add_modifier(name, aliases, key/keys)`

Allows you to add custom modifiers and then map them to actual keys.

```py
add_modifier("HYPER", aliases = ["Hyper"], key = Key.F24)
```

_Note:_ Just adding `HYPER` doesn't necessarily make it work with your software, you may still need to configure X11 setup to accept the key you choose as the "Hyper" key.


### `wm_class_match(re_str)`

Helper to make matching conditionals (and caching the compiled regex) just a tiny bit simpler.

```py
keymap("Firefox",{
    # ... keymap here
}, when = wm_class_match("^Firefox$"))
```


### `not_wm_class_match(re_str)`

The negation of `wm_class_match`, matches only when the regex does NOT match.


### `modmap(name, mappings, when_conditional = None)`

Maps a single physical key to a different key.  A default modmap will always be overruled by any conditional modmaps that apply.  `when_conditional` can be passed to make the modmap conditional.  The first modmap found that includes the pressed key and matches the `when_conditional` will be used to remap the key.

```py
modmap("default", {
    # mapping caps lock to left control
    Key.CAPSLOCK: Key.LEFT_CTRL
})
```

If you don't create a default (non-conditional) modmap a blank one is created for you.  For `modmap` both sides of the pairing will be `Key` literals (not combos).


### `multipurpose_modmap(name, mappings)`

Used to bestow a key with multiple-purposes, both for regular use and for use as a modifier.

```py
multipurpose_modmap("default",
    # Enter is enter if pressed and immediately released...
    # ...but Right Control if held down and paired with other keys.
    {Key.ENTER: [Key.ENTER, Key.RIGHT_CTRL]}
)
```


### `keymap(name, mappings)`

Defines a keymap of input combos mapped to output equivalents.

```py
keymap("Firefox", {
    # when Cmd-S is input instead send Ctrl-S to the output
    C("Cmd-s"): C("Ctrl-s"),
}, when = lambda ctx: ctx.wm_class == "Firefox")
```

Because of the `when` conditional this keymap will only apply for Firefox.


The argument `mappings` is a dictionary in the form of `{ combo: command, ...}` where `combo` and `command` take following forms:

- `combo`: Combo to map, specified by `K(combo_str)`
    - For the syntax of combo specifications, see [Combo Specifications](#combo-specifications).
- `command`: one of the following
    - `K(combo_str)`: Type a specific key combo to the output.
    - `[command1, command2, ...]`: Execute multiple commands sequentially.
    - `{ ... }`: Sub-keymap. Used to define [Multiple Stroke Keys](#multiple-stroke-keys).
    - `escape_next_key`: Escape the next (non-modifier) key pressed. Held modifiers are dropped!
    - `escape_next_combo`: Escapes the next [mod(s)]+key combo seen. Does NOT drop modifiers.
    - `ignore_key`: Ignore the key/combo that is pressed next. (often used to disable native combos)
    - `bind`: Bind an input and output modifier together such that the output is not lifted until the input is.
    - arbitrary function: The function is executed and the returned value (if any) is used as a command.

The argument `name` specifies the keymap name. Every keymap has a name - using `default` is suggested for a non-conditional keymap.


### `conditional(fn, map)`

Applies a map conditionally, only when the `fn` function evaluates `True`.  The below example is a modmap that is only active when the current `WM_CLASS` is `Terminal`.

```py
conditional(
    lambda ctx: ctx.wm_class == "Terminal",
    modmap({
        # ...
    })
)
```

The `context` object passed to the `fn` function has several attributes:

- `wm_class` - the WM_CLASS of the [input] focused X11 window
- `wm_name` - the WM_NAME of the [input] focused X11 window
- `device_name` - name of the device where an input originated
- `capslock_on` - state of CapsLock (boolean)
- `numlock_on` - state of NumLock (boolean)

_Note:_ The same conditional `fn` can always be passed directly to `modmap` using the `when` argument.

---

#### Marks

TODO: need docs (See issue #8)


#### Combo Specifications

The Combo specification in a keymap is written in the form of `C("(<Modifier>-)*<Key>")`.

`<Modifier>` is one of the following:

- `C` or `Ctrl` -> Control key
- `Alt` -> Alt key
- `Shift` -> Shift key
- `Super`, `Win`, `Command`, `Cmd`, `Meta` -> Super/Windows/Command key
- `Fn` -> Function key (on supported keyboards)

You can specify left/right modifiers by adding the prefixes `L` or `R`.

`<Key>` is any key whose name is defined in [`key.py`](https://github.com/RedBearAK/xwaykeyz/blob/main/keyszer/models/key.py).

Some combo examples:

- `C("LC-Alt-j")`: left Control, Alt, `j`
- `C("Ctrl-m")`: Left or Right Control, `m`
- `C("Win-o")`: Cmd/Windows,  `o`
- `C("Alt-Shift-comma")`: Alt, Left or Right Shift, comma


#### Multiple Stroke Keys

To use multiple stroke keys, simply define a nested keymap. For example, the
following example remaps `C-x C-c` to `C-q`.

```python
keymap("multi stroke", {
    C("C-x"): {
      C("C-c"): C("C-q"),
    }
})
```

If you'd like the first keystroke to also produce it's own output, `immediately` can be used:

```python
keymap("multi stroke", {
  C("C-x"): {
    # immediately output "x" when Ctrl-X is pressed
    immediately: C("x"),
    C("C-c"): C("C-q"),
  }
})
```

#### Finding out the proper `Key.NAME` literal for a key on your keyboard

From a terminal session run `evtest` and select your keyboard's input device.  Now hit the key in question.

```
Event: time 1655723568.594844, type 1 (EV_KEY), code 69 (KEY_NUMLOCK), value 1
Event: time 1655723568.594844, -------------- SYN_REPORT ------------
```

Above I've just pressed "clear" on my numpad and see `code 69 (KEY_NUMLOCK)` in the output. For Keyszer this would translate to `Key.NUMLOCK`.  You can also browse the [full list of key names](https://github.com/RedBearAK/xwaykeyz/blob/main/src/keyszer/models/key.py) in the source.


#### Finding an Application's `WM_CLASS`  and `WM_NAME` using `xprop`

> [!NOTE]  
> The [Toshy](https://github.com/RedBearAK/toshy) project has a custom function in its config that will show a dialog with the app class and window title in X11/Xorg and compatible Wayland environments. The `xprop` command will only work in X11/Xorg.  

Use the `xprop` command from a terminal:

    xprop WM_CLASS _NET_WM_NAME WM_NAME

...then click an application window.

Use the second `WM_CLASS` value (in this case `Google-chrome`) when matching `ctx.wm_class`.


#### Example of Case Insensitive Matching

```py
terminals = ["gnome-terminal","konsole","io.elementary.terminal","sakura"]
terminals = [term.casefold() for term in terminals]
USING_TERMINAL_RE = re.compile("|".join(terminals), re.IGNORECASE)

modmap("not in terminal", {
    Key.LEFT_ALT: Key.RIGHT_CTRL,
    # ...
    }, when = lambda ctx: ctx.wm_class.casefold() not in terminals
)

modmap("terminals", {
    Key.RIGHT_ALT: Key.RIGHT_CTRL,
    # ...
    }, when = lambda ctx: USING_TERMINAL_RE.search(ctx.wm_class)
)
```


## FAQ


**Can I remap the keyboard's `Fn` key?**

_It depends._  Most laptops do not allow this as the `Fn` keypress events are not _directly_ exposed to the operating system.  On some keyboards, it's just another key.  To find out you can run `evtest`.  Point it to your keyboard device and then hit a few keys; then try `Fn`.  If you get output, then you can map `Fn`.  If not, you can't.

Here is an example from a full size Apple keyboard I have:

```
Event: time 1654948033.572989, type 1 (EV_KEY), code 464 (KEY_FN), value 1
Event: time 1654948033.572989, -------------- SYN_REPORT ------------
Event: time 1654948033.636611, type 1 (EV_KEY), code 464 (KEY_FN), value 0
Event: time 1654948033.636611, -------------- SYN_REPORT ------------
```


**What if my keyboard seems laggy or is not repeating keys fast enough?**

You likely need to set the [virtual] keyboards repeat rate to match your actual keyboard.

Here is the command I use:

    xset r rate 200 20

For best results your real keyboard and Keyszer [virtual] keyboard should have matching repeat rates. That seems to work best for me. Anytime you restart keyszer you'll need to reconfigure the repeat rate because each time a new virtual keyboard device is created... or maybe it's that there is only a single repeat rate and every time you "plug in" a new keyboard it changes?

_If you could shed some light on this, please [get in touch](https://github.com/RedBearAK/xwaykeyz/issues/55)._


**Does Keyszer support FreeBSD/NetBSD or other BSDs?**

Not at the moment, perhaps never.  If you're an expert on the BSD kernel's input layers please
[join the discussion](https://github.com/RedBearAK/xwaykeyz/issues/46).  I'm at the very least open to the discussion to find out if this is possible, a good idea, etc...


**Is keyszer compatible with [Kinto.sh](https://github.com/rbreaves/kinto)?**


*That is certainly the plan.*   The major reason Kinto.sh required it's own fork [has been resolved](https://github.com/RedBearAK/xwaykeyz/issues/11).  Kinto.sh should simply "just work" with `keyszer` (with a few tiny config changes).  In fact, hopefully it works better than before since many quirks with the Kinto fork should be resolved. (such as nested combos not working, etc)

Reference:

- [Kinto GitHub issue](https://github.com/rbreaves/kinto/issues/718) regarding the transition.
- Instructions on altering your `kinto.py` config slightly. See [USING_WITH_KINTO.md](https://github.com/RedBearAK/xwaykeyz/blob/main/USING_WITH_KINTO.md).


**How can I help or contribute?**

Please open an issue to discuss how you'd like to get involved or respond on one of the existing issues. Also feel free to open new issues for feature requests.  Many issues are tagged [good first issue](https://github.com/RedBearAK/xwaykeyz/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22) or [help welcome](https://github.com/RedBearAK/xwaykeyz/issues?q=is%3Aissue+is%3Aopen+label%3A%22help+welcome%22).



## License

`keyszer` is distributed under GPL3.  See [LICENSE](https://github.com/RedBearAK/xwaykeyz/blob/main/LICENSE).


