"""
Menu bar manager for the main window.

This module provides a class for creating and styling the menu bar
of the main window, extracted from the MainWindow class.
"""

import logging
from typing import Callable, Optional

from PySide6.QtWidgets import QMainWindow, QMenuBar, QMenu
from PySide6.QtGui import QAction, QKeySequence

logger = logging.getLogger(__name__)


class MenuBarManager:
    """
    Manager for the main window menu bar.
    
    Handles creation, styling, and management of the menu bar and its actions.
    """
    
    def __init__(self, main_window: QMainWindow, theme_manager):
        """
        Initialize menu bar manager.
        
        Args:
            main_window: Parent main window
            theme_manager: Theme manager for styling
        """
        self.main_window = main_window
        self.theme_manager = theme_manager
        self.menubar = None
    
    def setup_menu_bar(self, 
                       exit_callback: Callable,
                       stations_settings_callback: Callable,
                       astronomy_settings_callback: Callable,
                       about_callback: Callable) -> QMenuBar:
        """
        Setup application menu bar.
        
        Args:
            exit_callback: Callback for exit action
            stations_settings_callback: Callback for stations settings action
            astronomy_settings_callback: Callback for astronomy settings action
            about_callback: Callback for about action
            
        Returns:
            Configured menu bar
        """
        # Ensure we're using the proper QMainWindow menu bar
        self.menubar = self.main_window.menuBar()

        # Clear any existing menu items
        self.menubar.clear()

        # Set menu bar properties to ensure proper display
        self.menubar.setNativeMenuBar(False)  # Force Qt menu bar on all platforms

        # File menu
        file_menu = self.menubar.addMenu("&File")

        exit_action = QAction("E&xit", self.main_window)
        exit_action.setShortcut(QKeySequence("Ctrl+Q"))
        exit_action.setStatusTip("Exit the application")
        exit_action.triggered.connect(exit_callback)
        file_menu.addAction(exit_action)

        # Settings menu
        settings_menu = self.menubar.addMenu("&Settings")

        stations_action = QAction("&Stations...", self.main_window)
        stations_action.setShortcut(QKeySequence("Ctrl+S"))
        stations_action.setStatusTip("Configure station settings, display, and refresh options")
        stations_action.triggered.connect(stations_settings_callback)
        settings_menu.addAction(stations_action)

        astronomy_action = QAction("&Astronomy...", self.main_window)
        astronomy_action.setShortcut(QKeySequence("Ctrl+A"))
        astronomy_action.setStatusTip("Configure astronomy settings and link preferences")
        astronomy_action.triggered.connect(astronomy_settings_callback)
        settings_menu.addAction(astronomy_action)

        # Help menu
        help_menu = self.menubar.addMenu("&Help")

        about_action = QAction("&About", self.main_window)
        about_action.setStatusTip("About this application")
        about_action.triggered.connect(about_callback)
        help_menu.addAction(about_action)

        # Apply menu bar styling
        self.apply_menu_bar_styling()
        
        return self.menubar
    
    def apply_menu_bar_styling(self) -> None:
        """Apply styling to the menu bar based on current theme."""
        if not self.menubar:
            logger.warning("Cannot style menu bar: no menu bar available")
            return
            
        # Get current theme colors
        if self.theme_manager.current_theme == "dark":
            menu_style = """
            QMenuBar {
                background-color: #2d2d2d;
                color: #ffffff;
                border: none;
                border-bottom: none;
                padding: 2px;
                margin: 0px;
            }
            QMenuBar::item {
                background-color: transparent;
                padding: 4px 8px;
                margin: 0px;
                border: none;
            }
            QMenuBar::item:selected {
                background-color: #1976d2;
                color: #ffffff;
            }
            QMenuBar::item:pressed {
                background-color: #0d47a1;
            }
            QMenu {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #404040;
            }
            QMenu::item {
                padding: 4px 20px;
                background-color: transparent;
            }
            QMenu::item:selected {
                background-color: #1976d2;
                color: #ffffff;
            }
            QMenu::separator {
                height: 1px;
                background-color: #404040;
                margin: 2px 0px;
            }
            """
        else:
            menu_style = """
            QMenuBar {
                background-color: #f0f0f0;
                color: #000000;
                border: none;
                border-bottom: none;
                padding: 2px;
                margin: 0px;
            }
            QMenuBar::item {
                background-color: transparent;
                padding: 4px 8px;
                margin: 0px;
                border: none;
            }
            QMenuBar::item:selected {
                background-color: #1976d2;
                color: #ffffff;
            }
            QMenuBar::item:pressed {
                background-color: #0d47a1;
            }
            QMenu {
                background-color: #ffffff;
                color: #000000;
                border: 1px solid #cccccc;
            }
            QMenu::item {
                padding: 4px 20px;
                background-color: transparent;
            }
            QMenu::item:selected {
                background-color: #1976d2;
                color: #ffffff;
            }
            QMenu::separator {
                height: 1px;
                background-color: #cccccc;
                margin: 2px 0px;
            }
            """

        self.menubar.setStyleSheet(menu_style)
        logger.debug(f"Menu bar styled for {self.theme_manager.current_theme} theme")