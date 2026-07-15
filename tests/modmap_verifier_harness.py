"""
Harness for the modmap region verifier. No tests live here.

Toshy/tests/modmap_verifier_harness.py

Extracts the SCAN_MARK region from the default Toshy config, exec()s it so
the registrations land in the REAL xwaykeyz registries, then resolves key
events by driving the REAL transform.apply_modmap()/apply_multi_modmap().
Nothing about keymapper semantics is reimplemented here; the harness only
supplies the namespace and mutates scenario globals between resolutions.

Scenario axes:
    capslock_mode   x   keyboard type   x   app context (GUI/Terminal/Remote)

Any name the region references that the harness has not stubbed raises
NameError at exec time and is reported loudly. That is deliberate: a new
helper or setting in the region must force a decision here.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from xwaykeyz import transform
from xwaykeyz import config_api
from xwaykeyz.models.key import Key
from xwaykeyz.models.action import Action
from xwaykeyz.models.keystate import Keystate

from toshy_common.modifier_modes import CAPSLOCK_MODES, CAPSLOCK_MODE_DEFAULT

from tests.modmap_verifier_rgx import scan_mark_start_rgx, scan_mark_end_rgx


__version__ = '20260714'

def _find_config_path() -> str:
    """Locate the config file to verify. Repo layout first
    (default-toshy-config/toshy_config.py), then installed layout
    (~/.config/toshy/toshy_config.py, i.e. toshy_config.py next to the
    tests folder). In the installed layout the LIVE config is scanned,
    user slice content included."""
    base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
    candidates = [
        os.path.join(base_dir, 'default-toshy-config', 'toshy_config.py'),
        os.path.join(base_dir, 'toshy_config.py'),
    ]
    for candidate in candidates:
        if os.path.isfile(candidate):
            return candidate
    raise RuntimeError(f'No toshy_config.py found. Tried: {candidates}')


CONFIG_PATH = _find_config_path()

KBD_TYPES       = ('Apple', 'Windows', 'IBM', 'Chromebook')
APP_CONTEXTS    = ('GUI', 'Terminal', 'Remote')

# The keys whose identities this whole system revolves around. The physical
# Caps position reports LEFT_META on Chromebook keyboards (they have no
# CapsLock key), CAPSLOCK everywhere else.
KEYS_OF_INTEREST = (Key.CAPSLOCK, Key.LEFT_CTRL, Key.LEFT_META)


def caps_position_inkey(kbd_type: str) -> Key:
    """The keycode the physical Caps-position key reports for this kbd type."""
    if kbd_type == 'Chromebook':
        return Key.LEFT_META
    return Key.CAPSLOCK


class FakeSettings:
    """Stand-in for the Settings object. Every attribute the scan region
    reads must be declared here explicitly; an unknown attribute fails
    loudly instead of returning a default, so a renamed setting cannot
    silently disable a `when` clause."""

    def __init__(self):
        self.screen_has_focus       = True
        self.capslock_mode          = CAPSLOCK_MODE_DEFAULT
        self.forced_numpad          = True
        self.media_arrows_fix       = False
        self.multi_lang             = False
        self.altgr_on_menu_key      = True
        self.Enter2Ent_Cmd          = False
        self.l_cmd_is_sup_and_cmd   = False
        self.l_opt_is_sup_and_opt   = False

    def __getattr__(self, name):
        # Only called for attributes NOT found normally.
        raise AttributeError(
            f"FakeSettings has no attribute '{name}'. The scan region reads a "
            f"setting the verifier does not model - add it to FakeSettings.")


def extract_region(config_source: str) -> str:
    """Return the source text between the SCAN_MARK lines, or raise."""
    start_match = scan_mark_start_rgx.search(config_source)
    end_match = scan_mark_end_rgx.search(config_source)
    if not start_match:
        raise RuntimeError('SCAN_MARK_START not found in config')
    if not end_match:
        raise RuntimeError('SCAN_MARK_END not found in config')
    if end_match.start() <= start_match.end():
        raise RuntimeError('SCAN_MARK_END precedes SCAN_MARK_START')
    # Slice at line boundaries: from the line after the start marker to the
    # start of the end-marker line.
    region_start = config_source.index('\n', start_match.end()) + 1
    region = config_source[region_start:end_match.start()]
    # Blank-pad the prefix so exec() tracebacks report true config line numbers.
    prefix_line_count = config_source[:region_start].count('\n')
    return ('\n' * prefix_line_count) + region


_cached_namespace = None
_cached_cnfg = None


def build_namespace():
    """exec() the scan region once per process into a namespace wired to the
    real xwaykeyz registration functions. Returns (namespace, fake_cnfg)."""
    global _cached_namespace, _cached_cnfg
    if _cached_namespace is not None:
        return _cached_namespace, _cached_cnfg

    with open(CONFIG_PATH, encoding='utf-8') as config_file:
        config_source = config_file.read()
    region_source = extract_region(config_source)

    fake_cnfg = FakeSettings()

    def _quiet(*args, **kwargs):
        pass

    ns = {
        # Real registration API - registrations land in the real registries
        'modmap':                   config_api.modmap,
        'multipurpose_modmap':      config_api.multipurpose_modmap,
        'keymap':                   config_api.keymap,
        'Key':                      Key,
        # Settings stand-in
        'cnfg':                     fake_cnfg,
        # Canonical mode constants (imported by the region's flag function)
        'CAPSLOCK_MODES':           CAPSLOCK_MODES,
        'CAPSLOCK_MODE_DEFAULT':    CAPSLOCK_MODE_DEFAULT,
        # Logger stand-ins (quiet)
        'debug':                    _quiet,
        'warn':                     _quiet,
        'error':                    _quiet,
        # Helpers defined outside the region, referenced by `when` clauses
        # inside it. All return inert values; none touch the keys of interest
        # (hygiene check C6 protects that assumption).
        '_context_pre_check':       lambda ctx: False,
        'hmp_numlk_off':            lambda ctx: False,
        'hmp_not_kpad_devs':        lambda ctx: False,
        # Device-exclusion plumbing for the numpad modmaps (inert stubs; the
        # matchProps hoist is immediately re-stubbed by the ctx lambdas above
        # after exec, via post_exec_overrides below).
        'toRgxStr':                 lambda lst: '',
        'matchProps':               lambda *args, **kwargs: (lambda ctx: False),
        'exclude_kpad_devs_UserCustom_lod': [],
        # Scenario globals - overwritten per scenario by set_scenario()
        'ctx_app_is_remote':        False,
        'ctx_app_is_terminal':      False,
        'ctx_kbd_is_apple':         False,
        'ctx_kbd_is_chromebook':    False,
        'ctx_kbd_is_ibm':           False,
        'ctx_kbd_is_windows':       False,
    }

    try:
        exec(compile(region_source, CONFIG_PATH, 'exec'), ns)
    except NameError as name_err:
        raise RuntimeError(
            f'Scan region references a name the harness has not stubbed: '
            f'{name_err}') from name_err

    # Load the registries into the transform module (real boot path)
    transform.boot_config()

    _cached_namespace, _cached_cnfg = ns, fake_cnfg
    return ns, fake_cnfg


def set_scenario(ns, fake_cnfg, mode: str, kbd_type: str, app_context: str):
    """Point the namespace globals and fake settings at one scenario cell,
    then run the region's real flag-derivation function."""
    fake_cnfg.capslock_mode         = mode
    ns['ctx_app_is_remote']         = (app_context == 'Remote')
    ns['ctx_app_is_terminal']       = (app_context == 'Terminal')
    ns['ctx_kbd_is_apple']          = (kbd_type == 'Apple')
    ns['ctx_kbd_is_windows']        = (kbd_type == 'Windows')
    ns['ctx_kbd_is_ibm']            = (kbd_type == 'IBM')
    ns['ctx_kbd_is_chromebook']     = (kbd_type == 'Chromebook')
    # Drive the REAL derivation defined inside the region, so a typo'd mode
    # string fails here exactly as it would in production.
    ns['_update_caps_mode_flags']()


