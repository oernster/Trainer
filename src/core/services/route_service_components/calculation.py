"""Core calculation logic for :class:`RouteServiceRefactored`.

The service itself stays as a thin orchestrator.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ...models.route import Route

from .cache import build_route_cache_key
from .misc import routes_similar


def calculate_route(
    *,
    route_service: Any,
    from_station: str,
    to_station: str,
    max_changes: Optional[int] = None,
    preferences: Optional[Dict[str, Any]] = None,
) -> Optional[Route]:
    """Calculate the best route between two stations."""

    normalized_from = route_service.station_normalizer.normalize_station_name(from_station)
    normalized_to = route_service.station_normalizer.normalize_station_name(to_station)

    if from_station == to_station:
        return None

    cache_key = build_route_cache_key(
        from_station=normalized_from,
        to_station=normalized_to,
        preferences=preferences,
    )

    if cache_key in route_service._route_cache:
        routes = route_service._route_cache[cache_key]
        if routes:
            route_service.logger.debug(
                "Using cached route for %s → %s with preferences",
                normalized_from,
                normalized_to,
            )
            return routes[0]

    cross_country_route = route_service.underground_handler.create_cross_country_route(
        from_station, to_station
    )
    if cross_country_route:
        route_service._route_cache[cache_key] = [cross_country_route]
        return cross_country_route

    if route_service.underground_handler.should_use_black_box_routing(from_station, to_station):
        if route_service.underground_handler.is_underground_station(
            from_station
        ) and route_service.underground_handler.is_underground_station(to_station):
            black_box_route = route_service.underground_handler.create_black_box_route(
                from_station, to_station
            )
            if black_box_route:
                route_service._route_cache[cache_key] = [black_box_route]
                return black_box_route

    from_system = route_service.underground_handler.get_underground_system(from_station)
    to_system = route_service.underground_handler.get_underground_system(to_station)
    if from_system and to_system and from_system[0] != to_system[0]:
        multi_system_route = route_service.underground_handler.create_multi_system_route(
            from_station, to_station
        )
        if multi_system_route:
            route_service._route_cache[cache_key] = [multi_system_route]
            return multi_system_route

    if route_service.underground_handler.should_use_black_box_routing(from_station, to_station):
        if (
            not route_service.underground_handler.is_underground_station(from_station)
            and route_service.underground_handler.is_underground_station(to_station)
        ):
            return route_service._calculate_terminus_to_underground_route(
                normalized_from, to_station, preferences
            )

        if (
            route_service.underground_handler.is_underground_station(from_station)
            and not route_service.underground_handler.is_underground_station(to_station)
        ):
            return route_service._calculate_underground_to_terminus_route(
                from_station, normalized_to, preferences
            )

    if not route_service.data_repository.validate_station_exists(normalized_from):
        route_service.logger.warning("From station does not exist: %s", from_station)
        return None
    if not route_service.data_repository.validate_station_exists(normalized_to):
        route_service.logger.warning("To station does not exist: %s", to_station)
        return None

    graph = route_service.network_builder.build_network_graph()
    route_service.logger.info(
        "Attempting to find route from '%s' to '%s' with preferences: %s",
        normalized_from,
        normalized_to,
        preferences,
    )

    path_node = route_service.pathfinder.dijkstra_shortest_path(
        normalized_from, normalized_to, graph, "time", preferences
    )
    if path_node is None:
        route_service.logger.warning(
            "No route found from '%s' to '%s'", normalized_from, normalized_to
        )
        route_service.logger.info(
            "Original station names: '%s' to '%s'", from_station, to_station
        )
        if normalized_from not in graph:
            route_service.logger.warning(
                "Station '%s' not found in network graph", normalized_from
            )
        if normalized_to not in graph:
            route_service.logger.warning(
                "Station '%s' not found in network graph", normalized_to
            )
        return None

    if max_changes is not None and path_node.changes > max_changes:
        route_service.logger.warning(
            "Route requires %s changes, max allowed: %s",
            path_node.changes,
            max_changes,
        )
        return None

    try:
        route = route_service.route_converter.path_to_route(path_node, graph)
        route_service._route_cache[cache_key] = [route]
        route_service.logger.debug(
            "Cached route for %s → %s with preferences",
            normalized_from,
            normalized_to,
        )
        return route
    except Exception as exc:  # pragma: no cover - defensive logging
        route_service.logger.error("Failed to convert path to route: %s", exc)
        return None


def calculate_multiple_routes(
    *,
    route_service: Any,
    from_station: str,
    to_station: str,
    max_routes: int = 5,
    max_changes: Optional[int] = None,
    preferences: Optional[Dict[str, Any]] = None,
) -> List[Route]:
    """Calculate multiple alternative routes between two stations."""

    normalized_from = route_service.station_normalizer.normalize_station_name(from_station)
    normalized_to = route_service.station_normalizer.normalize_station_name(to_station)

    routes: list[Route] = []
    cache_key = build_route_cache_key(
        from_station=normalized_from,
        to_station=normalized_to,
        preferences=preferences,
    )

    if cache_key in route_service._route_cache and len(route_service._route_cache[cache_key]) >= max_routes:
        route_service.logger.debug(
            "Using cached multiple routes for %s → %s with preferences",
            normalized_from,
            normalized_to,
        )
        return route_service._route_cache[cache_key][:max_routes]

    cross_country_route = route_service.underground_handler.create_cross_country_route(
        from_station, to_station
    )
    if cross_country_route:
        routes.append(cross_country_route)
        route_service._route_cache[cache_key] = routes
        return routes

    from_system = route_service.underground_handler.get_underground_system(from_station)
    to_system = route_service.underground_handler.get_underground_system(to_station)
    if from_system and to_system and from_system[0] != to_system[0]:
        multi_system_route = route_service.underground_handler.create_multi_system_route(
            from_station, to_station
        )
        if multi_system_route:
            routes.append(multi_system_route)
            route_service._route_cache[cache_key] = routes
            return routes

    if route_service.underground_handler.should_use_black_box_routing(from_station, to_station):
        if route_service.underground_handler.is_underground_station(
            from_station
        ) and route_service.underground_handler.is_underground_station(to_station):
            black_box_route = route_service.underground_handler.create_black_box_route(
                from_station, to_station
            )
            if black_box_route:
                routes.append(black_box_route)
                route_service._route_cache[cache_key] = routes
                return routes

        if (
            not route_service.underground_handler.is_underground_station(from_station)
            and route_service.underground_handler.is_underground_station(to_station)
        ):
            terminus_route = route_service._calculate_terminus_to_underground_route(
                normalized_from, to_station, preferences
            )
            if terminus_route:
                routes.append(terminus_route)
                route_service._route_cache[cache_key] = routes
                return routes

        if (
            route_service.underground_handler.is_underground_station(from_station)
            and not route_service.underground_handler.is_underground_station(to_station)
        ):
            underground_route = route_service._calculate_underground_to_terminus_route(
                from_station, normalized_to, preferences
            )
            if underground_route:
                routes.append(underground_route)
                route_service._route_cache[cache_key] = routes
                return routes

    graph = route_service.network_builder.build_network_graph()
    strategies = ["time", "changes", "distance"]

    for strategy in strategies:
        if len(routes) >= max_routes:
            break

        path_node = route_service.pathfinder.dijkstra_shortest_path(
            normalized_from, normalized_to, graph, strategy, preferences
        )
        if not path_node:
            continue

        if max_changes is not None and path_node.changes > max_changes:
            continue

        try:
            route = route_service.route_converter.path_to_route(path_node, graph)
            enhanced_route = route_service.underground_handler.enhance_route_with_black_box(route)

            if all(
                not routes_similar(route1=enhanced_route, route2=existing)
                for existing in routes
            ):
                routes.append(enhanced_route)
        except Exception as exc:  # pragma: no cover
            route_service.logger.error(
                "Failed to create route with strategy %s: %s", strategy, exc
            )

    routes.sort(
        key=lambda r: (
            r.total_journey_time_minutes or 999,
            r.changes_required,
            r.total_distance_km or 999,
        )
    )
    route_service._route_cache[cache_key] = routes
    route_service.logger.debug(
        "Cached %s routes for %s → %s with preferences",
        len(routes),
        normalized_from,
        normalized_to,
    )
    return routes[:max_routes]

