# src/xwaykeyz/lib/conditional_guard.py
#
# Guard for user-supplied `when` conditionals on keymaps, modmaps, multipurpose
# modmaps and timeout rules.
#
# A conditional is arbitrary config code and can raise at keystroke time (a
# NameError for a hoist that no longer exists, an AttributeError for a typo on
# the context object, a re.error from a bad pattern...). Without a guard the
# exception escapes the input callback: the key is never emitted, the rest of
# the event batch is dropped, and the device registry never sees the press, so
# the release that follows is mistaken for a key stuck from before the grab and
# the repair path ungrabs the device to inject it raw. That is the failure
# behind issue reports that look like "Shift stopped working after upgrade".
#
# call_conditional() turns that into: the broken conditional is treated as a
# non-match, the first failure is logged with a full traceback and the name of
# the keymap/modmap it belongs to, later failures are counted and summarized,
# and the failure is recorded where the config (or Toshy) can read it.
#
# check_conditional_names() is the complementary load-time check: it walks the
# bytecode of every registered conditional for global name loads and reports
# any name that does not exist in the config namespace, before any key is
# pressed. It only sees NameErrors, which is why both halves exist.

import dis
import types
import difflib
import builtins
import traceback

from .logger import error, warn


__version__ = '20261104'

LOG_PREFIX = 'CONDITIONAL ERROR'
REPEAT_SUMMARY_INTERVAL = 100

# {(kind, name): {'exc': str, 'count': int}}
_broken_dct: 'dict[tuple[str, str], dict]' = {}

# Optional callback registered by the config: fn(kind, name, exc). Called once
# per (kind, name), never required, never trusted to not raise.
_error_handler_fn = None


def set_error_handler(handler_fn):
    """Register (or clear with None) the optional one-shot error callback."""
    global _error_handler_fn
    if handler_fn is not None and not callable(handler_fn):
        raise TypeError(f'conditional error handler must be callable, got {type(handler_fn)}')
    _error_handler_fn = handler_fn


def get_broken_conditionals() -> 'dict[tuple[str, str], dict]':
    """Snapshot of every conditional that has failed since startup."""
    return {key: dict(val) for key, val in _broken_dct.items()}


def reset_broken_conditionals():
    """Forget all recorded failures (config reload, tests)."""
    _broken_dct.clear()


def _missing_name_from(exc: Exception) -> str:
    """The undefined identifier from a NameError, or '' if not determinable."""
    if not isinstance(exc, NameError):
        return ''
    # NameError.name exists from Python 3.10; parse the message before that.
    missing = getattr(exc, 'name', None)
    if missing:
        return missing
    msg = str(exc)
    if msg.startswith("name '") and msg.count("'") >= 2:
        return msg.split("'")[1]
    return ''


def _did_you_mean(exc: Exception, conditional) -> str:
    missing = _missing_name_from(exc)
    if not missing:
        return ''
    namespace = getattr(conditional, '__globals__', None)
    if not isinstance(namespace, dict):
        return ''
    candidates = [k for k in namespace if not k.startswith('__')]
    close_lst = difflib.get_close_matches(missing, candidates, n=3, cutoff=0.6)
    if not close_lst:
        return ''
    return f' Did you mean: {", ".join(repr(c) for c in close_lst)}?'


def _notify_handler(kind: str, name: str, exc: Exception):
    if _error_handler_fn is None:
        return
    try:
        _error_handler_fn(kind, name, exc)
    except Exception as handler_exc:
        error(f'{LOG_PREFIX}: error handler itself raised '
                f'{handler_exc.__class__.__name__}: {handler_exc}')


