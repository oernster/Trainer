"""Caching helpers for the route service."""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple


def build_route_cache_key(
    *,
    from_station: str,
    to_station: str,
    preferences: Optional[Dict[str, Any]] = None,
) -> Tuple[str, str, object]:
    """Create a cache key that includes relevant routing preferences."""

    pref_key = None
    if preferences:
        routing_prefs = {
            "avoid_walking": preferences.get("avoid_walking", False),
            "prefer_direct": preferences.get("prefer_direct", False),
            "avoid_london": preferences.get("avoid_london", False),
            "max_walking_distance_km": preferences.get("max_walking_distance_km", 0.1),
        }
        if any(routing_prefs.values()):
            pref_key = frozenset(routing_prefs.items())

    return (from_station, to_station, pref_key)


def precompute_common_routes(*, route_service, station_pairs: list[tuple[str, str]]) -> None:
    """Warm the route cache by calculating routes for known station pairs."""

    route_service.logger.info(
        "Precomputing routes for %s station pairs...", len(station_pairs)
    )
    for from_station, to_station in station_pairs:
        try:
            route = route_service.calculate_route(from_station, to_station)
            if route:
                route_service.logger.debug(
                    "Precomputed route: %s -> %s", from_station, to_station
                )
        except Exception as exc:  # pragma: no cover - defensive logging
            route_service.logger.error(
                "Failed to precompute route %s -> %s: %s", from_station, to_station, exc
            )

    route_service.logger.info(
        "Precomputation complete. Cache size: %s", len(route_service._route_cache)
    )

