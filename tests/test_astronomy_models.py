from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, cast

import pytest

from src.models.astronomy_daily_models import AstronomyData
from src.models.astronomy_event_models import (
    AstronomyEvent,
    AstronomyEventPriority,
    AstronomyEventType,
    MoonPhase,
)
from src.models.astronomy_links_db import AstronomyLink, AstronomyLinksDatabase, LinkCategory
from src.models.astronomy_forecast_models import AstronomyForecastData, Location


def test_astronomy_event_validation_and_time_properties(monkeypatch):
    start = datetime(2026, 1, 1, 10, 0)
    end = datetime(2026, 1, 1, 11, 0)
    e = AstronomyEvent(
        event_type=AstronomyEventType.APOD,
        title="Title",
        description="Desc",
        start_time=start,
        end_time=end,
        image_url="https://example.com/x.png",
        related_links=["https://example.com/a", "https://example.com/a#frag"],
    )
    assert e.duration == timedelta(hours=1)
    assert e.has_image is True
    assert e.has_visibility_info is False
    assert e.event_icon

    fixed_now = datetime(2026, 1, 1, 10, 30)

    class _FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            if tz is not None:
                return fixed_now.astimezone(tz)
            return fixed_now

    monkeypatch.setattr("src.models.astronomy_event_models.datetime", _FixedDateTime)
    assert e.is_ongoing is True
    assert e.is_future is False
    assert e.is_past is False

    with pytest.raises(ValueError, match="Event title cannot be empty"):
        AstronomyEvent(
            event_type=AstronomyEventType.APOD,
            title=" ",
            description="Desc",
            start_time=start,
        )
    with pytest.raises(ValueError, match="Event description cannot be empty"):
        AstronomyEvent(
            event_type=AstronomyEventType.APOD,
            title="Title",
            description=" ",
            start_time=start,
        )
    with pytest.raises(ValueError, match="End time cannot be before"):
        AstronomyEvent(
            event_type=AstronomyEventType.APOD,
            title="Title",
            description="Desc",
            start_time=end,
            end_time=start,
        )
    with pytest.raises(ValueError, match="Invalid image URL"):
        AstronomyEvent(
            event_type=AstronomyEventType.APOD,
            title="Title",
            description="Desc",
            start_time=start,
            image_url="not-a-url",
        )
    with pytest.raises(ValueError, match="Metadata must be a dictionary"):
        AstronomyEvent(
            event_type=AstronomyEventType.APOD,
            title="Title",
            description="Desc",
            start_time=start,
            # Runtime validation should reject non-dict metadata.
            metadata=cast(Any, []),
        )


def test_astronomy_data_validation_and_helpers(monkeypatch):
    d = date(2026, 1, 1)
    start = datetime(2026, 1, 1, 10, 0)
    e1 = AstronomyEvent(
        event_type=AstronomyEventType.MOON_PHASE,
        title="Moon",
        description="Desc",
        start_time=start,
        priority=AstronomyEventPriority.HIGH,
    )
    e2 = AstronomyEvent(
        event_type=AstronomyEventType.APOD,
        title="APOD",
        description="Desc",
        start_time=start + timedelta(hours=1),
        priority=AstronomyEventPriority.LOW,
    )

    ad = AstronomyData(
        date=d,
        events=[e1, e2],
        primary_event=e1,
        moon_phase=MoonPhase.FULL_MOON,
        moon_illumination=0.5,
        sunrise_time=datetime(2026, 1, 1, 7, 0),
        sunset_time=datetime(2026, 1, 1, 17, 0),
    )
    assert ad.has_events is True
    assert ad.event_count == 2
    assert ad.has_high_priority_events is True
    assert ad.moon_phase_icon == "🌕"
    assert ad.daylight_duration == timedelta(hours=10)
    assert ad.get_events_by_type(AstronomyEventType.APOD) == [e2]
    assert ad.get_events_by_priority(AstronomyEventPriority.HIGH) == [e1]
    assert ad.get_sorted_events() == [e1, e2]

    fixed_now = datetime(2026, 1, 1, 10, 30)

    class _FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            if tz is not None:
                return fixed_now.astimezone(tz)
            return fixed_now

    monkeypatch.setattr("src.models.astronomy_event_models.datetime", _FixedDateTime)
    assert ad.get_ongoing_events() == [e1]
    assert ad.get_future_events() == [e2]

    with pytest.raises(ValueError, match="Moon illumination must be between"):
        AstronomyData(date=d, moon_illumination=2.0)

    with pytest.raises(ValueError, match="Sunrise must be before sunset"):
        AstronomyData(
            date=d,
            sunrise_time=datetime(2026, 1, 1, 18, 0),
            sunset_time=datetime(2026, 1, 1, 17, 0),
        )

    with pytest.raises(ValueError, match="Primary event must be in"):
        AstronomyData(date=d, events=[e1], primary_event=e2)

    with pytest.raises(ValueError, match="is not for date"):
        AstronomyData(date=d, events=[AstronomyEvent(
            event_type=AstronomyEventType.APOD,
            title="X",
            description="Desc",
            start_time=datetime(2026, 1, 2, 10, 0),
        )])


