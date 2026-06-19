"""Shared keyboard-layout vocabulary for Toshy.

    toshy_common/kblayout_common.py

The single source of truth for how a keyboard layout is represented and how the
"blank" variant is named, so every component — detector, analyzer, keymapper
config, settings, GUI — speaks the same language.

This module is intentionally a dependency-free leaf: it imports nothing from the
rest of Toshy and nothing heavy (no gi, no Xlib, no ctypes), so any component can
import it without pulling in machinery or risking circular imports. Everything
that understands layouts depends on this; this depends on nothing.

The blank XKB variant — the base/default member of a layout's language group —
is represented internally by the token DEFAULT_VARIANT ('default') rather than
'' or None: a stable, truthy, self-describing string. XKB's empty-string form is
confined to the two boundary converters below; everywhere else in Toshy a
variant is a non-empty string.

Besides the layout vocabulary it also holds the shared keycode primitives — the
kernel<->XKB offset, the typing-block and number-row keycode sets, and the
offset helper — because both the analyzer (which builds the correction map) and
the symbol-table builder (which the analyzer imports) need them. Defining them
here, in the leaf both already depend on, keeps the dependency one-directional
and avoids a circular import between those two.
"""

__version__ = '20260616'

from collections import namedtuple


# Canonical token for the blank/base XKB variant. Chosen over '' (falsy, easy to
# mishandle) and None (a sentinel type we avoid). No real XKB variant is named
# 'default', so the token is safe to reserve.
DEFAULT_VARIANT = 'default'


# A keyboard layout as a single atomic value. 'variant' is always a non-empty
# string (a real variant such as 'azerty', or DEFAULT_VARIANT). 'description' is
# an optional human-readable label (e.g. KDE's longName) for display/logging
# only, and is not part of layout identity.
LayoutSpec = namedtuple('LayoutSpec', ['layout', 'variant', 'description'])


# ─── Shared keycode primitives ───────────────────────────────────────────────
# XKB keycodes are offset from kernel (evdev) keycodes by +8. This is a fixed
# property of the XKB/kernel relationship, not a layout property, so it lives in
# the leaf alongside the keycode sets that depend on it.
XKB_KEYCODE_OFFSET = 8

# Kernel keycodes of the digit row, KEY_1..KEY_0. Kept positional by default in
# build_correction_map so Cmd/Ctrl + number shortcuts keep firing from these
# physical keys even on layouts that hide the digits behind Shift (AZERTY), the
# way macOS behaves.
NUMBER_ROW_KEYCODES = frozenset(range(2, 12))

# Kernel keycodes of the main alphanumeric typing block — the letter, digit, and
# punctuation keys a US-authored config references. Correction is confined to
# these so it cannot drag in the extended "internet"/media keys that the evdev
# keymap also defines with duplicate base characters (e.g. a stray base-'$' on a
# high keycode), nor editing keys like CapsLock or Backspace that carry a control
# keysym; those are never sensible correction sources or targets. The symbol-
# table builder extends this set with the space bar for its own purposes; see
# kblayout_symtable.
TYPING_BLOCK_KEYCODES = frozenset(
    list(range(2, 14)) +        # KEY_1..KEY_0, KEY_MINUS, KEY_EQUAL
    list(range(16, 28)) +       # KEY_Q..KEY_RIGHTBRACE
    list(range(30, 42)) +       # KEY_A..KEY_GRAVE
    [43] +                      # KEY_BACKSLASH
    list(range(44, 54)) +       # KEY_Z..KEY_SLASH
    [86]                        # KEY_102ND (ISO < > key)
)


def _kernel_keycode(xkb_keycode):
    """Convert an XKB keycode to its kernel/evdev keycode (resolve +8 once).

    The XKB +8 offset is removed here, in exactly one place, so that nothing
    downstream offsets again — double-subtraction yields a valid-but-wrong code
    that slips past range checks, which is the single most damaging trap in this
    subsystem. Both the analyzer and the symbol-table builder route through this.
    """
    return xkb_keycode - XKB_KEYCODE_OFFSET


def variant_from_xkb(raw_variant):
    """Normalize a raw XKB variant (possibly '' or None) to the canonical token.

    The single entry point for variants arriving from the system (kxkbrc
    VariantList, GNOME source ids, _XKB_RULES_NAMES). Idempotent: a value that is
    already DEFAULT_VARIANT, or any real variant, passes through unchanged.
    """
    if raw_variant in (None, ''):
        return DEFAULT_VARIANT
    return raw_variant


def variant_to_xkb(variant):
    """Convert a canonical variant back to the XKB form (DEFAULT_VARIANT -> '').

    The single exit point, used right before handing a variant to xkbcommon
    (load_from_names) or to setxkbmap, where the blank variant must be empty.
    """
    if variant == DEFAULT_VARIANT:
        return ''
    return variant


def make_layout_spec(layout, raw_variant, description=None):
    """Build a LayoutSpec from a raw (possibly-blank) XKB variant.

    The normalizing constructor for specs sourced from the system, so call sites
    do not each have to remember to route the variant through variant_from_xkb.
    """
    return LayoutSpec(layout, variant_from_xkb(raw_variant), description)


def format_layout(spec):
    """Render a LayoutSpec as one consistent human-readable label.

    Prefers an explicit description when present (e.g. 'English (US)'), since
    that already names the variant; otherwise builds from the layout and
    variant, naming the blank variant explicitly as '(default)'.
    """
    if spec.description:
        return spec.description
    if spec.variant and spec.variant != DEFAULT_VARIANT:
        return f'{spec.layout} ({spec.variant})'
    return f'{spec.layout} (default)'


# End of file #
