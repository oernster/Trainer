#!/usr/bin/env python3
"""Build the Trainer Windows installer.

This mirrors the author's installer approach (Fulcrum is the canonical
reference): a self-contained GUI installer executable that carries the built
application as an embedded payload plus the LICENSE text. The installer UI is a
PySide6 program compiled with Nuitka (the same toolchain used for the
application itself), so end users get a single double-clickable setup binary
with no external installer framework (no Inno Setup / NSIS) required.

Two-step workflow (run from the project root):

    1) Build the app bundle:   python buildexe.py
    2) Build the installer:    python buildinstaller.py

Step 1 writes the standalone bundle to installer/payload/Trainer. Step 2 zips
that bundle (alongside the LICENSE and the LGPL notices) into the installer
payload, then compiles the installer UI (installer/app.py) into a single
onefile executable.

The bundle ships as a single zip because Nuitka's onefile build strips loose
executables and DLLs from an included data directory; the installer extracts
the zip on deploy to restore the exe and its DLLs.

Trainer is single-licensed GPL-3.0 (PySide6 is LGPL but Trainer is not
dual-licensed), so a single LICENSE plus the PySide6 LGPL notices and the
installer-wrapper INSTALLER_LICENSE ship, rather than Fulcrum's split GPL/LGPL
pair. The version is read from version.py (__version__), not a VERSION file,
and there is no stamp_version step to run.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from version import (
    __app_name__,
    __company__,
    __copyright__,
    __description__,
    __version__,
)

# --- Project identity (single source of truth for installer metadata) -------
APP_DISPLAY_NAME = __app_name__
APP_DESCRIPTION = __description__
APP_COMPANY = __company__
APP_COPYRIGHT = __copyright__
INSTALLER_NAME = "TrainerSetup"

# Repository layout, resolved relative to this script.
PROJECT_ROOT = Path(__file__).resolve().parent
LICENSE_FILE = PROJECT_ROOT / "LICENSE"
LICENSES_DIR = PROJECT_ROOT / "licenses"
INSTALLER_LICENSE_FILE = PROJECT_ROOT / "INSTALLER_LICENSE"
ICON_FILE = PROJECT_ROOT / "assets" / "trainer.ico"

# The PySide6 LGPL notices staged into the payload and shipped beside the
# installer binary so the licence buttons can show them without unpacking.
LICENSE_NOTICES = (
    LICENSES_DIR / "LGPL-3.0.txt",
    LICENSES_DIR / "THIRD_PARTY_LICENSES.txt",
)

# Installer UI entry point and payload locations. buildexe.py writes the
# standalone bundle directly into installer/payload/Trainer, so the bundle the
# installer packages is found there (not under dist/main.dist).
INSTALLER_DIR = PROJECT_ROOT / "installer"
INSTALLER_ENTRY = INSTALLER_DIR / "app.py"
PAYLOAD_DIR_NAME = "payload"
PAYLOAD_STAGE_DIR = INSTALLER_DIR / PAYLOAD_DIR_NAME
APP_BUNDLE_DIR = PAYLOAD_STAGE_DIR / APP_DISPLAY_NAME

# Staging + output locations. The installer is compiled into a temporary dist
# folder and then moved into place, so a running copy of an older installer
# cannot break the build mid-compile.
FINAL_DIST_DIR = PROJECT_ROOT / "dist-installer"
TEMP_DIST_DIR = PROJECT_ROOT / "dist-installer.build"

# Structural defaults.
DEFAULT_VERSION = "0.0.0-dev"
DEFAULT_JOBS = 1
PE_VERSION_PARTS = 4
PE_VERSION_PAD_VALUE = "0"
CONSOLE_MODE = "disable"

# Retry parameters for deleting a file briefly locked by AV/Explorer.
UNLINK_ATTEMPTS = 20
UNLINK_DELAY_SECONDS = 0.15


def read_version() -> str:
    """Return the project version from version.py, or a safe default."""
    return __version__ or DEFAULT_VERSION


def to_pe_version(version: str) -> str:
    """Normalise a semantic version into the 4-part numeric form Nuitka wants."""
    numeric_parts: list[str] = []
    for raw_part in version.split("."):
        digits = "".join(ch for ch in raw_part if ch.isdigit())
        numeric_parts.append(digits if digits else PE_VERSION_PAD_VALUE)
        if len(numeric_parts) == PE_VERSION_PARTS:
            break
    while len(numeric_parts) < PE_VERSION_PARTS:
        numeric_parts.append(PE_VERSION_PAD_VALUE)
    return ".".join(numeric_parts)


def resolve_python() -> str:
    """Return the interpreter to drive Nuitka (prefer the project venv)."""
    venv_python = PROJECT_ROOT / "venv" / "Scripts" / "python.exe"
    if venv_python.exists():
        return str(venv_python)
    return sys.executable


def parallel_jobs() -> str:
    """Return the number of parallel compile jobs as a string."""
    return str(os.cpu_count() or DEFAULT_JOBS)


def require_windows() -> None:
    if os.name != "nt":
        raise SystemExit("[buildinstaller] buildinstaller.py is Windows-only.")


def retry_unlink(path: Path) -> None:
    """Delete a file that may be briefly locked by AV/Explorer."""
    if not path.exists():
        return
    last_exc: Exception | None = None
    for _ in range(UNLINK_ATTEMPTS):
        try:
            path.unlink(missing_ok=True)
            return
        except OSError as exc:
            last_exc = exc
            time.sleep(UNLINK_DELAY_SECONDS)
    if last_exc:
        raise last_exc


def replace_file(src: Path, dst: Path) -> None:
    """Replace dst with src, tolerating a locked destination on Windows."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        retry_unlink(dst)
    shutil.move(str(src), str(dst))


