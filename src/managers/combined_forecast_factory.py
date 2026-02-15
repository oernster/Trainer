"""Factory helpers for [`CombinedForecastManager`](src/managers/combined_forecast_manager.py:31).

Split out to keep modules under the <= 400 non-blank LOC gate.
"""

from __future__ import annotations

from typing import Optional

from .astronomy_config import AstronomyConfig
from .weather_config import WeatherConfig
from .combined_forecast_manager import CombinedForecastManager


class CombinedForecastFactory:
    """Factory for creating combined forecast managers."""

    @staticmethod
    def create_manager(
        weather_config: Optional[WeatherConfig] = None,
        astronomy_config: Optional[AstronomyConfig] = None,
    ) -> CombinedForecastManager:
        """Create combined forecast manager with given configurations."""

        weather_manager = None
        astronomy_manager = None

        if weather_config and weather_config.enabled:
            from .weather_manager import WeatherManager

            weather_manager = WeatherManager(weather_config)

        if astronomy_config and astronomy_config.enabled:
            from .astronomy_manager import AstronomyManager

            astronomy_manager = AstronomyManager(astronomy_config)

        return CombinedForecastManager(weather_manager, astronomy_manager)

    @staticmethod
    def create_weather_only_manager(weather_config: WeatherConfig) -> CombinedForecastManager:
        """Create combined manager with only weather data."""
        from .weather_manager import WeatherManager

        weather_manager = WeatherManager(weather_config)
        return CombinedForecastManager(weather_manager, None)

    @staticmethod
    def create_astronomy_only_manager(
        astronomy_config: AstronomyConfig,
    ) -> CombinedForecastManager:
        """Create combined manager with only astronomy data."""
        from .astronomy_manager import AstronomyManager

        astronomy_manager = AstronomyManager(astronomy_config)
        return CombinedForecastManager(None, astronomy_manager)

    @staticmethod
    def create_test_manager() -> CombinedForecastManager:
        """Create combined manager for testing."""
        return CombinedForecastManager(None, None)

