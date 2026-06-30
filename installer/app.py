#!/usr/bin/env python3
"""Trainer installer UI entry point.

A self-contained PySide6 installer compiled into a single executable by
buildinstaller.py. It carries the built application bundle and the GPL-3.0
LICENSE as an embedded payload (staged under ``payload/`` by the build tooling)
and provides the full lifecycle the author's other installers offer:

- Install, upgrade, reinstall and repair the per-user application.
- Register the app in Windows "Apps & features" (the HKCU Uninstall key), so it
  appears as an installed program with a working Uninstall action.
- Uninstall (also runnable headlessly via ``--uninstall``, which is how the
  registered UninstallString re-invokes a copy of this installer).
- Optional desktop and Start Menu shortcuts, and optional launch at sign-in.

It never needs administrator rights: it deploys to
``%LOCALAPPDATA%\\Programs\\Trainer`` and registers under HKCU. It is
deliberately standalone (it imports nothing from the Trainer application) and
dependency-light, so the onefile build pulls in nothing beyond PySide6 and the
stdlib.

The module is split across a small set of files to keep each under the
~400-line limit: constants.py (identity, paths and theming), ops.py (the
side-effecting install/uninstall/registry/shortcut work) and ui.py (the themed
window and dialogs). This file is the thin composition root.

British spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
import traceback
from pathlib import Path
from types import TracebackType

from PySide6.QtWidgets import QApplication, QDialog

import ops
from constants import (
    APP_AUMID,
    APP_DISPLAY_NAME,
    INSTALLER_LOG_NAME,
    UNINSTALL_FLAG,
    WINDOW_TITLE,
)
from dialogs import UninstallDialog, app_icon
from ui import InstallerWindow


def _set_app_user_model_id() -> None:
    """Give the installer a stable taskbar identity (best effort)."""
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            f"{APP_AUMID}.installer"
        )
    except (OSError, AttributeError):
        return


def _run_uninstall_cli(args: argparse.Namespace) -> int:
    """Run the uninstall flow when invoked as the registered uninstaller."""
    app = QApplication(sys.argv)
    app.setApplicationName(f"{APP_DISPLAY_NAME} Setup")
    app.setWindowIcon(app_icon())
    if args.quiet:
        ops.uninstall(remove_settings=args.remove_settings)
        return 0
    dialog = UninstallDialog()
    if dialog.exec() == QDialog.DialogCode.Accepted:
        ops.uninstall(remove_settings=dialog.remove_settings())
    return 0


def _parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse the installer command line (used for the registered uninstaller)."""
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument(UNINSTALL_FLAG, dest="uninstall", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--remove-settings", action="store_true")
    return parser.parse_args(argv)


def _installer_log_path() -> Path:
    """Return the crash-log path under the per-user temporary directory."""
    return Path(tempfile.gettempdir()) / INSTALLER_LOG_NAME


def _install_crash_logging() -> None:
    """Log unhandled exceptions to a file before the default handler runs.

    The installer is a console-disabled onefile; a crash otherwise leaves no
    visible traceback. This excepthook appends one to a known log file and
    then chains to the default handler so behaviour is unchanged.
    """
    log_path = _installer_log_path()

    def _hook(
        exc_type: type[BaseException],
        exc: BaseException,
        tb: TracebackType | None,
    ) -> None:
        try:
            with log_path.open("a", encoding="utf-8") as handle:
                handle.write("\n=== Unhandled exception ===\n")
                traceback.print_exception(exc_type, exc, tb, file=handle)
        except OSError:
            pass
        sys.__excepthook__(exc_type, exc, tb)

    sys.excepthook = _hook


def main() -> int:
    """Run the installer GUI, or the uninstall flow when so invoked."""
    _install_crash_logging()
    _set_app_user_model_id()
    args = _parse_args(sys.argv[1:])
    if args.uninstall:
        return _run_uninstall_cli(args)

    app = QApplication(sys.argv)
    app.setApplicationName(WINDOW_TITLE)
    app.setWindowIcon(app_icon())
    window = InstallerWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
