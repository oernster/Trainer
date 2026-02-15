"""
Train main information section component.

This module provides a component for displaying the main train information,
including departure time, destination, platform, and route button.
"""

import logging
from typing import Optional

from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QSizePolicy, QLayout
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from .base_component import BaseTrainComponent
from ....models.train_data import TrainData

logger = logging.getLogger(__name__)


class TrainMainInfoSection(BaseTrainComponent):
    """
    Component for displaying the main train information.
    
    Displays train departure time, destination, platform, and route button.
    """
    
    # Signal emitted when route button is clicked
    route_clicked = Signal(TrainData)
    
    def __init__(self, train_data: Optional[TrainData] = None, theme: str = "dark", parent=None):
        """
        Initialize train main info section.
        
        Args:
            train_data: Train data to display
            theme: Current theme ("dark" or "light")
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.train_data = train_data
        self._current_theme = theme
        self._theme_colors = self.get_theme_colors(theme)
        
        # Setup UI first, which will initialize the UI elements
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
        """Setup the main info section UI layout."""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)  # No spacing between layout elements
        
        # Left side: Train icon, time, destination
        left_layout = QHBoxLayout()
        left_layout.setSpacing(1)  # Minimal spacing
        left_layout.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)  # No size constraints
        
        # Train service icon and time
        self.time_info = QLabel()
        time_font = QFont()
        time_font.setPointSize(28)
        time_font.setBold(True)
        self.time_info.setFont(time_font)
        left_layout.addWidget(self.time_info)
        
        # Arrow and destination
        self.destination_info = QLabel()
        dest_font = QFont()
        dest_font.setPointSize(24)
        self.destination_info.setFont(dest_font)
        left_layout.addWidget(self.destination_info)
        
        left_layout.addStretch()
        
        # Right side: Platform, status, and details button
        right_layout = QHBoxLayout()
        right_layout.setSpacing(1)  # Minimal spacing
        
        # Platform info
        self.platform_info = QLabel()
        self.platform_info.setAlignment(Qt.AlignmentFlag.AlignRight)
        platform_font = QFont()
        platform_font.setPointSize(20)
        self.platform_info.setFont(platform_font)
        right_layout.addWidget(self.platform_info)
        
        # Details button
        self.details_button = QLabel("🗺️ Route")
        self.details_button.setAlignment(Qt.AlignmentFlag.AlignRight)
        details_font = QFont()
        details_font.setPointSize(20)
        details_font.setBold(True)
        self.details_button.setFont(details_font)
        self._style_details_button()
        right_layout.addWidget(self.details_button)
        
        main_layout.addLayout(left_layout)
        main_layout.addLayout(right_layout)
        
        # Set size policy to allow expansion
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        
        # Update display with initial data
        self._update_display()
    
    def _update_display(self) -> None:
        """Update the display with current train data."""
        if not self.train_data or not hasattr(self, 'time_info'):
            return
        
        # Update time info
        time_text = f"{self.train_data.get_service_icon()} {self.train_data.format_departure_time()}"
        self.time_info.setText(time_text)
        
        # Update destination
        destination_text = self.train_data.destination or "Unknown"
        self.destination_info.setText(f"→ {destination_text}")
        
        # Update platform
        platform_text = f"Platform {self.train_data.platform or 'TBA'}"
        self.platform_info.setText(platform_text)
    
    def _style_details_button(self) -> None:
        """Style the details button."""
        self.details_button.setStyleSheet("""
            QLabel {
                background-color: rgba(79, 195, 247, 0.2);
                border: 1px solid #1976d2;
                border-radius: 4px;
                padding: 2px 6px;
                margin-left: 8px;
                font-weight: bold;
            }
            QLabel:hover {
                background-color: rgba(79, 195, 247, 0.4);
            }
        """)
        self.details_button.setCursor(Qt.CursorShape.PointingHandCursor)
    
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
    
    def mousePressEvent(self, event):
        """Handle mouse press event."""
        if event.button() == Qt.MouseButton.LeftButton:
            # Only handle clicks on the Route button
            if self.details_button and self.details_button.geometry().contains(event.pos()):
                if self.train_data:
                    self.route_clicked.emit(self.train_data)
        super().mousePressEvent(event)