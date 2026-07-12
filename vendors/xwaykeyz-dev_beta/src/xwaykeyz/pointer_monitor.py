"""
src/xwaykeyz/pointer_monitor.py

Read-only monitor for pointer devices (touchpads, mice), used to resume
suspended modifier keys when the user interacts with a pointing device.

Any pointer activity during a held-modifier suspend window is treated as
intent to use that modifier with the pointer, so suspended modifiers are
resumed immediately. Both motion and discrete events count: relative
motion (REL_X/REL_Y) and wheel on mice, absolute position/pressure/
contact on touchpads, and the button/touch press range on both. Hardware
and driver filtering (and disable-while-typing) already reject ghost and
palm touches, so a reported pointer event is a real, intentional
interaction; this module does not second-guess it.

Motion matters because a discrete click is often the LAST event in a
gesture, not the first. A physical clickpad press or a mouse click that
the monitor sees has, by then, already reached the compositor through
libinput in parallel (the devices are not grabbed). Resuming on the
earlier motion of the same gesture lands the modifier on output before
the click, removing the race. Touchpad taps still work via their
BTN_TOUCH contact, which precedes libinput's synthesized click.

The one case no in-stream signal can rescue is a genuinely motionless
click on a precursor-less device (a mouse, or a trackball, clicked with
no preceding motion). Its only event is the button press itself, seen
too late. For that case this module keeps a passive recency timestamp:
pointer devices are watched continuously (not just during the suspend
window), the time of the most recent pointer activity is recorded, and
suspend_keys() consults recent_activity_within() at modifier-press time.
If the pointer was used within the recency window just before the
modifier went down, the modifier is resumed proactively, so a motionless
click that follows lands into an already-held modifier. Only a click
with no pointer activity at all in the preceding window remains
unrescuable; that residual is the documented floor of the no-grab
design.

Passive watching is epoll-driven: readers sit in the event loop and the
kernel wakes them only when real events arrive, so an idle pointer costs
nothing. Each wakeup stamps the activity time and drains the device.
While a suspend window is active (_window_active, set by listen() and
cleared by unlisten() from suspend_keys()/resume_keys() in transform.py)
the same reader additionally triggers an immediate resume on any pointer
activity. Because the passive reader continuously consumes events, the
fds never back up and no stale event from before the window can trigger
a spurious resume.

Devices are opened without grabbing or isolating; libinput and the
compositor continue to own all pointer behavior.

Two monitoring modes share identical trigger criteria (any pointer
activity, per _event_is_pointer_activity) and differ only in reader
lifecycle and whether the recency rescue is available:

  - Passive mode (_PASSIVE_WATCH_ENABLED = True, the default): readers
    are registered continuously from start_passive_watch, stamping the
    recency time always and triggering an in-window resume on activity.
    This mode gets both the broad-trigger physical-click fix and the
    motionless-click recency rescue.

  - Window-only mode (_PASSIVE_WATCH_ENABLED = False): readers are
    registered only inside the suspend window (listen/unlisten), giving
    strict zero-cost-when-idle for low-resource systems (old laptops and
    MacBooks, typically touchpad-only). It keeps the same broad triggers,
    so the physical-click fix is retained; it lacks only the recency
    rescue for motionless precursor-less clicks, since nothing stamps
    activity outside the window.

The broad trigger criteria — including motion and absolute axes — is
what fixes the touchpad physical-click race, in BOTH modes, independent
of the passive layer. The passive layer adds only the recency stamp.

Hotplug pickup is lazy and rate-limited: /dev/input is re-listed at most
once per _RESCAN_MIN_INTERVAL seconds, at listen() time, and a rescan
only runs when the set of device paths actually changed. Newly scanned
devices have a reader registered immediately when readers should
currently be registered (passive watching active, or a window open).
"""

__version__ = '20260626'

import time

from evdev import ecodes, InputDevice, list_devices

from .output import VIRT_DEVICE_PREFIX
from .lib.logger import debug, error


PTR_LOG_PFX = '--> POINTER'
PTR_DBG_CTX = 'PT'

