from __future__ import annotations

from datetime import datetime

from src.models.astronomy_data import AstronomyEvent, AstronomyEventType
from src.utils.astronomy_icon_allocator import assign_unique_event_icons


def _make_event(event_type: AstronomyEventType, title: str) -> AstronomyEvent:
    return AstronomyEvent(
        event_type=event_type,
        title=title,
        description="x",
        start_time=datetime(2026, 1, 1, 0, 0, 0),
    )


def test_assign_unique_event_icons_is_deterministic_and_unique_across_week():
    # 7 days, 4 events each -> 28 icons.
    days_events = []
    types = [
        AstronomyEventType.ISS_PASS,
        AstronomyEventType.PLANETARY_EVENT,
        AstronomyEventType.SOLAR_EVENT,
        AstronomyEventType.NEAR_EARTH_OBJECT,
    ]
    for d in range(7):
        days_events.append([
            _make_event(types[0], f"iss-{d}"),
            _make_event(types[1], f"planet-{d}"),
            _make_event(types[2], f"solar-{d}"),
            _make_event(types[3], f"neo-{d}"),
        ])

    a1 = assign_unique_event_icons(days_events)
    a2 = assign_unique_event_icons(days_events)

    assert a1 == a2

    flattened = [emoji for day in a1 for emoji in day]
    assert len(flattened) == 28
    assert len(set(flattened)) == 28


def test_allocator_does_not_use_moon_phase_emojis_in_week_view():
    days_events = [[_make_event(AstronomyEventType.MOON_PHASE, f"moon-{d}-{i}") for i in range(4)] for d in range(7)]
    assigned = assign_unique_event_icons(days_events)
    forbidden = {"🌑", "🌒", "🌓", "🌔", "🌕", "🌖", "🌗", "🌘", "🌙", "🌚", "🌛", "🌜", "🌝"}
    flattened = [emoji for day in assigned for emoji in day]
    assert not (set(flattened) & forbidden)

