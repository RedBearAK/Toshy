"""
src/xwaykeyz/device_quirks.py

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
    recover_stale_state(self)                               (optional)
        Undo anything a previous, interrupted run left behind. Called once at
        startup, after a successful probe().
    shutdown(self)                                          (optional)
        Put the device back the way it was found. Called when the keymapper
        is shutting down. Must be safe to call more than once.

These fixes belong in the keymapper because the problems they address are
created by the keymapper's own behavior. The Touch Bar case below, for
example, is a direct consequence of the exclusive device grab the keymapper
takes in order to remap a keyboard, so cleaning up after that grab is the
keymapper's own responsibility.
"""

__version__ = '20261001'

import os
import grp
import pwd
import glob
import shutil

from evdev import ecodes

from xwaykeyz.lib.logger import debug, error, info


# Logging context tag shared by all device-quirk output; change in one place.
QUIRK_CTX = 'QK'

# Swap record: a small file that exists only while a Touch Bar quirk is holding
# a temporary mode (Fn is down). If the keymapper dies mid-hold, the record is
# the only evidence that the mode left behind is not the user's own choice. It
# is read back at the next startup, and by external recovery tools.
#   location:   $XDG_RUNTIME_DIR/<SWAP_RECORD_SUBDIR>/<SWAP_RECORD_NAME>
#   line 1:     sysfs attribute path, in /sys/bus/hid/drivers/<drv>/<dev>/ form
#   line 2:     original mode
#   line 3:     temporary mode written while Fn is held
SWAP_RECORD_SUBDIR  = 'xwaykeyz'
SWAP_RECORD_NAME    = 'touchbar_fn_swap'


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

    The two remaining hooks are optional and do nothing unless overridden:

        recover_stale_state(self)
        shutdown(self)
    """

    name = 'unnamed quirk'

    def probe(self) -> bool:
        raise NotImplementedError

    def announce_startup(self):
        raise NotImplementedError

    def handle_key_event(self, keycode, value, device):
        raise NotImplementedError

    def recover_stale_state(self):
        return

    def shutdown(self):
        return


class TouchBarFnQuirk(DeviceQuirk):
    """
    Apple T2 MacBook Touch Bar: restore the native Fn -> display-mode switch.

    The internal keyboard is grabbed for remapping, which severs the
    hid_appletb_kbd driver's input handler riding on that same device, so
    pressing Fn no longer flips the Touch Bar between the media row and the
    F-key row. Since the keymapper is now the only thing that sees Fn, it
    reproduces the driver's momentary toggle by writing the writable per-device
    sysfs 'mode' attribute on Fn down/up.

    While Fn is held, a swap record (see SWAP_RECORD_NAME) notes the original
    mode, so that a hold interrupted by a crash can be undone at next startup.
    """

    name            = 'Apple Touch Bar Fn'
    target_group    = 'input'

    # Touch Bar display modes. VERIFY against live hid_appletb_kbd:
    #   APPLETB_KBD_MODE_ESC / FN / SPCL / OFF
    MODE_ESC        = 0
    MODE_FN         = 1
    MODE_SPCL       = 2
    MODE_OFF        = 3
    MODE_MAX        = MODE_OFF

    mode_glob       = '/sys/bus/hid/devices/*/mode'
    drivers_dir     = '/sys/bus/hid/drivers'

    def __init__(self):
        self.mode_path          = None      # resolved at probe() time
        self.record_attr_path   = None      # mode_path as named in the swap record
        self.writable           = False     # refreshed before each decision
        self.saved_mode         = None      # set on Fn down, cleared on Fn up
        self.held_mode          = None      # set on Fn down, cleared on Fn up

    def probe(self) -> bool:
        # VERIFY on hardware: glob path, that '<device>/driver' is the symlink,
        # and that the resolved driver basename normalizes to hid_appletb_kbd.
        mode_paths_lst = sorted(glob.glob(self.mode_glob))
        for mode_path in mode_paths_lst:
            driver_link = os.path.join(os.path.dirname(mode_path), 'driver')
            if not os.path.islink(driver_link):
                continue
            driver_name = os.path.basename(os.path.realpath(driver_link))
            if driver_name.replace('-', '_') != 'hid_appletb_kbd':
                continue
            self.mode_path = mode_path
            # Same file, addressed through the driver directory. This is the
            # form the swap record uses, so every reader agrees on one spelling.
            device_id = os.path.basename(os.path.dirname(mode_path))
            self.record_attr_path = os.path.join(
                self.drivers_dir, os.path.basename(os.path.realpath(driver_link)),
                device_id, os.path.basename(mode_path))
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
        if not self._is_target_device(device):
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

    def recover_stale_state(self):
        # Startup only. Acts solely on the evidence of a swap record; without
        # one, whatever mode is set is taken to be the user's own choice.
        if not os.path.isfile(self._swap_record_path()):
            return
        swap_modes_tup = self._read_swap_record()
        if swap_modes_tup is None:
            error(  f'{self.name}: leftover swap record is unusable; removing it. '
                    f'Touch Bar mode left untouched.', ctx=QUIRK_CTX)
            self._clear_swap_record()
            return
        original_mode, held_mode = swap_modes_tup
        current_mode = self._read_mode()
        if current_mode is None:
            return
        if current_mode != held_mode:
            debug(  f'{self.name}: leftover swap record is stale (mode has changed '
                    f'since); removing it.', ctx=QUIRK_CTX)
            self._clear_swap_record()
            return
        if not self._refresh_writable():
            error(  f'{self.name}: an interrupted Fn hold left the Touch Bar in mode '
                    f'{held_mode} (was {original_mode}), but {self.mode_path} is not '
                    f'writable, so it cannot be restored. Swap record kept.', ctx=QUIRK_CTX)
            return
        if not self._write_mode(original_mode):
            return
        info(   f'{self.name}: an interrupted Fn hold left the Touch Bar in mode '
                f'{held_mode}; restored original mode {original_mode}.', ctx=QUIRK_CTX)
        self._clear_swap_record()

    def shutdown(self):
        if self.saved_mode is None:
            return
        debug(f'{self.name}: shutting down while Fn is held.', ctx=QUIRK_CTX)
        self._on_fn_up()

    def describe_fix(self) -> str:
        chgrp_path  = shutil.which('chgrp') or '/usr/bin/chgrp'
        chmod_path  = shutil.which('chmod') or '/usr/bin/chmod'
        rule_path   = '/etc/udev/rules.d/90-xwaykeyz-touchbar.rules'
        rule_body   = self._udev_rule_body(chgrp_path, chmod_path)
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

    def _udev_rule_body(self, chgrp_path, chmod_path) -> str:
        return (
            'ACTION=="add|change|bind", SUBSYSTEM=="hid", '
            'DRIVER=="hid?appletb?kbd", '
            f'RUN+="{chgrp_path} {self.target_group} /sys$devpath/mode", '
            f'RUN+="{chmod_path} g+w /sys$devpath/mode"'
        )

    def _is_target_device(self, device) -> bool:
        # VERIFY exact evdev name; mirror the driver's "Internal Keyboard" filter
        # so external Apple keyboards stay inert, matching native behavior.
        return 'Internal Keyboard' in getattr(device, 'name', '')

    def _held_mode_for(self, current_mode) -> 'int | None':
        # Mirror the driver: show the opposite row while held, and leave the
        # ESC-only and OFF modes untouched. VERIFY against current driver source.
        if current_mode == self.MODE_SPCL:
            return self.MODE_FN
        if current_mode == self.MODE_FN:
            return self.MODE_SPCL
        return None

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
        target_mode = self._held_mode_for(current_mode)
        if target_mode is None:
            return
        self.saved_mode = current_mode
        self.held_mode  = target_mode
        # Record the swap before making it, so there is never a moment when the
        # temporary mode is in place without the evidence needed to undo it.
        self._write_swap_record()
        debug(  f'{self.name}: Fn down - switching Touch Bar mode '
                f'{current_mode} -> {target_mode}.', ctx=QUIRK_CTX)
        if self._write_mode(target_mode):
            return
        self._clear_swap_record()
        self.saved_mode = None
        self.held_mode  = None

    def _on_fn_up(self):
        if self.saved_mode is None:
            return
        current_mode = self._read_mode()
        if current_mode is not None and current_mode != self.saved_mode:
            debug(  f'{self.name}: Fn up - restoring Touch Bar mode '
                    f'{current_mode} -> {self.saved_mode}.', ctx=QUIRK_CTX)
            self._write_mode(self.saved_mode)
        self._clear_swap_record()
        self.saved_mode = None
        self.held_mode  = None

    def _swap_record_path(self) -> str:
        runtime_dir = os.environ.get('XDG_RUNTIME_DIR') or f'/run/user/{os.getuid()}'
        return os.path.join(runtime_dir, SWAP_RECORD_SUBDIR, SWAP_RECORD_NAME)

    def _write_swap_record(self) -> bool:
        record_path = self._swap_record_path()
        temp_path   = record_path + '.tmp'
        record_text = f'{self.record_attr_path}\n{self.saved_mode}\n{self.held_mode}\n'
        try:
            os.makedirs(os.path.dirname(record_path), mode=0o700, exist_ok=True)
            with open(temp_path, 'w') as record_fh:
                record_fh.write(record_text)
            os.replace(temp_path, record_path)
            return True
        except OSError as record_err:
            error(  f'{self.name}: failed to write swap record; an interrupted Fn '
                    f'hold could not be undone automatically: {record_err}', ctx=QUIRK_CTX)
            return False

    def _clear_swap_record(self):
        try:
            os.remove(self._swap_record_path())
        except FileNotFoundError:
            return
        except OSError as record_err:
            error(f'{self.name}: failed to remove swap record: {record_err}', ctx=QUIRK_CTX)

    def _read_swap_record(self) -> 'tuple[int, int] | None':
        # Returns (original_mode, held_mode), or None if the record cannot be
        # trusted: unreadable, malformed, or describing some other attribute.
        try:
            with open(self._swap_record_path(), 'r') as record_fh:
                lines_lst = record_fh.read().splitlines()
        except OSError:
            return None
        if len(lines_lst) != 3:
            return None
        if lines_lst[0] != self.record_attr_path:
            return None
        valid_modes_lst = [str(mode_num) for mode_num in range(self.MODE_MAX + 1)]
        if lines_lst[1] not in valid_modes_lst or lines_lst[2] not in valid_modes_lst:
            return None
        return int(lines_lst[1]), int(lines_lst[2])


class TouchBarT1FnQuirk(TouchBarFnQuirk):
    """
    Apple T1 MacBook Touch Bar (2016-2017): restore the native Fn behavior.

    Same cause as the T2 case: the exclusive grab on the internal keyboard cuts
    off the input handler of the out-of-tree 'apple-touchbar' driver, so it
    never sees Fn. The remedy differs in one respect. The T1 driver's writable
    attribute, 'fnmode', is not what the Touch Bar is showing right now but a
    standing policy for what Fn does. So while Fn is held, the policy is
    swapped for the fixed mode showing the row that Fn would have revealed,
    and the original policy is put back on release.
    """

    name            = 'Apple T1 Touch Bar Fn'

    # Fn-key policies. Mirrors APPLETB_FN_MODE_* in the apple-touchbar driver.
    FNMODE_FKEYS    = 0     # F-keys only
    FNMODE_NORM     = 1     # special keys; Fn switches to F-keys
    FNMODE_INV      = 2     # F-keys; Fn switches to special keys
    FNMODE_SPCL     = 3     # special keys only
    FNMODE_ESC      = 4     # escape key only
    MODE_MAX        = FNMODE_ESC

    mode_glob       = '/sys/bus/hid/drivers/apple-touchbar/*/fnmode'

    def probe(self) -> bool:
        mode_paths_lst = sorted(glob.glob(self.mode_glob))
        if not mode_paths_lst:
            return False
        self.mode_path          = mode_paths_lst[0]
        self.record_attr_path   = self.mode_path
        return True

    def _udev_rule_body(self, chgrp_path, chmod_path) -> str:
        return (
            'ACTION=="add|bind", SUBSYSTEM=="hid", '
            'DRIVER=="apple-touchbar", TEST=="fnmode", '
            f'RUN+="{chgrp_path} {self.target_group} /sys%p/fnmode", '
            f'RUN+="{chmod_path} g+w /sys%p/fnmode"'
        )

    def _is_target_device(self, device) -> bool:
        # The internal keyboard on these models is on the SPI bus ('Apple SPI
        # Keyboard'). Bus type is steadier than a name, and no external
        # keyboard can be on that bus, so those stay inert.
        device_info = getattr(device, 'info', None)
        return getattr(device_info, 'bustype', None) == ecodes.BUS_SPI

    def _held_mode_for(self, current_mode) -> 'int | None':
        # The fixed-row policies and escape-only have no Fn behavior to restore.
        if current_mode == self.FNMODE_NORM:
            return self.FNMODE_FKEYS
        if current_mode == self.FNMODE_INV:
            return self.FNMODE_SPCL
        return None


# The quirk table. Append new device-specific input fixes here.
device_quirks_lst: 'list[DeviceQuirk]' = [
    TouchBarFnQuirk(),
    TouchBarT1FnQuirk(),
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
        quirk.recover_stale_state()
        quirk.announce_startup()
        active_quirks_lst.append(quirk)
    return active_quirks_lst


def shutdown_device_quirks(active_quirks_lst: 'list[DeviceQuirk]'):
    """
    Give every active quirk the chance to put its device back as it was found.
    Called on keymapper shutdown, possibly more than once. A failing quirk must
    not get in the way of the rest of the shutdown, so it is reported and skipped.
    """
    for quirk in active_quirks_lst:
        try:
            quirk.shutdown()
        except Exception as quirk_err:
            error(f'{quirk.name}: failed during shutdown: {quirk_err}', ctx=QUIRK_CTX)


# End of file #
