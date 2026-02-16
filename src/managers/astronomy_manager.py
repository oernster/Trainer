"""
Astronomy manager for the Trainer application.
Author: Oliver Ernster

This module provides business logic for astronomy data management,
following solid Object-Oriented design principles with proper
abstraction, error handling, and integration with the UI layer.

Now API-free - generates static astronomy events without requiring NASA API.
"""

import asyncio
import logging
from datetime import datetime, timedelta, tzinfo
from typing import Optional, Dict, Any, List
from PySide6.QtCore import QObject, Signal, QTimer

from ..models.astronomy_data import (
    AstronomyForecastData,
    AstronomyEvent,
    AstronomyEventType,
    AstronomyData,
    Location,
    AstronomyDataValidator,
)
from ..managers.astronomy_config import AstronomyConfig
from ..models.astronomy_data import MoonPhase
from ..services.moon_phase_service import HybridMoonPhaseService

from .astronomy_manager_helpers import (
    anchor_dt_for_day,
    calculate_moon_illumination_for_moment,
    calculate_moon_phase_for_moment,
    generate_static_astronomy_events,
    get_config_timezone,
)

logger = logging.getLogger(__name__)

class AstronomyManager(QObject):
    """
    Business logic manager for astronomy data.

    Follows Single Responsibility Principle - only responsible for
    astronomy data management and coordination with the UI layer.
    Implements Observer pattern through Qt signals for UI updates.
    
    Now API-free - generates static astronomy events without requiring NASA API.
    """

    # Qt Signals for observer pattern
    astronomy_updated = Signal(AstronomyForecastData)
    astronomy_error = Signal(str)
    loading_state_changed = Signal(bool)
    cache_status_changed = Signal(dict)

    def __init__(self, config: AstronomyConfig, *, moon_phase_service: HybridMoonPhaseService):
        """
        Initialize astronomy manager.

        Args:
            config: Astronomy configuration
        """
        super().__init__()
        self._config = config
        self._validator = AstronomyDataValidator()
        self._last_update_time: Optional[datetime] = None
        self._current_forecast: Optional[AstronomyForecastData] = None
        self._is_loading = False

        # Phase 2 boundary: injected dependency (no internal construction)
        self._moon_phase_service = moon_phase_service

        # Auto-refresh timer
        self._refresh_timer = QTimer()
        self._refresh_timer.timeout.connect(self._auto_refresh)

        logger.debug(f"AstronomyManager initialized (enabled: {config.enabled}, hybrid moon phase service)")

    def _generate_static_astronomy_events(self) -> List[AstronomyEvent]:
        """Generate static astronomy events for demonstration."""
        return generate_static_astronomy_events(now=datetime.now())

    async def refresh_astronomy(
        self, force_refresh: bool = False
    ) -> Optional[AstronomyForecastData]:
        """
        Refresh astronomy data (now generates static events).

        Args:
            force_refresh: Force refresh even if cache is valid

        Returns:
            AstronomyForecastData: Updated astronomy forecast or None on error
        """
        if not self._config.enabled:
            logger.warning("Astronomy refresh requested but astronomy is disabled")
            return None

        # Check if we should skip refresh (unless forced)
        if not force_refresh and self._should_skip_refresh():
            
            return self._current_forecast

        self._set_loading_state(True)

        try:
            # Create location from config
            location = Location(
                name=self._config.location_name,
                latitude=self._config.location_latitude,
                longitude=self._config.location_longitude,
                timezone=self._config.timezone,
            )

            # Generate static astronomy events
            events = self._generate_static_astronomy_events()

            # Create daily astronomy data from events
            daily_astronomy: list[AstronomyData] = []
            events_by_date: dict = {}
            
            # Group events by date
            for event in events:
                event_date = event.start_time.date()
                if event_date not in events_by_date:
                    events_by_date[event_date] = []
                events_by_date[event_date].append(event)
            
            # Create AstronomyData for each date with proper moon phases.
            # The UI wants the phase "tonight" for each day (22:00 local time).
            tz = get_config_timezone(config=self._config)

            for event_date, date_events in sorted(events_by_date.items()):
                anchor_dt = anchor_dt_for_day(event_date=event_date, tz=tz)

                moon_phase = calculate_moon_phase_for_moment(
                    moon_phase_service=self._moon_phase_service,
                    target_dt=anchor_dt,
                )
                moon_illumination = calculate_moon_illumination_for_moment(
                    moon_phase_service=self._moon_phase_service,
                    target_dt=anchor_dt,
                )
                
                daily_data = AstronomyData(
                    date=event_date,
                    events=date_events,
                    primary_event=date_events[0] if date_events else None,
                    moon_phase=moon_phase,
                    moon_illumination=moon_illumination,
                )
                daily_astronomy.append(daily_data)

            # Create forecast data
            forecast_data = AstronomyForecastData(
                location=location,
                daily_astronomy=daily_astronomy,
                last_updated=datetime.now(),
                data_source="Static Generator + Hybrid Moon Phase API"
            )

            # Validate data
            if not self._validator.validate_astronomy_forecast(forecast_data):
                raise ValueError("Invalid astronomy data generated")

            # Update internal state
            self._current_forecast = forecast_data
            self._last_update_time = datetime.now()

            # Emit signals
            self.astronomy_updated.emit(forecast_data)
            self._emit_cache_status()

            logger.info(
                f"Astronomy data generated successfully: {forecast_data.total_events} events"
            )
            return forecast_data

        except Exception as e:
            error_msg = f"Unexpected error generating astronomy data: {e}"
            logger.error(error_msg)
            self.astronomy_error.emit(error_msg)
            return None

        finally:
            self._set_loading_state(False)

    # Backwards-compatible shims expected by some UI wiring.
    def fetch_astronomy_data(self) -> None:
        """Compatibility shim for legacy call sites.

        Schedules an async refresh without blocking the Qt UI thread.
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self.refresh_astronomy())
            else:
                asyncio.run(self.refresh_astronomy())
        except RuntimeError:
            asyncio.run(self.refresh_astronomy())

    def cleanup(self) -> None:
        """Compatibility shim for legacy shutdown call sites."""
        self.shutdown()

    def _should_skip_refresh(self) -> bool:
        """Check if refresh should be skipped based on cache age."""
        if not self._last_update_time or not self._current_forecast:
            return False

        cache_age = datetime.now() - self._last_update_time
        cache_duration = timedelta(seconds=self._config.get_cache_duration_seconds())

        return cache_age < cache_duration

    def _set_loading_state(self, is_loading: bool) -> None:
        """Update loading state and emit signal."""
        if self._is_loading != is_loading:
            self._is_loading = is_loading
            self.loading_state_changed.emit(is_loading)
            logger.debug(f"Astronomy loading state changed: {is_loading}")

    def _emit_cache_status(self) -> None:
        """Emit cache status information."""
        # Hybrid mode - emit cache info including moon phase service status
        cache_info = {
            "manager_last_update": self._last_update_time,
            "has_current_forecast": self._current_forecast is not None,
            "cache_type": "hybrid_generator",
            "moon_phase_service": "available"
        }
        self.cache_status_changed.emit(cache_info)

    def _auto_refresh(self) -> None:
        """Handle automatic refresh timer."""
        logger.info("Auto-refresh triggered for astronomy data")

        # Run async refresh in event loop
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(self.refresh_astronomy())
        else:
            asyncio.run(self.refresh_astronomy())

    def start_auto_refresh(self) -> None:
        """Start automatic refresh timer."""
        if not self._config.enabled:
            logger.warning("Cannot start auto-refresh: astronomy is disabled")
            return

        # Use a default 1-hour interval for API-free mode
        interval_ms = 3600 * 1000  # 1 hour
        self._refresh_timer.start(interval_ms)
        logger.info(
            f"Astronomy auto-refresh started (interval: {interval_ms/1000:.0f}s)"
        )

    def stop_auto_refresh(self) -> None:
        """Stop automatic refresh timer."""
        self._refresh_timer.stop()
        logger.debug("Astronomy auto-refresh stopped")

    def is_auto_refresh_active(self) -> bool:
        """Check if auto-refresh is currently active."""
        return self._refresh_timer.isActive()

    def get_current_forecast(self) -> Optional[AstronomyForecastData]:
        """Get the current astronomy forecast."""
        return self._current_forecast

    def get_last_update_time(self) -> Optional[datetime]:
        """Get the timestamp of the last successful update."""
        return self._last_update_time

    def is_loading(self) -> bool:
        """Check if astronomy data is currently being loaded."""
        return self._is_loading

    def is_data_stale(self) -> bool:
        """Check if current data is considered stale."""
        if not self._current_forecast:
            return True
        return self._current_forecast.is_stale

    def get_cache_info(self) -> Dict[str, Any]:
        """Get comprehensive cache information."""
        info = {
            "enabled": self._config.enabled,
            "has_api_manager": True,  # Hybrid moon phase service available
            "has_current_forecast": self._current_forecast is not None,
            "last_update_time": self._last_update_time,
            "is_loading": self._is_loading,
            "auto_refresh_active": self.is_auto_refresh_active(),
            "data_stale": self.is_data_stale(),
            "cache_type": "hybrid_generator",
            "moon_phase_service": "hybrid_api"
        }

        return info

    def clear_cache(self) -> None:
        """Clear all cached astronomy data."""
        # API-free mode - just clear local data
        self._current_forecast = None
        self._last_update_time = None

        self._emit_cache_status()
        logger.debug("Astronomy cache cleared")

    def update_config(self, new_config: AstronomyConfig) -> None:
        """
        Update astronomy configuration.

        Args:
            new_config: New astronomy configuration
        """
        old_enabled = self._config.enabled
        self._config = new_config

        # Handle enable/disable state changes
        if not old_enabled and new_config.enabled:
            # Astronomy was enabled
            logger.info("Astronomy enabled (API-free mode)")

        elif old_enabled and not new_config.enabled:
            # Astronomy was disabled
            self.stop_auto_refresh()
            self.clear_cache()
            logger.info("Astronomy disabled")

        # Update auto-refresh if needed
        if new_config.enabled and self.is_auto_refresh_active():
            self.stop_auto_refresh()
            self.start_auto_refresh()

        logger.info("Astronomy configuration updated")

    def get_status_summary(self) -> str:
        """Get a human-readable status summary."""
        if not self._config.enabled:
            return "Astronomy disabled"

        if self._is_loading:
            return "Loading astronomy data..."

        if not self._current_forecast:
            return "No astronomy data available"

        if self.is_data_stale():
            return (
                f"Astronomy data stale ({self._current_forecast.total_events} events)"
            )

        return f"Astronomy data current ({self._current_forecast.total_events} events)"

    def get_enabled_services(self) -> list[str]:
        """Get list of enabled astronomy services."""
        # Return services including hybrid moon phase service
        return ["Static Generator", "Hybrid Moon Phase API", "Astronomy Links"]
    
    def get_current_moon_phase(self) -> Optional[Dict[str, Any]]:
        """Get current moon phase data using the hybrid service."""
        if not self._config.enabled:
            return None
            
        try:
            tz = get_config_timezone(config=self._config)
            now_local = datetime.now(tz)
            moon_data = self._moon_phase_service.get_moon_phase_sync(now_local)
            return {
                'phase_name': moon_data.phase.value.replace("_", " ").title(),
                'illumination_percent': moon_data.illumination * 100,  # Convert to percentage
                'phase': moon_data.phase.value,
                'source': moon_data.source.value,
                'confidence': moon_data.confidence,
                'timestamp': moon_data.timestamp.isoformat()
            }
        except Exception as e:
            logger.warning(f"Failed to get current moon phase: {e}")
            return None

    def shutdown(self) -> None:
        """Shutdown astronomy manager and cleanup resources."""
        logger.debug("Shutting down astronomy manager...")

        # Stop auto-refresh
        self.stop_auto_refresh()

        # Clear data (API-free mode - no API manager to shutdown)
        self._current_forecast = None
        self._last_update_time = None

        logger.debug("Astronomy manager shutdown complete")

    def _get_config_timezone(self) -> tzinfo:
        """Get timezone for astronomy calculations.

        Falls back to UTC if the configured timezone is missing/invalid.
        """
        return get_config_timezone(config=self._config)

    def _calculate_moon_phase_for_moment(self, target_dt: datetime) -> MoonPhase:
        """Calculate moon phase for a specific moment (timezone-aware datetime)."""
        return calculate_moon_phase_for_moment(
            moon_phase_service=self._moon_phase_service,
            target_dt=target_dt,
        )

    def _calculate_moon_illumination_for_moment(self, target_dt: datetime) -> float:
        """Calculate moon illumination for a specific moment (timezone-aware datetime)."""
        return calculate_moon_illumination_for_moment(
            moon_phase_service=self._moon_phase_service,
            target_dt=target_dt,
        )

# Backwards-compatible re-export
from .astronomy_manager_factory import AstronomyManagerFactory  # noqa: E402