# Seconds of look-back for the motionless-click rescue. Pointer activity
# this recent, immediately before a modifier press, is taken as intent to
# use the modifier with the pointer, so the modifier is resumed at press
# time rather than waiting for (and racing) a later click.
_POINTER_RECENCY_WINDOW = 0.25

# Master switch for the always-on passive watch. True keeps pointer
# readers registered continuously (recency-flag rescue enabled); the
# window-only fallback that registers readers solely inside the suspend
# window is the prior behavior and will branch from this seam when the
# config toggle is added. Hardcoded on for now.
_PASSIVE_WATCH_ENABLED = True

# Button-range and touch-contact key events that signal pointer intent.
# A press event (value == 1) of any of these resumes suspended modifiers.
_TRIGGER_KEY_CODES = frozenset([
    ecodes.BTN_BACK,
    ecodes.BTN_EXTRA,
    ecodes.BTN_FORWARD,
    ecodes.BTN_LEFT,
    ecodes.BTN_MIDDLE,
    ecodes.BTN_RIGHT,
    ecodes.BTN_SIDE,
    ecodes.BTN_TASK,
    ecodes.BTN_TOUCH,
])

# Wheel-only relative codes. Kept as a narrow PUBLIC set because
# transform.py imports it for the grabbed-device wheel-resume check in
# on_event() — that path intentionally resumes on wheel only, not on
# motion, and must not be widened here. The HI_RES codes may be missing
# from older evdev/kernel-header builds; their kernel ABI values are
# fixed, so a numeric fallback is safe.
TRIGGER_REL_CODES = frozenset([
    ecodes.REL_WHEEL,
    ecodes.REL_HWHEEL,
    getattr(ecodes, 'REL_WHEEL_HI_RES', 0x0b),
    getattr(ecodes, 'REL_HWHEEL_HI_RES', 0x0c),
])

# Minimum seconds between /dev/input rescans (hotplug pickup is lazy).
_RESCAN_MIN_INTERVAL = 20.0

_devices_dct: 'dict[str, InputDevice]'  = {}
_known_paths: 'set[str]'                = set()
_last_scan_time                         = 0.0
_last_activity_time                     = 0.0
_listening                              = False
_window_active                          = False
_passive_active                         = False
_loop                                   = None
_resume_fn                              = None


def _device_is_monitorable(device: InputDevice):
    """True for pointer devices worth monitoring: touchpads (BTN_TOUCH plus
    absolute axes) and mice (BTN_LEFT plus relative axes). Touchscreens
    (INPUT_PROP_DIRECT) and our own virtual output device are excluded.
    Grabbed devices may qualify but are silent on a read-only fd, which is
    harmless; non-grabbed combo keyboard/mouse devices qualify usefully.
    """
    if VIRT_DEVICE_PREFIX in device.name:
        return False

    try:
        caps_dct    = device.capabilities(verbose=False)
        props_lst   = device.input_props()
    except (OSError, AttributeError):
        return False

    if ecodes.INPUT_PROP_DIRECT in props_lst:
        return False

    keys_lst = caps_dct.get(ecodes.EV_KEY, [])

    if ecodes.BTN_TOUCH in keys_lst and ecodes.EV_ABS in caps_dct:
        return True
    if ecodes.BTN_LEFT in keys_lst and ecodes.EV_REL in caps_dct:
        return True

    return False


def _readers_should_be_registered():
    """Whether device readers should currently be registered on the loop.
    In always-on passive mode, readers are registered whenever passive
    watching has started. In window-only mode, readers exist only while a
    suspend window is open (_listening)."""
    if _PASSIVE_WATCH_ENABLED:
        return _passive_active
    return _listening


def _add_reader(device: InputDevice):
    """Register the reader for one device on the event loop, if readers
    should currently be registered and a loop is available. Safe to call
    repeatedly; the loop replaces any existing reader for the same fd. In
    always-on mode this is the passive recency reader; in window-only mode
    it is the in-window trigger reader. Same callback either way."""
    if not _readers_should_be_registered() or _loop is None:
        return
    try:
        _loop.add_reader(device.fileno(), _on_readable, device)
    except OSError:
        _close_device(device.path)


