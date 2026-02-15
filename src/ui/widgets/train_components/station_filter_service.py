"""
Station filter service for train widget components.

This module provides a service for filtering and processing station information
for train displays, including identifying major stations and interchanges.
"""

import json
import logging
import os
from typing import List, Set, Dict, Optional

from PySide6.QtWidgets import QWidget
from .base_component import BaseTrainComponent
from ....ui.formatters.underground_formatter import UndergroundFormatter
from ....models.train_data import CallingPoint
from datetime import datetime

logger = logging.getLogger(__name__)


class StationFilterService(BaseTrainComponent):
    """
    Service for filtering and processing station information.
    
    Provides functionality to filter calling points, identify major stations,
    and detect interchange stations.
    """
    
    def __init__(self, train_data=None, parent: Optional[QWidget] = None):
        """
        Initialize station filter service.
        
        Args:
            train_data: Train data to process
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.train_data = train_data
        
        # Initialize Underground formatter for black box routing
        self.underground_formatter = UndergroundFormatter()
        
        # Load configuration files
        self.major_stations = self._load_major_stations()
        self.underground_system_indicators = self._load_underground_system_indicators()
    
    def set_train_data(self, train_data):
        """
        Set the train data to process.
        
        Args:
            train_data: Train data to process
        """
        self.train_data = train_data
    
    def _load_major_stations(self) -> set:
        """
        Load major stations from configuration file.
        
        Returns:
            Set of major station names
        """
        try:
            # Get the path to the data directory
            data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'data')
            file_path = os.path.join(data_dir, 'major_stations.json')
            
            with open(file_path, 'r') as f:
                data = json.load(f)
                return set(data.get('major_stations', []))
        except Exception as e:
            logger.error(f"Error loading major stations: {e}")
            # Fallback to empty set if file can't be loaded
            return set()
    
    def _load_underground_system_indicators(self) -> dict:
        """
        Load underground system indicators from configuration file.
        
        Returns:
            Dictionary of underground system indicators
        """
        try:
            # Get the path to the data directory
            data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'data')
            file_path = os.path.join(data_dir, 'underground_systems.json')
            
            with open(file_path, 'r') as f:
                data = json.load(f)
                return data.get('system_indicators', {})
        except Exception as e:
            logger.error(f"Error loading underground system indicators: {e}")
            # Fallback to empty dict if file can't be loaded
            return {}
    
    def filter_calling_points(self, calling_points: List[CallingPoint]) -> List[CallingPoint]:
        """
        Filter calling points to remove duplicates while preserving important ones.
        
        Args:
            calling_points: List of calling points to filter
            
        Returns:
            Filtered list of calling points
        """
        seen_stations = set()
        filtered_calling_points = []
        
        for calling_point in calling_points:
            station_name = calling_point.station_name.strip() if calling_point.station_name else ""
            if station_name not in seen_stations:
                seen_stations.add(station_name)
                filtered_calling_points.append(calling_point)
            else:
                # If we've seen this station before, check if this one is more important
                for j, existing_cp in enumerate(filtered_calling_points):
                    if existing_cp.station_name == station_name:
                        # Prefer origin/destination over intermediate, or one with platform info
                        if (calling_point.is_origin or calling_point.is_destination or
                            (calling_point.platform and not existing_cp.platform)):
                            filtered_calling_points[j] = calling_point
                        break
        
        return filtered_calling_points
    
    def filter_for_essential_stations_only(self, calling_points: List[CallingPoint]) -> List[CallingPoint]:
        """
        Filter calling points to show only origin, destination, key interchange stations,
        London terminus stations, and underground indicators.
        
        Args:
            calling_points: List of calling points to filter
            
        Returns:
            Filtered list of essential calling points
        """
        if not self.train_data:
            return calling_points
            
        essential_calling_points = []
        
        # Always include origin and destination
        origin = None
        destination = None
        
        # Find origin and destination
        for cp in calling_points:
            if cp.is_origin:
                origin = cp
            elif cp.is_destination:
                destination = cp
        
        # Add origin if found
        if origin:
            essential_calling_points.append(origin)
        
        # Include interchange stations and major stations
        for calling_point in calling_points:
            if calling_point.is_origin or calling_point.is_destination:
                continue  # Already handled
                
            station_name = calling_point.station_name.strip() if calling_point.station_name else ""
            
            # Include Reading as it's a key interchange
            if "Reading" in station_name:
                essential_calling_points.append(calling_point)
                continue
                
            # Include interchange stations (where user changes trains)
            if self.is_actual_user_journey_interchange(station_name):
                essential_calling_points.append(calling_point)
                continue
                
            # Include major stations
            if self.is_major_station(station_name):
                essential_calling_points.append(calling_point)
                continue
                
            # Include London terminus stations if we have underground segments
            if hasattr(self.train_data, 'route_segments') and self.train_data.route_segments:
                # Check if we have any underground segments
                has_underground = False
                for segment in self.train_data.route_segments:
                    if self.underground_formatter.is_underground_segment(segment):
                        has_underground = True
                        break
                
                if has_underground:
                    # List of London terminus stations
                    london_terminus_stations = [
                        "London Paddington", "London Liverpool Street", "London Waterloo",
                        "London Victoria", "London Bridge", "London Euston",
                        "London Kings Cross", "London St Pancras", "London Marylebone",
                        "London Charing Cross", "London Cannon Street", "London Blackfriars",
                        "London Fenchurch Street"
                    ]
                    
                    # Check if this is a London terminus station
                    if any(terminus in station_name for terminus in london_terminus_stations):
                        essential_calling_points.append(calling_point)
                        
                        # Add underground indicator after this terminus station
                        # Create a dummy datetime for the required parameters
                        now = datetime.now()
                        
                        # Get system-specific information
                        system_info = {}
                        for segment in self.train_data.route_segments:
                            if self.underground_formatter.is_underground_segment(segment):
                                system_info = self.underground_formatter.get_underground_system_info(segment)
                                break
                                
                        system_name = system_info.get("short_name", "Underground")
                        time_range = system_info.get("time_range", "10-40min")
                        emoji = system_info.get("emoji", "🚇")
                        
                        # Create underground indicator
                        underground_indicator = CallingPoint(
                            station_name=f"<font color='#DC241F'>{emoji} Use {system_name} ({time_range})</font>",
                            scheduled_arrival=now,
                            scheduled_departure=now,
                            expected_arrival=now,
                            expected_departure=now,
                            platform="",
                            is_origin=False,
                            is_destination=False
                        )
                        
                        # Add underground indicator after this terminus station
                        essential_calling_points.append(underground_indicator)
        
        # Add destination if found and not already in the list
        if destination and destination not in essential_calling_points:
            essential_calling_points.append(destination)
        
        return essential_calling_points
    
    def is_major_station(self, station_name: str) -> bool:
        """
        Check if a station is considered a major station that should always be shown.
        
        Args:
            station_name: Name of the station to check
            
        Returns:
            True if the station is a major station, False otherwise
        """
        # Check if this is an HTML-formatted station name
        is_html_formatted = "<font" in station_name and "</font>" in station_name
        
        # Process station name based on whether it's HTML-formatted
        if is_html_formatted:
            # For HTML-formatted names, we need to be careful
            # This is a simplified approach - a more robust solution would use HTML parsing
            processed_name = station_name
        else:
            # Trim any leading and trailing spaces from the station name
            processed_name = station_name.strip() if station_name else ""
        
        # Use the loaded major stations list from configuration file
        return processed_name in self.major_stations
    
    def is_actual_user_journey_interchange(self, station_name: str) -> bool:
        """
        Determine if a station is an actual interchange where the user changes trains.
        
        Two-step logic:
        STEP 1: IF user changes lines → Mark as interchange
        STEP 2: IF user changes lines BUT stays on same physical train → Not an interchange
        
        Args:
            station_name: Name of the station to check
            
        Returns:
            True if the station is an actual interchange, False otherwise
        """
        if not self.train_data:
            return False
            
        # Check if this is an HTML-formatted station name
        is_html_formatted = "<font" in station_name and "</font>" in station_name
        
        # Process station name based on whether it's HTML-formatted
        if is_html_formatted:
            # For HTML-formatted names, we need to be careful with replacements
            # This is a simplified approach - a more robust solution would use HTML parsing
            clean_name = station_name.replace(" (Cross Country Line)", "")
        else:
            clean_name = station_name.replace(" (Cross Country Line)", "").strip()
        
        # Check if we have route segments to analyze
        if not hasattr(self.train_data, 'route_segments') or not self.train_data.route_segments:
            return False
        
        # STEP 1: Check if user changes lines at this station
        line_change_detected = False
        same_physical_train = False
        
        # Look for consecutive segments that connect at this station
        for i in range(len(self.train_data.route_segments) - 1):
            current_segment = self.train_data.route_segments[i]
            next_segment = self.train_data.route_segments[i + 1]
            
            # Check if this station connects two segments
            current_to = getattr(current_segment, 'to_station', '').strip()
            next_from = getattr(next_segment, 'from_station', '').strip()
            
            if current_to == clean_name and next_from == clean_name:
                # This station connects segments - check for line change
                current_line = getattr(current_segment, 'line_name', '')
                next_line = getattr(next_segment, 'line_name', '')
                
                if current_line != next_line:
                    line_change_detected = True
                    
                    # STEP 2: Check if it's the same physical train despite line change
                    current_train_id = getattr(current_segment, 'train_id', None)
                    next_train_id = getattr(next_segment, 'train_id', None)
                    
                    if current_train_id and next_train_id and current_train_id == next_train_id:
                        same_physical_train = True
        
        # Return True only if there's a line change AND it's not the same physical train
        return line_change_detected and not same_physical_train
    
    def get_underground_system_for_station(self, station_name: str) -> Optional[str]:
        """
        Get the underground system for a station if applicable.
        
        Args:
            station_name: Name of the station to check
            
        Returns:
            Underground system name or None if not an underground station
        """
        # This is a placeholder for future implementation
        # Currently, underground stations are identified by HTML formatting
        if "<font color='#DC241F'" in station_name:
            return "Underground"
        return None
