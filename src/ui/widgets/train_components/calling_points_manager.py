"""
Calling points manager component.

This module provides a component for managing and displaying train calling points
with proper formatting and styling.
"""

import logging
from typing import List, Optional

from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QWidget, QSizePolicy
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from .base_component import BaseTrainComponent
from .station_filter_service import StationFilterService
from ....models.train_data import TrainData, CallingPoint
from ....ui.formatters.underground_formatter import UndergroundFormatter
from .calling_points_styling import (
    stylesheet_for_direct_label,
    stylesheet_for_station_label,
)
from .calling_points_arrows import build_arrow_label

logger = logging.getLogger(__name__)


class CallingPointsManager(BaseTrainComponent):
    """
    Component for managing and displaying train calling points.
    
    Handles filtering, formatting, and displaying calling points with
    proper styling and indicators.
    """
    
    def __init__(self, train_data: Optional[TrainData] = None, theme: str = "dark", parent=None):
        """
        Initialize calling points manager.
        
        Args:
            train_data: Train data containing calling points
            theme: Current theme ("dark" or "light")
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.train_data = train_data
        self._current_theme = theme
        self._theme_colors = self.get_theme_colors(theme)
        
        # Initialize services
        self.station_filter_service = StationFilterService(train_data)
        self.underground_formatter = UndergroundFormatter()
        
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
        self.station_filter_service.set_train_data(train_data)
        self._refresh_display()
    
    def _setup_ui(self) -> None:
        """Setup the calling points manager UI layout."""
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)  # No spacing between layout elements
        
        # Create calling points container
        self.calling_points_widget = QWidget()
        self.calling_points_widget.setStyleSheet("""
            QWidget {
                background-color: transparent;
                border: none;
                margin: 0px;
                padding: 0px;
            }
        """)
        
        self.calling_points_layout = QVBoxLayout(self.calling_points_widget)
        self.calling_points_layout.setContentsMargins(0, 0, 0, 0)
        self.calling_points_layout.setSpacing(0)  # No spacing for calling points
        self.calling_points_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)  # Left-justify the layout
        
        self.main_layout.addWidget(self.calling_points_widget)
        
        # Set size policy to allow expansion
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        
        # Initial display
        self._refresh_display()
    
    def _refresh_display(self) -> None:
        """Refresh the calling points display."""
        # Clear existing content
        self._clear_layout(self.calling_points_layout)
        
        if not self.train_data:
            return
        
        # Get all calling points
        all_calling_points = self.train_data.calling_points
        
        if not all_calling_points:
            self._create_direct_service_display()
            return
        
        # Filter calling points
        filtered_calling_points = self.station_filter_service.filter_calling_points(all_calling_points)
        
        # Always filter to essential stations only
        essential_calling_points = self.station_filter_service.filter_for_essential_stations_only(filtered_calling_points)
        
        if essential_calling_points and len(essential_calling_points) >= 2:
            self._create_calling_points_display(essential_calling_points)
        else:
            self._create_direct_service_display()
    
    def _clear_layout(self, layout) -> None:
        """
        Clear all items from a layout.
        
        Args:
            layout: Layout to clear
        """
        if layout is None:
            return
            
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
            elif item.layout() is not None:
                self._clear_layout(item.layout())
                item.layout().deleteLater()
    
    def _create_calling_points_display(self, calling_points: List[CallingPoint]) -> None:
        """
        Create the display for calling points.
        
        Args:
            calling_points: List of calling points to display
        """
        # Show "Stops:" prefix on first line
        first_line_layout = QHBoxLayout()
        first_line_layout.setSpacing(0)  # No spacing
        first_line_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)  # Left-justify the layout
        
        stops_label = QLabel("Stops:")
        stops_font = QFont()
        stops_font.setPointSize(18)
        stops_font.setBold(True)
        stops_label.setFont(stops_font)
        first_line_layout.addWidget(stops_label)
        
        # Limit stations per line to avoid truncation
        max_stations_per_line = 3  # Allow 3 stations per line for better layout
        current_line_layout = first_line_layout
        stations_in_current_line = 0
        
        for i, calling_point in enumerate(calling_points):
            station_name = calling_point.station_name.strip() if calling_point.station_name else ""
            
            # Check if we need a new line
            if stations_in_current_line >= max_stations_per_line:
                current_line_layout.addStretch()
                self.calling_points_layout.addLayout(current_line_layout)
                
                # Start new line with indentation
                current_line_layout = QHBoxLayout()
                current_line_layout.setSpacing(0)  # No spacing
                current_line_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)  # Left-justify the layout
                
                # Add indentation
                indent_label = QLabel(" ")  # 1 space for indentation
                current_line_layout.addWidget(indent_label)
                stations_in_current_line = 0
            
            # Add arrow between stations
            if i > 0:
                self._add_station_arrow(current_line_layout, calling_points, i)
            
            # Create station label
            station_label = self._create_station_label(calling_point)
            current_line_layout.addWidget(station_label)
            stations_in_current_line += 1
        
        # Finish the last line with stretch at the end
        current_line_layout.addStretch(1)
        self.calling_points_layout.addLayout(current_line_layout)
    
    def _add_station_arrow(self, layout: QHBoxLayout, calling_points: List[CallingPoint], index: int) -> None:
        """
        Add arrow between stations with walking connection detection.
        
        Args:
            layout: Layout to add arrow to
            calling_points: List of all calling points
            index: Index of current calling point
        """
        raw_curr = calling_points[index].station_name if calling_points[index].station_name else ""
        raw_prev = calling_points[index - 1].station_name if calling_points[index - 1].station_name else ""

        colors = self.get_theme_colors(self._current_theme)
        arrow_label = build_arrow_label(
            train_data=self.train_data,
            underground_formatter=self.underground_formatter,
            theme=self._current_theme,
            theme_colors=colors,
            prev_station_raw=raw_prev,
            curr_station_raw=raw_curr,
        )

        arrow_font = QFont()
        arrow_font.setPointSize(15)
        arrow_label.setFont(arrow_font)
        layout.addWidget(arrow_label)
    
    def _create_station_label(self, calling_point: CallingPoint) -> QLabel:
        """
        Create a styled station label with underground system differentiation.
        
        Args:
            calling_point: Calling point to create label for
            
        Returns:
            Styled station label
        """
        station_label = QLabel()
        
        # Get station name and trim any leading and trailing spaces
        raw_name = calling_point.station_name if calling_point.station_name else ""
        
        # Check if this is an HTML-formatted station name (like underground connections)
        is_html_formatted = "<font" in raw_name and "</font>" in raw_name
        
        # For HTML-formatted names, we need to handle them differently
        if is_html_formatted:
            # Keep the HTML formatting but ensure consistent spacing
            station_name = raw_name
        else:
            # For plain text names, just strip spaces
            station_name = raw_name.strip()
        
        # Build the station text with appropriate indicators
        station_text = station_name
        
        station_label.setText(station_text)
        # Ensure text doesn't get truncated
        station_label.setWordWrap(False)
        station_label.setTextFormat(Qt.TextFormat.RichText)  # Use RichText for HTML formatting
        station_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        
        # Ensure no extra padding or margin
        station_label.setContentsMargins(0, 0, 0, 0)
        station_label.setStyleSheet("padding: 0px; margin: 0px;")
        
        station_font = QFont()
        station_font.setPointSize(18)
        
        # Special formatting for origin and destination
        if calling_point.is_origin or calling_point.is_destination:
            station_font.setBold(True)
        else:
            station_font.setItalic(True)
            
        station_label.setFont(station_font)
        
        # Apply styling based on station type
        self._style_station_label(station_label, calling_point)
        
        return station_label
    
    def _style_station_label(self, label: QLabel, calling_point: CallingPoint) -> None:
        """
        Apply styling to station label based on its type.
        
        Args:
            label: Label to style
            calling_point: Calling point data
        """
        # Get raw station name
        raw_name = calling_point.station_name if calling_point.station_name else ""
        
        # Check if this is an HTML-formatted station name
        is_html_formatted = "<font" in raw_name and "</font>" in raw_name
        
        # Process station name based on whether it's HTML-formatted
        if is_html_formatted:
            station_name = raw_name  # Keep HTML formatting
        else:
            station_name = raw_name.strip()
            
        colors = self.get_theme_colors(self._current_theme)
        
        # Check for walking connections
        is_walking = ("<font color='#f44336'" in station_name)
        
        is_user_interchange = self.station_filter_service.is_actual_user_journey_interchange(
            station_name
        )
        label.setStyleSheet(
            stylesheet_for_station_label(
                theme=self._current_theme,
                colors=colors,
                is_walking=is_walking,
                is_user_interchange=is_user_interchange,
                is_origin_or_destination=(
                    calling_point.is_origin or calling_point.is_destination
                ),
            )
        )
    
    def _create_direct_service_display(self) -> None:
        """Create display for direct service."""
        direct_layout = QHBoxLayout()
        direct_label = QLabel("Direct service")
        direct_font = QFont()
        direct_font.setPointSize(18)
        direct_font.setItalic(True)
        direct_label.setFont(direct_font)
        direct_layout.addWidget(direct_label)
        direct_layout.addStretch()
        self.calling_points_layout.addLayout(direct_layout)
    
    def _apply_theme_styles(self) -> None:
        """Apply theme-specific styling."""
        colors = self.get_theme_colors(self._current_theme)

        self.setStyleSheet(stylesheet_for_direct_label(self._current_theme, colors))
