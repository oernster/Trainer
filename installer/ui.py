#!/usr/bin/env python3
"""The themed Trainer installer window.

This module holds the state-aware installer window. The shared dialogs, the
bundled-icon lookup and the install-state helpers live in dialogs.py; the
side-effecting work lives in ops.py; the identity and theming live in
constants.py. The palette is Trainer's Material blue (accent #1976d2), and
every button uses the :enabled:hover border rule so hover never reflows.

British spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

import ops
from constants import (
    APP_DISPLAY_NAME,
    APP_TAGLINE,
    BUTTON_GAP,
    DIVIDER_PX,
    HEADER_SPACING,
    ICON_PX,
    LGPL_NOTICE_FILE_NAME,
    LICENSE_FILE_NAME,
    MARGIN_BOTTOM,
    MARGIN_SIDE,
    MARGIN_TOP,
    SECTION_SPACING,
    STYLESHEET,
    WINDOW_HEIGHT,
    WINDOW_TITLE,
    WINDOW_WIDTH,
)
from dialogs import (
    AppState,
    LicenceDialog,
    UninstallDialog,
    app_icon,
    detect_state,
    primary_label,
)


class InstallerWindow(QWidget):
    """The installer window: a themed, state-aware lifecycle screen."""

    def __init__(self) -> None:
        super().__init__()
        self._state = detect_state()
        self.setWindowTitle(WINDOW_TITLE)
        self.setWindowIcon(app_icon())
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.setStyleSheet(STYLESHEET)
        self._desktop = QCheckBox("Create a desktop shortcut")
        self._start_menu = QCheckBox("Create a Start Menu shortcut")
        self._launch_on_finish = QCheckBox(
            f"Launch {APP_DISPLAY_NAME} when finished"
        )
        self._autostart = QCheckBox(
            f"Start {APP_DISPLAY_NAME} when I sign in to Windows"
        )
        self._status = QLabel("")
        self._status.setObjectName("StatusLine")
        self._status.setWordWrap(True)
        self._primary = QPushButton(primary_label(self._state))
        self._primary.setObjectName("PrimaryAction")
        self._repair = QPushButton("Repair")
        self._repair.setObjectName("SecondaryAction")
        self._uninstall = QPushButton("Uninstall")
        self._uninstall.setObjectName("DangerAction")
        self._build_ui()

    # ----------------------------------------------------------------- layout

    def _build_ui(self) -> None:
        """Assemble the themed installer layout in one top-to-bottom column."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            MARGIN_SIDE, MARGIN_TOP, MARGIN_SIDE, MARGIN_BOTTOM
        )
        layout.setSpacing(SECTION_SPACING)

        layout.addLayout(self._build_header())

        subtitle = QLabel(self._subtitle_text())
        subtitle.setObjectName("SubTitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(subtitle)

        tagline = QLabel(APP_TAGLINE)
        tagline.setObjectName("Tagline")
        tagline.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        tagline.setWordWrap(True)
        layout.addWidget(tagline)

        divider = QFrame()
        divider.setObjectName("Divider")
        divider.setFixedHeight(DIVIDER_PX)
        layout.addWidget(divider)

        path_label = QLabel(f"Install location: {ops.install_target()}")
        path_label.setObjectName("InstallPath")
        path_label.setWordWrap(True)
        layout.addWidget(path_label)

        self._desktop.setChecked(True)
        layout.addWidget(self._desktop)
        self._start_menu.setChecked(True)
        layout.addWidget(self._start_menu)
        self._launch_on_finish.setChecked(True)
        layout.addWidget(self._launch_on_finish)
        layout.addWidget(self._autostart)
        layout.addWidget(self._status)

        layout.addStretch()
        layout.addLayout(self._build_buttons())

    def _build_header(self) -> QHBoxLayout:
        """Build the header row: icon, title and version, plus licence buttons."""
        header = QHBoxLayout()
        header.setSpacing(HEADER_SPACING)

        icon = app_icon()
        if not icon.isNull():
            badge = QLabel()
            badge.setPixmap(icon.pixmap(QSize(ICON_PX, ICON_PX)))
            header.addWidget(badge)

        title = QLabel(f"{APP_DISPLAY_NAME} Setup")
        title.setObjectName("HeaderTitle")
        header.addWidget(title)

        version = ops.app_version()
        if version:
            version_label = QLabel(f"v{version}")
            version_label.setObjectName("HeaderVersion")
            version_label.setAlignment(
                Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft
            )
            header.addWidget(version_label)

        header.addStretch()

        installer_licence_button = QPushButton("Installer notice")
        installer_licence_button.setObjectName("LicenceButton")
        installer_licence_button.clicked.connect(self._on_show_installer_licence)
        header.addWidget(installer_licence_button)

        licence_button = QPushButton("Licence (GPL-3.0)")
        licence_button.setObjectName("LicenceButton")
        licence_button.clicked.connect(self._on_show_licence)
        header.addWidget(licence_button)

        notices_button = QPushButton("PySide6 (LGPL-3.0)")
        notices_button.setObjectName("LicenceButton")
        notices_button.clicked.connect(self._on_show_notices)
        header.addWidget(notices_button)
        return header

    def _build_buttons(self) -> QHBoxLayout:
        """Build the action row: primary, Repair, Uninstall and Close."""
        self._primary.clicked.connect(self._on_primary)
        self._repair.clicked.connect(self._on_repair)
        self._uninstall.clicked.connect(self._on_uninstall)
        close_button = QPushButton("Close")
        close_button.setObjectName("SecondaryAction")
        close_button.clicked.connect(self.close)

        installed = self._state != AppState.NOT_INSTALLED
        self._repair.setVisible(installed)
        self._uninstall.setVisible(installed)

        buttons = QHBoxLayout()
        buttons.setSpacing(BUTTON_GAP)
        buttons.addWidget(self._uninstall)
        buttons.addStretch()
        buttons.addWidget(self._repair)
        buttons.addWidget(self._primary)
        buttons.addWidget(close_button)
        return buttons

    def _subtitle_text(self) -> str:
        """Return a subtitle reflecting whether this is a fresh install."""
        if self._state == AppState.NOT_INSTALLED:
            return f"Welcome to the {APP_DISPLAY_NAME} installer"
        return f"{APP_DISPLAY_NAME} is already installed"

    # ---------------------------------------------------------------- actions

    def _on_show_licence(self) -> None:
        """Open the application (GPL-3.0) licence in a themed dialog."""
        LicenceDialog(
            ops.licence_text(LICENSE_FILE_NAME),
            f"{APP_DISPLAY_NAME} Licence (GPL-3.0)",
            self,
        ).exec()

    def _on_show_notices(self) -> None:
        """Open the PySide6 (LGPL-3.0) third-party notice in a themed dialog."""
        LicenceDialog(
            ops.licence_text(LGPL_NOTICE_FILE_NAME),
            f"{APP_DISPLAY_NAME} Third-Party Notice (PySide6, LGPL-3.0)",
            self,
        ).exec()

    def _on_show_installer_licence(self) -> None:
        """Open the installer-wrapper licence notice in a themed dialog."""
        LicenceDialog(
            ops.installer_licence_text(),
            f"{APP_DISPLAY_NAME} Installer Notice",
            self,
        ).exec()

    def _guard_not_running(self) -> bool:
        """Return True when it is safe to proceed; warn if the app is running."""
        if ops.is_app_running():
            self._status.setText(
                f"{APP_DISPLAY_NAME} is running. Please close it, then retry."
            )
            return False
        return True

    def _on_primary(self) -> None:
        """Install, upgrade or reinstall, then optionally launch the app."""
        if not self._guard_not_running():
            return
        self._set_busy("Installing...")
        try:
            exe_path = ops.install(
                ops.install_target(),
                desktop=self._desktop.isChecked(),
                start_menu=self._start_menu.isChecked(),
                autostart=self._autostart.isChecked(),
            )
        except Exception as error:
            self._finish_error(f"Installation failed: {error}")
            return
        self._status.setText(f"Installed to {exe_path.parent}.")
        if self._launch_on_finish.isChecked():
            ops.launch(exe_path)
            self.close()
            return
        self._refresh_after_change()

    def _on_repair(self) -> None:
        """Re-deploy the application files over the existing install."""
        if not self._guard_not_running():
            return
        location = ops.installed_location() or ops.install_target()
        self._set_busy("Repairing...")
        try:
            ops.repair(location)
        except Exception as error:
            self._finish_error(f"Repair failed: {error}")
            return
        self._status.setText("Repair complete.")
        self._refresh_after_change()

    def _on_uninstall(self) -> None:
        """Confirm, then remove the application, shortcuts and registration."""
        if not self._guard_not_running():
            return
        dialog = UninstallDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self._set_busy("Uninstalling...")
        try:
            ops.uninstall(remove_settings=dialog.remove_settings())
        except Exception as error:
            self._finish_error(f"Uninstall failed: {error}")
            return
        self._status.setText(f"{APP_DISPLAY_NAME} has been uninstalled.")
        self._state = AppState.NOT_INSTALLED
        self._primary.setText(primary_label(self._state))
        self._repair.setVisible(False)
        self._uninstall.setVisible(False)
        self._primary.setEnabled(True)

    def _set_busy(self, message: str) -> None:
        """Show a status message and disable the action buttons during work."""
        self._status.setText(message)
        self._primary.setEnabled(False)
        self._repair.setEnabled(False)
        self._uninstall.setEnabled(False)
        QApplication.processEvents()

    def _finish_error(self, message: str) -> None:
        """Show an error and restore the buttons to their accepted state."""
        self._status.setText(message)
        self._primary.setEnabled(True)
        self._repair.setEnabled(True)
        self._uninstall.setEnabled(True)

    def _refresh_after_change(self) -> None:
        """Re-detect state after an install or repair and relabel the buttons."""
        self._state = detect_state()
        self._primary.setText(primary_label(self._state))
        installed = self._state != AppState.NOT_INSTALLED
        self._repair.setVisible(installed)
        self._uninstall.setVisible(installed)
        self._uninstall.setEnabled(True)
        self._primary.setEnabled(True)
        self._repair.setEnabled(True)
