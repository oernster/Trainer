"""
Base component for train widget components.

This module provides a base class for all train widget components,
ensuring consistent theming and behavior.
"""

import logging
from typing import Dict, Optional
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt

logger = logging.getLogger(__name__)


class BaseTrainComponent(QWidget):
    """
    Base class for all train widget components.
    
    Provides common functionality for theming and styling.
    """
    
    def __init__(self, parent=None):
        """Initialize base train component."""
        super().__init__(parent)
        self._theme_colors: Dict[str, str] = {}
        self._current_theme = "dark"  # Default theme
    
    def get_theme_colors(self, theme: str) -> Dict[str, str]:
        """
        Get color palette for the current theme.
        
        Args:
            theme: Current theme ("dark" or "light")
            
        Returns:
            Dictionary of colors for the theme
        """
        if theme == "light":
            return {
                "background_primary": "#ffffff",
                "background_secondary": "#f5f5f5",
                "background_hover": "#e3f2fd",
                "text_primary": "#212121",
                "text_secondary": "#757575",
                "border_primary": "#e0e0e0",
                "primary_accent": "#1976d2",
                "secondary_accent": "#03a9f4",
                "warning": "#ff9800",
                "error": "#f44336",
                "success": "#4caf50"
            }
        else:
            # Dark theme colors
            return {
                "background_primary": "#121212",
                "background_secondary": "#1e1e1e",
                "background_hover": "#2c2c2c",
                "text_primary": "#ffffff",
                "text_secondary": "#b0b0b0",
                "border_primary": "#333333",
                "primary_accent": "#90caf9",
                "secondary_accent": "#4fc3f7",
                "warning": "#ffb74d",
                "error": "#e57373",
                "success": "#81c784"
            }
    
    def apply_theme(self, theme: str) -> None:
        """
        Apply theme to the component.
        
        Args:
            theme: Theme to apply ("dark" or "light")
        """
        self._current_theme = theme
        self._theme_colors = self.get_theme_colors(theme)
        self._apply_theme_styles()
    
    def _apply_theme_styles(self) -> None:
        """Apply theme-specific styling. Override in subclasses."""
        pass
    
    def _make_log_safe(self, text: str) -> str:
        """
        Make text safe for logging by replacing problematic Unicode characters.
        
        Args:
            text: The text to make safe for logging
            
        Returns:
            A version of the text that is safe for logging
        """
        if not text:
            return ""
            
        # Replace common problematic Unicode characters
        replacements = {
            '🚇': '[subway]',
            '→': '->',
            '♿': '[wheelchair]',
            '📍': '[pin]',
            '🏁': '[flag]',
            '🗺️': '[map]'
        }
        
        result = text
        for char, replacement in replacements.items():
            result = result.replace(char, replacement)
            
        return result