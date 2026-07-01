#!/usr/bin/env bash
# build_flatpak.sh — Build trainer.flatpak for Linux
# Usage: ./build_flatpak.sh
#
# Self-contained: this script generates the launcher, desktop entry, metainfo
# and Flatpak manifest into packaging/ at build time, so only this script needs
# to be committed. Modelled on the Meridian and Calendifier build scripts.
# Trainer runs from source (main.py) staged under /app, with the Python
# dependencies pip-installed into the Flatpak prefix.

set -euo pipefail

APP_ID="com.oliverernster.Trainer"
CMD="trainer"
APP_VERSION=$(python3 -c "import version; print(version.__version__)")
RELEASE_DATE=$(date +%F)
BUNDLE="trainer.flatpak"
BUILD_DIR=".flatpak-build"
REPO_DIR=".flatpak-repo"
MANIFEST="${APP_ID}.yml"

# The KDE runtime bundles Qt6 plus Python 3.12 (PySide6 also ships its own Qt).
RUNTIME="org.kde.Platform"
SDK="org.kde.Sdk"
RUNTIME_VERSION="6.8"
PYTHON_DIR="python3.12"

# ── Colour helpers ────────────────────────────────────────────────────────────
bold=$(tput bold 2>/dev/null || true)
reset=$(tput sgr0 2>/dev/null || true)
section() { echo; echo "${bold}=== $* ===${reset}"; }

# ── Tool checks / install ─────────────────────────────────────────────────────
section "Checking dependencies"

install_if_missing() {
    local pkg="$1"
    if ! command -v "$pkg" &>/dev/null; then
        echo "  $pkg not found, installing..."
        if command -v apt-get &>/dev/null; then
            sudo apt-get update -qq && sudo apt-get install -y "$pkg"
        elif command -v dnf &>/dev/null; then
            sudo dnf install -y "$pkg"
        elif command -v pacman &>/dev/null; then
            sudo pacman -Sy --noconfirm "$pkg"
        elif command -v zypper &>/dev/null; then
            sudo zypper install -y "$pkg"
        else
            echo "ERROR: Cannot install $pkg, unsupported package manager." >&2
            exit 1
        fi
    else
        echo "  $pkg: OK"
    fi
}

install_if_missing flatpak
install_if_missing flatpak-builder

# ── Flatpak remotes ───────────────────────────────────────────────────────────
section "Configuring Flathub remote"
flatpak remote-add --if-not-exists --user flathub \
    https://dl.flathub.org/repo/flathub.flatpakrepo

# ── Runtime / SDK ─────────────────────────────────────────────────────────────
section "Installing runtime and SDK"
flatpak install --user --noninteractive flathub \
    "${RUNTIME}//${RUNTIME_VERSION}" \
    "${SDK}//${RUNTIME_VERSION}" \
    || true

# ── packaging/ helpers ────────────────────────────────────────────────────────
section "Writing packaging helpers"
mkdir -p packaging

cat > packaging/trainer-launcher.sh <<LAUNCHER
#!/bin/sh
export PYTHONPATH="/app:/app/lib/${PYTHON_DIR}/site-packages\${PYTHONPATH:+:\$PYTHONPATH}"
export QT_PLUGIN_PATH="/app/lib/${PYTHON_DIR}/site-packages/PySide6/Qt/plugins"
export QT_QPA_PLATFORM_PLUGIN_PATH="/app/lib/${PYTHON_DIR}/site-packages/PySide6/Qt/plugins/platforms"
export QT_AUTO_SCREEN_SCALE_FACTOR=1
export QT_ENABLE_HIGHDPI_SCALING=1
if [ -n "\$WAYLAND_DISPLAY" ] && [ -z "\$FORCE_X11" ]; then
    export QT_QPA_PLATFORM=wayland
elif [ -n "\$DISPLAY" ]; then
    export QT_QPA_PLATFORM=xcb
else
    export QT_QPA_PLATFORM=xcb
fi
cd /app
exec python3 main.py "\$@"
LAUNCHER
chmod +x packaging/trainer-launcher.sh

cat > "packaging/${APP_ID}.desktop" <<DESKTOP
[Desktop Entry]
Version=1.0
Type=Application
Name=Trainer
GenericName=Train Times Application
Comment=Train times with integrated weather forecasting and astronomical events
Icon=${APP_ID}
Exec=${CMD}
Terminal=false
Categories=Utility;Education;
Keywords=train;railway;times;schedule;weather;astronomy;transport;
StartupNotify=true
StartupWMClass=${CMD}
X-Flatpak=${APP_ID}
DESKTOP

