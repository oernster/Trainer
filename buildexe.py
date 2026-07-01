#!/usr/bin/env python3
"""Build the Trainer standalone Windows executable with Nuitka.

This produces a self-contained GUI executable so that end users do NOT need a
system-wide Python installation. It mirrors the Nuitka invocation style used by
the author's other PySide6 desktop builds (Fulcrum is the canonical reference)
and additionally embeds Windows PE version metadata (product name, versions,
file description and copyright).

Usage (from the project root, with the venv active or detected):

    python buildexe.py

Nuitka notes:

- --standalone: produce a self-contained app directory (no system Python).
- --enable-plugin=pyside6: ensures Qt/PySide6 integration.
- --jobs=N: parallel C compilation across logical cores.
- --windows-console-mode=disable: GUI app, no console window.
- The railway data (src/data) and the assets directory are bundled as data
  directories so the running app's offline-data resolver
  (src.utils.data_path_resolver.get_data_directory) finds src/data beside the
  executable in the frozen build. The GPL-3.0 LICENSE and the PySide6 LGPL
  notices are shipped at the bundle root for the in-app Help menu.

Trainer differs from Fulcrum in three ways that are reflected below:

1. The single source of truth for the version is the root VERSION file.
   version.py reads it, this script inherits it through __version__, and the
   file is bundled beside the executable so the frozen app reads the same
   value. There is no stamp_version step to run.
2. Trainer is single-licensed GPL-3.0 (PySide6 is LGPL but Trainer is not
   dual-licensed), so a single LICENSE plus the PySide6 LGPL notices ship,
   rather than Fulcrum's split GPL/LGPL pair.
3. The payload data is shipped as directories (src/data, assets) because the
   offline-data resolver locates src/data relative to the bundle, not as loose
   files beside the exe.

The standalone bundle is written directly into the installer payload directory
(installer/payload/Trainer) so buildinstaller.py can package it without an
intermediate copy step.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from version import (
    __app_name__,
    __company__,
    __copyright__,
    __description__,
    __version__,
)

# --- Project identity (single source of truth for build metadata) -----------
APP_DISPLAY_NAME = __app_name__
APP_DESCRIPTION = __description__
APP_COMPANY = __company__
APP_COPYRIGHT = __copyright__
EXE_NAME = "trainer"

# Repository layout, resolved relative to this script so the build works from
# any working directory.
PROJECT_ROOT = Path(__file__).resolve().parent
ENTRY_SCRIPT = PROJECT_ROOT / "main.py"
ICON_FILE = PROJECT_ROOT / "assets" / "trainer.ico"
LICENSE_FILE = PROJECT_ROOT / "LICENSE"
LICENSES_DIR = PROJECT_ROOT / "licenses"
# Single source of truth for the version; shipped beside the exe so the frozen
# app reads the same value version.py resolves in a dev checkout.
VERSION_FILE = PROJECT_ROOT / "VERSION"

# Data directories bundled into the standalone tree. The offline-data resolver
# (src.utils.data_path_resolver) finds src/data relative to the executable in
# the frozen build, so the railway JSON (incl. src/data/lines/*.json) and the
# assets directory ship as data directories rather than loose files.
DATA_DIRS = (
    (PROJECT_ROOT / "src" / "data", "src/data"),
    (PROJECT_ROOT / "assets", "assets"),
)

# The PySide6 LGPL notices shipped at the bundle root for the in-app Help menu.
LICENSE_NOTICES = (
    LICENSES_DIR / "LGPL-3.0.txt",
    LICENSES_DIR / "THIRD_PARTY_LICENSES.txt",
)

# The bundle is produced straight into the installer payload so the installer
# build can pick it up without a separate staging copy.
INSTALLER_DIR = PROJECT_ROOT / "installer"
PAYLOAD_DIR = INSTALLER_DIR / "payload"
OUTPUT_DIR = PAYLOAD_DIR
BUNDLE_DIR_NAME = APP_DISPLAY_NAME

# Defaults that are structural, not domain values.
DEFAULT_VERSION = "0.0.0-dev"
DEFAULT_JOBS = 1

# Nuitka requires a 4-part numeric version (a.b.c.d) for the PE resource.
PE_VERSION_PARTS = 4
PE_VERSION_PAD_VALUE = "0"

# Console-mode toggles. Set TRAINER_DEBUG_CONSOLE=1 to build a console-visible
# binary for diagnosing the packaged app; release builds keep it disabled.
CONSOLE_MODE_DEBUG = "attach"
CONSOLE_MODE_RELEASE = "disable"
DEBUG_CONSOLE_ENV_VAR = "TRAINER_DEBUG_CONSOLE"
TRUTHY_VALUES = {"1", "true", "yes", "on"}


def read_version() -> str:
    """Return the project version from the root VERSION file.

    The VERSION file is the single source of truth. version.py reads the same
    file, so ``__version__`` is used only as a fallback if the file cannot be
    read directly at build time.
    """
    try:
        text = VERSION_FILE.read_text(encoding="utf-8").strip()
        if text:
            return text
    except OSError:
        pass
    return __version__ or DEFAULT_VERSION


def to_pe_version(version: str) -> str:
    """Normalise a semantic version into the 4-part numeric form Nuitka wants.

    Non-numeric suffixes (for example a pre-release tag) are dropped, and the
    tuple is padded or truncated to exactly PE_VERSION_PARTS numeric segments.
    """
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
    """Return the interpreter to drive Nuitka.

    Prefer the project venv interpreter when this script was launched with a
    different one; otherwise use the current interpreter.
    """
    venv_python = PROJECT_ROOT / "venv" / "Scripts" / "python.exe"
    if venv_python.exists():
        return str(venv_python)
    return sys.executable


def parallel_jobs() -> str:
    """Return the number of parallel compile jobs as a string."""
    return str(os.cpu_count() or DEFAULT_JOBS)


def build_exe() -> int:
    """Build the standalone executable with Nuitka. Returns a process code."""
    if os.name != "nt":
        print("[buildexe] ERROR: buildexe.py targets Windows.", file=sys.stderr)
        return 1

    if not ENTRY_SCRIPT.exists():
        print(
            f"[buildexe] ERROR: entry point not found at {ENTRY_SCRIPT}.\n"
            "Create main.py at the repo root before building.",
            file=sys.stderr,
        )
        return 1

    version = read_version()
    pe_version = to_pe_version(version)
    console_mode = (
        CONSOLE_MODE_DEBUG
        if os.environ.get(DEBUG_CONSOLE_ENV_VAR, "").lower() in TRUTHY_VALUES
        else CONSOLE_MODE_RELEASE
    )
    python_exe = resolve_python()
    jobs = parallel_jobs()

    print(f"[buildexe] Building {APP_DISPLAY_NAME} {version} (PE {pe_version})")
    print(f"[buildexe] Entry script: {ENTRY_SCRIPT}")
    print(f"[buildexe] Python: {python_exe}")
    print(f"[buildexe] Parallel jobs: {jobs}")
    print(f"[buildexe] Windows console mode: {console_mode}")
    print(f"[buildexe] Output directory: {OUTPUT_DIR}")

    # Remove a previous standalone tree so stale files cannot leak into a build.
    standalone_dir = OUTPUT_DIR / f"{ENTRY_SCRIPT.stem}.dist"
    if standalone_dir.exists():
        print(f"[buildexe] Removing previous build: {standalone_dir}")
        shutil.rmtree(standalone_dir, ignore_errors=True)

    # Remove a previous renamed bundle too.
    final_bundle_dir = OUTPUT_DIR / BUNDLE_DIR_NAME
    if final_bundle_dir.exists():
        print(f"[buildexe] Removing previous bundle: {final_bundle_dir}")
        shutil.rmtree(final_bundle_dir, ignore_errors=True)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    nuitka_args: list[str] = [
        python_exe,
        "-m",
        "nuitka",
        "--standalone",
        "--assume-yes-for-downloads",
        "--enable-plugin=pyside6",
        f"--jobs={jobs}",
        f"--windows-console-mode={console_mode}",
        f"--output-dir={OUTPUT_DIR}",
        f"--output-filename={EXE_NAME}.exe",
        # Windows PE version metadata.
        f"--company-name={APP_COMPANY}",
        f"--product-name={APP_DISPLAY_NAME}",
        f"--file-version={pe_version}",
        f"--product-version={pe_version}",
        f"--file-description={APP_DESCRIPTION}",
        f"--copyright={APP_COPYRIGHT}",
    ]

    # Embed the application icon when present.
    if ICON_FILE.exists():
        nuitka_args.append(f"--windows-icon-from-ico={ICON_FILE}")
        print(f"[buildexe] Icon: {ICON_FILE}")
    else:
        print(
            f"[buildexe] WARNING: icon not found at {ICON_FILE}; "
            "building without it."
        )

    # Bundle the railway data and assets as data directories so the offline-data
    # resolver finds src/data beside the executable in the frozen build.
    for source, target in DATA_DIRS:
        if source.is_dir():
            nuitka_args.append(f"--include-data-dir={source}={target}")
            print(f"[buildexe] Bundling data dir: {source} -> {target}")
        else:
            print(
                f"[buildexe] WARNING: data dir not found at {source}; skipping."
            )

    # Ship the VERSION file at the bundle root so version.py reads the same
    # single source of truth at runtime as it does in a dev checkout.
    if VERSION_FILE.exists():
        nuitka_args.append(f"--include-data-file={VERSION_FILE}=VERSION")
        print(f"[buildexe] Bundling data file: {VERSION_FILE} -> VERSION")
    else:
        print(f"[buildexe] WARNING: VERSION not found at {VERSION_FILE}.")

    # Ship the GPL-3.0 LICENSE so the in-app Help can show the app licence.
    if LICENSE_FILE.exists():
        nuitka_args.append(f"--include-data-file={LICENSE_FILE}=LICENSE")
        print(f"[buildexe] Bundling data file: {LICENSE_FILE} -> LICENSE")
    else:
        print(f"[buildexe] WARNING: LICENSE not found at {LICENSE_FILE}.")

    # Ship the PySide6 LGPL notices for the third-party licence display.
    for notice in LICENSE_NOTICES:
        if notice.exists():
            nuitka_args.append(f"--include-data-file={notice}={notice.name}")
            print(f"[buildexe] Bundling notice: {notice} -> {notice.name}")

    nuitka_args.append(str(ENTRY_SCRIPT))

    print("[buildexe] Running Nuitka with args:")
    for part in nuitka_args:
        print("  ", part)

    result = subprocess.run(nuitka_args, cwd=str(PROJECT_ROOT))
    if result.returncode != 0:
        print(
            f"[buildexe] ERROR: Nuitka build failed (exit {result.returncode}).",
            file=sys.stderr,
        )
        return result.returncode

    # Rename the Nuitka output (main.dist) to the product bundle name so the
    # payload directory is installer/payload/Trainer.
    exe_path = standalone_dir / f"{EXE_NAME}.exe"
    if not exe_path.exists():
        print(
            f"[buildexe] ERROR: build finished but {exe_path} was not found.\n"
            "Check the Nuitka output above for details.",
            file=sys.stderr,
        )
        return 1

    print(f"[buildexe] Renaming bundle: {standalone_dir} -> {final_bundle_dir}")
    shutil.move(str(standalone_dir), str(final_bundle_dir))

    final_exe = final_bundle_dir / f"{EXE_NAME}.exe"
    size_mb = final_exe.stat().st_size / (1024 * 1024)
    print(f"[buildexe] [OK] Build complete: {final_exe}")
    print(f"[buildexe] Executable size: {size_mb:.1f} MB")
    print(f"[buildexe] Standalone bundle: {final_bundle_dir}")
    return 0


def main() -> int:
    return build_exe()


if __name__ == "__main__":
    raise SystemExit(main())
