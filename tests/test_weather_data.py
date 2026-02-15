from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest

from src.models.weather_data import (
    EmojiWeatherIconStrategy,
    Location,
    TemperatureUnit,
    WeatherData,
    WeatherDataValidator,
    WeatherForecastData,
    WeatherIconProviderImpl,
)


def test_location_validation():
    Location(name="X", latitude=0.0, longitude=0.0)
    with pytest.raises(ValueError, match="Invalid latitude"):
        Location(name="X", latitude=100.0, longitude=0.0)
    with pytest.raises(ValueError, match="Invalid longitude"):
        Location(name="X", latitude=0.0, longitude=200.0)
    with pytest.raises(ValueError, match="cannot be empty"):
        Location(name=" ", latitude=0.0, longitude=0.0)


def test_weather_data_validation_and_displays():
    ts = datetime(2026, 1, 1, 12, 0)
    wd = WeatherData(timestamp=ts, temperature=10.25, humidity=55, weather_code=1, description="Clear")
    assert wd.temperature_display == "10.2°C"
    assert wd.humidity_display == "55%"
    assert wd.get_temperature_in_unit(TemperatureUnit.CELSIUS) == 10.25
    assert wd.get_temperature_in_unit(TemperatureUnit.FAHRENHEIT) == pytest.approx(50.45)
    assert wd.get_temperature_display_in_unit(TemperatureUnit.FAHRENHEIT).endswith("°F")
    assert wd.weather_code_enum is not None

    with pytest.raises(ValueError, match="Invalid humidity"):
        WeatherData(timestamp=ts, temperature=0.0, humidity=101, weather_code=1)
    with pytest.raises(ValueError, match="Invalid weather code"):
        WeatherData(timestamp=ts, temperature=0.0, humidity=10, weather_code=-1)


def test_weather_data_precipitation_and_severity():
    ts = datetime(2026, 1, 1, 12, 0)
    rain = WeatherData(timestamp=ts, temperature=5.0, humidity=80, weather_code=61)
    assert rain.is_precipitation() is True
    assert rain.is_severe_weather() is False

    heavy = WeatherData(timestamp=ts, temperature=5.0, humidity=80, weather_code=95)
    assert heavy.is_precipitation() is True
    assert heavy.is_severe_weather() is True

    clear = WeatherData(timestamp=ts, temperature=5.0, humidity=80, weather_code=0)
    assert clear.is_precipitation() is False
    assert clear.is_severe_weather() is False


def test_weather_forecast_data_validation_and_helpers(monkeypatch):
    loc = Location(name="X", latitude=0.0, longitude=0.0)
    now = datetime(2026, 1, 1, 10, 0)

    class _FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):  # match datetime.now signature
            if tz is not None:
                return now.astimezone(tz)
            return now

    monkeypatch.setattr("src.models.weather_data.datetime", _FixedDateTime)

    h1 = WeatherData(timestamp=now - timedelta(hours=1), temperature=5.0, humidity=50, weather_code=0)
    h2 = WeatherData(timestamp=now + timedelta(hours=2), temperature=7.0, humidity=50, weather_code=0)
    daily = WeatherData(timestamp=now, temperature=6.0, humidity=50, weather_code=0)

    forecast = WeatherForecastData(location=loc, hourly_forecast=[h1, h2], daily_forecast=[daily])
    assert forecast.is_stale is False
    assert forecast.current_day_hourly == [h1, h2]
    assert forecast.get_current_weather() in {h1, h2}
    assert forecast.get_hourly_for_date(date(2026, 1, 1)) == [h1, h2]
    assert forecast.get_daily_summary_for_date(date(2026, 1, 1)) == daily
    assert forecast.has_severe_weather_today() is False
    assert forecast.get_temperature_range_today() == (5.0, 7.0)

    with pytest.raises(ValueError, match="Forecast must contain"):
        WeatherForecastData(location=loc)


def test_weather_icon_strategy_and_provider(caplog):
    caplog.set_level("INFO")
    strategy = EmojiWeatherIconStrategy()
    assert strategy.get_icon(0)
    assert strategy.get_icon(999) == "❓"
    assert strategy.get_strategy_name() == "emoji"

    provider = WeatherIconProviderImpl(strategy)
    assert provider.get_weather_icon(0)
    assert provider.get_current_strategy_name() == "emoji"

    class _Alt(EmojiWeatherIconStrategy):
        def get_strategy_name(self) -> str:
            return "alt"

    provider.set_strategy(_Alt())
    assert provider.get_current_strategy_name() == "alt"
    assert any("Icon strategy changed" in r.message for r in caplog.records)


def test_weather_data_validator():
    assert WeatherDataValidator.validate_temperature(-100.0) is True
    assert WeatherDataValidator.validate_temperature(60.0) is True
    assert WeatherDataValidator.validate_temperature(-101.0) is False

    assert WeatherDataValidator.validate_humidity(0) is True
    assert WeatherDataValidator.validate_humidity(100) is True
    assert WeatherDataValidator.validate_humidity(101) is False

    assert WeatherDataValidator.validate_weather_code(0) is True
    assert WeatherDataValidator.validate_weather_code(999) is False

    now = datetime.now()
    assert WeatherDataValidator.validate_timestamp(now) is True
    assert WeatherDataValidator.validate_timestamp(now - timedelta(days=2)) is False
    assert WeatherDataValidator.validate_timestamp(now + timedelta(days=8)) is False

    wd = WeatherData(timestamp=now, temperature=0.0, humidity=50, weather_code=0)
    assert WeatherDataValidator.validate_weather_data(wd) is True

    loc = Location(name="X", latitude=0.0, longitude=0.0)
    forecast = WeatherForecastData(location=loc, hourly_forecast=[wd])
    assert WeatherDataValidator.validate_forecast_data(forecast) is True