def resolve_key(inkey: Key) -> Keystate:
    """Resolve one key press through the real modmap chain for whatever
    scenario is currently set. Returns the final Keystate."""
    keystate = Keystate(inkey=inkey, action=Action.PRESS)
    transform.apply_modmap(keystate, None)
    transform.apply_multi_modmap(keystate, None)
    return keystate


def describe_keystate(keystate: Keystate) -> str:
    """Human-readable identity summary: 'ESC/LEFT_CTRL' for multis,
    plain key name otherwise."""
    if keystate.is_multi:
        return f'{keystate.key.name}/{keystate.multikey.name}'
    return keystate.key.name


def resolve_cell(ns, fake_cnfg, mode: str, kbd_type: str, app_context: str) -> dict:
    """Resolve all keys of interest for one scenario cell.
    Returns {'caps': str, 'lctrl': str, 'caps_keystate': Keystate}."""
    set_scenario(ns, fake_cnfg, mode, kbd_type, app_context)
    caps_ks = resolve_key(caps_position_inkey(kbd_type))
    lctrl_ks = resolve_key(Key.LEFT_CTRL)
    return {
        'caps':             describe_keystate(caps_ks),
        'lctrl':            describe_keystate(lctrl_ks),
        'caps_keystate':    caps_ks,
        'lctrl_keystate':   lctrl_ks,
    }


def live_claimants(ns, inkey: Key) -> 'list[tuple[str, str]]':
    """For the currently set scenario, list (kind, name) of every conditional
    registration containing `inkey` whose `when` clause passes. Order matches
    registration order. Used by the exclusivity check."""
    claimants = []
    for mm in transform._MODMAPS[1:]:
        if inkey in mm and mm.conditional(None):
            claimants.append(('modmap', mm.name))
    for mmm in transform._MULTI_MODMAPS[1:]:
        if inkey in mmm and mmm.conditional(None):
            claimants.append(('multi', mmm.name))
    return claimants


def all_registrations() -> 'list[tuple[str, object]]':
    """All conditional registrations as (kind, obj), registration order."""
    regs = [('modmap', mm) for mm in transform._MODMAPS[1:]]
    regs += [('multi', mmm) for mmm in transform._MULTI_MODMAPS[1:]]
    return regs

# End of file #
