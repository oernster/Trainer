"""
Refactored Route Service Implementation

Service implementation for route calculation and pathfinding using modular components.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from src.core.interfaces.i_route_service import IRouteService
from src.core.interfaces.i_data_repository import IDataRepository
from src.core.models.route import Route
from .network_graph_builder import NetworkGraphBuilder
from .pathfinding_algorithm import PathfindingAlgorithm
from .route_converter import RouteConverter
from .station_name_normalizer import StationNameNormalizer
from .underground_routing_handler import UndergroundRoutingHandler
from .route_service_components.direct_interchange import (
    find_direct_routes as _find_direct_routes,
    find_interchange_routes as _find_interchange_routes,
)
from .route_service_components.graph_queries import (
    find_circular_routes as _find_circular_routes,
    get_possible_destinations as _get_possible_destinations,
    get_route_statistics as _get_route_statistics,
)
from .route_service_components.cache import (
    build_route_cache_key as _build_route_cache_key,
    precompute_common_routes as _precompute_common_routes,
)
from .route_service_components.calculation import (
    calculate_multiple_routes as _calculate_multiple_routes,
    calculate_route as _calculate_route,
)
from .route_service_components.misc import (
    calculate_route_cost as _calculate_route_cost,
    get_interchange_stations as _get_interchange_stations,
    routes_similar as _routes_similar,
    validate_route as _validate_route,
)
from .route_service_components.underground_planner import UndergroundRoutePlanner


class RouteServiceRefactored(IRouteService):
    """Refactored service implementation for route calculation and pathfinding."""
    
    def __init__(self, data_repository: IDataRepository):
        """
        Initialize the route service with modular components.
        
        Args:
            data_repository: Data repository for accessing railway data
        """
        self.data_repository = data_repository
        self.logger = logging.getLogger(__name__)
        
        # Initialize modular components
        self.network_builder = NetworkGraphBuilder(data_repository)
        self.pathfinder = PathfindingAlgorithm(data_repository)
        self.route_converter = RouteConverter(data_repository)
        self.station_normalizer = StationNameNormalizer(data_repository)
        self.underground_handler = UndergroundRoutingHandler(data_repository)

        self._underground_planner = UndergroundRoutePlanner(
            network_builder=self.network_builder,
            pathfinder=self.pathfinder,
            route_converter=self.route_converter,
            underground_handler=self.underground_handler,
            logger=self.logger,
        )
        
        # Cache for route calculations
        # Cache key is (from_station, to_station, preferences_key)
        self._route_cache: Dict[Tuple, List[Route]] = {}
        
        self.logger.info("Initialized RefactoredRouteService with modular components")
    
    def calculate_route(self, from_station: str, to_station: str,
                       max_changes: Optional[int] = None,
                       preferences: Optional[Dict[str, Any]] = None) -> Optional[Route]:
        return _calculate_route(
            route_service=self,
            from_station=from_station,
            to_station=to_station,
            max_changes=max_changes,
            preferences=preferences,
        )
    
    def calculate_multiple_routes(self, from_station: str, to_station: str,
                                max_routes: int = 5, max_changes: Optional[int] = None,
                                preferences: Optional[Dict[str, Any]] = None) -> List[Route]:
        return _calculate_multiple_routes(
            route_service=self,
            from_station=from_station,
            to_station=to_station,
            max_routes=max_routes,
            max_changes=max_changes,
            preferences=preferences,
        )
    
    def find_direct_routes(self, from_station: str, to_station: str) -> List[Route]:
        return _find_direct_routes(
            data_repository=self.data_repository,
            route_converter=self.route_converter,
            from_station=from_station,
            to_station=to_station,
        )
    
    def find_interchange_routes(self, from_station: str, to_station: str) -> List[Route]:
        return _find_interchange_routes(
            data_repository=self.data_repository,
            route_converter=self.route_converter,
            from_station=from_station,
            to_station=to_station,
        )
    
    def get_fastest_route(self, from_station: str, to_station: str,
                         preferences: Optional[Dict[str, Any]] = None) -> Optional[Route]:
        """Get the fastest route between two stations."""
        graph = self.network_builder.build_network_graph()
        path_node = self.pathfinder.dijkstra_shortest_path(from_station, to_station, graph, 'time', preferences)
        
        if path_node:
            try:
                route = self.route_converter.path_to_route(path_node, graph)
                return self.underground_handler.enhance_route_with_black_box(route)
            except Exception as e:
                self.logger.error("Failed to create fastest route: %s", e)
        
        return None
    
    def get_shortest_route(self, from_station: str, to_station: str,
                          preferences: Optional[Dict[str, Any]] = None) -> Optional[Route]:
        """Get the shortest distance route between two stations."""
        graph = self.network_builder.build_network_graph()
        path_node = self.pathfinder.dijkstra_shortest_path(from_station, to_station, graph, 'distance', preferences)
        
        if path_node:
            try:
                route = self.route_converter.path_to_route(path_node, graph)
                return self.underground_handler.enhance_route_with_black_box(route)
            except Exception as e:
                self.logger.error("Failed to create shortest route: %s", e)
        
        return None
    
    def get_fewest_changes_route(self, from_station: str, to_station: str,
                                preferences: Optional[Dict[str, Any]] = None) -> Optional[Route]:
        """Get the route with fewest changes between two stations."""
        graph = self.network_builder.build_network_graph()
        path_node = self.pathfinder.dijkstra_shortest_path(from_station, to_station, graph, 'changes', preferences)
        
        if path_node:
            try:
                route = self.route_converter.path_to_route(path_node, graph)
                return self.underground_handler.enhance_route_with_black_box(route)
            except Exception as e:
                self.logger.error("Failed to create fewest changes route: %s", e)
        
        return None
    
    def find_routes_via_station(self, from_station: str, to_station: str,
                               via_station: str,
                               preferences: Optional[Dict[str, Any]] = None) -> List[Route]:
        """Find routes that pass through a specific intermediate station."""
        routes = []
        
        # Calculate route from start to via station
        first_leg = self.calculate_route(from_station, via_station, preferences=preferences)
        if not first_leg:
            return routes
        
        # Calculate route from via station to destination
        second_leg = self.calculate_route(via_station, to_station, preferences=preferences)
        if not second_leg:
            return routes
        
        # Combine the routes
        route = self.route_converter.create_via_station_route(
            from_station, to_station, first_leg, second_leg, via_station
        )
        
        routes.append(route)
        return routes
    
    def find_routes_avoiding_station(self, from_station: str, to_station: str,
                                   avoid_station: str,
                                   preferences: Optional[Dict[str, Any]] = None) -> List[Route]:
        """Find routes that avoid a specific station."""
        routes = self.calculate_multiple_routes(from_station, to_station, preferences=preferences)
        
        filtered_routes = []
        for route in routes:
            if avoid_station not in route.intermediate_stations:
                filtered_routes.append(route)
        
        return filtered_routes
    
    def find_routes_on_line(self, from_station: str, to_station: str,
                           line_name: str,
                           preferences: Optional[Dict[str, Any]] = None) -> List[Route]:
        """Find routes that use a specific railway line."""
        # Check if both stations are on the specified line
        line = self.data_repository.get_railway_line_by_name(line_name)
        if not line:
            return []
        
        if from_station not in line.stations or to_station not in line.stations:
            return []
        
        # Try to find direct route on this line
        direct_routes = self.find_direct_routes(from_station, to_station)
        
        routes_on_line = []
        for route in direct_routes:
            if any(seg.line_name == line_name for seg in route.segments):
                routes_on_line.append(route)
        
        return routes_on_line
    
    def get_possible_destinations(self, from_station: str, 
                                max_changes: int = 3) -> List[str]:
        return _get_possible_destinations(
            network_builder=self.network_builder,
            from_station=from_station,
            max_changes=max_changes,
        )
    
    def get_journey_time(self, from_station: str, to_station: str,
                        preferences: Optional[Dict[str, Any]] = None) -> Optional[int]:
        """Get estimated journey time between two stations."""
        route = self.get_fastest_route(from_station, to_station, preferences)
        return route.total_journey_time_minutes if route else None
    
    def get_distance(self, from_station: str, to_station: str,
                    preferences: Optional[Dict[str, Any]] = None) -> Optional[float]:
        """Get distance between two stations."""
        route = self.get_shortest_route(from_station, to_station, preferences)
        return route.total_distance_km if route else None
    
    def validate_route(self, route: Route) -> Tuple[bool, List[str]]:
        return _validate_route(data_repository=self.data_repository, route=route)
    
    def get_route_alternatives(self, route: Route, max_alternatives: int = 3,
                              preferences: Optional[Dict[str, Any]] = None) -> List[Route]:
        """Get alternative routes similar to the given route."""
        return self.calculate_multiple_routes(
            route.from_station,
            route.to_station,
            max_alternatives + 1,  # +1 because original might be included
            preferences=preferences,
        )[:max_alternatives]
    
    def calculate_route_cost(self, route: Route) -> Optional[float]:
        return _calculate_route_cost(route=route)
    
    def get_interchange_stations(self, from_station: str, to_station: str) -> List[str]:
        return _get_interchange_stations(
            data_repository=self.data_repository,
            from_station=from_station,
            to_station=to_station,
        )
    
    def find_circular_routes(self, station: str, max_distance: float = 50.0) -> List[Route]:
        return _find_circular_routes(
            network_builder=self.network_builder,
            route_converter=self.route_converter,
            station=station,
            max_distance=max_distance,
            logger=self.logger,
        )
    
    def get_route_statistics(self) -> Dict[str, Any]:
        stats = _get_route_statistics(
            network_builder=self.network_builder,
            data_repository=self.data_repository,
            underground_handler=self.underground_handler,
        )
        stats["cache_size"] = len(self._route_cache)
        return stats
    
    def clear_route_cache(self) -> None:
        """Clear any cached route calculations."""
        self._route_cache.clear()
        self.network_builder.clear_cache()
        self.underground_handler.clear_cache()
        self.logger.info("All caches cleared")
    
    def precompute_common_routes(self, station_pairs: List[Tuple[str, str]]) -> None:
        _precompute_common_routes(route_service=self, station_pairs=station_pairs)
    

    def _calculate_terminus_to_underground_route(
        self, from_station: str, to_station: str, preferences: Optional[Dict[str, Any]] = None
    ) -> Optional[Route]:
        return self._underground_planner.calculate_terminus_to_underground_route(
            from_station=from_station, to_station=to_station, preferences=preferences
        )

    def _calculate_underground_to_terminus_route(
        self, from_station: str, to_station: str, preferences: Optional[Dict[str, Any]] = None
    ) -> Optional[Route]:
        return self._underground_planner.calculate_underground_to_terminus_route(
            from_station=from_station, to_station=to_station, preferences=preferences
        )

