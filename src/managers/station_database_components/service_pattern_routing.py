"""Service-pattern-aware routing helpers.

Extracted from :class:`StationDatabaseManager` to keep that module under the LOC gate.
"""

from __future__ import annotations

import heapq
from typing import Optional


def build_service_aware_network(*, manager) -> dict:
    """Build network considering service patterns."""

    if not manager.loaded:
        if not manager.load_database():
            return {}

    network: dict = {}

    for station_name, station in manager.all_stations.items():
        network[station_name] = {
            "station": station,
            "coordinates": station.coordinates,
            "connections": [],
            "interchange_lines": station.interchange or [],
            "is_major_interchange": len(station.interchange or []) >= 2,
            "lines": manager.get_railway_lines_for_station(station_name),
        }

    for line_name, railway_line in manager.railway_lines.items():
        if not railway_line.service_patterns:
            manager._add_legacy_connections(network, railway_line, line_name)
            continue

        for pattern_code, pattern in railway_line.service_patterns.patterns.items():
            pattern_stations = manager.get_stations_for_service_pattern(line_name, pattern_code)
            for i in range(len(pattern_stations) - 1):
                current_name = pattern_stations[i]
                next_name = pattern_stations[i + 1]

                current_station = manager.get_station_by_name(current_name)
                next_station = manager.get_station_by_name(next_name)
                if not (current_station and next_station):
                    continue

                distance = manager.calculate_haversine_distance(
                    current_station.coordinates, next_station.coordinates
                )

                journey_time = manager.get_journey_time_between_stations(
                    current_name, next_name
                )
                if not journey_time:
                    speed_multiplier = {
                        manager.ServiceType.EXPRESS: 0.8,
                        manager.ServiceType.FAST: 1.0,
                        manager.ServiceType.SEMI_FAST: 1.3,
                        manager.ServiceType.STOPPING: 1.5,
                        manager.ServiceType.PEAK: 1.0,
                        manager.ServiceType.OFF_PEAK: 1.1,
                        manager.ServiceType.NIGHT: 1.4,
                    }.get(pattern.service_type, 1.2)
                    journey_time = max(2, int(distance * 1.5 * speed_multiplier))

                network[current_name]["connections"].append(
                    (
                        next_name,
                        distance,
                        journey_time,
                        line_name,
                        pattern_code,
                        pattern.service_type.priority,
                    )
                )
                network[next_name]["connections"].append(
                    (
                        current_name,
                        distance,
                        journey_time,
                        line_name,
                        pattern_code,
                        pattern.service_type.priority,
                    )
                )

    manager.logger.debug("Built service-aware network with %s stations", len(network))
    return network


def dijkstra_shortest_path_with_service_patterns(
    *,
    manager,
    start_name: str,
    end_name: str,
    max_routes: int = 5,
    max_changes: int = 3,
    departure_time: Optional[str] = None,
) -> list:
    """Enhanced Dijkstra with service pattern awareness."""

    import time

    start_time = time.time()
    timeout = 10.0

    network = build_service_aware_network(manager=manager)
    if start_name not in network or end_name not in network:
        return []

    start_lines = set(network[start_name]["lines"])
    end_lines = set(network[end_name]["lines"])
    common_lines = start_lines.intersection(end_lines)
    if common_lines:
        direct_route = manager._find_direct_route_on_line(
            start_name, end_name, list(common_lines)[0]
        )
        if direct_route:
            return [(direct_route, 1.0)]

    pq = [(0.0, start_name, [start_name], 0, None, None)]
    visited = {}
    routes = []
    iterations = 0
    max_iterations = 10000

    while pq and len(routes) < max_routes and iterations < max_iterations:
        iterations += 1
        if time.time() - start_time > timeout:
            manager.logger.warning("Route finding timed out after %s seconds", timeout)
            break

        current_cost, current_station, path, num_changes, current_line, current_pattern = heapq.heappop(
            pq
        )

        state_key = (current_station, num_changes, current_pattern)
        if state_key in visited and visited[state_key] <= current_cost:
            continue
        visited[state_key] = current_cost

        if current_station == end_name:
            routes.append((path, current_cost))
            continue

        if num_changes >= max_changes:
            continue
        if len(path) > 20:
            continue

        for next_station, distance, journey_time, line_name, pattern_code, priority in network[
            current_station
        ]["connections"]:
            if next_station in path:
                continue

            base_cost = journey_time + (distance * 0.1)
            pattern_bonus = (4 - priority) * 2
            connection_cost = base_cost - pattern_bonus

            if current_line and current_line != line_name:
                connection_cost += 15

            new_cost = current_cost + connection_cost
            new_path = path + [next_station]
            new_changes = num_changes + (
                1 if current_line and current_line != line_name else 0
            )

            heapq.heappush(
                pq,
                (new_cost, next_station, new_path, new_changes, line_name, pattern_code),
            )

    if iterations >= max_iterations:
        manager.logger.warning(
            "Route finding stopped after %s iterations", max_iterations
        )

    return routes

