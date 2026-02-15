"""Helper functions for [`CombinedForecastManager`](src/managers/combined_forecast_manager.py:27).

These helpers are extracted to keep each module under the <= 400 non-blank LOC
gate while retaining a stable public API.
"""

from __future__ import annotations

from typing import Any


def build_cache_info(manager: Any) -> dict[str, Any]:
    """Build a cache-info dict for UI diagnostics."""

    info: dict[str, Any] = {
        "has_current_forecast": manager._current_forecast is not None,
        "last_update_time": manager._last_update_time,
        "is_loading": manager._is_loading,
        "auto_refresh_active": manager.is_auto_refresh_active(),
        "has_weather_manager": manager._weather_manager is not None,
        "has_astronomy_manager": manager._astronomy_manager is not None,
    }

    if manager._current_forecast:
        info.update(
            {
                "forecast_status": manager._current_forecast.status.value,
                "forecast_days": manager._current_forecast.forecast_days,
                "total_astronomy_events": manager._current_forecast.total_astronomy_events,
            }
        )

    return info


def clear_cache(manager: Any) -> None:
    """Clear combined forecast cache and (optionally) underlying manager caches."""

    manager._current_forecast = None
    manager._last_update_time = None

    # Also clear individual manager caches if they support it
    if manager._weather_manager:
        clear_cache_method = getattr(manager._weather_manager, "clear_cache", None)
        if clear_cache_method:
            clear_cache_method()

    if manager._astronomy_manager:
        clear_cache_method = getattr(manager._astronomy_manager, "clear_cache", None)
        if clear_cache_method:
            clear_cache_method()


def shutdown(manager: Any) -> None:
    """Shutdown the manager and any owned child managers."""

    # Stop auto-refresh
    manager.stop_auto_refresh()

    # Shutdown individual managers
    if manager._weather_manager:
        manager._weather_manager.shutdown()

    if manager._astronomy_manager:
        manager._astronomy_manager.shutdown()

    # Clear data
    manager._current_forecast = None
    manager._last_update_time = None

