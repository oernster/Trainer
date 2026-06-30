#!/usr/bin/env python3
"""HKCU registry and autostart operations for the Trainer installer.

This module owns every winreg interaction: the Apps-and-features Uninstall
registration, the notification (AppUserModelId) cleanup and the per-user Run
entry that optionally launches the app at sign-in. It is per-user only and
never needs administrator rights. It imports from constants.py and the stdlib.

British spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

from pathlib import Path

from constants import (
    APP_AUMID,
    APP_DISPLAY_NAME,
    APP_PUBLISHER,
    APP_URL,
    AUMID_CLASSES_SUBKEY,
    EXE_NAME,
    RUN_SUBKEY,
    RUN_VALUE,
    SHORTCUT_ICON_FILE_NAME,
    UNINSTALL_FLAG,
    UNINSTALL_KEY,
)


def read_registry_str(key: str, name: str) -> str | None:
    """Return an HKCU string value, or None when the key or value is absent."""
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key) as handle:
            return str(winreg.QueryValueEx(handle, name)[0])
    except OSError:
        return None


def dir_size_kb(path: Path) -> int | None:
    """Return the total size of a directory in KiB, or None on error."""
    try:
        total = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
    except OSError:
        return None
    return total // 1024


def write_uninstall_entry(
    install_dir: Path, uninstaller: Path, version: str
) -> None:
    """Register the app under HKCU so it appears in Apps and features."""
    import winreg

    icon = install_dir / SHORTCUT_ICON_FILE_NAME
    display_icon = str(icon if icon.exists() else install_dir / EXE_NAME)
    estimated_kb = dir_size_kb(install_dir)
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY) as handle:
        winreg.SetValueEx(handle, "DisplayName", 0, winreg.REG_SZ, APP_DISPLAY_NAME)
        winreg.SetValueEx(handle, "DisplayVersion", 0, winreg.REG_SZ, version)
        winreg.SetValueEx(
            handle, "InstallLocation", 0, winreg.REG_SZ, str(install_dir)
        )
        winreg.SetValueEx(
            handle,
            "UninstallString",
            0,
            winreg.REG_SZ,
            f'"{uninstaller}" {UNINSTALL_FLAG}',
        )
        winreg.SetValueEx(handle, "DisplayIcon", 0, winreg.REG_SZ, display_icon)
        winreg.SetValueEx(handle, "Publisher", 0, winreg.REG_SZ, APP_PUBLISHER)
        winreg.SetValueEx(handle, "URLInfoAbout", 0, winreg.REG_SZ, APP_URL)
        winreg.SetValueEx(handle, "NoModify", 0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(handle, "NoRepair", 0, winreg.REG_DWORD, 1)
        if estimated_kb is not None:
            winreg.SetValueEx(
                handle, "EstimatedSize", 0, winreg.REG_DWORD, estimated_kb
            )


def delete_uninstall_entry() -> None:
    """Remove the HKCU Uninstall registration (best effort)."""
    import winreg

    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY)
    except OSError:
        return


def delete_toast_identity() -> None:
    """Remove the app's notification (AppUserModelId) registration.

    If the app wrote its toast name and icon under HKCU on launch, removing the
    key on uninstall leaves no orphaned registration behind. Best effort.
    """
    import winreg

    try:
        winreg.DeleteKey(
            winreg.HKEY_CURRENT_USER,
            rf"{AUMID_CLASSES_SUBKEY}\{APP_AUMID}",
        )
    except OSError:
        return


def installed_version() -> str | None:
    """Return the registered installed version, or None when not installed."""
    return read_registry_str(UNINSTALL_KEY, "DisplayVersion")


def installed_location() -> Path | None:
    """Return the registered install location, or None when not installed."""
    raw = read_registry_str(UNINSTALL_KEY, "InstallLocation")
    if not raw:
        return None
    path = Path(raw)
    return path if path.is_absolute() else None


def set_autostart(enabled: bool, exe_path: Path) -> None:
    """Add or remove the per-user Run entry that starts the app at sign-in."""
    import winreg

    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_SUBKEY) as key:
            if enabled:
                winreg.SetValueEx(key, RUN_VALUE, 0, winreg.REG_SZ, f'"{exe_path}"')
            else:
                try:
                    winreg.DeleteValue(key, RUN_VALUE)
                except OSError:
                    pass
    except OSError:
        return


def remove_autostart() -> None:
    """Remove the per-user Run entry (best effort), used on uninstall."""
    import winreg

    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, RUN_SUBKEY, 0, winreg.KEY_SET_VALUE
        ) as key:
            try:
                winreg.DeleteValue(key, RUN_VALUE)
            except OSError:
                pass
    except OSError:
        return
