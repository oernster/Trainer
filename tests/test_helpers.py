from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta

import pytest

import src.utils.helpers as helpers
from src.models.train_data import CallingPoint, ServiceType, TrainData, TrainStatus


def _train(*, departure_time: datetime, status: TrainStatus, delay_minutes: int) -> TrainData:
    return TrainData(
        departure_time=departure_time,
        scheduled_departure=departure_time,
        destination="Somewhere",
        platform=None,
        operator="TestRail",
        service_type=ServiceType.FAST,
        status=status,
        delay_minutes=delay_minutes,
        estimated_arrival=None,
        journey_duration=timedelta(minutes=42),
        current_location=None,
        train_uid="UID",
        service_id="SID",
        calling_points=[
            CallingPoint(
                station_name="Origin",
                scheduled_arrival=None,
                scheduled_departure=departure_time,
                expected_arrival=None,
                expected_departure=None,
                platform=None,
                is_origin=True,
                is_destination=False,
            ),
            CallingPoint(
                station_name="Destination",
                scheduled_arrival=departure_time + timedelta(minutes=42),
                scheduled_departure=None,
                expected_arrival=None,
                expected_departure=None,
                platform=None,
                is_origin=False,
                is_destination=True,
            ),
        ],
    )


def test_format_time():
    assert helpers.format_time(datetime(2026, 1, 1, 9, 5)) == "09:05"


def test_format_duration_minutes_only():
    assert helpers.format_duration(timedelta(minutes=45)) == "45m"


def test_format_duration_hours_and_minutes():
    assert helpers.format_duration(timedelta(minutes=90)) == "1h 30m"


def test_get_time_group_classification():
    now = datetime(2026, 1, 1, 10, 0)
    assert helpers.get_time_group(_train(departure_time=now, status=TrainStatus.ON_TIME, delay_minutes=0), now) == "Next Hour"
    assert helpers.get_time_group(_train(departure_time=now + timedelta(hours=2), status=TrainStatus.ON_TIME, delay_minutes=0), now) == "Next 3 Hours"
    assert helpers.get_time_group(_train(departure_time=now + timedelta(hours=5), status=TrainStatus.ON_TIME, delay_minutes=0), now) == "Later Today"
    assert helpers.get_time_group(_train(departure_time=now + timedelta(days=1, hours=1), status=TrainStatus.ON_TIME, delay_minutes=0), now) == "Tomorrow"


def test_group_trains_by_time_uses_current_time(monkeypatch):
    fixed_now = datetime(2026, 1, 1, 10, 0)

    class _FixedDateTime(datetime):
        @classmethod
        def now(cls):  # noqa: D401 - matches datetime API
            return fixed_now

    monkeypatch.setattr(helpers, "datetime", _FixedDateTime)
    trains = [
        _train(departure_time=fixed_now + timedelta(minutes=10), status=TrainStatus.ON_TIME, delay_minutes=0),
        _train(departure_time=fixed_now + timedelta(hours=2), status=TrainStatus.ON_TIME, delay_minutes=0),
    ]

    grouped = helpers.group_trains_by_time(trains)
    assert list(grouped.keys()) == ["Next Hour", "Next 3 Hours"]
    assert len(grouped["Next Hour"]) == 1
    assert len(grouped["Next 3 Hours"]) == 1


def test_filter_trains_by_status_excludes_cancelled_when_requested():
    trains = [
        _train(departure_time=datetime(2026, 1, 1, 10, 0), status=TrainStatus.ON_TIME, delay_minutes=0),
        _train(departure_time=datetime(2026, 1, 1, 11, 0), status=TrainStatus.CANCELLED, delay_minutes=0),
    ]
    assert helpers.filter_trains_by_status(trains, include_cancelled=True) == trains
    assert helpers.filter_trains_by_status(trains, include_cancelled=False) == [trains[0]]


def test_sort_trains_by_departure_sorts_ascending():
    t1 = _train(departure_time=datetime(2026, 1, 1, 11, 0), status=TrainStatus.ON_TIME, delay_minutes=0)
    t2 = _train(departure_time=datetime(2026, 1, 1, 10, 0), status=TrainStatus.ON_TIME, delay_minutes=0)
    assert helpers.sort_trains_by_departure([t1, t2]) == [t2, t1]


def test_get_next_departure_raises_for_empty_list():
    with pytest.raises(ValueError, match="No trains provided"):
        helpers.get_next_departure([])


def test_get_next_departure_raises_when_no_future_departures(monkeypatch):
    fixed_now = datetime(2026, 1, 1, 10, 0)

    class _FixedDateTime(datetime):
        @classmethod
        def now(cls):
            return fixed_now

    monkeypatch.setattr(helpers, "datetime", _FixedDateTime)
    trains = [
        _train(departure_time=fixed_now - timedelta(minutes=1), status=TrainStatus.ON_TIME, delay_minutes=0),
    ]

    with pytest.raises(ValueError, match="No future departures found"):
        helpers.get_next_departure(trains)


