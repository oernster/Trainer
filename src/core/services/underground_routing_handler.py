"""
Underground Routing Handler

Handles the "black box" approach for all UK underground systems:
- London Underground (including DLR)
- Glasgow Subway
- Tyne and Wear Metro
"""

import logging
from typing import List, Optional, Set, Dict, Tuple

from ..interfaces.i_data_repository import IDataRepository
from ..models.route import Route, RouteSegment
from .underground_components.data_loader import UndergroundDataLoader
from .underground_components.station_classifier import StationClassifier
from .underground_components.journey_estimator import JourneyEstimator
from .underground_components.terminal_manager import TerminalManager
from .underground_components.geographic_utils import GeographicUtils
from .underground_components.route_factory import RouteFactory
from .underground_components.statistics_provider import StatisticsProvider


class UndergroundRoutingHandler:
    """Handles black box routing logic for all UK underground systems."""
    
    def __init__(self, data_repository: IDataRepository):
        """
        Initialize the underground routing handler.
        
        Args:
            data_repository: Data repository for accessing railway data
        """
        self.data_repository = data_repository
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.data_loader = UndergroundDataLoader()
        self.station_classifier = StationClassifier(data_repository, self.data_loader)
        self.journey_estimator = JourneyEstimator()
        self.geographic_utils = GeographicUtils(self.data_loader)
        self.terminal_manager = TerminalManager(self.station_classifier, self.geographic_utils)
        self.route_factory = RouteFactory(
            self.station_classifier,
            self.journey_estimator,
            self.terminal_manager,
            self.geographic_utils,
            data_repository
        )
        self.statistics_provider = StatisticsProvider(
            self.data_loader,
            self.station_classifier,
            data_repository
        )
    
    # Station classification methods
    
    def get_underground_system(self, station_name: str) -> Optional[Tuple[str, str]]:
        """
        Determine which underground system a station belongs to.
        
        Args:
            station_name: The station name to check
            
        Returns:
            Tuple of (system_key, system_name) if found, None otherwise
        """
        return self.station_classifier.get_underground_system(station_name)
    
    def is_underground_station(self, station_name: str) -> bool:
        """
        Check if a station is part of any UK underground system.
        
        Args:
            station_name: The station name to check
            
        Returns:
            True if the station is part of any underground system, False otherwise
        """
        return self.station_classifier.is_underground_station(station_name)
    
    def is_london_underground_station(self, station_name: str) -> bool:
        """
        Check if a station is a London Underground station.
        
        Args:
            station_name: The station name to check
            
        Returns:
            True if the station is a London Underground station, False otherwise
        """
        return self.station_classifier.is_london_underground_station(station_name)
    
    def is_glasgow_subway_station(self, station_name: str) -> bool:
        """
        Check if a station is a Glasgow Subway station.
        
        Args:
            station_name: The station name to check
            
        Returns:
            True if the station is a Glasgow Subway station, False otherwise
        """
        return self.station_classifier.is_glasgow_subway_station(station_name)
    
    def is_tyne_wear_metro_station(self, station_name: str) -> bool:
        """
        Check if a station is a Tyne and Wear Metro station.
        
        Args:
            station_name: The station name to check
            
        Returns:
            True if the station is a Tyne and Wear Metro station, False otherwise
        """
        return self.station_classifier.is_tyne_wear_metro_station(station_name)
    
    def is_underground_only_station(self, station_name: str) -> bool:
        """
        Check if a station is underground-only (no National Rail services).
        
        Args:
            station_name: The station name to check
            
        Returns:
            True if the station is underground-only, False otherwise
        """
        return self.station_classifier.is_underground_only_station(station_name)
    
    def is_mixed_station(self, station_name: str) -> bool:
        """
        Check if a station serves both underground and National Rail.
        
        Args:
            station_name: The station name to check
            
        Returns:
            True if the station serves both underground and National Rail, False otherwise
        """
        return self.station_classifier.is_mixed_station(station_name)
    
    # Terminal station methods
    
    def get_system_terminals(self, system_key: str) -> List[str]:
        """
        Get the list of terminal stations for a specific underground system.
        
        Args:
            system_key: The system key ("london", "glasgow", "tyne_wear")
            
        Returns:
            List of terminal station names
        """
        return self.station_classifier.get_system_terminals(system_key)
    
    def get_london_terminals(self) -> List[str]:
        """
        Get the list of major London terminal stations that serve National Rail.
        
        Returns:
            List of London terminal station names
        """
        return self.station_classifier.get_london_terminals()
    
    def is_system_terminal(self, station_name: str, system_key: str) -> bool:
        """
        Check if a station is a terminal for a specific underground system.
        
        Args:
            station_name: The station name to check
            system_key: The system key ("london", "glasgow", "tyne_wear")
            
        Returns:
            True if the station is a terminal for the system, False otherwise
        """
        return self.station_classifier.is_system_terminal(station_name, system_key)
    
    def is_london_terminal(self, station_name: str) -> bool:
        """
        Check if a station is a major London terminal.
        
        Args:
            station_name: The station name to check
            
        Returns:
            True if the station is a London terminal, False otherwise
        """
        return self.station_classifier.is_london_terminal(station_name)
    
    def is_terminal_station(self, station_name: str) -> bool:
        """
        Check if a station is a terminal for any underground system.
        
        Args:
            station_name: The station name to check
            
        Returns:
            True if the station is a terminal, False otherwise
        """
        return self.station_classifier.is_terminal_station(station_name)
    
    # Route creation methods
    
    def should_use_black_box_routing(self, from_station: str, to_station: str) -> bool:
        """
        Determine if black box routing should be used for a journey.
        
        Args:
            from_station: Starting station
            to_station: Destination station
            
        Returns:
            True if black box routing should be used, False otherwise
        """
        return self.route_factory.should_use_black_box_routing(from_station, to_station)
    
    def create_black_box_route(self, from_station: str, to_station: str) -> Optional[Route]:
        """
        Create a black box route for underground journeys.
        
        Args:
            from_station: Starting station
            to_station: Destination station
            
        Returns:
            A Route object with black box underground segment, or None if not applicable
        """
        return self.route_factory.create_black_box_route(from_station, to_station)
    
    def create_multi_system_route(self, from_station: str, to_station: str) -> Optional[Route]:
        """
        Create a multi-system route connecting different underground systems via National Rail.
        
        Args:
            from_station: Starting station (underground station)
            to_station: Destination station (different underground system)
            
        Returns:
            A Route object with multiple segments, or None if not applicable
        """
        return self.route_factory.create_multi_system_route(from_station, to_station)
    
    def is_cross_country_route(self, from_station: str, to_station: str) -> bool:
        """
        Determine if this is a cross-country route that should go through London.
        
        Args:
            from_station: Starting station
            to_station: Destination station
            
        Returns:
            True if this is a cross-country route, False otherwise
        """
        return self.geographic_utils.is_cross_country_route(from_station, to_station)
    
    def create_cross_country_route(self, from_station: str, to_station: str) -> Optional[Route]:
        """
        Create a route for cross-country journeys that should go through London.
        
        Args:
            from_station: Starting station
            to_station: Destination station
            
        Returns:
            Route with cross-country pattern or None
        """
        return self.route_factory.create_cross_country_route(from_station, to_station)
    
    # Path and route enhancement methods
    
    def get_nearest_terminals(self, station_name: str) -> List[str]:
        """
        Get the nearest terminals to a given station based on its underground system.
        
        Args:
            station_name: The station name
            
        Returns:
            List of nearest terminal stations (ordered by preference)
        """
        return self.terminal_manager.get_nearest_terminals(station_name)
    
    def filter_underground_stations_from_path(self, path: List[str]) -> List[str]:
        """
        Filter out underground-only stations from a path, keeping only terminals and mixed stations.
        
        Args:
            path: List of station names in the path
            
        Returns:
            Filtered path with underground-only stations removed
        """
        return self.terminal_manager.filter_underground_stations_from_path(path)
    
    def enhance_route_with_black_box(self, route: Route) -> Route:
        """
        Enhance a route by replacing underground segments with black box representation.
        
        Args:
            route: The route to enhance
            
        Returns:
            Enhanced route with black box underground segments
        """
        return self.route_factory.enhance_route_with_black_box(route)
    
    # Data loading and statistics methods
    
    def load_underground_systems(self) -> Dict[str, Dict]:
        """Load all underground systems data from properly structured JSON file."""
        return self.data_loader.load_underground_systems()
    
    def load_london_underground_stations(self) -> Set[str]:
        """Load the list of London Underground stations from JSON file."""
        return self.data_loader.load_london_underground_stations()
    
    def load_glasgow_subway_stations(self) -> Set[str]:
        """Load the list of Glasgow Subway stations from JSON file."""
        return self.data_loader.load_glasgow_subway_stations()
    
    def load_tyne_wear_metro_stations(self) -> Set[str]:
        """Load the list of Tyne and Wear Metro stations from JSON file."""
        return self.data_loader.load_tyne_wear_metro_stations()
    
    def get_underground_statistics(self) -> dict:
        """
        Get statistics about all UK underground networks.
        
        Returns:
            Dictionary with underground network statistics
        """
        return self.statistics_provider.get_underground_statistics()
    
    def clear_cache(self) -> None:
        """Clear any cached underground station data for all systems."""
        self.data_loader.clear_cache()