cat > "packaging/${APP_ID}.metainfo.xml" <<XML
<?xml version="1.0" encoding="UTF-8"?>
<component type="desktop-application">
  <id>${APP_ID}</id>
  <name>Trainer</name>
  <summary>Train times with integrated weather forecasting and astronomical events</summary>
  <metadata_license>FSFAP</metadata_license>
  <project_license>GPL-3.0-only</project_license>
  <description>
    <p>Trainer is a desktop train times application for the UK railway network with
    real-time schedules, route planning, integrated weather forecasts and
    astronomical event tracking (sunrise, sunset and moon phases).</p>
  </description>
  <launchable type="desktop-id">${APP_ID}.desktop</launchable>
  <provides>
    <binary>${CMD}</binary>
  </provides>
  <url type="homepage">https://github.com/oliverernster/trainer</url>
  <developer_name>Oliver Ernster</developer_name>
  <releases>
    <release version="${APP_VERSION}" date="${RELEASE_DATE}"/>
  </releases>
  <content_rating type="oars-1.1"/>
</component>
XML

# ── Generate manifest ─────────────────────────────────────────────────────────
section "Writing manifest ${MANIFEST}"

cat > "${MANIFEST}" <<YAML
app-id: ${APP_ID}
runtime: ${RUNTIME}
runtime-version: "${RUNTIME_VERSION}"
sdk: ${SDK}

command: ${CMD}

build-options:
  env:
    PIP_CACHE_DIR: /run/build/trainer/pip-cache
  build-args:
    - --share=network

finish-args:
  - --share=ipc
  - --socket=fallback-x11
  - --socket=wayland
  - --device=dri
  - --share=network
  - --filesystem=home
  - --filesystem=xdg-documents
  - --filesystem=xdg-download
  - --talk-name=org.freedesktop.Notifications
  - --talk-name=org.kde.StatusNotifierWatcher
  - --own-name=${APP_ID}

modules:

  # ── Ensure pip is available ────────────────────────────────────────────────
  - name: python3-pip
    buildsystem: simple
    build-commands:
      - python3 -m ensurepip --upgrade

  # ── PySide6 (Qt for Python; the wheel bundles its own Qt) ──────────────────
  - name: pyside6
    buildsystem: simple
    build-commands:
      - pip3 install --no-cache-dir --prefix=/app "PySide6>=6.5.0"

  # ── Remaining runtime Python dependencies ──────────────────────────────────
  - name: python-deps
    buildsystem: simple
    build-commands:
      - pip3 install --no-cache-dir --prefix=/app "requests>=2.31.0" "aiohttp>=3.8.0" "python-dateutil>=2.8.0" "pydantic>=2.0.0" "imageio>=2.31.0"

  # ── Trainer application (staged source + launcher + assets) ─────────────────
  - name: trainer
    buildsystem: simple
    build-commands:
      - install -d /app
      - cp -r main.py src version.py VERSION assets LICENSE licenses /app/
      - install -Dm755 packaging/trainer-launcher.sh /app/bin/${CMD}
      - install -Dm644 packaging/${APP_ID}.desktop /app/share/applications/${APP_ID}.desktop
      - install -Dm644 packaging/${APP_ID}.metainfo.xml /app/share/metainfo/${APP_ID}.metainfo.xml
      - install -Dm644 assets/trainer_icon_512.png /app/share/icons/hicolor/512x512/apps/${APP_ID}.png
      - install -Dm644 assets/trainer_icon_256.png /app/share/icons/hicolor/256x256/apps/${APP_ID}.png
      - install -Dm644 assets/trainer_icon_128.png /app/share/icons/hicolor/128x128/apps/${APP_ID}.png
      - install -Dm644 assets/trainer_icon_96.png /app/share/icons/hicolor/96x96/apps/${APP_ID}.png
      - install -Dm644 assets/trainer_icon_64.png /app/share/icons/hicolor/64x64/apps/${APP_ID}.png
      - install -Dm644 assets/trainer_icon_48.png /app/share/icons/hicolor/48x48/apps/${APP_ID}.png
      - install -Dm644 assets/trainer_icon_32.png /app/share/icons/hicolor/32x32/apps/${APP_ID}.png
      - install -Dm644 assets/trainer_icon_24.png /app/share/icons/hicolor/24x24/apps/${APP_ID}.png
      - install -Dm644 assets/trainer_icon_16.png /app/share/icons/hicolor/16x16/apps/${APP_ID}.png
    sources:
      - type: dir
        path: .
YAML

echo "  Manifest written."

# ── Build ─────────────────────────────────────────────────────────────────────
section "Building Flatpak"
rm -rf "${BUILD_DIR}" "${REPO_DIR}"

flatpak-builder \
    --user \
    --install-deps-from=flathub \
    --force-clean \
    --repo="${REPO_DIR}" \
    "${BUILD_DIR}" \
    "${MANIFEST}"

# ── Bundle ────────────────────────────────────────────────────────────────────
section "Bundling to ${BUNDLE}"
flatpak build-bundle \
    --runtime-repo=https://dl.flathub.org/repo/flathub.flatpakrepo \
    "${REPO_DIR}" \
    "${BUNDLE}" \
    "${APP_ID}"

echo
echo "${bold}Build complete: ${BUNDLE}${reset}"
echo
echo "Install with:"
echo "  flatpak install --user ${BUNDLE}"
echo
echo "Run with:"
echo "  flatpak run ${APP_ID}"
