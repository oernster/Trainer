"""
Theme applier for the main window.

This module provides a class for applying themes to all components
of the main window, extracted from the MainWindow class.
"""

import logging
from typing import Dict, Optional, Any

from PySide6.QtWidgets import QMainWindow

logger = logging.getLogger(__name__)


class ThemeApplier:
    """
    Applier for themes to all main window components.
    
    Handles applying themes to the main window and all its components.
    """
    
    def __init__(self, main_window: QMainWindow, theme_manager):
        """
        Initialize theme applier.
        
        Args:
            main_window: Parent main window
            theme_manager: Theme manager for accessing themes
        """
        self.main_window = main_window
        self.theme_manager = theme_manager
    
    def apply_theme(self) -> None:
        """Apply current theme styling to the main window."""
        main_style = self.theme_manager.get_main_window_stylesheet()
        widget_style = self.theme_manager.get_widget_stylesheet()

        # Add custom styling to remove borders under menu bar
        if self.theme_manager.current_theme == "dark":
            custom_style = """
            QMainWindow {
                border: none;
            }
            QMainWindow::separator {
                border: none;
                background: transparent;
            }
            """
        else:
            custom_style = """
            QMainWindow {
                border: none;
            }
            QMainWindow::separator {
                border: none;
                background: transparent;
            }
            """

        self.main_window.setStyleSheet(main_style + widget_style + custom_style)
        logger.debug(f"Applied {self.theme_manager.current_theme} theme to main window")
    
    def apply_theme_to_all_widgets(self,
                                  train_list_widget: Optional[Any] = None,
                                  weather_widget: Optional[Any] = None,
                                  astronomy_widget: Optional[Any] = None) -> None:
        """
        Apply theme to all widgets after creation.
        
        Args:
            train_list_widget: Train list widget to apply theme to
            weather_widget: Weather widget to apply theme to
            astronomy_widget: Astronomy widget to apply theme to
        """
        current_theme = self.theme_manager.current_theme

        # Apply theme to train list widget
        if train_list_widget:
            train_list_widget.apply_theme(current_theme)
            logger.debug("Applied theme to train list widget")

        # Apply theme to weather widget
        if weather_widget:
            theme_colors = self._get_theme_colors_dict(current_theme)
            weather_widget.apply_theme(theme_colors)
            logger.debug("Applied theme to weather widget")

        # Apply theme to astronomy widget
        if astronomy_widget:
            theme_colors = self._get_theme_colors_dict(current_theme)
            astronomy_widget.apply_theme(theme_colors)
            logger.debug("Applied theme to astronomy widget")
    
    def _get_theme_colors_dict(self, theme_name: str) -> Dict[str, str]:
        """
        Get theme colors dictionary for widgets.
        
        Args:
            theme_name: Theme name ("dark" or "light")
            
        Returns:
            Dictionary of theme colors
        """
        if theme_name == "dark":
            return {
                "background_primary": "#1a1a1a",
                "background_secondary": "#2d2d2d",
                "background_hover": "#404040",
                "text_primary": "#ffffff",
                "primary_accent": "#1976d2",
                "border_primary": "#404040",
            }
        else:
            return {
                "background_primary": "#ffffff",
                "background_secondary": "#f5f5f5",
                "background_hover": "#e0e0e0",
                "text_primary": "#000000",
                "primary_accent": "#1976d2",
                "border_primary": "#cccccc",
            }