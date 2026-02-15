"""
Background Route Calculator

Handles background route calculation to avoid blocking the UI.
"""

import logging
from PySide6.QtCore import QObject, Signal

from .route_calculation_worker import RouteCalculationWorker

logger = logging.getLogger(__name__)


class BackgroundRouteCalculator(QObject):
    """Handles background route calculation to avoid blocking the UI."""
    
    def __init__(self, dialog):
        """
        Initialize the background route calculator.
        
        Args:
            dialog: The parent dialog
        """
        super().__init__()
        self.dialog = dialog
        self._route_worker = None
    
    def start_background_route_calculation(self, from_station, to_station):
        """Start route calculation in background thread."""
        try:
            # Stop any existing route calculation
            if self._route_worker and self._route_worker.isRunning():
                self._route_worker.terminate()
                self._route_worker.wait()
            
            # Create and start background worker
            self._route_worker = RouteCalculationWorker(self.dialog, from_station, to_station)
            
            # Connect worker signals
            self._route_worker.route_calculated.connect(self._on_background_route_calculated)
            self._route_worker.calculation_failed.connect(self._on_background_route_failed)
            self._route_worker.calculation_started.connect(self._on_background_calculation_started)
            self._route_worker.calculation_finished.connect(self._on_background_calculation_finished)
            
            # Start the worker thread
            self._route_worker.start()
            
            logger.info(f"Background route calculation started: {from_station} → {to_station}")
            
        except Exception as e:
            logger.error(f"Error starting background route calculation: {e}")
    
    def _on_background_route_calculated(self, route_data):
        """Handle successful background route calculation."""
        try:
            # Update UI with calculated route (this runs in main thread)
            self.dialog.dialog_state.set_route_data(route_data)
            if self.dialog.route_details_widget:
                self.dialog.route_details_widget.update_route_data(route_data)
            
            # Emit route_updated signal for main window connection
            self.dialog.route_updated.emit(route_data)
            
            # Update main UI with the new route
            if hasattr(self.dialog, 'event_handler'):
                self.dialog.event_handler._update_main_ui_with_route(route_data)
            
            self.dialog._update_status("Route calculated successfully")
            logger.info("Background route calculation completed successfully")
            
        except Exception as e:
            logger.error(f"Error handling background route result: {e}")
    
    def _on_background_route_failed(self, error_message):
        """Handle failed background route calculation."""
        try:
            self.dialog._update_status(f"Route calculation failed: {error_message}")
            logger.warning(f"Background route calculation failed: {error_message}")
            
        except Exception as e:
            logger.error(f"Error handling background route failure: {e}")
    
    def _on_background_calculation_started(self):
        """Handle background calculation start."""
        try:
            self.dialog._update_status("Calculating route in background...")
            logger.info("Background route calculation started")
            
        except Exception as e:
            logger.error(f"Error handling background calculation start: {e}")
    
    def _on_background_calculation_finished(self):
        """Handle background calculation finish."""
        try:
            # Clean up the worker
            if self._route_worker:
                self._route_worker.deleteLater()
                self._route_worker = None
            
            logger.info("Background route calculation finished")
            
        except Exception as e:
            logger.error(f"Error handling background calculation finish: {e}")
    
    def auto_calculate_route_deferred(self):
        """Auto-calculate route in background thread if both stations are set."""
        try:
            logger.info("auto_calculate_route_deferred called")
            
            if not self.dialog.station_selection_widget:
                logger.info("No station_selection_widget - skipping auto route calculation")
                return
            
            from_station = self.dialog.station_selection_widget.get_from_station()
            to_station = self.dialog.station_selection_widget.get_to_station()
            
            logger.info(f"Auto route check - FROM: '{from_station}', TO: '{to_station}'")
            
            if from_station and to_station and from_station != to_station:
                # Start background route calculation - this won't block the UI
                logger.info(f"✅ Auto-triggering background route calculation: {from_station} → {to_station}")
                self.start_background_route_calculation(from_station, to_station)
            else:
                logger.info(f"❌ Skipping auto route calculation - conditions not met")
                logger.info(f"   - from_station valid: {bool(from_station)}")
                logger.info(f"   - to_station valid: {bool(to_station)}")
                logger.info(f"   - stations different: {from_station != to_station if from_station and to_station else 'N/A'}")
            
        except Exception as e:
            logger.error(f"Error in auto route calculation: {e}")
            import traceback
            logger.error(traceback.format_exc())