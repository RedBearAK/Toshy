#!/usr/bin/env python3
"""
Keyboard layout analyzer (XKB) for Toshy.

File: toshy_common/kblayout_analyze.py

Ingests an XKB keymap — either from explicit RMLVO names (for testing a
specific layout) or from a raw keymap string (as a Wayland compositor hands
it over through the wl_keyboard keymap fd) — and reports, per key, which
symbols sit at each shift level and which modifier combinations actually
reach those levels. It can additionally diff the active layout against a
reference (normally plain US) and mark how each key diverges, and derive the
sparse keycode->keycode correction map the keymapper consumes.

This module is a pure analysis building block. It has no hooks into the
keymapper's event pipeline and does no live detection: importing it pulls in
the xkbcommon package but otherwise does nothing until its methods are called
explicitly. Acquisition lives in kblayout_detect; orchestration (re-analyze on
layout change and hand the result to the keymapper) lives in kblayout_context.

The central correctness point, learned the hard way: an XKB "level" index
does NOT have a fixed, layout-wide meaning. The mapping from "modifiers held"
to "level reached" is defined per key by that key's *key type*. So level 2 is
the AltGr level on a four-level alphabetic key, does not exist on a two-level
key, and means something tied to NumLock on a keypad key. The authoritative
source for "what produces this level" is key_get_mods_for_level(), which is
already key-type aware. This module trusts that function and keeps NO global
level-to-modifier table.

Two further subtleties this module bakes in:
  - key_get_mods_for_level() returns a LIST of alternative masks. Each entry
    is a separate, individually-sufficient way to reach the level (e.g. an
    alphabetic key reaches its capital via Shift alone OR Lock/Caps alone).
    They are OR-alternatives, never an AND set, so they are reported that way.
  - Masks are bitfields over real + virtual modifier indices, as named by
    mod_get_name(). AltGr may appear as the real "Mod5" on one keymap and as
    the virtual "LevelThree" on another; NumLock appears as "Mod2". The display
    annotates the common ones without altering the raw data.

Comparison model: the diff is keyed by modifier COMBINATION, not by level
index, because two layouts can give the same key different key types, so
"level 2 here" and "level 2 there" need not be reached by the same modifiers.
For each key, the union of every modifier combination either side defines is
walked, and each combination is judged:
  - changed  (both define it, symbols differ)            -> mark '!!!'
  - added    (active defines it, reference does not)     -> mark '+++'
  - dropped  (reference defines it, active does not)     -> mark '---'
A combination that exists on only one side is exactly how a level-count
mismatch surfaces, so that case needs no special handling.
"""

__version__ = '20260604'

import os
import sys

from xkbcommon import xkb

# The keymapper's Key enum is an optional cross-reference: it lets the debug
# view show what symbol the keymapper *thinks* a kernel keycode is (inherited
# from the Linux input header, i.e. a standard US layout) right next to what
# the active layout actually produces. The XKB analysis is fully useful without
# it, so a missing keymapper package degrades gracefully rather than crashing.
try:
    from xwaykeyz.models.key import Key
    _HAVE_KEYMAPPER_KEYS = True
except ImportError:
    Key = None
    _HAVE_KEYMAPPER_KEYS = False


# Path bootstrap so 'toshy_common' resolves when this module is run standalone
# from inside the package folder (mirrors kblayout_detect). Idempotent and
# harmless when the package is already importable.
_toshy_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _toshy_root not in sys.path:
    sys.path.insert(0, _toshy_root)

from toshy_common.kblayout_common import (
    LayoutSpec,
    make_layout_spec,
    variant_to_xkb,
)


# XKB keycodes are offset from kernel (evdev) keycodes by +8.
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
# keysym; those are never sensible correction sources or targets.
TYPING_BLOCK_KEYCODES = frozenset(
    list(range(2, 14)) +        # KEY_1..KEY_0, KEY_MINUS, KEY_EQUAL
    list(range(16, 28)) +       # KEY_Q..KEY_RIGHTBRACE
    list(range(30, 42)) +       # KEY_A..KEY_GRAVE
    [43] +                      # KEY_BACKSLASH
    list(range(44, 54)) +       # KEY_Z..KEY_SLASH
    [86]                        # KEY_102ND (ISO < > key)
)