def _close_device(path):
    device = _devices_dct.pop(path, None)
    # Forget the path so the next rate-limited check sees a set
    # difference and triggers a rescan (covers transient errors).
    _known_paths.discard(path)
    if device is None:
        return
    # Remove the reader only if one should currently be registered for it.
    # In window-only mode that is only while listening; in passive mode it
    # is whenever passive watching is active. Guarding avoids spurious
    # remove_reader calls on fds the loop isn't watching.
    if _readers_should_be_registered() and _loop is not None:
        try:
            _loop.remove_reader(device.fileno())
        except (OSError, ValueError):
            pass
    try:
        device.close()
    except OSError:
        pass


def _scan_devices():
    global _last_scan_time
    paths_lst       = list_devices()
    _last_scan_time = time.monotonic()

    # Drop devices whose nodes disappeared
    for path in [p for p in _devices_dct if p not in paths_lst]:
        _close_device(path)

    _known_paths.clear()
    _known_paths.update(paths_lst)

    # Probe paths we are not already holding open
    for path in paths_lst:
        if path in _devices_dct:
            continue
        try:
            device = InputDevice(path)
        except OSError:
            continue
        if not _device_is_monitorable(device):
            device.close()
            continue
        _devices_dct[path] = device
        debug(f"{PTR_LOG_PFX}: watching '{device.name}' ({path})", ctx=PTR_DBG_CTX)
        # New device picked up mid-run: give it a passive reader now so
        # it contributes recency stamps (and in-window triggers) without
        # waiting for the next listen().
        _add_reader(device)


def _drain_device(device: InputDevice):
    """Discard buffered events without stamping or triggering."""
    try:
        while device.read_one() is not None:
            pass
    except BlockingIOError:
        pass


def _event_is_pointer_activity(event):
    """The single pointer-intent test, used by both modes. Any real
    pointer activity counts: a button/touch PRESS, or any relative or
    absolute motion/wheel/pressure event. A button RELEASE is not fresh
    intent and is excluded.

    Motion and absolute axes are included deliberately. In either mode
    they let an earlier event in a gesture trigger the resume before the
    consequential click: touchpad contact/pressure/motion precede the
    physical clickpad BTN_LEFT, and mouse motion precedes a moved-then-
    clicked selection. This broad criteria is what fixes the touchpad
    physical-click race, independent of the always-on passive layer. The
    passive layer adds only the recency stamp that additionally rescues a
    motionless click; it does not change what counts as activity."""
    if event.type == ecodes.EV_KEY:
        return event.value == 1 and event.code in _TRIGGER_KEY_CODES
    if event.type == ecodes.EV_REL:
        return True
    if event.type == ecodes.EV_ABS:
        return True
    return False


def _on_readable(device: InputDevice):
    """Reader callback, used in both modes. Both modes use the same broad
    pointer-activity criteria; only the lifecycle and the recency stamp
    differ.

    Passive mode (_PASSIVE_WATCH_ENABLED): the reader is always
    registered. It stamps the recency time on every pointer-activity
    event, and while a suspend window is active (_window_active) resumes
    suspended modifiers on the first such event.

    Window-only mode: the reader is registered only while listening
    (_listening), so its mere existence means a window is open. It does
    not stamp recency (no recency consult happens in this mode), but
    triggers on the same broad criteria — so the touchpad physical-click
    fix is retained here; only the motionless-click recency rescue is
    absent.

    Either way the device is drained each wakeup, so fds never back up
    and pre-window events cannot linger to trigger spuriously."""
    global _last_activity_time
    passive = _PASSIVE_WATCH_ENABLED
    try:
        while True:
            event = device.read_one()
            if event is None:
                break
            if not _event_is_pointer_activity(event):
                continue

            if passive:
                _last_activity_time = time.monotonic()
                window_open = _window_active
            else:
                window_open = _listening

            if not window_open:
                continue

            debug(f"{PTR_LOG_PFX}: trigger event (type {event.type}, "
                    f"code {event.code}) on '{device.name}', resuming suspended keys",
                    ctx=PTR_DBG_CTX)
            # resume_keys() in transform.py calls unlisten(), clearing the
            # window flags. In passive mode the reader stays registered for
            # continued stamping; in window-only mode unlisten() removes it.
            # Returning is fine either way — remaining buffered events are
            # consumed on the next wakeup (passive) or after the next
            # listen() drain (window-only).
            _resume_fn()
            return
    except BlockingIOError:
        pass
    except OSError:
        error(f"{PTR_LOG_PFX}: lost device '{device.name}', dropping it")
        _close_device(device.path)


