"""
Weather Display Component

Abstract base class for weather display components.
"""

import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Signal

from ...models.weather_data import WeatherData
from ...managers.weather_config import WeatherConfig

logger = logging.getLogger(__name__)


class WeatherDisplayComponent(QWidget):
    """
    Abstract base class for weather display components.

    Follows Liskov Substitution Principle - derived classes are
    fully substitutable for this base class.
    """

    # Signals for weather widget interactions
    weather_item_clicked = Signal(object)  # WeatherData
    weather_item_hovered = Signal(object)  # WeatherData

    def __init__(self, parent=None):
        """Initialize weather display component."""
        super().__init__(parent)
        self._weather_data: Optional[WeatherData] = None
        self._config: Optional[WeatherConfig] = None
        self._theme_colors: Dict[str, str] = {}
        self.setup_ui()

    @abstractmethod
    def setup_ui(self) -> None:
        """Setup the user interface."""
        pass

    def update_weather_data(self, weather_data: WeatherData) -> None:
        """Update weather data and refresh display."""
        self._weather_data = weather_data
        self._refresh_display()

    def update_config(self, config: WeatherConfig) -> None:
        """Update weather configuration."""
        self._config = config
        self._refresh_display()

    @abstractmethod
    def _refresh_display(self) -> None:
        """Refresh the display with current weather data."""
        pass

    def apply_theme(self, theme_colors: Dict[str, str]) -> None:
        """Apply theme colors to the widget."""
        self._theme_colors = theme_colors
        self._apply_theme_styling()

    @abstractmethod
    def _apply_theme_styling(self) -> None:
        """Apply theme-specific styling."""
        pass

    def get_weather_data(self) -> Optional[WeatherData]:
        """Get current weather data."""
        return self._weather_data