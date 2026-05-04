#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Overlay flag definitions and manipulation helpers.

Module path: toshy_common/overlay_context.py

Provides a bitmask-based system for toggling groups of keymaps and modmaps
on and off at runtime. The config file tags each keymap/modmap with an
OverlayFlag member in its `when` clause; the user's current overlay_mask
setting determines which tagged rules are active.

Recommended import alias at call sites:

    from toshy_common.overlay_context import OverlayFlag as OFlag

Keymap/modmap tag usage (inline bitwise AND in the `when` clause):

    }, when = lambda ctx:
        cnfg.overlay_mask & OFlag.MACOS_GLOBALS and
        cnfg.screen_has_focus and
        hmp_not_term_or_remote(ctx)
    )

Callers (settings class, GUI, tray) use the helper functions here rather
than manipulating the mask directly, so bitwise arithmetic stays in one
place and dependency rules are enforced consistently.
"""

__version__ = '20260429'

from enum import IntFlag

from xwaykeyz.lib.logger import debug


# ─── Flag definitions ──────────────────────────────────────────────
# IntFlag members behave as ints under bitwise operators (&, |, ~, ^) but
# carry a readable repr in logs (e.g. <OverlayFlag.MACOS_SHORTCUTS: 1>)
# and allow reverse lookup from int value via OverlayFlag(n).

class OverlayFlag(IntFlag):
    # Built-in overlays (bits 0-6)
    MACOS_GLOBALS           = 1 << 0
    TERMINAL_ERGO           = 1 << 1
    FINDER_MODS             = 1 << 2
    ENTER_TO_RENAME         = 1 << 3
    BROWSER_SHORTCUTS       = 1 << 4
    VSCODE_SHORTCUTS        = 1 << 5
    DIALOG_ERGO             = 1 << 6
    # Reserved for future built-in overlays (bits 7-31).
    # Bit positions are effectively frozen once a stable release ships,
    # since users' saved masks store raw int values. Leaving a wide gap
    # here ensures new built-in overlays can always be added without
    # colliding with user flag bit positions below.
    USER_FLAG_A             = 1 << 32
    USER_FLAG_B             = 1 << 33
    USER_FLAG_C             = 1 << 34
    USER_FLAG_D             = 1 << 35
    USER_FLAG_E             = 1 << 36
    USER_FLAG_F             = 1 << 37


# ─── Composite presets ─────────────────────────────────────────────
# Convenience values for setting the mask to a common configuration.
# NOT for tagging individual keymaps — tags must always be single-bit flags.
# IntFlag supports OR composition, producing a combined-member value.
#
# User flags (USER_FLAG_A through USER_FLAG_F) are intentionally excluded
# from presets. Users opt into them individually by ticking the relevant
# entry in the tray/GUI menu.

OVL_PRESET_FULL             = (OverlayFlag.MACOS_GLOBALS |
                                OverlayFlag.TERMINAL_ERGO |
                                OverlayFlag.FINDER_MODS |
                                OverlayFlag.ENTER_TO_RENAME |
                                OverlayFlag.BROWSER_SHORTCUTS |
                                OverlayFlag.VSCODE_SHORTCUTS |
                                OverlayFlag.DIALOG_ERGO)
OVL_PRESET_MINIMAL          = OverlayFlag.TERMINAL_ERGO
OVL_PRESET_NONE             = OverlayFlag(0)


# ─── Default for new installs ──────────────────────────────────────

DEFAULT_OVERLAY_MASK        = OVL_PRESET_FULL


# ─── Metadata for UI consumption ───────────────────────────────────
# List of (flag, display_name, description) tuples. GUI and tray apps
# iterate this to build checkboxes/menu items dynamically, so adding
# a new flag requires no changes in UI code.

OVL_METADATA = [
    (OverlayFlag.MACOS_GLOBALS, "macOS Globals",
        "Globally-available Mac-style shortcuts shared across all apps."),
    (OverlayFlag.DIALOG_ERGO, "Dialog Ergonomics",
        "Escape to close dialogs and other dialog handling improvements."),
    (OverlayFlag.TERMINAL_ERGO, "Terminal Ergonomics",
        "Cmd+C/V for copy/paste in terminals, SIGINT prevention, per-terminal fixes."),
    (OverlayFlag.FINDER_MODS, "Finder Mods",
        "macOS Finder-style shortcuts in file managers."),
    (OverlayFlag.ENTER_TO_RENAME, "Enter to Rename",
        "Press Enter to rename files (macOS-style). Requires Finder Mods."),
    (OverlayFlag.BROWSER_SHORTCUTS, "Browser Shortcuts",
        "Mac-style remaps in web browsers (Cmd+T, Cmd+W, Cmd+L, etc.)."),
    (OverlayFlag.VSCODE_SHORTCUTS, "VSCode Shortcuts",
        "Mac-style remaps in VSCode, Cursor, VSCodium, and related editors."),
    (OverlayFlag.USER_FLAG_A, "User Flag A",
        "Available for custom keymaps in your config."),
    (OverlayFlag.USER_FLAG_B, "User Flag B",
        "Available for custom keymaps in your config."),
    (OverlayFlag.USER_FLAG_C, "User Flag C",
        "Available for custom keymaps in your config."),
    (OverlayFlag.USER_FLAG_D, "User Flag D",
        "Available for custom keymaps in your config."),
    (OverlayFlag.USER_FLAG_E, "User Flag E",
        "Available for custom keymaps in your config."),
    (OverlayFlag.USER_FLAG_F, "User Flag F",
        "Available for custom keymaps in your config."),
]


# ─── Dependency rules ──────────────────────────────────────────────
# Maps child flag to its required parent flag. When the parent is disabled,
# the child is automatically disabled too (enforced by apply_dependencies()).
# UI code reads this dict to show parent-child relationships (greying out
# child checkboxes when parent is unchecked, hint text, etc.).
#
# Nested dependencies (a child that is also a parent of something else) are
# not supported. Enforced at module load time by _check_no_nested_deps().

OVL_DEPENDENCIES = {
    OverlayFlag.ENTER_TO_RENAME:    OverlayFlag.FINDER_MODS,
    OverlayFlag.DIALOG_ERGO:        OverlayFlag.MACOS_GLOBALS,
}


# ─── Internal: union of all known single-bit flags ─────────────────
# Computed once at module load. Used for flag validation and stray-bit
# detection in active_flags().

_KNOWN_FLAGS = OverlayFlag(0)
# Initialized as OverlayFlag(0) rather than plain `0` so the variable's type
# is consistent from the start. If the loop below were ever skipped (empty
# enum, refactor mishap), this stays an OverlayFlag instead of silently
# becoming a bare int. IntFlag accepts 0 as the "no flags set" state.
for flag in OverlayFlag:
    _KNOWN_FLAGS |= flag


# ─── Load-time sanity checks ───────────────────────────────────────

def _check_no_nested_deps():
    """Ensure no flag is both a parent and a child in OVL_DEPENDENCIES.

    Called at module import. Nested dependencies would require multi-pass
    resolution in apply_dependencies(), which the current implementation
    does not do, so they're rejected outright.
    """
    parents = set(OVL_DEPENDENCIES.values())
    children = set(OVL_DEPENDENCIES.keys())
    nested = parents & children
    if nested:
        raise ValueError(
            f"overlay_context: nested dependencies not supported, "
            f"these flags are both parent and child: {nested}"
        )


_check_no_nested_deps()


# ─── Query functions ───────────────────────────────────────────────

def is_active(mask, flag):
    """Return True if the given flag bit is set in the mask."""
    return bool(mask & flag)


def active_flags(mask):
    """Return a list of single-bit OverlayFlag members set in the mask.

    If the mask contains any bits outside the set of defined flags, a debug
    warning is logged so the anomaly is visible in verbose logging without
    changing behavior.
    """
    stray = mask & ~_KNOWN_FLAGS
    if stray:
        debug(f"overlay_context: mask contains undefined bits: {int(stray):#b}")
    return [flag for flag in OverlayFlag if mask & flag]


# ─── Mutation functions ────────────────────────────────────────────
# All return a new OverlayFlag value rather than mutating in place. Caller
# assigns the return value back to wherever the mask is stored.

def _validate_flag(flag):
    """Raise ValueError if the flag is not a known single-bit flag.

    Accepts only single-bit members of OverlayFlag. Composite values
    (OR-combined flags) are intentionally rejected because mutation
    functions operate on individual flags, not groups.
    """
    flag_int = int(flag)
    if flag_int & ~int(_KNOWN_FLAGS) or flag_int == 0:
        raise ValueError(f"overlay_context: unknown overlay flag: {flag_int:#b}")
    # Single-bit check: a power of 2 has exactly one bit set, so
    # (flag & (flag - 1)) == 0 only for powers of 2.
    if flag_int & (flag_int - 1):
        raise ValueError(
            f"overlay_context: mutation requires a single-bit flag, "
            f"got composite value: {flag_int:#b}"
        )


def enable(mask, flag):
    """Return a new mask with the given flag bit set."""
    _validate_flag(flag)
    return mask | flag


def disable(mask, flag):
    """Return a new mask with the given flag bit cleared."""
    _validate_flag(flag)
    return mask & ~flag


def toggle(mask, flag):
    """Return a new mask with the given flag bit flipped."""
    _validate_flag(flag)
    return mask ^ flag


# ─── Dependency resolution ─────────────────────────────────────────

def apply_dependencies(mask):
    """Return a new mask with dependency rules enforced.

    For each child whose parent is not set, the child is also cleared.
    Used for load-time consistency checks on stored masks.

    The auto-enable behavior (parent transitions off→on enables child)
    is handled by the settings class setter, which has access to the
    previous mask state. This function is for stateless validation.
    """
    result = mask
    for child, parent in OVL_DEPENDENCIES.items():
        if not (result & parent):
            result &= ~child
    return result


# ─── Introspection for GUI/tray ────────────────────────────────────

def get_flag_metadata(flag):
    """Return the (flag, display_name, description) tuple for a flag.

    Returns None if the flag is not found in OVL_METADATA.
    """
    for entry in OVL_METADATA:
        if entry[0] == flag:
            return entry
    return None


def get_flag_parent(flag):
    """Return the parent flag for a given child, or None if no parent."""
    return OVL_DEPENDENCIES.get(flag)


def get_flag_children(flag):
    """Return a list of child flags that depend on the given parent."""
    return [child for child, parent in OVL_DEPENDENCIES.items() if parent == flag]


# End of file #
