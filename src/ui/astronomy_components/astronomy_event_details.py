"""
Astronomy Event Details

Detailed view of astronomy events for a specific day.
"""

import logging
from datetime import date
from typing import Optional
from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget
from PySide6.QtCore import Qt, Signal, QUrl
from PySide6.QtGui import QFont, QDesktopServices

from ...models.astronomy_data import AstronomyData, AstronomyEvent

from ...utils.url_utils import canonicalize_url

logger = logging.getLogger(__name__)


class AstronomyEventDetails(QFrame):
    """
    Detailed view of astronomy events for a specific day.

    Follows Single Responsibility Principle - only responsible for
    displaying detailed astronomy event information.
    """

    astronomy_link_clicked = Signal(str)

    def __init__(self, parent=None):
        """Initialize astronomy event details."""
        super().__init__(parent)
        self._astronomy_data: Optional[AstronomyData] = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Setup details layout."""
        self.setFrameStyle(QFrame.Shape.StyledPanel)
        self.setLineWidth(1)

        # Main layout
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(12, 12, 12, 12)
        self._layout.setSpacing(8)

        # Initially empty
        self._show_no_data()

    def _show_no_data(self) -> None:
        """Show message when no data is available."""
        self._clear_layout()

        label = QLabel("Select a day to view astronomy details")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("color: #888888; font-style: italic;")
        self._layout.addWidget(label)

    def _clear_layout(self) -> None:
        """Clear all widgets from layout."""
        while self._layout.count():
            child = self._layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def update_data(self, astronomy_data: AstronomyData) -> None:
        """Update details with astronomy data."""
        self._astronomy_data = astronomy_data
        self._clear_layout()

        # Track URLs shown within this details view so we don't show repeated
        # destinations when multiple events resolve to the same link.
        self._used_link_canon: set[str] = set()

        if not astronomy_data.has_events:
            self._show_no_events(astronomy_data.date)
            return

        # Date header
        date_label = QLabel(astronomy_data.date.strftime("%A, %B %d, %Y"))
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        date_label.setFont(font)
        date_label.setStyleSheet("color: #1976d2; margin-bottom: 8px;")
        self._layout.addWidget(date_label)

        # Moon phase info
        if astronomy_data.moon_phase:
            moon_widget = self._create_moon_info_widget(astronomy_data)
            self._layout.addWidget(moon_widget)

        # Events
        events = astronomy_data.get_sorted_events(by_priority=True)
        for event in events:
            event_widget = self._create_event_widget(event)
            self._layout.addWidget(event_widget)

        # Add stretch
        self._layout.addStretch()

    def _show_no_events(self, event_date: date) -> None:
        """Show message when no events are available for the date."""
        date_label = QLabel(event_date.strftime("%A, %B %d, %Y"))
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        date_label.setFont(font)
        self._layout.addWidget(date_label)

        no_events_label = QLabel("No astronomy events scheduled for this day")
        no_events_label.setStyleSheet(
            "color: #888888; font-style: italic; margin-top: 16px;"
        )
        self._layout.addWidget(no_events_label)

        self._layout.addStretch()

    def _create_moon_info_widget(self, astronomy_data: AstronomyData) -> QWidget:
        """Create moon phase information widget."""
        widget = QFrame()
        widget.setFrameStyle(QFrame.Shape.Box)
        widget.setStyleSheet(
            """
            QFrame {
                border: 1px solid #404040;
                border-radius: 6px;
                background-color: rgba(79, 195, 247, 0.05);
                padding: 8px;
            }
        """
        )

        layout = QHBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)

        # Moon icon - larger size
        moon_icon = QLabel(astronomy_data.moon_phase_icon)
        font = QFont()
        font.setPointSize(32)  # Larger moon icon in details
        moon_icon.setFont(font)
        layout.addWidget(moon_icon)

        # Moon info
        info_layout = QVBoxLayout()

        if astronomy_data.moon_phase:
            phase_name = astronomy_data.moon_phase.value.replace("_", " ").title()
        else:
            phase_name = "Unknown"
        phase_label = QLabel(f"Moon Phase: {phase_name}")
        font = QFont()
        font.setBold(True)
        phase_label.setFont(font)
        info_layout.addWidget(phase_label)

        if astronomy_data.moon_illumination is not None:
            illumination_label = QLabel(
                f"Illumination: {astronomy_data.moon_illumination:.1%}"
            )
            info_layout.addWidget(illumination_label)

        layout.addLayout(info_layout)
        layout.addStretch()

        return widget

    def _create_event_widget(self, event: AstronomyEvent) -> QWidget:
        """Create widget for a single astronomy event."""
        widget = QFrame()
        widget.setFrameStyle(QFrame.Shape.Box)

        # Style based on priority
        if event.priority.value >= 3:
            border_color = "#ff9800"  # Orange for high priority
        else:
            border_color = "#1976d2"  # Blue for normal priority

        widget.setStyleSheet(
            f"""
            QFrame {{
                border: 1px solid {border_color};
                border-radius: 6px;
                background-color: rgba(79, 195, 247, 0.03);
                padding: 8px;
                margin: 4px 0px;
            }}
        """
        )

        layout = QVBoxLayout(widget)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(6)

        # Header with icon and title
        header_layout = QHBoxLayout()

        # Event icon - larger size
        icon_label = QLabel(event.event_icon)
        font = QFont()
        font.setPointSize(26)  # Larger event icons in details
        icon_label.setFont(font)
        header_layout.addWidget(icon_label)

        # Title and time
        title_layout = QVBoxLayout()

        title_label = QLabel(event.title)
        font = QFont()
        font.setPointSize(12)
        font.setBold(True)
        title_label.setFont(font)
        title_layout.addWidget(title_label)

        time_label = QLabel(event.get_formatted_time())
        time_label.setStyleSheet("color: #888888;")
        title_layout.addWidget(time_label)

        header_layout.addLayout(title_layout)
        header_layout.addStretch()

        layout.addLayout(header_layout)

        # Description
        desc_label = QLabel(event.description)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("margin: 8px 0px;")
        layout.addWidget(desc_label)

        # Visibility info
        if event.has_visibility_info:
            visibility_label = QLabel(f"👁️ {event.visibility_info}")
            visibility_label.setStyleSheet("color: #81c784; font-style: italic;")
            layout.addWidget(visibility_label)

        # Link button for events with URLs.
        # Prefer a URL not already shown in this details panel.
        chosen_url: Optional[str] = None
        if hasattr(event, "get_link_urls"):
            for url in event.get_link_urls():
                canon = canonicalize_url(url)
                if canon and canon not in self._used_link_canon:
                    chosen_url = url
                    self._used_link_canon.add(canon)
                    break
        elif hasattr(event, "get_primary_link"):
            primary_url = event.get_primary_link()
            if primary_url:
                canon = canonicalize_url(primary_url)
                if canon and canon not in self._used_link_canon:
                    chosen_url = primary_url
                    self._used_link_canon.add(canon)

        if chosen_url:
            link_button = QPushButton("🔗 View on Astronomy Website")
            link_button.setStyleSheet(
                """
                QPushButton {
                    background-color: #1976d2;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 6px 12px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #1565c0;
                }
                QPushButton:pressed {
                    background-color: #0d47a1;
                }
            """
            )
            link_button.clicked.connect(
                lambda checked=False, url=chosen_url: self._open_astronomy_link(url)
            )
            layout.addWidget(link_button)

        return widget

    def _open_astronomy_link(self, url: str) -> None:
        """Open NASA link in browser."""
        try:
            QDesktopServices.openUrl(QUrl(url))
            self.astronomy_link_clicked.emit(url)
            logger.info(f"Opened NASA link: {url}")
        except Exception as e:
            logger.error(f"Failed to open NASA link {url}: {e}")
