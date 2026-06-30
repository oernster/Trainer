#!/usr/bin/env python3
"""Shortcut creation, process detection and PowerShell helpers.

This module owns the best-effort shell-outs the Trainer installer makes:
detecting whether the app is running (tasklist), running PowerShell commands and
writing or removing the per-user Desktop and Start Menu shortcuts. It imports
from constants.py and the stdlib only.

British spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from constants import (
    APP_DISPLAY_NAME,
    DESKTOP_DIR_NAME,
    ENV_APPDATA,
    EXE_NAME,
    POWERSHELL,
    SHORTCUT_EXT,
    SHORTCUT_ICON_FILE_NAME,
    SHORTCUT_TIMEOUT_S,
    START_MENU_SUBPATH,
    TASKLIST_TIMEOUT_S,
)


def is_app_running() -> bool:
    """Return True when trainer.exe appears in the task list (best effort)."""
    no_window = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        result = subprocess.run(
            ["tasklist", "/fi", f"imagename eq {EXE_NAME}", "/nh"],
            capture_output=True,
            text=True,
            timeout=TASKLIST_TIMEOUT_S,
            stdin=subprocess.DEVNULL,
            creationflags=no_window,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return EXE_NAME.lower() in result.stdout.lower()


def start_menu_link() -> Path | None:
    """Return the per-user Start Menu shortcut path, or None when unavailable."""
    appdata = os.environ.get(ENV_APPDATA)
    if not appdata:
        return None
    programs = Path(appdata).joinpath(*START_MENU_SUBPATH)
    return programs / f"{APP_DISPLAY_NAME}{SHORTCUT_EXT}"


def desktop_link() -> Path:
    """Return the per-user Desktop shortcut path."""
    return Path.home() / DESKTOP_DIR_NAME / f"{APP_DISPLAY_NAME}{SHORTCUT_EXT}"


def run_powershell(command: str) -> None:
    """Run a PowerShell command, ignoring failures (best effort)."""
    no_window = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        subprocess.run(
            [
                POWERSHELL,
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                command,
            ],
            check=False,
            timeout=SHORTCUT_TIMEOUT_S,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=no_window,
        )
    except (OSError, subprocess.SubprocessError):
        return


def create_shortcut(exe_path: Path, link: Path) -> None:
    """Write a shortcut to the installed exe with the app icon (best effort)."""
    link.parent.mkdir(parents=True, exist_ok=True)
    icon = exe_path.parent / SHORTCUT_ICON_FILE_NAME
    icon_clause = f"$s.IconLocation = '{icon}'; " if icon.exists() else ""
    command = (
        "$s = (New-Object -ComObject WScript.Shell).CreateShortcut('"
        f"{link}'); $s.TargetPath = '{exe_path}'; "
        f"$s.WorkingDirectory = '{exe_path.parent}'; "
        f"{icon_clause}$s.Save()"
    )
    run_powershell(command)


def remove_shortcut(link: Path | None) -> None:
    """Delete a shortcut file if present (best effort)."""
    if link is None:
        return
    try:
        link.unlink(missing_ok=True)
    except OSError:
        return


def apply_shortcuts(exe_path: Path, *, desktop: bool, start_menu: bool) -> None:
    """Create or remove the desktop and Start Menu shortcuts to match options."""
    desktop_target = desktop_link()
    if desktop:
        create_shortcut(exe_path, desktop_target)
    else:
        remove_shortcut(desktop_target)

    start_link = start_menu_link()
    if start_menu and start_link is not None:
        create_shortcut(exe_path, start_link)
    else:
        remove_shortcut(start_link)
