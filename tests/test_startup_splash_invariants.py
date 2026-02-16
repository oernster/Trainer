from __future__ import annotations

import ast
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _parse_main_py() -> ast.Module:
    source = (_repo_root() / "main.py").read_text(encoding="utf-8", errors="replace")
    return ast.parse(source, filename="main.py")


def _find_function(tree: ast.AST, func_name: str) -> ast.FunctionDef:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == func_name:
            return node
    raise AssertionError(f"Expected to find function {func_name!r} in main.py")


def _has_window_show_call(func: ast.FunctionDef) -> bool:
    for node in ast.walk(func):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Attribute) and node.func.attr == "show":
            if isinstance(node.func.value, ast.Name) and node.func.value.id == "window":
                return True
    return False


def test_on_widgets_ready_shows_window_without_waiting_for_train_signals():
    """Regression test for splash sticking forever.

    In the past, we waited for `train_manager.trains_updated` to show the main
    window. Under some launch paths (notably DE launcher), that signal could be
    delayed/missed due to threading/event timing, leaving the splash visible.

    Invariant: `on_widgets_ready` must show the main window directly.
    """

    tree = _parse_main_py()
    on_widgets_ready = _find_function(tree, "on_widgets_ready")
    assert _has_window_show_call(on_widgets_ready), "Expected window.show() call in on_widgets_ready"


def test_main_installs_init_watchdog_to_prevent_infinite_splash():
    """Regression test: startup must have a splash watchdog.

    If `initialization_completed` never fires (hang), we still want to show the
    main window and close the splash after a grace period.
    """

    tree = _parse_main_py()
    main_func = _find_function(tree, "main")

    # Look for a QTimer.singleShot(10000, ...) call in main().
    has_watchdog = False
    for node in ast.walk(main_func):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Attribute) and node.func.attr == "singleShot":
            if node.args and isinstance(node.args[0], ast.Constant) and node.args[0].value == 10000:
                has_watchdog = True
                break

    assert has_watchdog, "Expected a QTimer.singleShot(10000, ...) watchdog in main()"


def test_fallback_startup_shows_window_without_waiting_for_train_signals():
    """Same invariant as the primary path, but for fallback_startup."""

    tree = _parse_main_py()
    fallback_startup = _find_function(tree, "fallback_startup")
    assert _has_window_show_call(fallback_startup), "Expected window.show() call in fallback_startup"
