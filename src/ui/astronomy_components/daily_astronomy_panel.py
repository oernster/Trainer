"""
Daily Astronomy Panel

Panel displaying astronomy events for a single day.
"""

import logging
import sys
from typing import List, Optional
from PySide6.QtWidgets import QFrame, QVBoxLayout, QGridLayout, QWidget, QLabel, QSizePolicy
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from ...services.astronomy_ui_facade import AstronomyEventDTO
from .astronomy_event_icon import AstronomyEventIcon

logger = logging.getLogger(__name__)


class DailyAstronomyPanel(QFrame):
    """
    Panel displaying astronomy events for a single day.

    Follows Single Responsibility Principle - only responsible for
    displaying daily astronomy information.
    """

    event_icon_clicked = Signal(object)

    def __init__(self, parent=None, scale_factor=1.0):
        """Initialize daily astronomy panel."""
        super().__init__(parent)
        self._scale_factor = scale_factor
        self._astronomy_data: Optional[object] = None
        self._event_icons: List[AstronomyEventIcon] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Setup panel layout."""
        self.setFrameStyle(QFrame.Shape.NoFrame)  # Remove frame to eliminate dark bars
        self.setLineWidth(0)

        # Main layout (scaled)
        layout = QVBoxLayout(self)
        scaled_margin_h = int(4 * self._scale_factor)
        scaled_margin_v = int(6 * self._scale_factor)
        scaled_spacing = int(4 * self._scale_factor)
        layout.setContentsMargins(scaled_margin_h, scaled_margin_v, scaled_margin_h, scaled_margin_v)
        layout.setSpacing(scaled_spacing)

        # Date label - ensure no background styling (scaled)
        self._date_label = QLabel()
        self._date_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._date_label.setStyleSheet("background: transparent; border: none;")
        font = QFont()
        scaled_font_size = int(10 * self._scale_factor)
        font.setPointSize(scaled_font_size)
        font.setBold(True)
        self._date_label.setFont(font)
        layout.addWidget(self._date_label)

        # Icons container - 2x2 grid layout for better space utilization (scaled)
        self._icons_widget = QWidget()
        self._icons_widget.setStyleSheet("background: transparent; border: none;")
        self._icons_layout = QGridLayout(self._icons_widget)  # Changed from QHBoxLayout to QGridLayout
        scaled_icon_margin_h = int(2 * self._scale_factor)
        scaled_icon_margin_v = int(4 * self._scale_factor)
        scaled_icon_spacing = int(3 * self._scale_factor)
        self._icons_layout.setContentsMargins(scaled_icon_margin_h, scaled_icon_margin_v, scaled_icon_margin_h, scaled_icon_margin_v)
        self._icons_layout.setSpacing(scaled_icon_spacing)
        
        # Configure grid for 2x2 layout with equal spacing
        self._icons_layout.setColumnStretch(0, 1)
        self._icons_layout.setColumnStretch(1, 1)
        self._icons_layout.setRowStretch(0, 1)
        self._icons_layout.setRowStretch(1, 1)
        
        layout.addWidget(self._icons_widget)

        # Moon phase label - ensure no background styling, increased size for Linux (scaled)
        self._moon_label = QLabel()
        self._moon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Use larger moon icon size for Linux
        if sys.platform.startswith('linux'):
            base_moon_size = 32 if self._scale_factor < 1.0 else 40
        else:
            base_moon_size = 24 if self._scale_factor < 1.0 else 32
        scaled_moon_size = int(base_moon_size * self._scale_factor)
        self._moon_label.setStyleSheet(
            f"background: transparent; border: none; font-size: {scaled_moon_size}px; font-family: 'Apple Color Emoji';"
        )
        layout.addWidget(self._moon_label)

        # Set size policy - expanding width, fixed height for better distribution
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        base_height = 200 if self._scale_factor < 1.0 else 240  # Significantly increased for 2x2 emoji layout
        base_min_width = 100 if self._scale_factor < 1.0 else 120  # Minimum width
        scaled_height = int(base_height * self._scale_factor)
        scaled_min_width = int(base_min_width * self._scale_factor)
        self.setFixedHeight(scaled_height)
        self.setMinimumWidth(scaled_min_width)

    def update_data(self, astronomy_data: object, icon_overrides: list[str] | None = None) -> None:
        """Update panel with astronomy data."""
        self._astronomy_data = astronomy_data

        # Update date label
        date_value = getattr(astronomy_data, "date", None)
        if date_value is not None and hasattr(date_value, "strftime"):
            self._date_label.setText(date_value.strftime("%a\n%d"))
        else:
            self._date_label.setText("")

        # Clear existing icons
        self._clear_icons()

        # Add event icons (up to 4 for 2x2 grid)
        if hasattr(astronomy_data, "get_sorted_events"):
            events_to_show = astronomy_data.get_sorted_events(by_priority=True)[:4]
        else:
            events_to_show = []

        for i, event in enumerate(events_to_show):
            override = icon_overrides[i] if icon_overrides and i < len(icon_overrides) else None
            icon = AstronomyEventIcon(
                event,
                scale_factor=self._scale_factor,
                icon_override=override,
            )
            icon.event_clicked.connect(self.event_icon_clicked.emit)
            self._event_icons.append(icon)
            
            # Calculate grid position (2x2 layout)
            row = i // 2  # 0 or 1
            col = i % 2   # 0 or 1
            self._icons_layout.addWidget(icon, row, col)

        # Update moon phase
        self._moon_label.setText(getattr(astronomy_data, "moon_phase_icon", ""))

        # Update styling based on event priority
        self._update_styling()

    def _clear_icons(self) -> None:
        """Clear all event icons."""
        for icon in self._event_icons:
            icon.deleteLater()
        self._event_icons.clear()

    def _update_styling(self) -> None:
        """Update panel styling based on content."""
        if not self._astronomy_data:
            return

        if self._astronomy_data.has_high_priority_events:
            # High priority events - highlight border
            self.setStyleSheet(
                """
                DailyAstronomyPanel {
                    border: 2px solid #ff9800;
                    border-radius: 12px;
                    background-color: rgba(255, 152, 0, 0.1);
                }
            """
            )
        elif self._astronomy_data.has_events:
            # Regular events - subtle border
            self.setStyleSheet(
                """
                DailyAstronomyPanel {
                    border: 1px solid #1976d2;
                    border-radius: 12px;
                    background-color: rgba(25, 118, 210, 0.05);
                }
            """
            )
        else:
            # No events - minimal styling
            self.setStyleSheet(
                """
                DailyAstronomyPanel {
                    border: 1px solid #404040;
                    border-radius: 12px;
                    background-color: transparent;
                }
            """
            )
