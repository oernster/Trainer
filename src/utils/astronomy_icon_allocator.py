"""Astronomy icon allocation.

The week-view shows up to 4 event icons per day (7 days => up to 28 icons).

Requirements:
- Deterministic assignment: for the same ordered event list, the same icons are
  assigned every time.
- Uniqueness across the entire 7-day grid (no repeats) while keeping the moon
  phase *day-level* icon unchanged (handled elsewhere).
- Space-oriented emoji.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Iterable, Sequence

from ..models.astronomy_data import AstronomyEvent, AstronomyEventType


# Emojis that must not be used in the 7-day event icon grid because the
# moon-phase glyphs are reserved for the day-level moon display below.
WEEKVIEW_ICON_EXCLUDE: set[str] = {
    "🌑",
    "🌒",
    "🌓",
    "🌔",
    "🌕",
    "🌖",
    "🌗",
    "🌘",
    "🌙",
    "🌚",
    "🌛",
    "🌜",
    "🌝",
}


# Per-event-type emoji variants (space oriented). Keep these distinct and avoid
# common duplicates across types.
_TYPE_VARIANTS: dict[AstronomyEventType, list[str]] = {
    AstronomyEventType.APOD: ["🖼️", "🌌", "✨", "🪐"],
    AstronomyEventType.ISS_PASS: ["🛰️", "👨‍🚀", "🚀", "🛸"],
    AstronomyEventType.NEAR_EARTH_OBJECT: ["☄️", "🪨", "🌠", "💫"],
    # Do NOT use moon emojis in the grid; those are reserved for the day moon display.
    AstronomyEventType.MOON_PHASE: ["🗓️", "📆", "⏳", "🧮"],
    AstronomyEventType.PLANETARY_EVENT: ["🪐", "🔭", "🌟", "🧭"],
    AstronomyEventType.METEOR_SHOWER: ["🌠", "✨", "☄️", "💥"],
    AstronomyEventType.SOLAR_EVENT: ["☀️", "🌞", "🌤️", "🔥"],
    AstronomyEventType.SATELLITE_IMAGE: ["📡", "🛰️", "🗺️", "📷"],
    AstronomyEventType.UNKNOWN: ["❓", "🔭", "🌌", "🧪"],
}

# Global fallback pool used if a type runs out of variants or a collision occurs.
# Must have enough unique values to cover the worst-case grid (28).
_FALLBACK_POOL: list[str] = [
    "🪐",
    "🛰️",
    "🚀",
    "🛸",
    "👨‍🚀",
    "🔭",
    "🌌",
    "🌠",
    "☄️",
    "💫",
    "✨",
    "🔥",
    "☀️",
    "🧭",
    "📡",
    "📷",
    "🗺️",
    "🧪",
    "⚛️",
    "🧬",
    "🧲",
    "📈",
    "🧮",
    "🧰",
    "🧯",
    "🗃️",
    "🛰",
    "🌍",
    "🌎",
    "🌏",
    "🪨",
    "💥",
]


def assign_unique_event_icons(
    days_events: Sequence[Sequence[AstronomyEvent]],
    *,
    per_day_limit: int = 4,
) -> list[list[str]]:
    """Assign icon overrides for the week-view.

    Args:
        days_events: list of days, each a sequence of events (already sorted in
            the order they will be displayed)
        per_day_limit: max number of icons per day (default: 4)

    Returns:
        A parallel list-of-lists of emoji strings, where each inner list has
        length <= per_day_limit and aligns with the first N events of that day.
    """

    used: set[str] = set()
    type_counters: dict[AstronomyEventType, int] = defaultdict(int)
    fallback_idx = 0

    result: list[list[str]] = []

    def _allowed(emoji: str) -> bool:
        return emoji not in WEEKVIEW_ICON_EXCLUDE

    def _next_unique_from_pool(pool: Iterable[str]) -> str | None:
        for emoji in pool:
            if not _allowed(emoji):
                continue
            if emoji not in used:
                used.add(emoji)
                return emoji
        return None

    for day_events in days_events:
        day_icons: list[str] = []
        for event in list(day_events)[:per_day_limit]:
            variants = _TYPE_VARIANTS.get(event.event_type, _TYPE_VARIANTS[AstronomyEventType.UNKNOWN])
            idx = type_counters[event.event_type]
            type_counters[event.event_type] += 1

            # Try deterministic per-type variant first
            chosen = None
            if idx < len(variants):
                candidate = variants[idx]
                if _allowed(candidate) and candidate not in used:
                    used.add(candidate)
                    chosen = candidate

            # If collision or out of variants, walk remaining variants
            if chosen is None:
                chosen = _next_unique_from_pool(variants)

            # Then global fallback pool
            if chosen is None:
                while fallback_idx < len(_FALLBACK_POOL):
                    candidate = _FALLBACK_POOL[fallback_idx]
                    fallback_idx += 1
                    if _allowed(candidate) and candidate not in used:
                        used.add(candidate)
                        chosen = candidate
                        break

            # As a last resort, use a unique numeric marker (should never happen)
            if chosen is None:
                marker = f"{event.event_type.value[:1].upper()}{len(used)}"
                used.add(marker)
                chosen = marker

            day_icons.append(chosen)

        result.append(day_icons)

    return result

