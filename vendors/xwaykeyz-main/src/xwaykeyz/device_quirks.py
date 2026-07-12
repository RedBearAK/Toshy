"""
Per-device input quirks for the keymapper.

A small, flat table of self-contained "this device needs this fix" units,
in the spirit of the kernel's per-hardware quirk tables. Each unit knows how
to (a) detect whether it applies on the current machine, (b) announce itself,
and (c) react to a single raw input event as a pure side effect. The table is
expected to stay tiny; adding a new quirk is appending one entry.

A quirk object provides:
    probe(self) -> bool
        Detect whether this quirk applies here. Resolve and cache any paths.
    announce_startup(self)
        Log loudly that the device was found, and whether the fix can run.
    handle_key_event(self, keycode, value, device)
        Pure side effect on a raw, pre-remap event. Never consumes the event,
        never raises into the event loop, filters its own device and key.

These fixes belong in the keymapper because the problems they address are
created by the keymapper's own behavior. The Touch Bar case below, for
example, is a direct consequence of the exclusive device grab the keymapper
takes in order to remap a keyboard, so cleaning up after that grab is the
keymapper's own responsibility.
"""

__version__ = '20260610'

import os
import grp
import pwd
import glob
import shutil

from evdev import ecodes

from xwaykeyz.lib.logger import debug, error


# Logging context tag shared by all device-quirk output; change in one place.
QUIRK_CTX = 'QK'


class DeviceQuirk:
    """
    Base for a single device-specific input fix.

    Exists to give callers a real type to annotate against (so editors resolve
    the methods on a quirk pulled out of the table) and to state the contract in
    code. Not an abstract base class; the stubs just fail loudly if a subclass
    forgets one. A subclass implements:

        probe(self) -> bool
        announce_startup(self)
        handle_key_event(self, keycode, value, device)
    """

    name = 'unnamed quirk'

    def probe(self) -> bool:
        raise NotImplementedError

    def announce_startup(self):
        raise NotImplementedError

    def handle_key_event(self, keycode, value, device):
        raise NotImplementedError


