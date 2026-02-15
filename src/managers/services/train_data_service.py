"""
Train data service for generating and processing train information.

This service handles the creation of realistic train data from route calculations,
including calling points, timing, and service details.
"""

import logging
import random
from datetime import datetime, timedelta
from typing import List, Optional, Dict

from ...models.train_data import TrainData, TrainStatus, ServiceType, CallingPoint

logger = logging.getLogger(__name__)


class TrainDataService:
    """Service for generating and processing train data."""

    def __init__(self, config=None):
        """
        Initialize train data service.

        Args:
            config: Application configuration
        """
        self.config = config
        
        # CRASH FIX: Cache JsonDataRepository to prevent multiple instances
        # Each instance loads 72 railway lines and 859 stations from disk
        # Multiple instances during train generation cause memory pressure and crashes
        self._data_repo_cache = None
        self._underground_handler_cache = None

    def generate_trains_from_route(self, route_result, from_station: str, to_station: str,
                                  departure_time: datetime, max_trains: int = 100) -> List[TrainData]:
        """
        Generate realistic train services based on route calculation.

        Args:
            route_result: Route calculation result
            from_station: Origin station name
            to_station: Destination station name
            departure_time: Starting departure time
            max_trains: Maximum number of trains to generate

        Returns:
            List of generated train data
        """
        try:
            
            if not route_result:
                logger.warning("No route result provided for train generation")
                return []

            logger.info(f"Generating trains for route: {from_station} -> {to_station}")

            # Get time window from config
            time_window_hours = self._get_time_window_hours()
            
            trains = []
            current_time = departure_time
            train_count = 0
            
            
            # Generate trains at realistic intervals
            while train_count < max_trains and current_time < departure_time + timedelta(hours=time_window_hours):
                
                train_data = self._create_train_from_route(
                    route_result, from_station, to_station, current_time, train_count
                )
                
                
                if train_data:
                    trains.append(train_data)
                    train_count += 1
                
                # Next train at standard intervals (10-20 minutes)
                interval_minutes = random.randint(10, 20)
                current_time += timedelta(minutes=interval_minutes)

            logger.info(f"Generated {len(trains)} realistic trains")
            return trains
            
        except Exception as e:
            raise

    def _create_train_from_route(self, route_result, from_station: str, to_station: str,
                                departure_time: datetime, train_index: int) -> Optional[TrainData]:
        """Create a realistic TrainData object from route calculation."""
        try:
            # Validate route result has required properties
            if not hasattr(route_result, 'total_journey_time_minutes') or not route_result.total_journey_time_minutes:
                logger.error("Route result missing journey time")
                return None

            # Calculate arrival time
            arrival_time = departure_time + timedelta(minutes=route_result.total_journey_time_minutes)
            
            # Determine service type based on route complexity
            service_type = self._determine_service_type(route_result)
            
            # Generate realistic operator (check for Underground routes first)
            operator = self._select_operator_for_route(route_result, train_index)
            
            # Generate unique identifiers
            service_id = f"SVC{train_index+1:03d}{departure_time.strftime('%H%M')}"
            train_uid = f"T{train_index+1:05d}"
            
            # Generate platform (1-12)
            platform = str((train_index % 12) + 1)
            
            # All trains are on time for simplicity
            train_status = TrainStatus.ON_TIME
            delay_minutes = 0
            
            # Calculate journey duration
            journey_duration = arrival_time - departure_time
            
            # Generate calling points from route
            calling_points = self._generate_calling_points_from_route(
                route_result, from_station, to_station, departure_time, arrival_time
            )
            
            train_data = TrainData(
                departure_time=departure_time,
                scheduled_departure=departure_time,
                destination=to_station,
                platform=platform,
                operator=operator,
                service_type=service_type,
                status=train_status,
                delay_minutes=delay_minutes,
                estimated_arrival=arrival_time,
                journey_duration=journey_duration,
                current_location=None,
                train_uid=train_uid,
                service_id=service_id,
                calling_points=calling_points,
                route_segments=getattr(route_result, 'segments', [])
            )
            
            # Debug logging for route segments
            if train_data.route_segments:
                logger.debug(f"Attached {len(train_data.route_segments)} route segments to train {service_id}")
                for i, segment in enumerate(train_data.route_segments):
                    segment_from = getattr(segment, 'from_station', 'UNKNOWN')
                    segment_to = getattr(segment, 'to_station', 'UNKNOWN')
                    line_name = getattr(segment, 'line_name', 'UNKNOWN')
                    service_pattern = getattr(segment, 'service_pattern', 'NONE')
                    logger.debug(f"  Segment {i}: {segment_from} -> {segment_to} (line: {line_name}, service_pattern: {service_pattern})")
            
            return train_data
            
        except Exception as e:
            logger.error(f"Error creating train from route: {e}")
            return None

    def _determine_service_type(self, route_result) -> ServiceType:
        """Determine service type based on route characteristics."""
        if not hasattr(route_result, 'changes_required'):
            return ServiceType.FAST
            
        changes = route_result.changes_required
        distance = getattr(route_result, 'total_distance_km', 0)
        
        if changes == 0:
            return ServiceType.EXPRESS if distance and distance > 50 else ServiceType.FAST
        elif changes <= 2:
            return ServiceType.FAST
        else:
            return ServiceType.STOPPING

    def _select_operator(self, train_index: int) -> str:
        """Select realistic operator based on train index."""
        operators = [
            "Great Western Railway",
            "South Western Railway",
            "Southern",
            "CrossCountry",
            "Chiltern Railways"
        ]
        return operators[train_index % len(operators)]

    def _select_operator_for_route(self, route_result, train_index: int) -> str:
        """Select appropriate operator based on route type (Underground vs National Rail)."""
        # Check if this is an Underground-only route
        if hasattr(route_result, 'segments') and route_result.segments:
            # Check if all segments are Underground
            underground_segments = 0
            total_segments = 0
            
            for segment in route_result.segments:
                if hasattr(segment, 'service_pattern'):
                    total_segments += 1
                    if getattr(segment, 'service_pattern', '') == 'UNDERGROUND':
                        underground_segments += 1
            
            # If all segments are Underground, use Underground operator
            if total_segments > 0 and underground_segments == total_segments:
                logger.debug(f"Route has {underground_segments}/{total_segments} Underground segments - using Underground operator")
                return "London Underground"
        
        # For mixed or National Rail routes, use regular operator selection
        return self._select_operator(train_index)

    def _generate_calling_points_from_route(self, route_result, from_station: str, to_station: str,
                                           departure_time: datetime, arrival_time: datetime) -> List[CallingPoint]:
        """Generate calling points from route calculation."""
        calling_points = []
        
        # Add origin
        origin_point = CallingPoint(
            station_name=from_station,
            scheduled_arrival=None,
            scheduled_departure=departure_time,
            expected_arrival=None,
            expected_departure=departure_time,
            platform=None,
            is_origin=True,
            is_destination=False
        )
        calling_points.append(origin_point)
        
        # Get intermediate stations from route
        intermediate_stations = self._extract_intermediate_stations(route_result, from_station, to_station)
        
        # Add intermediate stations as calling points
        if intermediate_stations:
            logger.debug(f"Creating calling points for {len(intermediate_stations)} intermediate stations")
            total_journey_time = (arrival_time - departure_time).total_seconds() / 60  # minutes
            
            # Get segments for walking connection detection
            segments = getattr(route_result, 'segments', [])
            
            for i, station_name in enumerate(intermediate_stations):
                # Calculate proportional time for this station
                progress = (i + 1) / (len(intermediate_stations) + 1)
                station_time = departure_time + timedelta(minutes=int(total_journey_time * progress))
                
                # Add 2-minute stop duration
                stop_duration = timedelta(minutes=2)
                
                # Check for walking connections and add walking info if needed
                display_name = self._process_walking_connections(
                    station_name, segments, calling_points, station_time
                )
                
                intermediate_point = CallingPoint(
                    station_name=display_name,
                    scheduled_arrival=station_time,
                    scheduled_departure=station_time + stop_duration,
                    expected_arrival=station_time,
                    expected_departure=station_time + stop_duration,
                    platform=None,
                    is_origin=False,
                    is_destination=False
                )
                calling_points.append(intermediate_point)
        
        # Add destination
        destination_point = CallingPoint(
            station_name=to_station,
            scheduled_arrival=arrival_time,
            scheduled_departure=None,
            expected_arrival=arrival_time,
            expected_departure=None,
            platform=None,
            is_origin=False,
            is_destination=True
        )
        calling_points.append(destination_point)
        
        logger.debug(f"Generated {len(calling_points)} calling points for train")
        return calling_points

    def _extract_intermediate_stations(self, route_result, from_station: str, to_station: str) -> List[str]:
        from .train_data_components.intermediate_stations import extract_intermediate_stations

        return extract_intermediate_stations(
            service=self,
            route_result=route_result,
            from_station=from_station,
            to_station=to_station,
        )

    def _should_show_station_in_calling_points(self, station_name: str) -> bool:
        """
        Determine if a station should be shown in calling points.
        
        Args:
            station_name: The station name to check
            
        Returns:
            True if the station should be shown, False if it should be hidden (Underground black box)
        """
        # Always show major London terminals even if they're Underground stations
        london_terminals = [
            "London Waterloo", "London Liverpool Street", "London Victoria",
            "London Paddington", "London Kings Cross", "London St Pancras",
            "London Euston", "London Bridge", "London Charing Cross",
            "London Cannon Street", "London Fenchurch Street", "London Marylebone"
        ]
        
        if station_name in london_terminals:
            return True
        
        # Try to load Underground stations to check if this is Underground-only
        try:
            
            # CRASH FIX: Use cached instances to prevent repeated JSON loading
            # Creating new JsonDataRepository instances for each station check
            # causes massive memory pressure (72 lines + 859 stations loaded repeatedly)
            if self._data_repo_cache is None:
                from ...core.services.json_data_repository import JsonDataRepository
                self._data_repo_cache = JsonDataRepository()
            
            if self._underground_handler_cache is None:
                from ...core.services.underground_routing_handler import UndergroundRoutingHandler
                self._underground_handler_cache = UndergroundRoutingHandler(self._data_repo_cache)
            
            # If it's an Underground-only station (not mixed), hide it
            if self._underground_handler_cache.is_underground_only_station(station_name):
                logger.debug(f"Hiding Underground-only station from calling points: {station_name}")
                return False
            
        except Exception as e:
            logger.warning(f"Could not check Underground status for {station_name}: {e}")
        
        # Default: show the station
        return True

    def _extract_transfer_stations(self, segments, existing_stations: List[str],
                                  from_station: str, to_station: str) -> List[str]:
        """Extract transfer stations from route segments."""
        transfer_stations = []
        
        for i, segment in enumerate(segments):
            if not hasattr(segment, 'to_station'):
                continue
                
            station_name = segment.to_station
            
            # Skip if already in existing stations or is origin/destination
            if (station_name in existing_stations or 
                station_name == from_station or 
                station_name == to_station):
                continue
            
            # Check if this is a transfer point (line change)
            if i < len(segments) - 1:
                next_segment = segments[i + 1]
                current_line = getattr(segment, 'line_name', '')
                next_line = getattr(next_segment, 'line_name', '')
                
                # If line changes and it's not a walking connection, it's a transfer
                if (current_line != next_line and 
                    current_line != 'WALKING' and 
                    next_line != 'WALKING'):
                    transfer_stations.append(station_name)
                    logger.info(f"Found transfer station: {station_name} (change from {current_line} to {next_line})")
        
        return transfer_stations

    def _find_insert_position(self, transfer_station: str, intermediate_stations: List[str],
                             segments) -> int:
        """Find correct position to insert transfer station."""
        # Find position based on segment order
        for i, segment in enumerate(segments):
            if hasattr(segment, 'to_station') and segment.to_station == transfer_station:
                return min(i, len(intermediate_stations))
        
        return len(intermediate_stations)  # Default to end

    def _process_walking_connections(self, station_name: str, segments, calling_points: List[CallingPoint],
                                   station_time: datetime) -> str:
        from .train_data_components.walking_display import process_walking_connection_display

        return process_walking_connection_display(
            service=self,
            station_name=station_name,
            segments=segments,
            calling_points=calling_points,
            station_time=station_time,
        )

    def process_train_data(self, trains: List[TrainData]) -> List[TrainData]:
        from .train_data_components.post_processing import process_train_data

        return process_train_data(trains=trains)

    def _get_time_window_hours(self) -> int:
        """Get time window hours from config with fallback."""
        if not self.config:
            return 8  # Default fallback
            
        # Try configurable preference first
        time_window = getattr(self.config, 'train_lookahead_hours', None)
        if time_window is not None:
            return time_window
            
        # Fallback to display config
        if hasattr(self.config, 'display') and hasattr(self.config.display, 'time_window_hours'):
            return self.config.display.time_window_hours
            
        return 8  # Final fallback
    
    def _get_underground_indicator_for_segment(self, segment) -> str:
        """Get system-specific underground indicator for a segment."""
        try:
            # Non-UI formatter to avoid layering violations.
            from ..formatters.underground_formatter import UndergroundFormatter

            formatter = UndergroundFormatter()
            indicator = formatter.format_indicator_html(segment)
            if indicator:
                return indicator
        except Exception as e:
            logger.warning(f"Error getting underground system info for segment: {e}")

        # Fallback to generic underground indicator.
        return "<font color='#DC241F'>🚇 Underground (10-40min)</font>"
