from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path


EXCLUDED_DIRNAMES = {
    "venv",
    "docs",
    "assets",
    "licenses",
    "dist",
    ".pytest_cache",
}


@dataclass(frozen=True)
class Violation:
    file: Path
    line: int
    rule: str
    detail: str


def _is_excluded_path(path: Path) -> bool:
    return any(part in EXCLUDED_DIRNAMES for part in path.parts)


def _iter_repo_python_files(repo_root: Path) -> list[Path]:
    files: list[Path] = []
    for top in (repo_root / "src",):
        if not top.exists():
            continue
        for p in top.rglob("*.py"):
            rel = p.relative_to(repo_root)
            if _is_excluded_path(rel):
                continue
            files.append(p)
    return sorted(files)


def test_phase2_composition_helpers_are_only_imported_from_bootstrap_or_tests():
    """Enforce Phase 2: composition helper modules are bootstrap-only."""

    repo_root = Path(__file__).resolve().parents[1]
    forbidden_imports = {"src.services.routing.composition"}

    violations: list[Violation] = []
    for file_path in _iter_repo_python_files(repo_root):
        rel = file_path.relative_to(repo_root)

        source = file_path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source, filename=str(file_path))

        # Allow bootstrap and tests.
        if rel.as_posix().startswith("tests/"):
            continue
        if rel.as_posix() == "src/app/bootstrap.py":
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                module = node.module
                if module in forbidden_imports:
                    violations.append(
                        Violation(
                            file=rel,
                            line=getattr(node, "lineno", 1),
                            rule="phase2_composition_helpers_bootstrap_only",
                            detail=f"from {module} import ...",
                        )
                    )
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in forbidden_imports:
                        violations.append(
                            Violation(
                                file=rel,
                                line=getattr(node, "lineno", 1),
                                rule="phase2_composition_helpers_bootstrap_only",
                                detail=f"import {alias.name}",
                            )
                        )

    details = "\n".join(
        f"{v.file.as_posix()}:{v.line}  {v.rule}  {v.detail}"
        for v in sorted(violations, key=lambda x: (str(x.file), x.line, x.rule, x.detail))
    )
    assert not violations, "Phase 2 composition-helper import violations detected:\n" + details


def test_phase2_forbid_service_locators_and_module_level_instances_in_selected_layers():
    """Phase 2 (pragmatic): forbid hidden object graphs in critical layers.

    Scope: `src/app`, `src/managers`, `src/services`, `src/cache`, `src/api`, `src/workers`.

    Notes:
      - We do *not* globally ban `get_*` helpers everywhere: the codebase contains
        many pure helper functions named `get_*` (e.g. path resolvers) that are
        not singletons.
      - We do ban `__new__` singleton patterns and explicit module-level
        instantiation of selected classes.
    """

    repo_root = Path(__file__).resolve().parents[1]

    scoped_prefixes = (
        "src/app/",
        "src/managers/",
        "src/services/",
        "src/cache/",
        "src/api/",
        "src/workers/",
    )

    banned_getter_prefixes = (
        # Service locator patterns we explicitly removed / do not want.
        "get_station_cache_manager",
        "get_essential_station_cache",
        "get_essential_stations",
    )

    violations: list[Violation] = []
    for file_path in _iter_repo_python_files(repo_root):
        rel = file_path.relative_to(repo_root)

        if rel.as_posix().startswith("tests/"):
            continue
        if not rel.as_posix().startswith(scoped_prefixes):
            continue

        source = file_path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source, filename=str(file_path))

        for node in tree.body:
            # Ban known service-locator getters by name.
            if isinstance(node, ast.FunctionDef) and node.name.startswith(banned_getter_prefixes):
                violations.append(
                    Violation(
                        file=rel,
                        line=getattr(node, "lineno", 1),
                        rule="phase2_forbid_service_locator_getters",
                        detail=node.name,
                    )
                )

            # Ban module-level concrete instances like `thing = Service()`.
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
                func_expr = ast.unparse(node.value.func) if hasattr(ast, "unparse") else "<callable>"
                if func_expr and func_expr[:1].isupper():
                    violations.append(
                        Violation(
                            file=rel,
                            line=getattr(node, "lineno", 1),
                            rule="phase2_forbid_module_level_concrete_instances",
                            detail=f"{func_expr}(...) at module scope",
                        )
                    )

            # Ban __new__ singleton patterns in scoped packages.
            if isinstance(node, ast.ClassDef):
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name == "__new__":
                        violations.append(
                            Violation(
                                file=rel,
                                line=getattr(item, "lineno", 1),
                                rule="phase2_forbid___new___singletons",
                                detail=f"{node.name}.__new__",
                            )
                        )

    details = "\n".join(
        f"{v.file.as_posix()}:{v.line}  {v.rule}  {v.detail}"
        for v in sorted(violations, key=lambda x: (str(x.file), x.line, x.rule, x.detail))
    )
    assert not violations, "Phase 2 singleton/service-locator violations detected:\n" + details


def test_phase2_forbid_factory_based_composition_outside_bootstrap():
    """Enforce Phase 2: factories must not be used as composition outside bootstrap."""

    repo_root = Path(__file__).resolve().parents[1]

    violations: list[Violation] = []
    for file_path in _iter_repo_python_files(repo_root):
        rel = file_path.relative_to(repo_root)

        if rel.as_posix().startswith("tests/"):
            continue
        if rel.as_posix() == "src/app/bootstrap.py":
            continue

        source = file_path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source, filename=str(file_path))

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not isinstance(node.func, ast.Attribute):
                continue

            # WeatherAPIFactory.create_* is composition.
            if (
                isinstance(node.func.value, ast.Name)
                and node.func.value.id == "WeatherAPIFactory"
            ):
                violations.append(
                    Violation(
                        file=rel,
                        line=getattr(node, "lineno", 1),
                        rule="phase2_forbid_factories_as_composition",
                        detail=f"WeatherAPIFactory.{node.func.attr}(...)",
                    )
                )

    details = "\n".join(
        f"{v.file.as_posix()}:{v.line}  {v.rule}  {v.detail}"
        for v in sorted(violations, key=lambda x: (str(x.file), x.line, x.rule, x.detail))
    )
    assert not violations, "Factory-based composition violations detected:\n" + details

