"""Pydantic configuration models.

Extracted from [`src/managers/config_manager.py`](src/managers/config_manager.py:1)
to keep modules below the <=400 LOC quality gate.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field

from .astronomy_config import AstronomyConfig
from .weather_config import WeatherConfig, WeatherConfigFactory


class APIConfig(BaseModel):
    """Configuration for Transport API access."""

    app_id: str = Field(..., description="Transport API app ID")
    app_key: str = Field(..., description="Transport API app key")
    base_url: str = "https://transportapi.com/v3/uk"
    timeout_seconds: int = 10
    max_retries: int = 3
    rate_limit_per_minute: int = 30


class StationConfig(BaseModel):
    """Configuration for station names (codes removed)."""

    from_code: str = "Fleet"  # Now stores station name, not code
    from_name: str = "Fleet"
    to_code: str = "London Waterloo"  # Now stores station name, not code
    to_name: str = "London Waterloo"
    via_stations: List[str] = []
    route_auto_fixed: bool = False
    departure_time: str = ""  # Optional departure time in HH:MM format
    route_path: List[str] = []  # Store the complete route path for persistence


class RefreshConfig(BaseModel):
    """Configuration for data refresh settings."""

    auto_enabled: bool = True
    interval_minutes: int = 30
    manual_enabled: bool = True


class DisplayConfig(BaseModel):
    """Configuration for display settings."""

    max_trains: int = 100  # Increased to accommodate all railway lines
    time_window_hours: int = 16
    theme: str = "dark"  # "dark" or "light"


class UIConfig(BaseModel):
    """Configuration for UI state persistence."""

    weather_widget_visible: bool = True
    astronomy_widget_visible: bool = True

    # Window sizing per widget state (width, height)
    window_size_both_visible: tuple[int, int] = (1100, 1200)
    window_size_weather_only: tuple[int, int] = (1100, 800)
    window_size_astronomy_only: tuple[int, int] = (1100, 750)
    window_size_trains_only: tuple[int, int] = (1100, 500)


class ConfigData(BaseModel):
    """Main configuration data model with weather and astronomy integration."""

    api: APIConfig
    stations: StationConfig
    refresh: RefreshConfig
    display: DisplayConfig
    ui: UIConfig = UIConfig()  # Default UI state
    weather: Optional[WeatherConfig] = None
    astronomy: Optional[AstronomyConfig] = None

    # Route preferences
    optimize_for_speed: bool = True
    show_intermediate_stations: bool = True
    avoid_london: bool = False
    prefer_direct: bool = False
    avoid_walking: bool = False
    max_walking_distance_km: float = 1.0
    max_changes: int = 3
    max_journey_time: int = 8
    train_lookahead_hours: int = 16

    def __init__(self, **data):
        # If weather config is not provided, create default.
        if "weather" not in data or data["weather"] is None:
            data["weather"] = WeatherConfigFactory.create_waterloo_config()

        # If astronomy config is not provided, create default.
        if "astronomy" not in data or data["astronomy"] is None:
            data["astronomy"] = AstronomyConfig.create_default()

        # If UI config is not provided, create default (back-compat).
        if "ui" not in data or data["ui"] is None:
            data["ui"] = UIConfig()

        super().__init__(**data)


class ConfigurationError(Exception):
    """Exception raised for configuration-related errors."""


