"""Graph-based queries used by the route service."""

from __future__ import annotations

from collections import deque
from typing import Any, Dict, List

from ...models.route import Route


def get_possible_destinations(*, network_builder, from_station: str, max_changes: int = 3) -> List[str]:
    """Return reachable destinations within a max line-change budget."""

    graph = network_builder.build_network_graph()
    if from_station not in graph:
        return []

    destinations: set[str] = set()
    queue = deque([(from_station, 0, set())])  # (station, changes, lines_used)
    visited: set[tuple[str, int]] = set()

    while queue:
        current_station, changes, lines_used = queue.popleft()
        if (current_station, changes) in visited:
            continue

        visited.add((current_station, changes))
        if current_station != from_station:
            destinations.add(current_station)

        if changes >= max_changes:
            continue

        for next_station, connections in graph[current_station].items():
            for connection in connections:
                line = connection["line"]
                new_changes = changes + (1 if lines_used and line not in lines_used else 0)
                if new_changes <= max_changes:
                    queue.append((next_station, new_changes, lines_used | {line}))

    return sorted(destinations)


def find_circular_routes(
    *,
    network_builder,
    route_converter,
    station: str,
    max_distance: float = 50.0,
    logger,
) -> List[Route]:
    """Find a small set of circular routes starting and ending at ``station``."""

    circular_routes: list[Route] = []
    graph = network_builder.build_network_graph()
    if station not in graph:
        return circular_routes

    queue = deque([(station, 0.0, [station], [])])  # (current, distance, path, lines)

    while queue:
        current, distance, path, lines = queue.popleft()
        if distance > max_distance:
            continue

        if len(path) > 1 and current == station:
            try:
                circular_routes.append(
                    route_converter.create_circular_route(station, path, lines, distance)
                )
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.error("Failed to create circular route: %s", exc)
            continue

        for next_station, connections in graph[current].items():
            if len(path) > 1 and next_station in path[:-1]:
                continue
            for connection in connections:
                queue.append(
                    (
                        next_station,
                        distance + connection["distance"],
                        path + [next_station],
                        lines + [connection["line"]],
                    )
                )

    return circular_routes[:5]


def get_route_statistics(
    *, network_builder, data_repository, underground_handler
) -> Dict[str, Any]:
    """Return basic network statistics."""

    graph = network_builder.build_network_graph()
    total_stations = len(graph)
    total_connections = sum(len(neighbors) for neighbors in graph.values())

    lines = data_repository.load_railway_lines()
    underground_stats = underground_handler.get_underground_statistics()

    return {
        "total_stations": total_stations,
        "total_connections": total_connections // 2,
        "total_lines": len(lines),
        "average_connections_per_station": (
            total_connections / total_stations if total_stations > 0 else 0
        ),
        "underground_stats": underground_stats,
    }

