"""
Astronomy Event Icon

Clickable astronomy event icon widget.
"""

import logging
import sys
from PySide6.QtWidgets import QLabel, QSizePolicy
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor

from ...models.astronomy_data import AstronomyEvent

logger = logging.getLogger(__name__)


class AstronomyEventIcon(QLabel):
    """
    Clickable astronomy event icon widget.

    Follows Single Responsibility Principle - only responsible for
    displaying and handling clicks on astronomy event icons.
    """

    event_clicked = Signal(AstronomyEvent)

    def __init__(
        self,
        event: AstronomyEvent,
        parent=None,
        scale_factor=1.0,
        icon_override: str | None = None,
    ):
        """Initialize astronomy event icon."""
        super().__init__(parent)
        self._event = event
        self._scale_factor = scale_factor
        self._icon_override = icon_override
        self._setup_ui()
        self._setup_interactions()

    def _setup_ui(self) -> None:
        """Setup icon appearance."""
        # Set icon text
        icon_text = self._icon_override or self._event.event_icon
        self.setText(icon_text)

        # Font size will be set in _setup_interactions method

        # Set alignment
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Set size policy - smaller container to prevent truncation (scaled)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        if self._scale_factor < 1.0:  # Small screens - reasonable size
            base_size = 50  # Reduced from 70
        else:  # Large screens
            base_size = 60  # Reduced from 100
        scaled_size = int(base_size * self._scale_factor)
        self.setFixedSize(scaled_size, scaled_size)

        # Set tooltip
        tooltip = f"{self._event.title}\n{self._event.get_formatted_time()}"
        if self._event.has_visibility_info:
            tooltip += f"\n{self._event.visibility_info}"
        self.setToolTip(tooltip)

        # Set cursor
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

    def _setup_interactions(self) -> None:
        """Setup mouse interactions."""
        # Get current font size from the existing style (scaled) - increased for Linux
        if sys.platform.startswith('linux'):
            # Larger sizes for Linux
            if self._scale_factor < 1.0:  # Small screens
                base_font_size = 36 if self._event.priority.value >= 3 else 32
            else:  # Large screens
                base_font_size = 48 if self._event.priority.value >= 3 else 44
        else:
            # Original sizes for Windows/Mac
            if self._scale_factor < 1.0:  # Small screens
                base_font_size = 28 if self._event.priority.value >= 3 else 24
            else:  # Large screens
                base_font_size = 40 if self._event.priority.value >= 3 else 36
        scaled_font_size = int(base_font_size * self._scale_factor)
        font_size = f"{scaled_font_size}px"
        
        scaled_border_radius = int(4 * self._scale_factor)
        scaled_padding = int(2 * self._scale_factor)

        self.setStyleSheet(
            f"""
            AstronomyEventIcon {{
                border: 1px solid transparent;
                border-radius: {scaled_border_radius}px;
                padding: {scaled_padding}px;
                font-size: {font_size};
                font-family: 'Apple Color Emoji';
            }}
            AstronomyEventIcon:hover {{
                border: 1px solid #1976d2;
                background-color: rgba(25, 118, 210, 0.1);
                font-size: {font_size};
                font-family: 'Apple Color Emoji';
            }}
        """
        )

    def mousePressEvent(self, event):
        """Handle mouse press events."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.event_clicked.emit(self._event)
            logger.debug(f"Astronomy event icon clicked: {self._event.title}")
        super().mousePressEvent(event)

    def get_event(self) -> AstronomyEvent:
        """Get the associated astronomy event."""
        return self._event
