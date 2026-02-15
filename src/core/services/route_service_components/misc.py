"""Miscellaneous route utilities used by the route service."""

from __future__ import annotations

from typing import List, Tuple

from ...models.route import Route


def validate_route(*, data_repository, route: Route) -> Tuple[bool, List[str]]:
    """Validate that a route is feasible and consistent."""

    errors: list[str] = []

    if not data_repository.validate_station_exists(route.from_station):
        errors.append(f"From station does not exist: {route.from_station}")

    if not data_repository.validate_station_exists(route.to_station):
        errors.append(f"To station does not exist: {route.to_station}")

    for i, segment in enumerate(route.segments):
        if segment.service_pattern == "UNDERGROUND":
            continue

        if not data_repository.validate_line_exists(segment.line_name):
            errors.append(f"Segment {i}: Line does not exist: {segment.line_name}")
            continue

        line = data_repository.get_railway_line_by_name(segment.line_name)
        if line:
            if segment.from_station not in line.stations:
                errors.append(
                    f"Segment {i}: Station {segment.from_station} not on line {segment.line_name}"
                )
            if segment.to_station not in line.stations:
                errors.append(
                    f"Segment {i}: Station {segment.to_station} not on line {segment.line_name}"
                )

    for i in range(len(route.segments) - 1):
        current_segment = route.segments[i]
        next_segment = route.segments[i + 1]
        if current_segment.to_station != next_segment.from_station:
            errors.append(
                f"Segments {i} and {i+1}: Not continuous - {current_segment.to_station} != {next_segment.from_station}"
            )

    return (len(errors) == 0), errors


def calculate_route_cost(*, route: Route) -> float | None:
    """Return a simple estimated cost, or None if distance is unknown."""

    if route.total_distance_km is None:
        return None

    base_cost = route.total_distance_km * 0.20
    change_cost = route.changes_required * 2.0
    return base_cost + change_cost


def get_interchange_stations(*, data_repository, from_station: str, to_station: str) -> List[str]:
    """Return interchanges that connect the origin/destination networks."""

    from_lines = data_repository.get_lines_serving_station(from_station)
    to_lines = data_repository.get_lines_serving_station(to_station)
    all_interchanges = data_repository.get_interchange_stations()

    interchanges: list[str] = []
    for interchange in all_interchanges:
        interchange_lines = data_repository.get_lines_serving_station(interchange.name)
        connects_from = any(line in from_lines for line in interchange_lines)
        connects_to = any(line in to_lines for line in interchange_lines)
        if connects_from and connects_to and interchange.name not in (from_station, to_station):
            interchanges.append(interchange.name)

    return interchanges


def routes_similar(*, route1: Route, route2: Route, threshold: float = 0.8) -> bool:
    """Return True if routes share a high Jaccard similarity of intermediate stations."""

    stations1 = set(route1.intermediate_stations)
    stations2 = set(route2.intermediate_stations)

    if not stations1 and not stations2:
        return True
    if not stations1 or not stations2:
        return False

    intersection = len(stations1.intersection(stations2))
    union = len(stations1.union(stations2))
    similarity = intersection / union if union > 0 else 0
    return similarity >= threshold

