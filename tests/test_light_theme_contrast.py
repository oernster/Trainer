from __future__ import annotations

from datetime import datetime

import pytest

from src.models.train_data import CallingPoint, ServiceType, TrainData, TrainStatus
from src.ui.widgets.train_item_widget import TrainItemWidget


def test_train_item_widget_propagates_light_theme_to_children(qtbot):
    """Regression: ensure we don't end up with white-on-white text in light mode.

    Child components apply their own stylesheets, so TrainItemWidget must
    propagate theme changes down to them.
    """

    now = datetime(2026, 1, 1, 12, 0, 0)
    cps = [
        CallingPoint(
            station_name="Origin",
            scheduled_arrival=None,
            scheduled_departure=now,
            expected_arrival=None,
            expected_departure=now,
            platform=None,
            is_origin=True,
            is_destination=False,
        ),
        CallingPoint(
            station_name="Destination",
            scheduled_arrival=now,
            scheduled_departure=None,
            expected_arrival=now,
            expected_departure=None,
            platform=None,
            is_origin=False,
            is_destination=True,
        ),
    ]

    train = TrainData(
        departure_time=now,
        scheduled_departure=now,
        destination="Destination",
        platform="1",
        operator="Great Western Railway",
        service_type=ServiceType.FAST,
        status=TrainStatus.ON_TIME,
        delay_minutes=0,
        estimated_arrival=now,
        journey_duration=None,
        current_location=None,
        train_uid="uid",
        service_id="service",
        calling_points=cps,
        route_segments=None,
        full_calling_points=None,
    )

    w = TrainItemWidget(train, theme="dark")
    qtbot.addWidget(w)

    # Switch to light theme.
    w.update_theme("light")

    assert w.current_theme == "light"
    assert w.main_info_section._current_theme == "light"
    assert w.details_section._current_theme == "light"
    assert w.calling_points_manager._current_theme == "light"
    assert w.location_section._current_theme == "light"

    # The child component stylesheets should contain a dark text color.
    assert "color: #212121" in w.main_info_section.styleSheet()
    assert "color: #212121" in w.details_section.styleSheet()
    assert "color: #212121" in w.calling_points_manager.styleSheet()
    assert "color: #212121" in w.location_section.styleSheet()

