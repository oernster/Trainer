"""
Weather system manager for the main window.

This module provides a class for managing the weather system,
including initialization, updates, and error handling.
"""

import logging
import asyncio
from typing import Optional, Any, Dict, Callable

from PySide6.QtCore import QObject, Signal

logger = logging.getLogger(__name__)


class WeatherSystemManager(QObject):
    """
    Manager for the weather system.
    
    Handles weather system initialization, updates, and error handling.
    """
    
    # Signals
    weather_updated = Signal(object)
    weather_error = Signal(str)
    weather_loading_changed = Signal(bool)
    
    def __init__(self, config_manager, parent: Optional[QObject] = None):
        """
        Initialize weather system manager.
        
        Args:
            config_manager: Configuration manager for accessing config
            parent: Parent QObject
        """
        super().__init__(parent)
        self.config_manager = config_manager
        self.config = None
        self.weather_manager = None
        self.weather_widget = None
        self._weather_system_initialized = False
        
    def setup_weather_system(self, config, weather_widget: Optional[Any] = None) -> bool:
        """
        Setup weather integration system.
        
        Args:
            config: Application configuration
            weather_widget: Weather widget to connect to
            
        Returns:
            True if weather system was initialized successfully, False otherwise
        """
        self.config = config
        self.weather_widget = weather_widget
        
        if (
            not self.config
            or not hasattr(self.config, "weather")
            or not self.config.weather
        ):
            logger.warning("Weather configuration not available")
            self._update_weather_status(False)
            return False

        try:
            # Initialize weather manager (even if disabled, for potential later enabling)
            from ....managers.weather_manager import WeatherManager
            self.weather_manager = WeatherManager(self.config.weather)

            # Connect weather widget if it exists
            if self.weather_widget:
                # Connect weather widget signals
                self.weather_widget.weather_refresh_requested.connect(
                    self.refresh_weather
                )
                self.weather_widget.weather_settings_requested.connect(
                    self._on_weather_settings_requested
                )

                # Update weather widget config
                self.weather_widget.update_config(self.config.weather)

            # Connect weather manager Qt signals to weather widget
            self.weather_manager.weather_updated.connect(self.on_weather_updated)
            self.weather_manager.weather_error.connect(self.on_weather_error)
            self.weather_manager.loading_state_changed.connect(
                self.on_weather_loading_changed
            )

            # Connect weather manager signals directly to weather widget
            if self.weather_widget:
                self.weather_manager.weather_updated.connect(
                    self.weather_widget.on_weather_updated
                )
                self.weather_manager.weather_error.connect(
                    self.weather_widget.on_weather_error
                )
                self.weather_manager.loading_state_changed.connect(
                    self.weather_widget.on_weather_loading
                )

            # Update weather status and visibility
            enabled = self.config.weather.enabled
            self._update_weather_status(enabled)

            # CRITICAL FIX: Don't override user's manual visibility preference
            # Only set visibility if this is the first time AND user hasn't manually hidden the widget
            if self.weather_widget and not self._weather_system_initialized:
                if not hasattr(self.weather_widget, '_user_manually_hidden') or not self.weather_widget._user_manually_hidden:
                    # Don't override persisted UI state during system initialization
                    # Only set visibility if no UI config exists
                    if not (self.config and hasattr(self.config, 'ui') and self.config.ui):
                        self.weather_widget.setVisible(enabled)
                        logger.debug(f"Weather widget visibility set to {enabled} (first weather system setup, no UI config)")
                    else:
                        logger.debug("Weather widget visibility preserved from UI config during system setup")
                else:
                    logger.debug("Weather widget visibility preserved during system setup (user manually hidden)")
                self._weather_system_initialized = True
            elif self.weather_widget:
                logger.debug("Weather widget visibility preserved (user preference)")

            if enabled:
                logger.debug("Weather system initialized and enabled")
                # Start initial weather fetch
                self.refresh_weather()
            else:
                logger.info("Weather system initialized but disabled")
                
            return True

        except Exception as e:
            logger.error(f"Failed to initialize weather system: {e}")
            self._update_weather_status(False)
            if self.weather_widget:
                self.weather_widget.hide()
            return False
    
    def _update_weather_status(self, enabled: bool) -> None:
        """
        Update weather status display.
        
        Args:
            enabled: Whether weather integration is enabled
        """
        # Status bar removed - this method is kept for compatibility but does nothing
        logger.debug(f"Weather system status: {'enabled' if enabled else 'disabled'}")
    
    def refresh_weather(self) -> None:
        """Trigger manual weather refresh."""
        if self.weather_manager:
            # Run async refresh
            import asyncio

            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self.weather_manager.refresh_weather())
            else:
                asyncio.run(self.weather_manager.refresh_weather())
            logger.info("Manual weather refresh requested")
    
    def on_weather_updated(self, weather_data: Any) -> None:
        """
        Handle weather data update.
        
        Args:
            weather_data: Updated weather data
        """
        logger.debug("Weather data updated")
        # Re-emit the signal for other components
        self.weather_updated.emit(weather_data)
    
    def on_weather_error(self, error_message: str) -> None:
        """
        Handle weather error.
        
        Args:
            error_message: Error message
        """
        logger.warning(f"Weather error: {error_message}")
        # Re-emit the signal for other components
        self.weather_error.emit(error_message)
    
    def on_weather_loading_changed(self, is_loading: bool) -> None:
        """
        Handle weather loading state change.
        
        Args:
            is_loading: Whether weather data is loading
        """
        if is_loading:
            logger.debug("Weather data loading...")
        else:
            logger.debug("Weather data loading complete")
        # Re-emit the signal for other components
        self.weather_loading_changed.emit(is_loading)
    
    def _on_weather_settings_requested(self) -> None:
        """Handle weather settings requested signal."""
        # This will be connected to the main window's show_stations_settings_dialog method
        logger.debug("Weather settings requested")
        
    def update_config(self, config) -> None:
        """
        Update configuration.
        
        Args:
            config: Updated configuration
        """
        self.config = config
        
        if self.weather_manager and hasattr(self.config, "weather") and self.config.weather:
            self.weather_manager.update_config(self.config.weather)
            
            # Update weather widget configuration
            if self.weather_widget:
                self.weather_widget.update_config(self.config.weather)
                
            # Update weather status
            self._update_weather_status(self.config.weather.enabled)
            
            logger.debug("Weather system configuration updated")
    
    def shutdown(self) -> None:
        """Shutdown weather system."""
        if self.weather_manager:
            try:
                # Weather manager doesn't have a shutdown method, but we can clear references
                self.weather_manager = None
                logger.debug("Weather system shutdown complete")
            except Exception as e:
                logger.warning(f"Error shutting down weather system: {e}")