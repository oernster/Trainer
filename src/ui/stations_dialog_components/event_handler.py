"""
Event Handler

Handles events and signal connections for the stations settings dialog.
"""

import logging
from typing import Dict, Any
from PySide6.QtWidgets import QMessageBox
from PySide6.QtCore import QTimer

logger = logging.getLogger(__name__)


class EventHandler:
    """Handles events and signal connections for the stations settings dialog."""
    
    def __init__(self, dialog):
        """
        Initialize the event handler.
        
        Args:
            dialog: The parent dialog
        """
        self.dialog = dialog
    
    def connect_signals(self):
        """Connect all signals and slots."""
        # Station selection signals
        if self.dialog.station_selection_widget:
            self.dialog.station_selection_widget.from_station_changed.connect(self._on_station_changed)
            self.dialog.station_selection_widget.to_station_changed.connect(self._on_station_changed)
        
        # Route action button signals
        if self.dialog.route_action_buttons:
            self.dialog.route_action_buttons.find_route_clicked.connect(self._find_route)
            self.dialog.route_action_buttons.clear_route_clicked.connect(self._clear_route)
        
        # Route details signals
        if self.dialog.route_details_widget:
            self.dialog.route_details_widget.departure_time_changed.connect(self.dialog.dialog_state.set_departure_time)
        
        # Preferences signals
        if self.dialog.preferences_widget:
            self.dialog.preferences_widget.preferences_changed.connect(self.dialog.dialog_state.set_preferences)
        
        # Route calculation handler signals
        self.dialog.route_calculation_handler.route_calculated.connect(self._on_route_calculated)
        self.dialog.route_calculation_handler.route_calculation_failed.connect(self._on_route_calculation_failed)
        self.dialog.route_calculation_handler.calculation_started.connect(self._on_calculation_started)
        self.dialog.route_calculation_handler.calculation_finished.connect(self._on_calculation_finished)
        
        # Dialog state signals
        self.dialog.dialog_state.route_data_changed.connect(self._on_route_data_changed)
        self.dialog.dialog_state.preferences_changed.connect(self._on_preferences_changed)
        
        # Button signals
        if self.dialog.save_button:
            self.dialog.save_button.clicked.connect(self._save_settings)
        if self.dialog.cancel_button:
            self.dialog.cancel_button.clicked.connect(self.dialog.reject)
    
    def _on_station_changed(self):
        """Handle station selection change."""
        # Clear route data when stations change
        self.dialog.dialog_state.clear_route_data()
        if self.dialog.route_details_widget:
            self.dialog.route_details_widget.clear_route_data()
    
    def _find_route(self):
        """Find route between selected stations."""
        if not self.dialog.station_selection_widget:
            return
        
        from_station = self.dialog.station_selection_widget.get_from_station()
        to_station = self.dialog.station_selection_widget.get_to_station()
        
        # Get current preferences
        preferences = self.dialog.dialog_state.get_preferences()
        
        logger.info(f"Finding route: {from_station} → {to_station} with preferences: {preferences}")
        self.dialog.route_calculation_handler.calculate_route(from_station, to_station, [], preferences=preferences)
    
    def _clear_route(self):
        """Clear the current route."""
        self.dialog.dialog_state.clear_route_data()
        if self.dialog.route_details_widget:
            self.dialog.route_details_widget.clear_route_data()
        self.dialog._update_status("Route cleared")
    
    def _on_route_calculated(self, route_data: Dict[str, Any]):
        """Handle successful route calculation."""
        self.dialog.dialog_state.set_route_data(route_data)
        if self.dialog.route_details_widget:
            self.dialog.route_details_widget.update_route_data(route_data)
        self.dialog._update_status("Route found successfully")
        
        # Emit route_updated signal for main window connection
        self.dialog.route_updated.emit(route_data)
        
        # Immediately update the main UI with the new route
        self._update_main_ui_with_route(route_data)
    
    def _on_route_calculation_failed(self, error_message: str):
        """Handle failed route calculation."""
        QMessageBox.warning(self.dialog, "Route Calculation Failed", error_message)
        self.dialog._update_status(f"Route calculation failed: {error_message}")
        
        # Clear any previous route data to prevent UI inconsistency
        self.dialog.dialog_state.clear_route_data()
        if self.dialog.route_details_widget:
            self.dialog.route_details_widget.clear_route_data()
            
        logger.info(f"Cleared route data after calculation failure: {error_message}")
    
    def _on_calculation_started(self):
        """Handle calculation start."""
        if self.dialog.route_action_buttons:
            self.dialog.route_action_buttons.show_progress('find', 'Finding...')
        self.dialog._update_status("Calculating route...")
    
    def _on_calculation_finished(self):
        """Handle calculation finish."""
        if self.dialog.route_action_buttons:
            self.dialog.route_action_buttons.hide_progress('find')
    
    def _on_route_data_changed(self, route_data: Dict[str, Any]):
        """Handle route data change."""
        if self.dialog.route_details_widget:
            self.dialog.route_details_widget.update_route_data(route_data)
    
    def _on_preferences_changed(self, preferences: Dict[str, Any]):
        """Handle preferences change - automatically recalculate route if stations are set."""
        logger.info(f"Preferences changed: {preferences}")
        
        # Only recalculate if we have both stations set
        if self.dialog.station_selection_widget:
            from_station = self.dialog.station_selection_widget.get_from_station()
            to_station = self.dialog.station_selection_widget.get_to_station()
            
            if from_station and to_station and from_station != to_station:
                logger.info(f"Auto-recalculating route due to preference change: {from_station} → {to_station}")
                self._find_route()
            else:
                logger.debug("Skipping route recalculation - stations not properly set")
    
    def _update_main_ui_with_route(self, route_data: Dict[str, Any]):
        """Update the main UI immediately with the calculated route."""
        try:
            if not self.dialog.station_selection_widget:
                return
            
            from_station = self.dialog.station_selection_widget.get_from_station()
            to_station = self.dialog.station_selection_widget.get_to_station()
            
            if not from_station or not to_station:
                return
            
            # Extract route path from route_data
            route_path = None
            if route_data and 'full_path' in route_data:
                route_path = route_data['full_path']
                logger.info(f"Updating main UI with route path: {' → '.join(route_path)}")
            
            # Update train manager directly
            if (self.dialog.parent_window and
                hasattr(self.dialog.parent_window, 'train_manager') and
                self.dialog.parent_window.train_manager):
                
                train_manager = self.dialog.parent_window.train_manager
                train_manager.set_route(from_station, to_station, route_path)
                
                # Share config_manager for persistence
                if self.dialog.config_manager and hasattr(train_manager.__class__, 'config_manager'):
                    train_manager.__class__.config_manager = self.dialog.config_manager
                
                logger.info(f"Updated main UI train manager with route: {from_station} → {to_station}")
            
            # Emit signals to refresh the main UI
            if self.dialog.parent_window:
                if hasattr(self.dialog.parent_window, 'refresh_requested'):
                    self.dialog.parent_window.refresh_requested.emit()
                    logger.info("Emitted refresh_requested signal to main UI")
                
                if hasattr(self.dialog.parent_window, 'route_changed'):
                    self.dialog.parent_window.route_changed.emit(from_station, to_station)
                    logger.info("Emitted route_changed signal to main UI")
            
        except Exception as e:
            logger.error(f"Error updating main UI with route: {e}")
    
    def _save_settings(self):
        """Save settings and close dialog."""
        try:
            if not self.dialog.station_selection_widget:
                return
            
            from_station = self.dialog.station_selection_widget.get_from_station()
            to_station = self.dialog.station_selection_widget.get_to_station()
            preferences = self.dialog.preferences_widget.get_preferences() if self.dialog.preferences_widget else {}
            departure_time = self.dialog.route_details_widget.get_departure_time() if self.dialog.route_details_widget else "08:00"
            route_data = self.dialog.dialog_state.get_route_data()
            
            # Ensure route_data is complete and has full_path
            if route_data and 'full_path' not in route_data:
                logger.warning("Route data missing full_path - attempting to reconstruct")
                # Try to reconstruct from interchange stations if available
                if 'interchange_stations' in route_data:
                    route_data['full_path'] = [from_station] + route_data['interchange_stations'] + [to_station]
                    logger.info(f"Reconstructed full_path with {len(route_data['full_path'])} stations")
                else:
                    # Create minimal route path with just from and to stations
                    route_data['full_path'] = [from_station, to_station]
                    logger.warning(f"Created minimal route path with just from/to stations: {from_station} → {to_station}")
            
            # Validate and fix route_path if needed
            if route_data and 'full_path' in route_data:
                route_path = route_data['full_path']
                
                # Ensure route_path is a list
                if not isinstance(route_path, list):
                    logger.warning(f"Route path is not a list, converting: {route_path}")
                    try:
                        # Try to convert to list if it's a string or other type
                        if isinstance(route_path, str):
                            route_path = [s.strip() for s in route_path.split(',')]
                        else:
                            route_path = list(route_path)
                    except:
                        # Fallback to minimal path
                        route_path = [from_station, to_station]
                    route_data['full_path'] = route_path
                
                # Ensure route_path has at least from and to stations
                if len(route_path) < 2:
                    logger.warning(f"Route path too short ({len(route_path)}), fixing")
                    if len(route_path) == 1:
                        # Add missing station
                        if route_path[0] == from_station:
                            route_path.append(to_station)
                        else:
                            route_path.insert(0, from_station)
                    else:
                        # Empty path, create minimal path
                        route_path = [from_station, to_station]
                    route_data['full_path'] = route_path
                
                # Ensure first and last stations match from/to
                if route_path[0] != from_station or route_path[-1] != to_station:
                    logger.warning(f"Route path endpoints ({route_path[0]}, {route_path[-1]}) "
                                  f"don't match from/to stations ({from_station}, {to_station})")
                    # Fix the route path
                    route_path[0] = from_station
                    route_path[-1] = to_station
                    route_data['full_path'] = route_path
                
                # Log the validated route path
                logger.info(f"Saving route with {len(route_path)} stations: {' → '.join(route_path)}")
            
            # Save settings with complete route data
            success = self.dialog.settings_handler.save_settings(
                from_station, to_station, preferences, departure_time, route_data
            )
            
            if success:
                # CRASH DETECTION: Check parent window state before signal emission
                if self.dialog.parent_window is None:
                    self.dialog.accept()
                    return
                
                # Emit both signals for compatibility
                self.dialog.settings_changed.emit()
                self.dialog.settings_saved.emit()
                
                # Signal the main window to refresh trains with the new route
                if hasattr(self.dialog.parent_window, 'route_changed'):
                    self.dialog.parent_window.route_changed.emit(from_station, to_station)
                else:
                    logger.debug("Parent window has no route_changed signal")
                
                # Also emit refresh signal if available
                if hasattr(self.dialog.parent_window, 'refresh_requested'):
                    self.dialog.parent_window.refresh_requested.emit()
                else:
                    logger.debug("Parent window has no refresh_requested signal")
                
                # Direct call to train manager if available
                if self.dialog.parent_window is not None and hasattr(self.dialog.parent_window, 'train_manager') and self.dialog.parent_window.train_manager:
                    if from_station and to_station:
                        # Extract the full_path from route_data if available
                        route_path = None
                        if route_data and 'full_path' in route_data:
                            route_path = route_data['full_path']
                            logger.info(f"Passing route path with {len(route_path)} stations to train manager: {' → '.join(route_path)}")
                        
                        # Pass the route_path to the train manager
                        train_manager = self.dialog.parent_window.train_manager
                        train_manager.set_route(from_station, to_station, route_path)
                        
                        # Share config_manager with train_manager for direct access
                        if self.dialog.config_manager and hasattr(train_manager.__class__, 'config_manager'):
                            train_manager.__class__.config_manager = self.dialog.config_manager
                            logger.info("Shared config_manager with train_manager for direct access")
                        
                        # Force config save to ensure persistence
                        if self.dialog.config_manager:
                            # Get the current config to preserve theme
                            config = self.dialog.config_manager.load_config()
                            
                            # Update route information from train_manager
                            if hasattr(train_manager, 'config') and hasattr(config, 'stations'):
                                train_config = train_manager.config
                                if hasattr(train_config, 'stations'):
                                    config.stations = train_config.stations
                                    logger.debug("Updated stations config from train_manager")
                            
                            # Use force_flush if available
                            if hasattr(self.dialog.config_manager, 'save_config') and 'force_flush' in self.dialog.config_manager.save_config.__code__.co_varnames:
                                self.dialog.config_manager.save_config(config, force_flush=True)
                                logger.info("Forced config save with force_flush=True to ensure route persistence")
                            else:
                                self.dialog.config_manager.save_config(config)
                                logger.info("Saved config (force_flush not available)")
                
                self.dialog._update_status("Settings saved successfully")
                self.dialog.accept()
            
        except Exception as e:
            logger.error(f"Error saving settings: {e}")
            self.dialog._update_status(f"Error saving settings: {e}")
    
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
            self._update_main_ui_with_route(route_data)
            
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
            if self.dialog._route_worker:
                self.dialog._route_worker.deleteLater()
                self.dialog._route_worker = None
            
            logger.info("Background route calculation finished")
            
        except Exception as e:
            logger.error(f"Error handling background calculation finish: {e}")