def stage_payload() -> None:
    """Archive the built app bundle and stage the licences into the payload dir.

    buildexe.py already placed the standalone bundle at APP_BUNDLE_DIR; this
    step adds the deploy archive (a zip of the bundle) and the licence texts
    next to it. The bundle directory itself is left in place because the
    installer UI reads its non-binary files (icon) directly.
    """
    if not APP_BUNDLE_DIR.exists():
        raise SystemExit(
            f"[buildinstaller] App bundle not found at {APP_BUNDLE_DIR}.\n"
            "Run `python buildexe.py` first to produce the standalone bundle."
        )

    # Nuitka's onefile build strips loose executables and DLLs from an included
    # data directory, so the staged bundle ships only the app's non-binary
    # files (enough for the installer UI). Archive the full bundle into a single
    # zip too: a zip is opaque data that Nuitka embeds verbatim and the
    # installer extracts it on deploy to restore the exe and its DLLs.
    archive_base = str(APP_BUNDLE_DIR)
    archive_path = shutil.make_archive(
        archive_base, "zip", root_dir=str(APP_BUNDLE_DIR)
    )
    print(f"[buildinstaller] Archived bundle for deploy: {archive_path}")

    if LICENSE_FILE.exists():
        shutil.copy2(LICENSE_FILE, PAYLOAD_STAGE_DIR / "LICENSE")
        print(f"[buildinstaller] Staged LICENSE into payload from {LICENSE_FILE}")
    else:
        print(f"[buildinstaller] WARNING: LICENSE not found at {LICENSE_FILE}.")
    for notice in LICENSE_NOTICES:
        if notice.exists():
            shutil.copy2(notice, PAYLOAD_STAGE_DIR / notice.name)
            print(f"[buildinstaller] Staged {notice.name} into payload")


