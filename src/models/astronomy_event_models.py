"""Astronomy event types and event entity.

Split out of [`src/models/astronomy_data.py`](src/models/astronomy_data.py:1)
to satisfy the <=400 LOC quality gate.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol
from urllib.parse import urlparse

from ..utils.url_utils import dedupe_urls

logger = logging.getLogger(__name__)


class AstronomyEventType(Enum):
    """Enumeration of astronomy event types."""

    APOD = "apod"
    ISS_PASS = "iss_pass"
    NEAR_EARTH_OBJECT = "near_earth_object"
    MOON_PHASE = "moon_phase"
    PLANETARY_EVENT = "planetary_event"
    METEOR_SHOWER = "meteor_shower"
    SOLAR_EVENT = "solar_event"
    SATELLITE_IMAGE = "satellite_image"
    UNKNOWN = "unknown"


class MoonPhase(Enum):
    """Moon phase enumeration."""

    NEW_MOON = "new_moon"
    WAXING_CRESCENT = "waxing_crescent"
    FIRST_QUARTER = "first_quarter"
    WAXING_GIBBOUS = "waxing_gibbous"
    FULL_MOON = "full_moon"
    WANING_GIBBOUS = "waning_gibbous"
    LAST_QUARTER = "last_quarter"
    WANING_CRESCENT = "waning_crescent"


class AstronomyEventPriority(Enum):
    """Priority levels for astronomy events."""

    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class AstronomyDataReader(Protocol):
    """Protocol for reading astronomy data."""

    def get_event_type(self) -> AstronomyEventType: ...

    def get_title(self) -> str: ...

    def get_start_time(self) -> datetime: ...

    def has_visibility_info(self) -> bool: ...


class AstronomyIconProvider(Protocol):
    """Protocol for providing astronomy icons."""

    def get_astronomy_icon(self, event_type: AstronomyEventType) -> str: ...


@dataclass(frozen=True)
class AstronomyEvent:
    """Immutable astronomy event data."""

    event_type: AstronomyEventType
    title: str
    description: str
    start_time: datetime
    end_time: Optional[datetime] = None
    visibility_info: Optional[str] = None
    image_url: Optional[str] = None
    priority: AstronomyEventPriority = AstronomyEventPriority.MEDIUM
    metadata: Dict[str, Any] = field(default_factory=dict)
    related_links: List[str] = field(default_factory=list)
    suggested_categories: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.title.strip():
            raise ValueError("Event title cannot be empty")
        if not self.description.strip():
            raise ValueError("Event description cannot be empty")
        if self.end_time and self.end_time < self.start_time:
            raise ValueError("End time cannot be before start time")
        if self.image_url and not self._is_valid_url(self.image_url):
            raise ValueError(f"Invalid image URL: {self.image_url}")
        if not isinstance(self.metadata, dict):
            raise ValueError("Metadata must be a dictionary")

    @staticmethod
    def _is_valid_url(url: str) -> bool:
        try:
            result = urlparse(url)
            return bool(result.scheme and result.netloc)
        except Exception:
            return False

    @property
    def duration(self) -> Optional[timedelta]:
        return (self.end_time - self.start_time) if self.end_time else None

    @property
    def is_ongoing(self) -> bool:
        now = datetime.now()
        if self.end_time:
            return self.start_time <= now <= self.end_time
        return self.start_time <= now <= (self.start_time + timedelta(hours=24))

    @property
    def is_future(self) -> bool:
        return self.start_time > datetime.now()

    @property
    def is_past(self) -> bool:
        now = datetime.now()
        if self.end_time:
            return self.end_time < now
        return self.start_time < now

    @property
    def has_visibility_info(self) -> bool:
        return bool(self.visibility_info and self.visibility_info.strip())

    @property
    def has_image(self) -> bool:
        return bool(self.image_url and self.image_url.strip())

    @property
    def event_icon(self) -> str:
        icons = {
            AstronomyEventType.APOD: "🌌",
            AstronomyEventType.ISS_PASS: "🚀",
            AstronomyEventType.NEAR_EARTH_OBJECT: "💫",
            AstronomyEventType.MOON_PHASE: "🌕",
            AstronomyEventType.PLANETARY_EVENT: "🌟",
            AstronomyEventType.METEOR_SHOWER: "✨",
            AstronomyEventType.SOLAR_EVENT: "🌞",
            AstronomyEventType.SATELLITE_IMAGE: "🛰️",
            AstronomyEventType.UNKNOWN: "❓",
        }
        return icons.get(self.event_type, "❓")

    def get_formatted_time(self, format_str: str = "%H:%M") -> str:
        return self.start_time.strftime(format_str)

    def get_formatted_duration(self) -> str:
        if not self.duration:
            return "Unknown duration"
        total_seconds = int(self.duration.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        return f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"

    def get_link_urls(self) -> List[str]:
        """Get de-duplicated link URLs relevant for this event."""
        urls: list[str] = []

        # Curated suggestions (avoid import cycles by importing lazily).
        try:
            from .astronomy_links import astronomy_links_db

            suggested_links = astronomy_links_db.get_suggested_links_for_event_type(
                self.event_type.value
            )
            urls.extend([link.url for link in suggested_links])
        except Exception:
            pass

        urls.extend(self.related_links)
        return dedupe_urls(urls)

    def get_primary_link(self) -> Optional[str]:
        urls = self.get_link_urls()
        return urls[0] if urls else None

    def has_multiple_links(self) -> bool:
        return len(self.get_link_urls()) > 1


__all__ = [
    "AstronomyDataReader",
    "AstronomyEvent",
    "AstronomyEventPriority",
    "AstronomyEventType",
    "AstronomyIconProvider",
    "MoonPhase",
]

