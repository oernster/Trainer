"""
Weather Forecast Widget

Base class for weather forecast display widgets.
"""

import logging
from typing import List, Optional, Dict
from PySide6.QtWidgets import QWidget, QHBoxLayout
from PySide6.QtCore import Qt

from ...models.weather_data import WeatherData
from ...managers.weather_config import WeatherConfig
from .weather_item_widget import WeatherItemWidget

logger = logging.getLogger(__name__)


class WeatherForecastWidget(QWidget):
    """
    Simple weather forecast display widget with guaranteed rounded corners.

    Uses QWidget for clean, direct styling control.
    """

    def __init__(self, parent=None, scale_factor=1.0):
        """Initialize forecast widget."""
        super().__init__(parent)
        self._scale_factor = scale_factor
        self._weather_items: List[WeatherItemWidget] = []
        self._container_layout: QHBoxLayout
        self.setup_ui()

    def setup_ui(self) -> None:
        """Setup the forecast widget UI."""
        # Scale height based on screen size - increase for large screens to prevent cutoff
        if self._scale_factor < 1.0:  # Small screens
            base_height = 160
        else:  # Large screens
            base_height = 180  # Increased for large screens to accommodate taller items
        scaled_height = int(base_height * self._scale_factor)
        self.setFixedHeight(scaled_height)

        # Simple horizontal layout for weather items (scaled) - centered distribution
        self._container_layout = QHBoxLayout(self)
        scaled_margin_h = int(8 * self._scale_factor)
        scaled_margin_v = 0  # Zero vertical margins to maximize space
        self._container_layout.setContentsMargins(scaled_margin_h, scaled_margin_v, scaled_margin_h, scaled_margin_v)

    def update_weather_forecast(
        self,
        weather_data: List[WeatherData],
        is_daily: bool = False,
        config: Optional[WeatherConfig] = None,
    ) -> None:
        """
        Update weather forecast display.

        Args:
            weather_data: List of weather data to display
            is_daily: Whether this is daily forecast data
            config: Weather configuration
        """
        # Clear existing items
        self.clear_weather_items()

        # Add leading stretch to center the items
        self._container_layout.addStretch(1)

        # Create weather items with proper spacing and centering
        for i, weather in enumerate(weather_data):
            item = WeatherItemWidget(weather, is_daily, scale_factor=self._scale_factor)
            if config:
                item.update_config(config)

            # Connect signals
            item.weather_item_clicked.connect(self._on_weather_item_clicked)
            item.weather_item_hovered.connect(self._on_weather_item_hovered)

            self._weather_items.append(item)
            self._container_layout.addWidget(item, 0)  # Fixed size, no stretch
            
            # Add spacing between items (except after the last one)
            if i < len(weather_data) - 1:
                scaled_spacing = int(4 * self._scale_factor)
                self._container_layout.addSpacing(scaled_spacing)

        # Add trailing stretch to center the items
        self._container_layout.addStretch(1)

        logger.debug(f"Updated weather forecast with {len(weather_data)} items")

    def clear_weather_items(self) -> None:
        """Clear all weather items."""
        for item in self._weather_items:
            item.deleteLater()
        self._weather_items.clear()

        # Clear layout
        while self._container_layout.count():
            child = self._container_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def apply_theme(self, theme_colors: Dict[str, str]) -> None:
        """Apply theme to all weather items and frame."""
        for item in self._weather_items:
            item.apply_theme(theme_colors)

        # Make the forecast container completely transparent to allow weather items to blend with main window
        self.setStyleSheet(
            f"""
            background: transparent !important;
            border: none !important;
            border-radius: 0px !important;
            margin: 0px !important;
            padding: 0px !important;
        """
        )

    def _on_weather_item_clicked(self, weather_data: WeatherData) -> None:
        """Handle weather item click."""
        logger.info(f"Weather item clicked: {weather_data.timestamp}")

    def _on_weather_item_hovered(self, weather_data: WeatherData) -> None:
        """Handle weather item hover."""
        # Could show tooltip or status bar message
        pass