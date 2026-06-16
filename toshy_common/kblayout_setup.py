"""
Wiring that connects keyboard-layout detection to the keymapper.

    toshy_common/kblayout_setup.py

Bridges the two sides that deliberately do not import each other: it reads the
keymapper's opt-in flags (set in the config via keyboard_layout_correction) and,
when enabled, starts the detection coordinator with its callback pointed at the
keymapper's correction-map setter. Living here rather than inline in the config
means the config only declares the option and calls one function — all the
coordinator construction, the watcher-thread callback, the option translation,
and the coordinator's lifetime are held in this one place.

The keymapper-side imports are guarded: on a keymapper build that predates the
correction API, this module still imports cleanly and start_kblayout_correction()
reports the feature unavailable and does nothing, so Toshy keeps loading against
an older keymapper.
"""

__version__ = '20260608'

from xwaykeyz.lib.logger import debug, warn

# The layout-correction API (the config flags reader and the keymapper's
# correction-map setter) exists only on keymapper builds that ship it. Import it
# defensively so this module still loads against an older keymapper; the feature
# then simply stays inert (see start_kblayout_correction).
try:
    from xwaykeyz.config_api import layout_correction_options
    from xwaykeyz.layout_correction import set_correction_map
    _CORRECTION_API_AVAILABLE = True
except ImportError:
    _CORRECTION_API_AVAILABLE = False

from toshy_common.kblayout_common import format_layout


# Held at module scope so the coordinator (and the watcher thread it starts)
# stays alive for the lifetime of the keymapper process.
_layout_context = None


def _apply_layout_correction(spec, correction_map, symbol_hints):
    """Coordinator callback; runs on the detector's watcher thread. Names the
    active layout for the keymapper's logs and installs its correction map plus
    the active-layout symbol hints used to annotate corrected keycodes in those
    logs."""
    set_correction_map(correction_map, label=format_layout(spec), symbol_hints=symbol_hints)


def start_kblayout_correction() -> bool:
    """Start the layout-correction coordinator if the feature is enabled.

    Reads the opt-in flags set by keyboard_layout_correction() in the config.
    Returns False (doing nothing) when the keymapper lacks the correction API,
    correction is disabled, already started, or no detection backend is available
    for this environment.
    """
    global _layout_context
    if not _CORRECTION_API_AVAILABLE:
        debug("KBLAYOUT_CORRECTION: keymapper lacks the correction API; "
                "coordinator not started.", ctx="LC")
        return False
    if _layout_context is not None:
        return False                            # already started

    options = layout_correction_options()
    if not options['enabled']:
        debug("KBLAYOUT_CORRECTION: disabled; coordinator not started.", ctx="LC")
        return False

    # Deferred so xkbcommon and the gi/D-Bus detection backends load only when
    # correction is actually enabled, not on every config load.
    from toshy_common.kblayout_context import KeyboardLayoutContext

    number_row = 'glyph' if options['correct_number_row'] else 'positional'
    _layout_context = KeyboardLayoutContext(
        apply_correction_map    = _apply_layout_correction,
        number_row              = number_row,
    )
    if _layout_context.start():
        debug(f"KBLAYOUT_CORRECTION: started (number_row={number_row}).", ctx="LC")
        return True

    warn("Keyboard layout correction is enabled, but no detection backend is "
            "available for this environment; correction stays inert.")
    return False


def stop_kblayout_correction():
    """Stop the coordinator if it was started. Safe to call unconditionally."""
    global _layout_context
    if _layout_context is not None:
        _layout_context.stop()
        _layout_context = None


# End of file #
