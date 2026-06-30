# Trainer Development Guide

How to set up a development environment, run the app and tests, regenerate icons
and build distributable packages on each platform. For the runtime architecture
see [ARCHITECTURE.md](ARCHITECTURE.md); for the testing setup see [TESTING.md](TESTING.md).

## Prerequisites

- Python 3.13 (3.9+ runs, the project targets 3.13).
- Git.
- Platform build tooling, installed only for the platform you package on:
  - Windows: a working C toolchain for Nuitka (MSVC build tools); Nuitka downloads its
    own dependencies on first run.
  - Linux: `flatpak` and `flatpak-builder` (the build script installs them via the system
    package manager if missing).
  - macOS (Apple Silicon): Nuitka and `create-dmg` (the DMG script installs `create-dmg`
    via Homebrew if missing). Code signing and notarisation are optional (see below).

## Development setup

```bash
git clone <repo> trainer
cd trainer
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python3 main.py                 # Windows: python main.py
```

`requirements.txt` is the full development set (runtime dependencies plus the test,
lint and build tools). The runtime-only subset that ships in the Flatpak is pinned
inside `build_flatpak.sh`.

## Versioning

`version.py` is the single source of truth. `__version__` and `__version_info__` there
drive the app, the packaging metadata and the `--version` CLI output. Nothing else
hardcodes a version. Bump both fields together (a minor bump resets the patch to 0,
e.g. 5.0.3 then 5.1.0). The version single-source-of-truth is enforced by
`tests/test_version_single_source_of_truth.py`.

## Running the tests

```bash
QT_QPA_PLATFORM=offscreen python -m pytest
```

A 100% branch-coverage gate is enforced on the stable core (`src/core/models` and
`src/core/interfaces`). Trust the exit code: `0` means all tests passed and the gate
was met. See [TESTING.md](TESTING.md) for the full picture.

## Icons

All platform icon assets derive from one master, `trainer.png` at the repo root
(square, 1024x1024 RGBA). Regenerate the whole set after changing the master:

```bash
python generate_icons.py
```

This writes into `assets/`: `trainer_icon_<size>.png` for 16 through 1024, the
canonical `trainer_icon.png` (256), the multi-size Windows `trainer.ico` and the
macOS `trainer.icns`. The build scripts and the in-app icon resolver
(`src/utils/icon_resolver.py`) consume this set, so do not hand-edit individual sizes.

## Building per platform

Every build reads the version from `version.py` and bundles the railway data
(`src/data`) plus `assets/`. Build artefacts are gitignored.

### Windows (Nuitka standalone plus a themed per-user installer)

```bash
python buildexe.py          # standalone bundle -> installer/payload/Trainer/trainer.exe
python buildinstaller.py    # wraps the bundle -> dist-installer/TrainerSetup.exe
```

`buildexe.py` produces the standalone application tree under `installer/payload/Trainer/`.
`buildinstaller.py` zips that tree and wraps a bespoke per-user GUI installer (themed to
the app's Material blue) into `dist-installer/TrainerSetup.exe`. The installer needs no
administrator rights: it deploys to `%LOCALAPPDATA%\Programs\Trainer`, registers an
entry under `HKCU\...\Uninstall\Trainer`, offers Desktop and Start-Menu shortcuts and
registers itself as the uninstaller.

### Linux (Flatpak)

```bash
./build_flatpak.sh          # produces trainer.flatpak
flatpak install --user trainer.flatpak
flatpak run com.oliverernster.Trainer
```

`build_flatpak.sh` is self-contained: it generates the launcher, the desktop entry, the
AppStream metainfo and the Flatpak manifest into `packaging/` at build time, targets the
KDE 6.8 runtime (Qt6 plus Python 3.12), pip-installs the runtime dependency subset into
the Flatpak prefix and stages the app to run from source. Clean up with:

```bash
./clean_flatpak.sh          # uninstall plus remove build artefacts (Flatpak only)
./clean_flatpak.sh --purge-data   # also remove ~/.var/app/com.oliverernster.Trainer
```

### macOS (Apple Silicon DMG)

```bash
python3 builddmg.py         # produces trainer-macos-arm64.dmg
```

`builddmg.py` builds a self-contained `.app` with Nuitka (Python and PySide6 are frozen
in, so there is no dependency on the system interpreter) then creates a drag-to-install
DMG. By default the DMG is unsigned and is fine for local installation; Gatekeeper will
quarantine it on other machines. To sign and notarise, set the environment variables
`DEVELOPER_ID_APPLICATION`, `APPLE_ID`, `APPLE_APP_PASSWORD` and `APPLE_TEAM_ID` before
running (notarisation is skipped when `APPLE_ID` or `APPLE_APP_PASSWORD` is absent).

## Build outputs and cleanup

| Platform | Command | Output |
|---|---|---|
| Windows bundle | `python buildexe.py` | `installer/payload/Trainer/` |
| Windows installer | `python buildinstaller.py` | `dist-installer/TrainerSetup.exe` |
| Linux | `./build_flatpak.sh` | `trainer.flatpak` |
| macOS | `python3 builddmg.py` | `trainer-macos-arm64.dmg` |

All of the above plus the Nuitka intermediate trees (`*.build/`, `*.dist/`,
`*.onefile-build/`), the Flatpak working dirs (`.flatpak-build/`, `.flatpak-repo/`,
`.flatpak-builder/`, `packaging/`, the generated manifest) and `coverage.json` are
gitignored. The generated `assets/` icons and the master `trainer.png` are committed
source, not artefacts.
