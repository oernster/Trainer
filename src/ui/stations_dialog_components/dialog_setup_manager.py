"""
Dialog Setup Manager

Handles dialog setup, appearance, and basic properties.
"""

import logging
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPixmap, QPainter, QIcon, QFont
from PySide6.QtCore import Qt

logger = logging.getLogger(__name__)


class DialogSetupManager:
    """Handles dialog setup, appearance, and basic properties."""
    
    def __init__(self, dialog):
        """
        Initialize the dialog setup manager.
        
        Args:
            dialog: The parent dialog
        """
        self.dialog = dialog
    
    def setup_dialog(self):
        """Set up basic dialog properties."""
        self.dialog.setWindowTitle("Train Settings")
        self.dialog.setModal(True)
        
        # Use Linux implementation for all platforms - it works great
        # Detect small screen
        screen = QApplication.primaryScreen()
        if screen:
            screen_geometry = screen.availableGeometry()
            is_small_screen = screen_geometry.width() <= 1440 or screen_geometry.height() <= 900
        else:
            is_small_screen = False
        
        if is_small_screen:
            # Optimize for small screens - increase height for better alignment space
            self.dialog.setMinimumSize(850, 750)  # Increased height from 700 to 750
            self.dialog.resize(900, 800)  # Increased height from 750 to 800
        else:
            # Normal screens - increase height for better alignment space
            self.dialog.setMinimumSize(850, 700)  # Increased height from 650 to 700
            self.dialog.resize(950, 800)  # Increased height from 750 to 800
        
        # Center the dialog on Linux
        if sys.platform.startswith('linux'):
            self._center_on_screen()
        
        # Set custom clock icon for stations dialog
        self._setup_dialog_icon()
    
    def _setup_dialog_icon(self):
        """Setup dialog icon using Unicode alarm clock emoji."""
        try:
            # Create a pixmap for the icon
            pixmap = QPixmap(64, 64)
            pixmap.fill(Qt.GlobalColor.transparent)
            
            # Paint the emoji onto the pixmap
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # Set up font for emoji
            font = QFont()
            font.setPointSize(48)
            painter.setFont(font)
            painter.setPen(Qt.GlobalColor.black)
            
            # Draw the alarm clock emoji centered
            painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "⏰")
            painter.end()
            
            # Create icon and set it
            icon = QIcon(pixmap)
            self.dialog.setWindowIcon(icon)
            
            logger.debug("Dialog icon set using Unicode alarm clock emoji")
            
        except Exception as e:
            logger.warning(f"Failed to create emoji dialog icon: {e}")
            # Fallback to parent window icon if available
            if hasattr(self.dialog.parent_window, 'windowIcon') and self.dialog.parent_window:
                try:
                    self.dialog.setWindowIcon(self.dialog.parent_window.windowIcon())
                except:
                    pass
    
    def _center_on_screen(self):
        """Center the dialog on the primary screen."""
        screen = QApplication.primaryScreen()
        if screen:
            screen_geometry = screen.availableGeometry()
            dialog_geometry = self.dialog.frameGeometry()
            x = (screen_geometry.width() - dialog_geometry.width()) // 2
            y = (screen_geometry.height() - dialog_geometry.height()) // 2
            self.dialog.move(x, y)
            logger.debug(f"Centered stations settings dialog at ({x}, {y})")
    
    def apply_theme(self, theme_manager):
        """Apply the current theme to the dialog."""
        try:
            if not theme_manager:
                return
            
            # Apply theme to main dialog
            theme_manager.apply_theme_to_widget(self.dialog)
            
            # Apply theme to components
            if self.dialog.station_selection_widget:
                self.dialog.station_selection_widget.apply_theme(theme_manager)
            if self.dialog.route_action_buttons:
                self.dialog.route_action_buttons.apply_theme(theme_manager)
            if self.dialog.route_details_widget:
                self.dialog.route_details_widget.apply_theme(theme_manager)
            if self.dialog.preferences_widget:
                self.dialog.preferences_widget.apply_theme(theme_manager)
            
        except Exception as e:
            logger.error(f"Error applying theme: {e}")