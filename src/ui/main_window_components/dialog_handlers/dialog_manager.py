"""
Dialog manager for the main window.

This module provides a class for managing the creation and display
of various dialogs, extracted from the MainWindow class.
"""

import logging
from typing import Optional, Any, Callable, Union

from PySide6.QtWidgets import QMainWindow, QMessageBox

logger = logging.getLogger(__name__)


class DialogManager:
    """
    Manager for dialogs in the main window.
    
    Handles creation and display of various dialogs, including settings dialogs,
    train details, route display, and message boxes.
    """
    
    def __init__(self, main_window: QMainWindow, theme_manager):
        """
        Initialize dialog manager.
        
        Args:
            main_window: Parent main window
            theme_manager: Theme manager for styling dialogs
        """
        self.main_window = main_window
        self.theme_manager = theme_manager
    
    def show_stations_settings_dialog(self, config_manager, train_manager=None) -> Any:
        """
        Show stations settings dialog.
        
        Args:
            config_manager: Configuration manager for accessing config
            train_manager: Train manager for accessing station database
        """
        try:
            # Get station database from train manager if available
            station_db = getattr(train_manager, 'station_database', None) if train_manager else None
            
            from ...stations_settings_dialog import StationsSettingsDialog

            # Phase 2 boundary: UI dialogs must not construct routing services.
            station_service = getattr(train_manager, "route_calculation_service", None)
            station_service = getattr(station_service, "station_service", None)
            route_service = getattr(train_manager, "route_calculation_service", None)
            route_service = getattr(route_service, "route_service", None)

            dialog = StationsSettingsDialog(
                self.main_window,
                station_db,
                config_manager,
                self.theme_manager,
                station_service=station_service,
                route_service=route_service,
            )
            
            # Return the dialog for the caller to connect signals
            return dialog
        except Exception as e:
            logger.error(f"Failed to show stations settings dialog: {e}")
            self.show_error_message("Settings Error", f"Failed to open stations settings: {e}")
            return None
    
    def show_astronomy_settings_dialog(self, config_manager) -> Any:
        """
        Show astronomy settings dialog.
        
        Args:
            config_manager: Configuration manager for accessing config
        """
        try:
            from ...astronomy_settings_dialog import AstronomySettingsDialog
            dialog = AstronomySettingsDialog(config_manager, self.main_window, self.theme_manager)
            
            # Return the dialog for the caller to connect signals
            return dialog
        except Exception as e:
            logger.error(f"Failed to show astronomy settings dialog: {e}")
            self.show_error_message("Settings Error", f"Failed to open astronomy settings: {e}")
            return None
    
    def show_train_details(self, train_data) -> None:
        """
        Show detailed train information dialog.
        
        Args:
            train_data: Train data to display in detail
        """
        try:
            from ...train_detail_dialog import TrainDetailDialog
            dialog = TrainDetailDialog(
                train_data,
                self.theme_manager.current_theme,
                self.main_window
            )
            dialog.exec()
            logger.info(f"Showed train details for {train_data.destination}")
        except Exception as e:
            logger.error(f"Failed to show train details: {e}")
            self.show_error_message("Train Details Error", f"Failed to show train details: {e}")
    
    def show_route_details(self, train_data, train_manager=None) -> None:
        """
        Show route display dialog with all calling points.
        
        Args:
            train_data: Train data to display route for
            train_manager: Train manager for accessing route data
        """
        try:
            from ...widgets.route_display_dialog import RouteDisplayDialog
            dialog = RouteDisplayDialog(
                train_data,
                self.theme_manager.current_theme,
                self.main_window,
                train_manager
            )
            dialog.exec()
            logger.info(f"Showed route details for {train_data.destination}")
        except Exception as e:
            logger.error(f"Failed to show route details: {e}")
            self.show_error_message("Route Details Error", f"Failed to show route details: {e}")
    
    def show_error_message(self, title: str, message: str) -> None:
        """
        Show error message dialog.
        
        Args:
            title: Dialog title
            message: Error message
        """
        msg_box = QMessageBox(self.main_window)
        msg_box.setIcon(QMessageBox.Icon.Critical)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.exec()
    
    def show_info_message(self, title: str, message: str) -> None:
        """
        Show information message dialog.
        
        Args:
            title: Dialog title
            message: Information message
        """
        msg_box = QMessageBox(self.main_window)
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.exec()
    
    def show_about_dialog(self, config_path: Optional[str] = None) -> None:
        """
        Show about dialog using centralized version system.
        
        Args:
            config_path: Optional path to configuration file to display
        """
        from version import get_about_text
        from src.ui.widgets.about_dialog import AboutDialog

        about_html = get_about_text()
        dialog = AboutDialog(
            parent=self.main_window,
            about_html=about_html,
            config_path=config_path,
            title="About",
        )
        dialog.exec()
    
    def show_astronomy_enabled_message(self) -> None:
        """Show the astronomy enabled success message."""
        msg_box = QMessageBox(self.main_window)
        msg_box.setWindowTitle("Astronomy Enabled")
        msg_box.setText("Astronomy integration has been enabled! "
                       "You'll now see space events and astronomical data in your app.")
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.setStyleSheet("""
            QMessageBox {
                background-color: #ffffff;
                color: #1976d2;
            }
            QMessageBox QLabel {
                color: #1976d2;
                background-color: #ffffff;
            }
            QMessageBox QPushButton {
                background-color: #f0f0f0;
                border: 1px solid #cccccc;
                border-radius: 4px;
                padding: 6px 12px;
                color: #1976d2;
                min-width: 80px;
            }
            QMessageBox QPushButton:hover {
                background-color: #e0e0e0;
                border-color: #1976d2;
            }
            QMessageBox QPushButton:pressed {
                background-color: #1976d2;
                color: #ffffff;
            }
        """)
        msg_box.exec()
