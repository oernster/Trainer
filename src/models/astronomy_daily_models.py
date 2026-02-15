"""Daily astronomy data container."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import List, Optional

from .astronomy_event_models import AstronomyEvent, AstronomyEventPriority, AstronomyEventType, MoonPhase


@dataclass(frozen=True)
class AstronomyData:
    """Immutable daily astronomy data container."""

    date: date
    events: List[AstronomyEvent] = field(default_factory=list)
    primary_event: Optional[AstronomyEvent] = None
    moon_phase: Optional[MoonPhase] = None
    moon_illumination: Optional[float] = None
    sunrise_time: Optional[datetime] = None
    sunset_time: Optional[datetime] = None

    def __post_init__(self) -> None:
        if self.moon_illumination is not None and not (0.0 <= self.moon_illumination <= 1.0):
            raise ValueError("Moon illumination must be between 0.0 and 1.0")

        if self.sunrise_time and self.sunset_time:
            if self.sunrise_time.date() != self.date:
                raise ValueError("Sunrise time must be on the same date")
            if self.sunset_time.date() != self.date:
                raise ValueError("Sunset time must be on the same date")
            if self.sunrise_time >= self.sunset_time:
                raise ValueError("Sunrise must be before sunset")

        if self.primary_event and self.primary_event not in self.events:
            raise ValueError("Primary event must be in the events list")

        for event in self.events:
            if event.start_time.date() != self.date:
                raise ValueError(f"Event {event.title} is not for date {self.date}")

    @property
    def has_events(self) -> bool:
        return bool(self.events)

    @property
    def event_count(self) -> int:
        return len(self.events)

    @property
    def high_priority_events(self) -> List[AstronomyEvent]:
        return [
            e
            for e in self.events
            if e.priority in {AstronomyEventPriority.HIGH, AstronomyEventPriority.CRITICAL}
        ]

    @property
    def has_high_priority_events(self) -> bool:
        return bool(self.high_priority_events)

    @property
    def moon_phase_icon(self) -> str:
        if not self.moon_phase:
            return "🌑"
        icons = {
            MoonPhase.NEW_MOON: "🌑",
            MoonPhase.WAXING_CRESCENT: "🌒",
            MoonPhase.FIRST_QUARTER: "🌓",
            MoonPhase.WAXING_GIBBOUS: "🌔",
            MoonPhase.FULL_MOON: "🌕",
            MoonPhase.WANING_GIBBOUS: "🌖",
            MoonPhase.LAST_QUARTER: "🌗",
            MoonPhase.WANING_CRESCENT: "🌘",
        }
        return icons.get(self.moon_phase, "🌑")

    @property
    def daylight_duration(self) -> Optional[timedelta]:
        return (self.sunset_time - self.sunrise_time) if (self.sunrise_time and self.sunset_time) else None

    def get_events_by_type(self, event_type: AstronomyEventType) -> List[AstronomyEvent]:
        return [e for e in self.events if e.event_type == event_type]

    def get_events_by_priority(self, priority: AstronomyEventPriority) -> List[AstronomyEvent]:
        return [e for e in self.events if e.priority == priority]

    def get_ongoing_events(self) -> List[AstronomyEvent]:
        return [e for e in self.events if e.is_ongoing]

    def get_future_events(self) -> List[AstronomyEvent]:
        return [e for e in self.events if e.is_future]

    def get_sorted_events(self, by_priority: bool = False) -> List[AstronomyEvent]:
        if by_priority:
            return sorted(
                self.events,
                key=lambda e: (e.priority.value, e.start_time),
                reverse=True,
            )
        return sorted(self.events, key=lambda e: e.start_time)


__all__ = ["AstronomyData"]

