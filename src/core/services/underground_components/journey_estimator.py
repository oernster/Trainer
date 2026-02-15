"""
Underground Journey Estimator

Handles estimation of distances and journey times for underground routes.
"""

import logging
from typing import Dict


class JourneyEstimator:
    """Handles estimation of distances and journey times for underground routes."""
    
    def __init__(self):
        """Initialize the journey estimator."""
        self.logger = logging.getLogger(__name__)
    
    def estimate_underground_distance(self, from_station: str, to_station: str, system_key: str = "london") -> float:
        """
        Estimate the distance for an underground journey.
        
        Args:
            from_station: Starting station
            to_station: Destination station
            system_key: The underground system key ("london", "glasgow", "tyne_wear")
            
        Returns:
            Estimated distance in kilometers
        """
        if system_key == "glasgow":
            # Glasgow Subway is a small circular system
            return 3.0  # Average journey on Glasgow Subway: 2-4km
        elif system_key == "tyne_wear":
            # Tyne and Wear Metro covers a larger area
            return 8.0  # Average journey on Tyne and Wear Metro: 5-12km
        else:
            # London Underground distance estimation based on geography
            
            # Central London stations (Zone 1)
            central_london_indicators = [
                "Central", "City", "Covent Garden", "Oxford", "Piccadilly", "Leicester",
                "Charing Cross", "Westminster", "Victoria", "Liverpool Street", "Kings Cross",
                "Euston", "Paddington", "Waterloo", "London Bridge", "Bank", "Monument"
            ]
            
            # Inner London stations (Zones 2-3)
            inner_london_indicators = [
                "Clapham", "Camden", "Islington", "Hammersmith", "Kensington", "Chelsea",
                "Canary Wharf", "Greenwich", "Wimbledon"
            ]
            
            # Outer London stations (Zones 4-6)
            outer_london_indicators = [
                "Heathrow", "Stanmore", "Epping", "Upminster", "Croydon", "Richmond"
            ]
            
            def get_zone(station_name):
                if any(indicator in station_name for indicator in central_london_indicators):
                    return 1  # Central London
                elif any(indicator in station_name for indicator in inner_london_indicators):
                    return 2  # Inner London
                elif any(indicator in station_name for indicator in outer_london_indicators):
                    return 3  # Outer London
                else:
                    return 2  # Default to inner London
            
            from_zone = get_zone(from_station)
            to_zone = get_zone(to_station)
            
            # Distance estimation based on zones
            if from_zone == 1 and to_zone == 1:
                return 2.5  # Central to central: 2-3km
            elif (from_zone == 1 and to_zone == 2) or (from_zone == 2 and to_zone == 1):
                return 5.0  # Central to inner: 4-6km
            elif from_zone == 2 and to_zone == 2:
                return 7.0  # Inner to inner: 6-8km
            elif (from_zone <= 2 and to_zone == 3) or (from_zone == 3 and to_zone <= 2):
                return 12.0  # Inner/central to outer: 10-15km
            else:
                return 15.0  # Outer to outer: 12-18km
    
    def estimate_underground_time(self, from_station: str, to_station: str, system_key: str = "london") -> int:
        """
        Estimate the journey time for an underground journey.
        
        Args:
            from_station: Starting station
            to_station: Destination station
            system_key: The underground system key ("london", "glasgow", "tyne_wear")
            
        Returns:
            Estimated journey time in minutes
        """
        # Estimate based on distance
        distance = self.estimate_underground_distance(from_station, to_station, system_key)
        
        if system_key == "glasgow":
            # Glasgow Subway is frequent but smaller network
            # Average speed about 15-20 km/h including stops
            base_time = (distance / 18) * 60  # Convert to minutes
            estimated_time = max(5, min(20, int(base_time)))  # Between 5-20 minutes
        elif system_key == "tyne_wear":
            # Tyne and Wear Metro covers larger distances
            # Average speed about 25-30 km/h including stops
            base_time = (distance / 27) * 60  # Convert to minutes
            # Add time for potential changes
            if distance > 8:
                base_time += 3  # 3 minutes for one change
            estimated_time = max(8, min(35, int(base_time)))  # Between 8-35 minutes
        else:
            # London Underground
            # Average speed is about 20-25 km/h including stops
            base_time = (distance / 22) * 60  # Convert to minutes
            
            # Add time for potential changes (assume 1 change on average for longer journeys)
            if distance > 10:
                base_time += 5  # 5 minutes for one change
            
            # Realistic Underground time estimates (10-40 minutes):
            # - Short journeys: 10-15 minutes
            # - Medium journeys: 15-25 minutes
            # - Long journeys: 25-40 minutes
            
            estimated_time = max(10, min(40, int(base_time)))  # Between 10-40 minutes
        
        return estimated_time
    
    def estimate_national_rail_distance(self, from_station: str, to_station: str) -> float:
        """
        Estimate distance for National Rail segment between terminals.
        
        Args:
            from_station: Starting station
            to_station: Destination station
            
        Returns:
            Estimated distance in kilometers
        """
        # Rough estimates based on major UK city distances
        distance_map = {
            ("London", "Glasgow"): 650,
            ("London", "Newcastle"): 450,
            ("Glasgow", "Newcastle"): 250,
        }
        
        # Determine cities
        from_city = "London" if "London" in from_station else ("Glasgow" if any(term in from_station for term in ["Glasgow", "Buchanan", "St Enoch"]) else "Newcastle")
        to_city = "London" if "London" in to_station else ("Glasgow" if any(term in to_station for term in ["Glasgow", "Buchanan", "St Enoch"]) else "Newcastle")
        
        # Look up distance
        key = (from_city, to_city) if from_city <= to_city else (to_city, from_city)
        return distance_map.get(key, 400)  # Default 400km
    
    def estimate_national_rail_time(self, from_station: str, to_station: str) -> int:
        """
        Estimate journey time for National Rail segment between terminals.
        
        Args:
            from_station: Starting station
            to_station: Destination station
            
        Returns:
            Estimated journey time in minutes
        """
        distance = self.estimate_national_rail_distance(from_station, to_station)
        # Average speed for long-distance rail: 100-120 km/h
        base_time = (distance / 110) * 60  # Convert to minutes
        return int(base_time)
    
    def get_line_between_stations(self, from_station: str, to_station: str, data_repository) -> str:
        """
        Get the most appropriate line name between two stations.
        
        Args:
            from_station: Origin station
            to_station: Destination station
            data_repository: Data repository for accessing railway data
            
        Returns:
            Line name for the connection
        """
        # Check if we have a data repository to find common lines
        if data_repository:
            common_lines = data_repository.get_common_lines(from_station, to_station)
            if common_lines and len(common_lines) > 0:
                return common_lines[0].name
                
        # If no common line found, use geographic heuristics
        if "London" in from_station and "Glasgow" in to_station or "Glasgow" in from_station and "London" in to_station:
            return "West Coast Main Line"
        elif "London" in from_station and "Edinburgh" in to_station or "Edinburgh" in from_station and "London" in to_station:
            return "East Coast Main Line"
        elif "London" in from_station and "Southampton" in to_station or "Southampton" in from_station and "London" in to_station:
            return "South Western Main Line"
        elif "London" in from_station and "Brighton" in to_station or "Brighton" in from_station and "London" in to_station:
            return "Brighton Main Line"
        elif "London" in from_station and "Bristol" in to_station or "Bristol" in from_station and "London" in to_station:
            return "Great Western Main Line"
        else:
            return "National Rail"