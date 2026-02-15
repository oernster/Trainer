"""Weather/Astronomy update helpers after configuration changes."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def update_weather_system(*, window) -> None:
    """Update weather system after configuration change."""

    if not window.config or not hasattr(window.config, "weather") or not window.config.weather:
        return

    if window.config.weather.enabled and not window.weather_manager:
        window.setup_weather_system()
        return

    if not window.weather_manager:
        return

    window.weather_manager.update_config(window.config.weather)

    widgets = window.ui_layout_manager.get_widgets()
    weather_widget = widgets.get("weather_widget")
    if weather_widget:
        weather_widget.update_config(window.config.weather)


def update_astronomy_system(*, window) -> None:
    """Update astronomy system after configuration change."""

    if not window.config or not hasattr(window.config, "astronomy") or not window.config.astronomy:
        return

    needs_reinit = False
    needs_data_fetch = False

    if window.config.astronomy.enabled:
        if not window.astronomy_manager:
            needs_reinit = True
            needs_data_fetch = True
        else:
            window.astronomy_manager.update_config(window.config.astronomy)

    if needs_reinit:
        window.setup_astronomy_system()
        logger.info("Astronomy system reinitialized with new API key")

    if needs_data_fetch and window.astronomy_manager:
        logger.info("Emitting astronomy manager ready signal to trigger data fetch")
        window.astronomy_manager_ready.emit()

    widgets = window.ui_layout_manager.get_widgets()
    astronomy_widget = widgets.get("astronomy_widget")
    if astronomy_widget:
        logger.info(
            "Updating astronomy widget with config: enabled=%s",
            window.config.astronomy.enabled,
        )
        astronomy_widget.update_config(window.config.astronomy)

