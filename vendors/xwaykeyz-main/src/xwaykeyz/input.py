# src/xwaykeyz/input.py
# Async startup version - waits for devices to be idle before grabbing

import signal
import asyncio

from asyncio import Task, TimerHandle
from copy import copy
from inotify_simple import INotify, flags
from inotify_simple import Event as inotify_Event
from sys import exit
from typing import List, Optional

from evdev import InputDevice, InputEvent, ecodes
from evdev.eventio import EventIO

from . import config_api, transform
from .device_quirks import DeviceQuirk, initialize_device_quirks
from .devices import DeviceFilter, DeviceGrabError, DeviceRegistry
from .lib import logger
from .lib.asyncio_utils import get_or_create_event_loop
from .lib.dummy_device import DummyDevice
from .lib.logger import debug, error, info
from .models.action import Action, PRESS, RELEASE, REPEAT
from .models.key import Key
from .transform import boot_config, dump_diagnostics, on_event


CONFIG = config_api
_sup = None
_active_quirks_lst: 'list[DeviceQuirk]' = []


def shutdown():
    loop = get_or_create_event_loop()
    loop.stop()
    transform.shutdown()


def sig_term():
    print("signal TERM received", flush=True)
    shutdown()
    exit(0)


def sig_int():
    print("signal INT received", flush=True)
    shutdown()
    exit(0)


def watch_dev_input():
    inotify = INotify()
    inotify.add_watch("/dev/input", flags.CREATE | flags.ATTRIB | flags.DELETE)
    return inotify


# Why? xmodmap won't persist mapping changes until it's seen at least
# one keystroke on a new device, so we need to give it something that
# won't do any harm, but is still an actual keypress, hence shift.
async def wakeup_output():
    """
    Send a synthetic Shift press/release through the transform engine.
    Converted to async to use proper async sleep during startup phase.
    """
    # Store the user's current setting for verbosity
    _verbose_state = copy(logger.VERBOSE)

    # Keep the Shift key cycling events from appearing in the verbose logging at startup
    logger.VERBOSE = False

    # Use a dummy device instead of 'None', cures X11 issue of first mod key press being ignored!
    dummy_device = DummyDevice()
    down = InputEvent(0, 0, ecodes.EV_KEY, Key.LEFT_SHIFT, Action.PRESS)
    up = InputEvent(0, 0, ecodes.EV_KEY, Key.LEFT_SHIFT, Action.RELEASE)
    for ev in [down, up]:
        on_event(ev, dummy_device)
        await asyncio.sleep(0.01)   # Chill after press and release of Shift key

    # Restore the user's setting for verbosity, whether it was True or False
    logger.VERBOSE = _verbose_state



def main_loop(arg_devices, device_watch, ignore_devices=None):
    inotify = None

    boot_config()

    # We will handle device quirks that we cause, if we can.
    # Canonical example: keymapper blocks function of Fn key on
    # Touch Bar Mac models, by grabbing internal keyboard and
    # preventing kernel driver from seeing KEY_FN.
    global _active_quirks_lst
    _active_quirks_lst = initialize_device_quirks()

    if device_watch:
        inotify = watch_dev_input()

    loop = get_or_create_event_loop()
    registry = DeviceRegistry(
        loop,
        input_cb=receive_input,
        filterer=DeviceFilter(arg_devices, ignores=ignore_devices),
    )

    async def async_startup():
        """Run async startup tasks before entering the main event loop."""
        await wakeup_output()
        await registry.autodetect()

    try:
        # Run async startup (wakeup_output and device grabbing) before main loop
        loop.run_until_complete(async_startup())

        # Begin always-on passive pointer watching for the recency-flag
        # rescue (motionless clicks on precursor-less pointing devices).
        transform.pointer_monitor.start_passive_watch(loop)

        if device_watch:
            loop.add_reader(inotify.fd, _inotify_handler, registry, inotify)

        global _sup
        # The old "noqa: F841" comment was to suppress a flake8/Ruff notice about 
        # the "unused local variable" regarding "_sub", which was local.
        # This is cured by the global line, so it actually becomes global.
        # No functional difference overall. The var is only needed to prevent
        # premature garbage collection of the loop, apparently.
        _sup = loop.create_task(supervisor())
        loop.add_signal_handler(signal.SIGINT, sig_int)
        loop.add_signal_handler(signal.SIGTERM, sig_term)
        info("Ready to process input.")
        loop.run_forever()
    except DeviceGrabError:
        loop.stop()
    finally:
        shutdown()
        registry.ungrab_all()
        if device_watch:
            inotify.close()


_tasks: List[Task] = []


