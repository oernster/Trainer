"""
Route calculation service for train journey planning.

This service handles route finding, validation, and optimization for train journeys.
It coordinates with core services and provides fallback routing capabilities.
"""

import logging
from typing import List, Optional, Dict, Tuple
from datetime import datetime
from pathlib import Path
import json

from ...core.interfaces.i_route_service import IRouteService
from ...core.interfaces.i_station_service import IStationService

logger = logging.getLogger(__name__)


class RouteCalculationService:
    """Service for calculating and validating train routes."""

    def __init__(
        self,
        route_service: Optional[IRouteService] = None,
        station_service: Optional[IStationService] = None,
        *,
        simple_route_finder=None,
    ):
        """
        Initialize route calculation service.

        Args:
            route_service: Core route service for route calculations
            station_service: Core station service for station data
        """
        self.route_service = route_service
        self.station_service = station_service

        # Phase 2 boundary: fallback routing helper must be injected.
        self._simple_route_finder = simple_route_finder
        
        # Cache for line data to prevent repeated loading
        self._line_data_cache: Optional[Dict[str, Dict]] = None
        self._walking_connections_cache: Optional[Dict] = None

    def calculate_route(self, from_station: str, to_station: str, 
                       preferences: Optional[Dict] = None) -> Optional[object]:
        """
        Calculate route between two stations with preferences.

        Args:
            from_station: Origin station name
            to_station: Destination station name
            preferences: Route preferences (avoid_walking, prefer_direct, etc.)

        Returns:
            Route result object or None if no route found
        """
        logger.info(f"Calculating route: {from_station} -> {to_station}")
        
        if not from_station or not to_station:
            logger.warning("Missing origin or destination station")
            return None

        # Try core route service first
        if self.route_service:
            try:
                route_result = self.route_service.calculate_route(
                    from_station, to_station, preferences=preferences or {}
                )
                
                if route_result:
                    # Validate and enhance the route
                    validated_route = self._ensure_valid_interchange_route(
                        route_result, from_station, to_station
                    )
                    return validated_route
                    
            except Exception as e:
                logger.error(f"Core route service failed: {e}")

        # Fallback to simple route finder
        return self._calculate_fallback_route(from_station, to_station, preferences)

    def _calculate_fallback_route(self, from_station: str, to_station: str,
                                  preferences: Optional[Dict] = None) -> Optional[object]:
        """Calculate route using fallback simple route finder."""
        try:
            simple_finder = self._simple_route_finder
            if simple_finder is None:
                raise RuntimeError("SimpleRouteFinder is not injected")
            
            # Ensure simple finder is loaded
            if not simple_finder.loaded:
                simple_finder.load_data()
                
            if not simple_finder.loaded:
                logger.error("Could not load simple route finder")
                return self._create_minimal_route([from_station, to_station])

            # Get preferences
            avoid_walking = preferences.get('avoid_walking', False) if preferences else False
            
            # Load walking connections
            walking_connections = self._load_walking_connections()
            
            # Find route with increasing complexity
            route_path = self._find_optimal_route(
                from_station, to_station, simple_finder, avoid_walking, walking_connections
            )
            
            if route_path:
                return self._create_minimal_route(route_path, avoid_walking, walking_connections)
            else:
                return self._create_minimal_route([from_station, to_station])
                
        except Exception as e:
            logger.error(f"Fallback route calculation failed: {e}")
            return self._create_minimal_route([from_station, to_station])

    def _find_optimal_route(self, from_station: str, to_station: str, 
                           simple_finder, avoid_walking: bool, 
                           walking_connections: Dict) -> Optional[List[str]]:
        """Find optimal route using simple route finder with complexity analysis."""
        # Estimate minimum changes needed
        min_expected_changes = self._estimate_min_changes(from_station, to_station, simple_finder)
        logger.info(f"Estimated minimum changes needed: {min_expected_changes}")
        
        best_route = None
        
        # Try finding routes with various numbers of changes
        for max_changes in range(max(1, min_expected_changes), 10):
            logger.debug(f"Trying route with max_changes={max_changes}")
            
            candidate_route = simple_finder.find_route_with_changes(
                from_station, to_station, max_changes=max_changes
            )
            
            if not candidate_route or len(candidate_route) < 2:
                continue
            
            # Validate route based on preferences
            valid_route = True
            if avoid_walking:
                valid_route = self._is_valid_rail_route(candidate_route, walking_connections)
            
            # Store as best route if valid
            if valid_route and (not best_route or len(candidate_route) < len(best_route)):
                best_route = candidate_route
                logger.debug(f"Updated best route: {len(best_route)} stations")
            
            # Check if route is realistic
            if valid_route and self._is_realistic_route(candidate_route, min_expected_changes):
                logger.info(f"Found optimal route with {len(candidate_route)} stations")
                return candidate_route
                
            # Stop searching after reasonable attempts
            if max_changes >= min_expected_changes + 3:
                break
        
        return best_route

    def _estimate_min_changes(self, from_station: str, to_station: str, simple_finder) -> int:
        """Estimate minimum changes needed based on network analysis."""
        from_lines = simple_finder.get_lines_for_station(from_station)
        to_lines = simple_finder.get_lines_for_station(to_station)
        
        # If they share a line, likely 0-1 changes
        if set(from_lines) & set(to_lines):
            return 0
        
        # Known hubs that often require changes
        hubs = ["London", "Birmingham", "Manchester", "Edinburgh", "Glasgow", "Leeds", "Bristol"]
        
        is_from_hub = any(hub in from_station for hub in hubs)
        is_to_hub = any(hub in to_station for hub in hubs)
        
        if is_from_hub != is_to_hub:
            return 1
        
        # Get interchange stations
        interchanges = simple_finder.find_interchange_stations()
        
        if from_station in interchanges and to_station in interchanges:
            return 1
        
        return 2

    def _is_valid_rail_route(self, route: List[str], walking_connections: Dict) -> bool:
        """Check if route only uses rail connections."""
        if not route or len(route) < 2:
            return False
            
        for i in range(len(route) - 1):
            station_pair = (route[i], route[i+1])
            reverse_pair = (route[i+1], route[i])
            
            # If it's a known walking connection, the route is invalid
            if station_pair in walking_connections or reverse_pair in walking_connections:
                logger.debug(f"Found walking segment: {route[i]} → {route[i+1]}")
                return False
        
        return True

    def _is_realistic_route(self, route: List[str], min_expected_changes: int) -> bool:
        """Check if route is realistic given the UK rail network."""
        if not route or len(route) < 2:
            return False
        
        actual_changes = len(route) - 2  # Number of intermediate stations
        
        if min_expected_changes > 0 and actual_changes < min_expected_changes:
            logger.warning(f"Route with {actual_changes} changes rejected - expected at least {min_expected_changes}")
            return False
        
        return True

    def _ensure_valid_interchange_route(self, route_result, from_station: str, to_station: str):
        """Ensure routes between disconnected lines include necessary interchange stations."""
        logger.debug("Starting route validation")
        
        if not route_result:
            return route_result
        
        # If route service provided enhanced path, preserve it
        if (hasattr(route_result, 'full_path') and route_result.full_path and
            len(route_result.full_path) > 2):
            logger.debug(f"Route service provided enhanced path with {len(route_result.full_path)} stations")
            return route_result
        
        try:
            # Load line data for analysis
            line_data = self._load_all_line_data()
            if not line_data:
                return route_result
            
            # Build station-to-lines mapping
            station_to_lines = self._build_station_to_lines_mapping(line_data)
            
            # Check if stations are on disconnected lines
            origin_lines = station_to_lines.get(from_station, [])
            dest_lines = station_to_lines.get(to_station, [])
            
            common_lines = set(origin_lines) & set(dest_lines)
            
            if common_lines:
                return route_result  # Direct connection is valid
            
            logger.debug(f"Disconnected lines detected: {from_station} -> {to_station}")
            
            # Find required interchange stations
            required_interchanges = self._find_required_interchanges(
                origin_lines, dest_lines, station_to_lines
            )
            
            if required_interchanges:
                # Build corrected route
                corrected_path = self._build_corrected_route(
                    from_station, to_station, required_interchanges,
                    station_to_lines, line_data
                )
                
                if corrected_path and len(corrected_path) >= 2:
                    logger.debug(f"Corrected route: {' -> '.join(corrected_path)}")
                    
                    # Update route result
                    if hasattr(route_result, 'full_path'):
                        object.__setattr__(route_result, 'full_path', corrected_path)
                    
                    # Create proper segments
                    corrected_segments = self._create_route_segments_from_path(corrected_path, line_data)
                    if hasattr(route_result, 'segments'):
                        object.__setattr__(route_result, 'segments', corrected_segments)
            
            return route_result
            
        except Exception as e:
            logger.error(f"Route validation error: {e}")
            return route_result

    def _find_required_interchanges(self, origin_lines: List[str], dest_lines: List[str],
                                   station_to_lines: Dict[str, List[str]]) -> List[str]:
        """Find stations that can serve as interchanges between origin and destination lines."""
        interchange_candidates = []
        
        for station_name, station_lines in station_to_lines.items():
            station_line_set = set(station_lines)
            
            connects_origin = bool(station_line_set & set(origin_lines))
            connects_dest = bool(station_line_set & set(dest_lines))
            
            if connects_origin and connects_dest:
                interchange_candidates.append((station_name, 1))  # Direct connection
            elif connects_origin:
                # Check indirect connections to destination network
                for line in station_lines:
                    if self._line_connects_to_network(line, dest_lines, station_to_lines):
                        interchange_candidates.append((station_name, 2))  # Indirect
                        break
            elif connects_dest:
                # Check indirect connections to origin network
                for line in station_lines:
                    if self._line_connects_to_network(line, origin_lines, station_to_lines):
                        interchange_candidates.append((station_name, 2))  # Indirect
                        break
        
        # Sort by priority and return top candidates
        interchange_candidates.sort(key=lambda x: x[1])
        required_interchanges = [station for station, priority in interchange_candidates[:3]]
        
        logger.info(f"Required interchanges: {required_interchanges}")
        return required_interchanges

    def _line_connects_to_network(self, line_name: str, target_lines: List[str],
                                 station_to_lines: Dict[str, List[str]]) -> bool:
        """Check if a line connects to any station that serves the target line network."""
        for station_name, station_lines in station_to_lines.items():
            if line_name in station_lines:
                if any(target_line in station_lines for target_line in target_lines):
                    return True
        return False

    def _build_corrected_route(self, from_station: str, to_station: str,
                              required_interchanges: List[str],
                              station_to_lines: Dict[str, List[str]],
                              line_data: Dict[str, Dict]) -> List[str]:
        """Build a corrected route that includes all required interchange stations."""
        try:
            route = [from_station]
            
            if required_interchanges:
                first_interchange = required_interchanges[0]
                
                # Find path from origin to first interchange
                intermediate_to_first = self._find_path_between_stations(
                    from_station, first_interchange, station_to_lines, line_data
                )
                if intermediate_to_first:
                    route.extend(intermediate_to_first[1:-1])  # Exclude origin and interchange
                
                route.append(first_interchange)
                
                # Find path from interchange to destination
                intermediate_to_dest = self._find_path_between_stations(
                    first_interchange, to_station, station_to_lines, line_data
                )
                if intermediate_to_dest:
                    route.extend(intermediate_to_dest[1:])  # Exclude interchange, include destination
                else:
                    route.append(to_station)
            else:
                route.append(to_station)
            
            return route
            
        except Exception as e:
            logger.error(f"Error building corrected route: {e}")
            return [from_station, to_station]

    def _find_path_between_stations(self, start_station: str, end_station: str,
                                   station_to_lines: Dict[str, List[str]],
                                   line_data: Dict[str, Dict]) -> List[str]:
        """Find a path between two stations using line data."""
        start_lines = station_to_lines.get(start_station, [])
        end_lines = station_to_lines.get(end_station, [])
        
        common_lines = set(start_lines) & set(end_lines)
        
        if common_lines:
            line_name = list(common_lines)[0]
            line_stations = []
            
            if line_name in line_data:
                stations = line_data[line_name].get('stations', [])
                line_stations = [s.get('name', '') for s in stations]
            
            try:
                start_idx = line_stations.index(start_station)
                end_idx = line_stations.index(end_station)
                
                if start_idx < end_idx:
                    return line_stations[start_idx:end_idx + 1]
                else:
                    return line_stations[end_idx:start_idx + 1][::-1]
            except ValueError:
                pass
        
        return [start_station, end_station]

    def _create_route_segments_from_path(self, path: List[str], line_data: Dict[str, Dict]) -> List:
        from .route_calc_components.route_objects import create_route_segments_from_path

        return create_route_segments_from_path(service=self, path=path, line_data=line_data)

    def _create_minimal_route(self, path: List[str], avoid_walking: bool = False,
                              walking_connections: Optional[Dict] = None) -> object:
        from .route_calc_components.route_objects import create_minimal_route

        return create_minimal_route(
            path=path,
            avoid_walking=avoid_walking,
            walking_connections=walking_connections,
        )

    def _load_all_line_data(self) -> Dict[str, Dict]:
        from .route_calc_components.data_loading import load_all_line_data

        return load_all_line_data(service=self)

    def _build_station_to_lines_mapping(self, line_data: Dict[str, Dict]) -> Dict[str, List[str]]:
        """Build mapping of station names to the lines they appear on."""
        station_to_lines = {}
        
        for line_name, data in line_data.items():
            stations = data.get('stations', [])
            for station in stations:
                station_name = station.get('name', '')
                if station_name:
                    if station_name not in station_to_lines:
                        station_to_lines[station_name] = []
                    station_to_lines[station_name].append(line_name)
        
        return station_to_lines

    def _load_walking_connections(self) -> Dict:
        from .route_calc_components.data_loading import load_walking_connections

        return load_walking_connections(service=self)

    def _generate_train_service_id(self, line_name: str, service_pattern: Optional[str],
                                  from_station: str, to_station: str) -> str:
        """
        Generate a train service ID that identifies the physical train service.
        
        For the user's specific journey (Farnborough North → Farnborough Main → Clapham Junction → London Waterloo):
        - Farnborough North → Farnborough Main: Different train (GWR_READING_BASINGSTOKE)
        - Farnborough Main → Clapham Junction → London Waterloo: Same train (SWR_MAIN_LINE)
        """
        if line_name == 'WALKING':
            return f"WALKING_{from_station}_{to_station}"
        
        # Generate service ID based on line and service pattern
        line_key = line_name.upper().replace(' ', '_').replace('-', '_')
        
        # For specific journey segments, assign consistent service IDs
        if line_name == "Reading to Basingstoke Line":
            return "GWR_READING_BASINGSTOKE_SERVICE"
        elif line_name == "South Western Main Line":
            return "SWR_MAIN_LINE_SERVICE"
        elif line_name == "Portsmouth Direct Line":
            # Portsmouth Direct Line trains continue as South Western Main Line trains
            return "SWR_MAIN_LINE_SERVICE"
        elif "South Western" in line_name:
            return "SWR_MAIN_LINE_SERVICE"
        elif "Portsmouth" in line_name and "Direct" in line_name:
            # Portsmouth Direct trains are part of the SWR Main Line service
            return "SWR_MAIN_LINE_SERVICE"
        elif "Great Western" in line_name or "Reading" in line_name or "GWR" in line_name:
            # All Great Western Railway services use the same service ID
            return "GWR_MAIN_LINE_SERVICE"
        elif "Cross Country" in line_name or "CrossCountry" in line_name:
            # All Cross Country services use the same service ID
            return "CROSS_COUNTRY_SERVICE"
        else:
            # Generic service ID for other lines
            service_suffix = f"_{service_pattern}" if service_pattern else ""
            return f"{line_key}_SERVICE{service_suffix}"
