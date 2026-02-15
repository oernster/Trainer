"""Arrow-label builder for [`CallingPointsManager`](src/ui/widgets/train_components/calling_points_manager.py:25).

Extracted to keep modules under the <= 400 non-blank LOC gate.
"""

from __future__ import annotations

from typing import Any, Mapping

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel


def _is_html(text: str) -> bool:
    return "<font" in text and "</font>" in text


def _normalized_station_name(raw: str) -> str:
    return raw if _is_html(raw) else raw.strip()


def _segments_iter(train_data: Any):
    if not train_data:
        return []
    if not hasattr(train_data, "route_segments") or not train_data.route_segments:
        return []
    return train_data.route_segments


def _segment_connects(segment: Any, a: str, b: str) -> bool:
    raw_from = getattr(segment, "from_station", "")
    raw_to = getattr(segment, "to_station", "")
    seg_from = _normalized_station_name(raw_from)
    seg_to = _normalized_station_name(raw_to)

    return (seg_from == a and seg_to == b) or (seg_from == b and seg_to == a)


def _walk_info(segment: Any) -> str:
    walking_distance = getattr(segment, "distance_km", None)
    walking_time = getattr(segment, "journey_time_minutes", None)

    if walking_distance and walking_time:
        return f"Walk {walking_distance:.1f}km ({walking_time}min)"
    if walking_distance:
        return f"Walk {walking_distance:.1f}km"
    return "Walking connection"


def build_arrow_label(
    *,
    train_data: Any,
    underground_formatter: Any,
    theme: str,
    theme_colors: Mapping[str, str],
    prev_station_raw: str,
    curr_station_raw: str,
) -> QLabel:
    """Build the label used between two adjacent calling points."""

    prev_station = _normalized_station_name(prev_station_raw or "")
    curr_station = _normalized_station_name(curr_station_raw or "")

    # 1) Walking connections
    for segment in _segments_iter(train_data):
        if not _segment_connects(segment, prev_station, curr_station):
            continue

        line_name = getattr(segment, "line_name", "")
        service_pattern = getattr(segment, "service_pattern", "")
        is_walking = line_name == "WALKING" or service_pattern == "WALKING"
        if not is_walking:
            continue

        arrow_text = f"  → {_walk_info(segment)} →  "
        label = QLabel(arrow_text)
        label.setWordWrap(False)
        label.setTextFormat(Qt.TextFormat.PlainText)
        label.setStyleSheet(
            """
            QLabel {
                background-color: transparent;
                color: #f44336;
                border: none;
                margin: 0px;
                padding-left: 4px;
                padding-right: 4px;
            }
            """
        )
        return label

    # 2) Underground black-box segments
    for segment in _segments_iter(train_data):
        if not _segment_connects(segment, prev_station, curr_station):
            continue
        if not underground_formatter.is_underground_segment(segment):
            continue

        system_info = underground_formatter.get_underground_system_info(segment)
        system_name = system_info.get("short_name", "Underground")
        time_range = system_info.get("time_range", "10-40min")
        emoji = system_info.get("emoji", "🚇")
        underground_info = f"{emoji} {system_name} ({time_range})"

        arrow_text = f"  → {underground_info} →  "
        label = QLabel(arrow_text)
        label.setWordWrap(False)
        label.setTextFormat(Qt.TextFormat.PlainText)
        label.setStyleSheet(
            """
            QLabel {
                background-color: transparent;
                color: #DC241F;
                border: none;
                margin: 0px;
                padding-left: 4px;
                padding-right: 4px;
                font-weight: bold;
            }
            """
        )
        return label

    # 3) Default arrow
    label = QLabel("  →  ")
    label.setWordWrap(False)
    label.setTextFormat(Qt.TextFormat.PlainText)
    label.setStyleSheet(
        f"""
        QLabel {{
            background-color: transparent;
            color: {theme_colors['primary_accent']};
            border: none;
            margin: 0px;
            padding-left: 4px;
            padding-right: 4px;
        }}
        """
    )
    label.setFixedWidth(50)
    return label