def test_get_next_departure_returns_earliest_future_train(monkeypatch):
    fixed_now = datetime(2026, 1, 1, 10, 0)

    class _FixedDateTime(datetime):
        @classmethod
        def now(cls):
            return fixed_now

    monkeypatch.setattr(helpers, "datetime", _FixedDateTime)

    t_late = _train(departure_time=fixed_now + timedelta(minutes=40), status=TrainStatus.ON_TIME, delay_minutes=0)
    t_soon = _train(departure_time=fixed_now + timedelta(minutes=10), status=TrainStatus.ON_TIME, delay_minutes=0)
    t_past = _train(departure_time=fixed_now - timedelta(minutes=10), status=TrainStatus.ON_TIME, delay_minutes=0)

    assert helpers.get_next_departure([t_late, t_soon, t_past]) == t_soon


def test_calculate_journey_stats_empty():
    assert helpers.calculate_journey_stats([]) == {
        "total_trains": 0,
        "on_time": 0,
        "delayed": 0,
        "cancelled": 0,
        "average_delay": 0,
        "max_delay": 0,
    }


def test_calculate_journey_stats_non_empty_counts_and_delay_metrics():
    trains = [
        _train(departure_time=datetime(2026, 1, 1, 10, 0), status=TrainStatus.ON_TIME, delay_minutes=0),
        _train(departure_time=datetime(2026, 1, 1, 11, 0), status=TrainStatus.DELAYED, delay_minutes=5),
        _train(departure_time=datetime(2026, 1, 1, 12, 0), status=TrainStatus.DELAYED, delay_minutes=15),
        _train(departure_time=datetime(2026, 1, 1, 13, 0), status=TrainStatus.CANCELLED, delay_minutes=0),
    ]
    stats = helpers.calculate_journey_stats(trains)
    assert stats["total_trains"] == 4
    assert stats["on_time"] == 1
    assert stats["delayed"] == 2
    assert stats["cancelled"] == 1
    assert stats["average_delay"] == 10.0
    assert stats["max_delay"] == 15


def test_format_relative_time_past_and_future():
    now = datetime(2026, 1, 1, 10, 0, 0)
    assert helpers.format_relative_time(now + timedelta(seconds=10), now) == "10 seconds from now"
    assert helpers.format_relative_time(now - timedelta(seconds=10), now) == "10 seconds ago"
    assert helpers.format_relative_time(now + timedelta(minutes=2), now) == "2 minutes from now"
    assert helpers.format_relative_time(now - timedelta(hours=1), now) == "1 hour ago"
    assert helpers.format_relative_time(now + timedelta(days=2), now) == "2 days from now"


def test_validate_time_window_and_refresh_interval():
    assert helpers.validate_time_window(1) is True
    assert helpers.validate_time_window(24) is True
    assert helpers.validate_time_window(0) is False
    assert helpers.validate_time_window(25) is False

    assert helpers.validate_refresh_interval(1) is True
    assert helpers.validate_refresh_interval(60) is True
    assert helpers.validate_refresh_interval(0) is False
    assert helpers.validate_refresh_interval(61) is False


def test_get_status_summary():
    assert helpers.get_status_summary([]) == "No trains"

    trains = [
        _train(departure_time=datetime(2026, 1, 1, 10, 0), status=TrainStatus.ON_TIME, delay_minutes=0),
        _train(departure_time=datetime(2026, 1, 1, 11, 0), status=TrainStatus.DELAYED, delay_minutes=1),
        _train(departure_time=datetime(2026, 1, 1, 12, 0), status=TrainStatus.CANCELLED, delay_minutes=0),
    ]
    assert helpers.get_status_summary(trains) == "1 on time, 1 delayed, 1 cancelled"


def test_get_status_summary_when_no_known_categories_returns_total_count():
    trains = [
        _train(departure_time=datetime(2026, 1, 1, 10, 0), status=TrainStatus.UNKNOWN, delay_minutes=0),
        _train(departure_time=datetime(2026, 1, 1, 11, 0), status=TrainStatus.UNKNOWN, delay_minutes=0),
    ]
    assert helpers.get_status_summary(trains) == "2 trains"


def test_filter_trains_by_status_does_not_mutate_input_list():
    t1 = _train(departure_time=datetime(2026, 1, 1, 10, 0), status=TrainStatus.ON_TIME, delay_minutes=0)
    t2 = _train(departure_time=datetime(2026, 1, 1, 11, 0), status=TrainStatus.CANCELLED, delay_minutes=0)
    trains = [t1, t2]
    original = list(trains)
    _ = helpers.filter_trains_by_status(trains, include_cancelled=False)
    assert trains == original

