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
    """Check if user has appropriate permissions to /dev/input/ without requiring a keyboard"""

    # Check if /dev/input/ directory exists and is accessible
    if not os.path.exists('/dev/input'):
        return False, "'/dev/input/' directory does not exist"

    try:

        # Try to list directory contents
        device_files = os.listdir('/dev/input')
        if not device_files:
            return True, "'/dev/input/' directory is empty but accessible"

        # Check permissions on at least one event device if available
        for file in device_files:
            if file.startswith('event'):
                event_path = f'/dev/input/{file}'

                # Check read permission
                if not os.access(event_path, os.R_OK):
                    return False, f"No read permission on '{event_path}'"

                # Check write permission
                if not os.access(event_path, os.W_OK):
                    return False, f"No write permission on '{event_path}'"

                # Found at least one accessible event device
                return True, None

        return True, "No event devices found, but '/dev/input/' is accessible"

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

    def __contains__(self, device):
        return device in self._devices

    def cares_about(self, device):
        return self._filter.filter(device)

    def _safe_input_cb(self, device):
        try:
            self._input_cb(device)
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
        # First check permissions independently of device availability
        perms_ok, perms_msg = check_input_permissions()
        if not perms_ok:
            error(f"Input permission issue: {perms_msg}")
            error("Please ensure you have r/w permissions on /dev/input/*")
            # Continue running instead of exiting, but log clearly
            info("Waiting for permissions to be fixed...")
            return

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

    async def grab(self, device):
        """
        Async grab that waits for device to be idle before grabbing.
        This prevents state corruption when users have keys held during startup.
        """
        if not isinstance(device, InputDevice):
            return

        info(f"Grabbing '{device.name}' ({device.path})", ctx="+K")

        # ─── WAIT FOR DEVICE TO BE IDLE ─────────────────────────────────────────────
        # Wait for sustained quiet period with no keys held and no buffered events.
        # This catches both held keys and rapid tap-tap-tap patterns.
        
        max_idle_wait           = 5.0       # Maximum seconds to wait for device to be idle
        quiet_period            = 0.15      # Require 150ms of silence before grabbing
        
        idle_ok = await self._wait_for_device_idle(device, max_idle_wait, quiet_period)
        
        if not idle_ok:
            # Check if it's because of timeout vs device error
            try:
                active = device.active_keys()
                if active:
                    info(f"Device '{device.name}' still has keys held after {max_idle_wait}s: {active}")
                else:
                    info(f"Device '{device.name}' had continuous activity for {max_idle_wait}s")
                info("Grabbing anyway - user may experience input glitches")
            except OSError:
                error(f"Device '{device.name}' disappeared while waiting for idle")
                return

        # ─── ATTEMPT GRAB WITH RETRIES ──────────────────────────────────────────────
        tries                   = 9
        loop_cnt                = 1
        delay                   = 0.2
        delay_max               = delay * (2 ** (tries - 1))

        while loop_cnt <= tries:
            try:
                await asyncio.sleep(delay)
                device.grab()
                # Only add reader AFTER successful grab - this is the key fix!
                # Previously add_reader was called before grab, creating a window
                # where events could arrive before we had exclusive access.
                self._loop.add_reader(device, self._safe_input_cb, device)
                self._devices.append(device)
                info(f"Successfully grabbed '{device.name}' ({device.path})", ctx="+K")
                return
            except OSError as err:
                # OSError also inherits/catches PermissionError and IOError
                error(f"{err.__class__.__name__} grabbing '{device.name}' ({device.path})")
                error(f"Grab attempt {loop_cnt} of {tries}. The error was:\n\t{err}")
            loop_cnt           += 1
            delay               = min(delay * 2, delay_max)   # exponential backoff strategy

        error(f"Device grab was tried {tries} times and failed. Maybe, another instance is running?")
        error(f"Continuing without device: '{device.name}' ({device.path})")

    def ungrab(self, device: InputDevice):
        info(f"Ungrabbing: '{device.name}' (removed)", ctx="-K")
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
