"""Railway line parsing helpers extracted from JsonDataRepository."""

from __future__ import annotations

from typing import Any, Optional

from ...models.railway_line import LineStatus, RailwayLine


def parse_railway_line_json(
    *, repo, line_name: str, data: dict[str, Any]
) -> Optional[RailwayLine]:
    """Parse railway line data from a generic JSON structure."""

    try:
        stations: list[str] = []

        # Handle different JSON structures
        if "stations" in data:
            stations = data["stations"]
        elif "major_stations" in data:
            stations = data["major_stations"]
        elif isinstance(data, dict):
            # Look for journey time data to extract stations
            for key, value in data.items():
                if isinstance(value, dict):
                    # This might be journey time data
                    stations.extend(value.keys())
                    if key not in stations:
                        stations.append(key)

        # Remove duplicates while preserving order
        unique_stations: list[str] = []
        seen: set[str] = set()
        for station in stations:
            if station not in seen:
                unique_stations.append(station)
                seen.add(station)

        if len(unique_stations) < 2:
            repo.logger.warning(
                "Railway line %s has insufficient stations: %s",
                line_name,
                unique_stations,
            )
            return None

        journey_times: dict[str, Any] | None = None
        if isinstance(data, dict) and all(isinstance(v, dict) for v in data.values()):
            journey_times = data

        line_type = repo._determine_line_type(line_name)

        return RailwayLine(
            name=line_name,
            stations=unique_stations,
            line_type=line_type,
            status=LineStatus.ACTIVE,
            journey_times=journey_times,
        )

    except Exception as exc:  # pragma: no cover
        repo.logger.error("Failed to parse railway line %s: %s", line_name, exc)
        return None

