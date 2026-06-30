"""
Splash screen for the Trainer application.
Author: Oliver Ernster

This module provides a splash screen that displays while the application is loading.
"""

import logging
import sys
from pathlib import Path
from PySide6.QtWidgets import QSplashScreen, QLabel, QVBoxLayout, QWidget, QApplication
from PySide6.QtCore import Qt, QTimer, QPoint
from PySide6.QtGui import QPixmap, QPainter, QFont

from src.utils.icon_resolver import get_app_icon_png_path, get_app_icon_path

logger = logging.getLogger(__name__)

# Splash dimensions and icon badge size, in device-independent pixels.
SPLASH_WIDTH = 400
SPLASH_HEIGHT = 300
SPLASH_ICON_PX = 96


class TrainerSplashScreen(QSplashScreen):
    """
    Custom splash screen for the Trainer application.

    Shows the application icon and loading text while the application initializes.
    """

    def __init__(self):
        """Initialize the splash screen."""
        # Build the base pixmap at the screen's device pixel ratio so the splash
        # and its icon render at the correct physical size, and stay crisp, on
        # high-DPI displays such as macOS Retina and fractional-scaled Linux.
        screen = QApplication.primaryScreen()
        self._dpr = screen.devicePixelRatio() if screen else 1.0
        pixmap = QPixmap(round(SPLASH_WIDTH * self._dpr), round(SPLASH_HEIGHT * self._dpr))
        pixmap.setDevicePixelRatio(self._dpr)
        pixmap.fill(Qt.GlobalColor.transparent)

        super().__init__(pixmap, Qt.WindowType.WindowStaysOnTopHint)

        # Set window properties
        self.setWindowFlags(
            Qt.WindowType.SplashScreen
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.FramelessWindowHint
        )

        # Setup the UI
        self.setup_ui()

        # Apply dark theme styling
        self.apply_styling()

        # Load the real application icon for the splash badge.
        self._icon_pixmap = self._load_icon_pixmap()

        # Center the splash screen on Linux
        if sys.platform.startswith('linux'):
            self._center_on_screen()

        logger.debug("Splash screen initialized")
    
    def _center_on_screen(self):
        """Center the splash screen on the primary screen."""
        screen = QApplication.primaryScreen()
        if screen:
            screen_geometry = screen.availableGeometry()
            x = (screen_geometry.width() - self.width()) // 2
            y = (screen_geometry.height() - self.height()) // 2
            self.move(x, y)
            logger.debug(f"Centered splash screen at ({x}, {y})")

    def setup_ui(self):
        """Setup the splash screen UI."""
        # Initialize loading message
        self.loading_message = "Loading..."


    def apply_styling(self):
        """Apply dark theme styling to the splash screen."""
        # Styling is now handled in paintEvent - no widget styling needed
        pass

    def _load_icon_pixmap(self):
        """Load the application icon as a scaled, DPI-aware pixmap, or None."""
        # Pick a source PNG large enough for the device-pixel target so the icon
        # is downscaled (crisp), not upscaled, on high-DPI displays.
        target = round(SPLASH_ICON_PX * self._dpr)
        icon_path = get_app_icon_png_path(target) or get_app_icon_path()
        if icon_path is None:
            return None
        pixmap = QPixmap(str(icon_path))
        if pixmap.isNull():
            return None
        scaled = pixmap.scaled(
            target,
            target,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        scaled.setDevicePixelRatio(self._dpr)
        return scaled

    def paintEvent(self, event):
        """Custom paint event to draw the splash screen content."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Fill background
        painter.fillRect(self.rect(), Qt.GlobalColor.black)
        
        # Draw border
        painter.setPen(Qt.GlobalColor.blue)
        painter.drawRect(self.rect().adjusted(1, 1, -1, -1))
        
        # Calculate center position for main content
        center_y = self.rect().height() // 2
        
        # Draw the application icon centered, falling back to a glyph if missing
        icon_rect = self.rect().adjusted(0, center_y - 90, 0, center_y - 40)
        if self._icon_pixmap is not None and not self._icon_pixmap.isNull():
            center = icon_rect.center()
            # The pixmap carries a device pixel ratio, so its on-screen size is
            # the device-independent size; centre using that, not the raw pixels.
            logical_w = self._icon_pixmap.width() / self._icon_pixmap.devicePixelRatio()
            logical_h = self._icon_pixmap.height() / self._icon_pixmap.devicePixelRatio()
            painter.drawPixmap(
                int(center.x() - logical_w / 2),
                int(center.y() - logical_h / 2),
                self._icon_pixmap,
            )
        else:
            painter.setPen(Qt.GlobalColor.white)
            emoji_font = QFont()
            emoji_font.setPointSize(48)
            painter.setFont(emoji_font)
            painter.drawText(icon_rect, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, "🚂")
        
        # Draw title below emoji with more spacing
        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setBold(True)
        painter.setFont(title_font)
        title_rect = self.rect().adjusted(0, center_y - 10, 0, center_y + 20)
        painter.drawText(title_rect, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, "Trainer")
        
        # Draw subtitle below title
        subtitle_font = QFont()
        subtitle_font.setPointSize(12)
        painter.setFont(subtitle_font)
        subtitle_rect = self.rect().adjusted(0, center_y + 30, 0, center_y + 60)
        painter.drawText(subtitle_rect, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, "Train Times Application")
        
        # Draw loading message at bottom
        loading_font = QFont()
        loading_font.setPointSize(10)
        painter.setFont(loading_font)
        loading_rect = self.rect().adjusted(0, 0, 0, -20)
        painter.drawText(loading_rect, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom, self.loading_message)
        
        painter.end()

    def show_message(self, message: str):
        """
        Update the loading message.

        Args:
            message: The message to display
        """
        self.loading_message = message
        self.repaint()  # Force immediate repaint
        logger.debug(f"Splash screen message: {message}")

    def close_splash(self):
        """Close the splash screen."""
        logger.info("Closing splash screen")
        self.close()


