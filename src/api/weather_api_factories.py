"""Factories for weather API components.

Split out of [`weather_api_manager`](src/api/weather_api_manager.py:1) to keep the
module under the <= 400 non-blank LOC gate.
"""

from __future__ import annotations

from ..managers.weather_config import WeatherConfig


class WeatherAPIFactory:
    """Factory for creating weather API managers."""

    @staticmethod
    def create_openmeteo_manager(config: WeatherConfig):
        """Create weather manager using Open-Meteo API."""
        from .weather_api_manager import AioHttpClient, OpenMeteoWeatherSource, WeatherAPIManager

        http_client = AioHttpClient(timeout_seconds=config.timeout_seconds)
        weather_source = OpenMeteoWeatherSource(http_client, config)
        return WeatherAPIManager(weather_source, config)

    @staticmethod
    def create_manager_from_config(config: WeatherConfig):
        """Create weather manager based on configuration."""
        # Phase 2 directive: factories are banned as composition outside bootstrap.
        # Keep this symbol for import compatibility, but fail fast if called.
        raise RuntimeError(
            "WeatherAPIFactory is not allowed to compose WeatherAPIManager in Phase 2; "
            "use src.app.bootstrap.bootstrap_app()"
        )