# Friendly annotations for the most commonly seen modifier names, used for
# DISPLAY only. The structured data always carries the raw mod_get_name() names.
MOD_DISPLAY_NAMES = {
    'Lock':         'Lock/Caps',
    'Mod2':         'Mod2/NumLock',
    'Mod5':         'Mod5/AltGr',
    'LevelThree':   'LevelThree/AltGr',
}

# Comparison marks. MARK_SAME is whitespace of equal width so marked and
# unmarked rows stay column-aligned.
MARK_CHANGED = '!!!'
MARK_ADDED   = '+++'
MARK_DROPPED = '---'
MARK_SAME    = '   '

# Shown in the 'keymapper' field when the keymapper's Key enum has no name for
# a kernel keycode — either the whole enum is unavailable, or that specific
# keycode is not a member of it.
KEYMAPPER_NAME_NONE = '(not defined in Key enum)'

# Shown once when the analysis is asked for on a libxkbcommon too old to have
# key_get_mods_for_level (i.e. older than 1.0).
UNSUPPORTED_NOTICE = (
    "(EE) key_get_mods_for_level is unavailable — needs libxkbcommon >= 1.0. "
    "Layout analysis is disabled on this system."
)

# Tri-state cache for the capability probe: None = not yet probed.
_MODS_FOR_LEVEL_OK = None


def _kernel_keycode(xkb_keycode: int) -> int:
    """Convert an XKB keycode to its kernel/evdev keycode."""
    return xkb_keycode - XKB_KEYCODE_OFFSET


def _produces_character(keysym: int) -> bool:
    """True if a keysym yields a typed character (letter/digit/punctuation).

    keysym_to_string returns None for modifiers, function keys, and dead keys,
    so this keeps correction to character keys only — a Mac layout's
    RALT->ISO_Level3_Shift change, for instance, is never a keycode correction.
    """
    return xkb.keysym_to_string(keysym) is not None


def _base_char_keysyms(keymap) -> dict:
    """Map xkb_keycode -> base-level keysym, for character-producing keys only.

    Base level (level 0, primary group) is the key's identity: which letter or
    symbol it bears without modifiers. That is what determines whether a key has
    moved relative to US.
    """
    out_dct = {}
    for xkb_keycode in keymap:
        keysyms = keymap.key_get_syms_by_level(xkb_keycode, 0, 0)
        if keysyms and _produces_character(keysyms[0]):
            out_dct[xkb_keycode] = keysyms[0]
    return out_dct


def _keymapper_key_name(kernel_keycode: int) -> 'str | None':
    """
    Return the keymapper's symbol name for a kernel keycode, or None.

    The keymapper inherits a standard US layout from the kernel input header,
    so this is the keymapper's *assumption* about the key, independent of the
    user's active layout.
    """
    if not _HAVE_KEYMAPPER_KEYS:
        return None
    try:
        return Key(kernel_keycode).name
    except ValueError:
        # Kernel keycode the keymapper has no symbol for (expected for some
        # keys); nothing to cross-reference.
        return None


def mods_for_level_supported() -> bool:
    """
    Whether the underlying libxkbcommon exposes a working
    key_get_mods_for_level() — new in libxkbcommon 1.0.0. The entire
    modifier/level analysis depends on it, so on an older C library this
    returns False and the analysis methods decline rather than throw. The
    runtime layout-awareness feature can gate on this too.

    Probed once (by an actual call, since on an old library the binding's
    wrapper may exist while the C symbol does not) and cached.
    """
    global _MODS_FOR_LEVEL_OK
    if _MODS_FOR_LEVEL_OK is not None:
        return _MODS_FOR_LEVEL_OK

    try:
        probe_keymap = xkb.Context().keymap_new_from_names(layout='us')
        # AD01 (keycode 24) exists in any us keymap. An out-of-range keycode
        # would merely return no masks, so this tests the call path itself.
        # The broad catch is deliberate: any failure here — missing wrapper,
        # missing C symbol, or otherwise — means the capability is absent.
        probe_keymap.key_get_mods_for_level(24, 0, 0)
        _MODS_FOR_LEVEL_OK = True
    except Exception:
        _MODS_FOR_LEVEL_OK = False
    return _MODS_FOR_LEVEL_OK


