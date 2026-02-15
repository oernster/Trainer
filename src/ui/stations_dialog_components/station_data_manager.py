"""
Station Data Manager

Handles station data loading and management for the stations settings dialog.
"""

import logging
from typing import List, Optional, Dict, Any
from PySide6.QtCore import QTimer, Qt

logger = logging.getLogger(__name__)


class StationDataManager:
    """Handles station data loading and management for the stations settings dialog."""
    
    def __init__(self, dialog):
        """
        Initialize the station data manager.
        
        Args:
            dialog: The parent dialog
        """
        self.dialog = dialog
        self._stations_loaded = False
        self._essential_stations_loaded = False
        self._pending_station_settings = None  # Store settings for restoration after background loading
    
    def populate_station_combos(self):
        """Populate the station combo boxes using real station service."""
        try:
            stations = []
            
            # Try to use the core station service first
            if self.dialog.station_service:
                try:
                    # Use the new method that includes Underground stations for autocomplete
                    stations = self.dialog.station_service.get_all_station_names_with_underground()
                    logger.info(f"Loaded {len(stations)} stations (including Underground) from core service")
                except Exception as e:
                    logger.warning(f"Failed to load from core service with Underground: {e}")
                    # Fallback to regular stations if the new method fails
                    try:
                        all_stations = self.dialog.station_service.get_all_stations()
                        stations = [station.name for station in all_stations]
                        logger.info(f"Loaded {len(stations)} stations from core service (fallback)")
                    except Exception as e2:
                        logger.warning(f"Failed to load from core service fallback: {e2}")
            
            # Fallback to station database if core service fails
            if not stations and self.dialog.station_database:
                try:
                    stations = self.dialog.station_database.get_all_station_names()
                    logger.info(f"Loaded {len(stations)} stations from database fallback")
                except Exception as e:
                    logger.warning(f"Failed to load from database: {e}")
            
            # If we still have no stations, provide some defaults
            if not stations:
                stations = [
                    "London Waterloo", "London Victoria", "London Bridge", "London King's Cross",
                    "London Paddington", "Clapham Junction", "Woking", "Guildford",
                    "Portsmouth Harbour", "Southampton Central", "Brighton", "Reading",
                    "Cambridge", "Fleet", "Farnborough", "Basingstoke"
                ]
                logger.warning("Using default station list")
            
            # Populate station selection widget
            if self.dialog.station_selection_widget:
                self.dialog.station_selection_widget.populate_stations(stations)
            
            logger.debug(f"Populated station combos with {len(stations)} stations")
            
        except Exception as e:
            logger.error(f"Error populating station combos: {e}")
    
    def setup_optimized_loading(self):
        """Set up the optimized station data loading system."""
        try:
            # Initialize cache manager
            from src.cache.station_cache_manager import get_station_cache_manager
            self.dialog.cache_manager = get_station_cache_manager()
            
            # Initialize station data manager
            from src.ui.workers.station_data_worker import StationDataManager as WorkerManager
            self.dialog.station_data_manager = WorkerManager(self.dialog)
            
            # Connect signals for progressive loading
            self.dialog.station_data_manager.essential_stations_ready.connect(self._on_essential_stations_ready)
            self.dialog.station_data_manager.full_stations_ready.connect(self._on_full_stations_ready)
            self.dialog.station_data_manager.underground_stations_ready.connect(self._on_underground_stations_ready)
            self.dialog.station_data_manager.loading_progress.connect(self._on_loading_progress)
            self.dialog.station_data_manager.loading_error.connect(self._on_loading_error)
            
            logger.info("Optimized loading system initialized")
            
        except Exception as e:
            logger.error(f"Failed to setup optimized loading: {e}")
            # Fallback to original loading if optimization fails
            self.dialog.station_data_manager = None
            self.dialog.cache_manager = None
    
    def load_settings_optimized(self):
        """Load settings with optimized station data loading."""
        try:
            # STEP 1: Load essential stations immediately and populate combo boxes
            self._populate_essential_stations_immediately()
            
            # STEP 2: Load settings from configuration (with fallback for config loading issues)
            settings = None
            try:
                settings = self.dialog.settings_handler.load_settings()
            except Exception as e:
                logger.warning(f"Settings handler failed, trying direct config loading: {e}")
                # Fallback: try to load config directly if settings handler fails
                if self.dialog.config_manager:
                    try:
                        config = self.dialog.config_manager.load_config()
                        if hasattr(config, 'stations'):
                            # Use the correct attribute names from the Pydantic model
                            from_station = getattr(config.stations, 'from_name', '') or getattr(config.stations, 'from_code', '')
                            to_station = getattr(config.stations, 'to_name', '') or getattr(config.stations, 'to_code', '')
                            
                            settings = {
                                'from_station': from_station,
                                'to_station': to_station,
                                'departure_time': getattr(config.stations, 'departure_time', '08:00'),
                                'preferences': {}
                            }
                            logger.info(f"Loaded config directly from config manager: FROM='{from_station}', TO='{to_station}'")
                    except Exception as e2:
                        logger.warning(f"Direct config loading also failed: {e2}")
            
            # STEP 3: Store the loaded settings for later restoration after background loading
            self._pending_station_settings = settings
            
            # STEP 4: Apply saved FROM/TO stations immediately (they should work with essential stations)
            if settings and self.dialog.station_selection_widget:
                # Handle both direct station keys and nested stations object
                from_station = ''
                to_station = ''
                
                if 'from_station' in settings:
                    from_station = settings['from_station']
                elif 'stations' in settings and isinstance(settings['stations'], dict):
                    from_station = settings['stations'].get('from_station', '')
                
                if 'to_station' in settings:
                    to_station = settings['to_station']
                elif 'stations' in settings and isinstance(settings['stations'], dict):
                    to_station = settings['stations'].get('to_station', '')
                
                if from_station:
                    # Try to set immediately first
                    try:
                        self.dialog.station_selection_widget.set_from_station(from_station)
                        current_value = self.dialog.station_selection_widget.get_from_station()
                        if current_value == from_station:
                            logger.info(f"Successfully set FROM station immediately: {from_station}")
                        else:
                            # Use retry mechanism if immediate setting failed
                            QTimer.singleShot(50, lambda: self._set_station_with_retry('from', from_station))
                            logger.info(f"Scheduling FROM station retry: {from_station}")
                    except Exception as e:
                        logger.warning(f"Failed to set FROM station immediately: {e}")
                        QTimer.singleShot(50, lambda: self._set_station_with_retry('from', from_station))
                
                if to_station:
                    # Try to set immediately first
                    try:
                        self.dialog.station_selection_widget.set_to_station(to_station)
                        current_value = self.dialog.station_selection_widget.get_to_station()
                        if current_value == to_station:
                            logger.info(f"Successfully set TO station immediately: {to_station}")
                        else:
                            # Use retry mechanism if immediate setting failed
                            QTimer.singleShot(50, lambda: self._set_station_with_retry('to', to_station))
                            logger.info(f"Scheduling TO station retry: {to_station}")
                    except Exception as e:
                        logger.warning(f"Failed to set TO station immediately: {e}")
                        QTimer.singleShot(50, lambda: self._set_station_with_retry('to', to_station))
            
            # STEP 5: Apply other settings to UI components
            if settings:
                if self.dialog.route_details_widget:
                    self.dialog.route_details_widget.set_departure_time(settings.get('departure_time', '08:00'))
                
                if self.dialog.preferences_widget and 'preferences' in settings:
                    self.dialog.preferences_widget.set_preferences(settings['preferences'])
                    if self.dialog.route_details_widget:
                        self.dialog.route_details_widget.set_preferences(settings['preferences'])
                
                # Load route data if available
                if 'route_data' in settings and settings['route_data']:
                    self.dialog.dialog_state.set_route_data(settings['route_data'])
                    if self.dialog.route_details_widget:
                        self.dialog.route_details_widget.update_route_data(settings['route_data'])
                    self.dialog._update_status("Route path loaded from saved settings")
            
            # STEP 6: Start background loading for complete dataset (this enhances autocomplete)
            # The station selection widget will now preserve current selections when repopulated
            self._start_background_station_loading(settings)
            
            # STEP 7: Auto-trigger route calculation if both stations are set
            if settings and self.dialog.station_selection_widget:
                from_station = settings.get('from_station', '')
                to_station = settings.get('to_station', '')
                if from_station and to_station and from_station != to_station:
                    QTimer.singleShot(100, lambda: self.dialog._find_route())
                    logger.info(f"Auto-triggering route calculation for {from_station} → {to_station}")
            
            self.dialog._update_status("Ready - background loading in progress")
            
        except Exception as e:
            logger.error(f"Error in optimized settings loading: {e}")
            # Fallback to original loading
            self.dialog._load_settings()
    
    def _populate_essential_stations_immediately(self):
        """Populate combo boxes with essential stations immediately for instant interaction."""
        try:
            # Load essential stations (this is very fast - <0.001s)
            from src.core.services.essential_station_cache import get_essential_stations
            essential_stations = get_essential_stations()
            
            if essential_stations and self.dialog.station_selection_widget:
                # Populate the combo boxes immediately
                self.dialog.station_selection_widget.populate_stations(essential_stations)
                self._essential_stations_loaded = True
                
                # Ensure fields are enabled and editable
                self._enable_station_fields_immediately()
                
                logger.info(f"Essential stations populated immediately: {len(essential_stations)} stations")
                self.dialog._update_status(f"Ready ({len(essential_stations)} stations loaded)")
                
                return True
            else:
                logger.warning("No essential stations available for immediate population")
                return False
                
        except Exception as e:
            logger.error(f"Error populating essential stations immediately: {e}")
            return False
    
    def _enable_station_fields_immediately(self):
        """Enable station input fields immediately for user interaction."""
        try:
            if self.dialog.station_selection_widget:
                # Ensure the station selection widget is enabled
                self.dialog.station_selection_widget.setEnabled(True)
                
                # Ensure individual combo boxes are enabled and editable
                if hasattr(self.dialog.station_selection_widget, 'from_station_combo') and self.dialog.station_selection_widget.from_station_combo:
                    combo = self.dialog.station_selection_widget.from_station_combo
                    combo.setEnabled(True)
                    combo.setEditable(True)
                    
                    # Ensure the line edit is enabled and focusable
                    line_edit = combo.lineEdit()
                    if line_edit:
                        line_edit.setEnabled(True)
                        line_edit.setReadOnly(False)
                        line_edit.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
                
                if hasattr(self.dialog.station_selection_widget, 'to_station_combo') and self.dialog.station_selection_widget.to_station_combo:
                    combo = self.dialog.station_selection_widget.to_station_combo
                    combo.setEnabled(True)
                    combo.setEditable(True)
                    
                    # Ensure the line edit is enabled and focusable
                    line_edit = combo.lineEdit()
                    if line_edit:
                        line_edit.setEnabled(True)
                        line_edit.setReadOnly(False)
                        line_edit.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
                
                # Enable the swap button
                if hasattr(self.dialog.station_selection_widget, 'swap_button') and self.dialog.station_selection_widget.swap_button:
                    self.dialog.station_selection_widget.swap_button.setEnabled(True)
                
                logger.info("Station input fields enabled immediately for user interaction")
            
        except Exception as e:
            logger.error(f"Error enabling station fields immediately: {e}")
    
    def _start_background_station_loading(self, settings: Optional[dict] = None):
        """Start background loading without blocking UI."""
        try:
            if not self.dialog.station_data_manager:
                logger.warning("Station data manager not available for background loading")
                return
            
            # Start background loading for complete dataset (non-blocking)
            self.dialog.station_data_manager.start_loading(self.dialog.station_service,
                                                   getattr(self.dialog.station_service, 'data_repository', None))
            
            logger.info("Background station loading started (deferred)")
            
        except Exception as e:
            logger.error(f"Error starting deferred background loading: {e}")
    
    def _set_station_with_retry(self, field_type: str, station_name: str, max_retries: int = 3):
        """Set station value with retry logic to handle timing issues."""
        try:
            if not self.dialog.station_selection_widget or not station_name:
                return
            
            success = False
            for attempt in range(max_retries):
                try:
                    if field_type == 'from':
                        self.dialog.station_selection_widget.set_from_station(station_name)
                        # Verify it was set correctly
                        current_value = self.dialog.station_selection_widget.get_from_station()
                        if current_value == station_name:
                            success = True
                            logger.info(f"Successfully set FROM station to: {station_name}")
                            break
                    elif field_type == 'to':
                        self.dialog.station_selection_widget.set_to_station(station_name)
                        # Verify it was set correctly
                        current_value = self.dialog.station_selection_widget.get_to_station()
                        if current_value == station_name:
                            success = True
                            logger.info(f"Successfully set TO station to: {station_name}")
                            break
                    
                    # If we get here, the setting didn't work, wait and retry
                    if attempt < max_retries - 1:
                        logger.warning(f"Attempt {attempt + 1} failed to set {field_type} station to {station_name}, retrying...")
                        QTimer.singleShot(50, lambda: self._set_station_with_retry(field_type, station_name, max_retries - attempt - 1))
                        return
                        
                except Exception as e:
                    logger.warning(f"Attempt {attempt + 1} to set {field_type} station failed: {e}")
                    if attempt < max_retries - 1:
                        QTimer.singleShot(50, lambda: self._set_station_with_retry(field_type, station_name, max_retries - attempt - 1))
                        return
            
            if not success:
                logger.error(f"Failed to set {field_type} station to {station_name} after {max_retries} attempts")
                
        except Exception as e:
            logger.error(f"Error in _set_station_with_retry: {e}")
    
    # Signal handlers for optimized loading
    def _on_essential_stations_ready(self, stations: List[str]):
        """Handle essential stations loading completion."""
        try:
            if not self._stations_loaded:  # Only update if we don't have full data yet
                self._populate_station_combos_with_list(stations)
                self._essential_stations_loaded = True
                self.dialog._update_status(f"Essential stations ready ({len(stations)} stations)")
                logger.info(f"Essential stations ready: {len(stations)} stations")
        except Exception as e:
            logger.error(f"Error handling essential stations: {e}")
    
    def _on_full_stations_ready(self, stations: List[str]):
        """Handle full station data loading completion."""
        try:
            self._populate_station_combos_with_list(stations)
            self._stations_loaded = True
            self.dialog._update_status(f"All stations loaded ({len(stations)} stations)")
            logger.info(f"Full stations ready: {len(stations)} stations")
            
            # Save to cache for next time
            if self.dialog.cache_manager and stations:
                try:
                    data_directory = None
                    # Try to get data directory from various sources
                    if hasattr(self.dialog, 'station_service') and self.dialog.station_service:
                        # Try to access data_repository through the concrete implementation
                        if hasattr(self.dialog.station_service, 'data_repository'):
                            data_repo = getattr(self.dialog.station_service, 'data_repository', None)
                            if data_repo and hasattr(data_repo, 'data_directory'):
                                data_directory = data_repo.data_directory
                    
                    self.dialog.cache_manager.save_stations_to_cache(stations, data_directory)
                    logger.info("Station data cached for future use")
                except Exception as e:
                    logger.warning(f"Failed to cache station data: {e}")
                    
        except Exception as e:
            logger.error(f"Error handling full stations: {e}")
    
    def _on_underground_stations_ready(self, stations: List[str]):
        """Handle underground stations loading completion."""
        try:
            # Underground stations are included in the full dataset
            # This is just for progress indication
            logger.info(f"Underground stations ready: {len(stations)} stations")
        except Exception as e:
            logger.error(f"Error handling underground stations: {e}")
    
    def _on_loading_progress(self, message: str, percentage: int):
        """Handle loading progress updates."""
        try:
            self.dialog._update_status(f"{message} ({percentage}%)")
        except Exception as e:
            logger.error(f"Error handling loading progress: {e}")
    
    def _on_loading_error(self, error_message: str):
        """Handle loading errors."""
        try:
            logger.error(f"Station loading error: {error_message}")
            self.dialog._update_status(f"Loading error: {error_message}")
            
            # Fallback to original loading on error
            if not self._essential_stations_loaded and not self._stations_loaded:
                logger.info("Falling back to original station loading")
                self.populate_station_combos()
                
        except Exception as e:
            logger.error(f"Error handling loading error: {e}")
    
    def _populate_station_combos_with_list(self, stations: List[str]):
        """Populate station combos with a provided list of stations."""
        try:
            if not stations:
                return
            
            # Populate station selection widget
            if self.dialog.station_selection_widget:
                self.dialog.station_selection_widget.populate_stations(stations)
            
            logger.debug(f"Populated station combos with {len(stations)} stations")
            
        except Exception as e:
            logger.error(f"Error populating stations with list: {e}")