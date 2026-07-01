#!/usr/bin/env python3
"""Payload resolution and install/uninstall orchestration for Trainer.

This module locates the embedded payload, queries the bundled application
version, compares versions and drives the per-user install, repair and
uninstall flows. The registry and autostart work lives in registry.py and the
shortcut and process work lives in shortcuts.py; this module composes them. It
imports from constants.py, registry.py, shortcuts.py and the stdlib, so the
onefile build pulls in nothing extra.

It never needs administrator rights: it deploys to
%LOCALAPPDATA%\\Programs\\Trainer and registers under HKCU.

British spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

import registry
import shortcuts
from constants import (
    APP_NAME,
    BUNDLED_VERSION_FILE_NAME,
    DEFERRED_DELETE_ATTEMPTS,
    DEFERRED_DELETE_INTERVAL_MS,
    ENV_LOCALAPPDATA,
    EXE_NAME,
    EXE_SUFFIX,
    FALLBACK_VERSION,
    INSTALLER_LICENSE_FALLBACK,
    INSTALLER_LICENSE_FILE_NAME,
    LICENSE_FALLBACK,
    NUITKA_ONEFILE_ENV,
    PAYLOAD_ARCHIVE_NAME,
    PAYLOAD_DIR_NAME,
    POWERSHELL,
    PROGRAMS_DIR_NAME,
    STATE_DIR_NAME,
    TASKLIST_TIMEOUT_S,
    UNINSTALLER_NAME,
    UNINSTALLER_SUBDIR,
)

# Re-export the registry and shortcut lookups the UI and entry point use, so
# callers have a single operations surface (ops) without reaching across modules.
installed_version = registry.installed_version
installed_location = registry.installed_location
is_app_running = shortcuts.is_app_running


# --------------------------------------------------------------------- payload


def bundle_root() -> Path:
    """Return the directory holding the unpacked payload and licence."""
    return Path(__file__).resolve().parent


def payload_app_dir() -> Path:
    """Return the bundled application directory inside the payload."""
    return bundle_root() / PAYLOAD_DIR_NAME / APP_NAME


def payload_archive() -> Path:
    """Return the zipped application bundle inside the payload."""
    return bundle_root() / PAYLOAD_DIR_NAME / PAYLOAD_ARCHIVE_NAME


def licence_text(file_name: str) -> str:
    """Return a bundled licence text by file name, or a fallback if absent."""
    candidates = (
        bundle_root() / file_name,
        bundle_root() / PAYLOAD_DIR_NAME / file_name,
    )
    for candidate in candidates:
        try:
            return candidate.read_text(encoding="utf-8")
        except OSError:
            continue
    return LICENSE_FALLBACK


def installer_licence_text() -> str:
    """Return the installer-wrapper licence notice, or a fallback if absent."""
    candidates = (
        bundle_root() / INSTALLER_LICENSE_FILE_NAME,
        bundle_root() / PAYLOAD_DIR_NAME / INSTALLER_LICENSE_FILE_NAME,
    )
    for candidate in candidates:
        try:
            return candidate.read_text(encoding="utf-8")
        except OSError:
            continue
    return INSTALLER_LICENSE_FALLBACK


def bundled_version_file() -> Path:
    """Return the path to the build-stamped bundled-version text file."""
    return bundle_root() / PAYLOAD_DIR_NAME / BUNDLED_VERSION_FILE_NAME


def app_version() -> str:
    """Return the bundled application version.

    buildinstaller.py stamps the version into a small text file
    (BUNDLED_VERSION_FILE_NAME) inside the payload. That file is read first,
    because the bundled exe cannot be queried in a onefile installer: Nuitka
    strips the loose exe out of the embedded payload, leaving it only inside the
    deploy zip. The exe query is kept as a fallback for layouts where the bundle
    is present unpacked (for example local testing against an extracted
    payload). An empty string is returned when neither source is available.
    """
    stamped = _stamped_version()
    if stamped:
        return stamped
    return _exe_reported_version()


def _stamped_version() -> str:
    """Return the build-stamped bundled version, or '' when not present."""
    try:
        return bundled_version_file().read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _exe_reported_version() -> str:
    """Return the version the bundled exe reports via --version, or ''.

    Fallback only: in a onefile installer the loose exe is stripped from the
    payload, so this returns '' there.
    """
    exe = payload_app_dir() / EXE_NAME
    if not exe.is_file():
        return ""
    no_window = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        result = subprocess.run(
            [str(exe), "--version"],
            capture_output=True,
            text=True,
            timeout=TASKLIST_TIMEOUT_S,
            stdin=subprocess.DEVNULL,
            creationflags=no_window,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    output = (result.stdout or "").strip().splitlines()
    if not output:
        return ""
    # The exe prints "Trainer <version>"; keep the trailing version token.
    tokens = output[-1].split()
    return tokens[-1] if tokens else ""


def install_target() -> Path:
    """Return the per-user install directory for the application."""
    base = os.environ.get(ENV_LOCALAPPDATA)
    root = Path(base) if base else Path.home() / "AppData" / "Local"
    return root / PROGRAMS_DIR_NAME / APP_NAME


def state_dir() -> Path:
    """Return the per-user state directory the app writes (settings, caches)."""
    base = os.environ.get(ENV_LOCALAPPDATA)
    root = Path(base) if base else Path.home() / "AppData" / "Local"
    return root / STATE_DIR_NAME


# ------------------------------------------------------------------- versioning


def version_tuple(version: str) -> tuple[int, ...]:
    """Return a comparable tuple of the numeric parts of a version string."""
    parts: list[int] = []
    for raw in version.strip().split("."):
        digits = "".join(ch for ch in raw if ch.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts) if parts else (0,)


def compare_versions(left: str, right: str) -> int:
    """Return -1, 0 or 1 for left < right, left == right or left > right."""
    a = version_tuple(left)
    b = version_tuple(right)
    if a < b:
        return -1
    if a > b:
        return 1
    return 0


# ----------------------------------------------------------------- deploy/ops


def deploy_files(target: Path) -> Path:
    """Extract the bundled application archive to ``target``; return the exe.

    The bundle ships as a single zip because Nuitka's onefile build drops loose
    executables and DLLs from an included data directory. Any previous install
    at the target is removed first so the result is a clean deployment.
    """
    archive = payload_archive()
    if not archive.is_file():
        raise FileNotFoundError(f"Bundled application not found at {archive}.")
    if target.exists():
        shutil.rmtree(target, ignore_errors=True)
    target.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as bundle:
        bundle.extractall(target)
    return target / EXE_NAME


def original_installer_exe() -> Path:
    """Return the original onefile installer the user launched.

    Under a Nuitka onefile build ``sys.executable`` is the unpacked temporary
    bootstrap rather than the launcher; it must not be registered as the
    uninstaller. The real launcher is exposed through the NUITKA_ONEFILE_BINARY
    environment variable and as ``sys.argv[0]``. Prefer those and fall back to
    ``sys.executable`` only when neither resolves to an executable outside the
    temporary directory.
    """
    temp_root = Path(tempfile.gettempdir()).resolve()
    candidates = (
        os.environ.get(NUITKA_ONEFILE_ENV, ""),
        sys.argv[0] if sys.argv else "",
    )
    for raw in candidates:
        if not raw:
            continue
        try:
            path = Path(raw).resolve()
        except OSError:
            continue
        if path.suffix.lower() != EXE_SUFFIX or not path.is_file():
            continue
        if path == temp_root or temp_root in path.parents:
            continue
        return path
    return Path(sys.executable)


def copy_uninstaller(install_dir: Path) -> Path:
    """Copy this installer into the install root to act as the uninstaller.

    Best effort: the application is already deployed by the time this runs, so
    a failure here degrades to using the running executable as the uninstall
    source rather than failing the whole install.
    """
    source = original_installer_exe()
    destination = install_dir / UNINSTALLER_SUBDIR / UNINSTALLER_NAME
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    except Exception:
        return source
    return destination


def install(
    target: Path, *, desktop: bool, start_menu: bool, autostart: bool
) -> Path:
    """Run the full install/upgrade/reinstall: files, registry and shortcuts."""
    exe_path = deploy_files(target)
    uninstaller = copy_uninstaller(target)
    registry.write_uninstall_entry(
        target, uninstaller, app_version() or FALLBACK_VERSION
    )
    shortcuts.apply_shortcuts(exe_path, desktop=desktop, start_menu=start_menu)
    registry.set_autostart(autostart, exe_path)
    return exe_path


def repair(install_dir: Path) -> Path:
    """Re-deploy the application files over an existing install, then register.

    Without a per-file manifest the safe, simple repair is a full re-copy of the
    bundled files: it restores anything missing or altered. User settings live
    outside the install directory, so they are untouched.
    """
    exe_path = deploy_files(install_dir)
    uninstaller = copy_uninstaller(install_dir)
    registry.write_uninstall_entry(
        install_dir, uninstaller, app_version() or FALLBACK_VERSION
    )
    shortcuts.apply_shortcuts(exe_path, desktop=True, start_menu=True)
    return exe_path


def uninstall(*, remove_settings: bool) -> None:
    """Remove shortcuts, registry, autostart, user state and the install dir."""
    install_dir = registry.installed_location() or install_target()
    shortcuts.remove_shortcut(shortcuts.desktop_link())
    shortcuts.remove_shortcut(shortcuts.start_menu_link())
    registry.remove_autostart()
    registry.delete_uninstall_entry()
    registry.delete_toast_identity()
    if remove_settings:
        shutil.rmtree(state_dir(), ignore_errors=True)
    if install_dir.exists():
        if running_from_inside(install_dir):
            schedule_delete_after_exit(install_dir)
        else:
            shutil.rmtree(install_dir, ignore_errors=True)


def running_from_inside(install_dir: Path) -> bool:
    """Return True when this process's exe lives inside ``install_dir``."""
    try:
        running = Path(sys.executable).resolve()
        root = install_dir.resolve()
    except OSError:
        return True
    return running == root or root in running.parents


