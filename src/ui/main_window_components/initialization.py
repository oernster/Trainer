"""Main window initialization helpers."""

from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import QTimer, Qt

from ...managers.astronomy_manager import AstronomyManager
from ...managers.config_manager import ConfigManager
from ...managers.config_models import ConfigurationError
from ...managers.initialization_manager import InitializationManager
from ...managers.theme_manager import ThemeManager
from ...managers.train_manager import TrainManager
from ...managers.weather_manager import WeatherManager
from ..managers import (
    EventHandlerManager,
    SettingsDialogManager,
    UILayoutManager,
    WidgetLifecycleManager,
)

logger = logging.getLogger(__name__)


def initialize_main_window(*, window, config_manager: Optional[ConfigManager] = None) -> None:
    """Populate a MainWindow instance with its managers and initial state."""

    # Make window completely invisible during initialization
    window.setVisible(False)
    window.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    window.hide()  # Explicitly hide the window

    # Set a proper background color immediately to prevent white flash
    window.setStyleSheet("QMainWindow { background-color: #1a1a1a; }")

    # Additional measures to prevent visibility
    window.setWindowOpacity(0.0)  # Make completely transparent
    window.move(-10000, -10000)  # Move off-screen

    # Initialize core managers
    window.config_manager = config_manager or ConfigManager()
    window.theme_manager = ThemeManager()

    # Install default config to AppData on first run
    window.config_manager.install_default_config_to_appdata()

    # Load configuration
    try:
        window.config = window.config_manager.load_config()
        # Set theme from config (defaults to dark)
        window.theme_manager.set_theme(window.config.display.theme)
    except ConfigurationError as exc:
        logger.error("Configuration error: %s", exc)
        window.show_error_message("Configuration Error", str(exc))
        # Use default config
        window.config = None

    # Initialize UI manager classes
    window.ui_layout_manager = UILayoutManager(window)
    window.widget_lifecycle_manager = WidgetLifecycleManager(window)
    window.event_handler_manager = EventHandlerManager(window)
    window.settings_dialog_manager = SettingsDialogManager(window)

    # Set up manager cross-references
    window.widget_lifecycle_manager.set_ui_layout_manager(window.ui_layout_manager)
    window.event_handler_manager.set_managers(
        window.ui_layout_manager,
        window.widget_lifecycle_manager,
    )
    window.settings_dialog_manager.set_managers(
        window.ui_layout_manager,
        window.widget_lifecycle_manager,
    )

    # External managers (will be set by main.py)
    window.weather_manager: Optional[WeatherManager] = None
    window.astronomy_manager: Optional[AstronomyManager] = None
    window.initialization_manager: Optional[InitializationManager] = None
    window.train_manager: Optional[TrainManager] = None

    # Setup theme system first to ensure proper styling from the start
    window.setup_theme_system()
    window.apply_theme()

    # Setup UI with theme already applied
    window.ui_layout_manager.setup_ui()
    window.ui_layout_manager.setup_application_icon()

    # Initialize the optimized initialization manager
    window.initialization_manager = InitializationManager(window.config_manager, window)

    # Connect initialization signals
    window.initialization_manager.initialization_completed.connect(
        window._on_initialization_completed
    )

    # Apply theme to all widgets after creation
    window.apply_theme_to_all_widgets()
    window.connect_signals()

    # Start optimized widget initialization
    QTimer.singleShot(50, window._start_optimized_initialization)

    logger.debug("Main window initialized with manager architecture")
    logger.debug("Main window initialized but kept invisible until ready")

