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


# ---------------------------------------------------------------------------
# Phase 2 allowlist policy (composition root)
# ---------------------------------------------------------------------------
# Only these modules may *assemble the object graph* (construct concrete
# services/repositories/managers and wire them together):
#   - `src.app.bootstrap`
#   - specific pure constructor helper modules (when explicitly approved)
#
# All other modules must use dependency injection and must not create hidden
# object graphs (singletons, factories-as-composition, module-level instances).

PHASE2_COMPOSITION_ALLOWLIST_PREFIXES = (
    "src.app.bootstrap",
    # Approved constructor helper modules (bootstrap-only callers enforced below)
    "src.services.routing.composition",
)


LAYER_UI = "ui"
LAYER_SHARED_MODELS = "shared_models"
LAYER_DOMAIN = "domain"
LAYER_APPLICATION = "application"
LAYER_INFRASTRUCTURE = "infrastructure"


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


def _module_name_for_file(repo_root: Path, file_path: Path) -> str:
    """Convert file path to a Python module name.

    Examples:
        src/models/x.py -> src.models.x
        src/models/__init__.py -> src.models
    """

    rel = file_path.relative_to(repo_root)
    parts = list(rel.parts)
    if parts[-1] == "__init__.py":
        parts = parts[:-1]
    else:
        parts[-1] = parts[-1].removesuffix(".py")
    return ".".join(parts)


def _resolve_import_from(current_module: str, node: ast.ImportFrom) -> str | None:
    """Resolve an ImportFrom node to an absolute module string when possible."""

    # Ignore `from __future__ import ...`
    if node.module == "__future__":
        return None

    if node.level == 0:
        return node.module

    current_parts = current_module.split(".")
    # `from .x import y` inside module a.b.c should resolve to a.b.x
    if node.level > len(current_parts):
        return None

    base_parts = current_parts[: -node.level]
    if node.module:
        base_parts.extend(node.module.split("."))
    return ".".join(base_parts)


def _classify_layer(rel_path: Path) -> str | None:
    """Classify modules into coarse-grained architectural layers.

    Transitional policy (explicitly approved):
        The UI is temporarily allowed to import shared data models under
        `src/models/**` while non-UI code is refactored. UI must still not import
        core routing domain directly.

    Layers enforced (non-exhaustive):
        - ui: `src/ui/**`
        - shared_models: `src/models/**`
        - domain: pure core routing domain under `src/core/models/**` and
          `src/core/interfaces/**`
        - application: orchestration and coordination under `src/managers/**` (non-UI)
        - infrastructure: IO-bound adapters and external service implementations under
          `src/services/**`, `src/cache/**`, `src/api/**`, `src/data/**`, `src/utils/**`,
          `src/workers/**`
    """

    rel = rel_path.as_posix()

    if rel.startswith("src/ui/"):
        return LAYER_UI

    if rel.startswith("src/models/"):
        return LAYER_SHARED_MODELS

    if rel.startswith("src/core/models/") or rel.startswith("src/core/interfaces/"):
        return LAYER_DOMAIN

    if rel.startswith("src/managers/"):
        return LAYER_APPLICATION

    if rel.startswith(
        (
            "src/services/",
            "src/cache/",
            "src/api/",
            "src/data/",
            "src/utils/",
            "src/workers/",
        )
    ):
        return LAYER_INFRASTRUCTURE

    return None


def _is_under(rel_path: Path, prefix: str) -> bool:
    return rel_path.as_posix().startswith(prefix)


