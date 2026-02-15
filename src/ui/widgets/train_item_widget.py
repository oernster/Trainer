"""
Train item widget for displaying individual train information.

This module provides a widget for displaying comprehensive train information
including departure time, destination, platform, operator, status, and current location.
"""

import logging
from typing import Optional

from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QWidget
)
from PySide6.QtCore import Qt, Signal

from ...models.train_data import TrainData
from .train_widgets_base import BaseTrainWidget
from .train_components import (
    TrainMainInfoSection,
    TrainDetailsSection,
    CallingPointsManager,
    LocationInfoSection
)

logger = logging.getLogger(__name__)


class TrainItemWidget(BaseTrainWidget):
    """
    Individual train information display widget with theme support.

    Displays comprehensive train information including departure time,
    destination, platform, operator, status, and current location.
    
    This class has been refactored to use specialized components for each section,
    following the Single Responsibility Principle.
    """

    # Signal emitted when train item is clicked
    train_clicked = Signal(TrainData)
    # Signal emitted when route button is clicked
    route_clicked = Signal(TrainData)

    def __init__(self, train_data: TrainData, theme: str = "dark",
                 train_manager=None, preferences: Optional[dict] = None, parent: Optional[QWidget] = None):
        """
        Initialize train item widget.

        Args:
            train_data: Train information to display
            theme: Current theme ("dark" or "light")
            train_manager: Train manager instance for accessing route data
            preferences: User preferences dictionary
            parent: Parent widget
        """
        super().__init__(parent)
        
        # Initialize theme
        self.current_theme = theme
        
        self.train_data = train_data
        self.train_manager = train_manager
        self.preferences = preferences or {}
        
        # Setup UI
        self._setup_ui()
        self._apply_theme_styles()
    
    def _setup_ui(self) -> None:
        """Setup the train item UI layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(0)  # No spacing between layout elements
        
        # Main train info section (time, destination, platform, route button)
        self.main_info_section = TrainMainInfoSection(self.train_data, self.current_theme, self)
        self.main_info_section.route_clicked.connect(self._on_route_clicked)
        layout.addWidget(self.main_info_section)
        
        # Details section (operator, status)
        self.details_section = TrainDetailsSection(self.train_data, self.current_theme, self)
        layout.addWidget(self.details_section)
        
        # Calling points section (intermediate stations)
        self.calling_points_manager = CallingPointsManager(self.train_data, self.current_theme, self)
        layout.addWidget(self.calling_points_manager)
        
        # Location section (current location and arrival time)
        self.location_section = LocationInfoSection(self.train_data, self.current_theme, self)
        layout.addWidget(self.location_section)
    
    def _on_route_clicked(self, train_data: TrainData) -> None:
        """
        Handle route button click.
        
        Args:
            train_data: Train data to emit
        """
        self.route_clicked.emit(train_data)
    
    def set_preferences(self, preferences: dict) -> None:
        """
        Update preferences and refresh the display.
        
        Args:
            preferences: Updated preferences dictionary
        """
        self.preferences = preferences or {}
        # Refresh the calling points display to apply new preferences
        self.calling_points_manager._refresh_display()
    
    def _apply_theme_styles(self) -> None:
        """Apply theme-specific styling."""
        colors = self.get_theme_colors(self.current_theme)
        status_color = self.train_data.get_status_color(self.current_theme)

        # FORCE light theme styling when in light mode
        if self.current_theme == "light":
            style = f"""
            QFrame {{
                background-color: #ffffff !important;
                border: 1px solid #e0e0e0 !important;
                border-left: 4px solid {status_color} !important;
                border-radius: 8px !important;
                margin: 2px !important;
                padding: 8px !important;
            }}
            
            QFrame:hover {{
                background-color: #f5f5f5 !important;
                border-color: #1976d2 !important;
            }}
            
            QLabel {{
                color: #212121 !important;
                background-color: transparent !important;
                border: none !important;
                margin: 0px !important;
                padding: 0px !important;
                font-size: 15pt !important;
                text-align: left !important;
                max-width: 100000px !important;
                min-width: 0px !important;
            }}
            
            QWidget {{
                background-color: transparent !important;
            }}
            """
        else:
            # Dark theme styling
            style = f"""
            QFrame {{
                background-color: {colors['background_secondary']};
                border: 1px solid {colors['border_primary']};
                border-left: 4px solid {status_color};
                border-radius: 8px;
                margin: 2px;
                padding: 8px;
            }}
            
            QFrame:hover {{
                background-color: {colors['background_hover']};
                border-color: {colors['primary_accent']};
            }}
            
            QLabel {{
                color: {colors['text_primary']};
                background-color: transparent;
                border: none;
                margin: 0px;
                padding: 0px;
                font-size: 15pt;
                text-align: left;
                max-width: 100000px;
                min-width: 0px;
            }}
            
            QWidget {{
                background-color: transparent;
            }}
            """
        
        self.setStyleSheet(style)