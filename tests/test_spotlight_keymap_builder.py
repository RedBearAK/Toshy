#!/usr/bin/env python3
"""
tests/test_spotlight_keymap_builder.py

Focused tests for the Spotlight/input-switching dual-arrangement keymap
builder: arrangement contents, cohabiting GUI/terminal spellings,
blockers, decorator wrapping, and swap-flag condition gating.
"""
__version__ = '20260804'

import os
import sys
import types

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

# Stub sibling deps BEFORE package imports (proc_launcher pulls the
# xwaykeyz logger; logger not needed in isolated tests).
_fake_proc_launcher = types.ModuleType('toshy_common.proc_launcher')
_fake_proc_launcher.launch_detached = lambda args, **kwargs: False
sys.modules['toshy_common.proc_launcher'] = _fake_proc_launcher
_fake_logger = types.ModuleType('toshy_common.logger')
_fake_logger.debug = lambda *args, **kwargs: None
_fake_logger.error = lambda *args, **kwargs: None
_fake_logger.VERBOSE = False
sys.modules['toshy_common.logger'] = _fake_logger

from toshy_common.spotlight_input.spli_keymaps import setup_spotlight_input_keymaps


def _check(label_str: str, ok: bool) -> bool:
    print(f'  [{"PASS" if ok else "FAIL"}] {label_str}')
    return ok


class _FakeCnfg:
    def __init__(self):
        self.swap_spotlight_and_input = False


class _FakeAPI:

    def __init__(self):
        self.registered_lst = []
        self.cnfg = _FakeCnfg()

    def C(self, combo_str):
        return ('COMBO', combo_str)

    def namespace(self, **extra_dct) -> dict:
        ns_dct = {
            'keymap':       self._keymap,
            'C':            self.C,
            'iEF2NT':       lambda: ('IEF2NT',),
            'bind':         ('BIND',),
            'cnfg':         self.cnfg,
            'DESKTOP_ENV':  'kde',
            'DE_MAJ_VER':   '6',
        }
        ns_dct.update(extra_dct)
        return ns_dct

    def _keymap(self, name_str, mappings_dct, when=None):
        record_dct = {'name': name_str, 'mappings': mappings_dct, 'when': when}
        self.registered_lst.append(record_dct)
        return record_dct


def test_kde_arrangements() -> bool:
    api = _FakeAPI()
    setup_spotlight_input_keymaps(api.namespace())

    default_rec = next(r for r in api.registered_lst if 'default' in r['name'])
    swapped_rec = next(r for r in api.registered_lst if 'swapped' in r['name'])
    dm, sm = default_rec['mappings'], swapped_rec['mappings']

    all_ok = True
    all_ok &= _check('default: RC-Space is launcher with iEF2NT decorator',
        dm.get(('COMBO', 'RC-Space')) == [('IEF2NT',), ('COMBO', 'Alt-Space')])
    all_ok &= _check('default: cohabiting GUI+terms primary input (KDE last-used)',
        dm.get(('COMBO', 'Super-Space')) == [('BIND',), ('COMBO', 'Alt-Super-L')]
        and dm.get(('COMBO', 'LC-Space')) == [('BIND',), ('COMBO', 'Alt-Super-L')])
    all_ok &= _check('default: secondary input is Next on KDE (Shift variants)',
        dm.get(('COMBO', 'Shift-Super-Space')) == [('BIND',), ('COMBO', 'Alt-Super-K')]
        and dm.get(('COMBO', 'Shift-LC-Space')) == [('BIND',), ('COMBO', 'Alt-Super-K')])

    all_ok &= _check('swapped: launcher moves to Super-Space and LC-Space',
        sm.get(('COMBO', 'Super-Space')) == [('IEF2NT',), ('COMBO', 'Alt-Space')]
        and sm.get(('COMBO', 'LC-Space')) == [('IEF2NT',), ('COMBO', 'Alt-Space')])
    all_ok &= _check('swapped: RC-Space becomes input primary with bind',
        sm.get(('COMBO', 'RC-Space')) == [('BIND',), ('COMBO', 'Alt-Super-L')])
    all_ok &= _check('swapped: displaced defaults blocked with None',
        sm.get(('COMBO', 'Shift-Super-Space'), 'missing') is None
        and sm.get(('COMBO', 'Shift-LC-Space'), 'missing') is None)

    class _Ctx: pass
    ctx = _Ctx()
    api.cnfg.swap_spotlight_and_input = False
    all_ok &= _check('flag False: default active, swapped inactive',
        default_rec['when'](ctx) is True and swapped_rec['when'](ctx) is False)
    api.cnfg.swap_spotlight_and_input = True
    all_ok &= _check('flag True: swapped active, default inactive',
        default_rec['when'](ctx) is False and swapped_rec['when'](ctx) is True)

    base_calls_lst = []
    api2 = _FakeAPI()
    def base_when(ctx):
        base_calls_lst.append(True)
        return False
    setup_spotlight_input_keymaps(api2.namespace(), when=base_when)
    rec = api2.registered_lst[0]
    all_ok &= _check('base when= composed (False base vetoes arrangement)',
        rec['when'](ctx) is False and len(base_calls_lst) == 1)

    print('\n--- KDE dual arrangements ---')
    return all_ok


def main():
    results_lst = [
        test_kde_arrangements(),
    ]
    passed_cnt = sum(1 for result in results_lst if result)
    print(f'\nScore: {passed_cnt}/{len(results_lst)} test groups passed')
    return 0 if passed_cnt == len(results_lst) else 1


if __name__ == '__main__':
    sys.exit(main())

# End of file #
