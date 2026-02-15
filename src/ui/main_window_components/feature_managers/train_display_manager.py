"""
Train display manager for the main window.

This module provides a class for managing the train display,
including train data updates and route display.
"""

import logging
from typing import List, Optional, Any, Tuple

from PySide6.QtCore import QObject, Signal

from ....models.train_data import TrainData

logger = logging.getLogger(__name__)


class TrainDisplayManager(QObject):
    """
    Manager for the train display.
    
    Handles train data display, updates, and route display.
    """
    
    # Signals
    train_selected = Signal(TrainData)
    route_selected = Signal(TrainData)
    
    def __init__(self, parent: Optional[QObject] = None):
        """
        Initialize train display manager.
        
        Args:
            parent: Parent QObject
        """
        super().__init__(parent)
        self.train_list_widget = None
        self.train_manager = None
        self._train_selection_connected = False
        self._route_selection_connected = False
    
    def setup_train_display(self, train_list_widget: Any, train_manager: Any) -> None:
        """
        Setup train display.
        
        Args:
            train_list_widget: Train list widget to display trains in
            train_manager: Train manager for accessing train data
        """
        self.train_list_widget = train_list_widget
        self.train_manager = train_manager
        
        # Connect train selection signal if not already connected
        if not self._train_selection_connected and self.train_list_widget:
            self.train_list_widget.train_selected.connect(self._on_train_selected)
            self._train_selection_connected = True
            
        # Connect route selection signal if not already connected
        if not self._route_selection_connected and self.train_list_widget:
            self.train_list_widget.route_selected.connect(self._on_route_selected)
            self._route_selection_connected = True
            
        logger.debug("Train display setup complete")
    
    def update_train_display(self, trains: List[TrainData]) -> None:
        """
        Update train list display.
        
        Args:
            trains: List of train data to display
        """
        logger.debug(f"Updating train display with {len(trains)} trains")
        
        if self.train_list_widget:
            self.train_list_widget.update_trains(trains)
            logger.debug(f"Train display updated successfully with {len(trains)} trains")
        else:
            logger.warning("No train_list_widget available for display update")
    
    def update_route_display(self, from_station: str, to_station: str, via_stations: Optional[List[str]] = None) -> None:
        """
        Update route display (header removed - now only logs route info).
        
        Args:
            from_station: Origin station name
            to_station: Destination station name
            via_stations: Optional list of via stations
        """
        # Clean up station names by removing railway line context for logging
        def clean_station_name(station_name: str) -> str:
            """Remove railway line context from station name for cleaner display."""
            if not station_name:
                return station_name
            # Remove text in parentheses (railway line context)
            if '(' in station_name:
                return station_name.split('(')[0].strip()
            return station_name
        
        clean_from = clean_station_name(from_station)
        clean_to = clean_station_name(to_station)
        
        if via_stations:
            # Clean via station names
            clean_via_stations = [clean_station_name(station) for station in via_stations]
            via_text = " -> ".join(clean_via_stations)
            route_text = f"Route: {clean_from} -> {via_text} -> {clean_to}"
        else:
            route_text = f"Route: {clean_from} -> {clean_to}"
        
        logger.debug(f"Route display updated: {route_text}")
    
    def update_last_update_time(self, timestamp: str) -> None:
        """
        Update last update timestamp (header removed - now only logs).
        
        Args:
            timestamp: Formatted timestamp string
        """
        # Header removed - last update time no longer shown in UI, only logged
        logger.debug(f"Last Updated: {timestamp}")
    
    def _on_train_selected(self, train_data: TrainData) -> None:
        """
        Handle train selection.
        
        Args:
            train_data: Selected train data
        """
        logger.info(f"Train selected: {train_data.destination}")
        # Re-emit the signal for other components
        self.train_selected.emit(train_data)
    
    def _on_route_selected(self, train_data: TrainData) -> None:
        """
        Handle route selection.
        
        Args:
            train_data: Train data for selected route
        """
        logger.info(f"Route selected: {train_data.destination}")
        # Re-emit the signal for other components
        self.route_selected.emit(train_data)
    
    def get_current_preferences(self) -> dict:
        """
        Get current preferences from configuration.
        
        Returns:
            Dictionary of current preferences
        """
        default_preferences = {
            'show_intermediate_stations': True,
            'avoid_walking': False,
            'max_walking_distance_km': 1.0,
            'train_lookahead_hours': 16
        }
        
        if not self.train_manager or not hasattr(self.train_manager, 'config'):
            return default_preferences
        
        config = self.train_manager.config
        
        # Extract preferences from config
        preferences = {}
        
        # Get show_intermediate_stations from config if available
        preferences['show_intermediate_stations'] = getattr(config, 'show_intermediate_stations', default_preferences['show_intermediate_stations'])
        
        # Get route calculation preferences
        preferences['avoid_walking'] = getattr(config, 'avoid_walking', default_preferences['avoid_walking'])
        preferences['max_walking_distance_km'] = getattr(config, 'max_walking_distance_km', default_preferences['max_walking_distance_km'])
        preferences['train_lookahead_hours'] = getattr(config, 'train_lookahead_hours', default_preferences['train_lookahead_hours'])
        
        return preferences