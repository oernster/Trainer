"""
Underground Route Factory

Handles creation of different types of underground routes.
"""

import logging
from typing import List, Optional, Tuple

from src.core.models.route import Route, RouteSegment
from .station_classifier import StationClassifier
from .journey_estimator import JourneyEstimator
from .terminal_manager import TerminalManager
from .geographic_utils import GeographicUtils
from .cross_country_routes import create_cross_country_route


class RouteFactory:
    """Handles creation of different types of underground routes."""
    
    def __init__(
        self,
        station_classifier: StationClassifier,
        journey_estimator: JourneyEstimator,
        terminal_manager: TerminalManager,
        geographic_utils: GeographicUtils,
        data_repository
    ):
        """
        Initialize the route factory.
        
        Args:
            station_classifier: Station classifier for checking station types
            journey_estimator: Journey estimator for calculating distances and times
            terminal_manager: Terminal manager for handling terminal stations
            geographic_utils: Geographic utilities for region-based operations
            data_repository: Data repository for accessing railway data
        """
        self.station_classifier = station_classifier
        self.journey_estimator = journey_estimator
        self.terminal_manager = terminal_manager
        self.geographic_utils = geographic_utils
        self.data_repository = data_repository
        self.logger = logging.getLogger(__name__)
    
    def should_use_black_box_routing(self, from_station: str, to_station: str) -> bool:
        """
        Determine if black box routing should be used for a journey.
        
        Args:
            from_station: Starting station
            to_station: Destination station
            
        Returns:
            True if black box routing should be used, False otherwise
        """
        from_system = self.station_classifier.get_underground_system(from_station)
        to_system = self.station_classifier.get_underground_system(to_station)
        
        from_is_underground = from_system is not None
        to_is_underground = to_system is not None
        
        # If destination is a terminal that serves National Rail, prefer National Rail
        if to_is_underground and self.station_classifier.is_terminal_station(to_station):
            # Check if there's a direct National Rail connection
            if self.data_repository.validate_station_exists(from_station) and self.data_repository.validate_station_exists(to_station):
                # Both stations exist in National Rail network, prefer National Rail routing
                system_key, system_name = to_system
                self.logger.info(f"Preferring National Rail routing: {to_station} is a {system_name} terminal with National Rail services")
                return False
        
        # Use black box routing if:
        # 1. Both stations are underground stations (underground-to-underground routes)
        # 2. The destination is underground-only (not a mixed terminal)
        # 3. The origin is underground-only and destination is not underground (underground-to-national-rail routes)
        if to_is_underground:
            if from_is_underground:
                from_system_key, from_system_name = from_system
                to_system_key, to_system_name = to_system
                
                # Only use black box routing if both stations are from the same underground system
                if from_system_key == to_system_key:
                    self.logger.info(f"Using black box routing: {from_station} ({from_system_name}) to {to_station} ({to_system_name})")
                    return True
                else:
                    self.logger.info(f"Cannot use black box routing: {from_station} ({from_system_name}) and {to_station} ({to_system_name}) are from different underground systems")
                    return False
            elif self.station_classifier.is_underground_only_station(to_station):
                to_system_name = to_system[1]
                self.logger.info(f"Using black box routing: destination {to_station} is {to_system_name}-only station")
                return True
            else:
                to_system_name = to_system[1]
                self.logger.info(f"Preferring National Rail routing: destination {to_station} serves both {to_system_name} and National Rail")
                return False
        
        # Handle underground-to-national-rail routes
        if from_is_underground and not to_is_underground:
            # Check if origin is underground-only or if we should route via terminus
            if self.station_classifier.is_underground_only_station(from_station):
                from_system_name = from_system[1]
                self.logger.info(f"Using black box routing: origin {from_station} is {from_system_name}-only, routing via terminus to {to_station}")
                return True
            else:
                # Mixed station origin - check if destination exists in National Rail network
                if self.data_repository.validate_station_exists(to_station):
                    from_system_name = from_system[1]
                    self.logger.info(f"Using black box routing: routing from {from_system_name} station {from_station} via terminus to {to_station}")
                    return True
        
        return False
    
    def create_black_box_route(self, from_station: str, to_station: str) -> Optional[Route]:
        """
        Create a black box route for underground journeys.
        
        Args:
            from_station: Starting station
            to_station: Destination station
            
        Returns:
            A Route object with black box underground segment, or None if not applicable
        """
        if not self.should_use_black_box_routing(from_station, to_station):
            return None
        
        # Determine which underground system to use
        from_system = self.station_classifier.get_underground_system(from_station)
        to_system = self.station_classifier.get_underground_system(to_station)
        
        # Use the destination system if available, otherwise use the origin system
        system_info = to_system or from_system
        if not system_info:
            return None
        
        system_key, system_name = system_info
        
        # Create a single segment representing the underground journey
        segment = RouteSegment(
            from_station=from_station,
            to_station=to_station,
            line_name=system_name,
            distance_km=self.journey_estimator.estimate_underground_distance(from_station, to_station, system_key),
            journey_time_minutes=self.journey_estimator.estimate_underground_time(from_station, to_station, system_key),
            service_pattern="UNDERGROUND",
            train_service_id=f"{system_key.upper()}_UNDERGROUND_SERVICE"
        )
        
        route = Route(
            from_station=from_station,
            to_station=to_station,
            segments=[segment],
            total_distance_km=segment.distance_km,
            total_journey_time_minutes=segment.journey_time_minutes,
            changes_required=0,
            full_path=[from_station, to_station]
        )
        
        self.logger.info(f"Created black box {system_name} route: {from_station} -> {to_station}")
        return route
    
    def create_multi_system_route(self, from_station: str, to_station: str) -> Optional[Route]:
        """
        Create a multi-system route connecting different underground systems via National Rail.
        
        Args:
            from_station: Starting station (underground station)
            to_station: Destination station (different underground system)
            
        Returns:
            A Route object with multiple segments, or None if not applicable
        """
        from_system = self.station_classifier.get_underground_system(from_station)
        to_system = self.station_classifier.get_underground_system(to_station)
        
        # Only create multi-system routes if both stations are underground but from different systems
        if not (from_system and to_system and from_system[0] != to_system[0]):
            return None
        
        from_system_key, from_system_name = from_system
        to_system_key, to_system_name = to_system
        
        self.logger.info(f"Creating multi-system route: {from_station} ({from_system_name}) to {to_station} ({to_system_name})")
        
        # Get appropriate terminals for each system
        from_terminals = self.terminal_manager.get_nearest_terminals(from_station)
        to_terminals = self.terminal_manager.get_nearest_terminals(to_station)
        
        # Find the best terminal pair that exists in National Rail network
        best_from_terminal = None
        best_to_terminal = None
        
        for from_terminal in from_terminals:
            if self.data_repository.validate_station_exists(from_terminal):
                for to_terminal in to_terminals:
                    if self.data_repository.validate_station_exists(to_terminal):
                        best_from_terminal = from_terminal
                        best_to_terminal = to_terminal
                        break
                if best_from_terminal:
                    break
        
        if not (best_from_terminal and best_to_terminal):
            self.logger.warning(f"No suitable terminals found for multi-system route: {from_station} to {to_station}")
            return None
        
        segments = []
        total_distance = 0
        total_time = 0
        
        # Segment 1: Underground from origin to terminal
        if from_station != best_from_terminal:
            underground_segment1 = RouteSegment(
                from_station=from_station,
                to_station=best_from_terminal,
                line_name=from_system_name,
                distance_km=self.journey_estimator.estimate_underground_distance(from_station, best_from_terminal, from_system_key),
                journey_time_minutes=self.journey_estimator.estimate_underground_time(from_station, best_from_terminal, from_system_key),
                service_pattern="UNDERGROUND",
                train_service_id=f"{from_system_key.upper()}_UNDERGROUND_SERVICE"
            )
            segments.append(underground_segment1)
            total_distance += underground_segment1.distance_km or 0
            total_time += underground_segment1.journey_time_minutes or 0
        
        # Segment 2: National Rail between terminals
        if best_from_terminal != best_to_terminal:
            rail_distance = self.journey_estimator.estimate_national_rail_distance(best_from_terminal, best_to_terminal)
            rail_time = self.journey_estimator.estimate_national_rail_time(best_from_terminal, best_to_terminal)
            
            rail_segment = RouteSegment(
                from_station=best_from_terminal,
                to_station=best_to_terminal,
                line_name="National Rail",
                distance_km=rail_distance,
                journey_time_minutes=rail_time,
                service_pattern="NATIONAL_RAIL",
                train_service_id="NATIONAL_RAIL_SERVICE"
            )
            segments.append(rail_segment)
            total_distance += rail_segment.distance_km or 0
            total_time += rail_segment.journey_time_minutes or 0
        
        # Segment 3: Underground from terminal to destination
        if best_to_terminal != to_station:
            underground_segment2 = RouteSegment(
                from_station=best_to_terminal,
                to_station=to_station,
                line_name=to_system_name,
                distance_km=self.journey_estimator.estimate_underground_distance(best_to_terminal, to_station, to_system_key),
                journey_time_minutes=self.journey_estimator.estimate_underground_time(best_to_terminal, to_station, to_system_key),
                service_pattern="UNDERGROUND",
                train_service_id=f"{to_system_key.upper()}_UNDERGROUND_SERVICE"
            )
            segments.append(underground_segment2)
            total_distance += underground_segment2.distance_km or 0
            total_time += underground_segment2.journey_time_minutes or 0
        
        # Add interchange time (5 minutes per change)
        changes_required = len(segments) - 1
        total_time += changes_required * 5
        
        route = Route(
            from_station=from_station,
            to_station=to_station,
            segments=segments,
            total_distance_km=total_distance,
            total_journey_time_minutes=total_time,
            changes_required=changes_required,
            full_path=[from_station] + [seg.to_station for seg in segments]
        )
        
        self.logger.info(f"Created multi-system route: {from_station} -> {best_from_terminal} -> {best_to_terminal} -> {to_station}")
        return route
    
    def create_cross_country_route(self, from_station: str, to_station: str) -> Optional[Route]:
        return create_cross_country_route(self, from_station, to_station)
    
    def enhance_route_with_black_box(self, route: Route) -> Route:
        """
        Enhance a route by replacing underground segments with black box representation.
        
        Args:
            route: The route to enhance
            
        Returns:
            Enhanced route with black box underground segments
        """
        enhanced_segments = []
        
        for segment in route.segments:
            # Check if this segment involves underground-only stations
            from_underground_only = self.station_classifier.is_underground_only_station(segment.from_station)
            to_underground_only = self.station_classifier.is_underground_only_station(segment.to_station)
            
            if from_underground_only or to_underground_only:
                # Determine which underground system to use
                from_system = self.station_classifier.get_underground_system(segment.from_station)
                to_system = self.station_classifier.get_underground_system(segment.to_station)
                
                # Use the destination system if available, otherwise use the origin system
                system_info = to_system or from_system
                if system_info:
                    system_key, system_name = system_info
                    
                    # Replace with black box segment
                    black_box_segment = RouteSegment(
                        from_station=segment.from_station,
                        to_station=segment.to_station,
                        line_name=system_name,
                        distance_km=segment.distance_km,
                        journey_time_minutes=segment.journey_time_minutes,
                        service_pattern="UNDERGROUND",
                        train_service_id=f"{system_key.upper()}_UNDERGROUND_SERVICE"
                    )
                    enhanced_segments.append(black_box_segment)
                    self.logger.debug(f"Replaced segment with {system_name} black box: {segment.from_station} -> {segment.to_station}")
                else:
                    # Fallback to original segment if no system found
                    enhanced_segments.append(segment)
            else:
                # Keep the original segment
                enhanced_segments.append(segment)
        
        # Create enhanced route
        enhanced_route = Route(
            from_station=route.from_station,
            to_station=route.to_station,
            segments=enhanced_segments,
            total_distance_km=route.total_distance_km,
            total_journey_time_minutes=route.total_journey_time_minutes,
            changes_required=route.changes_required,
            full_path=self.terminal_manager.filter_underground_stations_from_path(route.full_path or [])
        )
        
        return enhanced_route
    
    def _create_national_rail_segment(self, from_station: str, to_station: str, line_name: str) -> RouteSegment:
        """
        Create a National Rail segment between two stations.
        
        Args:
            from_station: Origin station
            to_station: Destination station
            line_name: Railway line name
            
        Returns:
            RouteSegment for the connection
        """
        # Calculate approximate distance and time based on stations
        distance = self.journey_estimator.estimate_national_rail_distance(from_station, to_station)
        time = self.journey_estimator.estimate_national_rail_time(from_station, to_station)
        
        # Create the segment
        return RouteSegment(
            from_station=from_station,
            to_station=to_station,
            line_name=line_name,
            distance_km=distance,
            journey_time_minutes=time,
            service_pattern="NATIONAL_RAIL",
            train_service_id="NATIONAL_RAIL_SERVICE"
        )
