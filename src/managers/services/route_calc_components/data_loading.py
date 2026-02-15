"""Data loading helpers for `RouteCalculationService`."""

from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def load_all_line_data(*, service) -> dict[str, dict]:
    """Load all railway line JSON data files with caching."""

    if service._line_data_cache is not None:
        return service._line_data_cache

    try:
        try:
            from ...utils.data_path_resolver import get_lines_directory

            lines_dir = get_lines_directory()
        except (ImportError, FileNotFoundError):
            lines_dir = Path(__file__).parent.parent.parent / "data" / "lines"

        if not lines_dir.exists():
            logger.error("Lines directory not found: %s", lines_dir)
            return {}

        line_data: dict[str, dict] = {}
        for json_file in lines_dir.glob("*.json"):
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            line_name = data.get("metadata", {}).get("line_name", json_file.stem)
            line_data[str(line_name)] = data

        logger.info("Loaded %s railway line data files", len(line_data))
        service._line_data_cache = line_data
        return line_data

    except Exception as exc:  # pragma: no cover
        logger.error("Failed to load line data: %s", exc)
        return {}


def load_walking_connections(*, service) -> dict:
    """Load walking connections from interchange_connections.json with caching."""

    if service._walking_connections_cache is not None:
        return service._walking_connections_cache

    try:
        try:
            from ...utils.data_path_resolver import get_data_file_path

            connections_file = get_data_file_path("interchange_connections.json")
        except (ImportError, FileNotFoundError):
            connections_file = (
                Path(__file__).parent.parent.parent / "data" / "interchange_connections.json"
            )

        if not connections_file.exists():
            logger.warning("Interchange connections file not found: %s", connections_file)
            return {}

        with open(connections_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        walking_connections: dict = {}
        for connection in data.get("connections", []):
            if connection.get("connection_type") != "WALKING":
                continue

            from_station = connection.get("from_station")
            to_station = connection.get("to_station")
            walking_distance_m = connection.get("walking_distance_m", 1000)
            distance_km = walking_distance_m / 1000.0
            time_minutes = connection.get("time_minutes", 10)

            if not from_station or not to_station:
                continue

            conn_info = {"distance_km": distance_km, "time_minutes": time_minutes}
            walking_connections[(from_station, to_station)] = conn_info
            walking_connections[(to_station, from_station)] = conn_info

        logger.info("Loaded %s walking connections", len(walking_connections))
        service._walking_connections_cache = walking_connections
        return walking_connections

    except Exception as exc:  # pragma: no cover
        logger.error("Error loading walking connections: %s", exc)
        return {}

