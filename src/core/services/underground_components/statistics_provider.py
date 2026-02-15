"""
Underground Statistics Provider

Provides statistics about underground systems.
"""

import logging
from typing import Dict

from .data_loader import UndergroundDataLoader
from .station_classifier import StationClassifier


class StatisticsProvider:
    """Provides statistics about underground systems."""
    
    def __init__(self, data_loader: UndergroundDataLoader, station_classifier: StationClassifier, data_repository):
        """
        Initialize the statistics provider.
        
        Args:
            data_loader: Underground data loader for accessing underground system data
            station_classifier: Station classifier for checking station types
            data_repository: Data repository for accessing railway data
        """
        self.data_loader = data_loader
        self.station_classifier = station_classifier
        self.data_repository = data_repository
        self.logger = logging.getLogger(__name__)
    
    def get_underground_statistics(self) -> dict:
        """
        Get statistics about all UK underground networks.
        
        Returns:
            Dictionary with underground network statistics
        """
        systems = self.data_loader.load_underground_systems()
        all_stations = set(self.data_repository.get_all_station_names())
        
        stats = {
            "black_box_enabled": True,
            "systems": {}
        }
        
        total_underground_stations = 0
        total_underground_only = 0
        total_mixed_stations = 0
        total_terminals = 0
        
        for system_key, system_data in systems.items():
            system_stations = set(system_data.get('stations', []))
            system_terminals = system_data.get('terminals', [])
            
            # Count different types of stations for this system
            underground_only = 0
            mixed_stations = 0
            terminals = 0
            
            for station in system_stations:
                if station in all_stations:
                    mixed_stations += 1
                    if station in system_terminals:
                        terminals += 1
                else:
                    underground_only += 1
            
            system_name = system_data.get('metadata', {}).get('system', system_key.replace('_', ' ').title())
            
            stats["systems"][system_key] = {
                "name": system_name,
                "total_stations": len(system_stations),
                "underground_only_stations": underground_only,
                "mixed_stations": mixed_stations,
                "terminals": terminals
            }
            
            # Add to totals
            total_underground_stations += len(system_stations)
            total_underground_only += underground_only
            total_mixed_stations += mixed_stations
            total_terminals += terminals
        
        # Add overall totals
        stats.update({
            "total_underground_stations": total_underground_stations,
            "total_underground_only_stations": total_underground_only,
            "total_mixed_stations": total_mixed_stations,
            "total_terminals": total_terminals
        })
        
        return stats