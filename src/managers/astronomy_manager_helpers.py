"""Helper functions for [`python.AstronomyManager`](src/managers/astronomy_manager.py:34).

Extracted to keep each module below the repository's <=400 non-blank LOC gate.

No behavioural changes are intended.
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, time as dt_time, timedelta, timezone, tzinfo
from typing import Any

from zoneinfo import ZoneInfo

from src.managers.astronomy_config import AstronomyConfig
from src.models.astronomy_data import AstronomyEvent, AstronomyEventType, MoonPhase

logger = logging.getLogger(__name__)


def generate_static_astronomy_events(*, now: datetime) -> list[AstronomyEvent]:
    """Generate static astronomy events for demonstration."""

    events: list[AstronomyEvent] = []

    # Generate events for the next 7 days
    for day_offset in range(7):
        event_date = now + timedelta(days=day_offset)

        # Generate 2-4 events per day with variety
        daily_events = [
            AstronomyEvent(
                event_type=AstronomyEventType.PLANETARY_EVENT,
                title="Jupiter Visible",
                description=(
                    "Jupiter is visible in the evening sky, reaching its highest point around midnight."
                ),
                start_time=event_date.replace(hour=20, minute=30, second=0, microsecond=0),
                visibility_info="Eastern Sky, magnitude -2.1",
                related_links=["https://in-the-sky.org/"],
                suggested_categories=["Observatory", "Tonight's Sky"],
            ),
            AstronomyEvent(
                event_type=AstronomyEventType.MOON_PHASE,
                title="Moon Phase",
                description=(
                    "The Moon is in "
                    + (
                        "Waxing Crescent"
                        if day_offset < 3
                        else "First Quarter"
                        if day_offset < 5
                        else "Waxing Gibbous"
                    )
                    + " phase."
                ),
                start_time=event_date.replace(hour=22, minute=0, second=0, microsecond=0),
                visibility_info="Night Sky, magnitude -12.7",
                related_links=["https://www.timeanddate.com/moon/phases/"],
                suggested_categories=["Moon Info", "Tonight's Sky"],
            ),
            AstronomyEvent(
                event_type=AstronomyEventType.ISS_PASS,
                title="ISS Pass",
                description="International Space Station visible pass overhead.",
                start_time=event_date.replace(hour=6, minute=15, second=0, microsecond=0),
                visibility_info="Southwest to Northeast, magnitude -3.5",
                related_links=["https://spotthestation.nasa.gov/"],
                suggested_categories=["Space Agencies", "Live Data"],
            ),
            AstronomyEvent(
                event_type=AstronomyEventType.NEAR_EARTH_OBJECT,
                title="Orion Nebula",
                description="The Orion Nebula (M42) is well-positioned for observation.",
                start_time=event_date.replace(hour=23, minute=45, second=0, microsecond=0),
                visibility_info="Constellation Orion, magnitude 4.0",
                related_links=["https://www.eso.org/public/"],
                suggested_categories=["Observatory", "Educational"],
            ),
        ]

        # Add some variety - not all events every day
        if day_offset % 2 == 0:
            events.extend(daily_events[:3])  # 3 events on even days
        else:
            events.extend(daily_events[:2])  # 2 events on odd days

    return events


def get_config_timezone(*, config: AstronomyConfig) -> tzinfo:
    """Get timezone for astronomy calculations.

    Falls back to UTC if the configured timezone is missing/invalid.
    """

    tz_name = getattr(config, "timezone", None) or "UTC"
    try:
        return ZoneInfo(tz_name)
    except Exception:
        # Windows Python environments may not ship with IANA tzdata.
        # Fall back to python-dateutil if available.
        try:
            from dateutil import tz  # type: ignore

            tzinfo_obj = tz.gettz(tz_name)
            if tzinfo_obj is not None:
                return tzinfo_obj
        except Exception:
            pass

        # Fall back to the system local timezone if possible, otherwise UTC.
        logger.warning(
            "Invalid/unavailable timezone '%s'; falling back to system local timezone",
            tz_name,
        )
        return datetime.now().astimezone().tzinfo or timezone.utc


def calculate_moon_phase_for_moment(*, moon_phase_service: Any, target_dt: datetime) -> MoonPhase:
    """Calculate moon phase for a specific moment (timezone-aware datetime)."""

    try:
        moon_data = moon_phase_service.get_moon_phase_sync(target_dt)
        return moon_data.phase
    except Exception as exc:
        logger.warning("Failed to get moon phase from hybrid service: %s", exc)
        return MoonPhase.NEW_MOON


def calculate_moon_illumination_for_moment(*, moon_phase_service: Any, target_dt: datetime) -> float:
    """Calculate moon illumination for a specific moment (timezone-aware datetime)."""

    try:
        moon_data = moon_phase_service.get_moon_phase_sync(target_dt)
        return moon_data.illumination
    except Exception as exc:
        logger.warning("Failed to get moon illumination from hybrid service: %s", exc)

        illumination_map = {
            MoonPhase.NEW_MOON: 0.0,
            MoonPhase.WAXING_CRESCENT: 0.25,
            MoonPhase.FIRST_QUARTER: 0.5,
            MoonPhase.WAXING_GIBBOUS: 0.75,
            MoonPhase.FULL_MOON: 1.0,
            MoonPhase.WANING_GIBBOUS: 0.75,
            MoonPhase.LAST_QUARTER: 0.5,
            MoonPhase.WANING_CRESCENT: 0.25,
        }

        # Derive phase based on the same moment, if possible
        phase = calculate_moon_phase_for_moment(moon_phase_service=moon_phase_service, target_dt=target_dt)
        return illumination_map.get(phase, 0.5)


def anchor_dt_for_day(*, event_date, tz: tzinfo) -> datetime:
    """Pick the stable "tonight" anchor moment for a calendar date."""

    return datetime.combine(event_date, dt_time(22, 0)).replace(tzinfo=tz)

