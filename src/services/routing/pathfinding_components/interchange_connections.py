"""Loading of interchange connections used for walking penalty logic."""

from __future__ import annotations

import json
from pathlib import Path


def load_interchange_connections(*, logger) -> dict:
    """Load interchange connections from JSON file."""

    try:
        try:
            # NOTE: this module lives at `src.services.routing.pathfinding_components`.
            # To reach `src.utils.*` we must go up 4 levels.
            from ....utils.data_path_resolver import get_data_file_path

            interchange_file = get_data_file_path("interchange_connections.json")
        except (ImportError, FileNotFoundError):
            interchange_file = Path("src/data/interchange_connections.json")

        if not interchange_file.exists():
            logger.warning("Interchange connections file not found")
            return {}

        with open(interchange_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error("Failed to load interchange connections: %s", exc)
        return {}
