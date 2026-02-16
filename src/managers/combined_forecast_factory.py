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

        # Phase 2 directive: factories must not assemble the object graph.
        # Keep this helper for call sites that expect a CombinedForecastManager,
        # but require composition root to inject the concrete managers.
        return CombinedForecastManager(None, None)

    @staticmethod
    def create_weather_only_manager(weather_config: WeatherConfig) -> CombinedForecastManager:
        """Create combined manager with only weather data."""
        # Phase 2 directive: composition root must inject WeatherManager.
        return CombinedForecastManager(None, None)

    @staticmethod
    def create_astronomy_only_manager(
        astronomy_config: AstronomyConfig,
    ) -> CombinedForecastManager:
        """Create combined manager with only astronomy data."""
        # Phase 2 directive: composition root must inject AstronomyManager.
        return CombinedForecastManager(None, None)

    @staticmethod
    def create_test_manager() -> CombinedForecastManager:
        """Create combined manager for testing."""
        return CombinedForecastManager(None, None)

