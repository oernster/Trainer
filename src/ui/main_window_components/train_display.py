"""Train list display helpers."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def update_train_display(*, window, trains: list[Any]) -> None:
    """Update train list widget display."""

    widgets = window.ui_layout_manager.get_widgets()
    train_list_widget = widgets.get("train_list_widget")

    if train_list_widget:
        train_list_widget.update_trains(trains)

        if not hasattr(window, "_train_selection_connected"):
            train_list_widget.train_selected.connect(window.show_train_details)
            window._train_selection_connected = True

        if not hasattr(window, "_route_selection_connected"):
            train_list_widget.route_selected.connect(window.show_route_details)
            window._route_selection_connected = True

    logger.debug("Updated display with %s trains", len(trains))

