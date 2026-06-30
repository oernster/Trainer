#!/usr/bin/env python3
"""Identity, paths and theming constants for the Trainer installer.

This module holds every literal the installer depends on, so the UI and the
operations modules carry no inline values. Trainer is single-licensed GPL-3.0
(PySide6 is LGPL but Trainer is not dual-licensed), so there is one app licence
plus the PySide6 LGPL notices rather than Fulcrum's split GPL/LGPL pair.

British spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

APP_NAME = "Trainer"
# Display name shown in all installer UI text and the Apps list. For Trainer the
# identifier and the display name match (no embedded space), so the payload
# directory, install path and exe all share the same base name.
APP_DISPLAY_NAME = "Trainer"
APP_TAGLINE = "Train times with weather forecasting and astronomical events"
APP_PUBLISHER = "Oliver Ernster"
APP_URL = "https://oernster.github.io/Trainer/"

# Payload layout produced by buildinstaller.py: payload/Trainer/ holds the
# bundle's non-binary files (read by the installer UI), payload/Trainer.zip
# holds the full app bundle for deployment and payload/LICENSE holds the GPL-3.0
# licence text.
PAYLOAD_DIR_NAME = "payload"
LICENSE_FILE_NAME = "LICENSE"
LGPL_NOTICE_FILE_NAME = "LGPL-3.0.txt"
THIRD_PARTY_NOTICE_FILE_NAME = "THIRD_PARTY_LICENSES.txt"
INSTALLER_LICENSE_FILE_NAME = "INSTALLER_LICENSE"
EXE_NAME = "trainer.exe"
# The bundle ships as a single zip because Nuitka's onefile build drops loose
# executables and DLLs from an included data directory; the installer extracts
# this archive on deploy.
PAYLOAD_ARCHIVE_NAME = "Trainer.zip"
# The bundled icon used for the installer window, dialogs and the badge. Trainer
# ships its assets under an assets subdirectory in the bundle, so the icons live
# beside the railway data rather than at the bundle root.
ICON_FILE_NAME = "assets/trainer_icon_256.png"
# The multi-size .ico, used for shortcuts and the Apps-list DisplayIcon so the
# small sizes that Windows search and the taskbar render are present.
SHORTCUT_ICON_FILE_NAME = "assets/trainer.ico"

# Per-user locations (no administrator rights required).
ENV_LOCALAPPDATA = "LOCALAPPDATA"
ENV_APPDATA = "APPDATA"
PROGRAMS_DIR_NAME = "Programs"
START_MENU_SUBPATH = ("Microsoft", "Windows", "Start Menu", "Programs")
DESKTOP_DIR_NAME = "Desktop"
SHORTCUT_EXT = ".lnk"
# Per-user state directory the application writes (preferences, caches).
STATE_DIR_NAME = "Trainer"

# The registered uninstaller is a copy of this installer placed under the
# install root, so "Apps & features" can re-run it with --uninstall.
UNINSTALLER_SUBDIR = "_uninstall"
UNINSTALLER_NAME = "TrainerSetup.exe"
UNINSTALL_FLAG = "--uninstall"
# Under a Nuitka onefile build sys.executable is the unpacked temporary
# bootstrap, so the original launcher (the source for the registered
# uninstaller) is discovered via these instead.
NUITKA_ONEFILE_ENV = "NUITKA_ONEFILE_BINARY"
EXE_SUFFIX = ".exe"

# HKCU Uninstall registration: this is what makes the app appear in
# "Apps & features" with a working Uninstall button.
UNINSTALL_KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\Trainer"

# Per-user Run key for launching the app at Windows sign-in (no admin needed).
RUN_SUBKEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_VALUE = "Trainer"

# The app's Application User Model ID, used for the installer's taskbar identity
# and removed on uninstall if the app registered a toast identity under it.
APP_AUMID = "com.oliverernster.Trainer"
AUMID_CLASSES_SUBKEY = r"Software\Classes\AppUserModelId"

# Best-effort shell-out timeouts.
POWERSHELL = "powershell"
SHORTCUT_TIMEOUT_S = 15
TASKLIST_TIMEOUT_S = 10

# Deferred delete (when the uninstaller lives inside the dir it must remove).
DEFERRED_DELETE_ATTEMPTS = 30
DEFERRED_DELETE_INTERVAL_MS = 500

# Crash diagnostics: a console-disabled onefile shows no traceback when it
# dies, so unhandled exceptions are appended to this file under the temp
# directory for the user to send back.
INSTALLER_LOG_NAME = "trainer-installer.log"

# Fallback version when the bundle reports none.
FALLBACK_VERSION = "0.0.0"

# Window geometry, as named layout constants (pixel sizes).
WINDOW_TITLE = f"{APP_DISPLAY_NAME} Installer"
WINDOW_WIDTH = 620
WINDOW_HEIGHT = 560
LICENCE_DIALOG_HEIGHT = 540
LICENCE_FONT_PX = 12
ICON_PX = 56
DIVIDER_PX = 1
BORDER_PX = 1
TEXT_PADDING_PX = 8
SIDES = 2
WIDTH_SAFETY_PX = 8
MARGIN_SIDE = 36
MARGIN_TOP = 28
MARGIN_BOTTOM = 24
DIALOG_MARGIN = 20
SECTION_SPACING = 14
HEADER_SPACING = 14
BUTTON_GAP = 10

LICENSE_FALLBACK = "The licence text was not bundled with this installer."
INSTALLER_LICENSE_FALLBACK = (
    "The installer licence notice was not bundled with this installer."
)

# --- Trainer Material blue palette -------------------------------------------
# Named colour tokens for the installer surfaces, text and controls. Every
# QPushButton carries a transparent 2px border by default so the blue hover
# border does not reflow the layout, and the hover reaction is gated on
# :enabled so disabled buttons stay muted with no border change.
BACKGROUND = "#1a1a1a"
SURFACE = "#2d2d2d"
SURFACE_RAISED = "#3d3d3d"
BORDER = "#3d3d3d"
TEXT = "#ffffff"
TEXT_MUTED = "#b0b0b0"
ACCENT = "#1976d2"
ACCENT_HOVER = "#1565c0"
ERROR = "#f44336"
SUCCESS = "#4caf50"
DISABLED_TEXT = "#6b6b6b"

STYLESHEET = f"""
QWidget {{
    background: {BACKGROUND}; color: {TEXT}; font-family: 'Segoe UI';
}}
QLabel#HeaderTitle {{
    font-size: 30px; font-weight: 700; color: {ACCENT};
}}
QLabel#HeaderVersion {{ font-size: 13px; color: {TEXT_MUTED}; }}
QLabel#SubTitle {{ font-size: 18px; font-weight: 700; color: {ACCENT}; }}
QLabel#Tagline {{ font-size: 13px; color: {TEXT_MUTED}; }}
QLabel#InstallPath {{ font-size: 12px; color: {TEXT_MUTED}; }}
QLabel#StatusLine {{ font-size: 13px; color: {TEXT}; }}
QFrame#Divider {{ background: {BORDER}; border: none; }}
QCheckBox {{ spacing: 10px; font-size: 13px; color: {TEXT}; }}
QCheckBox::indicator {{ width: 16px; height: 16px; }}
QPushButton {{
    border: 2px solid transparent;
}}
QPushButton:enabled:hover {{
    border-color: {ACCENT};
}}
QPushButton#LicenceButton {{
    background: {SURFACE}; color: {TEXT};
    padding: 8px 16px; border-radius: 16px; font-weight: 600;
}}
QPushButton#PrimaryAction {{
    background: {ACCENT}; color: {TEXT};
    padding: 12px 28px; border-radius: 22px; font-size: 14px;
    font-weight: 700; min-width: 150px;
}}
QPushButton#PrimaryAction:enabled:hover {{
    background: {ACCENT_HOVER}; border-color: {ACCENT};
}}
QPushButton#PrimaryAction:disabled {{
    background: {SURFACE_RAISED}; color: {DISABLED_TEXT};
}}
QPushButton#SecondaryAction {{
    background: {SURFACE}; color: {TEXT};
    padding: 12px 22px; border-radius: 22px; font-size: 13px;
    font-weight: 600;
}}
QPushButton#SecondaryAction:disabled {{
    background: {SURFACE_RAISED}; color: {DISABLED_TEXT};
}}
QPushButton#DangerAction {{
    background: {SURFACE_RAISED}; color: {ERROR};
    padding: 12px 22px; border-radius: 22px; font-size: 13px;
    font-weight: 600;
}}
QPushButton#DangerAction:disabled {{
    background: {SURFACE_RAISED}; color: {DISABLED_TEXT};
}}
QTextEdit {{
    background: {SURFACE}; border: {BORDER_PX}px solid {BORDER};
    border-radius: 10px; color: {TEXT}; padding: {TEXT_PADDING_PX}px;
}}
QTextEdit#LicenceView {{
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: {LICENCE_FONT_PX}px;
}}
QDialog {{ background: {BACKGROUND}; }}
"""
