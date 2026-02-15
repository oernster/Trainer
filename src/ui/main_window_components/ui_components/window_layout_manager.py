"""
Window layout manager for the main window.

This module provides a class for managing the window layout, sizing, and positioning
of the main window, extracted from the MainWindow class.
"""

import logging
from typing import Optional, Tuple

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QApplication, QSizePolicy
)
from PySide6.QtCore import Qt

logger = logging.getLogger(__name__)


class WindowLayoutManager:
    """
    Manager for the main window layout.
    
    Handles window layout, sizing, and positioning.
    """
    
    def __init__(self, main_window: QMainWindow, config_manager):
        """
        Initialize window layout manager.
        
        Args:
            main_window: Parent main window
            config_manager: Configuration manager for accessing config
        """
        self.main_window = main_window
        self.config_manager = config_manager
        self.config = None
        
        # UI components
        self.central_widget = None
        self.main_layout = None
        
        # Screen properties
        self.is_small_screen = False
        self.ui_scale_factor = 0.85  # Default scale factor
        
        # Get screen dimensions for responsive sizing
        self._detect_screen_size()
    
    def _detect_screen_size(self) -> None:
        """Detect screen size and set scaling factors."""
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        screen_width = screen_geometry.width()
        screen_height = screen_geometry.height()
        
        # Calculate responsive window size
        # For smaller screens (like 13" laptops), scale to ~80% for better space utilization
        # For larger screens, keep full size
        self.is_small_screen = screen_width <= 1440 or screen_height <= 900
        
        # Unified scaling approach (based on proven Linux implementation)
        if self.is_small_screen:
            self.ui_scale_factor = 0.65  # 65% scale for all platforms on small screens
            logger.info(f"Small screen detected ({screen_width}x{screen_height}), using scale factor: {self.ui_scale_factor}")
        else:
            self.ui_scale_factor = 0.85  # 85% scale for all platforms on normal screens
            logger.debug(f"Large screen detected ({screen_width}x{screen_height}), using scale factor: {self.ui_scale_factor}")
    
    def setup_window_layout(self, config) -> QWidget:
        """
        Setup the main window layout.
        
        Args:
            config: Application configuration
            
        Returns:
            Central widget with configured layout
        """
        self.config = config
        
        # Determine initial widget visibility from persisted UI state
        weather_visible = True  # Default
        astronomy_visible = True  # Default
        
        if self.config and hasattr(self.config, 'ui') and self.config.ui:
            weather_visible = self.config.ui.weather_widget_visible
            astronomy_visible = self.config.ui.astronomy_widget_visible
        else:
            # Fallback: Check if astronomy is enabled to determine initial visibility
            astronomy_visible = bool(
                self.config and
                hasattr(self.config, 'astronomy') and
                self.config.astronomy and
                self.config.astronomy.enabled
            )
        
        # Get target window size from persisted config
        default_width, default_height = self._get_target_window_size(weather_visible, astronomy_visible)
        
        if self.is_small_screen:
            # Apply unified scaling for small screens (Linux approach)
            min_width = int(900 * 0.65)  # 585
            min_height = int(450 * 0.65)  # 292
            default_width = int(default_width * 0.65)
            default_height = int(default_height * 0.65)
            
            logger.info(f"Using scaled window size: {default_width}x{default_height} (weather={weather_visible}, astronomy={astronomy_visible})")
        else:
            # Set reasonable minimums for large screens (Linux approach)
            min_width = int(900 * 0.85)  # 765
            min_height = int(450 * 0.85)  # 382
            
            logger.debug(f"Using persisted window size: {default_width}x{default_height} (weather={weather_visible}, astronomy={astronomy_visible})")
        
        self.main_window.setMinimumSize(min_width, min_height)
        
        # Unified window sizing (based on proven Linux implementation)
        if self.is_small_screen:
            # Smaller default size for small screens - reduced height to fit train widgets
            self.main_window.resize(int(1100 * 0.65), int(1100 * 0.65))  # 715x715 - reduced from 780
        else:
            # Slightly reduced for normal screens
            self.main_window.resize(int(1100 * 0.85), int(1100 * 0.85))  # 935x935 - reduced from 1020
        
        # Center the window on the screen
        self.center_window()
        
        # Create central widget
        self.central_widget = QWidget()
        self.main_window.setCentralWidget(self.central_widget)
        
        # Main layout with minimal spacing for very compact UI
        self.main_layout = QVBoxLayout(self.central_widget)
        
        # Unified margins and spacing (based on proven Linux implementation)
        margin = int(4 * self.ui_scale_factor)
        self.main_layout.setContentsMargins(margin, margin, margin, margin)
        
        # Minimal spacing between widgets
        scaled_spacing = int(3 * self.ui_scale_factor)
        self.main_layout.setSpacing(scaled_spacing)
        
        return self.central_widget
    
    def add_widget_to_layout(self, widget: QWidget, stretch: int = 0) -> None:
        """
        Add a widget to the main layout.
        
        Args:
            widget: Widget to add
            stretch: Stretch factor (0 for no stretch)
        """
        if self.main_layout:
            self.main_layout.addWidget(widget, stretch)
        else:
            logger.warning("Cannot add widget to layout: no layout available")
    
    def center_window(self) -> None:
        """Center the window on the screen."""
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        window_geometry = self.main_window.frameGeometry()
        
        # Calculate center position
        center_x = screen_geometry.center().x() - window_geometry.width() // 2
        center_y = screen_geometry.center().y() - window_geometry.height() // 2
        
        # Move window to center
        self.main_window.move(center_x, center_y)
        logger.debug("Window centered on screen")
    
    def _update_window_size_for_widgets(self, weather_visible: bool, astronomy_visible: bool) -> None:
        """
        Update window size and center window based on currently visible widgets.
        
        Args:
            weather_visible: Whether weather widget is visible
            astronomy_visible: Whether astronomy widget is visible
        """
        # Get target size from persisted UI config or calculate defaults
        target_width, target_height = self._get_target_window_size(weather_visible, astronomy_visible)
        
        # Apply scaling for small screens
        if self.is_small_screen:
            target_width = int(target_width * 0.8)
            target_height = int(target_height * 0.8)
        
        # Always force resize regardless of current size
        current_height = self.main_window.height()
        current_width = self.main_window.width()
        
        # CRITICAL FIX: Temporarily remove minimum size constraint to allow ultra-aggressive shrinking
        self.main_window.setMinimumSize(0, 0)
        
        # Force resize to target size
        self.main_window.resize(target_width, target_height)
        
        # CRITICAL FIX: Restore a reasonable minimum size to prevent UI truncation
        # This ensures widgets remain usable while still allowing dynamic resizing
        min_width = 600   # Increased minimum width for better astronomy widget display
        min_height = 450  # Increased minimum height to prevent severe truncation
        self.main_window.setMinimumSize(min_width, min_height)
        
        # Center the window on screen after resizing
        self.center_window()
        
        # Log the resize with widget status
        widget_status = []
        if weather_visible:
            widget_status.append("weather")
        if astronomy_visible:
            widget_status.append("astronomy")
        if not widget_status:
            widget_status.append("trains only")
        
        logger.info(f"Window FORCED resize from {current_width}x{current_height} to {target_width}x{target_height} and recentered (visible: {', '.join(widget_status)})")
    
    def _get_target_window_size(self, weather_visible: bool, astronomy_visible: bool) -> Tuple[int, int]:
        """
        Get target window size based on widget visibility state from persisted config.
        
        Args:
            weather_visible: Whether weather widget is visible
            astronomy_visible: Whether astronomy widget is visible
            
        Returns:
            Tuple of (width, height)
        """
        if self.config and hasattr(self.config, 'ui') and self.config.ui:
            if weather_visible and astronomy_visible:
                return self.config.ui.window_size_both_visible
            elif weather_visible:
                return self.config.ui.window_size_weather_only
            elif astronomy_visible:
                return self.config.ui.window_size_astronomy_only
            else:
                return self.config.ui.window_size_trains_only
        else:
            # Fallback to default sizes if no config - properly sized for all widgets
            # Unified default sizes (based on proven Linux implementation)
            if self.is_small_screen:
                # Smaller for small screens - reduced heights to fit train widgets
                if weather_visible and astronomy_visible:
                    return (int(1100 * 0.65), int(1100 * 0.65))  # 715x715 - reduced from 780
                elif weather_visible:
                    return (int(1100 * 0.65), int(750 * 0.65))   # 715x488 - reduced from 520
                elif astronomy_visible:
                    return (int(1100 * 0.65), int(850 * 0.65))   # 715x553 - reduced from 585
                else:
                    return (int(1100 * 0.65), int(550 * 0.65))   # 715x358 - reduced from 390
            else:
                # Slightly reduced for normal screens
                if weather_visible and astronomy_visible:
                    return (int(1100 * 0.85), int(1100 * 0.85))  # 935x935 - reduced from 1020
                elif weather_visible:
                    return (int(1100 * 0.85), int(750 * 0.85))   # 935x638 - reduced from 680
                elif astronomy_visible:
                    return (int(1100 * 0.85), int(850 * 0.85))   # 935x723 - reduced from 765
                else:
                    return (int(1100 * 0.85), int(550 * 0.85))   # 935x468 - reduced from 510
    
    def save_ui_state(self, weather_visible: bool, astronomy_visible: bool) -> None:
        """
        Save current UI widget visibility states and window size to configuration.
        
        Args:
            weather_visible: Whether weather widget is visible
            astronomy_visible: Whether astronomy widget is visible
        """
        if self.config and hasattr(self.config, 'ui') and self.config.ui:
            # Update UI state in config
            self.config.ui.weather_widget_visible = weather_visible
            self.config.ui.astronomy_widget_visible = astronomy_visible
            
            # Save current window size for the current widget state
            current_size = (self.main_window.width(), self.main_window.height())
            
            if weather_visible and astronomy_visible:
                self.config.ui.window_size_both_visible = current_size
            elif weather_visible:
                self.config.ui.window_size_weather_only = current_size
            elif astronomy_visible:
                self.config.ui.window_size_astronomy_only = current_size
            else:
                self.config.ui.window_size_trains_only = current_size
            
            # Save to file
            try:
                self.config_manager.save_config(self.config)
                logger.debug(f"UI state saved: weather={weather_visible}, astronomy={astronomy_visible}, size={current_size}")
            except Exception as e:
                logger.error(f"Failed to save UI state: {e}")