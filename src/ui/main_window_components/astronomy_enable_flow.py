"""Astronomy enable flow helpers."""

from __future__ import annotations

import logging

from PySide6.QtWidgets import QMessageBox

logger = logging.getLogger(__name__)


def on_astronomy_enable_requested(*, window) -> None:
    """Handle astronomy enable request from settings dialog."""

    if window.astronomy_manager:
        window.astronomy_manager.astronomy_updated.connect(
            window._on_astronomy_data_ready_after_enable
        )
        window.astronomy_manager.astronomy_error.connect(window._on_astronomy_error_after_enable)
        logger.debug("Connected to astronomy signals to wait for data after enable")
        return

    show_astronomy_enabled_message(window=window)


def on_astronomy_data_ready_after_enable(*, window, forecast_data) -> None:
    """Handle astronomy data ready after enable request."""

    if window.astronomy_manager:
        window.astronomy_manager.astronomy_updated.disconnect(
            window._on_astronomy_data_ready_after_enable
        )
        window.astronomy_manager.astronomy_error.disconnect(
            window._on_astronomy_error_after_enable
        )

    window.widget_lifecycle_manager.ensure_astronomy_widget_in_layout()
    show_astronomy_enabled_message(window=window)
    logger.info("Astronomy data loaded successfully after enable")


def on_astronomy_error_after_enable(*, window, error_message: str) -> None:
    """Handle astronomy error after enable request."""

    if window.astronomy_manager:
        window.astronomy_manager.astronomy_updated.disconnect(
            window._on_astronomy_data_ready_after_enable
        )
        window.astronomy_manager.astronomy_error.disconnect(
            window._on_astronomy_error_after_enable
        )

    msg_box = QMessageBox(window)
    msg_box.setWindowTitle("Astronomy Data Error")
    msg_box.setText(
        "Astronomy integration has been enabled, but there was an error loading data:\n\n"
        f"{error_message}\n\n"
        "You can try refreshing the data later."
    )
    msg_box.setIcon(QMessageBox.Icon.Warning)
    msg_box.exec()
    logger.warning("Astronomy error after enable: %s", error_message)


def show_astronomy_enabled_message(*, window) -> None:
    """Show the astronomy enabled success message."""

    msg_box = QMessageBox(window)
    msg_box.setWindowTitle("Astronomy Enabled")
    msg_box.setText(
        "Astronomy integration has been enabled! "
        "You'll now see space events and astronomical data in your app."
    )
    msg_box.setIcon(QMessageBox.Icon.Information)
    msg_box.exec()

