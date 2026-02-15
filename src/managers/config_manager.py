"""Configuration management (load/save/migrate).

Model definitions live in [`src/managers/config_models.py`](src/managers/config_models.py:1)
to keep each module below the <=400 LOC quality gate.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Optional

from version import __version__

from .config_models import (
    APIConfig,
    ConfigData,
    ConfigurationError,
    DisplayConfig,
    RefreshConfig,
    StationConfig,
    UIConfig,
)
from .weather_config import WeatherConfig, WeatherConfigFactory, WeatherConfigMigrator
from .astronomy_config import AstronomyConfig

logger = logging.getLogger(__name__)


class ConfigManager:
    """Manages application configuration with file persistence."""

    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            self.config_path = self.get_default_config_path()
        else:
            self.config_path = Path(config_path)
        self.config: Optional[ConfigData] = None
        logger.debug("ConfigManager initialized with path: %s", self.config_path)

    @staticmethod
    def get_default_config_path() -> Path:
        if os.name == "nt":
            appdata = os.environ.get("APPDATA")
            if appdata:
                config_dir = Path(appdata) / "Trainer"
                config_dir.mkdir(parents=True, exist_ok=True)
                return config_dir / "config.json"
        else:
            xdg_config = os.environ.get("XDG_CONFIG_HOME")
            if xdg_config:
                config_dir = Path(xdg_config) / "Trainer"
            else:
                config_dir = Path.home() / ".config" / "Trainer"
            config_dir.mkdir(parents=True, exist_ok=True)
            return config_dir / "config.json"

        return Path("config.json")

    def install_default_config_to_appdata(self) -> bool:
        try:
            if os.name != "nt":
                return False

            appdata = os.environ.get("APPDATA")
            if not appdata:
                return False

            config_dir = Path(appdata) / "Trainer"
            config_dir.mkdir(parents=True, exist_ok=True)
            appdata_config_path = config_dir / "config.json"

            if not appdata_config_path.exists():
                default_config = ConfigData(
                    api=APIConfig(app_id="YOUR_APP_ID_HERE", app_key="YOUR_APP_KEY_HERE"),
                    stations=StationConfig(),
                    refresh=RefreshConfig(),
                    display=DisplayConfig(),
                    ui=UIConfig(),
                    weather=WeatherConfigFactory.create_waterloo_config(),
                    astronomy=AstronomyConfig.create_default(),
                )
                appdata_config_path.write_text(
                    json.dumps(default_config.model_dump(), indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
                return True

            return True
        except Exception as exc:  # pragma: no cover
            logger.warning("Failed to install config to AppData: %s", exc)
            return False

    def load_config(self) -> ConfigData:
        logger.debug("Loading config from: %s", self.config_path)

        if not self.config_path.exists():
            logger.info("Config missing; creating default at: %s", self.config_path)
            self.create_default_config()

        try:
            data = json.loads(self.config_path.read_text(encoding="utf-8"))
            self.config = ConfigData(**data)
            logger.debug("Successfully loaded config from: %s", self.config_path)
            return self.config
        except json.JSONDecodeError as exc:
            raise ConfigurationError(f"Invalid JSON in config file: {exc}")
        except Exception as exc:
            raise ConfigurationError(f"Failed to load config: {exc}")

    def save_config(self, config: ConfigData, force_flush: bool = False) -> bool:
        logger.info("Saving config to: %s", self.config_path)
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            config_json = config.model_dump()

            # Ensure route_path is a list.
            stations = config_json.get("stations")
            if isinstance(stations, dict) and "route_path" in stations:
                if not isinstance(stations["route_path"], list):
                    logger.warning("Invalid route_path type %s; resetting", type(stations["route_path"]))
                    stations["route_path"] = []

            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(config_json, f, indent=2, ensure_ascii=False)
                if force_flush:
                    f.flush()
                    os.fsync(f.fileno())

            self.config = config
            return True
        except Exception as exc:
            logger.error("Failed to save config to %s: %s", self.config_path, exc)
            return False

    def create_default_config(self) -> None:
        default_config = ConfigData(
            api=APIConfig(app_id="YOUR_APP_ID_HERE", app_key="YOUR_APP_KEY_HERE"),
            stations=StationConfig(),
            refresh=RefreshConfig(),
            display=DisplayConfig(),
            ui=UIConfig(),
            weather=WeatherConfigFactory.create_waterloo_config(),
            astronomy=AstronomyConfig.create_default(),
        )
        self.save_config(default_config)

    def validate_api_credentials(self) -> bool:
        if self.config is None:
            self.load_config()
        if not self.config:
            return False
        return (
            self.config.api.app_id != "YOUR_APP_ID_HERE"
            and self.config.api.app_key != "YOUR_APP_KEY_HERE"
            and bool(self.config.api.app_id)
            and bool(self.config.api.app_key)
        )

    def get_config_summary(self) -> dict:
        if self.config is None:
            self.load_config()
        if not self.config:
            return {"error": "Configuration not loaded"}

        summary = {
            "app_version": __version__,
            "theme": self.config.display.theme,
            "refresh_interval": f"{self.config.refresh.interval_minutes} minutes",
            "time_window": f"{self.config.display.time_window_hours} hours",
            "max_trains": self.config.display.max_trains,
            "auto_refresh": "Enabled" if self.config.refresh.auto_enabled else "Disabled",
            "api_configured": "Yes" if self.validate_api_credentials() else "No",
            "route": f"{self.config.stations.from_name} → {self.config.stations.to_name}",
        }

        if self.config.weather:
            weather_summary = self.config.weather.to_summary_dict()
            summary.update(
                {
                    "weather_enabled": weather_summary["enabled"],
                    "weather_location": weather_summary["location"],
                    "weather_refresh": weather_summary["refresh_interval"],
                    "weather_provider": weather_summary["api_provider"],
                }
            )
        else:
            summary["weather_enabled"] = False

        return summary

    def get_weather_config(self) -> Optional[WeatherConfig]:
        if self.config is None:
            self.load_config()
        return self.config.weather if self.config else None

    def is_weather_enabled(self) -> bool:
        weather_config = self.get_weather_config()
        return weather_config is not None and weather_config.enabled

    def migrate_config_if_needed(self) -> bool:
        if self.config is None:
            return False

        try:
            config_dict = self.config.model_dump()
            weather_dict = config_dict.get("weather")
            if weather_dict:
                if WeatherConfigMigrator.is_migration_needed(weather_dict):
                    config_dict["weather"] = WeatherConfigMigrator.migrate_to_current_version(weather_dict)
                    self.config = ConfigData(**config_dict)
                    self.save_config(self.config)
                    return True
            else:
                config_dict["weather"] = WeatherConfigFactory.create_waterloo_config().model_dump()
                self.config = ConfigData(**config_dict)
                self.save_config(self.config)
                return True
        except Exception as exc:
            logger.error("Configuration migration failed: %s", exc)
        return False


__all__ = [
    "ConfigManager",
    "ConfigData",
    "ConfigurationError",
    "APIConfig",
    "StationConfig",
    "RefreshConfig",
    "DisplayConfig",
    "UIConfig",
]

