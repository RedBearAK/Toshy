"""Regression checks for Toshy's general Cmd+Shift+bracket fallback.

Read the default config as an AST: loading it as Python would require a
running Toshy environment and active desktop services.
"""

import ast
from pathlib import Path
from types import SimpleNamespace

CONFIG_PATH = Path(__file__).resolve().parents[1] / "default-toshy-config" / "toshy_config.py"


def _general_gui_mappings():
    tree = ast.parse(CONFIG_PATH.read_text(encoding="utf-8"))
    calls = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name) and node.func.id == "keymap"
        and node.args and isinstance(node.args[0], ast.Constant)
        and node.args[0].value == "General GUI"
    ]
    assert len(calls) == 1
    mapping = calls[0].args[1]
    assert isinstance(mapping, ast.Dict)
    return {
        key.args[0].value: value
        for key, value in zip(mapping.keys, mapping.values)
        if isinstance(key, ast.Call) and isinstance(key.func, ast.Name)
        and key.func.id == "C"
    }


def _resolve_bracket_output(node, app_kind):
    assert isinstance(node, ast.Lambda)
    fake_env = {
        "C": lambda s: s,
        "hmp_is_browser": lambda ctx: ctx.kind == "browser",
        "hmp_is_terminal": lambda ctx: ctx.kind == "terminal",
    }
    mapper = eval(compile(ast.Expression(node), str(CONFIG_PATH), "eval"), fake_env)
    return mapper(SimpleNamespace(kind=app_kind))


def test_brackets_switch_tabs_in_browsers_and_terminals():
    mappings = _general_gui_mappings()
    for app in ("browser", "terminal"):
        assert _resolve_bracket_output(mappings["Shift-RC-Left_Brace"], app) == "C-Page_Up"
        assert _resolve_bracket_output(mappings["Shift-RC-Right_Brace"], app) == "C-Page_Down"


def test_brackets_preserve_native_shortcuts_in_other_gui_apps():
    mappings = _general_gui_mappings()
    for app in ("design-editor", "other-gui"):
        assert _resolve_bracket_output(mappings["Shift-RC-Left_Brace"], app) == "Shift-C-Left_Brace"
        assert _resolve_bracket_output(mappings["Shift-RC-Right_Brace"], app) == "Shift-C-Right_Brace"
    # App switching and within-app navigation remain global and unaffected.
    for shortcut in ("RC-Tab", "Shift-RC-Tab", "RC-Grave", "Shift-RC-Grave"):
        assert shortcut in mappings
