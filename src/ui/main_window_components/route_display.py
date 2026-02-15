"""Route display/logging helpers."""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def update_route_display(
    *, window, from_station: str, to_station: str, via_stations: Optional[list[str]] = None
) -> None:
    """Update route display (header removed - now only logs route info)."""

    def clean_station_name(station_name: str) -> str:
        """Remove railway line context from station name for cleaner display."""

        if not station_name:
            return station_name
        if "(" in station_name:
            return station_name.split("(")[0].strip()
        return station_name

    clean_from = clean_station_name(from_station)
    clean_to = clean_station_name(to_station)

    if via_stations:
        clean_via_stations = [clean_station_name(station) for station in via_stations]
        via_text = " -> ".join(clean_via_stations)
        route_text = f"Route: {clean_from} -> {via_text} -> {clean_to}"
    else:
        route_text = f"Route: {clean_from} -> {clean_to}"

    logger.debug("Route display updated: %s", route_text)

