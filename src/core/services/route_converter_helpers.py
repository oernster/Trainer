"""Helper functions for [`RouteConverter`](src/core/services/route_converter.py:17).

Split out to keep modules under the <= 400 non-blank LOC gate.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_line_data_with_coordinates(line_name: str, *, logger) -> dict[str, Any] | None:
    """Get line data with station coordinates from JSON files."""

    try:
        # Try to use data path resolver
        try:
            from ...utils.data_path_resolver import get_lines_directory

            lines_dir = get_lines_directory()
        except (ImportError, FileNotFoundError):
            # Fallback to old method
            lines_dir = Path("src/data/lines")

        # Convert line name to potential file name
        normalized_name = line_name.lower()
        normalized_name = (
            normalized_name.replace(" line", "")
            .replace(" main", "")
            .replace(" railway", "")
        )
        normalized_name = normalized_name.replace(" ", "_").replace("-", "_")

        potential_files = [
            f"{normalized_name}.json",
            f"{normalized_name}_line.json",
            f"{normalized_name}_main_line.json",
            f"{normalized_name}_railway.json",
        ]

        exact_match = line_name.lower().replace(" ", "_").replace("-", "_")
        potential_files.insert(0, f"{exact_match}.json")

        # Search through all JSON files if no direct match
        if not any((lines_dir / f).exists() for f in potential_files):
            for json_file in lines_dir.glob("*.json"):
                if json_file.name.endswith(".backup"):
                    continue
                try:
                    with open(json_file, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    metadata = data.get("metadata", {})
                    if metadata.get("line_name") == line_name:
                        return data
                except Exception:
                    continue

            logger.debug("No file found for line: %s", line_name)
            return None

        for file_name in potential_files:
            line_file = lines_dir / file_name
            if line_file.exists():
                with open(line_file, "r", encoding="utf-8") as f:
                    return json.load(f)

        return None

    except Exception as e:
        logger.error("Failed to load line data for %s: %s", line_name, e)
        return None


def generate_train_service_id(
    line_name: str,
    service_pattern: str | None,
    from_station: str,
    to_station: str,
) -> str:
    """Generate a train service ID that identifies the physical train service."""

    if line_name == "WALKING":
        return f"WALKING_{from_station}_{to_station}"

    line_key = line_name.upper().replace(" ", "_").replace("-", "_")

    if line_name == "Reading to Basingstoke Line":
        return "GWR_READING_BASINGSTOKE_SERVICE"
    if line_name == "South Western Main Line":
        return "SWR_MAIN_LINE_SERVICE"
    if line_name == "Portsmouth Direct Line":
        # Portsmouth Direct Line trains continue as South Western Main Line trains
        return "SWR_MAIN_LINE_SERVICE"
    if "South Western" in line_name:
        return "SWR_MAIN_LINE_SERVICE"
    if "Portsmouth" in line_name and "Direct" in line_name:
        return "SWR_MAIN_LINE_SERVICE"
    if "Great Western" in line_name or "Reading" in line_name or "GWR" in line_name:
        return "GWR_MAIN_LINE_SERVICE"
    if "Cross Country" in line_name or "CrossCountry" in line_name:
        return "CROSS_COUNTRY_SERVICE"
    if line_name == "London Underground":
        return "LONDON_UNDERGROUND_SERVICE"

    service_suffix = f"_{service_pattern}" if service_pattern else ""
    return f"{line_key}_SERVICE{service_suffix}"

