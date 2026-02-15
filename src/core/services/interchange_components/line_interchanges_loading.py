"""Line interchanges cache loading extracted from InterchangeDetectionService."""

from __future__ import annotations

import json
from pathlib import Path


def get_line_interchanges(*, service):
    """Thread-safe lazy loader for line interchanges."""

    if service._line_interchanges_cache is not None:
        return service._line_interchanges_cache

    with service._interchanges_lock:
        if service._line_interchanges_cache is not None:
            return service._line_interchanges_cache

        service.logger.debug("Loading line interchanges data (lazy loading)")

        try:
            from ....utils.data_path_resolver import get_data_directory

            data_dir = get_data_directory()

            interchange_file = data_dir / "interchange_connections.json"
            if not interchange_file.exists():
                # Optional file: warn once per process and negative-cache the empty mapping.
                service.logger.warning(
                    "Interchange connections file not found: %s",
                    interchange_file,
                )
                service._line_interchanges_cache = {}
                return service._line_interchanges_cache

            with open(interchange_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            line_interchanges_data = data.get("line_interchanges", [])

            line_interchanges = {}
            for item in line_interchanges_data:
                station = item.get("station", "")
                connections = item.get("connections", [])
                if station:
                    line_interchanges[station] = connections

            service.logger.debug(
                "Loaded line interchanges for %s stations",
                len(line_interchanges),
            )
            service._line_interchanges_cache = line_interchanges
            return service._line_interchanges_cache

        except Exception as exc:  # pragma: no cover
            service.logger.error("Error loading line interchanges data: %s", exc)
            return {}

