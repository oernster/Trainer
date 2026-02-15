"""Application bootstrap (composition root).

Phase 2 directive:
  - Bootstrap is the only place allowed to assemble the object graph.
  - UI wiring happens here (UI -> Managers), but we do not refactor UI behaviour.
  - Lifecycle shutdown is explicit and best-effort/idempotent.

This module intentionally starts small and will absorb construction of repositories
and services as Phase 2 progresses.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from src.managers.config_manager import ConfigManager
from src.managers.config_models import ConfigData
from src.managers.train_manager import TrainManager
from src.ui.main_window import MainWindow

from src.services.routing.composition import build_routing_services

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ApplicationContainer:
    """Root container returned by [`python.bootstrap_app()`](src/app/bootstrap.py:1)."""

    config_manager: ConfigManager
    config: ConfigData
    window: MainWindow
    train_manager: TrainManager

    def shutdown(self) -> None:
        """Best-effort shutdown for long-lived app resources.

        This must be safe to call multiple times and must not raise.
        """

        # Notes:
        # - Qt closeEvent cleanup does not stop the InitializationManager's worker.
        # - We shutdown after `app.exec()` returns (window closed), so do not touch
        #   UI widgets here; only stop background activity.
        try:
            init_manager = getattr(self.window, "initialization_manager", None)
            if init_manager and hasattr(init_manager, "shutdown"):
                init_manager.shutdown()
        except Exception as exc:  # pragma: no cover
            logger.debug("Bootstrap shutdown: initialization_manager shutdown failed: %s", exc)

        # As a safety net, also shutdown any managers that may have been swapped
        # onto the window after initialization.
        for attr in ("weather_manager", "astronomy_manager"):
            try:
                manager = getattr(self.window, attr, None)
                if manager and hasattr(manager, "shutdown"):
                    manager.shutdown()
            except Exception as exc:  # pragma: no cover
                logger.debug("Bootstrap shutdown: %s shutdown failed: %s", attr, exc)


def bootstrap_app(*, config_manager: ConfigManager, config: ConfigData) -> ApplicationContainer:
    """Build the application object graph.

    This function is intentionally explicit: no hidden singletons, and no
    internal construction inside managers/services.

    Args:
        config_manager: Loaded [`python.ConfigManager`](src/managers/config_manager.py:32)
            (used by UI for persistence).
        config: Loaded [`python.ConfigData`](src/managers/config_models.py:1).

    Returns:
        [`python.ApplicationContainer`](src/app/bootstrap.py:1) holding the
        constructed objects.
    """

    window = MainWindow(config_manager)

    # Composition root: assemble routing services once and inject.
    routing = build_routing_services()

    train_manager = TrainManager(
        config,
        station_service=routing.station_service,
        route_service=routing.route_service,
    )

    # External managers (expected by UI layer) - set explicitly.
    window.train_manager = train_manager

    _apply_initial_route_from_config(train_manager=train_manager, config=config)
    _attach_train_manager_to_train_list_widget(window=window, train_manager=train_manager)
    _connect_ui_signals(window=window, train_manager=train_manager)

    return ApplicationContainer(
        config_manager=config_manager,
        config=config,
        window=window,
        train_manager=train_manager,
    )


def _apply_initial_route_from_config(*, train_manager: TrainManager, config: ConfigData) -> None:
    """Apply persisted route to TrainManager if available."""

    try:
        stations = getattr(config, "stations", None)
        from_name = getattr(stations, "from_name", None) if stations else None
        to_name = getattr(stations, "to_name", None) if stations else None
        route_path = getattr(stations, "route_path", None) if stations else None
        if from_name and to_name:
            train_manager.set_route(from_name, to_name, route_path)
    except Exception as exc:  # pragma: no cover
        # Do not change behaviour: failure to apply persisted route should not
        # prevent startup.
        logger.debug("Failed to apply initial route from config: %s", exc)


def _attach_train_manager_to_train_list_widget(*, window: MainWindow, train_manager: TrainManager) -> None:
    """Attach TrainManager to the train list widget when available."""

    try:
        ui_layout_manager = getattr(window, "ui_layout_manager", None)
        train_list_widget = getattr(ui_layout_manager, "train_list_widget", None)
        if train_list_widget and hasattr(train_list_widget, "set_train_manager"):
            train_list_widget.set_train_manager(train_manager)
    except Exception as exc:  # pragma: no cover
        logger.debug("Failed to attach TrainManager to train list widget: %s", exc)


def _connect_ui_signals(*, window: MainWindow, train_manager: TrainManager) -> None:
    """Connect UI signals between MainWindow and TrainManager.

    This wiring previously lived in [`main.py`](main.py:299). It is moved into the
    composition root to prevent architecture drift.
    """

    # Connect refresh signals (manual refresh only)
    window.refresh_requested.connect(train_manager.fetch_trains)

    # Connect route change signal
    window.route_changed.connect(train_manager.set_route)

    # Connect config update signal
    window.config_updated.connect(train_manager.update_config)

    # Connect train manager signals to window updates
    train_manager.trains_updated.connect(window.update_train_display)
    train_manager.connection_changed.connect(window.update_connection_status)
    train_manager.last_update_changed.connect(window.update_last_update_time)
    train_manager.error_occurred.connect(lambda msg: window.show_error_message("Data Error", msg))

