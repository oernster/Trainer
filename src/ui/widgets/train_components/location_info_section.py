"""
Location information section component.

This module provides a component for displaying train location information,
including current location and arrival time.
"""

import logging
from typing import Optional

from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QSizePolicy
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from .base_component import BaseTrainComponent
from ....models.train_data import TrainData

logger = logging.getLogger(__name__)


class LocationInfoSection(BaseTrainComponent):
    """
    Component for displaying train location information.
    
    Displays current location and arrival time.
    """
    
    def __init__(self, train_data: Optional[TrainData] = None, theme: str = "dark", parent=None):
        """
        Initialize location info section.
        
        Args:
            train_data: Train data to display
            theme: Current theme ("dark" or "light")
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.train_data = train_data
        self._current_theme = theme
        self._theme_colors = self.get_theme_colors(theme)
        
        # Setup UI
        self._setup_ui()
        self._apply_theme_styles()
    
    def set_train_data(self, train_data: TrainData) -> None:
        """
        Update the train data and refresh the display.
        
        Args:
            train_data: Updated train data
        """
        self.train_data = train_data
        self._update_display()
    
    def _setup_ui(self) -> None:
        """Setup the location info section UI layout."""
        location_layout = QHBoxLayout(self)
        location_layout.setContentsMargins(0, 0, 0, 0)
        location_layout.setSpacing(1)  # Minimal spacing
        
        # Current location
        self.location_info = QLabel()
        location_font = QFont()
        location_font.setPointSize(18)
        self.location_info.setFont(location_font)
        location_layout.addWidget(self.location_info)
        
        location_layout.addStretch()
        
        # Arrival time
        self.arrival_info = QLabel()
        self.arrival_info.setAlignment(Qt.AlignmentFlag.AlignRight)
        arrival_font = QFont()
        arrival_font.setPointSize(18)
        self.arrival_info.setFont(arrival_font)
        location_layout.addWidget(self.arrival_info)
        
        # Set size policy to allow expansion
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        
        # Update display with initial data
        self._update_display()
    
    def _update_display(self) -> None:
        """Update the display with current train data."""
        if not self.train_data or not hasattr(self, 'location_info'):
            return
        
        # Update location info
        if self.train_data.current_location:
            location_text = f"Current: {self.train_data.current_location} 📍"
            self.location_info.setText(location_text)
            self.location_info.setVisible(True)
        else:
            self.location_info.setVisible(False)
        
        # Update arrival info
        if self.train_data.estimated_arrival:
            arrival_text = f"Arrives: {self.train_data.format_arrival_time()} 🏁"
            self.arrival_info.setText(arrival_text)
            self.arrival_info.setVisible(True)
        else:
            self.arrival_info.setVisible(False)
    
    def _apply_theme_styles(self) -> None:
        """Apply theme-specific styling."""
        colors = self.get_theme_colors(self._current_theme)
        
        # Apply theme-specific styles
        if self._current_theme == "light":
            self.setStyleSheet(f"""
                QLabel {{
                    color: #212121;
                    background-color: transparent;
                    border: none;
                    margin: 0px;
                    padding: 0px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QLabel {{
                    color: {colors['text_primary']};
                    background-color: transparent;
                    border: none;
                    margin: 0px;
                    padding: 0px;
                }}
            """)