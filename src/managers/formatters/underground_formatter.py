"""Underground formatter (non-UI).

This module provides *display-agnostic* formatting and detection for
"black box" underground routing segments.

Why this exists
--------------
Some application/services need to render a compact label for a segment.
Importing the UI formatter from `src/ui/**` would violate the layering rules.

This formatter:
  - contains no Qt/UI imports
  - contains no IO
  - is deterministic
  - depends only on data passed in

The UI layer may still use its richer formatter for styling/widgets.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class RouteSegmentLike(Protocol):
    """Minimal segment shape required by the formatter."""

    service_pattern: str
    line_name: str
    from_station: str
    to_station: str
    distance_km: float | None
    journey_time_minutes: int | None


@dataclass(frozen=True)
class UndergroundSystemInfo:
    name: str
    short_name: str
    emoji: str
    time_range: str


SYSTEM_INFO: dict[str, UndergroundSystemInfo] = {
    "London Underground": UndergroundSystemInfo(
        name="London Underground",
        short_name="London Underground",
        emoji="🚇",
        time_range="10-40min",
    ),
    "Glasgow Subway": UndergroundSystemInfo(
        name="Glasgow Subway",
        short_name="Glasgow Subway",
        emoji="🚇",
        time_range="5-20min",
    ),
    "Tyne and Wear Metro": UndergroundSystemInfo(
        name="Tyne and Wear Metro",
        short_name="Tyne & Wear Metro",
        emoji="🚇",
        time_range="8-35min",
    ),
}


class UndergroundFormatter:
    """Pure helper to detect underground segments and derive system display info."""

    def is_underground_segment(self, segment: RouteSegmentLike) -> bool:
        return (
            segment.service_pattern == "UNDERGROUND"
            or segment.line_name in SYSTEM_INFO
            or segment.line_name == "UNDERGROUND"
        )

    def get_underground_system_info(self, segment: RouteSegmentLike) -> UndergroundSystemInfo | None:
        if not self.is_underground_segment(segment):
            return None

        # Exact match first.
        if segment.line_name in SYSTEM_INFO:
            return SYSTEM_INFO[segment.line_name]

        line_name_lower = segment.line_name.lower().strip()
        if any(term in line_name_lower for term in ("glasgow", "subway")):
            return SYSTEM_INFO["Glasgow Subway"]
        if any(term in line_name_lower for term in ("tyne", "wear", "metro", "nexus")):
            return SYSTEM_INFO["Tyne and Wear Metro"]
        if any(term in line_name_lower for term in ("london", "underground", "tube", "tfl")):
            return SYSTEM_INFO["London Underground"]

        # If service_pattern is UNDERGROUND but no system match, try to infer from stations.
        if segment.service_pattern == "UNDERGROUND":
            from_station = getattr(segment, "from_station", "").lower()
            to_station = getattr(segment, "to_station", "").lower()

            if any(term in from_station or term in to_station for term in ("glasgow", "buchanan", "st enoch")):
                return SYSTEM_INFO["Glasgow Subway"]
            if any(
                term in from_station or term in to_station
                for term in ("newcastle", "gateshead", "sunderland", "central station")
            ):
                return SYSTEM_INFO["Tyne and Wear Metro"]

        # Backwards-compatible default.
        return SYSTEM_INFO["London Underground"]

    def format_indicator_html(self, segment: RouteSegmentLike) -> str:
        """Return a minimal HTML-ish indicator string used by some services."""

        info = self.get_underground_system_info(segment)
        if not info:
            return ""
        return f"<font color='#DC241F'>{info.emoji} {info.short_name} ({info.time_range})</font>"

