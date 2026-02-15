"""
Header buttons manager for the main window.

This module provides a class for creating, positioning, and styling
the header buttons of the main window, extracted from the MainWindow class.
"""

import logging
from typing import Callable, Optional, Tuple

from PySide6.QtWidgets import QMainWindow, QPushButton
from PySide6.QtCore import Qt

logger = logging.getLogger(__name__)


class HeaderButtonsManager:
    """
    Manager for the main window header buttons.
    
    Handles creation, positioning, styling, and management of the header buttons
    (theme, astronomy, and train).
    """
    
    def __init__(self, main_window: QMainWindow, theme_manager):
        """
        Initialize header buttons manager.
        
        Args:
            main_window: Parent main window
            theme_manager: Theme manager for styling
        """
        self.main_window = main_window
        self.theme_manager = theme_manager
        
        # Initialize button references
        self.theme_button = None
        self.astronomy_button = None
        self.train_button = None
    
    def setup_header_buttons(self, 
                            theme_callback: Callable,
                            astronomy_callback: Callable,
                            train_callback: Callable) -> Tuple[QPushButton, QPushButton, QPushButton]:
        """
        Setup header buttons (theme, astronomy toggle, and train settings) in top-right corner.
        
        Args:
            theme_callback: Callback for theme button click
            astronomy_callback: Callback for astronomy button click
            train_callback: Callback for train button click
            
        Returns:
            Tuple of (theme_button, astronomy_button, train_button)
        """
        # Create theme button (150% bigger: 32 * 1.5 = 48)
        self.theme_button = QPushButton(self.theme_manager.get_theme_icon(), self.main_window)
        self.theme_button.clicked.connect(theme_callback)
        self.theme_button.setToolTip(self.theme_manager.get_theme_tooltip())
        self.theme_button.setFixedSize(48, 48)
        
        # Create astronomy settings button (150% bigger: 32 * 1.5 = 48)
        self.astronomy_button = QPushButton("🔭", self.main_window)
        self.astronomy_button.clicked.connect(astronomy_callback)
        self.astronomy_button.setToolTip("Astronomy Settings")
        self.astronomy_button.setFixedSize(48, 48)
        
        # Create train settings button (150% bigger: 32 * 1.5 = 48)
        self.train_button = QPushButton("🚅", self.main_window)
        self.train_button.clicked.connect(train_callback)
        self.train_button.setToolTip("Train Settings")
        self.train_button.setFixedSize(48, 48)
        
        # Apply styling to all buttons
        self.apply_header_button_styling()
        
        # Position the buttons in the top-right corner
        self.position_header_buttons()
        
        # Make sure the buttons stay on top
        self.theme_button.raise_()
        self.astronomy_button.raise_()
        self.train_button.raise_()
        self.theme_button.show()
        self.astronomy_button.show()
        self.train_button.show()
        
        return (self.theme_button, self.astronomy_button, self.train_button)
    
    def position_header_buttons(self) -> None:
        """Position header buttons (theme, astronomy, and train) in the top-right corner."""
        button_width = 48  # Updated for 150% bigger buttons
        button_spacing = 12  # Increased spacing proportionally (8 * 1.5 = 12)
        right_margin = 12    # Increased margin proportionally (8 * 1.5 = 12)
        top_margin = 12      # Increased margin proportionally (8 * 1.5 = 12)
        
        if self.astronomy_button:
            # Astronomy button (rightmost)
            astro_x = self.main_window.width() - button_width - right_margin
            self.astronomy_button.move(astro_x, top_margin)
        
        if self.train_button:
            # Train button (middle - left of astronomy button)
            train_x = self.main_window.width() - (button_width * 2) - button_spacing - right_margin
            self.train_button.move(train_x, top_margin)
        
        if self.theme_button:
            # Theme button (leftmost - left of train button)
            theme_x = self.main_window.width() - (button_width * 3) - (button_spacing * 2) - right_margin
            self.theme_button.move(theme_x, top_margin)
    
    def apply_header_button_styling(self) -> None:
        """Apply styling to header buttons (theme, astronomy, and train)."""
        # Get current theme colors
        if self.theme_manager.current_theme == "dark":
            button_style = """
            QPushButton {
                background-color: #2d2d2d;
                border: 1px solid #404040;
                border-radius: 4px;
                color: #ffffff;
                padding: 4px;
                font-size: 24px;
            }
            QPushButton:hover {
                background-color: #404040;
                border-color: #1976d2;
            }
            QPushButton:pressed {
                background-color: #1976d2;
            }
            """
        else:
            button_style = """
            QPushButton {
                background-color: #f0f0f0;
                border: 1px solid #cccccc;
                border-radius: 4px;
                color: #000000;
                padding: 4px;
                font-size: 24px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
                border-color: #1976d2;
            }
            QPushButton:pressed {
                background-color: #1976d2;
                color: #ffffff;
            }
            """
        
        if self.theme_button:
            self.theme_button.setStyleSheet(button_style)
        if self.astronomy_button:
            self.astronomy_button.setStyleSheet(button_style)
        if self.train_button:
            self.train_button.setStyleSheet(button_style)
    
    def update_theme_button(self) -> None:
        """Update theme button icon and tooltip based on current theme."""
        if self.theme_button:
            self.theme_button.setText(self.theme_manager.get_theme_icon())
            self.theme_button.setToolTip(self.theme_manager.get_theme_tooltip())
            
    def get_astronomy_icon(self) -> str:
        """Get astronomy button icon (always telescope for settings)."""
        return "🔭"

    def get_astronomy_tooltip(self) -> str:
        """Get astronomy button tooltip (always settings)."""
        return "Astronomy Settings"