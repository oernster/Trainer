"""
Refactored Main window for the Train Times application.
Author: Oliver Ernster

This module contains the primary application window refactored to use
manager classes for better separation of concerns and maintainability.
"""

import logging
from typing import Any, List, Optional, TYPE_CHECKING
from PySide6.QtWidgets import (
    QMainWindow,
)
from PySide6.QtCore import QTimer, Signal, Qt
from PySide6.QtGui import QCloseEvent
from ..models.train_data import TrainData
from ..managers.train_manager import TrainManager
from ..managers.config_manager import ConfigManager
from ..managers.config_models import ConfigurationError
from ..managers.theme_manager import ThemeManager
from ..managers.weather_manager import WeatherManager
from ..managers.astronomy_manager import AstronomyManager
from ..managers.initialization_manager import InitializationManager

if TYPE_CHECKING:  # pragma: no cover
    from src.cache.station_cache_manager import StationCacheManager
    from src.services.routing.essential_station_cache import EssentialStationCache
from .managers import (
    UILayoutManager,
    WidgetLifecycleManager,
    EventHandlerManager,
    SettingsDialogManager
)
from .main_window_components.astronomy_enable_flow import (
    on_astronomy_data_ready_after_enable,
    on_astronomy_enable_requested,
    on_astronomy_error_after_enable,
    show_astronomy_enabled_message,
)
from .main_window_components.details_dialogs import show_route_details, show_train_details
from .main_window_components.dialog_route_update import on_dialog_route_updated
from .main_window_components.info_dialogs import (
    show_about_dialog,
    show_error_message,
    show_info_message,
)
from .main_window_components.initialization import initialize_main_window
from .main_window_components.route_display import update_route_display
from .main_window_components.settings_reload import (
    check_settings_changes_need_refresh,
    on_settings_saved,
)
from .main_window_components.theme import (
    apply_theme,
    apply_theme_to_all_widgets,
    get_theme_colors,
    on_theme_changed,
    setup_theme_system,
)
from .main_window_components.train_display import update_train_display
from .main_window_components.weather_astronomy_update import (
    update_astronomy_system,
    update_weather_system,
)

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """
    Refactored main application window using manager classes.

    Features:
    - Light/Dark theme switching (defaults to dark)
    - Unicode train emoji (🚂) in window title and about dialog
    - Scheduled train data display
    - 16-hour time window
    - Automatic and manual refresh
    - Modular manager-based architecture
    """

    # Signals
    refresh_requested = Signal()
    theme_changed = Signal(str)
    astronomy_manager_ready = Signal()  # Signal for when astronomy manager is ready
    route_changed = Signal(str, str)  # Signal for when route changes (from_name, to_name)
    config_updated = Signal(object)  # Signal for when configuration is updated

    # ---------------------------------------------------------------------
    # Injected dependencies (composition root owns construction)
    # ---------------------------------------------------------------------
    # These are set by [`python.bootstrap_app()`](src/app/bootstrap.py:64).
    train_manager: Optional[TrainManager]
    weather_manager: Optional[WeatherManager]
    astronomy_manager: Optional[AstronomyManager]
    initialization_manager: Optional[InitializationManager]
    essential_station_cache: "EssentialStationCache | None"
    station_cache_manager: "StationCacheManager | None"

    # Always present after bootstrap, but keep Optional for static analysis.
    config_manager: Optional[ConfigManager]

    # UI wiring (populated by `initialize_main_window`)
    config: Any
    theme_manager: ThemeManager
    ui_layout_manager: Any
    widget_lifecycle_manager: Any
    event_handler_manager: Any
    settings_dialog_manager: Any

    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """Create the MainWindow shell.

        Phase 2 boundary: this constructor must not assemble the object graph.
        Long-lived managers/services are injected by
        [`python.bootstrap_app()`](src/app/bootstrap.py:64).
        """

        super().__init__()

        # Keep for compatibility: bootstrap will re-assign the injected instance.
        self.config_manager = config_manager

    # ---------------------------------------------------------------------
    # Compatibility shims
    # ---------------------------------------------------------------------
    # The app historically exposed widgets directly on `MainWindow`.
    # After the UI refactor, widget ownership moved under `UILayoutManager`.
    # Keep these properties so non-refactored code paths (e.g. older managers)
    # can still access the widgets.

    @property
    def weather_widget(self) -> Any:
        ui_layout_manager = getattr(self, "ui_layout_manager", None)
        return getattr(ui_layout_manager, "weather_widget", None)

    @property
    def train_list_widget(self) -> Any:
        ui_layout_manager = getattr(self, "ui_layout_manager", None)
        return getattr(ui_layout_manager, "train_list_widget", None)

    @property
    def astronomy_widget(self) -> Any:
        ui_layout_manager = getattr(self, "ui_layout_manager", None)
        return getattr(ui_layout_manager, "astronomy_widget", None)

    def setup_theme_system(self):
        """Setup theme switching system."""
        setup_theme_system(window=self)

    def setup_weather_system(self):
        """Setup weather integration system."""
        self.widget_lifecycle_manager.setup_weather_system()

    def setup_astronomy_system(self):
        """Setup astronomy integration system."""
        self.widget_lifecycle_manager.setup_astronomy_system()

    def toggle_theme(self):
        """Toggle between light and dark themes."""
        self.theme_manager.switch_theme()

        # Update config if available
        if self.config:
            self.config.display.theme = self.theme_manager.current_theme
            try:
                if self.config_manager:
                    self.config_manager.save_config(self.config)
                logger.info(f"Theme switched to {self.theme_manager.current_theme}")
            except ConfigurationError as e:
                logger.error(f"Failed to save theme setting: {e}")

    def on_theme_changed(self, theme_name: str):
        """Handle theme change."""
        on_theme_changed(window=self, theme_name=theme_name)

    def _get_theme_colors(self, theme_name: str) -> dict:
        """Get theme colors dictionary for widgets."""
        return get_theme_colors(theme_name=theme_name)

    def apply_theme(self):
        """Apply current theme styling."""
        apply_theme(window=self)

    def apply_theme_to_all_widgets(self):
        """Apply theme to all widgets after creation."""
        apply_theme_to_all_widgets(window=self)

    def manual_refresh(self):
        """Trigger manual refresh of train data."""
        self.refresh_requested.emit()
        logger.info("Manual refresh requested")

    def refresh_weather(self):
        """Trigger manual weather refresh."""
        self.event_handler_manager.refresh_weather()

    def refresh_astronomy(self):
        """Trigger manual astronomy refresh."""
        self.event_handler_manager.refresh_astronomy()

    def update_route_display(self, from_station: str, to_station: str, via_stations: Optional[List[str]] = None):
        """
        Update route display (header removed - now only logs route info).
        
        Args:
            from_station: Origin station name
            to_station: Destination station name
            via_stations: Optional list of via stations
        """
        update_route_display(
            window=self,
            from_station=from_station,
            to_station=to_station,
            via_stations=via_stations,
        )

    def update_train_display(self, trains: List[TrainData]):
        """
        Update train list display.

        Args:
            trains: List of train data to display
        """
        update_train_display(window=self, trains=trains)

    def update_last_update_time(self, timestamp: str):
        """
        Update last update timestamp (header removed - now only logs).

        Args:
            timestamp: Formatted timestamp string
        """
        # Header removed - last update time no longer shown in UI, only logged
        logger.debug(f"Last Updated: {timestamp}")

    def update_connection_status(self, connected: bool, message: str = ""):
        """
        Update connection status.

        Args:
            connected: Whether connected to API
            message: Optional status message
        """
        # Status bar removed - this method is kept for compatibility but does nothing
        pass

    # Event handler delegates
    def on_weather_updated(self, weather_data):
        """Handle weather data update."""
        self.event_handler_manager.on_weather_updated(weather_data)

    def on_weather_error(self, error_message: str):
        """Handle weather error."""
        self.event_handler_manager.on_weather_error(error_message)

    def on_weather_loading_changed(self, is_loading: bool):
        """Handle weather loading state change."""
        self.event_handler_manager.on_weather_loading_changed(is_loading)

    def on_astronomy_updated(self, astronomy_data):
        """Handle astronomy data update."""
        self.event_handler_manager.on_astronomy_updated(astronomy_data)

    def on_astronomy_error(self, error_message: str):
        """Handle astronomy error."""
        self.event_handler_manager.on_astronomy_error(error_message)

    def on_astronomy_loading_changed(self, is_loading: bool):
        """Handle astronomy loading state change."""
        self.event_handler_manager.on_astronomy_loading_changed(is_loading)

    def on_astronomy_link_clicked(self, url: str):
        """Handle astronomy link clicks."""
        self.event_handler_manager.on_astronomy_link_clicked(url)

    # Settings dialog delegates
    def show_stations_settings_dialog(self):
        """Show stations settings dialog."""
        self.settings_dialog_manager.show_stations_settings_dialog()

    def show_astronomy_settings_dialog(self):
        """Show astronomy settings dialog."""
        self.settings_dialog_manager.show_astronomy_settings_dialog()

    def show_about_dialog(self):
        """Show about dialog using centralized version system."""
        show_about_dialog(window=self)

    def show_error_message(self, title: str, message: str):
        """
        Show error message dialog.

        Args:
            title: Dialog title
            message: Error message
        """
        show_error_message(window=self, title=title, message=message)

    def show_info_message(self, title: str, message: str):
        """
        Show information message dialog.

        Args:
            title: Dialog title
            message: Information message
        """
        show_info_message(window=self, title=title, message=message)

    def on_settings_saved(self):
        """Handle settings saved event."""
        on_settings_saved(window=self)

    def _check_settings_changes_need_refresh(self, old_time_window, old_train_lookahead, 
                                           old_avoid_walking, old_max_walking_distance,
                                           old_prefer_direct, old_max_changes) -> bool:
        """Check if settings changes require train data refresh."""
        return check_settings_changes_need_refresh(
            config=self.config,
            old_time_window=old_time_window,
            old_train_lookahead=old_train_lookahead,
            old_avoid_walking=old_avoid_walking,
            old_max_walking_distance=old_max_walking_distance,
            old_prefer_direct=old_prefer_direct,
            old_max_changes=old_max_changes,
        )

    def _update_weather_system(self):
        """Update weather system after configuration change."""
        update_weather_system(window=self)

    def _update_astronomy_system(self):
        """Update astronomy system after configuration change."""
        update_astronomy_system(window=self)

    def _on_dialog_route_updated(self, route_data: dict):
        """Handle route updates from the settings dialog during preference changes."""
        on_dialog_route_updated(window=self, route_data=route_data)

    def connect_signals(self):
        """Connect internal signals."""
        # Connect astronomy manager ready signal to trigger data fetch
        self.astronomy_manager_ready.connect(self._on_astronomy_manager_ready)

    def _on_astronomy_manager_ready(self):
        """Handle astronomy manager ready signal - trigger immediate data fetch."""
        if self.astronomy_manager:
            logger.debug("Astronomy manager ready signal received - triggering data fetch")
            self.refresh_astronomy()
            
            # Start auto-refresh if enabled
            if (self.config and
                hasattr(self.config, "astronomy") and
                self.config.astronomy and
                self.config.astronomy.enabled):
                self.astronomy_manager.start_auto_refresh()
                logger.debug("Auto-refresh started for newly configured astronomy")
        else:
            logger.warning("Astronomy manager ready signal received but no manager available")

    def on_astronomy_enable_requested(self):
        """Handle astronomy enable request from settings dialog."""
        on_astronomy_enable_requested(window=self)

    def _on_astronomy_data_ready_after_enable(self, forecast_data):
        """Handle astronomy data ready after enable request."""
        on_astronomy_data_ready_after_enable(window=self, forecast_data=forecast_data)

    def _on_astronomy_error_after_enable(self, error_message):
        """Handle astronomy error after enable request."""
        on_astronomy_error_after_enable(window=self, error_message=error_message)

    def _show_astronomy_enabled_message(self):
        """Show the astronomy enabled success message."""
        show_astronomy_enabled_message(window=self)

    def showEvent(self, event):
        """Handle window show event - trigger astronomy data fetch when UI is displayed."""
        super().showEvent(event)

        # Only fetch astronomy data once when window is first shown
        if not hasattr(self, "_astronomy_data_fetched"):
            self._astronomy_data_fetched = True
            if self.astronomy_manager:
                logger.debug("UI displayed - emitting astronomy manager ready signal")
                self.astronomy_manager_ready.emit()

    def resizeEvent(self, event):
        """Handle window resize event - reposition header buttons."""
        super().resizeEvent(event)
        # Delegate to UI layout manager
        self.ui_layout_manager.handle_resize_event(event)

    def closeEvent(self, event: QCloseEvent):
        """Handle window close event."""
        self.event_handler_manager.handle_close_event(event)

    def show_train_details(self, train_data: TrainData):
        """
        Show detailed train information dialog.
        
        Args:
            train_data: Train data to display in detail
        """
        show_train_details(window=self, train_data=train_data)

    def show_route_details(self, train_data: TrainData):
        """
        Show route display dialog with all calling points.
        
        Args:
            train_data: Train data to display route for
        """
        show_route_details(window=self, train_data=train_data)

    def _start_optimized_initialization(self) -> None:
        """Start the optimized widget initialization process."""
        if self.initialization_manager:
            self.initialization_manager.initialize_widgets(self)
        else:
            logger.warning("Cannot start optimized initialization: no initialization manager")

    def _on_initialization_completed(self) -> None:
        """Handle completion of optimized widget initialization."""
        # Update managers from initialization manager
        if self.initialization_manager:
            self.weather_manager = self.initialization_manager.weather_manager
            self.astronomy_manager = self.initialization_manager.astronomy_manager
        
        # Ensure menu states are synchronized with actual widget visibility after initialization
        QTimer.singleShot(50, self._final_menu_sync)
        logger.debug("Final menu sync scheduled after initialization completion")
    
    def _final_menu_sync(self):
        """Final menu synchronization after all initialization is complete."""
        widgets = self.ui_layout_manager.get_widgets()
        weather_widget = widgets.get('weather_widget')
        astronomy_widget = widgets.get('astronomy_widget')
        
        # Ensure both widgets are initialized
        if weather_widget and astronomy_widget:
            logger.debug("Final menu states synchronized with widget visibility")
            
            # Log current states for debugging
            weather_visible = weather_widget.isVisible()
            astronomy_visible = astronomy_widget.isVisible()
        else:
            # Retry sync after a short delay if widgets aren't ready
            QTimer.singleShot(100, self._final_menu_sync)
            logger.debug("Widgets not ready for menu sync, retrying in 100ms")

        # Start hourly top-of-hour refresh once the UI is fully initialized.
        try:
            self.event_handler_manager.setup_refresh_timer()
        except Exception as e:
            logger.warning(f"Failed to start hourly refresh timer: {e}")

    def show(self):
        """Override show to properly remove invisible attributes when ready."""
        # Remove all invisible attributes and restore normal visibility
        self.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, False)
        self.setWindowOpacity(1.0)  # Restore full opacity
        
        # Move window back to center before showing
        self.ui_layout_manager._center_window()
        
        # Now show the window normally
        self.setVisible(True)
        super().show()
        logger.debug("Main window shown with all invisible attributes removed")
