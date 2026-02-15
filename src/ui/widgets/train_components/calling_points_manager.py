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
        # Get raw station names
        raw_curr = calling_points[index].station_name if calling_points[index].station_name else ""
        raw_prev = calling_points[index-1].station_name if calling_points[index-1].station_name else ""
        
        # Check if these are HTML-formatted station names
        is_curr_html = "<font" in raw_curr and "</font>" in raw_curr
        is_prev_html = "<font" in raw_prev and "</font>" in raw_prev
        
        # Process station names based on whether they're HTML-formatted
        if is_curr_html:
            station_name = raw_curr  # Keep HTML formatting
        else:
            station_name = raw_curr.strip()
            
        if is_prev_html:
            prev_station = raw_prev  # Keep HTML formatting
        else:
            prev_station = raw_prev.strip()
        
        # Check for walking connections in segments
        is_walking_connection = False
        walking_info = ""
        
        if self.train_data and hasattr(self.train_data, 'route_segments') and self.train_data.route_segments:
            for segment in self.train_data.route_segments:
                # Get raw segment station names
                raw_from = getattr(segment, 'from_station', '')
                raw_to = getattr(segment, 'to_station', '')
                
                # Check if these are HTML-formatted station names
                is_from_html = "<font" in raw_from and "</font>" in raw_from
                is_to_html = "<font" in raw_to and "</font>" in raw_to
                
                # Process segment station names based on whether they're HTML-formatted
                if is_from_html:
                    segment_from = raw_from  # Keep HTML formatting
                else:
                    segment_from = raw_from.strip()
                    
                if is_to_html:
                    segment_to = raw_to  # Keep HTML formatting
                else:
                    segment_to = raw_to.strip()
                
                # Compare station names, considering HTML formatting
                from_matches_prev = segment_from == prev_station
                from_matches_curr = segment_from == station_name
                to_matches_prev = segment_to == prev_station
                to_matches_curr = segment_to == station_name
                
                connects_stations = (from_matches_prev and to_matches_curr) or (from_matches_curr and to_matches_prev)
                
                if connects_stations:
                    line_name = getattr(segment, 'line_name', '')
                    service_pattern = getattr(segment, 'service_pattern', '') if hasattr(segment, 'service_pattern') else ''
                    
                    # Check for Underground black box segments
                    is_underground_segment = self.underground_formatter.is_underground_segment(segment)
                    
                    # Detect walking segments
                    is_walking_segment = (line_name == 'WALKING' or service_pattern == 'WALKING')
                    
                    # Show walking if this is explicitly a walking segment
                    if is_walking_segment:
                        is_walking_connection = True
                        walking_distance = getattr(segment, 'distance_km', None)
                        walking_time = getattr(segment, 'journey_time_minutes', None)
                        
                        if walking_distance and walking_time:
                            walking_info = f"Walk {walking_distance:.1f}km ({walking_time}min)"
                        elif walking_distance:
                            walking_info = f"Walk {walking_distance:.1f}km"
                        else:
                            walking_info = "Walking connection"
                        break
        
        # Create appropriate arrow with crash protection
        if is_walking_connection and walking_info:
            # Use plain text for walking connections to avoid Qt HTML rendering crashes
            # Use consistent spacing on either side of the arrow
            arrow_text = f"  → {walking_info} →  "
            
            # Create the arrow label with fixed-width spaces to ensure consistency
            arrow_label = QLabel(arrow_text)
            
            # Ensure the label doesn't get truncated
            arrow_label.setWordWrap(False)
            arrow_label.setTextFormat(Qt.TextFormat.PlainText)  # Use plain text to avoid HTML interpretation
            
            # Apply red color via stylesheet instead of HTML with explicit padding
            arrow_label.setStyleSheet(f"""
                QLabel {{
                    background-color: transparent;
                    color: #f44336;
                    border: none;
                    margin: 0px;
                    padding-left: 4px;
                    padding-right: 4px;
                }}
            """)
        else:
            # Check if this is an Underground segment
            is_underground_connection = False
            underground_info = ""
            
            if self.train_data and hasattr(self.train_data, 'route_segments') and self.train_data.route_segments:
                for segment in self.train_data.route_segments:
                    # Get raw segment station names
                    raw_from = getattr(segment, 'from_station', '')
                    raw_to = getattr(segment, 'to_station', '')
                    
                    # Check if these are HTML-formatted station names
                    is_from_html = "<font" in raw_from and "</font>" in raw_from
                    is_to_html = "<font" in raw_to and "</font>" in raw_to
                    
                    # Process segment station names based on whether they're HTML-formatted
                    if is_from_html:
                        segment_from = raw_from  # Keep HTML formatting
                    else:
                        segment_from = raw_from.strip()
                        
                    if is_to_html:
                        segment_to = raw_to  # Keep HTML formatting
                    else:
                        segment_to = raw_to.strip()
                    
                    # Compare station names, considering HTML formatting
                    from_matches_prev = segment_from == prev_station
                    from_matches_curr = segment_from == station_name
                    to_matches_prev = segment_to == prev_station
                    to_matches_curr = segment_to == station_name
                    
                    connects_stations = (from_matches_prev and to_matches_curr) or (from_matches_curr and to_matches_prev)
                    
                    if connects_stations and self.underground_formatter.is_underground_segment(segment):
                        is_underground_connection = True
                        # Get system-specific information
                        system_info = self.underground_formatter.get_underground_system_info(segment)
                        system_name = system_info.get("short_name", "Underground")
                        time_range = system_info.get("time_range", "10-40min")
                        emoji = system_info.get("emoji", "🚇")
                        underground_info = f"{emoji} {system_name} ({time_range})"
                        break
            
            if is_underground_connection:
                # Always use red for underground connections, but show system-specific info with emoji
                # Use consistent spacing on either side of the arrow
                arrow_text = f"  → {underground_info} →  "
                
                # Create the arrow label with fixed-width spaces to ensure consistency
                arrow_label = QLabel(arrow_text)
                
                # Ensure the label doesn't get truncated
                arrow_label.setWordWrap(False)
                arrow_label.setTextFormat(Qt.TextFormat.PlainText)  # Use plain text to avoid HTML interpretation
                
                # Apply styling with explicit padding
                arrow_label.setStyleSheet(f"""
                    QLabel {{
                        background-color: transparent;
                        color: #DC241F;
                        border: none;
                        margin: 0px;
                        padding-left: 4px;
                        padding-right: 4px;
                        font-weight: bold;
                    }}
                """)
            else:
                # Use consistent spacing on either side of the arrow
                arrow_text = "  →  "  # Added extra spaces on both sides
                
                # Create the arrow label with fixed-width spaces to ensure consistency
                arrow_label = QLabel(arrow_text)
                
                # Ensure the label doesn't get truncated
                arrow_label.setWordWrap(False)
                arrow_label.setTextFormat(Qt.TextFormat.PlainText)  # Use plain text to avoid HTML interpretation
                
                # Apply consistent styling with explicit padding
                colors = self.get_theme_colors(self._current_theme)
                arrow_label.setStyleSheet(f"""
                    QLabel {{
                        background-color: transparent;
                        color: {colors['primary_accent']};
                        border: none;
                        margin: 0px;
                        padding-left: 4px;
                        padding-right: 4px;
                    }}
                """)
                
                # Set a fixed width for the arrow to ensure consistent spacing
                arrow_label.setFixedWidth(50)
        
        arrow_font = QFont()
        arrow_font.setPointSize(15)  # Reduced font size
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
        
        if not is_walking:
            if self.station_filter_service.is_actual_user_journey_interchange(station_name):
                # Use orange/yellow ONLY for stations where user actually changes trains
                interchange_color = colors["warning"]
                label.setStyleSheet(f"""
                    QLabel {{
                        background-color: transparent !important;
                        color: {interchange_color} !important;
                        border: none !important;
                        margin: 0px !important;
                        padding: 0px !important;
                    }}
                """)
            elif calling_point.is_origin or calling_point.is_destination:
                # FORCE light blue for From and To stations in light mode for visibility
                if self._current_theme == "light":
                    label.setStyleSheet(f"""
                        QLabel {{
                            background-color: transparent !important;
                            color: #1976d2 !important;
                            border: none !important;
                            margin: 0px !important;
                            padding: 0px !important;
                        }}
                    """)
                else:
                    # Dark mode: use normal text color
                    label.setStyleSheet(f"""
                        QLabel {{
                            background-color: transparent !important;
                            color: {colors['text_primary']} !important;
                            border: none !important;
                            margin: 0px !important;
                            padding: 0px !important;
                        }}
                    """)
            else:
                # Regular light blue text for normal intermediate stations
                label.setStyleSheet(f"""
                    QLabel {{
                        background-color: transparent !important;
                        color: {colors['primary_accent']} !important;
                        border: none !important;
                        margin: 0px !important;
                        padding: 0px !important;
                    }}
                """)
        else:
            # For walking connections, preserve HTML formatting
            label.setStyleSheet("""
                QLabel {
                    background-color: transparent !important;
                    border: none !important;
                    margin: 0px !important;
                    padding: 0px !important;
                }
            """)
    
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