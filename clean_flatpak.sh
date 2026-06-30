#!/usr/bin/env bash
# clean_flatpak.sh — Uninstall the Trainer Flatpak and remove build artefacts.
# Usage: ./clean_flatpak.sh [--user|--system|--all] [--kill] [--purge-data]
#
# Scoped to Flatpak only: it never touches the Windows (dist-installer/) or
# macOS (trainer-macos-arm64.dmg) outputs, so the three build paths stay
# independent.

set -euo pipefail

APP_ID="com.oliverernster.Trainer"
BUNDLE="trainer.flatpak"
MANIFEST="${APP_ID}.yml"

bold=$(tput bold 2>/dev/null || true)
reset=$(tput sgr0 2>/dev/null || true)
section() { echo; echo "${bold}=== $* ===${reset}"; }

MODE="--all"      # default: clean both user and system installs
PURGE_DATA=0
KILL_RUNNING=0

usage() {
  cat <<'EOF'
Usage: ./clean_flatpak.sh [--user|--system|--all] [--kill] [--purge-data]

Removes the installed Trainer Flatpak(s) and local build artefacts.

Options:
  --user        Uninstall the per-user install
  --system      Uninstall the system-wide install (may prompt for auth)
  --all         Try both --user and --system (default)
  --kill        Attempt to terminate a running instance first (flatpak kill)
  --purge-data  Also remove leftover user data folder (~/.var/app/<APP_ID>)
  -h, --help    Show this help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --user)   MODE="--user" ;;
    --system) MODE="--system" ;;
    --all)    MODE="--all" ;;
    --kill)   KILL_RUNNING=1 ;;
    --purge-data) PURGE_DATA=1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1"; usage; exit 2 ;;
  esac
  shift
done

if ! command -v flatpak >/dev/null 2>&1; then
  echo "flatpak is not installed or not on PATH"
  exit 1
fi

uninstall_one_scope() {
  local scope="$1"   # --user or --system
  if flatpak info "$scope" "$APP_ID" >/dev/null 2>&1; then
    echo "Uninstalling $APP_ID ($scope)..."
    flatpak uninstall "$scope" -y --delete-data "$APP_ID" || true
  else
    echo "$APP_ID not installed ($scope)"
  fi
  # Also remove any app extensions (e.g. locales) if present.
  local ext_ids
  ext_ids=$(flatpak list "$scope" --app --columns=application 2>/dev/null | grep -E "^${APP_ID}\\." || true)
  if [[ -n "${ext_ids}" ]]; then
    echo "Uninstalling extensions ($scope):"
    echo "${ext_ids}" | sed 's/^/  - /'
    # shellcheck disable=SC2086
    flatpak uninstall "$scope" -y --delete-data ${ext_ids} || true
  fi
}

cleanup_desktop_integration() {
  # Some install flows copy a desktop file and icons into ~/.local/share/*.
  # Flatpak uninstall does not remove these, leaving a ghost launcher entry.
  local desktop_file="${HOME}/.local/share/applications/${APP_ID}.desktop"
  if [[ -f "$desktop_file" ]]; then
    echo "Removing local desktop file: $desktop_file"
    rm -f "$desktop_file" || true
  fi
  local icon_root="${HOME}/.local/share/icons/hicolor"
  if [[ -d "$icon_root" ]]; then
    find "$icon_root" -type f -path "*/apps/${APP_ID}.*" -print -delete 2>/dev/null || true
  fi
  if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "${HOME}/.local/share/applications" 2>/dev/null || true
  fi
  if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -f -t "${icon_root}" 2>/dev/null || true
  fi
}

cleanup_lock_files() {
  # Stale singleton lock files created by the app (not Flatpak-managed).
  local tmp_lock="/tmp/trainer_app_ultra_early.lock"
  local runtime_lock=""
  if [[ -n "${XDG_RUNTIME_DIR:-}" ]]; then
    runtime_lock="${XDG_RUNTIME_DIR}/trainer_app_ultra_early.lock"
  fi
  [[ -f "$tmp_lock" ]] && { echo "Removing lock file: $tmp_lock"; rm -f "$tmp_lock" || true; }
  [[ -n "$runtime_lock" && -f "$runtime_lock" ]] && { echo "Removing lock file: $runtime_lock"; rm -f "$runtime_lock" || true; }
}

cleanup_build_artefacts() {
  # Flatpak build artefacts and generated packaging files only.
  rm -f "${BUNDLE}" "${MANIFEST}"
  rm -rf .flatpak-build .flatpak-repo .flatpak-builder packaging
}

if [[ "$KILL_RUNNING" -eq 1 ]]; then
  echo "Attempting to stop any running instance (flatpak kill)..."
  flatpak kill "$APP_ID" 2>/dev/null || true
fi

section "Uninstalling Flatpak"
case "$MODE" in
  --user|--system) uninstall_one_scope "$MODE" ;;
  --all) uninstall_one_scope "--user"; uninstall_one_scope "--system" ;;
esac

section "Cleaning desktop integration and locks"
cleanup_desktop_integration
cleanup_lock_files

section "Removing build artefacts"
cleanup_build_artefacts

if [[ "$PURGE_DATA" -eq 1 ]]; then
  data_dir="${HOME}/.var/app/${APP_ID}"
  if [[ -d "$data_dir" ]]; then
    echo "Removing leftover user data dir: $data_dir"
    rm -rf "$data_dir"
  fi
fi

echo
echo "Done."
