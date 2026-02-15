"""
Weather Widget

Main weather display widget with two horizontal layers.
"""

import logging
from typing import Optional, Dict, List
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QSizePolicy
from PySide6.QtCore import Signal, QTimer
from PySide6.QtGui import QFont

from ...models.weather_data import WeatherForecastData
from ...managers.weather_config import WeatherConfig
from .hourly_forecast_widget import HourlyForecastWidget
from .daily_forecast_widget import DailyForecastWidget

logger = logging.getLogger(__name__)


class WeatherWidget(QWidget):
    """
    Main weather display widget with two horizontal layers.

    Implements WeatherObserver interface to receive weather updates.
    Follows Composite pattern to manage child widgets.
    """

    # Signals for weather widget events
    weather_refresh_requested = Signal()
    weather_settings_requested = Signal()

    def __init__(self, parent=None, scale_factor=1.0):
        """Initialize weather widget."""
        super().__init__(parent)
        self._scale_factor = scale_factor

        # Child widgets
        self._daily_label: Optional[QLabel] = None
        self._weekly_label: Optional[QLabel] = None
        self._daily_forecast_widget: Optional[HourlyForecastWidget] = None
        self._weekly_forecast_widget: Optional[DailyForecastWidget] = None
        self._status_label: Optional[QLabel] = None

        # State
        self._current_forecast: Optional[WeatherForecastData] = None
        self._config: Optional[WeatherConfig] = None
        self._is_loading = False
        
        # Track user's manual visibility preference to prevent automatic overrides
        self._user_manually_hidden: bool = False

        # Auto-hide timer for error messages
        self._status_timer = QTimer()
        self._status_timer.setSingleShot(True)
        self._status_timer.timeout.connect(self._clear_status)

        self.setup_ui()
        logger.debug("WeatherWidget initialized")

    def setup_ui(self) -> None:
        """Setup the weather widget UI."""
        # Main layout with zero top padding to maximize content space
        scaled_margin_h = int(4 * self._scale_factor)  # Horizontal margins
        scaled_margin_top = 0  # Zero top margin to move content to very top
        scaled_margin_bottom = int(4 * self._scale_factor)  # Bottom margin
        scaled_spacing = int(4 * self._scale_factor)  # Further reduced spacing
        layout = QVBoxLayout(self)
        layout.setContentsMargins(scaled_margin_h, scaled_margin_top, scaled_margin_h, scaled_margin_bottom)
        layout.setSpacing(scaled_spacing)

        # Daily forecast section
        self._daily_label = QLabel("Today's Weather (3-hourly)")
        scaled_font_size = int(10 * self._scale_factor)
        self._daily_label.setFont(QFont("Arial", scaled_font_size, QFont.Weight.Bold))
        layout.addWidget(self._daily_label)

        self._daily_forecast_widget = HourlyForecastWidget(scale_factor=self._scale_factor)
        layout.addWidget(self._daily_forecast_widget)

        # Reduced spacing before the 7-Day Forecast label for more compact layout
        scaled_extra_spacing = int(10 * self._scale_factor)  # Reduced from 35 to 10
        layout.addSpacing(scaled_extra_spacing)

        # Weekly forecast section
        self._weekly_label = QLabel("7-Day Forecast")
        self._weekly_label.setFont(QFont("Arial", scaled_font_size, QFont.Weight.Bold))
        layout.addWidget(self._weekly_label)

        self._weekly_forecast_widget = DailyForecastWidget(scale_factor=self._scale_factor)
        layout.addWidget(self._weekly_forecast_widget)

        # Status label removed - no longer needed

        # Set size policy with reasonable height (scaled)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        # Further increased height to prevent truncation of humidity values
        if self._scale_factor < 1.0:  # Small screens
            base_height = 330  # Increased from 310 to 330 to prevent cut-off
        else:  # Large screens
            base_height = 370  # Increased from 350 to 370 to prevent cut-off
        scaled_height = int(base_height * self._scale_factor)
        self.setFixedHeight(scaled_height)

    def update_config(self, config: WeatherConfig) -> None:
        """Update weather configuration."""
        self._config = config

        # Update child widgets
        if self._daily_forecast_widget:
            for item in self._daily_forecast_widget._weather_items:
                item.update_config(config)

        if self._weekly_forecast_widget:
            for item in self._weekly_forecast_widget._weather_items:
                item.update_config(config)

        # CRITICAL FIX: Don't override user's manual visibility preference
        # Never automatically set visibility based on config.enabled during updates
        # The visibility should only be controlled by user actions, not config updates
        if not hasattr(self, '_config_visibility_set'):
            # Only set visibility on the very first initialization, not on subsequent updates
            self.setVisible(config.enabled)
            self._config_visibility_set = True
            logger.debug(f"Weather widget visibility set to {config.enabled} (initial setup only)")
        else:
            # ALWAYS preserve user's manual visibility preference during any config update
            current_visibility = self.isVisible()
            logger.debug(f"Weather widget visibility preserved during config update: {current_visibility} (user preference)")
            # Do NOT call setVisible() here - this was causing the widget to reappear

    def apply_theme(self, theme_colors: Dict[str, str]) -> None:
        """Apply theme to weather widget and children."""
        # Apply theme to child widgets
        if self._daily_forecast_widget:
            self._daily_forecast_widget.apply_theme(theme_colors)

        if self._weekly_forecast_widget:
            self._weekly_forecast_widget.apply_theme(theme_colors)

        # Apply theme to labels
        text_color = theme_colors.get("primary_accent", "#1976d2")
        bg_color = theme_colors.get("background_primary", "#1a1a1a")

        label_style = f"""
        QLabel {{
            color: {text_color};
            background: transparent;
            padding: 2px;
        }}
        """

        if self._daily_label:
            self._daily_label.setStyleSheet(label_style)

        if self._weekly_label:
            self._weekly_label.setStyleSheet(label_style)

        # Apply theme to main widget - make completely transparent to blend with main window
        widget_style = f"""
        WeatherWidget {{
            background: transparent;
            border: none;
            border-radius: 0px;
            margin: 0px;
            padding: 0px;
        }}
        WeatherWidget QWidget {{
            background: transparent;
            border: none;
            margin: 0px;
            padding: 0px;
        }}
        WeatherWidget QFrame {{
            background: transparent;
            border: none;
            margin: 0px;
            padding: 0px;
        }}
        """
        self.setStyleSheet(widget_style)

    # WeatherObserver implementation
    def on_weather_updated(self, weather_data: WeatherForecastData) -> None:
        """Handle weather data update."""
        self._current_forecast = weather_data

        # Update daily forecast (3-hourly for current day)
        if self._daily_forecast_widget:
            today_hourly = weather_data.current_day_hourly
            self._daily_forecast_widget.update_hourly_forecast(
                today_hourly, self._config
            )

        # Update weekly forecast
        if self._weekly_forecast_widget:
            self._weekly_forecast_widget.update_daily_forecast(
                weather_data.daily_forecast, self._config
            )

        # Status updates removed - no longer showing status messages

        logger.debug("Weather widget updated with new forecast data")

    def on_weather_error(self, error: Exception) -> None:
        """Handle weather error."""
        # Status messages disabled - only log errors
        logger.error(f"Weather widget received error: {error}")

    def on_weather_loading(self, is_loading: bool) -> None:
        """Handle weather loading state change."""
        self._is_loading = is_loading

        # Loading status messages removed - no longer showing status
        pass

    def _show_status(self, message: str, is_error: bool = False) -> None:
        """Show status message - disabled."""
        # Status messages disabled to eliminate unwanted widget below weather sections
        pass

    def _clear_status(self) -> None:
        """Clear status message - disabled."""
        # Status messages disabled
        pass

    def get_current_forecast(self) -> Optional[WeatherForecastData]:
        """Get current weather forecast."""
        return self._current_forecast

    def is_loading(self) -> bool:
        """Check if weather data is loading."""
        return self._is_loading

    def refresh_weather(self) -> None:
        """Request weather refresh."""
        self.weather_refresh_requested.emit()

    def show_weather_settings(self) -> None:
        """Request weather settings dialog."""
        self.weather_settings_requested.emit()