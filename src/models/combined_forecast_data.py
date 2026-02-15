"""
Combined forecast data models for the Trainer application.
Author: Oliver Ernster

This module contains immutable data classes that combine weather and astronomy
information, following solid Object-Oriented design principles with proper
encapsulation and single responsibility.
"""

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Optional

from .combined_forecast_enums import CombinedDataStatus, ForecastDataQuality
from .combined_forecast_validator import CombinedForecastValidator
from .weather_data import Location, WeatherData, WeatherForecastData
from .astronomy_data import (
    AstronomyData,
    AstronomyForecastData,
    AstronomyEvent,
    AstronomyEventType,
)
from version import __version__

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DailyForecastData:
    """
    Combined daily weather and astronomy data.

    Follows Single Responsibility Principle - only responsible for
    organizing daily weather and astronomy information together.
    """

    date: date
    weather_data: Optional[WeatherData] = None
    astronomy_data: Optional[AstronomyData] = None
    data_quality: ForecastDataQuality = ForecastDataQuality.POOR
    last_updated: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        """Validate daily forecast data on creation."""
        if not self.weather_data and not self.astronomy_data:
            raise ValueError(
                "Daily forecast must contain either weather or astronomy data"
            )

        # Validate dates match
        if self.weather_data and self.weather_data.timestamp.date() != self.date:
            raise ValueError("Weather data date must match forecast date")

        if self.astronomy_data and self.astronomy_data.date != self.date:
            raise ValueError("Astronomy data date must match forecast date")

    @property
    def has_complete_data(self) -> bool:
        """Check if both weather and astronomy data are available."""
        return self.weather_data is not None and self.astronomy_data is not None

    @property
    def has_weather_data(self) -> bool:
        """Check if weather data is available."""
        return self.weather_data is not None

    @property
    def has_astronomy_data(self) -> bool:
        """Check if astronomy data is available."""
        return self.astronomy_data is not None

    @property
    def primary_astronomy_event(self) -> Optional[AstronomyEvent]:
        """Get the primary astronomy event for this day."""
        if self.astronomy_data:
            return self.astronomy_data.primary_event
        return None

    @property
    def astronomy_event_count(self) -> int:
        """Get the number of astronomy events for this day."""
        if self.astronomy_data:
            return self.astronomy_data.event_count
        return 0

    @property
    def has_high_priority_astronomy(self) -> bool:
        """Check if there are high priority astronomy events."""
        if self.astronomy_data:
            return self.astronomy_data.has_high_priority_events
        return False

    @property
    def weather_description(self) -> str:
        """Get weather description or fallback."""
        if self.weather_data:
            return self.weather_data.description
        return "No weather data"

    @property
    def temperature_display(self) -> str:
        """Get formatted temperature display or fallback."""
        if self.weather_data:
            return self.weather_data.temperature_display
        return "N/A"

    @property
    def is_precipitation_day(self) -> bool:
        """Check if precipitation is expected."""
        if self.weather_data:
            return self.weather_data.is_precipitation()
        return False

    @property
    def moon_phase_icon(self) -> str:
        """Get moon phase icon or fallback."""
        if self.astronomy_data:
            return self.astronomy_data.moon_phase_icon
        return "🌑"

    def get_astronomy_events_by_type(
        self, event_type: AstronomyEventType
    ) -> list[AstronomyEvent]:
        """Get astronomy events of a specific type."""
        if self.astronomy_data:
            return self.astronomy_data.get_events_by_type(event_type)
        return []

    def get_display_summary(self) -> str:
        """Get a summary string for display purposes."""
        parts = []

        if self.weather_data:
            parts.append(f"{self.weather_data.temperature_display}")
            parts.append(f"{self.weather_data.description}")

        if self.astronomy_data and self.astronomy_data.has_events:
            event_count = self.astronomy_data.event_count
            parts.append(
                f"{event_count} astronomy event{'s' if event_count != 1 else ''}"
            )

        return " • ".join(parts) if parts else "No data available"


