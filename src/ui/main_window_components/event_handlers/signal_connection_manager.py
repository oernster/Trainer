"""
Signal connection manager for the main window.

This module provides a class for managing signal connections
between components, extracted from the MainWindow class.
"""

import logging
from typing import Optional, Any, Dict, List

from PySide6.QtCore import QObject, Signal, QTimer

logger = logging.getLogger(__name__)


class SignalConnectionManager(QObject):
    """
    Manager for signal connections.
    
    Handles connecting signals between components and handling settings changes.
    """
    
    # Signals
    refresh_requested = Signal()
    theme_changed = Signal(str)
    astronomy_manager_ready = Signal()
    route_changed = Signal(str, str)
    config_updated = Signal(object)
    
    def __init__(self, parent: Optional[QObject] = None):
        """
        Initialize signal connection manager.
        
        Args:
            parent: Parent QObject
        """
        super().__init__(parent)
        
        # Add refresh debounce timer to prevent rapid successive refreshes
        self._refresh_debounce_timer = QTimer()
        self._refresh_debounce_timer.setSingleShot(True)
        self._refresh_debounce_timer.timeout.connect(self._emit_debounced_refresh)
        self._pending_refresh = False
    
    def connect_signals(self, 
                       theme_manager=None,
                       weather_manager=None,
                       astronomy_manager=None,
                       train_display_manager=None,
                       dialog_manager=None) -> None:
        """
        Connect signals between components.
        
        Args:
            theme_manager: Theme manager to connect signals to
            weather_manager: Weather manager to connect signals to
            astronomy_manager: Astronomy manager to connect signals to
            train_display_manager: Train display manager to connect signals to
            dialog_manager: Dialog manager to connect signals to
        """
        # Connect theme manager signals
        if theme_manager:
            theme_manager.theme_changed.connect(self._on_theme_changed)
            logger.debug("Connected theme manager signals")
        
        # Connect astronomy manager ready signal to trigger data fetch
        if astronomy_manager:
            self.astronomy_manager_ready.connect(self._on_astronomy_manager_ready)
            logger.debug("Connected astronomy manager ready signal")
            
            # Connect astronomy manager to astronomy manager ready signal
            self.astronomy_manager_ready.connect(astronomy_manager.refresh_astronomy)
            logger.debug("Connected astronomy manager ready signal to refresh_astronomy")
        
        # Connect train display manager signals
        if train_display_manager:
            # Connect train selection signal
            train_display_manager.train_selected.connect(self._on_train_selected)
            logger.debug("Connected train selection signal")
            
            # Connect route selection signal
            train_display_manager.route_selected.connect(self._on_route_selected)
            logger.debug("Connected route selection signal")
        
        logger.debug("Signal connections established")
    
    def on_settings_saved(self, 
                         config_manager=None,
                         theme_manager=None,
                         weather_manager=None,
                         astronomy_manager=None,
                         train_list_widget=None) -> None:
        """
        Handle settings saved event.
        
        Args:
            config_manager: Configuration manager to reload config from
            theme_manager: Theme manager to update theme
            weather_manager: Weather manager to update config
            astronomy_manager: Astronomy manager to update config
            train_list_widget: Train list widget to update preferences
        """
        try:
            # Store old settings for comparison
            old_time_window = None
            old_train_lookahead = None
            old_avoid_walking = None
            old_max_walking_distance = None
            old_prefer_direct = None
            old_max_changes = None
            
            if hasattr(self, 'config'):
                config = getattr(self, 'config')
                if hasattr(config, 'display'):
                    old_time_window = config.display.time_window_hours
                old_train_lookahead = getattr(config, 'train_lookahead_hours', None)
                old_avoid_walking = getattr(config, 'avoid_walking', None)
                old_max_walking_distance = getattr(config, 'max_walking_distance_km', None)
                old_prefer_direct = getattr(config, 'prefer_direct', None)
                old_max_changes = getattr(config, 'max_changes', None)
            
            # Store current theme before reloading config
            current_theme = theme_manager.current_theme if theme_manager else None
            
            # Reload configuration
            if config_manager:
                self.config = config_manager.load_config()
                
                # GUARANTEED FIX: Always preserve the current theme from theme manager
                if self.config and current_theme:
                    # Force the theme to be what's currently active in the UI
                    self.config.display.theme = current_theme
                    if theme_manager:
                        theme_manager.set_theme(current_theme)
                    
                    # Save the config again with the correct theme
                    config_manager.save_config(self.config)
                    
                    # Emit config updated signal to update train manager
                    self.config_updated.emit(self.config)
                    
                    # Check for changes that require train data refresh
                    needs_refresh = False
                    
                    # Check display time window change
                    if hasattr(self.config, 'display') and self.config.display:
                        new_time_window = self.config.display.time_window_hours
                        if old_time_window != new_time_window:
                            logger.info(f"Display time window changed from {old_time_window} to {new_time_window} hours")
                            needs_refresh = True
                    
                    # Check train lookahead time change
                    new_train_lookahead = getattr(self.config, 'train_lookahead_hours', None)
                    if old_train_lookahead != new_train_lookahead:
                        logger.info(f"Train look-ahead time changed from {old_train_lookahead} to {new_train_lookahead} hours")
                        needs_refresh = True
                    
                    # Check route preference changes that affect route calculation
                    new_avoid_walking = getattr(self.config, 'avoid_walking', None)
                    if old_avoid_walking != new_avoid_walking:
                        logger.info(f"Avoid walking preference changed from {old_avoid_walking} to {new_avoid_walking}")
                        needs_refresh = True
                    
                    new_max_walking_distance = getattr(self.config, 'max_walking_distance_km', None)
                    if old_max_walking_distance != new_max_walking_distance:
                        logger.info(f"Max walking distance changed from {old_max_walking_distance} to {new_max_walking_distance} km")
                        needs_refresh = True
                    
                    new_prefer_direct = getattr(self.config, 'prefer_direct', None)
                    if old_prefer_direct != new_prefer_direct:
                        logger.info(f"Prefer direct routes changed from {old_prefer_direct} to {new_prefer_direct}")
                        needs_refresh = True
                    
                    new_max_changes = getattr(self.config, 'max_changes', None)
                    if old_max_changes != new_max_changes:
                        logger.info(f"Max changes preference changed from {old_max_changes} to {new_max_changes}")
                        needs_refresh = True
                    
                    # Update train list widget preferences if they changed
                    if train_list_widget:
                        from ...main_window_components.feature_managers.train_display_manager import TrainDisplayManager
                        train_display_manager = TrainDisplayManager()
                        current_preferences = train_display_manager.get_current_preferences()
                        train_list_widget.set_preferences(current_preferences)
                        logger.info("Updated train list widget preferences")
                    
                    # Trigger refresh if any setting that affects train data changed
                    if needs_refresh:
                        self.refresh_requested.emit()
                        logger.info("Refreshing train data for new preference settings")
                    
                    # Update route display with via stations
                    if hasattr(self.config, 'stations'):
                        via_stations = getattr(self.config.stations, 'via_stations', [])
                        # Emit route changed signal
                        self.route_changed.emit(self.config.stations.from_name, self.config.stations.to_name)
                        logger.info(f"Route changed: {self.config.stations.from_name} -> {self.config.stations.to_name}")
                    
                    # Trigger refresh to load trains with new route data (with debounce)
                    self._trigger_debounced_refresh()
                    logger.info("Route changed - refreshing train data for new route")
                    
                    # Update weather system if configuration changed
                    if weather_manager and hasattr(self.config, "weather") and self.config.weather:
                        weather_manager.update_config(self.config)
                        logger.info("Weather system configuration updated")
                    
                    # Update astronomy system if configuration changed
                    if astronomy_manager and hasattr(self.config, "astronomy") and self.config.astronomy:
                        astronomy_manager.update_config(self.config)
                        logger.info("Astronomy system configuration updated")
            
            logger.info("Settings reloaded after save")
            
        except Exception as e:
            logger.error(f"Failed to reload settings: {e}")
    
    def _on_theme_changed(self, theme_name: str) -> None:
        """
        Handle theme change.
        
        Args:
            theme_name: New theme name
        """
        # Re-emit the signal for other components
        self.theme_changed.emit(theme_name)
        logger.info(f"Theme changed to {theme_name}")
    
    def _on_astronomy_manager_ready(self) -> None:
        """Handle astronomy manager ready signal."""
        logger.debug("Astronomy manager ready signal received")
        # This signal will be connected to the astronomy manager's refresh_astronomy method
    
    def _on_train_selected(self, train_data) -> None:
        """
        Handle train selection.
        
        Args:
            train_data: Selected train data
        """
        logger.info(f"Train selected: {train_data.destination}")
        # This will be handled by the dialog manager
    
    def _on_route_selected(self, train_data) -> None:
        """
        Handle route selection.
        
        Args:
            train_data: Train data for selected route
        """
        logger.info(f"Route selected: {train_data.destination}")
        # This will be handled by the dialog manager
    
    def _trigger_debounced_refresh(self) -> None:
        """Trigger a debounced refresh to prevent rapid successive refresh requests."""
        logger.debug("Triggering debounced refresh")
        self._pending_refresh = True
        
        # Stop any existing timer and start a new one with 500ms delay
        self._refresh_debounce_timer.stop()
        self._refresh_debounce_timer.start(500)  # 500ms debounce
    
    def _emit_debounced_refresh(self) -> None:
        """Emit the actual refresh signal after debounce delay."""
        if self._pending_refresh:
            self._pending_refresh = False
            logger.debug("Emitting debounced refresh signal")
            self.refresh_requested.emit()
        else:
            logger.debug("No pending refresh, skipping signal emission")