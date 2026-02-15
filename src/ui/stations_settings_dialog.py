"""
Refactored Train Settings Dialog for the Train Times application.

This dialog provides a user interface for configuring train route settings,
using a modular component-based architecture for better maintainability.
"""

import logging
from typing import Optional, Dict, Any
from PySide6.QtWidgets import QDialog
from PySide6.QtCore import Signal

# Import components
from .components.station_selection_widget import StationSelectionWidget
from .components.route_action_buttons import RouteActionButtons
from .components.route_details_widget import RouteDetailsWidget
from .components.preferences_widget import PreferencesWidget

# Import handlers
from .handlers.settings_handler import SettingsHandler
from .handlers.route_calculation_handler import RouteCalculationHandler

# Import state management
from .state.dialog_state import DialogState

# Import refactored components
from .stations_dialog_components.dialog_setup_manager import DialogSetupManager
from .stations_dialog_components.ui_layout_manager import UILayoutManager
from .stations_dialog_components.station_data_manager import StationDataManager
from .stations_dialog_components.event_handler import EventHandler
from .stations_dialog_components.background_route_calculator import BackgroundRouteCalculator

logger = logging.getLogger(__name__)


class StationsSettingsDialog(QDialog):
    """
    Refactored Train Settings Dialog.
    
    This dialog provides a user interface for configuring train route settings
    using a modular component-based architecture.
    """
    
    # Signals - keep both for compatibility
    settings_saved = Signal()  # Original signal expected by main window
    settings_changed = Signal()
    route_updated = Signal(dict)
    
    def __init__(
        self,
        parent=None,
        station_database=None,
        config_manager=None,
        theme_manager=None,
        *,
        station_service=None,
        route_service=None,
    ):
        """
        Initialize the train settings dialog.
        
        Args:
            parent: Parent widget
            station_database: Station database manager (legacy)
            config_manager: Configuration manager
            theme_manager: Theme manager
        """
        super().__init__(parent)
        
        # Store references
        self.parent_window = parent
        self.station_database = station_database  # Keep for backward compatibility
        self.config_manager = config_manager
        self.theme_manager = theme_manager
        
        # Routing services are injected by bootstrap/UI composition.
        # Phase 2 boundary: this dialog must not construct services.
        self._station_service = station_service
        self._route_service = route_service
        
        # Initialize state management
        self.dialog_state = DialogState(self)
        
        # Initialize handlers
        self.settings_handler = SettingsHandler(
            self, config_manager, self.station_service, self.route_service
        )
        self.route_calculation_handler = RouteCalculationHandler(
            self, self.station_service, self.route_service
        )
        
        # UI components
        self.tab_widget = None
        self.station_selection_widget = None
        self.route_action_buttons = None
        self.route_details_widget = None
        self.preferences_widget = None
        self.status_label = None
        self.save_button = None
        self.cancel_button = None
        
        # Performance optimization components
        self.station_data_manager = None
        self.cache_manager = None
        self._route_worker = None
        
        # Initialize component managers
        self.dialog_setup_manager = DialogSetupManager(self)
        self.ui_layout_manager = UILayoutManager(self)
        self.station_data_manager = StationDataManager(self)
        self.event_handler = EventHandler(self)
        self.background_route_calculator = BackgroundRouteCalculator(self)
        
        # Initialize the dialog with immediate UI responsiveness
        self._initialize_dialog()
        
        logger.info("StationsSettingsDialog initialized with immediate UI responsiveness")
    
    def _initialize_dialog(self):
        """Initialize the dialog and its components."""
        # Create UI components
        self._create_ui_components()
        
        # Set up dialog properties
        self.dialog_setup_manager.setup_dialog()
        
        # Set up UI layout
        self.ui_layout_manager.setup_ui()
        
        # Connect signals
        self.event_handler.connect_signals()
        
        # Apply theme
        self.dialog_setup_manager.apply_theme(self.theme_manager)
        
        # CRITICAL: Enable station fields immediately and load config values
        self._setup_immediate_ui_responsiveness()
        
        # Defer heavy operations to background using QTimer
        from PySide6.QtCore import QTimer
        QTimer.singleShot(0, self._setup_deferred_initialization)
    
    def _create_ui_components(self):
        """Create UI components."""
        # Create station selection widget
        self.station_selection_widget = StationSelectionWidget(self, self.theme_manager)
        
        # Create route action buttons
        self.route_action_buttons = RouteActionButtons(self, self.theme_manager)
        
        # Create route details widget
        self.route_details_widget = RouteDetailsWidget(self, self.theme_manager)
        
        # Create preferences widget
        self.preferences_widget = PreferencesWidget(self, self.theme_manager)
    
    def _setup_immediate_ui_responsiveness(self):
        """Set up immediate UI responsiveness - make fields editable instantly."""
        # Load essential stations immediately (very fast)
        from src.services.routing.essential_station_cache import get_essential_stations
        essential_stations = get_essential_stations()
        
        if essential_stations and self.station_selection_widget:
            # Populate the combo boxes immediately
            self.station_selection_widget.populate_stations(essential_stations)
            logger.info(f"Essential stations populated immediately: {len(essential_stations)} stations")
        
        # Enable fields immediately
        self._enable_station_fields_immediately()
        
        # Load and apply config values immediately (very fast)
        self._load_config_values_immediately()
        
        # Set status to ready
        self._update_status("Ready")
    
    def _load_config_values_immediately(self):
        """Load config values immediately without heavy operations."""
        try:
            if not self.config_manager:
                return
            
            # Load config directly (very fast)
            config = self.config_manager.load_config()
            if not hasattr(config, 'stations'):
                return
            
            # Get station values
            from_name = getattr(config.stations, 'from_name', '')
            to_name = getattr(config.stations, 'to_name', '')
            departure_time = getattr(config.stations, 'departure_time', '08:00')
            
            # Apply values immediately
            if from_name and self.station_selection_widget:
                self.station_selection_widget.set_from_station(from_name)
                logger.info(f"Set FROM station immediately: {from_name}")
            
            if to_name and self.station_selection_widget:
                self.station_selection_widget.set_to_station(to_name)
                logger.info(f"Set TO station immediately: {to_name}")
            
            if self.route_details_widget:
                self.route_details_widget.set_departure_time(departure_time)
            
            logger.info("Config values loaded immediately")
            
        except Exception as e:
            logger.error(f"Error loading config values immediately: {e}")
    
    def _setup_deferred_initialization(self):
        """Set up heavy operations in the background after UI is responsive."""
        try:
            logger.info("Starting deferred initialization...")
            
            # Set up optimized loading system (background)
            from src.cache.station_cache_manager import get_station_cache_manager
            self.cache_manager = get_station_cache_manager()
            
            # Start background station loading for enhanced autocomplete
            # IMPORTANT: do not require a data_repository here; `StationService` already
            # holds it, and the worker only needs the service.
            if self.station_service:
                from src.ui.workers.station_data_worker import StationDataManager as WorkerManager
                self.worker_manager = WorkerManager(self)

                # Hook worker signals to update the UI with the full station list.
                self.worker_manager.full_stations_ready.connect(
                    self._on_full_stations_ready
                )
                self.worker_manager.loading_progress.connect(
                    lambda message, pct: self._update_status(f"{message} ({pct}%)")
                )
                self.worker_manager.loading_error.connect(
                    lambda error: self._update_status(f"Station loading error: {error}")
                )

                self.worker_manager.start_loading(self.station_service)
                logger.info("Background station loading started")
            
            # Auto-trigger route calculation if both stations are set (deferred with delay)
            # Use a longer delay to ensure stations are properly set
            from PySide6.QtCore import QTimer
            QTimer.singleShot(500, self.background_route_calculator.auto_calculate_route_deferred)
            
            # Update status
            self._update_status("Ready - enhanced features loading...")
            
            logger.info("Deferred initialization completed")
            
        except Exception as e:
            logger.error(f"Error in deferred initialization: {e}")

    def _on_full_stations_ready(self, stations: list[str]) -> None:
        """Update the station selection widget once the full station list is loaded."""
        try:
            if not stations:
                return

            if self.station_selection_widget:
                self.station_selection_widget.populate_stations(stations)

            self._update_status(f"Ready ({len(stations)} stations loaded)")
            logger.info("Station autocomplete upgraded to full dataset")

        except Exception as e:
            logger.error(f"Error applying full station list: {e}")
    
    @property
    def station_service(self):
        """Station service injected by bootstrap."""
        return self._station_service
    
    @property
    def route_service(self):
        """Route service injected by bootstrap."""
        return self._route_service
    
    def _update_status(self, message: str):
        """Update the status bar message."""
        if self.status_label:
            self.status_label.setText(message)
        logger.debug(f"Status: {message}")
    
    # Public interface methods for compatibility
    def get_current_route(self) -> dict:
        """Get the current route configuration."""
        if not self.station_selection_widget:
            return {}
        
        return {
            'from_station': self.station_selection_widget.get_from_station(),
            'to_station': self.station_selection_widget.get_to_station(),
            'via_stations': [],
            'departure_time': self.dialog_state.get_departure_time(),
            'route_data': self.dialog_state.get_route_data()
        }
    
    def set_route(self, route_config: dict):
        """Set the route configuration."""
        try:
            if 'from_station' in route_config and self.station_selection_widget:
                self.station_selection_widget.set_from_station(route_config['from_station'])
            
            if 'to_station' in route_config and self.station_selection_widget:
                self.station_selection_widget.set_to_station(route_config['to_station'])
            
            if 'departure_time' in route_config and self.route_details_widget:
                self.route_details_widget.set_departure_time(route_config['departure_time'])
            
            if 'route_data' in route_config:
                self.dialog_state.set_route_data(route_config['route_data'])
            
        except Exception as e:
            logger.error(f"Error setting route: {e}")
    
    def closeEvent(self, event):
        """Handle dialog close event."""
        try:
            # Stop background loading if active
            if hasattr(self, 'worker_manager') and self.worker_manager:
                if hasattr(self.worker_manager, 'stop_loading'):
                    self.worker_manager.stop_loading()
            
            # CRASH DETECTION: Check if signals are still being processed
            if hasattr(self, '_signals_processing'):
                # Wait briefly for signals to complete
                from PySide6.QtCore import QTimer
                QTimer.singleShot(100, lambda: event.accept())
                return
            
            # Accept the close event
            event.accept()
            
        except Exception as e:
            event.accept()
    
    # Delegate methods to component managers
    def _find_route(self):
        """Find route between selected stations."""
        self.event_handler._find_route()
    
    def _clear_route(self):
        """Clear the current route."""
        self.event_handler._clear_route()
    
    def _enable_station_fields_immediately(self):
        """Enable station input fields immediately for user interaction."""
        try:
            if self.station_selection_widget:
                # Ensure the station selection widget is enabled
                self.station_selection_widget.setEnabled(True)
                
                # Ensure individual combo boxes are enabled and editable
                if hasattr(self.station_selection_widget, 'from_station_combo') and self.station_selection_widget.from_station_combo:
                    combo = self.station_selection_widget.from_station_combo
                    combo.setEnabled(True)
                    combo.setEditable(True)
                    
                    # Ensure the line edit is enabled and focusable
                    line_edit = combo.lineEdit()
                    if line_edit:
                        line_edit.setEnabled(True)
                        line_edit.setReadOnly(False)
                        from PySide6.QtCore import Qt
                        line_edit.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
                
                if hasattr(self.station_selection_widget, 'to_station_combo') and self.station_selection_widget.to_station_combo:
                    combo = self.station_selection_widget.to_station_combo
                    combo.setEnabled(True)
                    combo.setEditable(True)
                    
                    # Ensure the line edit is enabled and focusable
                    line_edit = combo.lineEdit()
                    if line_edit:
                        line_edit.setEnabled(True)
                        line_edit.setReadOnly(False)
                        from PySide6.QtCore import Qt
                        line_edit.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
                
                # Enable the swap button
                if hasattr(self.station_selection_widget, 'swap_button') and self.station_selection_widget.swap_button:
                    self.station_selection_widget.swap_button.setEnabled(True)
                
                logger.info("Station input fields enabled immediately for user interaction")
            
        except Exception as e:
            logger.error(f"Error enabling station fields immediately: {e}")
