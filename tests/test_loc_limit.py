from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LocOffender:
    path: Path
    non_blank_loc: int


def _is_excluded_path(path: Path, excluded_dirnames: set[str]) -> bool:
    return any(part in excluded_dirnames for part in path.parts)


def _count_non_blank_lines(path: Path) -> int:
    # Physical LOC excluding blank lines only (comments/docstrings still count).
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return sum(1 for line in lines if line.strip())


def _iter_python_files(repo_root: Path) -> list[Path]:
    excluded_dirnames = {
        "venv",
        "docs",
        "assets",
        "licenses",
        "dist",
        ".pytest_cache",
    }

    files: list[Path] = []
    for top in (repo_root / "src", repo_root / "tests"):
        if not top.exists():
            continue
        for path in top.rglob("*.py"):
            rel = path.relative_to(repo_root)
            if _is_excluded_path(rel, excluded_dirnames):
                continue
            files.append(path)

    return sorted(files)


def test_all_python_files_are_at_most_400_loc():
    repo_root = Path(__file__).resolve().parents[1]

    offenders: list[LocOffender] = []
    for path in _iter_python_files(repo_root):
        rel = path.relative_to(repo_root)
        loc = _count_non_blank_lines(path)
        if loc > 400:
            offenders.append(LocOffender(path=rel, non_blank_loc=loc))

    offenders_sorted = sorted(offenders, key=lambda o: o.non_blank_loc, reverse=True)
    details = "\n".join(
        f"{o.non_blank_loc:5d}  {o.path.as_posix()}" for o in offenders_sorted
    )

    assert not offenders_sorted, (
        "Files must be <= 400 non-blank lines. Refactor by extracting smaller modules.\n"
        + details
    )

