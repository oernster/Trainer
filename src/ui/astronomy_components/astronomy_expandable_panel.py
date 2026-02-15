"""
Astronomy Expandable Panel

Expandable panel for detailed astronomy information.
"""

import logging
from datetime import date
from typing import Optional
from PySide6.QtWidgets import QWidget, QVBoxLayout, QFrame, QScrollArea, QLabel
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont, QCursor

from ...services.astronomy_ui_facade import AstronomyEventDTO
from .astronomy_event_details import AstronomyEventDetails

logger = logging.getLogger(__name__)


class AstronomyExpandablePanel(QWidget):
    """
    Expandable panel for detailed astronomy information.

    Follows Single Responsibility Principle - only responsible for
    managing the expandable/collapsible behavior and detailed content.
    """

    expansion_changed = Signal(bool)
    astronomy_link_clicked = Signal(str)

    def __init__(self, parent=None):
        """Initialize expandable panel."""
        super().__init__(parent)
        self._is_expanded = False
        self._forecast_data: Optional[object] = None
        self._animation: Optional[QPropertyAnimation] = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Setup expandable panel layout."""
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header with toggle button
        self._header = self._create_header()
        layout.addWidget(self._header)

        # Content area (initially hidden)
        self._content_area = QScrollArea()
        self._content_area.setWidgetResizable(True)
        self._content_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._content_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self._content_area.setMaximumHeight(0)  # Initially collapsed

        # Content widget
        self._content_widget = AstronomyEventDetails()
        self._content_widget.astronomy_link_clicked.connect(self.astronomy_link_clicked.emit)
        self._content_area.setWidget(self._content_widget)

        layout.addWidget(self._content_area)

        # Setup animation
        self._setup_animation()

    def _create_header(self) -> QWidget:
        """Create header with toggle button."""
        header = QFrame()
        header.setFrameStyle(QFrame.Shape.Box)
        header.setStyleSheet(
            """
            QFrame {
                border: 1px solid #1976d2;
                border-radius: 6px;
                background-color: rgba(25, 118, 210, 0.1);
                padding: 8px;
            }
            QFrame:hover {
                background-color: rgba(79, 195, 247, 0.2);
            }
        """
        )
        header.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        layout = QVBoxLayout(header)
        layout.setContentsMargins(12, 8, 12, 8)

        # Title
        title_label = QLabel("🌟 Astronomy Details")
        font = QFont()
        font.setPointSize(12)
        font.setBold(True)
        title_label.setFont(font)
        layout.addWidget(title_label)

        layout.addStretch()

        # Toggle indicator
        self._toggle_indicator = QLabel("▼")
        font = QFont()
        font.setPointSize(10)
        self._toggle_indicator.setFont(font)
        layout.addWidget(self._toggle_indicator)

        # Make header clickable
        header.mousePressEvent = self._on_header_clicked

        return header

    def _setup_animation(self) -> None:
        """Setup expand/collapse animation."""
        self._animation = QPropertyAnimation(self._content_area, b"maximumHeight")
        self._animation.setDuration(300)
        self._animation.setEasingCurve(QEasingCurve.Type.InOutCubic)

    def _on_header_clicked(self, event) -> None:
        """Handle header click to toggle expansion."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.toggle_expansion()

    def toggle_expansion(self) -> None:
        """Toggle panel expansion state."""
        if self._is_expanded:
            self._collapse()
        else:
            self._expand()

    def _expand(self) -> None:
        """Expand the panel."""
        if self._is_expanded:
            return

        self._is_expanded = True
        self._toggle_indicator.setText("▲")

        # Calculate target height
        content_height = self._content_widget.sizeHint().height()
        target_height = min(content_height, 400)  # Max height limit

        # Animate expansion
        if self._animation:
            self._animation.setStartValue(0)
            self._animation.setEndValue(target_height)
            self._animation.start()

        self.expansion_changed.emit(True)
        logger.debug("Astronomy panel expanded")

    def _collapse(self) -> None:
        """Collapse the panel."""
        if not self._is_expanded:
            return

        self._is_expanded = False
        self._toggle_indicator.setText("▼")

        # Animate collapse
        if self._animation:
            current_height = self._content_area.height()
            self._animation.setStartValue(current_height)
            self._animation.setEndValue(0)
            self._animation.start()

        self.expansion_changed.emit(False)
        logger.debug("Astronomy panel collapsed")

    def update_details(self, forecast_data: object) -> None:
        """Update detailed content with forecast data."""
        self._forecast_data = forecast_data

        # Show today's data by default
        today_data = (
            forecast_data.get_today_astronomy()
            if hasattr(forecast_data, "get_today_astronomy")
            else None
        )
        if today_data is not None:
            self._content_widget.update_data(today_data)
            return

        daily = getattr(forecast_data, "daily_astronomy", [])
        if daily:
            self._content_widget.update_data(daily[0])

    def show_date_details(self, target_date: date) -> None:
        """Show details for a specific date."""
        if not self._forecast_data:
            return

        astronomy_data = (
            self._forecast_data.get_astronomy_for_date(target_date)
            if self._forecast_data and hasattr(self._forecast_data, "get_astronomy_for_date")
            else None
        )
        if astronomy_data:
            self._content_widget.update_data(astronomy_data)

            # Expand if not already expanded
            if not self._is_expanded:
                self._expand()

    def is_expanded(self) -> bool:
        """Check if panel is currently expanded."""
        return self._is_expanded
