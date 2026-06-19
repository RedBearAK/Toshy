"""
Symbol-table builder tools for Toshy keyboard-layout correction (Phase 2).

toshy_common/kblayout_symtable.py

Phase 1 corrects shortcut *matching* with a flat keycode->keycode map: it knows
which physical key bears a given base character on the active layout. That is
enough for combos, but not for *typed string output* (`to_US_keystrokes`) or
Unicode output, which decompose a target character into keystrokes against an
assumed US layout and so emit garbage on any other layout. Phase 2 fixes that by
giving the keymapper, per active layout, the actual keystroke sequence that
produces each character on THAT layout.

This module is the stateless toolbox that builds that table. It is analysis-side
(it speaks xkbcommon, like kblayout_analyze) but emits only kernel/evdev integer
keycodes — never keymapper objects — so the package boundary holds: the table is
keymapper-agnostic data, converted to Key only on the keymapper side, in the
setter. It optionally reads two modifier keycode VALUES from the keymapper's Key
enum when that is importable (mirroring how kblayout_analyze borrows Key for
display), falling back to the kernel constants when it is not, so the builder
still runs standalone with no keymapper installed. Those values are Linux
input-event codes the Key enum merely mirrors; reading them from the enum just
keeps them from drifting from the enum the setter converts against.

The table it produces:

    dict[str, list[(base_keycode, list[modifier_keycode])]]

A target string maps to a keystroke SEQUENCE. Each keystroke is a base keycode
plus the modifier keycodes to hold while pressing it. The sequence is length 1
for a directly-typeable character (one keypress) and length 2 for a dead-key
character (press the dead key, then the base). All keycodes are evdev: XKB's +8
offset is resolved here, once, exactly as in kblayout_analyze — nothing
downstream offsets again (the single most important trap in this subsystem).

Two data sources, one output shape:
  - The active keymap's level data gives direct entries: every character a key
    produces at every shift level, with the modifier combination that reaches it.
  - The locale compose table, probed by feeding (dead, base) keysym pairs, gives
    dead-key entries: which dead key plus which base composes which character.
The compose table is locale-driven and passed in by the caller (the coordinator
owns its lifecycle); this module never constructs or caches it.

Path selection, when a character is reachable more than one way on the SAME
layout: a direct single keystroke always beats a two-keystroke dead-key sequence,
and among direct paths the fewest-modifier combination wins (base < Shift < AltGr
< Shift+AltGr). 'Left unless something must be right': Shift is emitted as
LEFT_SHIFT; AltGr is necessarily RIGHT_ALT (that IS the AltGr key).

A modifier combination this module cannot translate into a holdable modifier
(NumLock-as-layer on Neo, a stray CapsLock-only path) yields NO table entry for
that character: it routes to the caller's miss set rather than emitting a guessed
keystroke. Loud omission over silently-wrong output.
"""

__version__ = '20260616'

from xkbcommon import xkb

from toshy_common.kblayout_common import (
    TYPING_BLOCK_KEYCODES,
    _kernel_keycode,
)


# The symbol table enumerates the analyzer's typing block PLUS the space bar
# (KEY_SPACE, evdev 57). Phase 1 restricts correction to the alphanumeric typing
# block because its job is repositioning keys that MOVED between layouts, and it
# must avoid dragging in high keycodes that carry duplicate base characters.
# Phase 2's job is different: it enumerates every character the layout can TYPE,
# for string/Unicode output. Space never moves, so Phase 1 rightly omits it — but
# any literal-string macro obviously needs it. We extend the shared block by one
# key, so the divergence is intentional and visible. Cheapest-path selection
# downstream already neutralises the duplicate-base-character risk that motivated
# Phase 1's tighter block, since a character found on two keys keeps only its
# cheapest path.

_KC_SPACE = 57
SYMTABLE_KEYCODES = frozenset(TYPING_BLOCK_KEYCODES | {_KC_SPACE})


