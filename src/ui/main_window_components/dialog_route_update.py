"""Helpers for dialog-driven route updates."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def on_dialog_route_updated(*, window, route_data: dict) -> None:
    """Handle route updates from the settings dialog during preference changes."""

    try:
        logger.info("Route updated from settings dialog - triggering immediate refresh")
        window.refresh_requested.emit()

        if route_data and "full_path" in route_data and len(route_data["full_path"]) >= 2:
            from_station = route_data["full_path"][0]
            to_station = route_data["full_path"][-1]
            window.route_changed.emit(from_station, to_station)
            logger.info("Emitted route_changed signal: %s → %s", from_station, to_station)

    except Exception as exc:  # pragma: no cover
        logger.error("Error handling dialog route update: %s", exc)