async def supervisor():
    while True:
        await asyncio.sleep(5)
        for task in _tasks:
            if task.done():
                if task.exception():
                    import traceback

                    traceback.print_exception(task.exception())
                _tasks.remove(task)


def receive_input(device: EventIO):
    events = list(device.read())

    # Pre-scan: find key codes that have a release event in this batch.
    # Any repeat events for these keys are stale — the user already
    # let go, and the repeats just haven't been processed yet.
    released_in_batch = set()
    for event in events:
        if event.type == ecodes.EV_KEY and event.value == RELEASE:
            released_in_batch.add(event.code)

    for event in events:
        # Drop stale repeat events for keys whose release is already
        # waiting in this same batch. This prevents buffered repeats
        # from continuing to emit output after the user releases a key.
        if (event.type == ecodes.EV_KEY
                and event.value == REPEAT
                and event.code in released_in_batch):
            continue

        if event.type == ecodes.EV_KEY:
            if event.code == CONFIG.EMERGENCY_EJECT_KEY:
                error("BAIL OUT: Emergency eject - shutting down.")
                shutdown()
                exit(0)
            if event.code == CONFIG.DUMP_DIAGNOSTICS_KEY:
                action = Action(event.value)
                # Changed just_pressed to use property decorator, for consistency.
                if action.just_pressed:
                    debug("DIAG: Diagnostics requested.")
                    dump_diagnostics()
                continue

        if _active_quirks_lst and event.type == ecodes.EV_KEY:
            for quirk in _active_quirks_lst:
                quirk.handle_key_event(event.code, event.value, device)

        on_event(event, device)


_add_timer: Optional[TimerHandle] = None
_notify_events = []


def _inotify_handler(registry, inotify: INotify):
    global _add_timer
    global _notify_events

    # Use non-blocking read (timeout 0) to avoid blocking
    # Only process if there are actual events
    events = inotify.read(0)
    if not events:
        return

    _notify_events.extend(events)

    if _add_timer:
        _add_timer.cancel()

    def device_change_task():
        task = loop.create_task(device_change(registry, _notify_events))
        _tasks.append(task)

    loop = asyncio.get_running_loop()
    # slow the roll a bit to allow for udev to change permissions, etc...
    _add_timer = loop.call_later(0.5, device_change_task)


async def device_change(registry, events):

    if not isinstance(registry, DeviceRegistry):
        return

    if not isinstance(events, list):
        return

    while events:
        event = events.pop(0)

        if not isinstance(event, inotify_Event):
            raise TypeError(f"Expected inotify_Event, got {type(event).__name__}")

        # ignore mouse, mice, etc, non-event devices

        # This guard clause lights up '.startswith()' by affirming the string type.
        if not isinstance(event.name, str):
            continue

        if not event.name.startswith("event"):
            continue

        filename = f"/dev/input/{event.name}"

        # deal with a permission problem of unknown origin
        tries                   = 9
        loop_cnt                = 1
        delay                   = 0.2
        delay_max               = delay * (2 ** (tries - 1))

        device = None
        while loop_cnt <= tries:
            try:
                device = InputDevice(filename)
                break  # Successful device initialization, exit retry loop
            except FileNotFoundError:
                registry.ungrab_by_filename(filename)
                break  # Exit retry loop if the device is not found
            except BrokenPipeError as bp_err:
                if loop_cnt == tries:
                    error(f"BrokenPipeError after {tries} attempts for '{filename}':\n\t{bp_err}")
                    error("Device may be in transition (KVM switch?), will retry on next event")
                    break  # Exit retry loop after final attempt
                else:
                    error(  f"Retrying to initialize '{filename}' due to BrokenPipeError. "
                            f"Attempt {loop_cnt} of {tries}.\n\t{bp_err}")
                await asyncio.sleep(delay)
                delay = min(delay * 2, delay_max)
                loop_cnt += 1
            except PermissionError as perm_err:
                if loop_cnt == tries:
                    error(f"PermissionError after {tries} attempts for '{filename}':\n\t{perm_err}")
                    break  # Final attempt due to PermissionError, exit retry loop
                else:
                    error(  f"Retrying to initialize '{filename}' due to PermissionError. "
                            f"Attempt {loop_cnt} of {tries}.\n\t{perm_err}")
                await asyncio.sleep(delay)
                delay = min(delay * 2, delay_max)
                loop_cnt += 1

        if device is None:
            continue

        # unplugging
        if event.mask == flags.DELETE:
            if device in registry:
                registry.ungrab(device)
            continue

        # potential new device - use async grab for hot-plugged devices too
        try:
            if device not in registry:
                if registry.cares_about(device):
                    await registry.grab(device)
        except FileNotFoundError:
            # likely received ATTR right before a DELETE, so we ignore
            continue

# End of file #
