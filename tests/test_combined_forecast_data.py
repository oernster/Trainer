from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest

from src.models.astronomy_daily_models import AstronomyData
from src.models.astronomy_event_models import AstronomyEvent, AstronomyEventType
from src.models.astronomy_forecast_models import AstronomyForecastData, Location as AstronomyLocation
from src.models.combined_forecast_data import (
    CombinedForecastData,
    DailyForecastData,
    create_astronomy_only_forecast,
    create_complete_forecast,
    create_weather_only_forecast,
)
from src.models.combined_forecast_enums import CombinedDataStatus, ForecastDataQuality
from src.models.combined_forecast_validator import CombinedForecastValidator
from src.models.weather_data import Location as WeatherLocation
from src.models.weather_data import WeatherData, WeatherForecastData


def _fixed_today(monkeypatch, today: date) -> None:
    import src.models.combined_forecast_data as mod

    class _FixedDate(date):
        @classmethod
        def today(cls):
            return today

    monkeypatch.setattr(mod, "date", _FixedDate)


def test_daily_forecast_data_validation_and_properties():
    d = date(2026, 1, 1)
    ts = datetime(2026, 1, 1, 12, 0)
    wd = WeatherData(timestamp=ts, temperature=10.0, humidity=50, weather_code=0)
    ad = AstronomyData(date=d)

    df = DailyForecastData(date=d, weather_data=wd, astronomy_data=ad)
    assert df.has_complete_data is True
    assert df.has_weather_data is True
    assert df.has_astronomy_data is True
    assert df.astronomy_event_count == 0
    assert df.has_high_priority_astronomy is False
    assert df.weather_description == ""
    assert df.temperature_display
    assert df.is_precipitation_day is False
    assert df.moon_phase_icon
    assert df.get_astronomy_events_by_type(AstronomyEventType.APOD) == []
    assert df.get_display_summary() == "10.0°C • "

    with pytest.raises(ValueError, match="must contain either"):
        DailyForecastData(date=d)

    with pytest.raises(ValueError, match="Weather data date must match"):
        DailyForecastData(
            date=d,
            weather_data=WeatherData(
                timestamp=datetime(2026, 1, 2, 12, 0),
                temperature=10.0,
                humidity=50,
                weather_code=0,
            ),
        )

    with pytest.raises(ValueError, match="Astronomy data date must match"):
        DailyForecastData(date=d, astronomy_data=AstronomyData(date=date(2026, 1, 2)))


def test_combined_forecast_data_post_init_validates_order_and_duplicates():
    loc = WeatherLocation(name="X", latitude=0.0, longitude=0.0)
    d1 = date(2026, 1, 1)
    d2 = date(2026, 1, 2)
    ts1 = datetime(2026, 1, 1, 12, 0)
    ts2 = datetime(2026, 1, 2, 12, 0)
    df1 = DailyForecastData(date=d1, weather_data=WeatherData(timestamp=ts1, temperature=10.0, humidity=50, weather_code=0))
    df2 = DailyForecastData(date=d2, weather_data=WeatherData(timestamp=ts2, temperature=11.0, humidity=50, weather_code=0))

    CombinedForecastData(location=loc, daily_forecasts=[df1, df2])

    # Default status is COMPLETE_FAILURE, which permits empty forecasts.
    with pytest.raises(ValueError, match="at least one"):
        CombinedForecastData(
            location=loc,
            daily_forecasts=[],
            status=CombinedDataStatus.WEATHER_ONLY,
        )

    with pytest.raises(ValueError, match="chronological"):
        CombinedForecastData(location=loc, daily_forecasts=[df2, df1])

    with pytest.raises(ValueError, match="duplicate"):
        CombinedForecastData(location=loc, daily_forecasts=[df1, df1])

    # Duplicate date is validated before max length.
    with pytest.raises(ValueError, match="duplicate"):
        CombinedForecastData(location=loc, daily_forecasts=[df1] * 15)


def test_combined_forecast_create_no_sources_returns_failure(monkeypatch):
    _fixed_today(monkeypatch, date(2026, 1, 1))
    loc = WeatherLocation(name="X", latitude=0.0, longitude=0.0)
    combined = CombinedForecastData.create(location=loc)
    assert combined.status == CombinedDataStatus.COMPLETE_FAILURE
    assert combined.error_messages == ["No weather or astronomy data available"]


def test_combined_forecast_create_weather_only(monkeypatch):
    _fixed_today(monkeypatch, date(2026, 1, 1))
    loc = WeatherLocation(name="X", latitude=0.0, longitude=0.0)

    d1 = datetime(2026, 1, 1, 12, 0)
    d2 = datetime(2026, 1, 2, 12, 0)
    wd1 = WeatherData(timestamp=d1, temperature=10.0, humidity=50, weather_code=0)
    wd2 = WeatherData(timestamp=d2, temperature=11.0, humidity=50, weather_code=61)
    weather = WeatherForecastData(location=loc, daily_forecast=[wd1, wd2])

    combined = CombinedForecastData.create(location=loc, weather_data=weather, astronomy_data=None)
    assert combined.status == CombinedDataStatus.WEATHER_ONLY
    assert combined.has_weather_data is True
    assert combined.has_astronomy_data is False
    assert "Astronomy data unavailable" in combined.error_messages
    assert combined.forecast_days == 2
    assert combined.get_precipitation_days()


