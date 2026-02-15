"""
Main window components package.

This package contains the refactored components of the main window,
following the Single Responsibility Principle to improve maintainability.
"""

# UI Components
from .ui_components.menu_bar_manager import MenuBarManager
from .ui_components.header_buttons_manager import HeaderButtonsManager
from .ui_components.window_layout_manager import WindowLayoutManager
from .ui_components.theme_applier import ThemeApplier

# Feature Managers
from .feature_managers.weather_system_manager import WeatherSystemManager
from .feature_managers.astronomy_system_manager import AstronomySystemManager
from .feature_managers.train_display_manager import TrainDisplayManager

# Dialog Handlers
from .dialog_handlers.dialog_manager import DialogManager

# Event Handlers
from .event_handlers.window_event_handler import WindowEventHandler
from .event_handlers.signal_connection_manager import SignalConnectionManager

__all__ = [
    # UI Components
    'MenuBarManager',
    'HeaderButtonsManager',
    'WindowLayoutManager',
    'ThemeApplier',
    
    # Feature Managers
    'WeatherSystemManager',
    'AstronomySystemManager',
    'TrainDisplayManager',
    
    # Dialog Handlers
    'DialogManager',
    
    # Event Handlers
    'WindowEventHandler',
    'SignalConnectionManager',
]