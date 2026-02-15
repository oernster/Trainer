"""Data directory resolution helpers."""

from __future__ import annotations

from pathlib import Path


def get_lines_directory_fallback() -> Path:
    """Resolve the lines directory, using the resolver if available."""

    # Always use the shared resolver. If it cannot locate data, it should raise
    # (and the calling code can decide whether that is fatal or optional).
    from ....utils.data_path_resolver import get_lines_directory

    return get_lines_directory()