# ─── Modifier keycodes (kernel/evdev; Linux input-event-codes) ───────────────
# Only two modifiers ever select a printable character: Shift and AltGr. Every
# character-bearing level on a normal Latin layout is base / Shift / AltGr /
# Shift+AltGr, so these two keycodes (combined) span them all. Other modifiers
# (Ctrl, Meta, NumLock-as-layer) do not type characters and are out of scope.
#
# AltGr is always the RIGHT Alt; Shift is emitted as the LEFT Shift ('left
# unless something must be right'). The values are kernel input-event codes,
# which the keymapper's Key enum mirrors. We prefer to read them FROM that enum
# when the keymapper is importable, so a value can never drift from the enum the
# setter will convert against; we fall back to the kernel constants when it is
# not (e.g. building/testing the table standalone, with no keymapper installed).
# Either way the table still crosses the boundary as plain ints.

try:
    from xwaykeyz.models.key import Key as _Key
    _KC_LEFT_SHIFT  = int(_Key.LEFT_SHIFT)
    _KC_RIGHT_ALT   = int(_Key.RIGHT_ALT)
except ImportError:
    _KC_LEFT_SHIFT  = 42
    _KC_RIGHT_ALT   = 100


# ─── XKB modifier-name vocabulary ────────────────────────────────────────────
# key_get_mods_for_level reports masks over named modifier indices. We translate
# a canonical mask into the set of XKB modifier names it carries, then map those
# names to the evdev modifier keycodes the keymapper holds. AltGr surfaces under
# either the real 'Mod5' or the virtual 'LevelThree' depending on the keymap;
# both mean the same physical AltGr. 'Shift' is Shift. Anything else (Lock/Caps,
# Mod2/NumLock, and other Mod*) is NOT a holdable output modifier here.

_XKB_MOD_SHIFT      = 'Shift'
_XKB_MOD_ALTGR_SET  = frozenset(('Mod5', 'LevelThree'))

# Human-readable label per translated combination, DISPLAY/log use only (stays
# this side of the boundary; never crosses to the keymapper).
_COMBO_LABELS = {
    frozenset():                            'base',
    frozenset((_KC_LEFT_SHIFT,)):           'Shift',
    frozenset((_KC_RIGHT_ALT,)):            'AltGr',
    frozenset((_KC_LEFT_SHIFT, _KC_RIGHT_ALT)): 'Shift+AltGr',
}


def _is_dead_keysym(keysym):
    """True if a keysym is a dead key (its name begins 'dead_')."""
    name = xkb.keysym_get_name(keysym) or ''
    return name.startswith('dead_')


def _canonical_mask(masks):
    """The minimal modifier combination for a level: fewest bits set, then
    smallest value. Drops CapsLock-variant alternatives, giving one stable mask
    per level. Mirrors kblayout_analyze._canonical_mask so both sides agree.
    """
    mask_lst = list(masks)
    if not mask_lst:
        return None
    return min(mask_lst, key=lambda m: (bin(m).count('1'), m))


def _mask_to_modifier_keycodes(keymap, mask):
    """Translate one canonical XKB modifier mask to the evdev modifier keycodes
    the keymapper must hold, or None if the mask is not translatable.

    Returns:
        []                 for the base level (no modifiers),
        [_KC_LEFT_SHIFT]   for Shift,
        [_KC_RIGHT_ALT]    for AltGr (Mod5 / LevelThree),
        both               for Shift+AltGr,
        None               if the mask carries any modifier we do not emit
                           (Lock/Caps, Mod2/NumLock-as-layer, etc.) — the caller
                           treats None as 'unreachable', a miss, not an entry.

    The translation is deliberately strict: an untranslatable bit makes the whole
    mask untranslatable, so we never emit a partial/guessed modifier set that
    would press the wrong keys. 'base' is mask == 0, an empty (truthy) list.
    """
    if mask == 0:
        return []

    names = set()
    for idx in range(keymap.num_mods()):
        if mask & (1 << idx):
            names.add(keymap.mod_get_name(idx))

    keycodes = []
    remaining = set(names)

    if _XKB_MOD_SHIFT in remaining:
        keycodes.append(_KC_LEFT_SHIFT)
        remaining.discard(_XKB_MOD_SHIFT)

    if remaining & _XKB_MOD_ALTGR_SET:
        keycodes.append(_KC_RIGHT_ALT)
        remaining -= _XKB_MOD_ALTGR_SET

    if remaining:
        # Anything left is a modifier we do not turn into a held output key.
        return None
    return keycodes