def _iter_imported_modules(repo_root: Path, file_path: Path) -> list[tuple[int, str]]:
    """Return list of (lineno, module) for imports in a file."""

    source = file_path.read_text(encoding="utf-8", errors="replace")
    tree = ast.parse(source, filename=str(file_path))

    current_module = _module_name_for_file(repo_root, file_path)
    imported: list[tuple[int, str]] = []

    class _ImportVisitor(ast.NodeVisitor):
        def __init__(self) -> None:
            self._in_type_checking = False

        def visit_If(self, node: ast.If) -> None:  # noqa: N802
            # Ignore imports guarded by `if TYPE_CHECKING:`.
            # These are used purely for static typing and should not count as
            # architectural dependencies.
            is_type_checking_guard = (
                isinstance(node.test, ast.Name) and node.test.id == "TYPE_CHECKING"
            )

            prev = self._in_type_checking
            if is_type_checking_guard:
                self._in_type_checking = True

            for stmt in node.body:
                self.visit(stmt)

            self._in_type_checking = prev

            for stmt in node.orelse:
                self.visit(stmt)

        def visit_Import(self, node: ast.Import) -> None:  # noqa: N802
            if self._in_type_checking:
                return
            for alias in node.names:
                imported.append((node.lineno, alias.name))

        def visit_ImportFrom(self, node: ast.ImportFrom) -> None:  # noqa: N802
            if self._in_type_checking:
                return
            resolved = _resolve_import_from(current_module, node)
            if resolved:
                imported.append((node.lineno, resolved))

    _ImportVisitor().visit(tree)
    return imported


def test_architecture_layering_constraints():
    """Enforce strict layering constraints.

    This test is intentionally conservative and AST-based: it prevents accidental
    layer violations without requiring runtime imports.

    Enforced rules:
      - Domain (`src/core/models`, `src/core/interfaces`) must not depend on
        application/infrastructure/UI.
      - Application (`src/core/services`, `src/managers`) must not depend on UI.
      - UI (`src/ui`) must not import core routing domain directly.
      - UI may (temporarily) import shared models under `src/models`.
    """

    repo_root = Path(__file__).resolve().parents[1]

    domain_forbidden_prefixes = (
        # Application + UI
        "src.managers",
        "src.ui",
        # Infrastructure
        "src.api",
        "src.cache",
        "src.data",
        "src.utils",
        "src.workers",
        "src.services",
    )

    application_forbidden_prefixes = (
        "src.ui",
    )

    ui_forbidden_prefixes = (
        # UI must not reach into core routing domain directly
        "src.core.models",
        "src.core.interfaces",
        # UI must not import routing/services implementations directly
        "src.services.routing",
    )

    violations: list[ImportViolation] = []

    for file_path in _iter_repo_python_files(repo_root):
        rel = file_path.relative_to(repo_root)
        layer = _classify_layer(rel)
        if layer is None:
            continue

        for lineno, module in _iter_imported_modules(repo_root, file_path):
            # Only enforce for imports that resolve into our package.
            if not module.startswith("src"):
                continue

            if layer == LAYER_DOMAIN and module.startswith(domain_forbidden_prefixes):
                violations.append(
                    ImportViolation(
                        file=rel,
                        line=lineno,
                        imported_module=module,
                        rule="domain_may_not_import_services_ui_managers_api",
                    )
                )
            elif layer == LAYER_APPLICATION and module.startswith(application_forbidden_prefixes):
                violations.append(
                    ImportViolation(
                        file=rel,
                        line=lineno,
                        imported_module=module,
                        rule="application_may_not_import_ui",
                    )
                )
            elif layer == LAYER_UI and module.startswith(ui_forbidden_prefixes):
                violations.append(
                    ImportViolation(
                        file=rel,
                        line=lineno,
                        imported_module=module,
                        rule="ui_may_not_import_domain",
                    )
                )

    details = "\n".join(
        f"{v.file.as_posix()}:{v.line}  {v.rule}  imports {v.imported_module}"
        for v in sorted(violations, key=lambda x: (str(x.file), x.line, x.imported_module))
    )

    assert not violations, "Architecture layer violations detected:\n" + details


