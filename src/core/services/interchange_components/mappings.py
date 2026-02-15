"""Mapping builders for interchange detection."""

from __future__ import annotations

import json
from pathlib import Path

from .line_dir_resolution import get_lines_directory_fallback


def build_line_to_file_mapping(*, logger) -> dict[str, str]:
    """Build mapping of line names/operators to JSON file stems."""

    line_to_file: dict[str, str] = {}
    lines_dir = get_lines_directory_fallback()
    if not lines_dir.exists():
        logger.error("Lines directory not found: %s", lines_dir)
        return {}

    try:
        json_files = list(lines_dir.glob("*.json"))
        logger.debug("Processing %s JSON files for line mapping", len(json_files))

        for json_file in json_files:
            if json_file.name.endswith(".backup"):
                continue

            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                metadata = data.get("metadata", {})
                line_name = metadata.get("line_name", "").strip()
                operator = metadata.get("operator", "").strip()
                file_name = json_file.stem

                if line_name:
                    line_to_file[line_name] = file_name
                if operator:
                    line_to_file[operator] = file_name

                _add_service_variations(line_to_file, file_name)

            except json.JSONDecodeError as exc:
                logger.error("Invalid JSON in file %s: %s", json_file, exc)
            except Exception as exc:  # pragma: no cover
                logger.error("Error processing file %s: %s", json_file, exc)

        logger.debug("Built line-to-file mapping with %s lines", len(line_to_file))
        return line_to_file

    except Exception as exc:  # pragma: no cover
        logger.error("Failed to build line-to-file mapping: %s", exc)
        return {}


def _add_service_variations(line_to_file: dict[str, str], file_name: str) -> None:
    service_variations = {
        "south_western": ["South Western Railway", "South Western Main Line"],
        "cross_country": ["CrossCountry", "Cross Country", "Cross Country Line"],
        "reading_to_basingstoke": ["Reading to Basingstoke Line"],
        "great_western_main_line": [
            "Great Western Railway",
            "Great Western Main Line",
        ],
    }

    for pattern, variations in service_variations.items():
        if pattern in file_name:
            for variation in variations:
                line_to_file[variation] = file_name


def build_station_to_files_mapping(*, logger) -> dict[str, list[str]]:
    """Build mapping of station name -> list of JSON file stems containing it."""

    station_to_files: dict[str, list[str]] = {}
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
            file_name = json_file.stem
            for station in stations:
                station_name = station.get("name", "")
                if station_name:
                    station_to_files.setdefault(station_name, []).append(file_name)

        logger.debug(
            "Built station-to-files mapping with %s stations", len(station_to_files)
        )
        return station_to_files
    except Exception as exc:  # pragma: no cover
        logger.error("Failed to build station-to-files mapping: %s", exc)
        return {}

