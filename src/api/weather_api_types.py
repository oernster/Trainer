"""Weather API abstractions and small value types.

Split out of [`weather_api_manager`](src/api/weather_api_manager.py:1) to keep
modules under the <= 400 non-blank LOC gate.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Dict

from ..models.weather_data import Location, WeatherForecastData


class WeatherAPIException(Exception):
    """Base exception for weather API-related errors."""


class WeatherNetworkException(WeatherAPIException):
    """Exception for network-related errors."""


class WeatherDataException(WeatherAPIException):
    """Exception for weather data processing errors."""


class WeatherRateLimitException(WeatherAPIException):
    """Exception for rate limit exceeded errors."""


@dataclass
class WeatherAPIResponse:
    """Container for raw weather API response data."""

    status_code: int
    data: Dict
    timestamp: datetime
    source: str


class WeatherDataSource(ABC):
    """Abstract base class for weather data sources."""

    @abstractmethod
    async def fetch_weather_data(self, location: Location) -> WeatherForecastData:
        """Fetch weather data from source."""

    @abstractmethod
    def get_source_name(self) -> str:
        """Get the name of the weather data source."""

    @abstractmethod
    def get_source_url(self) -> str:
        """Get the base URL of the weather data source."""

    @abstractmethod
    async def shutdown(self) -> None:
        """Shutdown the weather data source and cleanup resources."""

    @abstractmethod
    def shutdown_sync(self) -> None:
        """Shutdown the weather data source synchronously."""


class HTTPClient(ABC):
    """Abstract HTTP client interface for dependency injection."""

    @abstractmethod
    async def get(self, url: str, params: Dict) -> WeatherAPIResponse:
        """Make HTTP GET request."""

    @abstractmethod
    async def close(self) -> None:
        """Close HTTP client."""

    @abstractmethod
    def close_sync(self) -> None:
        """Close HTTP client synchronously."""