def report_failure(kind: str, name: str, exc: Exception, conditional=None, where: str = ''):
    """
    Record and log a conditional failure. First occurrence per (kind, name)
    gets the full traceback; later ones are counted, with a one-line summary
    every REPEAT_SUMMARY_INTERVAL occurrences.
    """
    key = (kind, name)
    entry = _broken_dct.get(key)
    if entry is None:
        _broken_dct[key] = {'exc': f'{exc.__class__.__name__}: {exc}', 'count': 1}
        hint = _did_you_mean(exc, conditional)
        where_str = f' ({where})' if where else ''
        error(f'{LOG_PREFIX}: {kind} {name!r}{where_str} raised '
                f'{exc.__class__.__name__}: {exc}.{hint}')
        error(f'{LOG_PREFIX}: this {kind} is disabled (treated as non-matching) '
                f'until the config is fixed and the keymapper restarted.')
        tb_str = ''.join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        for line in tb_str.rstrip().splitlines():
            error(f'    {line}')
        _notify_handler(kind, name, exc)
        return
    entry['count'] += 1
    if entry['count'] % REPEAT_SUMMARY_INTERVAL == 0:
        error(f'{LOG_PREFIX}: {kind} {name!r} still failing '
                f'({entry["count"]} times): {entry["exc"]}')


def call_conditional(kind: str, name: str, conditional, ctx) -> bool:
    """
    Evaluate a `when` conditional safely. None means unconditional (True).
    Any exception is reported and the conditional is treated as non-matching.
    """
    if conditional is None:
        return True
    try:
        return bool(conditional(ctx))
    except Exception as exc:
        report_failure(kind, name, exc, conditional=conditional, where='at keystroke')
        return False


# ---------------------------------------------------------------------------
# Load-time static check for missing global names
# ---------------------------------------------------------------------------

_GLOBAL_LOAD_OPS = frozenset(('LOAD_GLOBAL', 'LOAD_NAME'))


def _global_names_in_code(code: types.CodeType) -> 'set[str]':
    """All names loaded as globals by this code object and any nested ones."""
    names = set()
    for instr in dis.get_instructions(code):
        if instr.opname in _GLOBAL_LOAD_OPS:
            names.add(instr.argval)
    for const in code.co_consts:
        if isinstance(const, types.CodeType):
            names |= _global_names_in_code(const)
    return names


def find_missing_names(conditional) -> 'list[str]':
    """
    Names a Python-level conditional loads as globals that do not exist in
    its own globals or in builtins. Non-Python callables (C functions,
    objects with __call__) are skipped and yield an empty list.
    """
    code = getattr(conditional, '__code__', None)
    namespace = getattr(conditional, '__globals__', None)
    if not isinstance(code, types.CodeType) or not isinstance(namespace, dict):
        return []
    builtin_names = set(dir(builtins))
    missing_lst = []
    for name in sorted(_global_names_in_code(code)):
        if name in namespace or name in builtin_names:
            continue
        missing_lst.append(name)
    return missing_lst


def check_conditional_names(items: 'list[tuple[str, str, object]]') -> int:
    """
    Static check across (kind, name, conditional) triples. Reports each
    conditional that references a missing global, through the same path as
    a runtime failure, and returns how many conditionals were flagged.
    Must run after the config has finished executing, since hoists may be
    defined after the keymaps that use them.
    """
    flagged_cnt = 0
    for kind, name, conditional in items:
        if conditional is None:
            continue
        missing_lst = find_missing_names(conditional)
        if not missing_lst:
            continue
        flagged_cnt += 1
        exc = NameError(f"name {missing_lst[0]!r} is not defined")
        exc.name = missing_lst[0]
        extra = ''
        if len(missing_lst) > 1:
            extra = f' (also missing: {", ".join(repr(n) for n in missing_lst[1:])})'
        report_failure(kind, name, exc, conditional=conditional,
                        where=f'found at config load{extra}')
    if flagged_cnt:
        warn(f'{LOG_PREFIX}: {flagged_cnt} conditional(s) reference undefined names '
                f'and will never match. Fix the config to restore them.')
    return flagged_cnt


# End of file #
