from __future__ import annotations

from src.managers.services.route_calc_components.route_objects import MinimalSegment
from src.ui.formatters.underground_formatter import UndergroundFormatter


def test_minimal_segment_has_service_pattern_for_ui_protocol() -> None:
    """Regression: Train list rows must not crash when fallback `MinimalRoute` is used.

    The UI Underground formatter requires `segment.service_pattern: str`.
    """

    seg = MinimalSegment(from_station="A", to_station="B", is_walking=False)
    assert seg.service_pattern == "RAIL"


def test_minimal_walking_segment_service_pattern_is_walking() -> None:
    seg = MinimalSegment(from_station="A", to_station="B", is_walking=True)
    assert seg.service_pattern == "WALKING"


def test_underground_formatter_does_not_treat_minimal_segment_as_underground() -> None:
    fmt = UndergroundFormatter()
    seg = MinimalSegment(from_station="A", to_station="B", is_walking=False)
    assert fmt.is_underground_segment(seg) is False
