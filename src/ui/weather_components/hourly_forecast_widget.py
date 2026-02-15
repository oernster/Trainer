"""
Hourly Forecast Widget

Widget for displaying hourly weather forecast.
"""

import logging
from typing import List, Optional

from ...models.weather_data import WeatherData
from ...managers.weather_config import WeatherConfig
from .weather_forecast_widget import WeatherForecastWidget

logger = logging.getLogger(__name__)


class HourlyForecastWidget(WeatherForecastWidget):
    """Widget for displaying hourly weather forecast."""

    def __init__(self, parent=None, scale_factor=1.0):
        """Initialize hourly forecast widget."""
        super().__init__(parent, scale_factor=scale_factor)

    def update_hourly_forecast(
        self, hourly_data: List[WeatherData], config: Optional[WeatherConfig] = None
    ) -> None:
        """Update hourly forecast display."""
        self.update_weather_forecast(hourly_data, is_daily=False, config=config)