"""
Underground Terminal Manager

Handles operations related to terminal stations for underground systems.
"""

import logging
from typing import List, Optional, Tuple

from .station_classifier import StationClassifier
from .geographic_utils import GeographicUtils


class TerminalManager:
    """Handles operations related to terminal stations for underground systems."""
    
    def __init__(self, station_classifier: StationClassifier, geographic_utils: GeographicUtils):
        """
        Initialize the terminal manager.
        
        Args:
            station_classifier: Station classifier for checking station types
            geographic_utils: Geographic utilities for region-based operations
        """
        self.station_classifier = station_classifier
        self.geographic_utils = geographic_utils
        self.logger = logging.getLogger(__name__)
    
    def get_nearest_terminals(self, station_name: str) -> List[str]:
        """
        Get the nearest terminals to a given station based on its underground system.
        
        Args:
            station_name: The station name
            
        Returns:
            List of nearest terminal stations (ordered by preference)
        """
        system_info = self.station_classifier.get_underground_system(station_name)
        
        if not system_info:
            # Not an underground station, return London terminals as default
            return self.station_classifier.get_london_terminals()[:6]  # Top 6 London terminals
        
        system_key, system_name = system_info
        terminals = self.station_classifier.get_system_terminals(system_key)
        
        # For multi-system routing, we need National Rail terminals, not underground terminals
        # So we skip the check for underground terminals and go directly to system-specific logic
        
        if system_key == "london":
            # For London Underground stations
            if self.station_classifier.is_underground_only_station(station_name):
                # Return terminals in order of general preference
                return [
                    "London Waterloo",
                    "London Liverpool Street",
                    "London Victoria",
                    "London Paddington",
                    "London Kings Cross",
                    "London Bridge"
                ]
            else:
                # For mixed stations, return terminals that are likely to be well-connected
                return [
                    "London Waterloo",
                    "London Liverpool Street",
                    "London Victoria",
                    "London Paddington"
                ]
        elif system_key == "glasgow":
            # For Glasgow Subway, return National Rail interchange terminals
            return ["Glasgow Central", "Glasgow Queen Street", "Partick"]
        elif system_key == "tyne_wear":
            # For Tyne and Wear Metro, return main terminals
            return ["Central Station", "Sunderland", "South Shields", "Airport"]
        else:
            # Fallback to all terminals for the system
            return terminals
    
    def filter_underground_stations_from_path(self, path: List[str]) -> List[str]:
        """
        Filter out underground-only stations from a path, keeping only terminals and mixed stations.
        
        Args:
            path: List of station names in the path
            
        Returns:
            Filtered path with underground-only stations removed
        """
        filtered_path = []
        
        for station in path:
            # Keep the station if it's:
            # 1. Not an underground station at all
            # 2. A terminal station for any underground system
            # 3. A mixed station (serves both underground and National Rail)
            if (not self.station_classifier.is_underground_station(station) or
                self.station_classifier.is_terminal_station(station) or
                self.station_classifier.is_mixed_station(station)):
                filtered_path.append(station)
            else:
                system_info = self.station_classifier.get_underground_system(station)
                system_name = system_info[1] if system_info else "underground"
                self.logger.debug(f"Filtered out {system_name}-only station: {station}")
        
        return filtered_path