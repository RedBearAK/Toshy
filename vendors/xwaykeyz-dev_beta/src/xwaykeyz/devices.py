# src/xwaykeyz/devices.py
# Async startup version - waits for devices to be idle before grabbing

import os
import re
import errno
import asyncio
import hashlib
import time

from asyncio import AbstractEventLoop
from evdev import ecodes, InputDevice, InputEvent, list_devices
from typing import List

from .lib.logger import debug, error, info
from .models.key import Key
from .output import VIRT_DEVICE_PREFIX


QWERTY = [Key.Q, Key.W, Key.E, Key.R, Key.T, Key.Y]
A_Z_SPACE = [Key.SPACE, Key.A, Key.Z]


# Pattern to detect synthetic device IDs:
# b0019:v0000:p0001:e0000:n51dc9927  (with optional @phys suffix)
_synth_id_prefix_rgx = re.compile(
    r'^b[0-9a-f]{4}:v[0-9a-f]{4}:p[0-9a-f]{4}:e[0-9a-f]{4}:n[0-9a-f]{8}')


def check_input_permissions():
    """
    Advisory check of the user's access to '/dev/input/' event nodes.

    Returns a (perms_ok, message) tuple. The check fails only when NO event
    node is readable and writable, which usually means the user is not in the
    'input' group or the udev rule has not been applied. A node that just
    appeared (e.g. a Bluetooth device reconnecting at login) stays root-only
    for a moment until udev applies the group/mode/ACL, so a few inaccessible
    nodes alongside accessible ones is normal and is reported as a warning
    message with perms_ok still True. Devices.all() skips nodes it cannot
    open, and the inotify ATTRIB handler grabs them once udev fixes them.
    """

    # Check if /dev/input/ directory exists and is accessible
    if not os.path.exists('/dev/input'):
        return False, "'/dev/input/' directory does not exist"

    try:

        # Try to list directory contents
        device_files = os.listdir('/dev/input')
        if not device_files:
            return True, "'/dev/input/' directory is empty but accessible"

        event_nodes = [f for f in device_files if f.startswith('event')]
        if not event_nodes:
            return True, "No event devices found, but '/dev/input/' is accessible"

        inaccessible = []
        for file in event_nodes:
            event_path = f'/dev/input/{file}'
            if not os.access(event_path, os.R_OK | os.W_OK):
                inaccessible.append(file)

        if len(inaccessible) == len(event_nodes):
            return False, (
                f"No read/write access to any of the {len(event_nodes)} "
                f"event device(s) in '/dev/input/'"
            )

        if inaccessible:
            return True, (
                f"{len(inaccessible)} of {len(event_nodes)} event device(s) not yet "
                f"accessible (udev may still be applying permissions): {inaccessible}"
            )

        # Every event device is accessible
        return True, None

    except PermissionError as e:
        return False, f"Permission error accessing '/dev/input/': {e}"
    except Exception as e:
        return False, f"Error checking input device permissions: {e}"