def test_combined_forecast_create_astronomy_only(monkeypatch):
    _fixed_today(monkeypatch, date(2026, 1, 1))
    loc = WeatherLocation(name="X", latitude=0.0, longitude=0.0)
    aloc = AstronomyLocation(name="X", latitude=0.0, longitude=0.0)
    a1 = AstronomyData(date=date(2026, 1, 1))
    a2 = AstronomyData(date=date(2026, 1, 2))
    astronomy = AstronomyForecastData(location=aloc, daily_astronomy=[a1, a2])

    combined = CombinedForecastData.create(location=loc, weather_data=None, astronomy_data=astronomy)
    assert combined.status == CombinedDataStatus.ASTRONOMY_ONLY
    assert combined.has_weather_data is False
    assert combined.has_astronomy_data is True
    assert "Weather data unavailable" in combined.error_messages
    assert combined.get_forecasts_with_astronomy()


def test_combined_forecast_create_complete_and_quality_paths(monkeypatch):
    _fixed_today(monkeypatch, date(2026, 1, 1))
    loc = WeatherLocation(name="X", latitude=0.0, longitude=0.0)
    aloc = AstronomyLocation(name="X", latitude=0.0, longitude=0.0)

    # Weather has daily for day1; hourly for day2 (noon) so _get_weather_for_date uses fallback.
    wd1 = WeatherData(timestamp=datetime(2026, 1, 1, 9, 0), temperature=10.0, humidity=50, weather_code=0)
    wh2 = WeatherData(timestamp=datetime(2026, 1, 2, 12, 0), temperature=11.0, humidity=50, weather_code=0)
    weather = WeatherForecastData(location=loc, daily_forecast=[wd1], hourly_forecast=[wh2])

    # Astronomy day1 has an event -> EXCELLENT; day2 has no events -> GOOD when combined.
    e = AstronomyEvent(
        event_type=AstronomyEventType.APOD,
        title="A",
        description="Desc",
        start_time=datetime(2026, 1, 1, 10, 0),
    )
    a1 = AstronomyData(date=date(2026, 1, 1), events=[e], primary_event=e)
    a2 = AstronomyData(date=date(2026, 1, 2))
    astronomy = AstronomyForecastData(location=aloc, daily_astronomy=[a1, a2])

    combined = CombinedForecastData.create(location=loc, weather_data=weather, astronomy_data=astronomy)
    assert combined.status == CombinedDataStatus.COMPLETE
    assert combined.has_complete_data is True
    assert combined.total_astronomy_events == 1
    assert combined.has_high_priority_astronomy is False

    qualities = {f.date: f.data_quality for f in combined.daily_forecasts}
    assert qualities[date(2026, 1, 1)] == ForecastDataQuality.EXCELLENT
    assert qualities[date(2026, 1, 2)] == ForecastDataQuality.GOOD

    summary = combined.data_quality_summary
    assert sum(summary.values()) == len(combined.daily_forecasts)
    assert combined.get_status_summary()
    assert combined.get_error_summary() == "No errors"


def test_combined_forecast_factories_delegate(monkeypatch):
    _fixed_today(monkeypatch, date(2026, 1, 1))
    loc = WeatherLocation(name="X", latitude=0.0, longitude=0.0)
    aloc = AstronomyLocation(name="X", latitude=0.0, longitude=0.0)

    wd = WeatherData(timestamp=datetime(2026, 1, 1, 12, 0), temperature=10.0, humidity=50, weather_code=0)
    weather = WeatherForecastData(location=loc, daily_forecast=[wd])
    astronomy = AstronomyForecastData(location=aloc, daily_astronomy=[AstronomyData(date=date(2026, 1, 1))])

    w_only = create_weather_only_forecast(loc, weather)
    a_only = create_astronomy_only_forecast(loc, astronomy)
    complete = create_complete_forecast(loc, weather, astronomy)

    assert w_only.status == CombinedDataStatus.WEATHER_ONLY
    assert a_only.status == CombinedDataStatus.ASTRONOMY_ONLY
    assert complete.status in {CombinedDataStatus.COMPLETE, CombinedDataStatus.PARTIAL_FAILURE}


def test_combined_forecast_validator():
    loc = WeatherLocation(name="X", latitude=0.0, longitude=0.0)
    ts = datetime(2026, 1, 1, 12, 0)
    df = DailyForecastData(date=date(2026, 1, 1), weather_data=WeatherData(timestamp=ts, temperature=10.0, humidity=50, weather_code=0))
    combined = CombinedForecastData(location=loc, daily_forecasts=[df])

    assert CombinedForecastValidator.validate_daily_forecast(df) is True
    assert CombinedForecastValidator.validate_location_consistency(combined) is True
    assert CombinedForecastValidator.validate_combined_forecast(combined) is True

    assert CombinedForecastValidator.validate_daily_forecast(object()) is False
    class _Bad:
        location = object()
        weather_forecast = None
        astronomy_forecast = None

    assert CombinedForecastValidator.validate_location_consistency(_Bad()) is True
    assert CombinedForecastValidator.validate_combined_forecast(_Bad()) is False

