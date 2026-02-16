"""
Initialization manager for optimized widget startup sequence.
Author: Oliver Ernster

This module provides optimized initialization of widgets in the specified order:
1. Weather widgets
2. Train widgets
3. Astronomy widgets (with parallel data fetching)

The manager ensures all widgets appear on the main UI almost simultaneously
by using parallel threading for data-intensive operations.
"""

import asyncio
import logging
import threading
import time
from typing import Optional, Callable, Any
from PySide6.QtCore import QObject, Signal, QTimer, QThread
from PySide6.QtWidgets import QApplication

from ..managers.weather_manager import WeatherManager
from ..managers.astronomy_manager import AstronomyManager
from ..managers.train_manager import TrainManager
from ..managers.config_manager import ConfigManager

logger = logging.getLogger(__name__)

class AstronomyDataWorker(QThread):
    """
    Worker thread for parallel astronomy data fetching.
    
    This worker runs in a separate thread to fetch astronomy data
    without blocking the main UI initialization process.
    """
    
    # Signals for communication with main thread
    data_fetched = Signal(object)  # AstronomyForecastData
    fetch_error = Signal(str)  # Error message
    fetch_started = Signal()
    fetch_completed = Signal()
    
    def __init__(self, astronomy_manager: AstronomyManager, parent=None):
        super().__init__(parent)
        self.astronomy_manager = astronomy_manager
        self.should_stop = False
        
    def run(self):
        """Run the astronomy data fetching in background thread."""
        try:
            self.fetch_started.emit()

            # Check if we should stop before starting
            if self.should_stop:
                return
                
            # Create new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # Fetch astronomy data asynchronously
                if not self.should_stop and self.astronomy_manager:
                    forecast_data = loop.run_until_complete(
                        self.astronomy_manager.refresh_astronomy(force_refresh=True)
                    )
                    
                    if not self.should_stop and forecast_data:
                        self.data_fetched.emit(forecast_data)
                        
                    elif not self.should_stop:
                        self.fetch_error.emit("No astronomy data received")
                        
            except Exception as e:
                if not self.should_stop:
                    error_msg = f"Failed to fetch astronomy data: {e}"
                    logger.error(error_msg)
                    self.fetch_error.emit(error_msg)
            finally:
                loop.close()
                
        except Exception as e:
            if not self.should_stop:
                error_msg = f"Astronomy data worker thread error: {e}"
                logger.error(error_msg)
                self.fetch_error.emit(error_msg)
        finally:
            if not self.should_stop:
                self.fetch_completed.emit()
                logger.debug("Astronomy data worker thread completed")
    
    def stop(self):
        """Stop the worker thread gracefully."""
        self.should_stop = True
        logger.debug("Astronomy data worker thread stop requested")

