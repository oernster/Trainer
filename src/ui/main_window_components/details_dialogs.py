"""Train/route details dialog helpers."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def show_train_details(*, window, train_data) -> None:
    """Show detailed train information dialog."""

    try:
        from ..train_detail_dialog import TrainDetailDialog

        dialog = TrainDetailDialog(
            train_data,
            window.theme_manager.current_theme,
            window,
        )
        dialog.exec()
        logger.info("Showed train details for %s", getattr(train_data, "destination", ""))
    except Exception as exc:  # pragma: no cover
        logger.error("Failed to show train details: %s", exc)
        window.show_error_message("Train Details Error", f"Failed to show train details: {exc}")


def show_route_details(*, window, train_data) -> None:
    """Show route display dialog with all calling points."""

    try:
        from ..widgets.route_display_dialog import RouteDisplayDialog

        dialog = RouteDisplayDialog(
            train_data,
            window.theme_manager.current_theme,
            window,
            window.train_manager,
        )
        dialog.exec()
        logger.info("Showed route details for %s", getattr(train_data, "destination", ""))
    except Exception as exc:  # pragma: no cover
        logger.error("Failed to show route details: %s", exc)
        window.show_error_message("Route Details Error", f"Failed to show route details: {exc}")

