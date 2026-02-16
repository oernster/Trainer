import ast
from pathlib import Path


def _iter_python_files() -> list[Path]:
    root = Path(__file__).resolve().parents[1]
    ignore_dirs = {
        ".venv",
        "venv",
        "__pycache__",
        ".git",
        "build",
        "dist",
        "main.build",
        "main.dist",
        "main.onefile-build",
    }
    python_files: list[Path] = []
    for path in root.rglob("*.py"):
        if any(part in ignore_dirs for part in path.parts):
            continue
        python_files.append(path)
    return python_files


def _has_top_level_assignment(module: ast.Module, name: str) -> bool:
    for node in module.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    return True
        if isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and node.target.id == name:
                return True
    return False


def test__version_defined_only_in_root_version_module():
    offenders: list[str] = []
    for path in _iter_python_files():
        if path.name == "version.py" and path.parent == Path(__file__).resolve().parents[1]:
            continue

        module = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        if _has_top_level_assignment(module, "__version__"):
            offenders.append(str(path.relative_to(Path(__file__).resolve().parents[1])))

    assert offenders == [], f"Found __version__ assignments outside version.py: {offenders}"


def test_no_known_schema_version_literals_reintroduced():
    # Guardrail: these were previously hardcoded and should now come from version.py imports.
    forbidden_snippets = [
        "cache_version = \"1.0.0\"",
        "self.cache_version = \"1.0.0\"",
        "self._data_version = \"1.0.0\"",
        "get(\"config_version\", \"1.0.0\")",
    ]

    offenders: list[str] = []
    for path in _iter_python_files():
        text = path.read_text(encoding="utf-8")
        for snippet in forbidden_snippets:
            if snippet in text:
                offenders.append(f"{path.relative_to(Path(__file__).resolve().parents[1])}: {snippet}")

    assert offenders == [], "Forbidden version literals found:\n" + "\n".join(offenders)

