"""UI compatibility helpers extracted from StationDatabaseManager.

These functions keep UI-facing behaviors available while shrinking the
core manager module to satisfy the LOC gate.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def search_stations(*, manager, query: str, limit: int = 10) -> list[str]:
    """Search for stations matching the query with disambiguation context."""

    if not manager.loaded:
        if not manager.load_database():
            return []

    query_lower = query.lower().strip()
    if not query_lower:
        return []

    matches: list[str] = []
    for station_name in manager.all_stations.keys():
        station_name_lower = station_name.lower()

        if query_lower in station_name_lower:
            lines = manager.get_railway_lines_for_station(station_name)
            if len(lines) > 1:
                primary_line = lines[0]
                matches.append(f"{station_name} ({primary_line})")
            else:
                matches.append(station_name)

    def relevance_score(station: str) -> tuple[int, str]:
        name_lower = station.lower()
        if " (" in name_lower:
            name_lower = name_lower.split(" (", 1)[0]

        if name_lower == query_lower:
            return (0, station.lower())
        if name_lower.startswith(query_lower):
            return (1, station.lower())
        return (2, station.lower())

    matches.sort(key=relevance_score)
    return matches[:limit]


def parse_station_name(*, station_name: str) -> str:
    """Parse station name to remove disambiguation context."""

    if not station_name:
        return ""

    # Remove line context in parentheses - but NOT station name parentheses like (Main)
    if " (" in station_name:
        paren_content = (
            station_name.split(" (", 1)[1].split(")", 1)[0]
            if ")" in station_name
            else ""
        )
        line_indicators = [
            "Line",
            "Railway",
            "Network",
            "Express",
            "Main Line",
            "Coast",
        ]
        if any(indicator in paren_content for indicator in line_indicators):
            return station_name.split(" (", 1)[0].strip()

    return station_name.strip()


def get_all_stations_with_context(*, manager) -> list[str]:
    """Get all stations with disambiguation context where needed."""

    if not manager.loaded:
        if not manager.load_database():
            return []

    stations_with_context: list[str] = []
    for station_name in manager.all_stations.keys():
        lines = manager.get_railway_lines_for_station(station_name)
        if len(lines) > 1:
            primary_line = lines[0]
            stations_with_context.append(f"{station_name} ({primary_line})")
        else:
            stations_with_context.append(station_name)

    return sorted(stations_with_context)


def suggest_via_stations(
    *, manager, from_station: str, to_station: str, limit: int = 10
) -> list[str]:
    """Suggest via stations for a route."""

    if not manager.loaded:
        if not manager.load_database():
            return []

    from_parsed = manager.parse_station_name(from_station)
    to_parsed = manager.parse_station_name(to_station)

    routes = manager.dijkstra_shortest_path_with_service_patterns(
        from_parsed,
        to_parsed,
        max_routes=3,
        max_changes=2,
    )

    via_stations: set[str] = set()
    for route_names, _ in routes:
        if len(route_names) > 2:
            for station_name in route_names[1:-1]:
                via_stations.add(station_name)

    return sorted(via_stations)[:limit]


def find_route_between_stations(
    *,
    manager,
    from_station: str,
    to_station: str,
    max_changes: int = 3,
    departure_time: str | None = None,
) -> list[list[str]]:
    """Find routes between stations (UI compatibility method)."""

    return manager.find_route_between_stations_with_service_patterns(
        from_station,
        to_station,
        max_changes,
        departure_time,
    )


def identify_train_changes(*, manager, route: list[str]) -> list[str]:
    """Identify stations where train changes are required."""

    if not manager.loaded or len(route) < 3:
        return []

    train_changes: list[str] = []
    current_line: str | None = None

    for i in range(len(route) - 1):
        current_station = route[i]
        next_station = route[i + 1]

        current_parsed = manager.parse_station_name(current_station)
        next_parsed = manager.parse_station_name(next_station)

        current_lines = set(manager.get_railway_lines_for_station(current_parsed))
        next_lines = set(manager.get_railway_lines_for_station(next_parsed))
        common_lines = current_lines.intersection(next_lines)

        if not common_lines:
            if i > 0:
                train_changes.append(current_station)
            continue

        if current_line and current_line not in common_lines and i > 0:
            train_changes.append(current_station)

        current_line = list(common_lines)[0]

    return train_changes


def get_operator_for_segment(
    *, manager, from_station: str, to_station: str
) -> str | None:
    """Get operator for a segment between two stations."""

    if not manager.loaded:
        if not manager.load_database():
            return None

    from_parsed = manager.parse_station_name(from_station)
    to_parsed = manager.parse_station_name(to_station)

    from_lines = set(manager.get_railway_lines_for_station(from_parsed))
    to_lines = set(manager.get_railway_lines_for_station(to_parsed))
    common_lines = from_lines.intersection(to_lines)

    if not common_lines:
        return None

    line_name = list(common_lines)[0]
    railway_line = manager.railway_lines.get(line_name)
    if railway_line:
        return railway_line.operator

    return None


def get_database_stats(*, manager) -> dict[str, int]:
    """Get database statistics."""

    if not manager.loaded:
        if not manager.load_database():
            return {}

    return {
        "total_stations": len(manager.all_stations),
        "total_lines": len(manager.railway_lines),
        "lines_with_service_patterns": sum(
            1 for line in manager.railway_lines.values() if line.service_patterns
        ),
    }