class InitializationManager(QObject):
    """
    Manager for optimized widget initialization sequence.
    
    Handles the initialization of widgets in the specified order:
    1. Weather widgets (immediate)
    2. Train widgets (immediate)
    3. Astronomy widgets (immediate UI, parallel data fetch)
    
    Uses parallel threading to ensure astronomy data fetching doesn't block
    the UI initialization process.
    """
    
    # Signals for initialization progress
    initialization_started = Signal()
    weather_initialized = Signal()
    train_initialized = Signal()
    astronomy_initialized = Signal()
    astronomy_data_ready = Signal()
    initialization_completed = Signal()
    initialization_error = Signal(str)
    
    def __init__(self, config_manager: ConfigManager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.config = None
        
        # Managers
        self.weather_manager: Optional[WeatherManager] = None
        self.astronomy_manager: Optional[AstronomyManager] = None
        self.train_manager: Optional[TrainManager] = None
        
        # Astronomy data worker
        self.astronomy_worker: Optional[AstronomyDataWorker] = None
        
        # Initialization state
        self.is_initializing = False
        self.initialization_start_time = 0
        
        logger.debug("InitializationManager created")
    
    def initialize_widgets(self, main_window) -> None:
        """
        Initialize all widgets in optimized sequence.
        
        Args:
            main_window: MainWindow instance to initialize widgets for
        """
        if self.is_initializing:
            logger.warning("Initialization already in progress")
            return
            
        self.is_initializing = True
        self.initialization_start_time = time.time()
        
        try:
            self.initialization_started.emit()

            # Load configuration
            self.config = self.config_manager.load_config()
            
            # Step 1: Initialize Weather Widgets (immediate)
            self._initialize_weather_widgets(main_window)
            
            # Step 2: Initialize Train Widgets (immediate)
            self._initialize_train_widgets(main_window)
            
            # Step 3: Initialize Astronomy Widgets (immediate UI, parallel data fetch)
            self._initialize_astronomy_widgets(main_window)
            
            # Complete initialization
            elapsed_time = time.time() - self.initialization_start_time
            
            self.initialization_completed.emit()
            
        except Exception as e:
            error_msg = f"Widget initialization failed: {e}"
            logger.error(error_msg)
            self.initialization_error.emit(error_msg)
        finally:
            self.is_initializing = False
    
    def _initialize_weather_widgets(self, main_window) -> None:
        """Initialize weather widgets and manager."""
        try:
            logger.debug("Initializing weather widgets...")
            
            # Initialize weather manager if config available
            if (self.config and
                hasattr(self.config, "weather") and
                self.config.weather and
                self.config.weather.enabled):
                
                # Phase 2 boundary: bootstrap composes WeatherManager.
                # InitializationManager may only wire an injected instance.
                if not self.weather_manager:
                    self.weather_manager = getattr(main_window, "weather_manager", None)

                if not self.weather_manager:
                    logger.warning(
                        "Weather is enabled in config but no WeatherManager was injected; skipping weather wiring"
                    )
                    self.weather_initialized.emit()
                    return
                
                # Connect to main window's weather widget
                if main_window.weather_widget:
                    # Only connect signals if not already connected
                    if not hasattr(main_window.weather_widget, '_initialization_signals_connected'):
                        # Connect signals
                        self.weather_manager.weather_updated.connect(
                            main_window.weather_widget.on_weather_updated
                        )
                        self.weather_manager.weather_error.connect(
                            main_window.weather_widget.on_weather_error
                        )
                        self.weather_manager.loading_state_changed.connect(
                            main_window.weather_widget.on_weather_loading
                        )
                        main_window.weather_widget._initialization_signals_connected = True
                    
                    # Update widget config
                    main_window.weather_widget.update_config(self.config.weather)
                    
                    # CRITICAL FIX: Don't override user's manual visibility preference
                    # Only set visible if this is the first initialization
                    if not hasattr(main_window, '_weather_widget_initialized'):
                        # CRITICAL FIX: Don't override user's manual visibility preference
                        # Only set visibility if weather is enabled in config AND user hasn't manually hidden it
                        if (hasattr(main_window, 'config') and main_window.config and
                            hasattr(main_window.config, 'weather') and main_window.config.weather and
                            main_window.config.weather.enabled):
                            # Only set visible if user hasn't manually hidden the widget
                            if not hasattr(main_window.weather_widget, '_user_manually_hidden'):
                                main_window.weather_widget.setVisible(True)
                                logger.debug("Weather widget set visible during initialization (config enabled)")
                            else:
                                logger.debug("Weather widget kept hidden during initialization (user preference)")
                        else:
                            main_window.weather_widget.setVisible(False)
                            logger.debug("Weather widget set hidden during initialization (config disabled)")
                        main_window._weather_widget_initialized = True
                        logger.debug("Weather widget visibility set to True (first initialization)")
                    else:
                        logger.debug("Weather widget visibility preserved (user preference)")
                    
                    # Apply theme to weather widget immediately
                    self._apply_weather_theme(main_window)
                    
                    # Start initial weather fetch (non-blocking) only if manager is new
                    if not hasattr(self, '_weather_fetch_started'):
                        QTimer.singleShot(100, self._fetch_weather_data)
                        self._weather_fetch_started = True

            else:
                logger.info("Weather widgets skipped (disabled or no config)")
                # CRITICAL FIX: Don't override user's manual visibility preference
                # Only hide if this is the first initialization
                if main_window.weather_widget and not hasattr(main_window, '_weather_widget_initialized'):
                    # CRITICAL FIX: Don't override user's manual visibility preference
                    # Only set visibility based on config if user hasn't manually changed it
                    if not hasattr(main_window.weather_widget, '_user_manually_hidden'):
                        main_window.weather_widget.setVisible(False)
                        logger.debug("Weather widget set hidden during initialization (weather disabled)")
                    else:
                        logger.debug("Weather widget visibility preserved during initialization (user preference)")
                    main_window._weather_widget_initialized = True
                    logger.debug("Weather widget visibility set to False (first initialization)")
            
            self.weather_initialized.emit()
            
        except Exception as e:
            logger.error(f"Weather widget initialization failed: {e}")
            raise
    
    def _initialize_train_widgets(self, main_window) -> None:
        """Initialize train widgets and manager."""
        try:
            logger.debug("Initializing train widgets...")
            
            # Train widgets are already created in main_window.setup_ui()
            # Just ensure they're visible and configured
            if main_window.train_list_widget:
                main_window.train_list_widget.setVisible(True)
                
                # Train manager will be created and connected in main.py
                # This just ensures the widget is ready

            self.train_initialized.emit()
            
        except Exception as e:
            logger.error(f"Train widget initialization failed: {e}")
            raise
    
    def _initialize_astronomy_widgets(self, main_window) -> None:
        """Initialize astronomy widgets with parallel data fetching."""
        try:
            logger.debug("Initializing astronomy widgets...")
            
            # CRITICAL FIX: Only initialize if astronomy widget actually exists
            # This prevents trying to initialize astronomy when it's disabled
            if not main_window.astronomy_widget:
                logger.info("Astronomy widgets skipped (astronomy widget does not exist - astronomy disabled)")
                self.astronomy_initialized.emit()
                return
            
            # Initialize astronomy manager if config available
            if (self.config and
                hasattr(self.config, "astronomy") and
                self.config.astronomy and
                self.config.astronomy.enabled):
                
                # Phase 2 boundary: bootstrap composes AstronomyManager.
                # InitializationManager may only wire an injected instance.
                if not self.astronomy_manager:
                    self.astronomy_manager = getattr(main_window, "astronomy_manager", None)

                if not self.astronomy_manager:
                    logger.warning(
                        "Astronomy is enabled in config but no AstronomyManager was injected; skipping astronomy wiring"
                    )
                    self.astronomy_initialized.emit()
                    return
                
                # Connect to main window's astronomy widget (we know it exists now)
                # Only connect signals if not already connected
                if not hasattr(main_window.astronomy_widget, '_initialization_signals_connected'):
                    # Connect signals
                    self.astronomy_manager.astronomy_updated.connect(
                        main_window.astronomy_widget.on_astronomy_updated
                    )
                    self.astronomy_manager.astronomy_error.connect(
                        main_window.astronomy_widget.on_astronomy_error
                    )
                    self.astronomy_manager.loading_state_changed.connect(
                        main_window.astronomy_widget.on_astronomy_loading
                    )
                    main_window.astronomy_widget._initialization_signals_connected = True
                
                # Update widget config
                main_window.astronomy_widget.update_config(self.config.astronomy)
                
                # CRITICAL FIX: Don't override user's manual visibility preference
                # Only set visible if this is the first initialization
                if not hasattr(main_window, '_astronomy_widget_initialized'):
                    main_window.astronomy_widget.setVisible(True)
                    main_window._astronomy_widget_initialized = True
                    logger.debug("Astronomy widget visibility set to True (first initialization)")
                else:
                    logger.debug("Astronomy widget visibility preserved (user preference)")
                
                # Start parallel astronomy data fetching (API-free mode) only if manager is new
                if not hasattr(self, '_astronomy_fetch_started'):
                    self._start_parallel_astronomy_fetch()
                    self._astronomy_fetch_started = True
                    logger.debug("Astronomy data fetch started in parallel")

            else:
                logger.info("Astronomy widgets skipped (disabled or no config)")
                # CRITICAL FIX: Don't override user's manual visibility preference
                # Only hide if this is the first initialization
                if not hasattr(main_window, '_astronomy_widget_initialized'):
                    main_window.astronomy_widget.setVisible(False)
                    main_window._astronomy_widget_initialized = True
                    logger.debug("Astronomy widget visibility set to False (first initialization)")
            
            self.astronomy_initialized.emit()
            
        except Exception as e:
            logger.error(f"Astronomy widget initialization failed: {e}")
            raise
    
    def _start_parallel_astronomy_fetch(self) -> None:
        """Start parallel astronomy data fetching in background thread."""
        # Phase 2 boundary: background data fetching orchestration moved out.
        # Keep the method as a no-op for compatibility.
        return
    
    def _fetch_weather_data(self) -> None:
        """Fetch initial weather data (non-blocking)."""
        # Phase 2 boundary: background data fetching orchestration moved out.
        return
    
    def _apply_weather_theme(self, main_window) -> None:
        """Apply theme to weather widget based on main window's current theme."""
        # Phase 2 boundary: theming is owned by UI/theme system.
        return
    
    def _on_astronomy_data_fetched(self, forecast_data) -> None:
        """Handle astronomy data fetch completion."""
        # Phase 2 boundary: fetching moved out.
        return
    
    def _on_astronomy_fetch_error(self, error_message: str) -> None:
        """Handle astronomy data fetch error."""
        return
    
    def _on_astronomy_fetch_started(self) -> None:
        """Handle astronomy fetch start."""
        return
    
    def _on_astronomy_fetch_completed(self) -> None:
        """Handle astronomy fetch completion."""
        return
    
    def shutdown(self) -> None:
        """Shutdown initialization manager and cleanup resources."""
        logger.debug("Shutting down initialization manager...")
        
        # Stop astronomy worker if running
        if self.astronomy_worker and self.astronomy_worker.isRunning():
            self.astronomy_worker.stop()
            self.astronomy_worker.wait(3000)  # Wait up to 3 seconds
            if self.astronomy_worker.isRunning():
                logger.warning("Astronomy worker thread did not stop gracefully")
                self.astronomy_worker.terminate()
        
        # Shutdown managers
        if self.weather_manager:
            self.weather_manager.shutdown()
            
        if self.astronomy_manager:
            self.astronomy_manager.shutdown()
            
        logger.debug("Initialization manager shutdown complete")
    
    def get_initialization_stats(self) -> dict:
        """Get initialization performance statistics."""
        return {
            "is_initializing": self.is_initializing,
            "has_weather_manager": self.weather_manager is not None,
            "has_astronomy_manager": self.astronomy_manager is not None,
            "has_train_manager": self.train_manager is not None,
            "initialization_time": (
                time.time() - self.initialization_start_time
                if self.initialization_start_time > 0
                else 0
            ),
        }