class Devices:
    @staticmethod
    def is_keyboard(device: InputDevice):
        """Guess the device is a keyboard or not"""
        capabilities = device.capabilities(verbose=False)
        if 1 not in capabilities:
            return False
        supported_keys = capabilities[1]

        qwerty = all(k in supported_keys for k in QWERTY)
        az = all(k in supported_keys for k in A_Z_SPACE)
        if qwerty and az:
            return True
        # Otherwise, its not a keyboard!
        return False

    @staticmethod
    def all():
        """Get all available input devices, skipping any that fail to initialize"""
        devices = []
        for path in reversed(list_devices()):
            try:
                device = InputDevice(path)
                devices.append(device)
            except (OSError, BrokenPipeError) as err:
                # OSError covers IOError, PermissionError, FileNotFoundError
                # BrokenPipeError is explicitly caught for clarity (it's a subclass of OSError)
                error(f"Skipping device '{path}': {err.__class__.__name__}: {err}")
                continue
        return devices

    @staticmethod
    def _event_number(device: InputDevice):
        """Extract numeric event ID from device path for sorting."""
        # device.path is like '/dev/input/event6'
        name = os.path.basename(device.path)
        if isinstance(name, str) and name.startswith('event'):
            try:
                return int(name[5:])
            except ValueError:
                pass
        return float('inf')

    @staticmethod
    def _build_by_id_map():
        """Build a reverse lookup from realpath → by-id symlink full path."""
        by_id_dir = '/dev/input/by-id'
        by_id_map = {}
        if not os.path.isdir(by_id_dir):
            return by_id_map
        try:
            for entry in os.listdir(by_id_dir):
                full_path = os.path.join(by_id_dir, entry)
                if os.path.islink(full_path):
                    real = os.path.realpath(full_path)
                    by_id_map[real] = full_path
        except OSError:
            pass
        return by_id_map

    @staticmethod
    def _build_synth_id(device: InputDevice):
        """Build a synthetic device identifier from kernel info fields
        and a short hash of the device name, with optional phys suffix."""
        info        = device.info
        name_hash   = hashlib.md5(device.name.encode()).hexdigest()[:8]
        synth_id    = (
            f"b{info.bustype:04x}:v{info.vendor:04x}"
            f":p{info.product:04x}:e{info.version:04x}"
            f":n{name_hash}"
        )
        phys = device.phys if device.phys else ''
        if phys:
            synth_id += f"@{phys}"
        return synth_id

    @staticmethod
    def print_list():
        """Print all input devices in a readable multi-line format."""

        devices: 'list[InputDevice]' = Devices.all()
        if not devices:
            print("No input devices found.")
            print()
            return

        # Sort by event number for predictable ordering
        devices.sort(key=Devices._event_number)

        # Build reverse lookup for by-id symlinks
        by_id_map = Devices._build_by_id_map()

        sep = "               --"

        print(  '\n  The "Synthetic ID" string is composed of evdev-reported info:\n'
                '  bustype : vendor : product : version : name_hash @ physical_bus\n'
        )

        for device in devices:
            by_id_path  = by_id_map.get(os.path.realpath(device.path), '')
            phys        = device.phys if device.phys else ''
            uniq        = device.uniq if device.uniq else ''
            synth_id    = Devices._build_synth_id(device)

            print(f"  Device Path:   {device.path}")

            if phys:
                print(f"  Bus Path:      {phys}")

            print(f"  Device Name:   {device.name}")

            if by_id_path:
                print(f"  Device ID:     {by_id_path}")

            if uniq:
                print(f"  Device Uniq:   {uniq}")

            print(f"  Synthetic ID:  {synth_id}")

            print(sep)

        print()


class DeviceGrabError(IOError):
    pass


