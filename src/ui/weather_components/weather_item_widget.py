"""
Weather Item Widget

Individual weather display item widget.
"""

import logging
from typing import Optional, Dict
from PySide6.QtWidgets import QVBoxLayout, QLabel
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from ...models.weather_data import WeatherData, TemperatureUnit, default_weather_icon_provider
from .weather_display_component import WeatherDisplayComponent

logger = logging.getLogger(__name__)


class WeatherItemWidget(WeatherDisplayComponent):
    """
    Individual weather display item widget.

    Follows Single Responsibility Principle - only responsible for
    displaying a single weather data point.
    """

    def __init__(
        self,
        weather_data: Optional[WeatherData] = None,
        is_daily: bool = False,
        parent=None,
        scale_factor=1.0,
    ):
        """
        Initialize weather item widget.

        Args:
            weather_data: Weather data to display
            is_daily: Whether this is a daily forecast item
            parent: Parent widget
            scale_factor: UI scale factor for responsive design
        """
        self._is_daily = is_daily
        self._scale_factor = scale_factor
        self._time_label: Optional[QLabel] = None
        self._icon_label: Optional[QLabel] = None
        self._temp_label: Optional[QLabel] = None
        self._humidity_label: Optional[QLabel] = None

        super().__init__(parent)

        if weather_data:
            self.update_weather_data(weather_data)

    def setup_ui(self) -> None:
        """Setup the weather item UI."""
        # Scale widget size based on screen size - reasonable compact size for small screens
        if self._scale_factor < 1.0:  # Small screens
            base_width = 90 if self._is_daily else 80
            base_height = 130
        else:  # Large screens
            base_width = 120 if self._is_daily else 100
            base_height = 170 if self._is_daily else 150  # Increased height for daily forecast on large screens
        scaled_width = int(base_width * self._scale_factor)
        scaled_height = int(base_height * self._scale_factor)
        self.setFixedSize(scaled_width, scaled_height)

        # Main layout with minimal top margins to maximize space usage (scaled)
        layout = QVBoxLayout(self)
        scaled_margin_h = int(4 * self._scale_factor)
        scaled_margin_v_top = 0  # Zero top margin to eliminate space at top
        scaled_margin_v_bottom = int(8 * self._scale_factor)  # Reduced bottom margin
        scaled_spacing = int(1 * self._scale_factor)  # Minimal spacing
        layout.setContentsMargins(scaled_margin_h, scaled_margin_v_top, scaled_margin_h, scaled_margin_v_bottom)
        layout.setSpacing(scaled_spacing)

        # Time/Date label
        self._time_label = QLabel("--:--")
        self._time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scaled_font_size = int(8 * self._scale_factor)
        self._time_label.setFont(QFont("Arial", scaled_font_size))
        layout.addWidget(self._time_label)

        # Weather icon - reasonable size for smaller screens (scaled)
        self._icon_label = QLabel("❓")
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Use reasonable icon size for small screens - not too small
        base_icon_size = 32 if self._scale_factor < 1.0 else 48
        scaled_icon_size = int(base_icon_size * self._scale_factor)
        self._icon_label.setStyleSheet(
            f"font-size: {scaled_icon_size}px; font-family: 'Apple Color Emoji';"
        )
        layout.addWidget(self._icon_label)

        # Temperature
        self._temp_label = QLabel("--°")
        self._temp_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scaled_temp_font = int(10 * self._scale_factor)
        self._temp_label.setFont(QFont("Arial", scaled_temp_font, QFont.Weight.Bold))
        layout.addWidget(self._temp_label)

        # Humidity
        self._humidity_label = QLabel("--%")
        self._humidity_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._humidity_label.setFont(QFont("Arial", scaled_font_size))
        layout.addWidget(self._humidity_label)

        # Enable mouse tracking for hover effects
        self.setMouseTracking(True)

    def _refresh_display(self) -> None:
        """Refresh the display with current weather data."""
        if not self._weather_data:
            return

        # Update time/date display
        if self._time_label:
            time_text = self._get_time_display()
            self._time_label.setText(time_text)

        # Update weather icon
        if self._icon_label:
            icon = default_weather_icon_provider.get_weather_icon(
                self._weather_data.weather_code
            )
            self._icon_label.setText(icon)

        # Update temperature
        if self._temp_label:
            if self._config and not self._config.is_metric_units():
                temp_text = self._weather_data.get_temperature_display_in_unit(
                    TemperatureUnit.FAHRENHEIT
                )
            else:
                temp_text = self._weather_data.temperature_display
            self._temp_label.setText(temp_text)

        # Update humidity
        if self._humidity_label:
            show_humidity = not self._config or self._config.show_humidity
            if show_humidity:
                # Add "H:" prefix to make it clear this is humidity
                humidity_text = f"H:{self._weather_data.humidity}%"
                self._humidity_label.setText(humidity_text)
                self._humidity_label.show()
            else:
                self._humidity_label.hide()

    def _get_time_display(self) -> str:
        """Get formatted time display."""
        if not self._weather_data:
            return "--:--"

        if self._is_daily:
            # Show day name for daily forecast
            return self._weather_data.timestamp.strftime("%a")
        else:
            # Show time for hourly forecast
            return self._weather_data.timestamp.strftime("%H:%M")

    def _apply_theme_styling(self) -> None:
        """Apply theme-specific styling."""
        if not self._theme_colors:
            return

        # Get theme colors with fallbacks
        text_color = self._theme_colors.get("text_primary", "#ffffff")
        hover_color = self._theme_colors.get("background_hover", "#404040")
        accent_color = self._theme_colors.get("primary_accent", "#1976d2")

        # Apply styling with completely transparent background
        style = f"""
        WeatherItemWidget {{
            background: transparent;
            border: none;
            border-radius: 12px;
            color: {text_color};
            padding: 0px;
        }}
        WeatherItemWidget:hover {{
            background-color: {hover_color};
            border: 1px solid {accent_color};
        }}
        QLabel {{
            color: {text_color};
            background: transparent;
            border: none;
            margin: 0px;
            padding: 0px;
        }}
        """
        self.setStyleSheet(style)

    def mousePressEvent(self, event):
        """Handle mouse press events."""
        if event.button() == Qt.MouseButton.LeftButton and self._weather_data:
            self.weather_item_clicked.emit(self._weather_data)
        super().mousePressEvent(event)

    def enterEvent(self, event):
        """Handle mouse enter events."""
        if self._weather_data:
            self.weather_item_hovered.emit(self._weather_data)
        super().enterEvent(event)