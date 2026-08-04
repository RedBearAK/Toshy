#!/usr/bin/env python3
"""
toshy_common/shortcut_detect/sc_det_diag.py

Diagnostic apparatus for shortcut-detection CLI check commands: a
recording stand-in for the config-API namespace (so keymap builders can
run outside the keymapper) and a renderer that prints the captured
keymap structures as config-file-style literal syntax.
"""
__version__ = '20260803'


class ReprCombo:
    """Stands in for C(); repr renders as config-file syntax."""

    def __init__(self, combo_str):
        self.combo_str = combo_str

    def __hash__(self):
        return hash(self.combo_str)

    def __eq__(self, other):
        return isinstance(other, ReprCombo) and other.combo_str == self.combo_str

    def __repr__(self):
        return f'C("{self.combo_str}")'


class ReprSleep:
    """Stands in for sleep(); repr renders as config-file syntax."""

    def __init__(self, sec):
        self.sec = sec

    def __repr__(self):
        return f'sleep({self.sec})'


class ReprImmediately:

    def __repr__(self):
        return 'immediately'


class RecordingAPI:
    """Injected in place of the config globals() to capture the literal
    keymap structures a builder would register. Extra namespace entries
    (DESKTOP_ENV, DE_MAJ_VER, feature-specific names) are supplied by
    the caller via namespace(**extra)."""

    def __init__(self):
        self.registered_lst = []
        self.immediately = ReprImmediately()

    def namespace(self, **extra_dct) -> dict:
        ns_dct = {
            'keymap':       self._keymap,
            'C':            ReprCombo,
            'immediately':  self.immediately,
            'sleep':        ReprSleep,
        }
        ns_dct.update(extra_dct)
        return ns_dct

    def _keymap(self, name_str, mappings_dct, when=None):
        record_dct = {'name': name_str, 'mappings': mappings_dct}
        self.registered_lst.append(record_dct)
        return record_dct


def _render_mapping_value(value, indent_str) -> str:
    if isinstance(value, dict):
        inner_str = render_mappings(value, indent_str + '    ')
        return '{\n' + inner_str + indent_str + '}'
    if isinstance(value, list):
        return '[' + ', '.join(repr(item) for item in value) + ']'
    if callable(value) and hasattr(value, 'cmd_candidates_lst'):
        cmds_str = ' | '.join(' '.join(cmd) for cmd in value.cmd_candidates_lst)
        return f'<launch first found: {cmds_str}>'
    return repr(value)


def render_mappings(mappings_dct: dict, indent_str: str) -> str:
    key_reprs_lst = [repr(key) for key in mappings_dct]
    key_width = max((len(key_repr) for key_repr in key_reprs_lst), default=0) + 1
    lines_lst = []
    for key, value in mappings_dct.items():
        key_str = (repr(key) + ':').ljust(key_width + 1)
        lines_lst.append(f'{indent_str}{key_str} '
                            f'{_render_mapping_value(value, indent_str)},\n')
    return ''.join(lines_lst)


def print_keymap_records(registered_lst: 'list[dict]'):
    """Print captured keymap registrations as literal config syntax."""
    for record_dct in registered_lst:
        print()
        print(f'  keymap("{record_dct["name"]}", {{')
        print(render_mappings(record_dct['mappings'], '      '), end='')
        print('  })')

# End of file #
