"""
JSON Data Repository Implementation

Repository implementation for loading railway data from JSON files.
"""

import json
import os
import logging
from typing import List, Optional, Dict, Any, Set
from pathlib import Path
from datetime import datetime
import shutil

from src.core.interfaces.i_data_repository import IDataRepository
from src.core.models.station import Station
from src.core.models.railway_line import RailwayLine, LineType, LineStatus

from version import __routing_data_version__


class JsonDataRepository(IDataRepository):
    """Repository implementation for JSON-based railway data."""
    
    def __init__(self, data_directory: Optional[str] = None):
        """
        Initialize the JSON data repository.
        
        Args:
            data_directory: Path to directory containing JSON data files
        """
        try:
            from ...utils.data_path_resolver import get_data_directory
            if data_directory is None:
                self.data_directory = get_data_directory()
            else:
                self.data_directory = Path(data_directory)
        except ImportError:
            # Fallback for standalone execution
            import os
            if data_directory is None:
                data_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'data')
                self.data_directory = Path(data_dir)
            else:
                self.data_directory = Path(data_directory)
        
        self.lines_directory = self.data_directory / "lines"
        self.logger = logging.getLogger(__name__)
        
        # Cache for loaded data
        self._stations_cache: Optional[List[Station]] = None
        self._railway_lines_cache: Optional[List[RailwayLine]] = None
        self._station_name_to_station: Optional[Dict[str, Station]] = None
        self._line_name_to_line: Optional[Dict[str, RailwayLine]] = None
        
        # Data version and metadata
        self._data_version = __routing_data_version__
        self._last_loaded: Optional[datetime] = None
        
        self.logger.info(f"Initialized JsonDataRepository with data directory: {self.data_directory}")
    
    def _ensure_data_loaded(self) -> None:
        """Ensure data is loaded into cache."""
        if self._stations_cache is None or self._railway_lines_cache is None:
            self._load_all_data()
    
    def _load_all_data(self) -> None:
        """Load all data from JSON files."""
        self.logger.info("Loading railway data from JSON files...")
        
        try:
            # Load railway lines first
            self._railway_lines_cache = self._load_railway_lines_from_json()
            
            self._line_name_to_line = {line.name: line for line in self._railway_lines_cache}
            
            # Extract stations from railway lines
            self._stations_cache = self._extract_stations_from_lines()
            
            self._station_name_to_station = {station.name: station for station in self._stations_cache}
            
            self._last_loaded = datetime.now()
            self.logger.info(f"Loaded {len(self._stations_cache)} stations and {len(self._railway_lines_cache)} railway lines")
            
        except json.JSONDecodeError as e:
            self.logger.critical(f"JSON parsing failed at line {e.lineno}, column {e.colno}: {e}")
            # Initialize empty caches to prevent further crashes
            self._railway_lines_cache = []
            self._stations_cache = []
            self._line_name_to_line = {}
            self._station_name_to_station = {}
            # Don't re-raise - let the application continue with empty data
        except Exception as e:
            # Initialize empty caches to prevent further crashes
            self._railway_lines_cache = []
            self._stations_cache = []
            self._line_name_to_line = {}
            self._station_name_to_station = {}
            # Don't re-raise - let the application continue with empty data
    
    def _load_railway_lines_from_json(self) -> List[RailwayLine]:
        from .json_data_components.railway_lines_loading import load_railway_lines_from_json

        return load_railway_lines_from_json(repo=self)
    
    def _parse_railway_line_json_with_index(self, line_info: Dict[str, Any], line_data: Dict[str, Any]) -> Optional[RailwayLine]:
        from .json_data_components.line_parsing import parse_railway_line_json_with_index

        return parse_railway_line_json_with_index(repo=self, line_info=line_info, line_data=line_data)
    
    def _parse_railway_line_json_from_file(self, file_name: str, data: Dict[str, Any]) -> Optional[RailwayLine]:
        from .json_data_components.line_parsing import parse_railway_line_json_from_file

        return parse_railway_line_json_from_file(repo=self, file_name=file_name, data=data)
    
    def _parse_railway_line_json(self, line_name: str, data: Dict[str, Any]) -> Optional[RailwayLine]:
        from .json_data_components.railway_line_parsing import parse_railway_line_json

        return parse_railway_line_json(repo=self, line_name=line_name, data=data)
    
    def _determine_line_type(self, line_name: str) -> LineType:
        """Determine line type based on line name."""
        line_name_lower = line_name.lower()
        
        if "branch" in line_name_lower:
            return LineType.BRANCH
        elif any(keyword in line_name_lower for keyword in ["metro", "underground", "tube"]):
            return LineType.METRO
        elif any(keyword in line_name_lower for keyword in ["suburban", "local"]):
            return LineType.SUBURBAN
        elif any(keyword in line_name_lower for keyword in ["heritage", "preserved"]):
            return LineType.HERITAGE
        else:
            return LineType.MAINLINE
    
    def _extract_stations_from_lines(self) -> List[Station]:
        """Extract unique stations from all railway lines."""
        if self._railway_lines_cache is None:
            return []
            
        station_data = {}
        
        for line in self._railway_lines_cache:
            for station_name in line.stations:
                if station_name not in station_data:
                    station_data[station_name] = {
                        'lines': [],
                        'is_terminus': False
                    }
                
                station_data[station_name]['lines'].append(line.name)
                
                # Check if this is a terminus station
                if station_name in line.terminus_stations:
                    station_data[station_name]['is_terminus'] = True
        
        # Create Station objects
        stations = []
        for station_name, data in station_data.items():
            # Create station with interchange lines
            interchange_lines = data['lines'].copy() if len(data['lines']) > 1 else None
            
            station = Station(
                name=station_name,
                interchange=interchange_lines
            )
            
            stations.append(station)
        
        return stations
    
    def _is_major_station_by_name(self, station_name: str) -> bool:
        """Determine if a station is major based on its name."""
        major_keywords = [
            "central", "main", "terminus", "junction", "interchange",
            "airport", "international", "parkway", "cross"
        ]
        
        station_lower = station_name.lower()
        return any(keyword in station_lower for keyword in major_keywords)
    
    def _is_london_station(self, station_name: str) -> bool:
        """Determine if a station is in London based on its name."""
        london_keywords = [
            "london", "kings cross", "st pancras", "euston", "paddington",
            "victoria", "waterloo", "liverpool street", "marylebone",
            "fenchurch street", "cannon street", "blackfriars", "charing cross"
        ]
        
        station_lower = station_name.lower()
        return any(keyword in station_lower for keyword in london_keywords)
    
    # Interface implementation methods
    
    def load_stations(self) -> List[Station]:
        """Load all stations from the data source."""
        self._ensure_data_loaded()
        return self._stations_cache.copy() if self._stations_cache else []
    
    def load_railway_lines(self) -> List[RailwayLine]:
        """Load all railway lines from the data source."""
        self._ensure_data_loaded()
        return self._railway_lines_cache.copy() if self._railway_lines_cache else []
    
    def get_station_by_name(self, name: str) -> Optional[Station]:
        """Get a station by its name."""
        self._ensure_data_loaded()
        return self._station_name_to_station.get(name) if self._station_name_to_station else None
    
    def get_railway_line_by_name(self, name: str) -> Optional[RailwayLine]:
        """Get a railway line by its name."""
        self._ensure_data_loaded()
        return self._line_name_to_line.get(name) if self._line_name_to_line else None
    
    def get_stations_on_line(self, line_name: str) -> List[Station]:
        """Get all stations on a specific railway line."""
        line = self.get_railway_line_by_name(line_name)
        if not line:
            return []
        
        stations = []
        for station_name in line.stations:
            station = self.get_station_by_name(station_name)
            if station:
                stations.append(station)
        
        return stations
    
    def get_lines_serving_station(self, station_name: str) -> List[RailwayLine]:
        """Get all railway lines serving a specific station."""
        station = self.get_station_by_name(station_name)
        if not station:
            return []
        
        lines = []
        station_lines = station.get_lines()  # Use the get_lines() method
        for line_name in station_lines:
            line = self.get_railway_line_by_name(line_name)
            if line:
                lines.append(line)
        
        return lines
    
    def get_journey_time(self, from_station: str, to_station: str, 
                        line_name: str) -> Optional[int]:
        """Get journey time between two stations on a specific line."""
        line = self.get_railway_line_by_name(line_name)
        if not line:
            return None
        
        return line.get_journey_time(from_station, to_station)
    
    def get_distance(self, from_station: str, to_station: str,
                    line_name: str) -> Optional[float]:
        """Get distance between two stations on a specific line."""
        line = self.get_railway_line_by_name(line_name)
        if not line:
            return None
        
        return line.get_distance(from_station, to_station)
    
    def get_all_station_names(self) -> Set[str]:
        """Get all unique station names in the system."""
        self._ensure_data_loaded()
        return set(self._station_name_to_station.keys()) if self._station_name_to_station else set()
    
    def get_all_line_names(self) -> Set[str]:
        """Get all railway line names in the system."""
        self._ensure_data_loaded()
        return set(self._line_name_to_line.keys()) if self._line_name_to_line else set()
    
    def get_interchange_stations(self) -> List[Station]:
        """Get all stations that are interchanges."""
        self._ensure_data_loaded()
        if not self._stations_cache:
            return []
        return [station for station in self._stations_cache if station.is_interchange]
    
    def get_terminus_stations(self) -> List[Station]:
        """Get all stations that are terminus points."""
        self._ensure_data_loaded()
        if not self._stations_cache or not self._railway_lines_cache:
            return []
        
        terminus_stations = []
        for line in self._railway_lines_cache:
            for terminus_name in line.terminus_stations:
                station = self.get_station_by_name(terminus_name)
                if station and station not in terminus_stations:
                    terminus_stations.append(station)
        return terminus_stations
    
    def get_major_stations(self) -> List[Station]:
        """Get all major stations in the system."""
        self._ensure_data_loaded()
        if not self._stations_cache:
            return []
        return [station for station in self._stations_cache if station.is_major_station]
    
    def get_london_stations(self) -> List[Station]:
        """Get all stations in London."""
        self._ensure_data_loaded()
        if not self._stations_cache:
            return []
        return [station for station in self._stations_cache if station.is_london_station]
    
    def search_stations_by_name(self, query: str, limit: int = 10) -> List[Station]:
        """Search for stations by name using fuzzy matching."""
        self._ensure_data_loaded()
        
        if not self._stations_cache:
            return []
        
        query_lower = query.lower()
        matches = []
        
        for station in self._stations_cache:
            station_lower = station.name.lower()
            
            # Exact match gets highest priority
            if station_lower == query_lower:
                matches.append((station, 100))
            # Starts with query gets high priority
            elif station_lower.startswith(query_lower):
                matches.append((station, 90))
            # Contains query gets medium priority
            elif query_lower in station_lower:
                matches.append((station, 70))
            # Word boundary matches get lower priority
            elif any(word.startswith(query_lower) for word in station_lower.split()):
                matches.append((station, 50))
        
        # Sort by score (descending) and return top results
        matches.sort(key=lambda x: x[1], reverse=True)
        return [match[0] for match in matches[:limit]]
    
    def search_lines_by_name(self, query: str, limit: int = 10) -> List[RailwayLine]:
        """Search for railway lines by name using fuzzy matching."""
        self._ensure_data_loaded()
        
        if not self._railway_lines_cache:
            return []
        
        query_lower = query.lower()
        matches = []
        
        for line in self._railway_lines_cache:
            line_lower = line.name.lower()
            
            # Exact match gets highest priority
            if line_lower == query_lower:
                matches.append((line, 100))
            # Starts with query gets high priority
            elif line_lower.startswith(query_lower):
                matches.append((line, 90))
            # Contains query gets medium priority
            elif query_lower in line_lower:
                matches.append((line, 70))
            # Word boundary matches get lower priority
            elif any(word.startswith(query_lower) for word in line_lower.split()):
                matches.append((line, 50))
        
        # Sort by score (descending) and return top results
        matches.sort(key=lambda x: x[1], reverse=True)
        return [match[0] for match in matches[:limit]]
    
    def get_stations_near_location(self, latitude: float, longitude: float,
                                  radius_km: float = 10.0) -> List[Station]:
        """Get stations near a geographic location."""
        # This would require coordinate data which isn't available in current JSON structure
        self.logger.warning("Geographic search not implemented - coordinate data not available")
        return []
    
    def get_common_lines(self, station1: str, station2: str) -> List[RailwayLine]:
        """Get railway lines that serve both stations."""
        lines1 = self.get_lines_serving_station(station1)
        lines2 = self.get_lines_serving_station(station2)
        
        common_lines = []
        for line1 in lines1:
            for line2 in lines2:
                if line1.name == line2.name:
                    common_lines.append(line1)
                    break
        
        return common_lines
    
    def validate_station_exists(self, station_name: str) -> bool:
        """Check if a station exists in the system."""
        self._ensure_data_loaded()
        return (self._station_name_to_station is not None and
                station_name in self._station_name_to_station)
    
    def validate_line_exists(self, line_name: str) -> bool:
        """Check if a railway line exists in the system."""
        self._ensure_data_loaded()
        return (self._line_name_to_line is not None and
                line_name in self._line_name_to_line)
    
    def get_service_patterns(self, line_name: str) -> List[str]:
        """Get service patterns for a railway line."""
        line = self.get_railway_line_by_name(line_name)
        if not line or not line.service_patterns:
            return []
        return line.service_patterns.copy()
    
    def get_line_statistics(self, line_name: str) -> Dict[str, Any]:
        """Get statistics for a railway line."""
        line = self.get_railway_line_by_name(line_name)
        if not line:
            return {}
        
        return line.get_line_summary()
    
    def get_network_statistics(self) -> Dict[str, Any]:
        """Get overall network statistics."""
        self._ensure_data_loaded()
        
        return {
            "total_stations": len(self._stations_cache) if self._stations_cache else 0,
            "total_lines": len(self._railway_lines_cache) if self._railway_lines_cache else 0,
            "interchange_stations": len(self.get_interchange_stations()),
            "terminus_stations": len(self.get_terminus_stations()),
            "major_stations": len(self.get_major_stations()),
            "london_stations": len(self.get_london_stations()),
            "data_version": self._data_version,
            "last_loaded": self._last_loaded.isoformat() if self._last_loaded else None
        }
    
    def refresh_data(self) -> bool:
        """Refresh data from the source."""
        try:
            # Clear cache
            self._stations_cache = None
            self._railway_lines_cache = None
            self._station_name_to_station = None
            self._line_name_to_line = None
            
            # Reload data
            self._load_all_data()
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to refresh data: {e}")
            return False
    
    def get_data_version(self) -> str:
        """Get the version of the loaded data."""
        return self._data_version
    
    def get_last_updated(self) -> Optional[str]:
        """Get the last updated timestamp of the data."""
        return self._last_loaded.isoformat() if self._last_loaded else None
    
    def backup_data(self, backup_path: str) -> bool:
        """Create a backup of the current data."""
        try:
            backup_dir = Path(backup_path)
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy all JSON files to backup directory
            for json_file in self.data_directory.glob("*.json"):
                shutil.copy2(json_file, backup_dir / json_file.name)
            
            self.logger.info(f"Data backed up to: {backup_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to backup data: {e}")
            return False
    
    def restore_data(self, backup_path: str) -> bool:
        """Restore data from a backup."""
        try:
            backup_dir = Path(backup_path)
            if not backup_dir.exists():
                self.logger.error(f"Backup directory does not exist: {backup_path}")
                return False
            
            # Copy all JSON files from backup directory
            for json_file in backup_dir.glob("*.json"):
                shutil.copy2(json_file, self.data_directory / json_file.name)
            
            # Refresh data after restore
            self.refresh_data()
            
            self.logger.info(f"Data restored from: {backup_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to restore data: {e}")
            return False
