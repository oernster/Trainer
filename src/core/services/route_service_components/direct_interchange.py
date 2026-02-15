"""Direct and single-interchange route construction."""

from __future__ import annotations

from typing import List

from ...models.route import Route


def find_direct_routes(*, data_repository, route_converter, from_station: str, to_station: str) -> List[Route]:
    """Find all direct routes (no changes) between two stations."""

    common_lines = data_repository.get_common_lines(from_station, to_station)
    direct_routes: list[Route] = []

    for line in common_lines:
        line_stations = line.stations
        try:
            from_idx = line_stations.index(from_station)
            to_idx = line_stations.index(to_station)
        except ValueError:
            continue

        if from_idx == to_idx:
            continue

        journey_time = line.get_journey_time(from_station, to_station) or 0
        distance = line.get_distance(from_station, to_station) or 0.0
        direct_routes.append(
            route_converter.create_direct_route(
                from_station, to_station, line.name, journey_time, distance
            )
        )

    return direct_routes


def find_interchange_routes(
    *, data_repository, route_converter, from_station: str, to_station: str
) -> List[Route]:
    """Find routes with exactly one interchange between two stations."""

    interchange_routes: list[Route] = []
    interchange_stations = data_repository.get_interchange_stations()

    for interchange in interchange_stations:
        if interchange.name in (from_station, to_station):
            continue

        first_leg = find_direct_routes(
            data_repository=data_repository,
            route_converter=route_converter,
            from_station=from_station,
            to_station=interchange.name,
        )
        second_leg = find_direct_routes(
            data_repository=data_repository,
            route_converter=route_converter,
            from_station=interchange.name,
            to_station=to_station,
        )

        for leg1 in first_leg:
            for leg2 in second_leg:
                leg1_lines = {seg.line_name for seg in leg1.segments}
                leg2_lines = {seg.line_name for seg in leg2.segments}
                if leg1_lines.intersection(leg2_lines):
                    continue

                interchange_routes.append(
                    route_converter.create_interchange_route(
                        from_station, to_station, leg1, leg2, interchange.name
                    )
                )

    interchange_routes.sort(key=lambda r: r.total_journey_time_minutes or 999)
    return interchange_routes

