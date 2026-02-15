"""
Settings Dialog Manager for the main window.

This module handles settings dialogs, configuration management,
and user preference interfaces.
"""

import logging
from typing import Optional, Dict, Any
from PySide6.QtWidgets import QDialog, QMessageBox
from PySide6.QtCore import QObject

logger = logging.getLogger(__name__)


class SettingsDialogManager(QObject):
    """
    Manages settings dialogs and configuration interfaces.
    
    Handles opening settings dialogs, managing user preferences,
    and coordinating configuration changes across the application.
    """
    
    def __init__(self, main_window):
        """
        Initialize the settings dialog manager.
        
        Args:
            main_window: Reference to the main window instance
        """
        super().__init__()
        self.main_window = main_window
        self.ui_layout_manager = None  # Will be set by main window
        self.widget_lifecycle_manager = None  # Will be set by main window
        
        # Track open dialogs
        self._open_dialogs = {}
        
        logger.debug("SettingsDialogManager initialized")
    
    def set_managers(self, ui_layout_manager, widget_lifecycle_manager) -> None:
        """Set references to other managers."""
        self.ui_layout_manager = ui_layout_manager
        self.widget_lifecycle_manager = widget_lifecycle_manager
    
    def show_stations_settings_dialog(self) -> None:
        """Show the stations settings dialog."""
        try:
            # Prevent multiple instances of the same dialog
            if 'stations_settings' in self._open_dialogs:
                existing_dialog = self._open_dialogs['stations_settings']
                if existing_dialog and existing_dialog.isVisible():
                    existing_dialog.raise_()
                    existing_dialog.activateWindow()
                    return
            
            # Import dialog class
            try:
                # Current project layout exposes the dialog at `src.ui.stations_settings_dialog`.
                from src.ui.stations_settings_dialog import StationsSettingsDialog
            except ImportError:
                logger.error("StationsSettingsDialog not found - creating placeholder")
                self._show_placeholder_dialog("Stations Settings", "Station configuration dialog would appear here.")
                return
            
            # Create and show dialog
            config_manager = getattr(self.main_window, "config_manager", None)
            theme_manager = getattr(self.main_window, "theme_manager", None)
            station_database = getattr(self.main_window, "station_database", None)

            # Phase 2 boundary: inject routing services from the already-constructed
            # TrainManager rather than constructing inside the dialog/UI.
            train_manager = getattr(self.main_window, "train_manager", None)
            station_service = getattr(train_manager, "route_calculation_service", None)
            station_service = getattr(station_service, "station_service", None)
            route_service = getattr(train_manager, "route_calculation_service", None)
            route_service = getattr(route_service, "route_service", None)

            dialog = StationsSettingsDialog(
                parent=self.main_window,
                station_database=station_database,
                config_manager=config_manager,
                theme_manager=theme_manager,
                station_service=station_service,
                route_service=route_service,
            )
            self._open_dialogs['stations_settings'] = dialog

            # Connect dialog signals
            # In the refactored flow, dialogs emit no payload; MainWindow is the
            # single place that reloads config + refreshes subsystems.
            if hasattr(dialog, "settings_saved"):
                dialog.settings_saved.connect(self.main_window.on_settings_saved)
            elif hasattr(dialog, "settings_changed"):
                dialog.settings_changed.connect(self.main_window.on_settings_saved)
            
            # Show dialog
            result = dialog.exec()
            
            # Clean up dialog reference
            if 'stations_settings' in self._open_dialogs:
                del self._open_dialogs['stations_settings']
            
            logger.debug(f"Stations settings dialog closed with result: {result}")
            
        except Exception as e:
            logger.error(f"Error showing stations settings dialog: {e}")
            self._show_error_dialog("Settings Error", f"Failed to open stations settings: {str(e)}")
    
    def show_weather_settings_dialog(self) -> None:
        """Show the weather settings dialog."""
        try:
            # Prevent multiple instances of the same dialog
            if 'weather_settings' in self._open_dialogs:
                existing_dialog = self._open_dialogs['weather_settings']
                if existing_dialog and existing_dialog.isVisible():
                    existing_dialog.raise_()
                    existing_dialog.activateWindow()
                    return
            
            # Import dialog class
            try:
                # Weather settings dialog has not been migrated into this manager-based
                # system yet.
                raise ImportError
            except ImportError:
                logger.error("WeatherSettingsDialog not found - creating placeholder")
                self._show_placeholder_dialog("Weather Settings", "Weather configuration dialog would appear here.")
                return
            
            # Dialog not available.
            return
            
        except Exception as e:
            logger.error(f"Error showing weather settings dialog: {e}")
            self._show_error_dialog("Settings Error", f"Failed to open weather settings: {str(e)}")
    
    def show_astronomy_settings_dialog(self) -> None:
        """Show the astronomy settings dialog."""
        try:
            # Prevent multiple instances of the same dialog
            if 'astronomy_settings' in self._open_dialogs:
                existing_dialog = self._open_dialogs['astronomy_settings']
                if existing_dialog and existing_dialog.isVisible():
                    existing_dialog.raise_()
                    existing_dialog.activateWindow()
                    return
            
            # Import dialog class
            try:
                from src.ui.astronomy_settings_dialog import AstronomySettingsDialog
            except ImportError:
                logger.error("AstronomySettingsDialog not found - creating placeholder")
                self._show_placeholder_dialog("Astronomy Settings", "Astronomy configuration dialog would appear here.")
                return
            
            # Create and show dialog
            config = getattr(self.main_window, 'config', None)
            if not config:
                logger.error("No configuration available for astronomy settings")
                return
            
            # AstronomySettingsDialog signature: (config_manager, parent=None, theme_manager=None)
            config_manager = getattr(self.main_window, "config_manager", None)
            theme_manager = getattr(self.main_window, "theme_manager", None)
            if not config_manager:
                logger.error("No config_manager available for astronomy settings")
                return

            dialog = AstronomySettingsDialog(config_manager, parent=self.main_window, theme_manager=theme_manager)
            self._open_dialogs['astronomy_settings'] = dialog
            
            # Connect dialog signals
            if hasattr(dialog, 'settings_saved'):
                dialog.settings_saved.connect(self._on_astronomy_settings_changed)
            
            # Show dialog
            result = dialog.exec()
            
            # Clean up dialog reference
            if 'astronomy_settings' in self._open_dialogs:
                del self._open_dialogs['astronomy_settings']
            
            logger.debug(f"Astronomy settings dialog closed with result: {result}")
            
        except Exception as e:
            logger.error(f"Error showing astronomy settings dialog: {e}")
            self._show_error_dialog("Settings Error", f"Failed to open astronomy settings: {str(e)}")
    
    def show_general_settings_dialog(self) -> None:
        """Show the general application settings dialog."""
        try:
            # Prevent multiple instances of the same dialog
            if 'general_settings' in self._open_dialogs:
                existing_dialog = self._open_dialogs['general_settings']
                if existing_dialog and existing_dialog.isVisible():
                    existing_dialog.raise_()
                    existing_dialog.activateWindow()
                    return
            
            # Import dialog class
            try:
                # General settings dialog is not implemented in this project layout.
                raise ImportError
            except ImportError:
                logger.error("GeneralSettingsDialog not found - creating placeholder")
                self._show_placeholder_dialog("General Settings", "General application settings dialog would appear here.")
                return
            
            # Dialog not available.
            return
            
        except Exception as e:
            logger.error(f"Error showing general settings dialog: {e}")
            self._show_error_dialog("Settings Error", f"Failed to open general settings: {str(e)}")
    
    def show_about_dialog(self) -> None:
        """Show the about dialog."""
        try:
            # About dialog is handled by [`python.show_about_dialog()`](src/ui/main_window_components/info_dialogs.py:14)
            # in the refactored main window.
            self.main_window.show_about_dialog()
            
            logger.debug("About dialog shown")
            
        except Exception as e:
            logger.error(f"Error showing about dialog: {e}")
            self._show_error_dialog("About Error", f"Failed to open about dialog: {str(e)}")
    
    def _show_placeholder_dialog(self, title: str, message: str) -> None:
        """Show a placeholder dialog when the actual dialog is not available."""
        msg_box = QMessageBox(self.main_window)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.exec()
    
    def _show_error_dialog(self, title: str, message: str) -> None:
        """Show an error dialog."""
        msg_box = QMessageBox(self.main_window)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setIcon(QMessageBox.Icon.Critical)
        msg_box.exec()
    
    def _on_stations_settings_changed(self, settings: Optional[Dict[str, Any]] = None) -> None:
        """Handle stations settings changes.

        NOTE: kept for backward compatibility. The refactored dialog now emits
        `settings_saved` without payload, and the preferred flow is to call
        [`python.MainWindow.on_settings_saved()`](src/ui/main_window_refactored.py:276).
        """
        try:
            logger.info("Stations settings changed")

            if hasattr(self.main_window, "on_settings_saved"):
                self.main_window.on_settings_saved()
                return
            
            # Update configuration
            config = getattr(self.main_window, 'config', None)
            if config and hasattr(config, 'stations') and settings:
                # Apply settings changes
                for key, value in settings.items():
                    if hasattr(config.stations, key):
                        setattr(config.stations, key, value)
                
                # Save configuration
                config_manager = getattr(self.main_window, 'config_manager', None)
                if config_manager:
                    config_manager.save_config(config)
                
                # Refresh train data with new settings
                train_manager = getattr(self.main_window, 'train_manager', None)
                if train_manager:
                    if hasattr(train_manager, "fetch_trains"):
                        train_manager.fetch_trains()
                    elif hasattr(train_manager, "refresh_trains"):
                        train_manager.refresh_trains()
                
                logger.debug("Stations settings applied and trains refreshed")
            
        except Exception as e:
            logger.error(f"Error applying stations settings: {e}")
    
    def _on_weather_settings_changed(self, settings: Dict[str, Any]) -> None:
        """
        Handle weather settings changes.
        
        Args:
            settings: Updated weather settings
        """
        try:
            logger.info("Weather settings changed")
            
            # Update configuration
            config = getattr(self.main_window, 'config', None)
            if config and hasattr(config, 'weather'):
                # Apply settings changes
                for key, value in settings.items():
                    if hasattr(config.weather, key):
                        setattr(config.weather, key, value)
                
                # Save configuration
                config_manager = getattr(self.main_window, 'config_manager', None)
                if config_manager:
                    config_manager.save_config(config)
                
                # Reinitialize weather system with new settings
                if self.widget_lifecycle_manager:
                    self.widget_lifecycle_manager.setup_weather_system()
                
                logger.debug("Weather settings applied and system reinitialized")
            
        except Exception as e:
            logger.error(f"Error applying weather settings: {e}")
    
    def _on_astronomy_settings_changed(self, settings: Optional[Dict[str, Any]] = None) -> None:
        """Handle astronomy settings changes.

        The refactored [`python.AstronomySettingsDialog`](src/ui/astronomy_settings_dialog.py:41)
        emits `settings_saved` without a payload. Older code paths expected a dict.

        Args:
            settings: Optional updated astronomy settings.
        """
        try:
            logger.info("Astronomy settings changed")

            # Preferred path in the refactored app: let MainWindow reload config +
            # update subsystems consistently.
            if hasattr(self.main_window, "on_settings_saved"):
                try:
                    self.main_window.on_settings_saved()
                    return
                except Exception as e:
                    logger.warning("MainWindow.on_settings_saved() failed: %s", e)
             
            # Update configuration
            config = getattr(self.main_window, 'config', None)
            if config and hasattr(config, 'astronomy'):
                # Apply settings changes if provided
                if settings:
                    for key, value in settings.items():
                        if hasattr(config.astronomy, key):
                            setattr(config.astronomy, key, value)
                 
                # Save configuration
                config_manager = getattr(self.main_window, 'config_manager', None)
                if config_manager:
                    config_manager.save_config(config)
                
                # Reinitialize astronomy system with new settings
                if self.widget_lifecycle_manager:
                    self.widget_lifecycle_manager.setup_astronomy_system()
                
                logger.debug("Astronomy settings applied and system reinitialized")
            
        except Exception as e:
            logger.error(f"Error applying astronomy settings: {e}")
    
    def _on_general_settings_changed(self, settings: Dict[str, Any]) -> None:
        """
        Handle general settings changes.
        
        Args:
            settings: Updated general settings
        """
        try:
            logger.info("General settings changed")
            
            # Update configuration
            config = getattr(self.main_window, 'config', None)
            if config:
                # Apply settings changes
                for key, value in settings.items():
                    if hasattr(config, key):
                        setattr(config, key, value)
                
                # Save configuration
                config_manager = getattr(self.main_window, 'config_manager', None)
                if config_manager:
                    config_manager.save_config(config)
                
                # Apply changes that require immediate action
                if 'refresh_interval_minutes' in settings:
                    # Update refresh timer
                    event_handler = getattr(self.main_window, 'event_handler_manager', None)
                    if event_handler:
                        event_handler.setup_refresh_timer()
                
                if 'theme' in settings:
                    # Apply theme changes
                    if self.ui_layout_manager:
                        self.ui_layout_manager.apply_theme()
                
                logger.debug("General settings applied")
            
        except Exception as e:
            logger.error(f"Error applying general settings: {e}")
    
    def close_all_dialogs(self) -> None:
        """Close all open settings dialogs."""
        try:
            for dialog_name, dialog in list(self._open_dialogs.items()):
                if dialog and dialog.isVisible():
                    dialog.close()
                    logger.debug(f"Closed {dialog_name} dialog")
            
            self._open_dialogs.clear()
            
        except Exception as e:
            logger.error(f"Error closing dialogs: {e}")