def start_passive_watch(loop):
    """Begin always-on passive watching of pointer devices. Called once
    from the keymapper startup (main_loop in input.py) after the event
    loop and devices exist. Registers a reader per device that records
    pointer-activity times continuously, enabling the motionless-click
    recency rescue. No-op when passive watching is disabled or already
    started."""
    global _last_scan_time, _loop, _passive_active
    if not _PASSIVE_WATCH_ENABLED or _passive_active:
        return

    _loop = loop
    _scan_devices()
    _last_scan_time = time.monotonic()
    _passive_active = True

    for device in list(_devices_dct.values()):
        _add_reader(device)


def recent_activity_within(window=_POINTER_RECENCY_WINDOW):
    """True if pointer activity was recorded within the given look-back
    (default _POINTER_RECENCY_WINDOW seconds). Consulted by suspend_keys()
    at modifier-press time to proactively resume when the pointer was just
    used, rescuing a motionless click that is about to follow."""
    if not _passive_active:
        return False
    if _last_activity_time == 0.0:
        return False
    return (time.monotonic() - _last_activity_time) <= window


def listen(loop, resume_callback):
    """Open the suspend window: from now until unlisten(), pointer
    activity resumes suspended modifiers immediately. Called from
    suspend_keys() in transform.py. Idempotent while the window is
    already open (the resuspend path calls suspend_keys() again).

    Passive mode: readers are already registered from start_passive_watch,
    so this refreshes the resume callback, runs lazy hotplug pickup, and
    flips _window_active. The continuously-draining passive reader means
    nothing is buffered to go stale.

    Window-only mode: this registers a reader per device and drains it
    (the original behavior). _listening is set before registering so the
    _readers_should_be_registered() gate inside _add_reader passes."""
    global _last_scan_time, _listening, _loop, _resume_fn, _window_active
    if _listening:
        return

    _loop           = loop
    _resume_fn      = resume_callback
    _listening      = True
    _window_active  = True

    now = time.monotonic()
    if now - _last_scan_time > _RESCAN_MIN_INTERVAL:
        if set(list_devices()) != _known_paths:
            _scan_devices()
        else:
            _last_scan_time = now

    # Passive mode already has readers up; this re-adds harmlessly (the
    # loop replaces a reader for an fd it already watches) and drains any
    # straggler. Window-only mode registers readers here for the first
    # time. The drain guards against pre-window events triggering a resume.
    for device in list(_devices_dct.values()):
        _add_reader(device)
        _drain_device(device)


def unlisten():
    """Close the suspend window. Called from resume_keys() in
    transform.py, the single teardown path for all resume causes (timer
    expiry, key events, pointer activity).

    Passive mode: readers stay registered for continued recency stamping;
    only the in-window trigger behavior is switched off.

    Window-only mode: readers are removed, restoring strict zero-cost-
    when-idle. _window_active is cleared first so the removal is not
    mistaken for an in-window teardown by anything inspecting state."""
    global _listening, _window_active
    if not _listening:
        return
    _window_active  = False

    if not _PASSIVE_WATCH_ENABLED and _loop is not None:
        for device in list(_devices_dct.values()):
            try:
                _loop.remove_reader(device.fileno())
            except (OSError, ValueError):
                pass

    _listening = False


# End of file #
