"""Data directory resolution helpers."""

from __future__ import annotations

from pathlib import Path


def get_lines_directory_fallback() -> Path:
    """Resolve the lines directory, using the resolver if available."""

    try:
        from ...utils.data_path_resolver import get_lines_directory

        return get_lines_directory()
    except (ImportError, FileNotFoundError):
        return Path(__file__).parent.parent.parent / "data" / "lines"