class KeyboardLayoutAnalyzer:
    """
    Loads an XKB keymap and answers per-key, per-level symbol/modifier queries,
    and optionally diffs the active layout against a reference layout.

    Typical use:
        klc = KeyboardLayoutAnalyzer()
        klc.load_from_names(layout='fr', variant='azerty')  # or load_from_string(...)
        klc.print_layout()                                   # raw per-key dump
        klc.set_reference_from_names(layout='us')            # diff against plain US
        klc.print_comparison()                               # marked divergences
        info = klc.compare_key(24)                            # structured diff, one key
    """

    def __init__(self):
        self.context = xkb.Context()
        self.keymap = None          # set by a load_* call; methods guard on it
        self.layout_name = None
        self.layout_spec = None     # source LayoutSpec on name/spec loads; None
                                    # when string-loaded (literal identity unknown)
        self._reference = None      # another KeyboardLayoutAnalyzer, set on demand

    # ── Loading ─────────────────────────────────────────────────────────

    def load_from_names(self, rules=None, model=None, layout=None,
                            variant=None, options=None) -> bool:
        """
        Compile a keymap from RMLVO names. Useful for inspecting a known
        layout by name without a live session.
        """
        try:
            keymap = self.context.keymap_new_from_names(
                rules=rules,
                model=model,
                layout=layout,
                variant=variant,
                options=options,
            )
        except xkb.XKBError as load_err:
            print(f"(EE) Failed to compile keymap from names: {load_err}")
            return False
        if not self._adopt_keymap(keymap):
            return False
        if layout:
            self.layout_spec = make_layout_spec(layout, variant, None)
        return True

    def load_from_spec(self, spec: 'LayoutSpec') -> bool:
        """
        Compile a keymap from a LayoutSpec, as produced by the detector.

        This is the canonical-vocabulary entry point. The spec's variant is the
        Toshy token (DEFAULT_VARIANT for the base layout), so it is converted
        back to XKB's empty-string form with variant_to_xkb on the way into
        xkbcommon — the single outbound boundary. Layout reasoning everywhere
        else stays in the shared vocabulary; only this hop speaks XKB-blank.
        """
        if not self.load_from_names(
            layout=spec.layout,
            variant=variant_to_xkb(spec.variant),
        ):
            return False
        # load_from_names rebuilt an equivalent spec from the names; replace it
        # with the original so any description (e.g. KDE's longName) is kept.
        self.layout_spec = spec
        return True

    def load_from_string(self, keymap_str: str) -> bool:
        """
        Compile a keymap from a full XKB keymap string. This is the path for
        ingesting what a Wayland compositor delivers through the wl_keyboard
        keymap fd: read the fd to a string and pass it here.
        """
        if not keymap_str:
            print("(EE) Empty keymap string; nothing to compile.")
            return False
        try:
            keymap = self.context.keymap_new_from_string(keymap_str)
        except xkb.XKBError as load_err:
            print(f"(EE) Failed to compile keymap from string: {load_err}")
            return False
        return self._adopt_keymap(keymap)

    def _adopt_keymap(self, keymap) -> bool:
        """Store a freshly compiled keymap and cache its primary layout name.

        Resets layout_spec to None — the 'literal identity unknown' default that
        the string path keeps and the name/spec paths overwrite after this call.
        """
        self.keymap = keymap
        self.layout_name = keymap.layout_get_name(0)
        self.layout_spec = None
        return True

    def set_reference_from_names(self, rules=None, model=None, layout='us',
                                    variant=None, options=None) -> bool:
        """
        Compile a reference layout (plain US by default) to diff against. This
        is what the keymapper inherited from the kernel header, and the basis
        the comparison marks are measured against.
        """
        reference = KeyboardLayoutAnalyzer()
        if not reference.load_from_names(rules=rules, model=model, layout=layout,
                                            variant=variant, options=options):
            print("(EE) Failed to compile reference keymap.")
            return False
        self._reference = reference
        return True

    # ── Analysis ────────────────────────────────────────────────────────

    def _decode_mask(self, mask: int) -> 'list[str]':
        """
        Decode one modifier-mask bitfield into a list of raw modifier names.

        An empty result (mask == 0) means "no modifiers" — the base level.
        """
        keymap = self.keymap
        if keymap is None:
            return []
        names_lst = []
        for idx in range(keymap.num_mods()):
            if mask & (1 << idx):
                names_lst.append(keymap.mod_get_name(idx))
        return names_lst

    def analyze_key(self, xkb_keycode: int) -> 'dict | None':
        """
        Return structured information about a single key, or None if the
        keycode is not present in the keymap.

        'alternatives' is a list of OR-alternatives; each inner list is the
        AND-set of modifiers for one sufficient way to reach the level. An
        inner list that is empty means "no modifiers needed" for that path.
        """
        keymap = self.keymap
        if keymap is None:
            print("(EE) No keymap loaded; call a load_* method first.")
            return None
        if not mods_for_level_supported():
            # Capability absent (old libxkbcommon). Return None silently so loop
            # callers don't spam; print_* methods emit the notice once.
            return None

        try:
            xkb_key_name = keymap.key_get_name(xkb_keycode)
        except xkb.XKBInvalidKeycode:
            # Not a real key position in this keymap (gaps are normal).
            return None

        kernel_keycode = _kernel_keycode(xkb_keycode)

        levels_lst = []
        layout_idx = 0      # primary layout/group; multi-group handled later
        for level in range(keymap.num_levels_for_key(xkb_keycode, layout_idx)):
            keysyms = keymap.key_get_syms_by_level(xkb_keycode, layout_idx, level)
            symbol_names_lst = [xkb.keysym_get_name(ks) for ks in keysyms]

            # List of alternative masks; decode EACH separately (they are not
            # to be merged — each is its own sufficient modifier combination).
            masks = keymap.key_get_mods_for_level(xkb_keycode, layout_idx, level)
            alternatives_lst = [self._decode_mask(mask) for mask in masks]

            levels_lst.append({
                'level':        level,
                'symbols':      symbol_names_lst,
                'alternatives': alternatives_lst,
            })

        return {
            'xkb_keycode':      xkb_keycode,
            'kernel_keycode':   kernel_keycode,
            'xkb_key_name':     xkb_key_name,
            'keymapper_name':   _keymapper_key_name(kernel_keycode),
            'levels':           levels_lst,
        }

    def iter_layout(self):
        """Yield analyze_key() results for every real key in the keymap, in order."""
        keymap = self.keymap
        if keymap is None:
            print("(EE) No keymap loaded; call a load_* method first.")
            return
        for xkb_keycode in keymap:
            info = self.analyze_key(xkb_keycode)
            if info is not None:
                yield info

    # ── Comparison ──────────────────────────────────────────────────────

    @staticmethod
    def _canonical_mask(masks) -> 'int | None':
        """
        The minimal modifier combination for a level: fewest bits set, then
        smallest value. This drops the CapsLock-variant alternatives and
        gives one stable key per level for cross-layout matching.
        """
        mask_lst = list(masks)
        if not mask_lst:
            return None
        return min(mask_lst, key=lambda m: (bin(m).count('1'), m))

    def _combo_symbol_dct(self, xkb_keycode: int) -> 'dict | None':
        """
        Map canonical-modifier-mask -> tuple of keysym names for one key,
        keyed by MODIFIERS rather than by level index. None if the keycode is
        not present in this keymap.
        """
        keymap = self.keymap
        if keymap is None:
            return None
        try:
            keymap.key_get_name(xkb_keycode)
        except xkb.XKBInvalidKeycode:
            return None

        out_dct = {}
        layout_idx = 0
        for level in range(keymap.num_levels_for_key(xkb_keycode, layout_idx)):
            masks = keymap.key_get_mods_for_level(xkb_keycode, layout_idx, level)
            canon = self._canonical_mask(masks)
            if canon is None:
                continue
            keysyms = keymap.key_get_syms_by_level(xkb_keycode, layout_idx, level)
            # Record the level even when it is NoSymbol (empty keysyms). A
            # present-but-empty level is meaningfully different from an absent
            # one (no level at that combo at all), and compare_key() relies on
            # that distinction to label '(NoSymbol)' vs '(none)'. Rows where
            # neither side yields a real symbol are filtered out there.
            out_dct[canon] = tuple(xkb.keysym_get_name(ks) for ks in keysyms)
        return out_dct

    def _format_combo(self, mask: int) -> str:
        """Render one canonical modifier mask as a readable label."""
        if mask == 0:
            return 'base'
        keymap = self.keymap
        parts_lst = []
        for idx in range(keymap.num_mods()):
            if mask & (1 << idx):
                raw = keymap.mod_get_name(idx)
                parts_lst.append(MOD_DISPLAY_NAMES.get(raw, raw))
        return '+'.join(parts_lst) if parts_lst else 'base'

    def compare_key(self, xkb_keycode: int) -> 'dict | None':
        """
        Diff one key against the reference layout, keyed by modifier combo.

        Returns None if no reference is set or the keycode is absent from the
        active layout. Otherwise returns a dict whose 'rows' list holds one
        entry per modifier combination (union of both layouts), each judged
        same / changed / added / dropped, plus a 'diverges' flag.
        """
        if self._reference is None:
            print("(EE) No reference layout set; call set_reference_from_names() first.")
            return None
        if not mods_for_level_supported():
            # Capability absent (old libxkbcommon); silent None, see analyze_key.
            return None

        act_dct = self._combo_symbol_dct(xkb_keycode)
        if act_dct is None:
            return None      # keycode not present on the active layout
        ref_dct = self._reference._combo_symbol_dct(xkb_keycode) or {}

        kernel_keycode = _kernel_keycode(xkb_keycode)
        rows_lst = []
        for mask in sorted(set(act_dct) | set(ref_dct),
                            key=lambda m: (bin(m).count('1'), m)):
            ref_syms = ref_dct.get(mask)        # tuple (maybe empty) if the
            act_syms = act_dct.get(mask)        # level exists, else None
            us_present = mask in ref_dct        # a level exists at this combo
            act_present = mask in act_dct       # (even if it is NoSymbol)
            us_has = bool(ref_syms)             # ... and yields a real symbol
            act_has = bool(act_syms)

            if not us_has and not act_has:
                # Neither side yields a glyph here (absent and/or NoSymbol on
                # both); nothing meaningful to compare.
                continue
            if act_has and not us_has:
                verdict, mark = 'added', MARK_ADDED
            elif us_has and not act_has:
                verdict, mark = 'dropped', MARK_DROPPED
            elif ref_syms != act_syms:
                verdict, mark = 'changed', MARK_CHANGED
            else:
                verdict, mark = 'same', MARK_SAME

            rows_lst.append({
                'mask':         mask,
                'combo':        self._format_combo(mask),
                'us_symbols':   list(ref_syms) if ref_syms is not None else [],
                'act_symbols':  list(act_syms) if act_syms is not None else [],
                'us_present':   us_present,
                'act_present':  act_present,
                'verdict':      verdict,
                'mark':         mark,
            })

        return {
            'xkb_keycode':      xkb_keycode,
            'kernel_keycode':   kernel_keycode,
            'xkb_key_name':     self.keymap.key_get_name(xkb_keycode),
            'keymapper_name':   _keymapper_key_name(kernel_keycode),
            'rows':             rows_lst,
            'diverges':         any(row['verdict'] != 'same' for row in rows_lst),
        }

    def iter_comparison(self, divergent_only: bool = True):
        """Yield compare_key() results for every active key, optionally only divergent ones."""
        keymap = self.keymap
        if keymap is None or self._reference is None:
            print("(EE) Need both a loaded keymap and a reference layout.")
            return
        for xkb_keycode in keymap:
            comparison_dct = self.compare_key(xkb_keycode)
            if comparison_dct is None:
                continue
            if divergent_only and not comparison_dct['diverges']:
                continue
            yield comparison_dct

    # ── Correction map (keymapper hand-off) ─────────────────────────────

    def build_correction_map(self, number_row='positional', latin_fallback=False) -> dict:
        """Return the sparse keycode->keycode correction map for the keymapper.

        Each active kernel keycode whose base-level character sits on a different
        physical key in US is mapped to the US kernel keycode that natively bears
        that character, so the keymapper can translate an incoming keycode to its
        US equivalent for matching and emit the original on no match. Only
        character-producing keys are considered (letters, digits, punctuation);
        modifier, function, and dead keys are never corrected. The map is empty
        for US-like layouts, where no correction is needed.

        number_row:
            'positional' (default) leaves the digit-row keys (KEY_1..KEY_0)
            uncorrected, matching macOS: Cmd/Ctrl + 1..9 keep firing from the
            physical number keys even on layouts that hide the digits behind
            Shift (AZERTY), and the Cmd+Shift+digit shortcuts stay reachable.
            'glyph' corrects the digit row like any other key, following the base
            character (so a relocated punctuation mark becomes reachable, at the
            cost of the positional digit shortcuts).
        latin_fallback:
            Reserved for non-Latin layouts whose base characters have no US home
            (e.g. Cyrillic), where correction should fall back to the layout's
            Latin level. Not yet implemented; accepted and ignored for now.
        """
        if number_row not in ('positional', 'glyph'):
            raise ValueError(
                f"number_row must be 'positional' or 'glyph', got {number_row!r}")
        if self.keymap is None or self._reference is None:
            print("(EE) build_correction_map needs both a loaded keymap and a reference.")
            return {}

        us_syms = _base_char_keysyms(self._reference.keymap)
        us_sym_to_kernel = {}
        for xkb_keycode, keysym in us_syms.items():
            kernel = _kernel_keycode(xkb_keycode)
            if kernel in TYPING_BLOCK_KEYCODES:
                us_sym_to_kernel.setdefault(keysym, kernel)   # first block key wins

        correction_dct = {}
        for xkb_keycode, active_sym in _base_char_keysyms(self.keymap).items():
            kernel = _kernel_keycode(xkb_keycode)
            if kernel not in TYPING_BLOCK_KEYCODES:
                continue                                # only the main typing block
            if number_row == 'positional' and kernel in NUMBER_ROW_KEYCODES:
                continue                                # keep the digit row positional
            if active_sym == us_syms.get(xkb_keycode):
                continue                                # unchanged from US
            target_kernel = us_sym_to_kernel.get(active_sym)
            if target_kernel is None:
                # Active base character has no US home in the typing block; a
                # non-Latin layout lands here, and latin_fallback (when built)
                # would resolve it.
                continue
            if target_kernel != kernel:
                correction_dct[kernel] = target_kernel

        return correction_dct

    # ── Display ─────────────────────────────────────────────────────────

    @staticmethod
    def _format_alternatives(alternatives: 'list[list[str]]') -> str:
        """
        Render OR-alternatives for one level as readable text, annotating the
        common modifier names. Example: 'Shift  or  Lock/Caps'.
        """
        rendered_lst = []
        for alt in alternatives:
            if not alt:
                rendered_lst.append('(base)')
                continue
            parts_lst = [MOD_DISPLAY_NAMES.get(name, name) for name in alt]
            rendered_lst.append('+'.join(parts_lst))
        return '  or  '.join(rendered_lst) if rendered_lst else '(none)'

    def format_key(self, info: dict) -> str:
        """Build a multi-line debug string for one analyze_key() result."""
        keymapper = info['keymapper_name'] or KEYMAPPER_NAME_NONE
        header = (
            f"xkb={info['xkb_keycode']:<3} "
            f"kernel={info['kernel_keycode']:<3} "
            f"name={info['xkb_key_name']:<5} "
            f"keymapper={keymapper}"
        )
        lines_lst = [header]
        for level_info in info['levels']:
            symbols = ' '.join(level_info['symbols']) or '(none)'
            mods = self._format_alternatives(level_info['alternatives'])
            lines_lst.append(f"    L{level_info['level']}  {symbols:<16}  ←  {mods}")
        return '\n'.join(lines_lst)

    def _layout_label(self) -> str:
        """Identity for a header, showing every name source this object holds so
        the less-informative xkbcommon name and a richer source/registry name
        (e.g. KDE's longName, carried on the spec) are both visible rather than
        mistaken for different layouts.

        The literal layout/variant tokens are appended when the keymap was loaded
        by name or spec; on the string path (compositor keymap fd) there are no
        RMLVO tokens, so only the compiled name shows.
        """
        spec = self.layout_spec
        names_lst = []
        if spec is not None and spec.description and spec.description != self.layout_name:
            names_lst.append(spec.description)      # richer source/registry name
        names_lst.append(self.layout_name)          # xkbcommon's compiled name
        label = '  /  '.join(names_lst)
        if spec is not None:
            label += f"  [layout={spec.layout} variant={spec.variant}]"
        return label

    def print_layout(self):
        """Print a human-readable dump of the whole loaded layout (no diff)."""
        if self.keymap is None:
            print("(EE) No keymap loaded; call a load_* method first.")
            return
        if not mods_for_level_supported():
            print(UNSUPPORTED_NOTICE)
            return
        print(f"Layout: {self._layout_label()}")
        if not _HAVE_KEYMAPPER_KEYS:
            print(f"(--) Keymapper Key enum unavailable; keymapper field shown as '{KEYMAPPER_NAME_NONE}'.")
        print()
        for info in self.iter_layout():
            print(self.format_key(info))

    @staticmethod
    def _render_symbols(symbols: 'list[str]', present: bool) -> str:
        """
        Render one side of a comparison row. A non-empty symbol list joins as
        usual; an empty list means no glyph, distinguished as '(NoSymbol)' when
        a level exists at that combo or '(none)' when no level does.
        """
        if symbols:
            return ' '.join(symbols)
        return '(NoSymbol)' if present else '(none)'

    def format_comparison(self, comparison_dct: dict) -> str:
        """Build a multi-line marked diff string for one compare_key() result."""
        keymapper = comparison_dct['keymapper_name'] or KEYMAPPER_NAME_NONE
        header = (
            f"xkb={comparison_dct['xkb_keycode']:<3} "
            f"kernel={comparison_dct['kernel_keycode']:<3} "
            f"name={comparison_dct['xkb_key_name']:<5} "
            f"keymapper={keymapper}"
        )
        lines_lst = [header]
        for row in comparison_dct['rows']:
            us_syms = self._render_symbols(row['us_symbols'], row['us_present'])
            act_syms = self._render_symbols(row['act_symbols'], row['act_present'])
            lines_lst.append(
                f"  {row['mark']} [{row['combo']:<18}] "
                f"us={us_syms:<14} act={act_syms}"
            )
        return '\n'.join(lines_lst)

    def print_comparison(self, divergent_only: bool = True):
        """Print the marked diff of the active layout against the reference."""
        if self.keymap is None:
            print("(EE) No keymap loaded; call a load_* method first.")
            return
        if self._reference is None:
            print("(EE) No reference layout set; call set_reference_from_names() first.")
            return
        if not mods_for_level_supported():
            print(UNSUPPORTED_NOTICE)
            return
        print(f"Layout:    {self._layout_label()}")
        print(f"Reference: {self._reference._layout_label()}")
        print(f"Marks: {MARK_CHANGED} changed   "
                f"{MARK_ADDED} added vs ref   "
                f"{MARK_DROPPED} missing vs ref")
        if not _HAVE_KEYMAPPER_KEYS:
            print(f"(--) Keymapper Key enum unavailable; keymapper field shown as '{KEYMAPPER_NAME_NONE}'.")
        print()
        shown = 0
        for comparison_dct in self.iter_comparison(divergent_only=divergent_only):
            print(self.format_comparison(comparison_dct))
            print()
            shown += 1
        if shown == 0:
            print("No divergences from the reference layout.")


def main():
    """Standalone debug entry point: diff a layout by RMLVO names against US."""
    # Args (all optional). With no args at all, default to AZERTY — the
    # canonical divergence case. With a layout given but no variant, use no
    # variant (rather than carrying the azerty default onto another layout).
    args_lst = sys.argv[1:]
    if not args_lst:
        layout, variant = 'fr', 'azerty'
    else:
        layout = args_lst[0]
        variant = args_lst[1] if len(args_lst) > 1 else None

    klc = KeyboardLayoutAnalyzer()
    if not klc.load_from_names(layout=layout, variant=variant):
        sys.exit(1)
    if not klc.set_reference_from_names(layout='us'):
        sys.exit(1)
    klc.print_comparison(divergent_only=True)


if __name__ == '__main__':
    main()


# End of file #
