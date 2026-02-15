"""
UI Layout Manager

Handles UI layout creation and management for the stations settings dialog.
"""

import logging
import sys
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QWidget, QGroupBox, QSizePolicy, QApplication
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

logger = logging.getLogger(__name__)


class UILayoutManager:
    """Handles UI layout creation and management for the stations settings dialog."""
    
    def __init__(self, dialog):
        """
        Initialize the UI layout manager.
        
        Args:
            dialog: The parent dialog
        """
        self.dialog = dialog
    
    def setup_ui(self):
        """Set up the complete user interface."""
        main_layout = QVBoxLayout(self.dialog)
        
        # Use Linux layout settings for all platforms - reduced spacing to give more room for content
        main_layout.setSpacing(8)  # Reduced from 12
        main_layout.setContentsMargins(15, 15, 15, 15)  # Reduced from 20
        
        # Create tab widget for different sections
        self.dialog.tab_widget = QTabWidget()
        main_layout.addWidget(self.dialog.tab_widget)
        
        # Create tabs
        self._create_route_tab()
        self._create_preferences_tab()
        
        # Create button bar with integrated status
        button_layout = self._create_button_bar()
        main_layout.addLayout(button_layout)
        
        # Set initial tab
        self.dialog.tab_widget.setCurrentIndex(0)
    
    def _create_route_tab(self):
        """Create the main route planning tab."""
        route_tab = QWidget()
        self.dialog.tab_widget.addTab(route_tab, "Route Planning")
        
        layout = QVBoxLayout(route_tab)
        
        # Use Linux implementation for all platforms - reduced spacing to save vertical space
        layout.setSpacing(10)  # Reduced from 20 to save vertical space
        
        # Station selection section
        station_group = QGroupBox("Station Selection")
        station_layout = QVBoxLayout(station_group)
        
        # Use Linux layout adjustments for all platforms
        station_layout.setContentsMargins(5, 5, 5, 5)  # Very tight margins
        station_layout.setSpacing(0)  # No spacing
        # Set a maximum height for the station group
        station_group.setMaximumHeight(150)  # Limit the height
        
        station_layout.addWidget(self.dialog.station_selection_widget)
        layout.addWidget(station_group)
        
        # Route action buttons
        layout.addWidget(self.dialog.route_action_buttons)
        
        # Route details section
        details_group = QGroupBox("Route Details")
        details_layout = QVBoxLayout(details_group)
        
        details_layout.addWidget(self.dialog.route_details_widget)
        
        # Platform-specific sizing for the details group
        if sys.platform.startswith('linux'):
            # Detect small screen
            screen = QApplication.primaryScreen()
            if screen:
                screen_geometry = screen.availableGeometry()
                is_small_screen = screen_geometry.width() <= 1440 or screen_geometry.height() <= 900
            else:
                is_small_screen = False
            
            if is_small_screen:
                # Make the Route Details group expand to fill available space
                details_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        layout.addWidget(details_group, 1)  # Add with stretch factor of 1 to allow expansion
    
    def _create_preferences_tab(self):
        """Create the preferences tab."""
        preferences_tab = QWidget()
        self.dialog.tab_widget.addTab(preferences_tab, "Preferences")
        
        layout = QVBoxLayout(preferences_tab)
        
        # Use Linux implementation for all platforms
        layout.setSpacing(20)
        
        # Preferences widget
        layout.addWidget(self.dialog.preferences_widget)
        
        # Add stretch
        layout.addStretch()
    
    def _create_status_bar(self):
        """Create the status bar."""
        self.dialog.status_label = QLabel("Ready")
        # Remove hardcoded styles - let theme manager handle it
        self.dialog.status_label.setObjectName("statusLabel")
        
        # Platform-specific sizing for status label
        if sys.platform.startswith('linux'):
            self.dialog.status_label.setMaximumHeight(25)  # Limit height on Linux
            self.dialog.status_label.setFont(QFont("Arial", 9))  # Smaller font
    
    def _create_button_bar(self):
        """Create the dialog button bar with integrated status."""
        layout = QHBoxLayout()
        
        # Create and add status label on the left
        self._create_status_bar()
        layout.addWidget(self.dialog.status_label)
        
        # Add stretch to push buttons to the right
        layout.addStretch()
        
        # Cancel button (now first/left)
        self.dialog.cancel_button = QPushButton("Cancel")
        self.dialog.cancel_button.setObjectName("cancelButton")
        layout.addWidget(self.dialog.cancel_button)
        
        # Save button (now second/right)
        self.dialog.save_button = QPushButton("Save")
        self.dialog.save_button.setDefault(True)
        self.dialog.save_button.setObjectName("saveButton")
        layout.addWidget(self.dialog.save_button)
        
        return layout