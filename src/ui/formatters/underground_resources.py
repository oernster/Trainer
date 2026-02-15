"""Shared resources for the Underground UI formatter.

This module deliberately contains only UI-layer data/helpers. It must not import
from the core domain.
"""

from __future__ import annotations


SYSTEM_INFO: dict[str, dict[str, str]] = {
    "London Underground": {
        "name": "London Underground",
        "emoji": "🚇",
        "color": "#DC241F",  # TfL red
        "time_range": "10-40min",
        "short_name": "London Underground",
    },
    "Glasgow Subway": {
        "name": "Glasgow Subway",
        "emoji": "🚇",
        "color": "#FF6600",  # SPT orange
        "time_range": "5-20min",
        "short_name": "Glasgow Subway",
    },
    "Tyne and Wear Metro": {
        "name": "Tyne and Wear Metro",
        "emoji": "🚇",
        "color": "#FFD700",  # Metro yellow
        "time_range": "8-35min",
        "short_name": "Tyne & Wear Metro",
    },
}


def build_underground_css_styles(
    *,
    underground_background: str,
    underground_color: str,
    regular_background: str,
    regular_color: str,
) -> str:
    """Return a CSS snippet used by some widgets to style route segments."""

    return f"""
        .underground-segment {{
            background-color: {underground_background};
            border: 2px solid {underground_color};
            border-radius: 6px;
            padding: 8px;
            margin: 4px 0;
            color: {underground_color};
            font-weight: bold;
        }}

        .underground-icon {{
            color: {underground_color};
            font-size: 18px;
            margin-right: 8px;
        }}

        .underground-text {{
            color: {underground_color};
            font-weight: bold;
        }}

        .underground-time {{
            color: {underground_color};
            font-style: italic;
            margin-left: 8px;
        }}

        .regular-segment {{
            background-color: {regular_background};
            border: 1px solid #cccccc;
            border-radius: 4px;
            padding: 6px;
            margin: 2px 0;
            color: {regular_color};
        }}

        .route-legend {{
            background-color: #f9f9f9;
            border: 1px solid #dddddd;
            border-radius: 4px;
            padding: 8px;
            margin: 4px 0;
            font-size: 12px;
        }}
        """


UNDERGROUND_WARNING_TEXT = (
    "Underground routing is simplified. Check the relevant transport authority website or app "
    "(TfL for London Underground, SPT for Glasgow Subway, Nexus for Tyne & Wear Metro) for detailed "
    "journey planning, live service updates, and accessibility information."
)

