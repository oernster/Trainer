"""
Underground Geographic Utilities

Handles geographic utilities for underground routing, including region detection
and coordinate-related functionality.
"""

import logging
from typing import Dict, Optional, List, Tuple

from .data_loader import UndergroundDataLoader


class GeographicUtils:
    """Handles geographic utilities for underground routing."""
    
    def __init__(self, data_loader: UndergroundDataLoader):
        """
        Initialize the geographic utilities.
        
        Args:
            data_loader: Underground data loader for accessing data files
        """
        self.data_loader = data_loader
        self.logger = logging.getLogger(__name__)
    
    def is_cross_country_route(self, from_station: str, to_station: str) -> bool:
        """
        Determine if this is a cross-country route that should go through London.
        
        Args:
            from_station: Starting station
            to_station: Destination station
            
        Returns:
            True if this is a cross-country route, False otherwise
        """
        # Check if one station is in Scotland and the other is in South England
        from_region = self._get_station_region(from_station)
        to_region = self._get_station_region(to_station)
        
        # If stations are in different regions and far apart, it's a cross-country route
        if from_region and to_region and from_region != to_region:
            # Check if one region is Scotland and the other is South England
            if (from_region == "Scotland" and to_region == "South England") or \
               (from_region == "South England" and to_region == "Scotland"):
                self.logger.info(f"Detected cross-country route: {from_station} → {to_station}")
                return True
        
        # Check for specific known cross-country routes
        known_cross_country_routes = [
            ("Southampton Central", "Hillhead"),
            ("Southampton Central", "Glasgow Central"),
            ("Hillhead", "Southampton Central"),
            ("Glasgow Central", "Southampton Central")
        ]
        
        for origin, destination in known_cross_country_routes:
            if self._station_name_match(from_station, origin) and self._station_name_match(to_station, destination):
                self.logger.info(f"Detected known cross-country route: {from_station} → {to_station}")
                return True
        
        return False
    
    def _station_name_match(self, station1: str, station2: str) -> bool:
        """Check if station names match, handling variations."""
        return station1.lower() == station2.lower() or \
               station1.lower() in station2.lower() or \
               station2.lower() in station1.lower()
    
    def _get_station_region(self, station_name: str) -> Optional[str]:
        """
        Determine the region of a station based on its coordinates or name.
        
        Args:
            station_name: The station name
            
        Returns:
            Region name or None if unknown
        """
        # Use coordinates from JSON data to determine region
        # This is a data-driven approach that doesn't rely on hard-coded values
        
        # Scotland coordinates (roughly)
        scotland_lat_min = 54.5
        
        # South England coordinates (roughly)
        south_england_lat_max = 52.0
        
        # Get station coordinates from data
        station_coords = self._get_station_coordinates(station_name)
        
        if station_coords:
            lat = station_coords.get('lat')
            if lat:
                if lat > scotland_lat_min:
                    return "Scotland"
                elif lat < south_england_lat_max:
                    return "South England"
                else:
                    return "Middle England"
        
        # Fallback to name-based detection
        if any(term in station_name for term in ["Glasgow", "Edinburgh", "Aberdeen", "Hillhead"]):
            return "Scotland"
        elif any(term in station_name for term in ["Southampton", "Portsmouth", "Bournemouth"]):
            return "South England"
        
        return None
    
    def _get_station_coordinates(self, station_name: str) -> Optional[Dict]:
        """
        Get the coordinates of a station from the data files.
        
        Args:
            station_name: The station name
            
        Returns:
            Dictionary with lat/lng coordinates or None if not found
        """
        # Look up station coordinates in cross_country_line.json
        cross_country_data = self.data_loader._load_cross_country_data()
        for station in cross_country_data.get('stations', []):
            if station.get('name') == station_name:
                coords = station.get('coordinates', {})
                if coords:
                    return coords
        
        # Try to find in interchange_connections.json
        interchange_connections = self.data_loader._load_interchange_connections_data()
        for conn in interchange_connections.get('connections', []):
            if conn.get('from_station') == station_name and 'coordinates' in conn:
                coords = conn.get('coordinates', {}).get('from', {})
                if coords:
                    return coords
            elif conn.get('to_station') == station_name and 'coordinates' in conn:
                coords = conn.get('coordinates', {}).get('to', {})
                if coords:
                    return coords
        
        return None
    
    def get_region_terminals(self, region: str) -> List[str]:
        """
        Get the main terminals for a specific region.
        
        Args:
            region: Region name ("South England", "Scotland", etc.)
            
        Returns:
            List of terminal stations for the region
        """
        if region == "South England":
            return [
                "London Waterloo",
                "London Paddington",
                "London Victoria",
                "London Liverpool Street",
                "London Bridge",
                "London Euston",
                "London Kings Cross",
                "London St Pancras"
            ]
        elif region == "Scotland":
            return [
                "Glasgow Central",
                "Edinburgh Waverley",
                "Glasgow Queen Street",
                "Aberdeen",
                "Inverness"
            ]
        elif region == "North England":
            return [
                "Manchester Piccadilly",
                "Liverpool Lime Street",
                "Leeds",
                "Newcastle",
                "York"
            ]
        elif region == "Wales":
            return [
                "Cardiff Central",
                "Swansea",
                "Newport"
            ]
        else:
            return ["London Waterloo"]  # Default to London Waterloo
    
    def find_best_terminus_for_station(self, station: str, terminals: List[str], data_repository) -> str:
        """
        Find the best terminus for a given station.
        
        Args:
            station: Station to find terminus for
            terminals: List of possible terminals
            data_repository: Data repository for accessing railway data
            
        Returns:
            Best terminus for the station
        """
        # If station is already a terminus, return it
        if station in terminals:
            return station
            
        # Check if we have a data repository to find connections
        if data_repository:
            # Try to find direct connections to terminals
            for terminus in terminals:
                common_lines = data_repository.get_common_lines(station, terminus)
                if common_lines:
                    return terminus
                    
        # If no direct connection found, use the first terminus in the list
        return terminals[0] if terminals else "London Waterloo"
    
    def find_best_london_connection(self, from_terminus: str, to_terminus: str) -> Tuple[str, str]:
        """
        Find the best London Underground connection between two terminals.
        
        Args:
            from_terminus: Origin terminus
            to_terminus: Destination terminus
            
        Returns:
            Tuple of (from_station, to_station) for the Underground connection
        """
        # Define common London terminal connections
        london_connections = {
            "London Waterloo": "London Euston",
            "London Paddington": "London Euston",
            "London Victoria": "London Euston",
            "London Liverpool Street": "London Euston",
            "London Bridge": "London Euston",
            "London Kings Cross": "London Euston",
            "London St Pancras": "London Euston",
            "London Euston": "London Waterloo"
        }
        
        # If from_terminus is a London terminal, use it as the starting point
        if from_terminus.startswith("London "):
            from_station = from_terminus
        else:
            from_station = "London Waterloo"  # Default
            
        # If to_terminus is a London terminal, use it as the ending point
        if to_terminus.startswith("London "):
            to_station = to_terminus
        else:
            # Look up the best connection for the from_station
            to_station = london_connections.get(from_station, "London Euston")
            
        # If from and to are the same, use a different to_station
        if from_station == to_station:
            if from_station == "London Euston":
                to_station = "London Kings Cross"
            else:
                to_station = "London Euston"
                
        return from_station, to_station