def _combo_label(modifier_keycodes):
    """Readable label for a translated modifier-keycode list (log use only)."""
    return _COMBO_LABELS.get(frozenset(modifier_keycodes), '+'.join(
        str(kc) for kc in modifier_keycodes) or 'base')


# ─── Direct-keystroke entries (from the active keymap's levels) ──────────────

def _direct_paths(keymap):
    """Build char -> list of candidate direct paths from the active keymap.

    Walks every typing-block key at every shift level. For each character a level
    produces, records a candidate path [(base_keycode, [modifier_keycodes])] — a
    one-keystroke sequence. A character can appear on more than one key/level, so
    the value is a list of candidates; selection happens later.

    Untranslatable modifier combinations are skipped here (not recorded), so a
    character only reachable via, say, a NumLock layer simply has no direct path.
    """
    direct = {}
    for xkb_keycode in keymap:
        kernel = _kernel_keycode(xkb_keycode)
        if kernel not in SYMTABLE_KEYCODES:
            continue
        layout_idx = 0
        for level in range(keymap.num_levels_for_key(xkb_keycode, layout_idx)):
            canon = _canonical_mask(
                keymap.key_get_mods_for_level(xkb_keycode, layout_idx, level))
            if canon is None:
                continue
            mod_keycodes = _mask_to_modifier_keycodes(keymap, canon)
            if mod_keycodes is None:
                continue                                # unreachable modifier combo
            for keysym in keymap.key_get_syms_by_level(xkb_keycode, layout_idx, level):
                char = xkb.keysym_to_string(keysym)
                if char in (None, ''):
                    continue                            # dead keys, controls, etc.
                path = [(kernel, mod_keycodes)]
                direct.setdefault(char, []).append(path)
    return direct


def _dead_key_presses(keymap):
    """Build dead_keysym -> press (base_keycode, [modifier_keycodes]) for every
    dead key the active layout exposes, choosing the cheapest press if a dead key
    sits on more than one key/level. Dead keys whose press needs an untranslatable
    modifier are skipped (cannot be produced, so cannot start a sequence).
    """
    dead = {}
    for xkb_keycode in keymap:
        kernel = _kernel_keycode(xkb_keycode)
        if kernel not in SYMTABLE_KEYCODES:
            continue
        layout_idx = 0
        for level in range(keymap.num_levels_for_key(xkb_keycode, layout_idx)):
            canon = _canonical_mask(
                keymap.key_get_mods_for_level(xkb_keycode, layout_idx, level))
            if canon is None:
                continue
            mod_keycodes = _mask_to_modifier_keycodes(keymap, canon)
            if mod_keycodes is None:
                continue
            for keysym in keymap.key_get_syms_by_level(xkb_keycode, layout_idx, level):
                if not _is_dead_keysym(keysym):
                    continue
                press = (kernel, mod_keycodes)
                prev = dead.get(keysym)
                if prev is None or len(mod_keycodes) < len(prev[1]):
                    dead[keysym] = press
    return dead


# ─── Dead-key (composed) entries (from the locale compose table) ─────────────

def _keysym_for_char(char):
    """Resolve a single character to a feedable keysym.

    keysym_from_name() encodes ASCII and raises on anything else, so it is only
    used for ASCII; non-ASCII characters use the Unicode keysym form
    (0x01000000 + codepoint), which compose matching accepts for those bases.
    """
    codepoint = ord(char)
    if codepoint < 128:
        keysym = xkb.keysym_from_name(char)
        if keysym:
            return keysym
    return 0x01000000 + codepoint


