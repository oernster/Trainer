"""Validation logic for combined forecast data.

Split out of `combined_forecast_data.py` to keep modules under the <= 400
non-blank LOC gate.
"""

from __future__ import annotations


class CombinedForecastValidator:
    """Validator for combined forecast data integrity."""

    @staticmethod
    def validate_daily_forecast(daily_forecast) -> bool:
        """Validate daily forecast data."""

        try:
            # Must have at least one data source
            if (
                not daily_forecast.has_weather_data
                and not daily_forecast.has_astronomy_data
            ):
                return False

            # Validate date consistency
            if daily_forecast.weather_data:
                if daily_forecast.weather_data.timestamp.date() != daily_forecast.date:
                    return False

            if daily_forecast.astronomy_data:
                if daily_forecast.astronomy_data.date != daily_forecast.date:
                    return False

            return True
        except (AttributeError, TypeError):
            return False

    @staticmethod
    def validate_location_consistency(combined_forecast) -> bool:
        """Validate that all data sources use the same location."""

        base_location = combined_forecast.location

        if combined_forecast.weather_forecast:
            weather_location = combined_forecast.weather_forecast.location
            if (
                weather_location.latitude != base_location.latitude
                or weather_location.longitude != base_location.longitude
            ):
                return False

        if combined_forecast.astronomy_forecast:
            astronomy_location = combined_forecast.astronomy_forecast.location
            if (
                astronomy_location.latitude != base_location.latitude
                or astronomy_location.longitude != base_location.longitude
            ):
                return False

        return True

    @classmethod
    def validate_combined_forecast(cls, combined_forecast) -> bool:
        """Validate complete combined forecast data."""

        try:
            # Validate basic structure
            if not combined_forecast.daily_forecasts:
                return False

            # Validate location consistency
            if not cls.validate_location_consistency(combined_forecast):
                return False

            # Validate all daily forecasts
            for daily_forecast in combined_forecast.daily_forecasts:
                if not cls.validate_daily_forecast(daily_forecast):
                    return False

            # Validate chronological order
            dates = [forecast.date for forecast in combined_forecast.daily_forecasts]
            if dates != sorted(dates):
                return False

            # Validate no duplicates
            if len(dates) != len(set(dates)):
                return False

            return True
        except (AttributeError, TypeError):
            return False

