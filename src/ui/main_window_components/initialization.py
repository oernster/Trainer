"""Main window initialization helpers.

Phase 2 directive:
  - This module may *wire* UI managers/widgets, but must not assemble the
    application/service object graph.
  - Construction of long-lived managers/services happens in
    [`python.bootstrap_app()`](src/app/bootstrap.py:71).
"""

from __future__ import annotations

import logging

from PySide6.QtCore import QTimer, Qt

from ...managers.config_manager import ConfigManager
from ...managers.config_models import ConfigData
from ...managers.initialization_manager import InitializationManager
from ...managers.theme_manager import ThemeManager
from ..managers import (
    EventHandlerManager,
    SettingsDialogManager,
    UILayoutManager,
    WidgetLifecycleManager,
)

logger = logging.getLogger(__name__)


def initialize_main_window(
    *,
    window,
    config_manager: ConfigManager,
    config: ConfigData,
    theme_manager: ThemeManager,
    initialization_manager: InitializationManager,
) -> None:
    """Populate a MainWindow instance with its UI managers and initial state.

    This function is intentionally *UI-only wiring*. It must not create
    long-lived managers/services (Weather/Astronomy/Train/etc.).
    """

    # Make window completely invisible during initialization
    window.setVisible(False)
    window.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    window.hide()  # Explicitly hide the window

    # Set a proper background color immediately to prevent white flash
    window.setStyleSheet("QMainWindow { background-color: #1a1a1a; }")

    # Additional measures to prevent visibility
    window.setWindowOpacity(0.0)  # Make completely transparent
    window.move(-10000, -10000)  # Move off-screen

    # Bootstrap owns configuration + theming.
    window.config_manager = config_manager
    window.config = config
    window.theme_manager = theme_manager

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

    # Long-lived managers are injected by bootstrap; do not overwrite them.

    # Setup theme system first to ensure proper styling from the start
    window.setup_theme_system()
    window.apply_theme()

    # Setup UI with theme already applied
    window.ui_layout_manager.setup_ui()
    window.ui_layout_manager.setup_application_icon()

    # Initialization manager is injected by bootstrap.
    window.initialization_manager = initialization_manager

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

