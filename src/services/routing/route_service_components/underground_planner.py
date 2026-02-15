"""Underground-specific route planning helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from src.core.models.route import Route, RouteSegment


@dataclass(frozen=True)
class UndergroundRoutePlanner:
    """Builds hybrid National Rail + Underground routes."""

    network_builder: Any
    pathfinder: Any
    route_converter: Any
    underground_handler: Any
    logger: Any

    def calculate_terminus_to_underground_route(
        self,
        *,
        from_station: str,
        to_station: str,
        preferences: Optional[Dict[str, Any]] = None,
    ) -> Optional[Route]:
        self.logger.info(
            "Calculating terminus-to-underground route: %s → %s", from_station, to_station
        )

        system_info = self.underground_handler.get_underground_system(to_station)
        if not system_info:
            self.logger.warning("Destination %s is not an underground station", to_station)
            return None

        system_key, system_name = system_info
        best_terminus = self.get_best_terminus_for_underground_system(
            from_station=from_station, system_key=system_key
        )
        if not best_terminus:
            self.logger.warning(
                "No suitable terminus found for %s → %s (%s)",
                from_station,
                to_station,
                system_name,
            )
            return None

        if from_station == best_terminus:
            return self.create_underground_only_route(
                from_station=from_station,
                to_station=to_station,
                system_key=system_key,
                system_name=system_name,
            )

        graph = self.network_builder.build_network_graph()
        path_node = self.pathfinder.dijkstra_shortest_path(
            from_station, best_terminus, graph, "time", preferences
        )
        if not path_node:
            self.logger.warning(
                "No route found from %s to terminus %s", from_station, best_terminus
            )
            return None

        try:
            mainline_route = self.route_converter.path_to_route(path_node, graph)
            underground_segment = RouteSegment(
                from_station=best_terminus,
                to_station=to_station,
                line_name=system_name,
                distance_km=self.underground_handler._estimate_underground_distance(
                    best_terminus, to_station, system_key
                ),
                journey_time_minutes=self.underground_handler._estimate_underground_time(
                    best_terminus, to_station, system_key
                ),
                service_pattern="UNDERGROUND",
                train_service_id=f"{system_key.upper()}_UNDERGROUND_SERVICE",
            )

            all_segments = mainline_route.segments + [underground_segment]
            total_time = (mainline_route.total_journey_time_minutes or 0) + (
                underground_segment.journey_time_minutes or 0
            )
            total_distance = (mainline_route.total_distance_km or 0) + (
                underground_segment.distance_km or 0
            )

            full_path = mainline_route.full_path[:-1] if mainline_route.full_path else [from_station]
            full_path.extend([best_terminus, to_station])

            combined_route = Route(
                from_station=from_station,
                to_station=to_station,
                segments=all_segments,
                total_distance_km=total_distance,
                total_journey_time_minutes=total_time,
                changes_required=mainline_route.changes_required + 1,
                full_path=full_path,
            )

            self.logger.info(
                "Created terminus-to-underground route: %s → %s → %s (%s)",
                from_station,
                best_terminus,
                to_station,
                system_name,
            )
            return combined_route
        except Exception as exc:  # pragma: no cover - defensive logging
            self.logger.error("Failed to create terminus-to-underground route: %s", exc)
            return None

    def calculate_underground_to_terminus_route(
        self,
        *,
        from_station: str,
        to_station: str,
        preferences: Optional[Dict[str, Any]] = None,
    ) -> Optional[Route]:
        self.logger.info(
            "Calculating underground-to-terminus route: %s → %s", from_station, to_station
        )

        system_info = self.underground_handler.get_underground_system(from_station)
        if not system_info:
            self.logger.warning("Origin %s is not an underground station", from_station)
            return None

        system_key, system_name = system_info
        best_terminus = self.get_best_terminus_for_underground_system(
            from_station=to_station, system_key=system_key
        )
        if not best_terminus:
            self.logger.warning(
                "No suitable terminus found for %s → %s (%s)",
                from_station,
                to_station,
                system_name,
            )
            return None

        if to_station == best_terminus:
            return self.create_underground_only_route(
                from_station=from_station,
                to_station=to_station,
                system_key=system_key,
                system_name=system_name,
            )

        graph = self.network_builder.build_network_graph()
        path_node = self.pathfinder.dijkstra_shortest_path(
            best_terminus, to_station, graph, "time", preferences
        )
        if not path_node:
            self.logger.warning(
                "No route found from terminus %s to %s", best_terminus, to_station
            )
            return None

        try:
            mainline_route = self.route_converter.path_to_route(path_node, graph)
            underground_segment = RouteSegment(
                from_station=from_station,
                to_station=best_terminus,
                line_name=system_name,
                distance_km=self.underground_handler._estimate_underground_distance(
                    from_station, best_terminus, system_key
                ),
                journey_time_minutes=self.underground_handler._estimate_underground_time(
                    from_station, best_terminus, system_key
                ),
                service_pattern="UNDERGROUND",
                train_service_id=f"{system_key.upper()}_UNDERGROUND_SERVICE",
            )

            all_segments = [underground_segment] + mainline_route.segments
            total_time = (underground_segment.journey_time_minutes or 0) + (
                mainline_route.total_journey_time_minutes or 0
            )
            total_distance = (underground_segment.distance_km or 0) + (
                mainline_route.total_distance_km or 0
            )

            full_path = [from_station, best_terminus]
            if mainline_route.full_path and len(mainline_route.full_path) > 1:
                full_path.extend(mainline_route.full_path[1:])
            else:
                full_path.append(to_station)

            combined_route = Route(
                from_station=from_station,
                to_station=to_station,
                segments=all_segments,
                total_distance_km=total_distance,
                total_journey_time_minutes=total_time,
                changes_required=1 + mainline_route.changes_required,
                full_path=full_path,
            )

            self.logger.info(
                "Created underground-to-terminus route: %s → %s → %s (%s)",
                from_station,
                best_terminus,
                to_station,
                system_name,
            )
            return combined_route
        except Exception as exc:  # pragma: no cover
            self.logger.error("Failed to create underground-to-terminus route: %s", exc)
            return None

    def get_best_terminus_for_underground_system(
        self, *, from_station: str, system_key: str
    ) -> Optional[str]:
        if system_key == "london":
            return self.get_best_london_terminus_for_route(
                from_station=from_station, to_station=""
            )
        if system_key == "glasgow":
            return "Glasgow Central"
        if system_key == "tyne_wear":
            return "Newcastle"
        return "London Waterloo"

    def get_best_london_terminus_for_route(
        self, *, from_station: str, to_station: str
    ) -> Optional[str]:
        southwest_stations = [
            "Farnborough",
            "Basingstoke",
            "Southampton",
            "Woking",
            "Guildford",
            "Winchester",
        ]
        western_stations = ["Reading", "Swindon", "Bristol", "Oxford", "Bath"]
        eastern_stations = ["Colchester", "Chelmsford", "Ipswich", "Norwich", "Cambridge"]
        northern_stations = ["Birmingham", "Manchester", "Leeds", "York", "Newcastle"]

        from_lower = from_station.lower()

        if any(station.lower() in from_lower for station in southwest_stations):
            return "London Waterloo"
        if any(station.lower() in from_lower for station in western_stations):
            return "London Paddington"
        if any(station.lower() in from_lower for station in eastern_stations):
            return "London Liverpool Street"
        if any(station.lower() in from_lower for station in northern_stations):
            return "London Euston"
        return "London Waterloo"

    def create_underground_only_route(
        self,
        *,
        from_station: str,
        to_station: str,
        system_key: str = "london",
        system_name: str = "London Underground",
    ) -> Route:
        underground_segment = RouteSegment(
            from_station=from_station,
            to_station=to_station,
            line_name=system_name,
            distance_km=self.underground_handler._estimate_underground_distance(
                from_station, to_station, system_key
            ),
            journey_time_minutes=self.underground_handler._estimate_underground_time(
                from_station, to_station, system_key
            ),
            service_pattern="UNDERGROUND",
            train_service_id=f"{system_key.upper()}_UNDERGROUND_SERVICE",
        )

        return Route(
            from_station=from_station,
            to_station=to_station,
            segments=[underground_segment],
            total_distance_km=underground_segment.distance_km,
            total_journey_time_minutes=underground_segment.journey_time_minutes,
            changes_required=0,
            full_path=[from_station, to_station],
        )

