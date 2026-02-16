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
class ImportViolation:
    file: Path
    line: int
    imported_module: str
    rule: str


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


def test_qt_imports_are_ui_only_with_explicit_allowlist():
    """Forbid Qt imports outside `src/ui/**`, with a narrow legacy allowlist.

    Phase 2 goal is *no* Qt in managers/workers/services/cache/api/utils.
    Today there are still Qt-based managers/workers; we allowlist them
    explicitly so additions become CI-failing.
    """

    repo_root = Path(__file__).resolve().parents[1]

    allowlisted_non_ui_files = {
        # Legacy Qt-based orchestration layers (follow-up: move under src/ui)
        "src/managers/astronomy_manager.py",
        "src/managers/combined_forecast_manager.py",
        "src/managers/initialization_manager.py",
        "src/managers/theme_manager.py",
        "src/managers/train_manager.py",
        "src/managers/weather_manager.py",
        # Legacy Qt worker infrastructure
        "src/workers/base_worker.py",
        "src/workers/database_worker.py",
        "src/workers/route_worker.py",
        "src/workers/worker_manager.py",
    }

    violations: list[ImportViolation] = []
    for file_path in _iter_repo_python_files(repo_root):
        rel = file_path.relative_to(repo_root).as_posix()

        if rel.startswith("src/ui/"):
            continue
        if rel in allowlisted_non_ui_files:
            continue

        source = file_path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source, filename=str(file_path))

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".")[0] in {"PySide6", "PySide2", "pyside6", "pyside2"}:
                        violations.append(
                            ImportViolation(
                                file=Path(rel),
                                line=getattr(node, "lineno", 1),
                                imported_module=alias.name,
                                rule="qt_imports_must_be_ui_or_allowlisted",
                            )
                        )
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module.split(".")[0] in {"PySide6", "PySide2", "pyside6", "pyside2"}:
                    violations.append(
                        ImportViolation(
                            file=Path(rel),
                            line=getattr(node, "lineno", 1),
                            imported_module=node.module,
                            rule="qt_imports_must_be_ui_or_allowlisted",
                        )
                    )

    details = "\n".join(
        f"{v.file.as_posix()}:{v.line}  {v.rule}  imports {v.imported_module}"
        for v in sorted(violations, key=lambda x: (str(x.file), x.line, x.imported_module))
    )
    assert not violations, "Qt import violations detected:\n" + details

