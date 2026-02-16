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


def test_no_top_level_ui_imports_under_src():
    """Flatpak packaging invariant.

    In Flatpak we ship the code as `/app/src` and set `PYTHONPATH=/app`.
    That means `src` is the import root; importing `ui.*` will fail because
    there is no top-level `ui` package.

    Enforce: No `import ui` or `from ui ...` anywhere under `src/**`.
    """

    repo_root = Path(__file__).resolve().parents[1]

    violations: list[ImportViolation] = []
    for file_path in _iter_repo_python_files(repo_root):
        rel = file_path.relative_to(repo_root).as_posix()
        source = file_path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source, filename=str(file_path))

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "ui" or alias.name.startswith("ui."):
                        violations.append(
                            ImportViolation(
                                file=Path(rel),
                                line=getattr(node, "lineno", 1),
                                imported_module=alias.name,
                                rule="no_top_level_ui_imports_under_src",
                            )
                        )
            elif isinstance(node, ast.ImportFrom):
                # Only forbid *absolute* imports from `ui.*`.
                # For relative imports (e.g. `from ...ui.formatters import X`),
                # `ast` stores the dots in `node.level`, while `node.module`
                # remains `ui.formatters...`.
                if (
                    getattr(node, "level", 0) == 0
                    and node.module
                    and (node.module == "ui" or node.module.startswith("ui."))
                ):
                    violations.append(
                        ImportViolation(
                            file=Path(rel),
                            line=getattr(node, "lineno", 1),
                            imported_module=node.module,
                            rule="no_top_level_ui_imports_under_src",
                        )
                    )

    details = "\n".join(
        f"{v.file.as_posix()}:{v.line}  {v.rule}  imports {v.imported_module}"
        for v in sorted(violations, key=lambda x: (str(x.file), x.line, x.imported_module))
    )
    assert not violations, "Flatpak import invariant violations detected:\n" + details
