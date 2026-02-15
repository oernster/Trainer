"""Settings reload / apply helpers for MainWindow."""

from __future__ import annotations

import logging

from ...managers.config_models import ConfigurationError

logger = logging.getLogger(__name__)


def check_settings_changes_need_refresh(
    *,
    config,
    old_time_window,
    old_train_lookahead,
    old_avoid_walking,
    old_max_walking_distance,
    old_prefer_direct,
    old_max_changes,
) -> bool:
    """Check if settings changes require train data refresh."""

    needs_refresh = False

    if config and hasattr(config, "display") and config.display:
        new_time_window = config.display.time_window_hours
        if old_time_window != new_time_window:
            logger.info(
                "Display time window changed from %s to %s hours",
                old_time_window,
                new_time_window,
            )
            needs_refresh = True

    new_train_lookahead = getattr(config, "train_lookahead_hours", None)
    if old_train_lookahead != new_train_lookahead:
        logger.info(
            "Train look-ahead time changed from %s to %s hours",
            old_train_lookahead,
            new_train_lookahead,
        )
        needs_refresh = True

    new_avoid_walking = getattr(config, "avoid_walking", None)
    if old_avoid_walking != new_avoid_walking:
        logger.info(
            "Avoid walking preference changed from %s to %s",
            old_avoid_walking,
            new_avoid_walking,
        )
        needs_refresh = True

    new_max_walking_distance = getattr(config, "max_walking_distance_km", None)
    if old_max_walking_distance != new_max_walking_distance:
        logger.info(
            "Max walking distance changed from %s to %s km",
            old_max_walking_distance,
            new_max_walking_distance,
        )
        needs_refresh = True

    new_prefer_direct = getattr(config, "prefer_direct", None)
    if old_prefer_direct != new_prefer_direct:
        logger.info(
            "Prefer direct routes changed from %s to %s",
            old_prefer_direct,
            new_prefer_direct,
        )
        needs_refresh = True

    new_max_changes = getattr(config, "max_changes", None)
    if old_max_changes != new_max_changes:
        logger.info(
            "Max changes preference changed from %s to %s",
            old_max_changes,
            new_max_changes,
        )
        needs_refresh = True

    return needs_refresh


def on_settings_saved(*, window) -> None:
    """Handle settings saved event."""

    try:
        old_time_window = None
        old_train_lookahead = None
        old_avoid_walking = None
        old_max_walking_distance = None
        old_prefer_direct = None
        old_max_changes = None

        if window.config:
            if hasattr(window.config, "display"):
                old_time_window = window.config.display.time_window_hours
            old_train_lookahead = getattr(window.config, "train_lookahead_hours", None)
            old_avoid_walking = getattr(window.config, "avoid_walking", None)
            old_max_walking_distance = getattr(window.config, "max_walking_distance_km", None)
            old_prefer_direct = getattr(window.config, "prefer_direct", None)
            old_max_changes = getattr(window.config, "max_changes", None)

        window.config = window.config_manager.load_config()

        if window.config:
            window.theme_manager.set_theme(window.config.display.theme)
            window.config_updated.emit(window.config)

            needs_refresh = check_settings_changes_need_refresh(
                config=window.config,
                old_time_window=old_time_window,
                old_train_lookahead=old_train_lookahead,
                old_avoid_walking=old_avoid_walking,
                old_max_walking_distance=old_max_walking_distance,
                old_prefer_direct=old_prefer_direct,
                old_max_changes=old_max_changes,
            )

            if needs_refresh:
                window.refresh_requested.emit()
                logger.info("Refreshing train data for new preference settings")

            window.route_changed.emit(
                window.config.stations.from_name,
                window.config.stations.to_name,
            )

            via_stations = getattr(window.config.stations, "via_stations", [])
            window.update_route_display(
                window.config.stations.from_name,
                window.config.stations.to_name,
                via_stations,
            )

            window.refresh_requested.emit()
            logger.info("Route changed - refreshing train data for new route")

            if hasattr(window.config, "weather") and window.config.weather:
                window._update_weather_system()

            if hasattr(window.config, "astronomy") and window.config.astronomy:
                window._update_astronomy_system()

        logger.info("Settings reloaded after save")

    except ConfigurationError as exc:
        logger.error("Failed to reload settings: %s", exc)
        window.show_error_message(
            "Configuration Error",
            f"Failed to reload settings: {exc}",
        )

