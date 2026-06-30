#!/usr/bin/env python3
"""Shared dialogs, icon and install-state helpers for the Trainer installer.

This module holds the small presentation pieces the installer window reuses:
the bundled-icon lookup, the install-state classification, the scrollable
licence dialog and the uninstall confirmation. The main window lives in ui.py.
It reads identity and theming from constants.py and drives ops.py.

British spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

import ops
from constants import (
    APP_DISPLAY_NAME,
    BORDER_PX,
    BUTTON_GAP,
    DIALOG_MARGIN,
    ICON_FILE_NAME,
    LICENCE_DIALOG_HEIGHT,
    SIDES,
    STYLESHEET,
    TEXT_PADDING_PX,
    WIDTH_SAFETY_PX,
)


def app_icon() -> QIcon:
    """Return the bundled application icon, or an empty icon when absent."""
    path = ops.payload_app_dir() / ICON_FILE_NAME
    if path.is_file():
        return QIcon(str(path))
    return QIcon()


# ------------------------------------------------------------------- app state


class AppState:
    """The installed-vs-bundled relationship, driving the primary action."""

    NOT_INSTALLED = "not_installed"
    UPGRADE = "upgrade"
    REINSTALL = "reinstall"
    DOWNGRADE = "downgrade"


def detect_state() -> str:
    """Classify the current install against the bundled version."""
    installed = ops.installed_version()
    location = ops.installed_location()
    if installed is None or location is None or not location.exists():
        return AppState.NOT_INSTALLED
    comparison = ops.compare_versions(ops.app_version() or "0.0.0", installed)
    if comparison > 0:
        return AppState.UPGRADE
    if comparison < 0:
        return AppState.DOWNGRADE
    return AppState.REINSTALL


def primary_label(state: str) -> str:
    """Return the primary button caption for an install state."""
    version = ops.app_version()
    if state == AppState.NOT_INSTALLED:
        return "Install"
    if state == AppState.UPGRADE:
        return f"Upgrade to {version}" if version else "Upgrade"
    if state == AppState.DOWNGRADE:
        return "Reinstall (older)"
    return "Reinstall"


# ----------------------------------------------------------------------- views


def licence_view_width(view: QTextEdit, text: str) -> int:
    """Return the pixel width that shows the widest licence line in full."""
    view.ensurePolished()
    metrics = view.fontMetrics()
    lines = text.splitlines() or [text]
    widest = max(metrics.horizontalAdvance(line) for line in lines)
    doc_margin = round(view.document().documentMargin())
    scrollbar = view.verticalScrollBar().sizeHint().width()
    chrome = SIDES * (doc_margin + TEXT_PADDING_PX + BORDER_PX)
    return widest + scrollbar + chrome + WIDTH_SAFETY_PX


class LicenceDialog(QDialog):
    """A themed, scrollable view of a licence text."""

    def __init__(
        self,
        licence_text: str,
        title: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setWindowIcon(app_icon())
        self.setStyleSheet(STYLESHEET)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            DIALOG_MARGIN, DIALOG_MARGIN, DIALOG_MARGIN, DIALOG_MARGIN
        )
        layout.setSpacing(BUTTON_GAP)

        view = QTextEdit()
        view.setObjectName("LicenceView")
        view.setReadOnly(True)
        view.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        view.setPlainText(licence_text)
        layout.addWidget(view)

        view_width = licence_view_width(view, licence_text)
        view.setMinimumWidth(view_width)
        self.resize(view_width + SIDES * DIALOG_MARGIN, LICENCE_DIALOG_HEIGHT)

        close = QPushButton("Close")
        close.setObjectName("SecondaryAction")
        close.clicked.connect(self.accept)
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(close)
        layout.addLayout(row)


class UninstallDialog(QDialog):
    """A small themed uninstall confirmation, with a remove-settings option."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Uninstall {APP_DISPLAY_NAME}")
        self.setWindowIcon(app_icon())
        self.setStyleSheet(STYLESHEET)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            DIALOG_MARGIN, DIALOG_MARGIN, DIALOG_MARGIN, DIALOG_MARGIN
        )
        layout.setSpacing(BUTTON_GAP)

        message = QLabel(
            f"Remove {APP_DISPLAY_NAME} and its shortcuts from this PC? Your "
            "settings are kept unless you tick the box below."
        )
        message.setWordWrap(True)
        layout.addWidget(message)

        self._remove_settings = QCheckBox(
            f"Also remove my {APP_DISPLAY_NAME} settings"
        )
        layout.addWidget(self._remove_settings)

        confirm = QPushButton("Uninstall")
        confirm.setObjectName("DangerAction")
        confirm.clicked.connect(self.accept)
        cancel = QPushButton("Cancel")
        cancel.setObjectName("SecondaryAction")
        cancel.clicked.connect(self.reject)
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(cancel)
        row.addWidget(confirm)
        layout.addLayout(row)

    def remove_settings(self) -> bool:
        """Return whether the user asked to also remove their settings."""
        return self._remove_settings.isChecked()