def build_installer() -> int:
    """Compile the installer UI into a onefile executable. Returns a code."""
    require_windows()

    if not INSTALLER_ENTRY.exists():
        raise SystemExit(
            f"[buildinstaller] Installer UI entry script not found at "
            f"{INSTALLER_ENTRY}.\n"
            "Provide installer/app.py (the PySide6 installer UI) first."
        )

    version = read_version()
    pe_version = to_pe_version(version)
    python_exe = resolve_python()
    jobs = parallel_jobs()

    print(
        f"[buildinstaller] Building {INSTALLER_NAME} for "
        f"{APP_DISPLAY_NAME} {version}"
    )
    print(f"[buildinstaller] Installer UI: {INSTALLER_ENTRY}")
    print(f"[buildinstaller] Python: {python_exe}")
    print(f"[buildinstaller] Parallel jobs: {jobs}")

    # 1) Stage the payload (zip of the built bundle + licence texts).
    stage_payload()

    # 2) Reset temporary build/output locations.
    for path in (TEMP_DIST_DIR,):
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)

    nuitka_args: list[str] = [
        python_exe,
        "-m",
        "nuitka",
        "--onefile",
        "--assume-yes-for-downloads",
        "--enable-plugin=pyside6",
        f"--jobs={jobs}",
        f"--windows-console-mode={CONSOLE_MODE}",
        f"--output-dir={TEMP_DIST_DIR}",
        f"--output-filename={INSTALLER_NAME}.exe",
        # Windows PE version metadata for the installer binary.
        f"--company-name={APP_COMPANY}",
        f"--product-name={APP_DISPLAY_NAME} Setup",
        f"--file-version={pe_version}",
        f"--product-version={pe_version}",
        f"--file-description={APP_DESCRIPTION} Installer",
        f"--copyright={APP_COPYRIGHT}",
        # Embed the staged payload (app bundle + zip + licences) in the
        # installer.
        f"--include-data-dir={PAYLOAD_STAGE_DIR}={PAYLOAD_DIR_NAME}",
    ]

    if ICON_FILE.exists():
        nuitka_args.append(f"--windows-icon-from-ico={ICON_FILE}")
        print(f"[buildinstaller] Icon: {ICON_FILE}")
    else:
        print(
            f"[buildinstaller] WARNING: icon not found at {ICON_FILE}; "
            "building installer without an embedded icon."
        )

    # Ship the LICENSE alongside the binary too, so the installer UI can show
    # it directly without unpacking the payload first.
    if LICENSE_FILE.exists():
        nuitka_args.append(f"--include-data-file={LICENSE_FILE}=LICENSE")

    # Ship the PySide6 LGPL notices for the third-party licence display.
    for notice in LICENSE_NOTICES:
        if notice.exists():
            nuitka_args.append(f"--include-data-file={notice}={notice.name}")

    # Ship the installer-wrapper licence notice next to the binary as well.
    if INSTALLER_LICENSE_FILE.exists():
        nuitka_args.append(
            f"--include-data-file={INSTALLER_LICENSE_FILE}=INSTALLER_LICENSE"
        )

    nuitka_args.append(str(INSTALLER_ENTRY))

    print("[buildinstaller] Running Nuitka with args:")
    for part in nuitka_args:
        print("  ", part)

    result = subprocess.run(nuitka_args, cwd=str(PROJECT_ROOT))
    if result.returncode != 0:
        print(
            f"[buildinstaller] ERROR: Nuitka build failed "
            f"(exit {result.returncode}).",
            file=sys.stderr,
        )
        return result.returncode

    built_exe = TEMP_DIST_DIR / f"{INSTALLER_NAME}.exe"
    final_exe = FINAL_DIST_DIR / f"{INSTALLER_NAME}.exe"

    if not built_exe.exists():
        print(
            f"[buildinstaller] ERROR: build finished but {built_exe} "
            "was not found.\nCheck the Nuitka output above for details.",
            file=sys.stderr,
        )
        return 1

    try:
        replace_file(built_exe, final_exe)
    except PermissionError as exc:
        raise SystemExit(
            "[buildinstaller] Unable to overwrite the installer EXE because it "
            "is in use.\nClose any running installer instances, then try again."
        ) from exc

    shutil.rmtree(TEMP_DIST_DIR, ignore_errors=True)

    size_mb = final_exe.stat().st_size / (1024 * 1024)
    print(f"[buildinstaller] [OK] Built installer: {final_exe}")
    print(f"[buildinstaller] Installer size: {size_mb:.1f} MB")
    return 0


def main() -> int:
    return build_installer()


if __name__ == "__main__":
    raise SystemExit(main())
