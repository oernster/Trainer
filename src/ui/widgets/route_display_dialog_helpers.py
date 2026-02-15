"""Helpers for [`RouteDisplayDialog`](src/ui/widgets/route_display_dialog.py:27).

This file exists to keep the dialog module under the <= 400 non-blank LOC gate.
The helpers are UI-layer utilities and should not import from the core domain.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)


def build_route_dialog_stylesheet(theme: str) -> str:
    """Return the dialog stylesheet for a given theme name."""

    if theme == "dark":
        return """
            QDialog {
                background-color: #1a1a1a;
                color: #ffffff;
            }
            QLabel {
                color: #ffffff;
                background-color: transparent;
            }
            QPushButton {
                background-color: #1976d2;
                color: #000000;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1565c0;
            }
            QScrollArea {
                border: 1px solid #404040;
                border-radius: 4px;
                background-color: #1a1a1a;
            }
        """

    return """
        QDialog {
            background-color: #ffffff;
            color: #212121;
        }
        QLabel {
            color: #212121;
            background-color: transparent;
        }
        QPushButton {
            background-color: #1976d2;
            color: #ffffff;
            border: none;
            border-radius: 4px;
            padding: 8px 16px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #1565c0;
        }
        QScrollArea {
            border: 1px solid #e0e0e0;
            border-radius: 4px;
            background-color: #ffffff;
        }
    """


def station_has_underground_connection(
    *,
    train_data: Any,
    underground_formatter: Any,
    station_name: str,
) -> bool:
    """Return True if `station_name` is an endpoint of an underground segment."""

    if not hasattr(train_data, "route_segments") or not train_data.route_segments:
        return False

    for segment in train_data.route_segments:
        if underground_formatter.is_underground_segment(segment):
            segment_from = getattr(segment, "from_station", "")
            segment_to = getattr(segment, "to_station", "")

            if station_name == segment_from or station_name == segment_to:
                return True

    return False


def build_station_to_files_mapping(lines_dir: Path) -> dict[str, list[str]]:
    """Build mapping of station name -> list of line JSON filenames."""

    station_to_files: dict[str, list[str]] = {}

    if not lines_dir.exists():
        logger.error("Lines directory not found: %s", lines_dir)
        return {}

    try:
        for json_file in lines_dir.glob("*.json"):
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            stations = data.get("stations", [])
            file_name = json_file.stem

            for station in stations:
                station_name = station.get("name", "")
                if not station_name:
                    continue

                station_to_files.setdefault(station_name, []).append(file_name)

        logger.debug(
            "Built station-to-files mapping with %s stations", len(station_to_files)
        )
        return station_to_files

    except Exception as e:
        logger.error("Failed to build station-to-files mapping: %s", e)
        return {}

