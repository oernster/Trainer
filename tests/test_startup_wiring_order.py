from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CallSite:
    name: str
    line: int


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


def _call_line_numbers(func: ast.FunctionDef) -> list[CallSite]:
    calls: list[CallSite] = []

    for node in ast.walk(func):
        if not isinstance(node, ast.Call):
            continue

        # train_manager.trains_updated.connect(...)
        if isinstance(node.func, ast.Attribute) and node.func.attr == "connect":
            v = node.func.value
            if (
                isinstance(v, ast.Attribute)
                and v.attr == "trains_updated"
                and isinstance(v.value, ast.Name)
                and v.value.id == "train_manager"
            ):
                calls.append(CallSite("connect_trains_updated", getattr(node, "lineno", 0)))

        # train_manager.fetch_trains()
        if (
            isinstance(node.func, ast.Attribute)
            and node.func.attr == "fetch_trains"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "train_manager"
        ):
            calls.append(CallSite("fetch_trains", getattr(node, "lineno", 0)))

    return sorted(calls, key=lambda c: c.line)


def test_startup_wires_trains_updated_before_fetch_to_avoid_splash_hang():
    """Regression test for a first-run splash hang.

    On a fresh install (no station config), TrainManager can emit
    `trains_updated([])` quickly. If the UI connects to `trains_updated` *after*
    calling `fetch_trains()`, the signal can be missed and the splash can remain
    visible forever.

    This test asserts the wiring order in `on_widgets_ready` is:
      connect(trains_updated)  ->  fetch_trains()
    """

    tree = _parse_main_py()
    on_widgets_ready = _find_function(tree, "on_widgets_ready")

    calls = _call_line_numbers(on_widgets_ready)
    connect_lines = [c.line for c in calls if c.name == "connect_trains_updated"]
    fetch_lines = [c.line for c in calls if c.name == "fetch_trains"]

    assert connect_lines, "Expected a trains_updated.connect(...) call in on_widgets_ready"
    assert fetch_lines, "Expected a train_manager.fetch_trains() call in on_widgets_ready"
    assert min(connect_lines) < min(fetch_lines), (
        "Expected trains_updated.connect(...) to occur before fetch_trains() in on_widgets_ready; "
        f"connect at lines {connect_lines}, fetch at lines {fetch_lines}"
    )


def test_fallback_startup_wires_trains_updated_before_fetch_to_avoid_splash_hang():
    """Same invariant as the primary startup path, but for fallback_startup."""

    tree = _parse_main_py()
    fallback_startup = _find_function(tree, "fallback_startup")

    calls = _call_line_numbers(fallback_startup)
    connect_lines = [c.line for c in calls if c.name == "connect_trains_updated"]
    fetch_lines = [c.line for c in calls if c.name == "fetch_trains"]

    assert connect_lines, "Expected a trains_updated.connect(...) call in fallback_startup"
    assert fetch_lines, "Expected a train_manager.fetch_trains() call in fallback_startup"
    assert min(connect_lines) < min(fetch_lines), (
        "Expected trains_updated.connect(...) to occur before fetch_trains() in fallback_startup; "
        f"connect at lines {connect_lines}, fetch at lines {fetch_lines}"
    )