class TouchBarFnQuirk(DeviceQuirk):
    """
    Apple T2 MacBook Touch Bar: restore the native Fn -> display-mode switch.

    The internal keyboard is grabbed for remapping, which severs the
    hid_appletb_kbd driver's input handler riding on that same device, so
    pressing Fn no longer flips the Touch Bar between the media row and the
    F-key row. Since the keymapper is now the only thing that sees Fn, it
    reproduces the driver's momentary toggle by writing the writable per-device
    sysfs 'mode' attribute on Fn down/up.
    """

    name            = 'Apple Touch Bar Fn'
    target_group    = 'input'

    # Touch Bar display modes. VERIFY against live hid_appletb_kbd:
    #   APPLETB_KBD_MODE_ESC / FN / SPCL / OFF
    MODE_ESC        = 0
    MODE_FN         = 1
    MODE_SPCL       = 2
    MODE_OFF        = 3

    def __init__(self):
        self.mode_path  = None      # resolved at probe() time
        self.writable   = False     # refreshed before each decision
        self.saved_mode = None      # set on Fn down, cleared on Fn up

    def probe(self) -> bool:
        # VERIFY on hardware: glob path, that '<device>/driver' is the symlink,
        # and that the resolved driver basename normalizes to hid_appletb_kbd.
        mode_paths_lst = glob.glob('/sys/bus/hid/devices/*/mode')
        for mode_path in mode_paths_lst:
            driver_link = os.path.join(os.path.dirname(mode_path), 'driver')
            if not os.path.islink(driver_link):
                continue
            driver_name = os.path.basename(os.path.realpath(driver_link))
            if driver_name.replace('-', '_') != 'hid_appletb_kbd':
                continue
            self.mode_path = mode_path
            return True
        return False

    def announce_startup(self):
        self._refresh_writable()
        if self.writable:
            debug(  f'{self.name}: problematic device detected at {self.mode_path}; '
                    f'solution will be applied.', ctx=QUIRK_CTX)
            return
        debug(  f'{self.name}: problematic device detected at {self.mode_path}, '
                f'but its mode file is not writable; the fix cannot run yet.', ctx=QUIRK_CTX)
        debug(self.describe_fix(), ctx=QUIRK_CTX)

    def handle_key_event(self, keycode, value, device):
        # Raw, pre-remap, input-side. Side effect only; the event still flows on.
        if keycode != ecodes.KEY_FN:
            return
        # VERIFY exact evdev name; mirror the driver's "Internal Keyboard" filter
        # so external Apple keyboards stay inert, matching native behavior.
        if 'Internal Keyboard' not in getattr(device, 'name', ''):
            return
        if value == 2:                          # auto-repeat: ignore
            return

        was_writable = self.writable
        self._refresh_writable()

        if not self.writable:
            if value == 1:                      # down edge only: one line per press
                debug(  f'{self.name}: Fn pressed but {self.mode_path} is not writable; '
                        f'Touch Bar display will not switch.', ctx=QUIRK_CTX)
                debug(self.describe_fix(), ctx=QUIRK_CTX)
            return

        if not was_writable:                    # self-healed since last press
            debug(f'{self.name}: write permission now present; handling is active.', ctx=QUIRK_CTX)

        if value == 1:
            self._on_fn_down()
        elif value == 0:
            self._on_fn_up()

    def describe_fix(self) -> str:
        chgrp_path  = shutil.which('chgrp') or '/usr/bin/chgrp'
        chmod_path  = shutil.which('chmod') or '/usr/bin/chmod'
        rule_path   = '/etc/udev/rules.d/90-xwaykeyz-touchbar.rules'
        rule_body   = (
            'ACTION=="add|change|bind", SUBSYSTEM=="hid", '
            'DRIVER=="hid?appletb?kbd", '
            f'RUN+="{chgrp_path} {self.target_group} /sys$devpath/mode", '
            f'RUN+="{chmod_path} g+w /sys$devpath/mode"'
        )
        lines_lst = [
            '',
            f'To let {self.target_group}-group members drive the Touch Bar, '
            f'install this udev rule:',
            '',
            f"sudo tee {rule_path} > /dev/null <<'EOF'",
            rule_body,
            'EOF',
            'sudo udevadm control --reload-rules && sudo udevadm trigger',
            '',
        ]

        group_exists, user_in_group = self._group_status()
        user_name = pwd.getpwuid(os.getuid()).pw_name

        if not group_exists:
            lines_lst += [
                f"The '{self.target_group}' group does not exist; create it and "
                f'add yourself:',
                f'sudo groupadd {self.target_group}',
                f'sudo usermod -aG {self.target_group} {user_name}',
                'Then log out and back in for the group change to take effect.',
                '',
            ]
        elif not user_in_group:
            lines_lst += [
                f"Your user '{user_name}' is not in the '{self.target_group}' "
                f'group; add it:',
                f'sudo usermod -aG {self.target_group} {user_name}',
                'Then log out and back in for the group change to take effect.',
                '',
            ]

        return '\n'.join(lines_lst)

    def _refresh_writable(self) -> bool:
        self.writable = bool(self.mode_path) and os.access(self.mode_path, os.W_OK)
        return self.writable

    def _group_status(self):
        # Returns (group_exists, user_in_group). Writability is the real gate;
        # this only enriches the proclamation with what specifically is missing.
        try:
            grp.getgrnam(self.target_group)
            group_exists = True
        except KeyError:
            group_exists = False
        user_name = pwd.getpwuid(os.getuid()).pw_name
        member_groups_lst = [g.gr_name for g in grp.getgrall() if user_name in g.gr_mem]
        primary_group = grp.getgrgid(os.getgid()).gr_name
        user_in_group = self.target_group in member_groups_lst \
            or primary_group == self.target_group
        return group_exists, user_in_group

    def _read_mode(self) -> 'int | None':
        try:
            with open(self.mode_path, 'r') as mode_fh:
                return int(mode_fh.read().strip())
        except (OSError, ValueError) as read_err:
            error(f'{self.name}: failed to read mode file: {read_err}', ctx=QUIRK_CTX)
            return None

    def _write_mode(self, mode_value) -> bool:
        try:
            with open(self.mode_path, 'w') as mode_fh:
                mode_fh.write(str(mode_value))
            return True
        except OSError as write_err:
            error(f'{self.name}: failed to write mode file: {write_err}', ctx=QUIRK_CTX)
            return False

    def _on_fn_down(self):
        current_mode = self._read_mode()
        if current_mode is None:
            return
        # Mirror the driver: show the opposite row while held, and leave the
        # ESC-only and OFF modes untouched. VERIFY against current driver source.
        if current_mode == self.MODE_SPCL:
            target_mode = self.MODE_FN
        elif current_mode == self.MODE_FN:
            target_mode = self.MODE_SPCL
        else:
            return
        self.saved_mode = current_mode
        debug(  f'{self.name}: Fn down - switching Touch Bar mode '
                f'{current_mode} -> {target_mode}.', ctx=QUIRK_CTX)
        self._write_mode(target_mode)

    def _on_fn_up(self):
        if self.saved_mode is None:
            return
        current_mode = self._read_mode()
        if current_mode is not None and current_mode != self.saved_mode:
            debug(  f'{self.name}: Fn up - restoring Touch Bar mode '
                    f'{current_mode} -> {self.saved_mode}.', ctx=QUIRK_CTX)
            self._write_mode(self.saved_mode)
        self.saved_mode = None


# The quirk table. Append new device-specific input fixes here.
device_quirks_lst: 'list[DeviceQuirk]' = [
    TouchBarFnQuirk(),
]


def initialize_device_quirks() -> 'list[DeviceQuirk]':
    """
    Probe every registered quirk, announce the ones that apply, and return them.
    Called once at keymapper startup. On any normal machine this returns an
    empty list, so the per-event dispatch at the call site stays free.
    """
    active_quirks_lst: 'list[DeviceQuirk]' = []
    for quirk in device_quirks_lst:
        if not quirk.probe():
            continue
        quirk.announce_startup()
        active_quirks_lst.append(quirk)
    return active_quirks_lst


# End of file #
