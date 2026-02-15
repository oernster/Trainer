"""
Route Calculation Worker

Background worker thread for route calculation to avoid blocking UI.
"""

import logging
from typing import Any, Optional

from PySide6.QtCore import QThread, Signal

logger = logging.getLogger(__name__)


class RouteCalculationWorker(QThread):
    """Background worker thread for route calculation to avoid blocking UI."""
    
    # Signals
    route_calculated = Signal(dict)
    calculation_failed = Signal(str)
    calculation_started = Signal()
    calculation_finished = Signal()
    
    def __init__(self, dialog, from_station, to_station, preferences=None):
        super().__init__()
        self.dialog = dialog
        self.from_station = from_station
        self.to_station = to_station
        self.preferences = preferences or {}
        
    def run(self):
        """Run route calculation in background thread."""
        try:
            self.calculation_started.emit()
            logger.info(f"Background route calculation started: {self.from_station} → {self.to_station}")
            
            # NOTE: This code runs in a background thread. Avoid touching Qt widgets
            # or mutating dialog-owned state from here.
            preferences = (
                self.dialog.dialog_state.get_preferences()
                if getattr(self.dialog, "dialog_state", None)
                else {}
            )

            try:
                # Build a route service instance locally to avoid cross-thread
                # interaction with dialog lazy properties / shared caches.
                from src.core.services.service_factory import ServiceFactory

                route_service = ServiceFactory().get_route_service()
                route_data = self._calculate_route_data(
                    route_service=route_service,
                    preferences=preferences,
                )
                if route_data:
                    self.route_calculated.emit(route_data)
                else:
                    self.calculation_failed.emit("No route found")

            except Exception as e:
                logger.error(f"Route calculation error: {e}")
                self.calculation_failed.emit(str(e))
                
        except Exception as e:
            logger.error(f"Background route calculation failed: {e}")
            self.calculation_failed.emit(str(e))
        finally:
            self.calculation_finished.emit()
    
    def _calculate_route_data(self, *, route_service: Any, preferences: dict) -> Optional[dict]:
        """Calculate full route data using the core route service.

        Returns a dict compatible with the dialog's route display + persistence.
        """
        try:
            # Keep this conservative; UI callers can re-run with a higher limit.
            max_changes = 10
            route_result = route_service.calculate_route(
                self.from_station,
                self.to_station,
                max_changes=max_changes,
                preferences=preferences,
            )
            if not route_result:
                return None

            route_data = self._convert_route_result(
                route_result=route_result,
                from_station=self.from_station,
                to_station=self.to_station,
            )
            logger.info(
                "Route calculated in background: %s → %s (%s changes)",
                self.from_station,
                self.to_station,
                route_data.get("changes"),
            )
            return route_data

        except Exception as e:
            logger.error(f"Error in route data calculation: {e}")
            return None

    @staticmethod
    def _convert_route_result(*, route_result: Any, from_station: str, to_station: str) -> dict:
        """Convert a core Route to the dialog's dict format."""
        interchange_stations: list[str] = []
        if getattr(route_result, "interchange_stations", None):
            interchange_stations = list(route_result.interchange_stations)
        elif getattr(route_result, "segments", None):
            segments = list(route_result.segments)
            for segment in segments[:-1]:
                to_name = getattr(segment, "to_station", None)
                if to_name:
                    interchange_stations.append(to_name)

        full_path = list(getattr(route_result, "full_path", []) or [])

        return {
            "from_station": from_station,
            "to_station": to_station,
            "via_stations": [],
            "journey_time": getattr(route_result, "total_journey_time_minutes", 0) or 0,
            "distance": getattr(route_result, "total_distance_km", 0.0) or 0.0,
            "changes": getattr(route_result, "changes_required", 0) or 0,
            "operators": getattr(route_result, "lines_used", None) or [],
            "segments": getattr(route_result, "segments", None) or [],
            "route_type": getattr(route_result, "route_type", None) or "calculated",
            "is_direct": getattr(route_result, "is_direct", False) or False,
            "interchange_stations": interchange_stations,
            "full_path": full_path,
            "calculated_at": "background_thread",
        }
