"""Railway line parsing helpers extracted from JsonDataRepository."""

from __future__ import annotations

from typing import Any, Optional

from src.core.models.railway_line import LineStatus, RailwayLine


def parse_railway_line_json_with_index(
    *, repo, line_info: dict[str, Any], line_data: dict[str, Any]
) -> Optional[RailwayLine]:
    """Parse railway line data from JSON structure using index information."""

    try:
        line_name = line_info.get("name", "Unknown")

        stations: list[str] = []
        if "stations" in line_data:
            stations_data = line_data["stations"]
            if isinstance(stations_data, list):
                for station_data in stations_data:
                    if isinstance(station_data, dict):
                        station_name = station_data.get("name", "")
                        if station_name:
                            stations.append(station_name)
                    elif isinstance(station_data, str):
                        stations.append(station_data)
        elif "major_stations" in line_data:
            stations = line_data["major_stations"]

        unique_stations: list[str] = []
        seen: set[str] = set()
        for station in stations:
            if station and station not in seen:
                unique_stations.append(station)
                seen.add(station)

        if len(unique_stations) < 2:
            repo.logger.warning(
                "Railway line %s has insufficient stations: %s",
                line_name,
                unique_stations,
            )
            return None

        journey_times: dict[str, Any] = {}
        if "typical_journey_times" in line_data:
            raw_journey_times = line_data["typical_journey_times"]
            if isinstance(raw_journey_times, dict):
                station_set = set(unique_stations)
                for journey_key, time_value in raw_journey_times.items():
                    if journey_key == "metadata" or not isinstance(time_value, (int, float)):
                        continue
                    if "-" in journey_key:
                        parts = journey_key.split("-", 1)
                        if len(parts) == 2:
                            from_station = parts[0].strip()
                            to_station = parts[1].strip()
                            if from_station in station_set and to_station in station_set:
                                journey_times[journey_key] = time_value
                            else:
                                repo.logger.debug(
                                    "Skipping journey time %s: stations not in line",
                                    journey_key,
                                )

        line_type = repo._determine_line_type(line_name)

        return RailwayLine(
            name=line_name,
            stations=unique_stations,
            line_type=line_type,
            status=LineStatus.ACTIVE,
            operator=line_info.get("operator"),
            journey_times=journey_times if journey_times else None,
        )

    except Exception as exc:  # pragma: no cover
        repo.logger.error(
            "Failed to parse railway line %s: %s",
            line_info.get("name", "Unknown"),
            exc,
        )
        return None


def parse_railway_line_json_from_file(
    *, repo, file_name: str, data: dict[str, Any]
) -> Optional[RailwayLine]:
    """Parse railway line data from JSON file when not in index."""

    try:
        metadata = data.get("metadata", {})
        line_name = metadata.get("line_name", "")
        if not line_name:
            line_name = file_name.replace(".json", "").replace("_", " ").title()

        stations: list[str] = []
        if "stations" in data:
            stations_data = data["stations"]
            if isinstance(stations_data, list):
                for station_data in stations_data:
                    if isinstance(station_data, dict):
                        station_name = station_data.get("name", "")
                        if station_name:
                            stations.append(station_name)
                    elif isinstance(station_data, str):
                        stations.append(station_data)
        elif "major_stations" in data:
            stations = data["major_stations"]

        unique_stations: list[str] = []
        seen: set[str] = set()
        for station in stations:
            if station and station not in seen:
                unique_stations.append(station)
                seen.add(station)

        if len(unique_stations) < 2:
            repo.logger.warning(
                "Railway line %s has insufficient stations: %s",
                line_name,
                unique_stations,
            )
            return None

        journey_times: dict[str, Any] = {}
        if "typical_journey_times" in data:
            raw_journey_times = data["typical_journey_times"]
            if isinstance(raw_journey_times, dict):
                station_set = set(unique_stations)
                for journey_key, time_value in raw_journey_times.items():
                    if journey_key == "metadata" or not isinstance(time_value, (int, float)):
                        continue
                    if "-" in journey_key:
                        parts = journey_key.split("-", 1)
                        if len(parts) == 2:
                            from_station = parts[0].strip()
                            to_station = parts[1].strip()
                            if from_station in station_set and to_station in station_set:
                                journey_times[journey_key] = time_value
                            else:
                                repo.logger.debug(
                                    "Skipping journey time %s: stations not in line",
                                    journey_key,
                                )

        line_type = repo._determine_line_type(line_name)
        operator = metadata.get("operator", "Unknown")

        return RailwayLine(
            name=line_name,
            stations=unique_stations,
            line_type=line_type,
            status=LineStatus.ACTIVE,
            operator=operator,
            journey_times=journey_times if journey_times else None,
        )

    except Exception as exc:  # pragma: no cover
        repo.logger.error("Failed to parse railway line from file %s: %s", file_name, exc)
        return None

