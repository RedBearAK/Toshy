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
"""

__version__ = '20260603'

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
