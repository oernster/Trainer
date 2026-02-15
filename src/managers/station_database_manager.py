"""
Station Database Manager for offline railway station data with Service Pattern Support.
Author: Oliver Ernster

This module provides functionality to load and search UK railway station data
from local JSON files, with support for service patterns (express, fast, stopping).
UPDATED: Now uses station names exclusively - no more station codes.
"""

import json
import logging
import math
from pathlib import Path
from typing import List, Dict, Optional, Set, Tuple
from dataclasses import dataclass
from datetime import datetime, time
from ..models.service_patterns import ServicePattern, ServicePatternSet, ServiceType

# Import data path resolver
from ..utils.data_path_resolver import get_data_directory, get_lines_directory, get_data_file_path

logger = logging.getLogger(__name__)

@dataclass
class Station:
    """Represents a railway station."""
    name: str
    coordinates: Dict[str, float]
    zone: Optional[int] = None
    interchange: Optional[List[str]] = None

@dataclass
class RailwayLine:
    """Represents a railway line with its stations."""
    name: str
    file: str
    operator: str
    terminus_stations: List[str]
    major_stations: List[str]
    stations: List[Station]
    service_patterns: Optional[ServicePatternSet] = None

class StationDatabaseManager:
    """Manages the offline railway station database with service pattern support."""
    
    def __init__(self):
        """Initialize the station database manager."""
        try:
            self.data_dir = get_data_directory()
            self.lines_dir = get_lines_directory()
        except FileNotFoundError as e:
            logger.error(f"Failed to find data directory: {e}")
            # Fallback to old method
            self.data_dir = Path(__file__).parent.parent / "data"
            self.lines_dir = self.data_dir / "lines"
            
        self.railway_lines: Dict[str, RailwayLine] = {}
        self.all_stations: Dict[str, Station] = {}  # name -> Station
        self.loaded = False
    
    def load_database(self) -> bool:
        from .station_database_components.loading import load_database

        # Provide extracted module access to the same logger + types.
        self.logger = logger
        self.Station = Station
        self.RailwayLine = RailwayLine
        self.ServicePatternSet = ServicePatternSet

        return load_database(manager=self)

    def get_service_patterns_for_line(self, line_name: str) -> Optional[ServicePatternSet]:
        """Get service patterns for a railway line."""
        if not self.loaded:
            if not self.load_database():
                return None
        
        railway_line = self.railway_lines.get(line_name)
        if railway_line:
            return railway_line.service_patterns
        return None
    
    def find_best_service_pattern(self, from_station: str, to_station: str, line_name: str, 
                                departure_time: Optional[str] = None) -> Optional[ServicePattern]:
        """Find the best service pattern (prefer fast over semi-fast over stopping)."""
        if not self.loaded:
            if not self.load_database():
                return None
        
        service_patterns = self.get_service_patterns_for_line(line_name)
        if not service_patterns:
            return None
        
        # Get all station names for this line
        railway_line = self.railway_lines.get(line_name)
        if not railway_line:
            return None
        
        all_station_names = [station.name for station in railway_line.stations]
        
        # Find the best pattern that serves both stations
        return service_patterns.get_best_pattern_for_stations(from_station, to_station, all_station_names)
    
    def get_stations_for_service_pattern(self, line_name: str, pattern_name: str) -> List[str]:
        """Get station names for a specific service pattern."""
        if not self.loaded:
            if not self.load_database():
                return []
        
        service_patterns = self.get_service_patterns_for_line(line_name)
        if not service_patterns:
            return []
        
        pattern = service_patterns.get_pattern(pattern_name)
        if not pattern:
            return []
        
        # Get all station names for this line
        railway_line = self.railway_lines.get(line_name)
        if not railway_line:
            return []
        
        all_station_names = [station.name for station in railway_line.stations]
        
        if pattern.stations == "all":
            return all_station_names
        elif isinstance(pattern.stations, list):
            return pattern.stations
        return []
    
    def build_service_aware_network(self) -> Dict[str, Dict]:
        """
        Build network considering service patterns.
        Creates connections only between stations served by the same pattern,
        with weights based on service speed (fast < semi-fast < stopping).
        """
        from .station_database_components.service_pattern_routing import (
            build_service_aware_network,
        )

        self.ServiceType = ServiceType  # type: ignore[attr-defined]
        self.logger = logger  # type: ignore[assignment]
        return build_service_aware_network(manager=self)
    
    def _add_legacy_connections(self, network: Dict, railway_line, line_name: str):
        """Add connections for lines without service patterns (legacy method)."""
        stations = railway_line.stations
        
        # Connect adjacent stations on the same line
        for i in range(len(stations) - 1):
            current_station = stations[i]
            next_station = stations[i + 1]
            
            # Calculate distance and time
            distance = self.calculate_haversine_distance(
                current_station.coordinates, next_station.coordinates
            )
            
            journey_time = self.get_journey_time_between_stations(
                current_station.name, next_station.name
            )
            if not journey_time:
                journey_time = max(2, int(distance * 1.5))
            
            # Add bidirectional connections (legacy format)
            network[current_station.name]['connections'].append(
                (next_station.name, distance, journey_time, line_name, "legacy", 3)  # Default priority
            )
            network[next_station.name]['connections'].append(
                (current_station.name, distance, journey_time, line_name, "legacy", 3)
            )

    def dijkstra_shortest_path_with_service_patterns(self, start_name: str, end_name: str,
                                                   max_routes: int = 5, max_changes: int = 3,
                                                   departure_time: Optional[str] = None) -> List[Tuple[List[str], float]]:
        """
        Enhanced Dijkstra with service pattern awareness.
        Prioritizes faster service patterns when building routes.
        """
        from .station_database_components.service_pattern_routing import (
            dijkstra_shortest_path_with_service_patterns,
        )

        self.ServiceType = ServiceType  # type: ignore[attr-defined]
        self.logger = logger  # type: ignore[assignment]
        return dijkstra_shortest_path_with_service_patterns(
            manager=self,
            start_name=start_name,
            end_name=end_name,
            max_routes=max_routes,
            max_changes=max_changes,
            departure_time=departure_time,
        )
    
    def _find_direct_route_on_line(self, start_name: str, end_name: str, line_name: str) -> Optional[List[str]]:
        """Find direct route between two stations on the same railway line."""
        try:
            railway_line = self.railway_lines.get(line_name)
            if not railway_line:
                return None
            
            # Get station positions on the line
            station_names = [station.name for station in railway_line.stations]
            
            try:
                start_idx = station_names.index(start_name)
                end_idx = station_names.index(end_name)
            except ValueError:
                return None
            
            # Build direct route
            if start_idx < end_idx:
                # Forward direction
                route_names = station_names[start_idx:end_idx + 1]
            else:
                # Reverse direction
                route_names = station_names[end_idx:start_idx + 1]
                route_names.reverse()
            
            return route_names if len(route_names) >= 2 else None
            
        except Exception as e:
            logger.warning(f"Error finding direct route: {e}")
            return None

    def get_station_by_name(self, station_name: str) -> Optional[Station]:
        """Get station object by name."""
        if not self.loaded:
            if not self.load_database():
                return None
        
        parsed_name = self.parse_station_name(station_name)
        return self.all_stations.get(parsed_name)
    
    def get_railway_lines_for_station(self, station_name: str) -> List[str]:
        """Get all railway lines that serve a given station."""
        if not self.loaded:
            if not self.load_database():
                return []
        
        lines = []
        for line_name, railway_line in self.railway_lines.items():
            line_station_names = [s.name for s in railway_line.stations]
            if station_name in line_station_names:
                lines.append(line_name)
        return lines
    
    def calculate_haversine_distance(self, coord1: Dict[str, float], coord2: Dict[str, float]) -> float:
        """Calculate the great circle distance between two points on Earth using the Haversine formula."""
        if not coord1 or not coord2:
            return float("inf")

        lat1, lng1 = coord1.get("lat", 0), coord1.get("lng", 0)
        lat2, lng2 = coord2.get("lat", 0), coord2.get("lng", 0)

        if not all([lat1, lng1, lat2, lng2]):
            return float("inf")

        from .station_database_components.geo import calculate_haversine_distance

        return calculate_haversine_distance({"lat": lat1, "lng": lng1}, {"lat": lat2, "lng": lng2})
    
    def get_journey_time_between_stations(self, from_station: str, to_station: str) -> Optional[int]:
        """Get journey time between two stations from JSON data."""
        if not self.loaded:
            if not self.load_database():
                return None
        
        # Load all line data to find journey times
        for line_name, railway_line in self.railway_lines.items():
            # Load the JSON file for this line to get journey times
            line_file = self.lines_dir / railway_line.file
            if not line_file.exists():
                continue
                
            try:
                with open(line_file, 'r', encoding='utf-8') as f:
                    line_data = json.load(f)
                
                journey_times = line_data.get('typical_journey_times', {})
                
                # Try direct journey time using station names
                journey_key = f"{from_station}-{to_station}"
                if journey_key in journey_times:
                    return journey_times[journey_key]
                
                # Try reverse direction
                reverse_key = f"{to_station}-{from_station}"
                if reverse_key in journey_times:
                    return journey_times[reverse_key]
                    
            except Exception as e:
                logger.warning(f"Error reading journey times from {line_file}: {e}")
                continue
        
        return None

    # UI Compatibility Methods - Required by stations_settings_dialog.py
     
    def search_stations(self, query: str, limit: int = 10) -> List[str]:
        """Search for stations matching the query with disambiguation context and improved case insensitive matching."""
        from .station_database_components.ui_compat import search_stations

        return search_stations(manager=self, query=query, limit=limit)
    
    def parse_station_name(self, station_name: str) -> str:
        """Parse station name to remove disambiguation context."""
        from .station_database_components.ui_compat import parse_station_name

        return parse_station_name(station_name=station_name)
    
    def get_all_stations_with_context(self) -> List[str]:
        """Get all stations with disambiguation context where needed."""
        from .station_database_components.ui_compat import get_all_stations_with_context

        return get_all_stations_with_context(manager=self)
    
    def suggest_via_stations(self, from_station: str, to_station: str, limit: int = 10) -> List[str]:
        """Suggest via stations for a route."""
        from .station_database_components.ui_compat import suggest_via_stations

        return suggest_via_stations(
            manager=self,
            from_station=from_station,
            to_station=to_station,
            limit=limit,
        )
    
    def find_route_between_stations(self, from_station: str, to_station: str,
                                  max_changes: int = 3, departure_time: Optional[str] = None) -> List[List[str]]:
        """Find routes between stations (UI compatibility method)."""
        from .station_database_components.ui_compat import find_route_between_stations

        return find_route_between_stations(
            manager=self,
            from_station=from_station,
            to_station=to_station,
            max_changes=max_changes,
            departure_time=departure_time,
        )
    
    def identify_train_changes(self, route: List[str]) -> List[str]:
        """Identify stations where train changes are required."""
        from .station_database_components.ui_compat import identify_train_changes

        return identify_train_changes(manager=self, route=route)
    
    def get_operator_for_segment(self, from_station: str, to_station: str) -> Optional[str]:
        """Get operator for a segment between two stations."""
        from .station_database_components.ui_compat import get_operator_for_segment

        return get_operator_for_segment(
            manager=self,
            from_station=from_station,
            to_station=to_station,
        )
    
    def get_database_stats(self) -> Dict[str, int]:
        """Get database statistics."""
        from .station_database_components.ui_compat import get_database_stats

        return get_database_stats(manager=self)

    def find_route_between_stations_with_service_patterns(self, from_station: str, to_station: str,
                                                        max_changes: int = 3,
                                                        departure_time: Optional[str] = None) -> List[List[str]]:
        """
        Find routes between stations using service pattern optimization.
        This is the new main routing method that prioritizes faster services.
        """
        if not self.loaded:
            if not self.load_database():
                logger.error("Database loading failed")
                return []
        
        # Parse station names to remove line context
        from_parsed = self.parse_station_name(from_station)
        to_parsed = self.parse_station_name(to_station)
        
        # Check if stations exist in the database
        from_station_obj = self.all_stations.get(from_parsed)
        to_station_obj = self.all_stations.get(to_parsed)
        
        if not from_station_obj or not to_station_obj:
            logger.error(f"Station objects not found: from='{from_parsed}' -> {from_station_obj is not None}, to='{to_parsed}' -> {to_station_obj is not None}")
            return []
        
        # First try simple direct route check
        direct_route = self._find_simple_direct_route(from_parsed, to_parsed)
        if direct_route:
            return [direct_route]
        
        # Try service pattern aware Dijkstra with timeout protection
        try:
            route_results = self.dijkstra_shortest_path_with_service_patterns(
                from_parsed, to_parsed, max_routes=5, max_changes=max_changes, departure_time=departure_time
            )
            
            # Routes are already in station names
            named_routes = []
            for route_names, cost in route_results:
                if route_names:
                    named_routes.append(route_names)
                    logger.info(f"Service-aware route: {' -> '.join(route_names)} (Cost: {cost:.2f})")
            
            if named_routes:
                return named_routes
                
        except Exception as e:
            logger.debug(f"Service pattern routing failed: {e}")
        
        # Fallback to simple routing if service pattern routing fails
        logger.info("Falling back to simple routing")
        return self._find_simple_routes(from_parsed, to_parsed, max_changes)
    
    def _find_simple_direct_route(self, from_name: str, to_name: str) -> Optional[List[str]]:
        """Find a simple direct route between two stations on the same line."""
        from .station_database_components.routing_fallback import find_simple_direct_route

        return find_simple_direct_route(manager=self, from_name=from_name, to_name=to_name)
    
    def _find_simple_routes(self, from_name: str, to_name: str, max_changes: int = 3) -> List[List[str]]:
        """Simple fallback routing without service patterns."""
        from .station_database_components.routing_fallback import find_simple_routes

        return find_simple_routes(
            manager=self,
            from_name=from_name,
            to_name=to_name,
            max_changes=max_changes,
        )

    def _test_database_integrity(self) -> bool:
        """Test database integrity by checking key stations exist by name."""
        try:
            # Test key stations that should definitely exist (by name only now)
            test_stations = [
                "Farnborough (Main)",
                "London Waterloo",
                "Fleet",
                "Woking",
                "Clapham Junction"
            ]
            
            all_passed = True
            failed_tests = []
            
            for station_name in test_stations:
                # Test that station exists in all_stations (now keyed by name)
                if station_name not in self.all_stations:
                    failed_tests.append(f"'{station_name}' -> Station not found in database")
                    all_passed = False
                    continue
                
                # Test that we can get the station object
                station_obj = self.all_stations.get(station_name)
                if not station_obj or station_obj.name != station_name:
                    failed_tests.append(f"'{station_name}' -> Station object lookup failed")
                    all_passed = False
            
            if all_passed:
                logger.debug("All database integrity tests passed")
            else:
                logger.error(f"Database integrity test failures: {failed_tests}")
            
            return all_passed
            
        except Exception as e:
            logger.error(f"Database integrity test error: {e}")
            return False
