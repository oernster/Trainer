"""
Astronomy Widget

Main astronomy widget container.
"""

import logging
import sys
from typing import Dict, Optional
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QSizePolicy
from PySide6.QtCore import Signal, QUrl
from PySide6.QtGui import QDesktopServices

from ...services.astronomy_ui_facade import AstronomyEventDTO
from ...managers.astronomy_config import AstronomyConfig
from .astronomy_forecast_panel import AstronomyForecastPanel

from ...utils.url_utils import canonicalize_url

logger = logging.getLogger(__name__)


class AstronomyWidget(QWidget):
    """
    Main astronomy widget container.

    Follows Composite pattern - contains and coordinates multiple
    astronomy-related UI components.
    """

    astronomy_refresh_requested = Signal()
    astronomy_event_clicked = Signal(object)
    astronomy_link_clicked = Signal(str)

    def __init__(self, parent=None, scale_factor=1.0):
        """Initialize astronomy widget."""
        super().__init__(parent)
        self._scale_factor = scale_factor
        self._config: Optional[AstronomyConfig] = None
        # Tracks canonical URLs opened within the current forecast session so we
        # can avoid repeatedly opening the same destination from different events.
        self._opened_link_canon: set[str] = set()
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """Setup main astronomy widget layout."""
        # Main layout (scaled)
        layout = QVBoxLayout(self)
        scaled_margin_h = int(8 * self._scale_factor)
        scaled_margin_v = int(6 * self._scale_factor)
        scaled_spacing = int(6 * self._scale_factor)
        layout.setContentsMargins(scaled_margin_h, scaled_margin_v, scaled_margin_h, scaled_margin_v)
        layout.setSpacing(scaled_spacing)

        # Forecast panel
        self._forecast_panel = AstronomyForecastPanel(scale_factor=self._scale_factor)
        layout.addWidget(self._forecast_panel)

        # Create horizontal layout for astronomy link buttons
        self._buttons_layout = QHBoxLayout()
        self._buttons_layout.setSpacing(int(4 * self._scale_factor))
        
        # Button styling - increased font size for Linux
        if sys.platform.startswith('linux'):
            base_font_size = 24  # Significantly increased for better readability
        else:
            base_font_size = 20  # Significantly increased for better readability
        scaled_font_size = int(base_font_size * self._scale_factor)
        scaled_padding_h = int(10 * self._scale_factor)  # Increased from 8
        scaled_padding_v = int(6 * self._scale_factor)   # Increased from 4
        scaled_border_radius = int(4 * self._scale_factor)
        scaled_max_height = int(36 * self._scale_factor)  # Increased from 28
        
        button_style = f"""
            QPushButton {{
                background-color: #1976d2;
                color: white;
                border: none;
                border-radius: {scaled_border_radius}px;
                padding: {scaled_padding_v}px {scaled_padding_h}px;
                font-weight: bold;
                font-size: {scaled_font_size}px;
                max-height: {scaled_max_height}px;
            }}
            QPushButton:hover {{
                background-color: #1565c0;
            }}
            QPushButton:pressed {{
                background-color: #0d47a1;
            }}
        """
        
        # Create buttons and add them to layout immediately - always visible
        # Tonight's Sky button
        self._sky_button = QPushButton("🌌 Tonight's Sky")
        self._sky_button.setStyleSheet(button_style)
        self._sky_button.clicked.connect(self._open_night_sky_view)
        self._buttons_layout.addWidget(self._sky_button)
        
        # Observatories button
        self._observatories_button = QPushButton("🔭 Observatories")
        self._observatories_button.setStyleSheet(button_style)
        self._observatories_button.clicked.connect(self._open_observatories_view)
        self._buttons_layout.addWidget(self._observatories_button)
        
        # Space Agencies button
        self._agencies_button = QPushButton("🚀 Space Agencies")
        self._agencies_button.setStyleSheet(button_style)
        self._agencies_button.clicked.connect(self._open_space_agencies_view)
        self._buttons_layout.addWidget(self._agencies_button)
        
        # Educational Resources button
        self._educational_button = QPushButton("📚 Educational")
        self._educational_button.setStyleSheet(button_style)
        self._educational_button.clicked.connect(self._open_educational_view)
        self._buttons_layout.addWidget(self._educational_button)
        
        # Live Data Feeds button
        self._live_data_button = QPushButton("📡 Live Data")
        self._live_data_button.setStyleSheet(button_style)
        self._live_data_button.clicked.connect(self._open_live_data_view)
        self._buttons_layout.addWidget(self._live_data_button)
        
        # Community Forums button
        self._community_button = QPushButton("👥 Community")
        self._community_button.setStyleSheet(button_style)
        self._community_button.clicked.connect(self._open_community_view)
        self._buttons_layout.addWidget(self._community_button)
        
        # All buttons are created and added to layout
        
        layout.addLayout(self._buttons_layout)

        # Set size policy and minimum height to ensure all content is visible
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        # Set appropriate minimum height to show forecast panels + buttons
        min_height = int(320 * self._scale_factor)  # Reduced to proper size for forecast + buttons
        self.setMinimumHeight(min_height)
        
        # Initial button visibility will be set when config is updated
        logger.info("Astronomy buttons initialized")

    def _connect_signals(self) -> None:
        """Connect internal signals."""
        # Connect forecast panel signals
        self._forecast_panel.event_icon_clicked.connect(self._on_event_icon_clicked)

    def _on_event_icon_clicked(self, event: object) -> None:
        """Handle event icon click."""
        # Prefer the first not-yet-opened canonical URL for this event.
        candidates: list[str] = []
        if hasattr(event, "get_link_urls"):
            candidates = event.get_link_urls()
        elif hasattr(event, "get_primary_link"):
            primary_link = event.get_primary_link()
            candidates = [primary_link] if primary_link else []

        chosen_url: Optional[str] = None
        for url in candidates:
            canon = canonicalize_url(url)
            if canon and canon not in self._opened_link_canon:
                chosen_url = url
                self._opened_link_canon.add(canon)
                break

        if chosen_url:
            self._open_astronomy_link(chosen_url)
            self.astronomy_event_clicked.emit(event)
            return

        # If all event candidates are exhausted (or none exist), open a unique
        # fallback destination instead of repeatedly sending the user to the
        # same NASA page.
        fallback_url = self._get_unique_fallback_url()
        if fallback_url:
            self._open_astronomy_link(fallback_url)
            self.astronomy_event_clicked.emit(event)
            return

        # Final fallback to general NASA astronomy page
        self._open_nasa_astronomy_page()

        # Emit signal for external handling
        self.astronomy_event_clicked.emit(event)

    def _get_unique_fallback_url(self) -> Optional[str]:
        """Pick a high-quality fallback URL that hasn't been opened yet."""

        try:
            # Curated links belong to the domain layer; UI isn't allowed to
            # import them. Use a small, stable set of safe fallbacks here.
            candidates = [
                "https://science.nasa.gov/astrophysics/",
                "https://www.esa.int/Science_Exploration/Space_Science",
                "https://earthsky.org/tonight/",
                "https://stellarium.org/",
            ]
            for url in candidates:
                canon = canonicalize_url(url)
                if canon and canon not in self._opened_link_canon:
                    self._opened_link_canon.add(canon)
                    return url
        except Exception as exc:
            logger.debug(f"Failed selecting unique fallback URL: {exc}")

        return None

    def _open_night_sky_view(self) -> None:
        """Open current astronomical events page showing today's phenomena."""
        sky_url = "https://earthsky.org/tonight/"
        self._open_astronomy_link(sky_url)

    def _open_observatories_view(self) -> None:
        """Open observatories page."""
        self._open_astronomy_link("https://hubblesite.org/")

    def _open_space_agencies_view(self) -> None:
        """Open space agencies page."""
        self._open_astronomy_link("https://www.nasa.gov/")

    def _open_educational_view(self) -> None:
        """Open educational resources page."""
        self._open_astronomy_link("https://www.nasa.gov/audience/foreducators/")

    def _open_live_data_view(self) -> None:
        """Open live data feeds page."""
        self._open_astronomy_link("https://www.nasa.gov/live/")

    def _open_community_view(self) -> None:
        """Open community forums page."""
        self._open_astronomy_link("https://www.reddit.com/r/astronomy/")

    def _open_nasa_astronomy_page(self) -> None:
        """Open NASA astronomy page in browser."""
        primary_url = "https://science.nasa.gov/astrophysics/"
        self._open_astronomy_link(primary_url)

    def _open_astronomy_link(self, url: str) -> None:
        """Open NASA link in browser."""
        try:
            QDesktopServices.openUrl(QUrl(url))
            self.astronomy_link_clicked.emit(url)
            logger.info(f"Opened NASA link: {url}")
        except Exception as e:
            logger.error(f"Failed to open NASA link {url}: {e}")

    def on_astronomy_updated(self, forecast_data: object) -> None:
        """Handle astronomy data updates."""
        # New forecast means we reset opened-link tracking.
        self._opened_link_canon.clear()

        # Update forecast panel
        self._forecast_panel.update_forecast(forecast_data)



    def on_astronomy_error(self, error_message: str) -> None:
        """Handle astronomy error."""
        logger.warning(f"Astronomy error in widget: {error_message}")
        # Could show error state in UI

    def on_astronomy_loading(self, is_loading: bool) -> None:
        """Handle astronomy loading state change."""
        # Could show loading indicator
        logger.debug(f"Astronomy loading state: {is_loading}")

    def update_config(self, config: AstronomyConfig) -> None:
        """Update astronomy configuration."""
        old_config = self._config
        self._config = config

        # Don't automatically show the widget here - let the main window control visibility
        # based on whether it's properly added to the layout with data
        # self.setVisible(config.enabled and config.display.show_in_forecast)
        
        # Update button visibility based on enabled link categories
        self._update_link_buttons_visibility()
        
        # API-free mode - always ready for data when enabled
        if config.enabled:
            logger.debug("Astronomy widget enabled in config")

        logger.debug("Astronomy widget configuration updated")
    
    def _update_link_buttons_visibility(self) -> None:
        """Update visibility of link buttons based on enabled categories."""
        if not self._config:
            return
            
        enabled_categories = self._config.enabled_link_categories
        
        # Update button visibility based on enabled categories
        self._sky_button.setVisible("tonight_sky" in enabled_categories)
        self._observatories_button.setVisible("observatory" in enabled_categories)
        self._agencies_button.setVisible("space_agency" in enabled_categories)
        self._educational_button.setVisible("educational" in enabled_categories)
        self._live_data_button.setVisible("live_data" in enabled_categories)
        self._community_button.setVisible("community" in enabled_categories)
        
        logger.debug(f"Updated astronomy button visibility: {enabled_categories}")

    def apply_theme(self, theme_colors: Dict[str, str]) -> None:
        """Apply theme colors to astronomy widget."""
        # Apply theme to the widget with absolutely no borders or frames
        self.setStyleSheet(
            f"""
            AstronomyWidget {{
                background-color: {theme_colors.get('background_primary', '#1a1a1a')};
                color: {theme_colors.get('text_primary', '#ffffff')};
                border: none;
                border-radius: 0px;
                margin: 0px;
                padding: 0px;
            }}
            AstronomyWidget QWidget {{
                border: none;
                margin: 0px;
                padding: 0px;
            }}
            AstronomyWidget QFrame {{
                border: none;
                margin: 0px;
                padding: 0px;
            }}
        """
        )

        logger.debug("Applied theme to astronomy widget")
