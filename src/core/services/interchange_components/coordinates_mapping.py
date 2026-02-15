"""Station coordinates mapping."""

from __future__ import annotations

import json

from .line_dir_resolution import get_lines_directory_fallback


def build_station_coordinates_mapping(*, logger) -> dict[str, dict[str, float]]:
    station_coordinates: dict[str, dict[str, float]] = {}

    lines_dir = get_lines_directory_fallback()
    if not lines_dir.exists():
        logger.error("Lines directory not found: %s", lines_dir)
        return {}

    try:
        for json_file in lines_dir.glob("*.json"):
            if json_file.name.endswith(".backup"):
                continue

            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            stations = data.get("stations", [])
            for station in stations:
                station_name = station.get("name", "")
                coordinates = station.get("coordinates", {})
                if (
                    station_name
                    and coordinates
                    and "lat" in coordinates
                    and "lng" in coordinates
                ):
                    station_coordinates[station_name] = coordinates

        logger.debug(
            "Built station coordinates mapping with %s stations",
            len(station_coordinates),
        )
        return station_coordinates
    except Exception as exc:  # pragma: no cover
        logger.error("Failed to build station coordinates mapping: %s", exc)
        return {}