def _composed_paths(compose_table, dead_presses, direct):
    """Build composed-target -> list of candidate dead-key paths.

    For each dead key (with its known press), feed (dead, base) through the
    compose state machine for every character the active layout can directly
    type, recording each COMPOSED result. The base's own press comes from the
    direct table, so the recorded path is the real two-keystroke sequence a user
    would perform: press the dead key, then press the base.

    Returns (composed, dead_miss):
        composed   target_string -> list of
                   [(dead_kc, [dead_mods]), (base_kc, [base_mods])]
        dead_miss  list of dead-keysym NAMES that composed nothing under this
                   compose table (present on the layout, unknown to the locale) —
                   the caller's loud miss domain.
    """
    cstate = compose_table.compose_state_new()

    candidates = []
    for char in direct:
        if len(char) != 1:
            continue                                    # multi-cp targets are outputs, not bases
        candidates.append((char, _keysym_for_char(char)))

    composed = {}
    dead_miss = []

    for dead_ks, dead_press in dead_presses.items():
        composed_any = False
        for char, base_ks in candidates:
            cstate.reset()
            cstate.feed(dead_ks)
            if cstate.get_status() == xkb.ComposeStatus.XKB_COMPOSE_NOTHING:
                # This compose table does not know this dead key at all.
                break
            cstate.feed(base_ks)
            if cstate.get_status() != xkb.ComposeStatus.XKB_COMPOSE_COMPOSED:
                continue
            target = cstate.get_utf8()
            if not target:
                continue
            base_paths = direct.get(char)
            if not base_paths:
                continue                                # base not directly typeable; skip
            base_press = _cheapest_path(base_paths)[0]
            composed_any = True
            path = [dead_press, base_press]
            composed.setdefault(target, []).append(path)
        if not composed_any:
            dead_miss.append(xkb.keysym_get_name(dead_ks))

    return composed, dead_miss


# ─── Path selection ──────────────────────────────────────────────────────────

def _path_cost(path):
    """Cost of a keystroke sequence: longer sequences cost more, then more total
    held modifiers cost more. Lower is better. This encodes 'direct (length 1)
    beats dead-key (length 2)' and 'fewer modifiers wins' in one comparable key.
    """
    length = len(path)
    mod_total = sum(len(mods) for _kc, mods in path)
    return (length, mod_total)


def _cheapest_path(paths):
    """The lowest-cost path among candidates for one target."""
    return min(paths, key=_path_cost)


# ─── Public entry point ──────────────────────────────────────────────────────

def build_symbol_table(keymap, compose_table):
    """Build the per-layout symbol table for the keymapper's string/Unicode output.

    keymap          a compiled xkbcommon Keymap for the ACTIVE layout (the same
                    object the analyzer holds; do not recompile from names).
    compose_table   a compiled xkbcommon ComposeTable for the active LOCALE,
                    constructed and owned by the caller (the coordinator).

    Returns (table, miss_info):

        table       dict[str, list[(base_keycode, list[modifier_keycode])]]
                    target string -> cheapest keystroke sequence to produce it on
                    this layout. Empty-ish for US-like layouts (ASCII present via
                    base/Shift directly), which is the common, zero-surprise case.

        miss_info   dict with diagnostic detail the caller may log:
                      'dead_miss'  : dead keys present on the layout that the
                                     locale compose table does not know (composed
                                     nothing) — characters behind them are
                                     unreachable here, a loud gap, not an error.
                      'collisions' : count of characters reachable both directly
                                     and via a dead key; resolved to the direct
                                     path. Informational.

    All keycodes are evdev. The +8 XKB offset is already resolved (via
    _kernel_keycode); the keymapper must NOT offset again.
    """
    if keymap is None:
        return {}, {'dead_miss': [], 'collisions': 0}

    direct = _direct_paths(keymap)

    if compose_table is None:
        composed, dead_miss = {}, []
    else:
        dead_presses = _dead_key_presses(keymap)
        composed, dead_miss = _composed_paths(compose_table, dead_presses, direct)

    table = {}
    collisions = 0

    # Direct first: every directly-typeable character gets its cheapest direct
    # (length-1) path.
    for char, paths in direct.items():
        table[char] = _cheapest_path(paths)

    # Composed next: fill gaps; a target already present directly is a collision,
    # resolved by keeping the (shorter) direct path.
    for target, paths in composed.items():
        if target in table:
            collisions += 1
            continue
        table[target] = _cheapest_path(paths)

    miss_info = {
        'dead_miss':    dead_miss,
        'collisions':   collisions,
    }
    return table, miss_info


# End of file #
