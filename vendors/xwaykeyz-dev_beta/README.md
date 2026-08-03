# xwaykeyz - a smart key remapper for Linux (X11/Xorg and Wayland)

The `xwaykeyz` keymapper is a smart key remapper for Linux, written in Python. It is similar in spirit to `xmodmap` but allows far more flexible remapping: per-application keymaps, multipurpose (tap/hold) keys, multi-tap combos, multi-stroke sequences, string and Unicode macro output, custom modifiers, and arbitrary Python functions as combo actions. It works in X11/Xorg and in a long list of Wayland environments, though Wayland support is strictly per-compositor and mostly depends on Toshy components (see [Supported environments](#supported-environments) before assuming any particular Wayland setup is covered).

This project was forked from [`keyszer`](https://github.com/joshgoebel/keyszer) (X11-only, no commits since late 2023), which was in turn forked from [`xkeysnail`](https://github.com/mooz/xkeysnail) (no longer maintained). Since the fork, `xwaykeyz` has grown Wayland support, non-US keyboard layout correction, conditional timeouts, in-keymapper multi-tap, a Hyper key subsystem, pointer-aware modifier handling, device quirks, and many reliability fixes. This README documents the keymapper as it is now.

Feel free to pronounce `xwaykeyz` however you want: Ex-Way-Keys, Sway-Keys, or Zway-Keyzzzzzz... (Or maybe Chewy-Keyz?!)

> [!IMPORTANT]
> Installing the keymapper by installing [Toshy](https://github.com/RedBearAK/toshy) is the recommended path for nearly everyone, and it is a hard requirement for most Wayland environments. Several essential subsystems are fed by Toshy components at runtime: most Wayland window context methods are Toshy D-Bus services, shell extensions, or KWin scripts; environment detection (which drives `environ_api`) comes from a Toshy module; and keyboard layout correction gets its layout analysis data from Toshy components. Toshy also handles permissions (udev rules, `input` group) and runs the keymapper under systemd user services, with no `sudoers` modifications. Standalone `xwaykeyz` is fully usable, but mainly in X11/Xorg and the few Wayland environments it can query directly. The Toshy installer accepts a `--barebones-config` argument that leaves you with a clean config file without any of the Mac-like remapping, so Toshy can also serve as just a management layer around the keymapper.


## How it works

Xwaykeyz works at quite a low level, close to the hardware. It grabs input directly from the kernel's [`evdev`](https://www.freedesktop.org/wiki/Software/libevdev/) input devices (`/dev/input/event*`) using `EVIOCGRAB`, transforms the event stream through your configured modmaps and keymaps, and re-emits the result through an emulated [`uinput`](https://kernel.org/doc/html/latest/input/uinput.html) virtual keyboard. Because this happens below the display server, the remapping itself works from the console all the way into X11 or Wayland, in any toolkit. Per-application features are a different matter: they depend on a window context provider existing for your specific environment (see [Supported environments](#supported-environments)).

The keymapper itself deals only in integer keycodes; it sits below the XKB layer that turns keycodes into characters. Historically that meant non-US layouts could see wrong keys in remapped shortcuts and broken macro output. That limitation is now addressed by the opt-in keyboard layout correction system (see `keyboard_layout_correction` below), which corrects both input combo matching and string/Unicode macro output against the user's actual layout. General typing was never affected either way; only keys and shortcuts touched by the config were ever at risk.


## Feature highlights

- Per-application keybindings that follow the focused window, in X11 and [supported Wayland environments](#supported-environments)
- Multipurpose keys: a regular key becomes a modifier when held (`Enter` as `Enter`/`Ctrl`, `CapsLock` as `Esc`/`Ctrl`, and so on)
- Multi-tap combos: different actions for 1 to 5 rapid taps of the same combo, via the `MultiTap()` descriptor
- Multi-stroke sequences: `Ctrl+x Ctrl+c` can map to `Ctrl+q`, with optional immediate first-stroke output
- Very flexible output: a combo can type strings, Unicode characters, other combos, or run arbitrary Python functions (as the user running the keymapper)
- Custom modifiers via `add_modifier`, plus a one-call Hyper key scheme via `setup_hyper`
- `bind` for persistent holds across combos (the classic macOS-style `Cmd-Tab` app switching case)
- Held-combo output driven by compositor key repeat, instead of synthetic tap cycles
- Opt-in non-US keyboard layout correction for combo matching and macro output
- Conditional (per-application) timeout overrides through one `timeouts()` API
- Pointer monitor: touching a mouse or touchpad instantly resumes suspended modifiers, fixing modifier+click reliability
- Device quirks framework (currently: restoring the Fn display-mode switch on Apple T2 Touch Bar keyboards)
- Throttle delays to pace virtual keystroke output for compositors and input methods with event-order sensitivities
- Low CPU while holding keys (repeats ignored by default), configurable diagnostics and emergency-eject hotkeys
- Runs as a normal (or dedicated) user; running as `root` is deprecated


## Supported environments

The keymapper needs to know the focused window's application class and title to drive conditional keymaps. It contains multiple "window context providers" for this, selected by the `environ_api()` call in the config (see below).

Supported standalone, with no Toshy components (the keymapper queries these directly):

- **X11/Xorg sessions** (any window manager, via `Xlib`)
- **Sway** (via `i3ipc`)
- **Hyprland** (via `hyprpy`)
- **Pantheon** (via D-Bus queries to the DE's own Gala WM)

Requiring Toshy components (D-Bus services, shell extensions, or KWin scripts that feed window context to the keymapper's providers):

- **Wayland compositors with the `zwlr_foreign_toplevel_manager_v1` interface** (via the Toshy Wlroots D-Bus service): Hyprland, labwc, Miracle-WM, Miriway, Niri, Qtile, River, Sway, Wayfire, and other compatible compositors
- **GNOME 3.38 or later** (needs a third-party shell extension)
- **Plasma 5 and Plasma 6 (KDE)** (Toshy KWin script and D-Bus service)
- **Cinnamon 6.0 or later** (Toshy custom shell extension)
- **COSMIC desktop environment** (Toshy D-Bus service)

The full, current list with requirements is kept updated in the [Toshy README](https://github.com/RedBearAK/toshy#currently-working-desktop-environments-or-window-managers). For trying the `wlroots` method on untested compositors, see the [wlroots wiki article](https://github.com/RedBearAK/toshy/wiki/Wlroots-Based-Wayland-Compositors) on the Toshy repo.


## Installation

Requires Python 3.8 or later.

From source:

    git clone https://github.com/RedBearAK/xwaykeyz.git
    cd xwaykeyz
    pip3 install --user --upgrade .

For testing/hacking/contributing, a `venv` is the simplest way to get started:

    git clone https://github.com/RedBearAK/xwaykeyz.git
    cd xwaykeyz
    python3 -m venv .venv
    source .venv/bin/activate
    pip3 install -e .
    ./bin/xwaykeyz -c config_file


## System requirements and permissions

Xwaykeyz requires read/write access to:

- `/dev/input/event*` - to grab input from your `evdev` input devices
- `/dev/uinput` - to provide an emulated keyboard to the kernel

### Running as the logged-in user (the supported way, required for Wayland)

The keymapper runs as the logged-in desktop user. This is a hard architectural requirement in Wayland environments, not a convenience: window context comes from per-session sources that only exist inside the user's login session (the session D-Bus bus, Toshy's D-Bus services, shell extensions, KWin scripts, compositor IPC sockets). A keymapper process running outside that session cannot reach any of them, so conditional keymaps would be blind. There is also little real security benefit to a separate account: the config file is executable Python owned by the user either way, and write access to `uinput` allows arbitrary keystroke injection regardless of which account holds it. The reasoning is laid out in more depth in a dedicated article on the [Toshy wiki](https://github.com/RedBearAK/Toshy/wiki).

Toshy sets all of this up automatically: it creates the `input` group if needed, adds your user to it, installs a udev rules file, and runs the keymapper (and its D-Bus helper services) as systemd user services, with no `sudoers` modifications. The udev rules Toshy installs (`/etc/udev/rules.d/70-toshy-keymapper-input.rules`) look like this:

    SUBSYSTEM=="input", GROUP="input", MODE="0660", TAG+="uaccess"
    KERNEL=="uinput", SUBSYSTEM=="misc", GROUP="input", MODE="0660", TAG+="uaccess"

For a manual standalone setup, install an equivalent rules file, then add your user to the `input` group and log out and back in:

    sudo usermod -aG input $USER

### Fallback: dedicated semi-privileged user (X11/Xorg only)

An isolated user with ACL-granted device access can run the keymapper instead. This only makes sense in X11/Xorg sessions, where the `Xlib` window context provider can be pointed at the display without the per-session plumbing Wayland requires, and X11 itself is slowly disappearing. Expect conditional keymaps to be broken in any Wayland session with this arrangement.

    sudo useradd keymapper

    cat <<EOF | sudo tee /etc/udev/rules.d/90-keymapper-acl.rules
    KERNEL=="event*", SUBSYSTEM=="input", RUN+="/usr/bin/setfacl -m user:keymapper:rw /dev/input/%k"
    KERNEL=="uinput", SUBSYSTEM=="misc", RUN+="/usr/bin/setfacl -m user:keymapper:rw /dev/uinput"
    EOF

### Running as root

Do not do this. It is dangerous and unnecessary, and support for it (`--very-bad-idea`) exists only as a deprecated escape hatch.


## Usage

    xwaykeyz

A successful bare startup (no Toshy, default logging) should resemble:

    xwaykeyz v1.25.0
    (+K) Grabbing 'Apple, Inc Apple Keyboard' (/dev/input/event3)
    (+K) Successfully grabbed 'Apple, Inc Apple Keyboard' (/dev/input/event3)
    (--) Ready to process input.

Devices are grabbed asynchronously, waiting for keys to be released first, hence the two-step grab messages. The config file path and much more detail appear with `-v`. Startups under Toshy are far noisier because the Toshy config file logs environment detection, machine identity, and remap setup while it loads; that output comes from the config, not the keymapper core.

### CLI options

- `-c`, `--config` - location of the configuration file (default: `~/.config/xwaykeyz/config.py`)
- `-d`, `--devices` - manually specify one or more devices to remap, by path or name
- `-w`, `--watch` - watch for hot-plugged keyboard devices
- `-v` - increase debug logging
- `--flush` - immediately flush all log output (useful under journald)
- `--list-devices` - list all input devices, with every matchable identifier for each (path, bus path, name, by-id symlink, uniq, synthetic ID)
- `--check` - evaluate the config file and check for errors, then exit
- `--version` - print the version and exit


## Configuration

By default the configuration is read from `~/.config/xwaykeyz/config.py` (override with `-c`). The configuration file is Python. For a small example see [`example/config.py`](https://github.com/RedBearAK/xwaykeyz/blob/main/example/config.py); for a very large real-world example see the [Toshy config](https://github.com/RedBearAK/toshy/blob/main/default-toshy-config/toshy_config.py).

The configuration API at a glance:

- `environ_api(session_type=..., wl_compositor=...)` - tell the keymapper which window context provider to use
- `devices_api(only_devices=[...])` - limit remapping to specific devices, from inside the config
- `timeouts(multipurpose=..., suspend=..., tap_interval=..., min_tap_delay=..., when=..., name=...)` - global and per-condition timing
- `throttle_delays(key_pre_delay_ms, key_post_delay_ms)` - pace virtual keystroke output
- `keyboard_layout_correction(...)` and `layout_correction_options()` - opt-in non-US layout correction
- `ignore_repeating_keys(bool)` - repeat-event handling (repeats ignored by default)
- `modmap(name, mappings, when=...)` - key identity remapping
- `multipurpose_modmap(name, mappings, when=...)` - tap/hold dual-purpose keys
- `keymap(name, mappings, when=...)` - combo-to-action mapping
- `conditional(fn, map)` - wrap a map with a condition (same effect as `when=`)
- `matchProps(...)` - window/device context matcher factory for `when=` clauses
- `MultiTap(...)` - multi-tap action descriptor for keymap values (deprecated alias: `isMultiTap`)
- `add_modifier(name, aliases, key/keys)` - define custom modifiers
- `setup_hyper(trigger_key, ...)` - one-call Hyper key scheme
- `setup_level3_combos_via_left_alt(when=...)` - reach AltGr glyph layers with left Alt on non-US layouts
- `dump_diagnostics_key(key)` / `emergency_eject_key(key)` - diagnostic and bail-out hotkeys
- `wm_class_match(re_str)` / `not_wm_class_match(re_str)` - tiny regex conditional helpers
- `include(relative_filename)` - pull other Python files into the config
- String/Unicode macro helpers: `to_US_keystrokes(...)`, `unicode_keystrokes(...)`, `sleep(...)`, `usleep(...)`
- Marks (Emacs-style shift/mark combos): `with_mark(...)`, `set_mark(...)`, `with_or_set_mark(...)`

### `environ_api(...)`

Xwaykeyz has multiple window context providers for X11/Xorg and the supported Wayland environments. `environ_api()` tells it which one to instantiate:

```py
environ_api(
    session_type  = 'wayland',      # 'x11' or 'wayland'
    wl_compositor = 'kwin_wayland', # 'wlroots', 'kwin_wayland', 'mutter', 'sway', 'hyprland', etc.
)
```

For X11/Xorg, only `session_type='x11'` matters (the default, for backward compatibility). For Wayland, the compositor argument selects the provider; the `wlroots` value covers a dozen or more compositors that implement `zwlr_foreign_toplevel_manager_v1`.

Toshy wires this automatically from an environment detection module, so users moving between desktop environments on the same system rarely need to specify anything. For a single-environment setup, a static call in the config is perfectly fine.

### `devices_api(...)`

Control which devices are grabbed, from inside the config. `only_devices` is an allowlist (equivalent to the `--devices` CLI option); `ignore_devices` excludes devices that would otherwise be grabbed. The ignore list wins if a device appears in both:

```py
devices_api(
    only_devices = [
        'Topre Corporation HHKB Professional',              # exact device name
    ],
    ignore_devices = [
        '/dev/input/by-id/usb-Some_Gaming_Pad-event-kbd',   # any path; by-id symlinks resolve
        'dc:2c:26:xx:xx:xx',                                # uniq string (serial / MAC)
        'b0019:v0000:p0001:e0000:n51dc9927',                # synthetic ID (see below)
    ],
)
```

Each entry can match a device four different ways:

- Exact device name (survives re-enumeration, but some hardware ships identical names)
- Device path, including `/dev/input/by-id/` symlinks (candidates starting with `/` are resolved through `realpath`)
- The device `uniq` string, when the hardware provides one (typically a serial number or Bluetooth MAC)
- A synthetic ID built from evdev-reported kernel info, in the form `bustype:vendor:product:version:name_hash`, with an optional `@physical_bus` suffix. Without the suffix it matches that hardware model+name on any port; with the suffix it pins one exact physical connection. This is the reliable way to single out one of several identically named devices.

Run `xwaykeyz --list-devices` to see every matchable identifier for each attached device. The output is a multi-line block per device showing the device path, bus path, name, by-id symlink (when one exists), uniq string (when the hardware provides one), and the synthetic ID.

### `timeouts(...)`

One API for all timing values, global and per-condition:

```py
timeouts(
    multipurpose  = 1,      # sec before a held multipurpose key resolves as its "held" identity
    suspend       = 1,      # sec modifiers are withheld from output while combo intent is unclear
    tap_interval  = 0.25,   # max sec between taps of a MultiTap combo (range 0.15 to 1.5)
    min_tap_delay = 0.07,   # sec of key-repeat protection between taps (range 0.05 to 0.5)
)
```

Every key is optional. A global call (no `when`) merges the values you pass onto the current settings, so multiple global calls compose instead of resetting each other.

Passing `when=` registers a conditional override with the same predicate style as keymaps. Only the keys you pass are stored on the rule; anything omitted falls through. Rules are consulted first-match-wins, per key, at resolution time:

```py
timeouts(suspend = 0.3, when = matchProps(clas="^firefox$"), name = "firefox_menu_guard")
```

The classic use: run a zero or near-zero global `suspend` for instant modifier response, then restore a working suspend window only for apps that steal menu focus on a bare modifier press (Firefox, VSCode, Slack). The `name=` shows up in debug logging when an override wins.

### `throttle_delays(...)`

Paces virtual keyboard output to deal with modifier press/release timing being misinterpreted downstream (certain compositors, input methods like IBus/fcitx5, and virtual machines):

```py
throttle_delays(
    key_pre_delay_ms  = 0,  # delay before the "normal" key event, after modifier presses (0 to 150)
    key_post_delay_ms = 0,  # delay after the "normal" key event, before modifier releases (0 to 150)
)
```

Symptoms that suggest enabling throttle delays: combos that intermittently behave as if unmapped, macros with missing characters, premature macro termination, wrong shift states in macro output, or Unicode sequences failing to complete. Try 40/70 ms in virtual machines with major problems; try 0.1/0.5 ms on bare metal with occasional macro glitches. Events the keymapper passes through unmodified take a fast path with a minimal floor delay, so throttle settings mainly affect remapped and synthesized output rather than ordinary typing.

### `keyboard_layout_correction(...)`

Opt-in correction for non-US keyboard layouts, in two phases: input combo matching (so `C("Cmd-z")` matches the key that produces `z` on the active layout) and string/Unicode macro output (so typed strings come out correctly). Deliberately off by default because it manipulates output:

```py
keyboard_layout_correction(
    correction_enabled = True,
    correct_number_row = False,     # opt-in for layouts with a position-flipped number row
    symbol_miss_policy = 'refuse',  # 'refuse' | 'fold' | 'placeholder'
)
```

When a macro contains a character the active layout cannot type, the miss policy decides the outcome: `refuse` emits nothing and logs loudly (the default), `fold` substitutes the closest ASCII equivalent (uses `anyascii` when available), `placeholder` substitutes a visible placeholder character. The keymapper consumes layout analysis data (corrected key matching tables and a per-layout symbol table for output); in practice this data is provisioned by Toshy components, which detect the active layout and feed the correction system automatically, including layout changes. Standalone users should read the docstrings in `config_api.py` for the data-provisioning details.

### `modmap(name, mappings, when=None)`

Maps a physical key to a different key identity. Conditional modmaps overrule the default modmap; the first modmap that contains the pressed key and matches its condition wins. Both sides are `Key` literals:

```py
modmap("default", {
    Key.CAPSLOCK: Key.LEFT_CTRL,
})
```

If you do not create a default (non-conditional) modmap, a blank one is created for you.

### `multipurpose_modmap(name, mappings, when=None)`

Gives a key two purposes: its tap identity and its held identity:

```py
multipurpose_modmap("default", {
    # Enter is Enter when tapped, Right Ctrl when held with other keys
    Key.ENTER: [Key.ENTER, Key.RIGHT_CTRL],
})
```

A held multipurpose key resolves to its modifier identity when another key is pressed while it is down, or when the `multipurpose` timeout expires; a quick lone press-release resolves as the tap identity.

### `keymap(name, mappings, when=None)`

Maps input combos to output actions:

```py
keymap("Firefox", {
    C("Cmd-s"): C("Ctrl-s"),
}, when = matchProps(clas="^firefox$"))
```

The `mappings` dict maps `combo: command`, where `command` is one of:

- `C(combo_str)` - emit a combo (single-Combo mappings ride compositor key repeat while held)
- `Key.NAME` - emit a single key
- `[command1, command2, ...]` - execute commands sequentially
- `{ ... }` - nested keymap for multi-stroke sequences (see below)
- `MultiTap(...)` - tap-count-dependent actions (see below)
- `to_US_keystrokes("text")` - type out a string (100 characters or less)
- `unicode_keystrokes(0x1F3B5)` - type a Unicode character by codepoint
- arbitrary function - executed (with `ctx` if it accepts one argument); any return value is run as a command
- `escape_next_key` - escape the next non-modifier key (held modifiers are dropped)
- `escape_next_combo` - escape the next mods+key combo (modifiers are kept)
- `ignore_key` - swallow the input entirely (often used to disable a native combo)
- `bind` - bind input and output modifiers so the output is not lifted until the input is
- `sleep(sec)` / `usleep(usec)` - pauses inside a command list

### `MultiTap(...)`

A passive descriptor used as the value side of a keymap entry, giving one combo different actions for 1 to 5 rapid taps:

```py
keymap("multi-tap demo", {
    C("Shift-RC-t"): MultiTap(
        tap_1_action = C("C-n"),            # None here would block single-tap
        tap_2_action = some_function,
        tap_3_action = [to_US_keystrokes("x3!"), C("Enter")],
        # tap_interval / min_tap_delay kwargs override the timeouts() values
    ),
})
```

Any tap level can be a Combo, a Key, a callable, a list of those, or `None` (no action at that level), so sparse setups like "act only on 2 and 4 taps" work naturally. Timing resolves per sequence: explicit kwargs first, then any matching conditional `timeouts()` rule, then the global values. Tap counting, timing, and deferred emission all run inside the keymapper's event loop. `isMultiTap(...)` remains as a deprecated compatibility alias.

### `matchProps(...)`

Factory producing a `when=` predicate that matches the current window and device context. All parameters are named; at least one is required:

```py
keymap("Terminals", {
    # ...
}, when = matchProps(clas="gnome-terminal|konsole|alacritty"))
```

Supported parameters: `clas`, `name`, `devn` (regex strings matched against the application class, window title, and device name; case insensitive by default, `cse=True` for case sensitive), negations `not_clas`, `not_name`, `not_devn`, booleans `numlk` and `capslk`, and list-of-dicts forms `lst`/`not_lst` for matching several property sets with one call. For performance-sensitive configs, hoist the factory call into a variable at load time and reference it in `when=`, rather than calling the factory inside a lambda on every key event.

### `conditional(fn, map)`

Wraps a map so it applies only when `fn(ctx)` is true; equivalent to passing `when=` to the map function. Prefer `matchProps()` for building these predicates; writing a raw function is the escape hatch for conditions `matchProps()` cannot express (combining context with external state, custom logic, and so on). The `ctx` object such a function receives exposes:

- `wm_class` - application class of the focused window (`WM_CLASS` in X11/Xorg; the compositor-reported `app_id` or equivalent in Wayland environments)
- `wm_name` - title of the focused window
- `device_name` - name of the device the input came from
- `capslock_on` / `numlock_on` - lock key states (booleans)

### `add_modifier(...)` and `setup_hyper(...)`

```py
add_modifier("HYPER", aliases = ["Hyper"], key = Key.F24)
```

Custom modifiers can then be used in combo strings like any built-in modifier. For the common Hyper scheme, `setup_hyper()` does everything in one call: creates the modifier on a virtual carrier keycode, binds the trigger key (as a plain modmap, or a multipurpose modmap when `tap_output` is given), and appends an expansion keymap that turns `Hyper-X` into `Shift+Ctrl+Alt+Super+X` (or a two-layer variant with `add_unshifted_layer=True`):

```py
setup_hyper(Key.CAPSLOCK, tap_output=Key.ESC)
```

User keymaps referencing Hyper combos automatically take priority over the expansion, since the expansion keymap is appended last.

### `dump_diagnostics_key(key)` and `emergency_eject_key(key)`

```py
dump_diagnostics_key(Key.F15)   # default; dumps diagnostic info to stdout when hit
emergency_eject_key(Key.F16)    # default; immediately terminates the keymapper when hit
```

The eject key is invaluable while developing a config that has gone sideways.

### `include(relative_filename)`

Loads another Python file into the config at the point of inclusion, sharing the same global scope. Files must live in the same directory as the main config:

```py
include("os.py")
include("apps.py")
```

### Combo specifications

Combos are written as `C("(<Modifier>-)*<Key>")`. Modifiers:

- `C` or `Ctrl` - Control
- `Alt` - Alt
- `Shift` - Shift
- `Super`, `Win`, `Command`, `Cmd`, `Meta` - Super/Windows/Command
- `Fn` - Function (on hardware that exposes it)
- Any custom modifier alias created with `add_modifier`

Prefix `L` or `R` for a specific side (`LC-`, `RAlt-`). `<Key>` is any name defined in [`key.py`](https://github.com/RedBearAK/xwaykeyz/blob/main/src/xwaykeyz/models/key.py). Examples:

- `C("LC-Alt-j")` - left Control, Alt, `j`
- `C("Ctrl-m")` - either Control, `m`
- `C("Alt-Shift-comma")` - Alt, either Shift, comma

`K()` is an older alias for `C()` kept for config compatibility.

### Multi-stroke sequences

Nested keymaps create multi-stroke bindings; `immediately` gives the first stroke its own output:

```py
keymap("multi stroke", {
    C("C-x"): {
        immediately: C("x"),        # optional
        C("C-c"): C("C-q"),
    },
})
```


## Finding key names and window properties

To find the `Key.NAME` literal for a physical key, run `evtest`, select your keyboard device, and hit the key:

    Event: time 1655723568.594844, type 1 (EV_KEY), code 69 (KEY_NUMLOCK), value 1

`KEY_NUMLOCK` translates to `Key.NUMLOCK`. The [full list of key names](https://github.com/RedBearAK/xwaykeyz/blob/main/src/xwaykeyz/models/key.py) is in the source.

The `ctx.wm_class` and `ctx.wm_name` attributes carry the application class and window title regardless of session type: in X11/Xorg they come from the `WM_CLASS` and `WM_NAME`/`_NET_WM_NAME` window properties, while in Wayland environments the window context providers fill them with the compositor-reported `app_id` (or its equivalent) and window title. In X11/Xorg you can inspect these directly: run `xprop WM_CLASS _NET_WM_NAME WM_NAME` and click the window, then match `ctx.wm_class` against the second `WM_CLASS` value.

> [!NOTE]
> `xprop` only works in X11/Xorg. The Toshy config has a diagnostic hotkey function that shows a dialog with the app class and window title in X11/Xorg and all supported Wayland environments, which is the practical way to get these values on Wayland.


## Upgrading from xkeysnail or Kinto

Some configuration changes and CLI argument changes are needed coming from `xkeysnail` 0.4.0; see [UPGRADE_FROM_XKEYSNAIL.md](https://github.com/RedBearAK/xwaykeyz/blob/main/UPGRADE_FROM_XKEYSNAIL.md). For the Kinto variety of `xkeysnail`, see [USING_WITH_KINTO.md](https://github.com/RedBearAK/xwaykeyz/blob/main/USING_WITH_KINTO.md).

> [!NOTE]
> Kinto users should strongly consider migrating to [Toshy](https://github.com/RedBearAK/toshy), which is intrinsically designed around this keymapper, supports many Wayland environments Kinto cannot, and is actively maintained.


## FAQ

**Can I remap the keyboard's `Fn` key?**

It depends. Most laptops do not expose `Fn` keypress events directly to the operating system. On some keyboards it is just another key. Run `evtest` against your keyboard device and press `Fn`: if you get output (e.g. `code 464 (KEY_FN)`), you can map it; if not, you cannot. On Apple T2 MacBooks, the built-in device quirk restores the Touch Bar's native Fn display-mode switching that grabbing the keyboard would otherwise break.

**What if my keyboard seems laggy or is not repeating keys fast enough?**

The virtual keyboard's repeat settings may not match your physical keyboard. In X11/Xorg, `xset r rate 200 20` (adjust to taste) after the keymapper starts usually fixes it. Wayland compositors manage repeat rate per their own settings.

**My modifier+click combos were unreliable. Is that fixed?**

Yes, this is what the pointer monitor is for. Modifiers are briefly "suspended" from the output while the keymapper waits to see whether they are part of a combo; any mouse or touchpad activity during that window now resumes them immediately, so modifier+click and modifier+scroll work as expected even with the suspend timeout active. Suspend behavior is tunable globally and per-app via `timeouts()`.

**Does xwaykeyz support FreeBSD/NetBSD or other BSDs?**

No. The keymapper is built directly on the Linux kernel's `evdev`/`uinput` interfaces.

**How can I help or contribute?**

Open an [issue](https://github.com/RedBearAK/xwaykeyz/issues) to discuss what you would like to work on, or pick up an existing one. Bug reports with clear reproduction steps are always valuable, as are reports of Wayland compositors that do or do not work with the wlroots window context method.


## License

`xwaykeyz` is distributed under GPL3. See [LICENSE](https://github.com/RedBearAK/xwaykeyz/blob/main/LICENSE).