def test_astronomy_links_db_dedupes_by_canonical_url_and_queries():
    l1 = AstronomyLink(
        name="NASA",
        url="https://www.nasa.gov/path/#frag",
        category=LinkCategory.SPACE_AGENCY,
        emoji="🚀",
        description="desc",
        priority=2,
        tags=["space"],
    )
    # Same canonical URL but higher priority should replace.
    l2 = AstronomyLink(
        name="NASA Duplicate",
        url="https://nasa.gov/path",
        category=LinkCategory.SPACE_AGENCY,
        emoji="🚀",
        description="desc",
        priority=1,
        tags=["space"],
    )
    db = AstronomyLinksDatabase.from_links([l1, l2])
    all_links = db.get_all_links()
    assert len(all_links) == 1
    assert all_links[0].priority == 1

    assert db.get_links_by_category(LinkCategory.SPACE_AGENCY)
    assert db.get_high_priority_links()
    assert db.search_links("space")
    assert db.get_category_emoji(LinkCategory.SPACE_AGENCY) == "🚀"

    suggested = db.get_suggested_links_for_event_type("apod")
    assert suggested == sorted(suggested, key=lambda l: (l.priority, l.name.lower()))


def test_astronomy_link_validation():
    with pytest.raises(ValueError, match="Link name cannot be empty"):
        AstronomyLink(
            name=" ",
            url="https://example.com",
            category=LinkCategory.EDUCATIONAL,
            emoji="📚",
            description="desc",
        )


def test_astronomy_forecast_models(tmp_path, monkeypatch):
    loc = Location(name="X", latitude=0.0, longitude=0.0, elevation=10.0)
    d1 = date(2026, 1, 1)
    d2 = date(2026, 1, 2)

    start = datetime(2026, 1, 1, 10, 0)
    e1 = AstronomyEvent(
        event_type=AstronomyEventType.APOD,
        title="A",
        description="Desc",
        start_time=start,
        priority=AstronomyEventPriority.HIGH,
    )
    e2 = AstronomyEvent(
        event_type=AstronomyEventType.ISS_PASS,
        title="B",
        description="Desc",
        start_time=start + timedelta(days=1),
        priority=AstronomyEventPriority.MEDIUM,
    )

    day1 = AstronomyData(date=d1, events=[e1], primary_event=e1)
    day2 = AstronomyData(date=d2, events=[e2], primary_event=e2)

    fixed_now = datetime(2026, 1, 1, 9, 0)

    class _FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            if tz is not None:
                return fixed_now.astimezone(tz)
            return fixed_now

    monkeypatch.setattr("src.models.astronomy_forecast_models.datetime", _FixedDateTime)

    forecast = AstronomyForecastData(location=loc, daily_astronomy=[day1, day2], last_updated=fixed_now)
    assert forecast.is_stale is False
    assert forecast.total_events == 2
    assert forecast.has_high_priority_events is True
    assert forecast.forecast_start_date == d1
    assert forecast.forecast_end_date == d2
    assert forecast.get_astronomy_for_date(d1) == day1
    assert forecast.get_today_astronomy() is None
    assert forecast.get_tomorrow_astronomy() is None
    assert forecast.get_events_by_type(AstronomyEventType.APOD) == [e1]
    assert e1 in forecast.get_high_priority_events()

    # Upcoming events uses AstronomyEvent.is_future; patch that module's datetime too.
    monkeypatch.setattr("src.models.astronomy_event_models.datetime", _FixedDateTime)
    upcoming = forecast.get_upcoming_events()
    assert upcoming == [e1, e2]
    assert forecast.get_upcoming_events(limit=1) == [e1]

    with pytest.raises(ValueError, match="at least one day"):
        AstronomyForecastData(location=loc, daily_astronomy=[])
    with pytest.raises(ValueError, match="more than"):
        AstronomyForecastData(location=loc, daily_astronomy=[day1, day2], forecast_days=1)
    with pytest.raises(ValueError, match="chronological"):
        AstronomyForecastData(location=loc, daily_astronomy=[day2, day1])
    with pytest.raises(ValueError, match="duplicate"):
        AstronomyForecastData(location=loc, daily_astronomy=[day1, day1])

    with pytest.raises(ValueError, match="Invalid elevation"):
        Location(name="X", latitude=0.0, longitude=0.0, elevation=-999.0)
    with pytest.raises(ValueError, match="Link URL cannot be empty"):
        AstronomyLink(
            name="X",
            url=" ",
            category=LinkCategory.EDUCATIONAL,
            emoji="📚",
            description="desc",
        )
    with pytest.raises(ValueError, match="Invalid URL"):
        AstronomyLink(
            name="X",
            url="not-a-url",
            category=LinkCategory.EDUCATIONAL,
            emoji="📚",
            description="desc",
        )
    with pytest.raises(ValueError, match="Link description cannot be empty"):
        AstronomyLink(
            name="X",
            url="https://example.com",
            category=LinkCategory.EDUCATIONAL,
            emoji="📚",
            description=" ",
        )
    with pytest.raises(ValueError, match="Priority must be between"):
        AstronomyLink(
            name="X",
            url="https://example.com",
            category=LinkCategory.EDUCATIONAL,
            emoji="📚",
            description="desc",
            priority=99,
        )