class DeviceRegistry:
    def __init__(self, loop, input_cb, filterer):
        self._devices: List[InputDevice] = []
        self._loop: AbstractEventLoop = loop
        self._input_cb = input_cb
        self._filter: DeviceFilter = filterer
        # Keys pressed on each grabbed device since we grabbed it, by device
        # path. A release of any OTHER key means its press reached the desktop
        # before the grab, so the desktop still has that key down.
        self._down_since_grab: dict = {}

    def __contains__(self, device):
        return device in self._devices

    def cares_about(self, device):
        return self._filter.filter(device)

    def _safe_input_cb(self, device):
        try:
            events = self._input_cb(device)
            if isinstance(events, list) and isinstance(device, InputDevice):
                self._repair_stuck_keys(device, events)
        except OSError as e:
            if e.errno == errno.ENODEV:
                error(f"ENODEV on '{device.name}' ({device.path}) - device removed")
                try:
                    self.ungrab(device)
                except Exception:
                    pass
            else:
                raise

    async def autodetect(self):
        """
        Async version of autodetect - finds keyboards and grabs them,
        waiting for each device to be idle (no keys held) before grabbing.
        """
        # Advisory permission check. This must NOT return early: a single node
        # that udev has not fixed up yet would otherwise block grabbing every
        # keyboard that IS accessible. Devices.all() skips what it cannot open,
        # and the hotplug handler grabs nodes once their permissions change.
        perms_ok, perms_msg = check_input_permissions()
        if not perms_ok:
            error(f"Input permission issue: {perms_msg}")
            error("Please ensure you have r/w permissions on /dev/input/* "
                  "(membership in 'input' group, udev rules applied)")
            info("Continuing anyway. Devices will be grabbed if/when they become accessible.")
        elif perms_msg:
            info(f"Input permission note: {perms_msg}")

        # Get all available devices (regardless of type)
        all_devices = Devices.all()

        if not all_devices:
            error("No input devices found at all in /dev/input/*")
            info("Continuing to run and waiting for devices to be connected...")
            return

        # Filter for matching devices (keyboards)
        matching_devices = list(filter(self._filter.filter, all_devices))

        if not matching_devices:
            # User specified devices with -d/--devices flag (or devices_api call in config)
            if self._filter.matches:
                error(f"Specified device(s) not found: {', '.join(self._filter.matches)}")
            else:
                error("No keyboard devices detected among available input devices")
                debug(f"Found {len(all_devices)} non-keyboard input devices")

            info("Continuing to run and waiting for compatible devices...")
            return

        # Grab all matching devices using async grab
        for device in matching_devices:
            await self.grab(device)

    async def _wait_for_device_idle(self, device: InputDevice, max_wait=5.0, quiet_period=0.15):
        """
        Wait for device to be idle with no key activity for quiet_period seconds.
        
        Checks both instantaneous key state (via active_keys) and buffered events
        (via read_one). This catches rapid tap-tap-tap patterns that instantaneous
        checks alone would miss.
        
        Returns True if device became idle, False if timed out or device error.
        """
        start_time              = time.monotonic()
        last_activity           = time.monotonic()
        poll_interval           = 0.02        # 20ms between checks
        
        while time.monotonic() - start_time < max_wait:
            # Check instantaneous key state
            try:
                active = device.active_keys()
                if active:
                    debug(f"Waiting for '{device.name}' to be idle, held keys: {active}")
                    last_activity = time.monotonic()
            except OSError as e:
                error(f"Device '{device.name}' error checking active keys: {e}")
                return False  # Device gone
            
            # Check for buffered events
            # We can consume these safely - we don't own the device yet, so the
            # compositor/desktop is still receiving events through its own fd.
            # This just lets us detect activity.
            try:
                while True:
                    event: InputEvent = device.read_one()
                    if event is None:
                        break
                    # Only keyboard key events reset the idle timer - ignore EV_REL
                    # (mouse movement), EV_ABS (touchpad), EV_SYN, etc.
                    # This allows mice and combo devices to be grabbed immediately
                    # while still protecting against mid-keypress keyboard grabs.
                    if event.type == ecodes.EV_KEY:
                        debug(f"Device '{device.name}' has buffered key event, resetting idle timer")
                        last_activity = time.monotonic()
            except BlockingIOError:
                pass  # No events waiting, that's fine
            except OSError as e:
                error(f"Device '{device.name}' error reading events: {e}")
                return False  # Device gone
            
            # Have we been quiet long enough?
            idle_duration = time.monotonic() - last_activity
            if idle_duration >= quiet_period:
                debug(f"Device '{device.name}' idle for {idle_duration:.3f}s, proceeding with grab")
                return True
            
            await asyncio.sleep(poll_interval)
        
        # Timed out
        return False

    @staticmethod
    def _drain_buffered_events(device: InputDevice):
        """
        Discard events queued on our fd. Called right after a grab: anything
        buffered at that point also reached the desktop directly, so replaying
        it would type those keys twice.
        """
        try:
            while device.read_one() is not None:
                pass
        except BlockingIOError:
            pass
        except OSError:
            pass

    def _repair_stuck_keys(self, device: InputDevice, events: list):
        """
        Clear keys stuck down in the desktop because their press reached it
        before our grab, and their release reached only us.

        libinput only accepts a release from the device that pressed the key,
        and the kernel drops a release for a key it already has up. So inject
        a press and a release into the device's own evdev node while
        ungrabbed: libinput ignores the press (it has the key down already)
        and takes the release. Only keyboard keys, never mouse buttons or
        touchpad touches.
        """
        down = self._down_since_grab.get(device.path)
        if down is None:
            return

        stuck = []
        for event in events:
            if not isinstance(event, InputEvent):
                continue
            if event.type != ecodes.EV_KEY or event.code >= ecodes.BTN_MISC:
                continue
            if event.value == 1:
                down.add(event.code)
            elif event.value == 0:
                if event.code in down:
                    down.discard(event.code)
                else:
                    stuck.append(event.code)

        if not stuck:
            return

        info(f"Releasing keys stuck in the desktop from '{device.name}': {stuck}")
        try:
            device.ungrab()
            for code in stuck:
                device.write(ecodes.EV_KEY, code, 1)
                device.write(ecodes.EV_SYN, ecodes.SYN_REPORT, 0)
                device.write(ecodes.EV_KEY, code, 0)
                device.write(ecodes.EV_SYN, ecodes.SYN_REPORT, 0)
            # Everything queued while ungrabbed, our injected events included,
            # also reached the desktop directly.
            self._drain_buffered_events(device)
        except OSError as err:
            error(f"{err.__class__.__name__} repairing stuck keys on '{device.name}': {err}")

        try:
            device.grab()
        except OSError as err:
            # Ungrabbed but still being read by us would double every keystroke.
            # Drop the device entirely; hotplug handling can bring it back.
            error(f"{err.__class__.__name__} re-grabbing '{device.name}' after repair: {err}")
            self.ungrab(device)

    async def grab(self, device):
        """
        Async grab that waits for device to be idle before grabbing.

        A grab must not span a key release the desktop is waiting for. If a
        key goes down before the grab and comes up after it, the desktop saw
        the press but only we get the release, and libinput then treats the
        key as held forever (ignoring every later press of it, from any
        device). So: wait for idle, grab, then verify with the kernel's exact
        key state. If anything is held, let go so the release reaches the
        desktop, wait for idle again, and retry. Past the time budget we grab
        anyway and _repair_stuck_keys() clears the key when its release
        arrives.
        """
        if not isinstance(device, InputDevice):
            return

        info(f"Grabbing '{device.name}' ({device.path})", ctx="+K")

        # ─── WAIT FOR DEVICE TO BE IDLE ─────────────────────────────────────────────
        # Wait for sustained quiet period with no keys held and no buffered events.
        # This catches both held keys and rapid tap-tap-tap patterns.

        max_idle_wait           = 5.0       # Maximum seconds to wait for device to be idle
        quiet_period            = 0.15      # Require 150ms of silence before grabbing
        held_deadline           = time.monotonic() + max_idle_wait

        idle_ok = await self._wait_for_device_idle(device, max_idle_wait, quiet_period)

        if not idle_ok:
            # Check if it's because of timeout vs device error
            try:
                active = device.active_keys()
                if active:
                    info(f"Device '{device.name}' still has keys held after {max_idle_wait}s: {active}")
                    info("Grabbing anyway - stuck keys will be repaired when released")
                else:
                    info(f"Device '{device.name}' had continuous activity for {max_idle_wait}s")
                    info("Grabbing anyway - user may experience input glitches")
            except OSError:
                error(f"Device '{device.name}' disappeared while waiting for idle")
                return

        # ─── ATTEMPT GRAB WITH RETRIES ──────────────────────────────────────────────
        # Grab immediately after the idle wait. Any delay here reopens the window
        # for a key to go down before the grab. Sleep only before retrying after
        # a failed grab (EBUSY from another grabber, permissions not settled, etc).
        tries                   = 9
        loop_cnt                = 1
        delay                   = 0.2
        delay_max               = delay * (2 ** (tries - 1))

        while loop_cnt <= tries:
            try:
                device.grab()
            except OSError as err:
                # OSError also inherits/catches PermissionError and IOError
                error(f"{err.__class__.__name__} grabbing '{device.name}' ({device.path})")
                error(f"Grab attempt {loop_cnt} of {tries}. The error was:\n\t{err}")
                loop_cnt       += 1
                await asyncio.sleep(delay)
                delay           = min(delay * 2, delay_max)   # exponential backoff strategy
                continue

            # Grabbed. From here on only we receive this device's events.
            self._drain_buffered_events(device)

            try:
                held = device.active_keys()
            except OSError:
                error(f"Device '{device.name}' disappeared right after grab")
                try:
                    device.ungrab()
                except OSError:
                    pass
                return

            if held and time.monotonic() < held_deadline:
                # Kernel state is exact here: these keys went down before the
                # grab, so the desktop saw the press and needs the release.
                # The deadline shares the idle-wait budget, so a key held the
                # whole time costs max_idle_wait in total, not twice that.
                try:
                    device.ungrab()
                except OSError:
                    pass
                info(f"Keys held on '{device.name}' at grab: {held}. "
                     f"Released grab so the desktop gets the key release, retrying.")
                await self._wait_for_device_idle(device,
                                                 held_deadline - time.monotonic(),
                                                 quiet_period)
                continue

            if held:
                info(f"Keys still held on '{device.name}' after {max_idle_wait}s: {held}")
                info("Grabbing anyway - stuck keys will be repaired when released")

            self._down_since_grab[device.path] = set()
            # Only add reader AFTER successful grab, so no events arrive before
            # we have exclusive access (and before the drain above).
            self._loop.add_reader(device, self._safe_input_cb, device)
            self._devices.append(device)
            info(f"Successfully grabbed '{device.name}' ({device.path})", ctx="+K")
            return

        error(f"Device grab was tried {tries} times and failed. Maybe, another instance is running?")
        error(f"Continuing without device: '{device.name}' ({device.path})")

    def ungrab(self, device: InputDevice):
        info(f"Ungrabbing: '{device.name}' (removed)", ctx="-K")
        self._down_since_grab.pop(device.path, None)
        self._loop.remove_reader(device)
        if device in self._devices:
            self._devices.remove(device)
        try:
            device.ungrab()
        except OSError:
            pass
        try:
            device.close()
        except OSError:
            pass

    def ungrab_by_filename(self, filename):
        for device in self._devices:
            try:
                if device.path == filename:
                    info(f"Ungrabbing by filename: '{filename}'", ctx="-K")
                    self.ungrab(device)
                    return
            except OSError:
                pass

    def ungrab_all(self):
        for device in list(self._devices):
            try:
                self.ungrab(device)
            except OSError:
                pass


