"""
Weather UI widgets for the Trainer application.
Author: Oliver Ernster

This module contains weather display widgets following solid Object-Oriented
design principles with proper separation of concerns and theme integration.
"""

import logging
from typing import List, Optional, Dict, Any

# Import all components from the weather_components package
from .weather_components.weather_display_component import WeatherDisplayComponent
from .weather_components.weather_item_widget import WeatherItemWidget
from .weather_components.weather_forecast_widget import WeatherForecastWidget
from .weather_components.daily_forecast_widget import DailyForecastWidget
from .weather_components.hourly_forecast_widget import HourlyForecastWidget
from .weather_components.weather_widget import WeatherWidget

# Re-export all components
__all__ = [
    'WeatherDisplayComponent',
    'WeatherItemWidget',
    'WeatherForecastWidget',
    'DailyForecastWidget',
    'HourlyForecastWidget',
    'WeatherWidget'
]

logger = logging.getLogger(__name__)
logger.info("Weather widgets module loaded")
