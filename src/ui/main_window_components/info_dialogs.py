"""Standard info/error dialogs shown by MainWindow."""

from __future__ import annotations

import logging

from PySide6.QtWidgets import QMessageBox

from version import get_about_text

from src.ui.widgets.about_dialog import AboutDialog
from src.utils.icon_resolver import get_app_icon_png_path, get_app_icon_path

logger = logging.getLogger(__name__)

# Size of the About icon badge requested from the PNG asset set.
ABOUT_ICON_PNG_SIZE = 256


def show_about_dialog(*, window) -> None:
    """Show about dialog using centralized version system."""

    config_path = window.config_manager.config_path

    about_html = get_about_text()
    icon_path = get_app_icon_png_path(ABOUT_ICON_PNG_SIZE) or get_app_icon_path()
    dialog = AboutDialog(
        parent=window,
        about_html=about_html,
        config_path=str(config_path),
        title="About",
        icon_path=str(icon_path) if icon_path else None,
    )
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