class DeviceFilter:
    def __init__(self, matches, ignores=None):
        self.matches = matches
        self.ignores = ignores or []

        if not matches:
            info("Autodetecting all keyboards (no allowlist specified)")

        if self.ignores:
            info(f"Ignore list active for {len(self.ignores)} device(s):")
            for ignored in self.ignores:
                info(f"    '{ignored}'")

    @staticmethod
    def _device_matches(device: InputDevice, candidate: str):
        """Check if a candidate string matches a device by path, name,
        uniq, or synthetic ID.

        Path candidates (starting with '/') are resolved through realpath
        so that /dev/input/by-id/ symlinks match correctly.

        Synthetic ID candidates (matching the b____:v____:... pattern) are
        compared against the device's computed synthetic ID. If the candidate
        includes an @phys suffix, the full ID must match. If the candidate
        omits the @phys suffix, only the model+name portion is compared,
        matching any device with those identifiers regardless of bus path.
        """
        # Synthetic ID match
        if _synth_id_prefix_rgx.match(candidate):
            full_synth_id = Devices._build_synth_id(device)
            # Candidate includes @phys — require exact full match
            if '@' in candidate:
                return full_synth_id == candidate
            # Candidate is model+name only — compare without @phys
            short_synth_id = full_synth_id.split('@', 1)[0]
            return short_synth_id == candidate

        # Path match (resolve symlinks for by-id support)
        if candidate.startswith('/'):
            return os.path.realpath(candidate) == os.path.realpath(device.path)

        # Name match
        if device.name == candidate:
            return True

        # Uniq match (serial number, MAC address, etc.)
        if device.uniq and device.uniq == candidate:
            return True

        return False

    def is_virtual_device(self, device: InputDevice):
        if VIRT_DEVICE_PREFIX in device.name:
            return True

        from .output import _uinput

        if _uinput.device == device:
            return True

        return False

    def filter(self, device: InputDevice):

        # Check ignore list first — takes priority over everything,
        # including an explicit allowlist from only_devices/--devices.
        if self.ignores:
            for ignored in self.ignores:
                if self._device_matches(device, ignored):
                    info(f"Ignoring device: "
                            f"'{device.name}' ({device.path})")
                    if ignored != device.path and ignored != device.name:
                        info(f"    resolved from: '{ignored}'")
                    return False

        # Match by device path or name, if no keyboard devices specified,
        # picks up keyboard-ish devices.
        if self.matches:
            for match in self.matches:
                if self._device_matches(device, match):
                    return True
            return False

        # Exclude our own emulated devices to prevent feedback loop
        if self.is_virtual_device(device):
            return False

        # Exclude none keyboard devices
        return Devices.is_keyboard(device)


# End of file #
