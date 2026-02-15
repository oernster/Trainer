"""
Underground Station Classifier

Handles classification and identification of underground stations.
"""

import logging
from typing import Dict, Optional, Set, Tuple

from .data_loader import UndergroundDataLoader
from src.core.interfaces.i_data_repository import IDataRepository


class StationClassifier:
    """Handles classification and identification of underground stations."""
    
    def __init__(self, data_repository: IDataRepository, data_loader: UndergroundDataLoader):
        """
        Initialize the station classifier.
        
        Args:
            data_repository: Data repository for accessing railway data
            data_loader: Underground data loader for accessing underground system data
        """
        self.data_repository = data_repository
        self.data_loader = data_loader
        self.logger = logging.getLogger(__name__)
    
    def get_underground_system(self, station_name: str) -> Optional[Tuple[str, str]]:
        """
        Determine which underground system a station belongs to.
        
        Args:
            station_name: The station name to check
            
        Returns:
            Tuple of (system_key, system_name) if found, None otherwise
        """
        # Check London Underground first (most comprehensive)
        if self.is_london_underground_station(station_name):
            return ("london", "London Underground")
        
        # Check Glasgow Subway
        if self.is_glasgow_subway_station(station_name):
            return ("glasgow", "Glasgow Subway")
        
        # Check Tyne and Wear Metro
        if self.is_tyne_wear_metro_station(station_name):
            return ("tyne_wear", "Tyne and Wear Metro")
        
        return None
    
    def is_underground_station(self, station_name: str) -> bool:
        """
        Check if a station is part of any UK underground system.
        
        Args:
            station_name: The station name to check
            
        Returns:
            True if the station is part of any underground system, False otherwise
        """
        return self.get_underground_system(station_name) is not None
    
    def is_london_underground_station(self, station_name: str) -> bool:
        """
        Check if a station is a London Underground station.
        
        Args:
            station_name: The station name to check
            
        Returns:
            True if the station is a London Underground station, False otherwise
        """
        underground_stations = self.data_loader.load_london_underground_stations()
        return self._check_station_match(station_name, underground_stations, "london")
    
    def is_glasgow_subway_station(self, station_name: str) -> bool:
        """
        Check if a station is a Glasgow Subway station.
        
        Args:
            station_name: The station name to check
            
        Returns:
            True if the station is a Glasgow Subway station, False otherwise
        """
        subway_stations = self.data_loader.load_glasgow_subway_stations()
        return self._check_station_match(station_name, subway_stations, "glasgow")
    
    def is_tyne_wear_metro_station(self, station_name: str) -> bool:
        """
        Check if a station is a Tyne and Wear Metro station.
        
        Args:
            station_name: The station name to check
            
        Returns:
            True if the station is a Tyne and Wear Metro station, False otherwise
        """
        metro_stations = self.data_loader.load_tyne_wear_metro_stations()
        return self._check_station_match(station_name, metro_stations, "tyne_wear")
    
    def _check_station_match(self, station_name: str, system_stations: Set[str], system_key: str) -> bool:
        """
        Check if a station name matches any station in the given system.
        
        Args:
            station_name: The station name to check
            system_stations: Set of stations in the system
            system_key: Key identifying the system for specific logic
            
        Returns:
            True if the station matches, False otherwise
        """
        # Check exact match first
        if station_name in system_stations:
            return True
        
        # System-specific normalization
        if system_key == "london":
            return self._check_london_variations(station_name, system_stations)
        elif system_key == "glasgow":
            return self._check_glasgow_variations(station_name, system_stations)
        elif system_key == "tyne_wear":
            return self._check_tyne_wear_variations(station_name, system_stations)
        
        # Generic punctuation handling
        return self._check_generic_variations(station_name, system_stations)
    
    def _check_london_variations(self, station_name: str, underground_stations: Set[str]) -> bool:
        """Handle London-specific station name variations."""
        # Try normalized variations for London terminals
        # Handle "London Liverpool Street" -> "Liverpool Street" etc.
        normalized_name = station_name
        if normalized_name.startswith("London "):
            normalized_name = normalized_name[7:]  # Remove "London " prefix
            if normalized_name in underground_stations:
                return True
        
        # Handle common station name variations
        # King's Cross St. Pancras variations
        if "king" in station_name.lower() and ("cross" in station_name.lower() or "pancras" in station_name.lower()):
            # Try "Kings Cross St Pancras" (the version in our JSON)
            if "Kings Cross St Pancras" in underground_stations:
                return True
        
        return self._check_generic_variations(station_name, underground_stations)
    
    def _check_glasgow_variations(self, station_name: str, subway_stations: Set[str]) -> bool:
        """Handle Glasgow-specific station name variations."""
        # Handle "Glasgow Central" -> "St Enoch" interchange mapping
        if "glasgow central" in station_name.lower():
            return "St Enoch" in subway_stations
        elif "glasgow queen street" in station_name.lower():
            return "Buchanan Street" in subway_stations
        
        return self._check_generic_variations(station_name, subway_stations)
    
    def _check_tyne_wear_variations(self, station_name: str, metro_stations: Set[str]) -> bool:
        """Handle Tyne and Wear Metro-specific station name variations."""
        # Handle "Newcastle" -> "Central Station" mapping
        if station_name.lower() in ["newcastle", "newcastle central"]:
            return "Central Station" in metro_stations
        
        return self._check_generic_variations(station_name, metro_stations)
    
    def _check_generic_variations(self, station_name: str, system_stations: Set[str]) -> bool:
        """Handle generic station name variations (punctuation, etc.)."""
        # Handle apostrophe and period variations
        # Remove apostrophes and periods for comparison
        clean_name = station_name.replace("'", "").replace(".", "")
        if clean_name in system_stations:
            return True
        
        # Try adding/removing common punctuation
        for station in system_stations:
            clean_station = station.replace("'", "").replace(".", "")
            if clean_name == clean_station:
                return True
        
        return False
    
    def is_underground_only_station(self, station_name: str) -> bool:
        """
        Check if a station is underground-only (no National Rail services).
        
        Args:
            station_name: The station name to check
            
        Returns:
            True if the station is underground-only, False otherwise
        """
        # Check if it's an underground station in any system
        if not self.is_underground_station(station_name):
            return False
        
        # Check if it also has National Rail services
        # If the station exists in our railway lines data, it has National Rail services
        all_stations = self.data_repository.get_all_station_names()
        return station_name not in all_stations
    
    def is_mixed_station(self, station_name: str) -> bool:
        """
        Check if a station serves both underground and National Rail.
        
        Args:
            station_name: The station name to check
            
        Returns:
            True if the station serves both underground and National Rail, False otherwise
        """
        # Must be both an underground station AND in our railway lines data
        return (self.is_underground_station(station_name) and
                self.data_repository.validate_station_exists(station_name))
    
    def is_system_terminal(self, station_name: str, system_key: str) -> bool:
        """
        Check if a station is a terminal for a specific underground system.
        
        Args:
            station_name: The station name to check
            system_key: The system key ("london", "glasgow", "tyne_wear")
            
        Returns:
            True if the station is a terminal for the system, False otherwise
        """
        terminals = self.get_system_terminals(system_key)
        return station_name in terminals
    
    def is_london_terminal(self, station_name: str) -> bool:
        """
        Check if a station is a major London terminal.
        
        Args:
            station_name: The station name to check
            
        Returns:
            True if the station is a London terminal, False otherwise
        """
        return self.is_system_terminal(station_name, "london")
    
    def is_terminal_station(self, station_name: str) -> bool:
        """
        Check if a station is a terminal for any underground system.
        
        Args:
            station_name: The station name to check
            
        Returns:
            True if the station is a terminal, False otherwise
        """
        system_info = self.get_underground_system(station_name)
        if not system_info:
            return False
        
        system_key, _ = system_info
        return self.is_system_terminal(station_name, system_key)
    
    def get_system_terminals(self, system_key: str) -> list[str]:
        """
        Get the list of terminal stations for a specific underground system.
        
        Args:
            system_key: The system key ("london", "glasgow", "tyne_wear")
            
        Returns:
            List of terminal station names
        """
        systems = self.data_loader.load_underground_systems()
        system_data = systems.get(system_key, {})
        
        if system_key == "london":
            return [
                "London Waterloo",
                "London Liverpool Street",
                "London Victoria",
                "London Paddington",
                "London Kings Cross",
                "London St Pancras",
                "London Euston",
                "London Bridge",
                "London Charing Cross",
                "London Cannon Street",
                "London Fenchurch Street",
                "London Marylebone"
            ]
        else:
            return system_data.get('terminals', [])
    
    def get_london_terminals(self) -> list[str]:
        """
        Get the list of major London terminal stations that serve National Rail.
        
        Returns:
            List of London terminal station names
        """
        return self.get_system_terminals("london")
    
    def _station_name_match(self, station1: str, station2: str) -> bool:
        """Check if station names match, handling variations."""
        return station1.lower() == station2.lower() or \
               station1.lower() in station2.lower() or \
               station2.lower() in station1.lower()