def test_domain_layer_has_no_side_effect_imports():
    """Ensure the domain layer stays pure by forbidding side-effectful imports.

    This is a structural enforcement tool: if the domain imports these modules,
    unit tests can no longer be guaranteed deterministic/pure.

    Forbidden in domain:
      - UI frameworks and threading primitives
      - filesystem/network/OS/time/random/logging

    Notes:
      - We allow `dataclasses` and `typing` and other stdlib utilities.
      - We forbid importing `logging` in domain; domain code should surface
        decisions as return values, not emit logs.
      - IO is owned by infrastructure/repositories.
    """

    repo_root = Path(__file__).resolve().parents[1]

    forbidden_top_level = {
        "logging",
        "pathlib",
        "os",
        "sys",
        "json",
        "pickle",
        "shutil",
        "subprocess",
        "socket",
        "http",
        "urllib",
        "requests",
        "time",
        "random",
        "secrets",
        "uuid",
        "PySide6",
        "PySide2",
        "pyside6",
        "pyside2",
        "threading",
        "multiprocessing",
    }

    # Domain = core routing model + ports.
    domain_roots = (
        Path("src/core/models"),
        Path("src/core/interfaces"),
    )

    violations: list[ImportViolation] = []
    for file_path in _iter_repo_python_files(repo_root):
        rel = file_path.relative_to(repo_root)
        if not any(rel.as_posix().startswith(root.as_posix()) for root in domain_roots):
            continue

        for lineno, module in _iter_imported_modules(repo_root, file_path):
            top = module.split(".")[0]
            if top in forbidden_top_level:
                violations.append(
                    ImportViolation(
                        file=rel,
                        line=lineno,
                        imported_module=module,
                        rule="domain_may_not_import_side_effect_modules",
                    )
                )

    details = "\n".join(
        f"{v.file.as_posix()}:{v.line}  {v.rule}  imports {v.imported_module}"
        for v in sorted(violations, key=lambda x: (str(x.file), x.line, x.imported_module))
    )

    assert not violations, "Domain purity violations detected:\n" + details


def test_domain_layer_does_not_access_wall_clock_or_randomness():
    """Forbid wall-clock/random access from the pure domain.

    We allow importing `datetime`/`date` types for *data representation*, but we
    forbid calling:
      - datetime.now / datetime.utcnow
      - date.today

    This is a hard guardrail that keeps domain logic deterministic.
    """

    repo_root = Path(__file__).resolve().parents[1]

    domain_roots = (
        Path("src/core/models"),
        Path("src/core/interfaces"),
    )

    @dataclass(frozen=True)
    class CallViolation:
        file: Path
        line: int
        expr: str

    def _expr_for_call(node: ast.Call) -> str:
        if isinstance(node.func, ast.Attribute):
            base = ast.unparse(node.func.value) if hasattr(ast, "unparse") else "<expr>"
            return f"{base}.{node.func.attr}()"
        return "<call>()"

    violations: list[CallViolation] = []
    for file_path in _iter_repo_python_files(repo_root):
        rel = file_path.relative_to(repo_root)
        if not any(rel.as_posix().startswith(root.as_posix()) for root in domain_roots):
            continue

        source = file_path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source, filename=str(file_path))

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not isinstance(node.func, ast.Attribute):
                continue

            attr = node.func.attr
            if attr not in {"now", "utcnow", "today"}:
                continue

            # Only catch the obvious global access patterns.
            if isinstance(node.func.value, ast.Name) and node.func.value.id in {"datetime", "date"}:
                violations.append(
                    CallViolation(file=rel, line=getattr(node, "lineno", 1), expr=_expr_for_call(node))
                )

    details = "\n".join(
        f"{v.file.as_posix()}:{v.line}  domain_may_not_access_wall_clock  calls {v.expr}"
        for v in sorted(violations, key=lambda x: (str(x.file), x.line, x.expr))
    )

    assert not violations, "Domain wall-clock violations detected:\n" + details


def test_phase2_composition_helpers_are_only_imported_from_bootstrap_or_tests():
    """Moved to [`tests/test_phase2_boundaries.py`](tests/test_phase2_boundaries.py:1)."""

    # Kept as a stub to avoid churn in history; real assertions live elsewhere.
    assert True


def test_phase2_forbid_module_level_singletons_and_service_locators():
    """Moved to [`tests/test_phase2_boundaries.py`](tests/test_phase2_boundaries.py:1)."""

    assert True


def test_phase2_forbid_qt_imports_outside_ui_layer():
    """Moved to [`tests/test_phase2_boundaries.py`](tests/test_phase2_boundaries.py:1)."""

    assert True

