"""
Astronomy Forecast Panel

Panel displaying 7-day astronomy forecast.
"""

import logging
from typing import List
from PySide6.QtWidgets import QWidget, QHBoxLayout
from PySide6.QtCore import Signal

from ...models.astronomy_data import AstronomyForecastData, AstronomyEvent
from .daily_astronomy_panel import DailyAstronomyPanel

from ...utils.astronomy_icon_allocator import assign_unique_event_icons

logger = logging.getLogger(__name__)


class AstronomyForecastPanel(QWidget):
    """
    Panel displaying 7-day astronomy forecast.

    Follows Single Responsibility Principle - only responsible for
    displaying the astronomy forecast overview.
    """

    event_icon_clicked = Signal(AstronomyEvent)

    def __init__(self, parent=None, scale_factor=1.0):
        """Initialize astronomy forecast panel."""
        super().__init__(parent)
        self._scale_factor = scale_factor
        self._daily_panels: List[DailyAstronomyPanel] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Setup forecast panel layout."""
        # Main layout - evenly distributed panels across full width
        layout = QHBoxLayout(self)
        scaled_margin = int(4 * self._scale_factor)
        layout.setContentsMargins(scaled_margin, scaled_margin, scaled_margin, scaled_margin)
        
        # Create 7 daily panels with equal distribution
        for i in range(7):
            panel = DailyAstronomyPanel(scale_factor=self._scale_factor)
            panel.event_icon_clicked.connect(self.event_icon_clicked.emit)
            self._daily_panels.append(panel)
            layout.addWidget(panel, 1)  # Equal stretch for all panels
            
            # Add minimal spacing between panels (except after the last one)
            if i < 6:
                scaled_spacing = int(2 * self._scale_factor)  # Reduced spacing
                layout.addSpacing(scaled_spacing)

    def update_forecast(self, forecast_data: AstronomyForecastData) -> None:
        """Update forecast display with new data."""
        # Compute icon overrides ensuring uniqueness across the full 7-day grid.
        # We align with the exact ordering used by each DailyAstronomyPanel
        # (sorted-by-priority, first 4 events).
        days_events = [
            day.get_sorted_events(by_priority=True)[:4]
            for day in forecast_data.daily_astronomy[:7]
        ]
        icon_overrides_by_day = assign_unique_event_icons(days_events, per_day_limit=4)

        # Update each daily panel
        for i, panel in enumerate(self._daily_panels):
            if i < len(forecast_data.daily_astronomy):
                overrides = icon_overrides_by_day[i] if i < len(icon_overrides_by_day) else None
                panel.update_data(forecast_data.daily_astronomy[i], icon_overrides=overrides)
                panel.show()
            else:
                panel.hide()

        logger.debug(
            f"Updated astronomy forecast panel with {len(forecast_data.daily_astronomy)} days"
        )
