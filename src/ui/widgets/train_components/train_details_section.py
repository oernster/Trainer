"""
Train details section component.

This module provides a component for displaying train details information,
including operator and status.
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


class TrainDetailsSection(BaseTrainComponent):
    """
    Component for displaying train details information.
    
    Displays operator and status information.
    """
    
    def __init__(self, train_data: Optional[TrainData] = None, theme: str = "dark", parent=None):
        """
        Initialize train details section.
        
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
        """Setup the details section UI layout."""
        details_layout = QHBoxLayout(self)
        details_layout.setContentsMargins(0, 0, 0, 0)
        details_layout.setSpacing(1)  # Minimal spacing
        
        # Left: Operator and service details
        self.operator_info = QLabel()
        operator_font = QFont()
        operator_font.setPointSize(20)
        self.operator_info.setFont(operator_font)
        details_layout.addWidget(self.operator_info)
        
        details_layout.addStretch()
        
        # Right: Status with icon
        self.status_info = QLabel()
        self.status_info.setAlignment(Qt.AlignmentFlag.AlignRight)
        status_font = QFont()
        status_font.setPointSize(20)
        status_font.setBold(True)
        self.status_info.setFont(status_font)
        details_layout.addWidget(self.status_info)
        
        # Set size policy to allow expansion
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        
        # Update display with initial data
        self._update_display()
    
    def _update_display(self) -> None:
        """Update the display with current train data."""
        if not self.train_data or not hasattr(self, 'operator_info'):
            return
        
        # Update operator info
        operator_text = self.train_data.operator or "Unknown Operator"
        self.operator_info.setText(operator_text)
        
        # Update status info
        status_text = f"{self.train_data.get_status_icon()} {self.train_data.format_delay()}"
        self.status_info.setText(status_text)
        
        # Set status color
        status_color = self.train_data.get_status_color(self._current_theme)
        self.status_info.setStyleSheet(f"color: {status_color};")
    
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