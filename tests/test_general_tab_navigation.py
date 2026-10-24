"""Regression checks for Toshy's shared literal-bracket exemption.

Read the config as an AST: importing it requires a running Toshy environment.
"""

import ast
from pathlib import Path
from types import SimpleNamespace

CONFIG_PATH = Path(__file__).resolve().parents[1] / "default-toshy-config" / "toshy_config.py"


def _tree():
    return ast.parse(CONFIG_PATH.read_text(encoding="utf-8"))


def _keymap(tree, name):
    matches = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name) and node.func.id == "keymap"
        and node.args and isinstance(node.args[0], ast.Constant)
        and node.args[0].value == name
    ]
    assert len(matches) == 1
    return matches[0]


def _bindings(call):
    mapping = call.args[1]
    assert isinstance(mapping, ast.Dict)
    return {
        key.args[0].value: value.args[0].value
        for key, value in zip(mapping.keys, mapping.values)
        if isinstance(key, ast.Call) and isinstance(key.func, ast.Name)
        and key.func.id == "C"
        and isinstance(value, ast.Call) and isinstance(value.func, ast.Name)
        and value.func.id == "C"
    }


def _exempt_app_ids(tree):
    assignments = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "tab_nav_braces_exempt_lst"
                for target in node.targets)
    ]
    assert len(assignments) == 1
    return ast.literal_eval(assignments[0].value)


def test_general_tab_navigation_and_app_switching_remain_unchanged():
    bindings = _bindings(_keymap(_tree(), "General GUI"))
    assert bindings["Shift-RC-Left_Brace"] == "C-Page_Up"
    assert bindings["Shift-RC-Right_Brace"] == "C-Page_Down"
    # App/window switching remains defined in the original general keymap.
    tree = _tree()
    general = _keymap(tree, "General GUI")
    keys = [key.args[0].value for key in general.args[1].keys
            if isinstance(key, ast.Call) and isinstance(key.func, ast.Name)
            and key.func.id == "C"]
    for shortcut in ("RC-Tab", "Shift-RC-Tab", "RC-Grave", "Shift-RC-Grave"):
        assert shortcut in keys


def test_shared_exemption_overrides_tab_navigation_before_other_tab_maps():
    tree = _tree()
    exemption = _keymap(tree, "Tab Nav exemption - literal Shift+Cmd+Braces")
    tab_fix = _keymap(tree, "Tab Nav fix for apps that use Ctrl+Shift+Tab/Ctrl+Tab")
    general = _keymap(tree, "General GUI")
    assert exemption.lineno < tab_fix.lineno < general.lineno
    assert _bindings(exemption) == {
        "Shift-RC-Left_Brace": "C-Shift-Left_Brace",
        "Shift-RC-Right_Brace": "C-Shift-Right_Brace",
    }


def test_exemption_is_selected_only_for_listed_focused_local_apps():
    tree = _tree()
    app_ids = _exempt_app_ids(tree)
    assert len(app_ids) == len(set(app_ids))
    assert {
        "ai.storyteller.deckcraft",
        "ai.storyteller.designcraft",
        "ai.storyteller.filmcraft",
        "ai.storyteller.gridcraft",
        "ai.storyteller.photocraft",
        "ai.storyteller.vectorcraft",
    }.issubset(app_ids)

    exemption = _keymap(tree, "Tab Nav exemption - literal Shift+Cmd+Braces")
    when = next(keyword.value for keyword in exemption.keywords if keyword.arg == "when")
    config = SimpleNamespace(screen_has_focus=True)
    env = {
        "cnfg": config,
        "ctx_app_is_remote": False,
        "hmp_is_tab_nav_braces_exempt": lambda ctx: ctx.wm_class in app_ids,
    }
    predicate = eval(compile(ast.Expression(when), str(CONFIG_PATH), "eval"), env)
    assert predicate(SimpleNamespace(wm_class="ai.storyteller.vectorcraft"))
    assert not predicate(SimpleNamespace(wm_class="unlisted.application"))
    env["ctx_app_is_remote"] = True
    assert not predicate(SimpleNamespace(wm_class="ai.storyteller.vectorcraft"))
    env["ctx_app_is_remote"] = False
    config.screen_has_focus = False
    assert not predicate(SimpleNamespace(wm_class="ai.storyteller.vectorcraft"))
