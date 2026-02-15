"""Enums shared by combined forecast models.

Split out of `combined_forecast_data.py` to keep modules under the <= 400
non-blank LOC gate.
"""

from __future__ import annotations

from enum import Enum


class ForecastDataQuality(Enum):
    """Quality levels for forecast data."""

    EXCELLENT = "excellent"  # Both weather and astronomy data available
    GOOD = "good"  # One primary data source available
    PARTIAL = "partial"  # Limited data available
    POOR = "poor"  # Minimal or stale data


class CombinedDataStatus(Enum):
    """Status of combined forecast data."""

    COMPLETE = "complete"  # All data sources successful
    WEATHER_ONLY = "weather_only"  # Only weather data available
    ASTRONOMY_ONLY = "astronomy_only"  # Only astronomy data available
    PARTIAL_FAILURE = "partial_failure"  # Some data sources failed
    COMPLETE_FAILURE = "complete_failure"  # All data sources failed

