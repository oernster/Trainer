"""Multi-day astronomy forecast models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import List, Optional

from version import __version__

from .astronomy_daily_models import AstronomyData
from .astronomy_event_models import AstronomyEvent, AstronomyEventType


@dataclass(frozen=True)
class Location:
    """Immutable location data for astronomy calculations."""

    name: str
    latitude: float
    longitude: float
    timezone: Optional[str] = None
    elevation: Optional[float] = None

    def __post_init__(self) -> None:
        if not (-90 <= self.latitude <= 90):
            raise ValueError(f"Invalid latitude: {self.latitude}")
        if not (-180 <= self.longitude <= 180):
            raise ValueError(f"Invalid longitude: {self.longitude}")
        if not self.name.strip():
            raise ValueError("Location name cannot be empty")
        if self.elevation is not None and self.elevation < -500:
            raise ValueError(f"Invalid elevation: {self.elevation}")


@dataclass(frozen=True)
class AstronomyForecastData:
    """Complete astronomy forecast data container."""

    location: Location
    daily_astronomy: List[AstronomyData] = field(default_factory=list)
    last_updated: datetime = field(default_factory=datetime.now)
    data_source: str = "Static Generator"
    data_version: str = field(default=__version__)
    forecast_days: int = 7

    def __post_init__(self) -> None:
        if not self.daily_astronomy:
            raise ValueError("Forecast must contain at least one day of astronomy data")
        if len(self.daily_astronomy) > self.forecast_days:
            raise ValueError(f"Forecast cannot contain more than {self.forecast_days} days")

        dates = [data.date for data in self.daily_astronomy]
        if dates != sorted(dates):
            raise ValueError("Daily astronomy data must be in chronological order")
        if len(dates) != len(set(dates)):
            raise ValueError("Daily astronomy data cannot contain duplicate dates")

    @property
    def is_stale(self) -> bool:
        return (datetime.now() - self.last_updated) > timedelta(hours=6)

    @property
    def total_events(self) -> int:
        return sum(data.event_count for data in self.daily_astronomy)

    @property
    def has_high_priority_events(self) -> bool:
        return any(data.has_high_priority_events for data in self.daily_astronomy)

    @property
    def forecast_start_date(self) -> Optional[date]:
        return self.daily_astronomy[0].date if self.daily_astronomy else None

    @property
    def forecast_end_date(self) -> Optional[date]:
        return self.daily_astronomy[-1].date if self.daily_astronomy else None

    def get_astronomy_for_date(self, target_date: date) -> Optional[AstronomyData]:
        return next((data for data in self.daily_astronomy if data.date == target_date), None)

    def get_today_astronomy(self) -> Optional[AstronomyData]:
        return self.get_astronomy_for_date(date.today())

    def get_tomorrow_astronomy(self) -> Optional[AstronomyData]:
        return self.get_astronomy_for_date(date.today() + timedelta(days=1))

    def get_events_by_type(self, event_type: AstronomyEventType) -> List[AstronomyEvent]:
        events: list[AstronomyEvent] = []
        for daily in self.daily_astronomy:
            events.extend(daily.get_events_by_type(event_type))
        return events

    def get_high_priority_events(self) -> List[AstronomyEvent]:
        events: list[AstronomyEvent] = []
        for daily in self.daily_astronomy:
            events.extend(daily.high_priority_events)
        return events

    def get_upcoming_events(self, limit: Optional[int] = None) -> List[AstronomyEvent]:
        events: list[AstronomyEvent] = []
        for daily in self.daily_astronomy:
            events.extend(daily.get_future_events())
        events.sort(key=lambda e: e.start_time)
        return events[:limit] if limit else events


__all__ = ["AstronomyForecastData", "Location"]

