"""Standard info/error dialogs shown by MainWindow."""

from __future__ import annotations

import logging

from PySide6.QtWidgets import QMessageBox

from version import get_about_text

from src.ui.widgets.about_dialog import AboutDialog

logger = logging.getLogger(__name__)


def show_about_dialog(*, window) -> None:
    """Show about dialog using centralized version system."""

    config_path = window.config_manager.config_path

    about_html = get_about_text()
    dialog = AboutDialog(parent=window, about_html=about_html, config_path=str(config_path), title="About")
    dialog.exec()


def show_error_message(*, window, title: str, message: str) -> None:
    """Show error message dialog."""

    msg_box = QMessageBox(window)
    msg_box.setIcon(QMessageBox.Icon.Critical)
    msg_box.setWindowTitle(title)
    msg_box.setText(message)
    msg_box.exec()


def show_info_message(*, window, title: str, message: str) -> None:
    """Show information message dialog."""

    msg_box = QMessageBox(window)
    msg_box.setIcon(QMessageBox.Icon.Information)
    msg_box.setWindowTitle(title)
    msg_box.setText(message)
    msg_box.exec()
