"""
Daily Forecast Widget

Widget for displaying daily weather forecast.
"""

import logging
from typing import List, Optional

from ...models.weather_data import WeatherData
from ...managers.weather_config import WeatherConfig
from .weather_forecast_widget import WeatherForecastWidget

logger = logging.getLogger(__name__)


class DailyForecastWidget(WeatherForecastWidget):
    """Widget for displaying daily weather forecast."""

    def __init__(self, parent=None, scale_factor=1.0):
        """Initialize daily forecast widget."""
        super().__init__(parent, scale_factor=scale_factor)

    def update_daily_forecast(
        self, daily_data: List[WeatherData], config: Optional[WeatherConfig] = None
    ) -> None:
        """Update daily forecast display."""
        self.update_weather_forecast(daily_data, is_daily=True, config=config)