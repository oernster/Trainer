"""
Interchange Detection Service

This service provides intelligent detection of actual user journey interchanges,
distinguishing between stations where users must change trains versus stations
that simply serve multiple lines.
"""

import logging
from typing import List, Optional, Dict, Any, Set
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import json
import math
import threading

logger = logging.getLogger(__name__)


class InterchangeType(Enum):
    """Types of interchange connections."""
    TRAIN_CHANGE = "train_change"  # User must change trains
    PLATFORM_CHANGE = "platform_change"  # User changes platforms but not trains
    THROUGH_SERVICE = "through_service"  # Same train continues with different line name
    WALKING_CONNECTION = "walking_connection"  # Walking between stations


@dataclass
class InterchangePoint:
    """Represents a point where a user may need to change during their journey."""
    station_name: str
    from_line: str
    to_line: str
    interchange_type: InterchangeType
    walking_time_minutes: int
    is_user_journey_change: bool
    coordinates: Optional[Dict[str, float]] = None
    description: str = ""


class InterchangeDetectionService:
    """Service for detecting actual user journey interchanges."""
    
    _instance: Optional['InterchangeDetectionService'] = None
    _instance_lock = threading.Lock()
    
    def __new__(cls):
        """Implement singleton pattern to prevent multiple expensive initializations."""
        if cls._instance is None:
            with cls._instance_lock:
                # Double-check pattern
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize the interchange detection service with lazy loading (singleton-safe)."""
        # Prevent re-initialization of singleton
        if hasattr(self, '_initialized'):
            return
            
        self.logger = logging.getLogger(__name__)
        
        # Cache for performance - all initialized as None for lazy loading
        self._station_coordinates_cache: Optional[Dict[str, Dict[str, float]]] = None
        self._line_to_file_cache: Optional[Dict[str, str]] = None
        self._station_to_files_cache: Optional[Dict[str, List[str]]] = None
        self._line_interchanges_cache: Optional[Dict[str, List[Dict[str, Any]]]] = None
        
        # Thread locks for safe lazy loading
        self._coordinates_lock = threading.Lock()
        self._line_mapping_lock = threading.Lock()
        self._station_mapping_lock = threading.Lock()
        self._interchanges_lock = threading.Lock()
        
        # Mark as initialized
        self._initialized = True
        
        self.logger.info("InterchangeDetectionService singleton initialized with lazy loading")
    
    def _get_line_interchanges(self) -> Dict[str, List[Dict[str, Any]]]:
        from .interchange_components.line_interchanges_loading import get_line_interchanges

        return get_line_interchanges(service=self)
    
    def detect_user_journey_interchanges(self, route_segments: List[Any]) -> List[InterchangePoint]:
        from .interchange_components.interchange_analysis import (
            detect_user_journey_interchanges,
        )

        return detect_user_journey_interchanges(service=self, route_segments=route_segments)
    
    def _analyze_interchange(self, station_name: str, from_line: str, to_line: str,
                           current_segment: Any, next_segment: Any) -> Optional[InterchangePoint]:
        from .interchange_components.interchange_analysis import analyze_interchange

        # Provide dataclass/enum access for the helper module.
        self.InterchangePoint = InterchangePoint
        self.InterchangeType = InterchangeType

        return analyze_interchange(
            service=self,
            station_name=station_name,
            from_line=from_line,
            to_line=to_line,
            current_segment=current_segment,
            next_segment=next_segment,
        )
    
    def _is_known_through_service(self, line1: str, line2: str, station_name: str) -> bool:
        from .interchange_components.journey_change_logic import is_known_through_service

        return is_known_through_service(
            service=self,
            line1=line1,
            line2=line2,
            station_name=station_name,
        )
    
    def _is_meaningful_user_journey_change(self, from_line: str, to_line: str, station_name: str,
                                          current_segment: Any, next_segment: Any) -> bool:
        from .interchange_components.journey_change_logic import (
            is_meaningful_user_journey_change,
        )

        return is_meaningful_user_journey_change(
            service=self,
            from_line=from_line,
            to_line=to_line,
            station_name=station_name,
            current_segment=current_segment,
            next_segment=next_segment,
        )
    
    def _is_continuous_train_service(self, from_line: str, to_line: str, station_name: str) -> bool:
        from .interchange_components.journey_change_logic import is_continuous_train_service

        return is_continuous_train_service(
            service=self,
            from_line=from_line,
            to_line=to_line,
            station_name=station_name,
        )
    
    def _is_through_station_for_journey(self, station_name: str, from_line: str, to_line: str,
                                       current_segment: Any, next_segment: Any) -> bool:
        from .interchange_components.journey_change_logic import is_through_station_for_journey

        return is_through_station_for_journey(
            service=self,
            station_name=station_name,
            from_line=from_line,
            to_line=to_line,
            current_segment=current_segment,
            next_segment=next_segment,
        )
    
    def _is_json_file_line_change(self, line1: str, line2: str) -> bool:
        from .interchange_components.journey_change_logic import is_json_file_line_change

        return is_json_file_line_change(service=self, line1=line1, line2=line2)
    
    def _is_valid_interchange_geographically(self, station_name: str, from_line: str, to_line: str) -> bool:
        """
        Validate that an interchange is geographically legitimate.
        
        Args:
            station_name: Station where the interchange occurs
            from_line: Incoming line
            to_line: Outgoing line
            
        Returns:
            True if this is a valid interchange based on geographic constraints
        """
        try:
            # Get station coordinates
            station_coordinates = self._get_station_coordinates()
            
            if station_name not in station_coordinates:
                self.logger.debug(f"Missing coordinates for station: {station_name}")
                return True  # Conservative: allow if we can't validate
            
            # Get the line-to-file mapping
            line_to_file = self._get_line_to_json_file_mapping()
            
            file1 = line_to_file.get(from_line)
            file2 = line_to_file.get(to_line)
            
            if not file1 or not file2:
                self.logger.debug(f"Could not find JSON files for lines: {from_line} -> {file1}, {to_line} -> {file2}")
                return True  # Conservative: allow if we can't validate
            
            # Check if the station appears in both JSON files
            station_to_files = self._get_station_to_json_files_mapping()
            station_files = station_to_files.get(station_name, [])
            
            if file1 in station_files and file2 in station_files:
                self.logger.debug(f"Valid interchange: {station_name} appears in both {file1} and {file2}")
                return True
            else:
                self.logger.debug(f"Invalid interchange: {station_name} not in both files. Found in: {station_files}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error in geographic validation: {e}")
            return True  # Conservative: allow if validation fails
    
    def _calculate_interchange_walking_time(self, station_name: str, from_line: str, to_line: str) -> int:
        """Calculate estimated walking time for an interchange using data-driven approach."""
        try:
            # Try to use data path resolver
            try:
                from ...utils.data_path_resolver import get_data_directory
                data_dir = get_data_directory()
            except (ImportError, FileNotFoundError):
                # Fallback to old method
                data_dir = Path(__file__).parent.parent.parent / "data"
            
            interchange_file = data_dir / "interchange_connections.json"
            
            if not interchange_file.exists():
                self.logger.error(f"Interchange connections file not found: {interchange_file}")
                return 5  # Default time if file not found
            
            with open(interchange_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                # Check connections for walking times
                connections = data.get('connections', [])
                for connection in connections:
                    from_station = connection.get('from_station', '')
                    to_station = connection.get('to_station', '')
                    time_minutes = connection.get('time_minutes', 0)
                    
                    if station_name in [from_station, to_station]:
                        return time_minutes
                
                # Default interchange times based on line types
                if 'Underground' in from_line or 'Underground' in to_line:
                    return 3  # Underground interchanges are typically faster
                elif 'Express' in from_line or 'Express' in to_line:
                    return 8  # Express services often use different platforms
                else:
                    return 5  # Standard interchange time
                    
        except Exception as e:
            self.logger.error(f"Error calculating interchange walking time: {e}")
            return 5  # Default time if error occurs
    
    def _get_station_coordinates(self) -> Dict[str, Dict[str, float]]:
        """Get station coordinates from JSON files with thread-safe lazy loading."""
        if self._station_coordinates_cache is not None:
            return self._station_coordinates_cache
        
        with self._coordinates_lock:
            # Double-check pattern to prevent race conditions
            if self._station_coordinates_cache is not None:
                return self._station_coordinates_cache
            
            self.logger.debug("Loading station coordinates (lazy loading)")
            self._station_coordinates_cache = self._build_station_coordinates_mapping()
            return self._station_coordinates_cache
    
    def _build_station_coordinates_mapping(self) -> Dict[str, Dict[str, float]]:
        from .interchange_components.coordinates_mapping import (
            build_station_coordinates_mapping,
        )

        return build_station_coordinates_mapping(logger=self.logger)
    
    def _get_line_to_json_file_mapping(self) -> Dict[str, str]:
        """Create a mapping of line names to their JSON file names with thread-safe lazy loading."""
        if self._line_to_file_cache is not None:
            return self._line_to_file_cache
        
        with self._line_mapping_lock:
            # Double-check pattern to prevent race conditions
            if self._line_to_file_cache is not None:
                return self._line_to_file_cache
            
            self.logger.debug("Loading line-to-file mapping (lazy loading)")
            self._line_to_file_cache = self._build_line_to_file_mapping()
            return self._line_to_file_cache
    
    def _build_line_to_file_mapping(self) -> Dict[str, str]:
        from .interchange_components.mappings import build_line_to_file_mapping

        return build_line_to_file_mapping(logger=self.logger)
    
    def _add_service_variations(self, line_to_file: Dict[str, str], file_name: str):
        # Kept for backwards compatibility. Implementation moved.
        from .interchange_components.mappings import _add_service_variations

        _add_service_variations(line_to_file, file_name)
    
    def _get_station_to_json_files_mapping(self) -> Dict[str, List[str]]:
        """Create a mapping of station names to the JSON files they appear in with thread-safe lazy loading."""
        if self._station_to_files_cache is not None:
            return self._station_to_files_cache
        
        with self._station_mapping_lock:
            # Double-check pattern to prevent race conditions
            if self._station_to_files_cache is not None:
                return self._station_to_files_cache
            
            self.logger.debug("Loading station-to-files mapping (lazy loading)")
            self._station_to_files_cache = self._build_station_to_files_mapping()
            return self._station_to_files_cache
    
    def _build_station_to_files_mapping(self) -> Dict[str, List[str]]:
        from .interchange_components.mappings import build_station_to_files_mapping

        return build_station_to_files_mapping(logger=self.logger)
    
    def validate_interchange_necessity(self, from_line: str, to_line: str, station: str) -> bool:
        """
        Validate if an interchange is necessary for the user's journey.
        
        Args:
            from_line: Line the user is coming from
            to_line: Line the user is going to
            station: Station where the potential interchange occurs
            
        Returns:
            True if the user must actually change trains at this station
        """
        # Same line = no change needed
        if from_line == to_line:
            return False
        
        # Check if it's a through service
        if self._is_known_through_service(from_line, to_line, station):
            return False
        
        # Check if it's the same network (same JSON file)
        if not self._is_json_file_line_change(from_line, to_line):
            return False
        
        # If we get here, it's likely a real interchange
        return True
    
    def get_station_line_mappings(self) -> Dict[str, List[str]]:
        """Get mapping of stations to the lines that serve them."""
        station_to_lines = {}
        line_to_file = self._get_line_to_json_file_mapping()
        
        # Reverse the mapping to get file to lines
        file_to_lines = {}
        for line, file in line_to_file.items():
            if file not in file_to_lines:
                file_to_lines[file] = []
            file_to_lines[file].append(line)
        
        # Get station to files mapping
        station_to_files = self._get_station_to_json_files_mapping()
        
        # Build station to lines mapping
        for station, files in station_to_files.items():
            lines = []
            for file in files:
                if file in file_to_lines:
                    lines.extend(file_to_lines[file])
            station_to_lines[station] = list(set(lines))  # Remove duplicates
        
        return station_to_lines
    
    def clear_cache(self):
        """Clear all cached data to force reload with thread safety."""
        with self._coordinates_lock:
            self._station_coordinates_cache = None
        with self._line_mapping_lock:
            self._line_to_file_cache = None
        with self._station_mapping_lock:
            self._station_to_files_cache = None
        with self._interchanges_lock:
            self._line_interchanges_cache = None
        
        self.logger.debug("InterchangeDetectionService cache cleared")
    
    def _are_stations_on_same_line(self, line1: str, line2: str) -> bool:
        """
        Check if two lines are effectively the same line (same physical train service).
        This is a stronger check than just comparing line names, as it accounts for
        lines that are operationally the same but have different names.
        """
        # If the line names are identical, they're definitely the same line
        if line1 == line2:
            return True
            
        # Check if these lines are part of the same network (same JSON file)
        if not self._is_json_file_line_change(line1, line2):
            return True
            
        # Check all stations for continuous services between these lines
        line_interchanges = self._get_line_interchanges()
        for station, connections in line_interchanges.items():
            for connection in connections:
                connection_from_line = connection.get("from_line", "")
                connection_to_line = connection.get("to_line", "")
                requires_change = connection.get("requires_change", True)
                
                if not requires_change and (
                    (connection_from_line == line1 and connection_to_line == line2) or
                    (connection_from_line == line2 and connection_to_line == line1)
                ):
                    return True
        
        # Known line pairs that are operationally the same
        same_line_pairs = [
            ("South Western Main Line", "South Western Railway"),
            ("Great Western Main Line", "Great Western Railway"),
            ("Cross Country Line", "Cross Country")
        ]
        
        for pair in same_line_pairs:
            if (line1 in pair and line2 in pair):
                return True
                
        return False
    
    def _calculate_haversine_distance(self, coord1: Dict[str, float], coord2: Dict[str, float]) -> float:
        """
        Calculate the great-circle distance between two points on Earth using Haversine formula.
        Returns distance in kilometers.
        
        Args:
            coord1: Dictionary with 'lat' and 'lng' keys
            coord2: Dictionary with 'lat' and 'lng' keys
            
        Returns:
            Distance in kilometers
        """
        # Extract coordinates
        lat1 = coord1.get('lat', 0)
        lon1 = coord1.get('lng', 0)
        lat2 = coord2.get('lat', 0)
        lon2 = coord2.get('lng', 0)
        
        # Convert to radians
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        
        # Haversine formula
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        # Earth radius in kilometers
        r = 6371
        return c * r