@dataclass(frozen=True)
class CombinedForecastData:
    """
    Complete combined weather and astronomy forecast data.

    Follows Single Responsibility Principle - only responsible for
    organizing and providing access to combined forecast information.
    """

    location: Location
    daily_forecasts: list[DailyForecastData] = field(default_factory=list)
    weather_forecast: Optional[WeatherForecastData] = None
    astronomy_forecast: Optional[AstronomyForecastData] = None
    last_updated: datetime = field(default_factory=datetime.now)
    data_version: str = field(default=__version__)
    status: CombinedDataStatus = CombinedDataStatus.COMPLETE_FAILURE
    error_messages: list[str] = field(default_factory=list)

    def __post_init__(self):
        """Validate combined forecast data on creation."""
        # For total failure cases we allow an empty daily forecast list.
        # This keeps the type usable as an error container while still
        # enforcing strong invariants for successful/partial data.
        if not self.daily_forecasts:
            if self.status == CombinedDataStatus.COMPLETE_FAILURE:
                return
            raise ValueError(
                "Combined forecast must contain at least one daily forecast"
            )

        # Validate dates are in chronological order
        dates = [forecast.date for forecast in self.daily_forecasts]
        if dates != sorted(dates):
            raise ValueError("Daily forecasts must be in chronological order")

        # Validate no duplicate dates
        if len(dates) != len(set(dates)):
            raise ValueError("Daily forecasts cannot contain duplicate dates")

        # Validate forecast length (typically 7 days)
        if len(self.daily_forecasts) > 14:  # Reasonable upper limit
            raise ValueError("Combined forecast cannot exceed 14 days")

    @classmethod
    def create(
        cls,
        location: Location,
        weather_data: Optional[WeatherForecastData] = None,
        astronomy_data: Optional[AstronomyForecastData] = None,
    ) -> "CombinedForecastData":
        """
        Factory method to create combined forecast from separate data sources.

        Args:
            location: Location for the forecast
            weather_data: Weather forecast data (optional)
            astronomy_data: Astronomy forecast data (optional)

        Returns:
            CombinedForecastData: Combined forecast object
        """
        if not weather_data and not astronomy_data:
            return cls(
                location=location,
                status=CombinedDataStatus.COMPLETE_FAILURE,
                error_messages=["No weather or astronomy data available"],
            )

        # Determine date range
        start_date = date.today()
        end_date = start_date + timedelta(days=6)  # 7-day forecast

        # Extend date range if we have data beyond 7 days
        if weather_data and weather_data.daily_forecast:
            weather_end = max(w.timestamp.date() for w in weather_data.daily_forecast)
            end_date = max(end_date, weather_end)

        if astronomy_data and astronomy_data.daily_astronomy:
            astronomy_end = max(a.date for a in astronomy_data.daily_astronomy)
            end_date = max(end_date, astronomy_end)

        # Create daily forecasts
        daily_forecasts = []
        current_date = start_date

        while current_date <= end_date:
            # Get weather data for this date
            weather_for_date = None
            if weather_data:
                weather_for_date = cls._get_weather_for_date(weather_data, current_date)

            # Get astronomy data for this date
            astronomy_for_date = None
            if astronomy_data:
                astronomy_for_date = astronomy_data.get_astronomy_for_date(current_date)

            # Skip dates with no data
            if not weather_for_date and not astronomy_for_date:
                current_date += timedelta(days=1)
                continue

            # Determine data quality
            data_quality = cls._determine_data_quality(
                weather_for_date, astronomy_for_date
            )

            daily_forecast = DailyForecastData(
                date=current_date,
                weather_data=weather_for_date,
                astronomy_data=astronomy_for_date,
                data_quality=data_quality,
            )

            daily_forecasts.append(daily_forecast)
            current_date += timedelta(days=1)

        # Determine overall status
        status = cls._determine_status(weather_data, astronomy_data, daily_forecasts)

        # Collect error messages
        error_messages = []
        if not weather_data:
            error_messages.append("Weather data unavailable")
        if not astronomy_data:
            error_messages.append("Astronomy data unavailable")

        return cls(
            location=location,
            daily_forecasts=daily_forecasts,
            weather_forecast=weather_data,
            astronomy_forecast=astronomy_data,
            status=status,
            error_messages=error_messages,
        )

    @staticmethod
    def _get_weather_for_date(
        weather_data: WeatherForecastData, target_date: date
    ) -> Optional[WeatherData]:
        """Get weather data for a specific date."""
        # Try daily forecast first
        for weather in weather_data.daily_forecast:
            if weather.timestamp.date() == target_date:
                return weather

        # Fallback to hourly forecast (use noon data if available)
        for weather in weather_data.hourly_forecast:
            if weather.timestamp.date() == target_date and weather.timestamp.hour == 12:
                return weather

        # Last resort: any hourly data for that date
        for weather in weather_data.hourly_forecast:
            if weather.timestamp.date() == target_date:
                return weather

        return None

    @staticmethod
    def _determine_data_quality(
        weather_data: Optional[WeatherData], astronomy_data: Optional[AstronomyData]
    ) -> ForecastDataQuality:
        """Determine the quality of combined data."""
        if weather_data and astronomy_data:
            if astronomy_data.has_events:
                return ForecastDataQuality.EXCELLENT
            return ForecastDataQuality.GOOD
        elif weather_data or astronomy_data:
            return ForecastDataQuality.PARTIAL
        else:
            return ForecastDataQuality.POOR

    @staticmethod
    def _determine_status(
        weather_data: Optional[WeatherForecastData],
        astronomy_data: Optional[AstronomyForecastData],
        daily_forecasts: list[DailyForecastData],
    ) -> CombinedDataStatus:
        """Determine the overall status of combined forecast."""
        has_weather = weather_data is not None
        has_astronomy = astronomy_data is not None

        if has_weather and has_astronomy:
            return CombinedDataStatus.COMPLETE
        elif has_weather and not has_astronomy:
            return CombinedDataStatus.WEATHER_ONLY
        elif not has_weather and has_astronomy:
            return CombinedDataStatus.ASTRONOMY_ONLY
        elif daily_forecasts:
            return CombinedDataStatus.PARTIAL_FAILURE
        else:
            return CombinedDataStatus.COMPLETE_FAILURE

    @property
    def is_stale(self) -> bool:
        """Check if combined forecast data is stale (older than 1 hour)."""
        return (datetime.now() - self.last_updated) > timedelta(hours=1)

    @property
    def forecast_days(self) -> int:
        """Get the number of forecast days."""
        return len(self.daily_forecasts)

    @property
    def has_complete_data(self) -> bool:
        """Check if both weather and astronomy data are available."""
        return self.status == CombinedDataStatus.COMPLETE

    @property
    def has_weather_data(self) -> bool:
        """Check if weather data is available."""
        return self.weather_forecast is not None

    @property
    def has_astronomy_data(self) -> bool:
        """Check if astronomy data is available."""
        return self.astronomy_forecast is not None

    @property
    def total_astronomy_events(self) -> int:
        """Get total number of astronomy events across all days."""
        return sum(forecast.astronomy_event_count for forecast in self.daily_forecasts)

    @property
    def has_high_priority_astronomy(self) -> bool:
        """Check if there are high priority astronomy events in the forecast."""
        return any(
            forecast.has_high_priority_astronomy for forecast in self.daily_forecasts
        )

    @property
    def data_quality_summary(self) -> dict[ForecastDataQuality, int]:
        """Get a summary of data quality across all days."""
        quality_counts = {quality: 0 for quality in ForecastDataQuality}
        for forecast in self.daily_forecasts:
            quality_counts[forecast.data_quality] += 1
        return quality_counts

    def get_forecast_for_date(self, target_date: date) -> Optional[DailyForecastData]:
        """Get combined forecast for a specific date."""
        return next(
            (
                forecast
                for forecast in self.daily_forecasts
                if forecast.date == target_date
            ),
            None,
        )

    def get_today_forecast(self) -> Optional[DailyForecastData]:
        """Get combined forecast for today."""
        return self.get_forecast_for_date(date.today())

    def get_tomorrow_forecast(self) -> Optional[DailyForecastData]:
        """Get combined forecast for tomorrow."""
        tomorrow = date.today() + timedelta(days=1)
        return self.get_forecast_for_date(tomorrow)

    def get_forecasts_with_astronomy(self) -> list[DailyForecastData]:
        """Get all forecasts that have astronomy data."""
        return [
            forecast for forecast in self.daily_forecasts if forecast.has_astronomy_data
        ]

    def get_forecasts_with_weather(self) -> list[DailyForecastData]:
        """Get all forecasts that have weather data."""
        return [
            forecast for forecast in self.daily_forecasts if forecast.has_weather_data
        ]

    def get_high_priority_astronomy_days(self) -> list[DailyForecastData]:
        """Get forecasts with high priority astronomy events."""
        return [
            forecast
            for forecast in self.daily_forecasts
            if forecast.has_high_priority_astronomy
        ]

    def get_precipitation_days(self) -> list[DailyForecastData]:
        """Get forecasts with expected precipitation."""
        return [
            forecast
            for forecast in self.daily_forecasts
            if forecast.is_precipitation_day
        ]

    def get_status_summary(self) -> str:
        """Get a human-readable status summary."""
        status_messages = {
            CombinedDataStatus.COMPLETE: "Complete weather and astronomy data available",
            CombinedDataStatus.WEATHER_ONLY: "Weather data available, astronomy data unavailable",
            CombinedDataStatus.ASTRONOMY_ONLY: "Astronomy data available, weather data unavailable",
            CombinedDataStatus.PARTIAL_FAILURE: "Partial data available with some failures",
            CombinedDataStatus.COMPLETE_FAILURE: "No forecast data available",
        }
        return status_messages.get(self.status, "Unknown status")

    def get_error_summary(self) -> str:
        """Get a summary of all errors."""
        if not self.error_messages:
            return "No errors"
        return "; ".join(self.error_messages)



# Factory functions for creating combined forecasts
def create_weather_only_forecast(
    location: Location, weather_data: WeatherForecastData
) -> CombinedForecastData:
    """Create a combined forecast with only weather data."""
    return CombinedForecastData.create(location, weather_data, None)


def create_astronomy_only_forecast(
    location: Location, astronomy_data: AstronomyForecastData
) -> CombinedForecastData:
    """Create a combined forecast with only astronomy data."""
    return CombinedForecastData.create(location, None, astronomy_data)


def create_complete_forecast(
    location: Location,
    weather_data: WeatherForecastData,
    astronomy_data: AstronomyForecastData,
) -> CombinedForecastData:
    """Create a complete combined forecast with both weather and astronomy data."""
    return CombinedForecastData.create(location, weather_data, astronomy_data)
