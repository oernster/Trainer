"""Validation helpers for astronomy models."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from .astronomy_daily_models import AstronomyData
from .astronomy_event_models import AstronomyEvent, AstronomyEventPriority, AstronomyEventType, MoonPhase
from .astronomy_forecast_models import AstronomyForecastData, Location


class AstronomyDataValidator:
    """Validator for astronomy data integrity."""

    @staticmethod
    def validate_event_type(event_type: AstronomyEventType) -> bool:
        return isinstance(event_type, AstronomyEventType)

    @staticmethod
    def validate_timestamp(timestamp: datetime) -> bool:
        now = datetime.now()
        return (now - timedelta(days=1)) <= timestamp <= (now + timedelta(days=30))

    @staticmethod
    def validate_priority(priority: AstronomyEventPriority) -> bool:
        return isinstance(priority, AstronomyEventPriority)

    @staticmethod
    def validate_moon_phase(moon_phase: Optional[MoonPhase]) -> bool:
        return moon_phase is None or isinstance(moon_phase, MoonPhase)

    @staticmethod
    def validate_location(location: Location) -> bool:
        try:
            return (
                -90 <= location.latitude <= 90
                and -180 <= location.longitude <= 180
                and location.name.strip() != ""
            )
        except (AttributeError, TypeError):
            return False

    @classmethod
    def validate_astronomy_event(cls, event: AstronomyEvent) -> bool:
        return (
            cls.validate_event_type(event.event_type)
            and cls.validate_timestamp(event.start_time)
            and cls.validate_priority(event.priority)
            and event.title.strip() != ""
            and event.description.strip() != ""
            and (event.end_time is None or event.end_time >= event.start_time)
        )

    @classmethod
    def validate_astronomy_data(cls, astronomy_data: AstronomyData) -> bool:
        for event in astronomy_data.events:
            if not cls.validate_astronomy_event(event):
                return False
        if not cls.validate_moon_phase(astronomy_data.moon_phase):
            return False
        if astronomy_data.moon_illumination is not None and not (0.0 <= astronomy_data.moon_illumination <= 1.0):
            return False
        return True

    @classmethod
    def validate_astronomy_forecast(cls, forecast: AstronomyForecastData) -> bool:
        if not cls.validate_location(forecast.location):
            return False
        for daily_data in forecast.daily_astronomy:
            if not cls.validate_astronomy_data(daily_data):
                return False
        if len(forecast.daily_astronomy) > forecast.forecast_days:
            return False
        return True


__all__ = ["AstronomyDataValidator"]