def schedule_delete_after_exit(install_dir: Path) -> None:
    """Delete ``install_dir`` from a detached helper once this process exits.

    The registered uninstaller lives inside the install directory, so it cannot
    remove its own running exe. A hidden PowerShell process polls and deletes
    once the lock is released, rather than racing a fixed delay.
    """
    escaped = str(install_dir).replace("'", "''")
    script = (
        f"$d = '{escaped}'; "
        f"for ($i = 0; $i -lt {DEFERRED_DELETE_ATTEMPTS}; $i++) {{ "
        "if (-not (Test-Path -LiteralPath $d)) { break } "
        "Remove-Item -LiteralPath $d -Recurse -Force "
        "-ErrorAction SilentlyContinue; "
        "if (-not (Test-Path -LiteralPath $d)) { break } "
        f"Start-Sleep -Milliseconds {DEFERRED_DELETE_INTERVAL_MS} "
        "}"
    )
    no_window = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    detached = getattr(subprocess, "DETACHED_PROCESS", 0)
    try:
        subprocess.Popen(
            [
                POWERSHELL,
                "-NoProfile",
                "-NonInteractive",
                "-WindowStyle",
                "Hidden",
                "-Command",
                script,
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=no_window | detached,
        )
    except (OSError, subprocess.SubprocessError):
        return


def launch(exe_path: Path) -> None:
    """Start the installed application without waiting for it (best effort)."""
    try:
        subprocess.Popen([str(exe_path)], cwd=str(exe_path.parent))
    except OSError:
        return
