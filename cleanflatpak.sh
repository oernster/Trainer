#!/usr/bin/env bash
set -euo pipefail

APP_ID="com.oliverernster.Trainer"

if ! command -v flatpak >/dev/null 2>&1; then
  echo "flatpak is not installed or not on PATH"
  exit 1
fi

MODE="--all"  # default: clean both user and system installs
PURGE_DATA=0
KILL_RUNNING=0

usage() {
  cat <<'EOF'
Usage: ./cleanflatpak.sh [--user|--system|--all] [--purge-data]

Removes the installed Trainer Flatpak(s): com.oliverernster.Trainer

Options:
  --user        Uninstall the per-user install
  --system      Uninstall the system-wide install (may prompt for auth)
  --all         Try both --user and --system (default)
  --kill         Attempt to terminate a running instance first (flatpak kill)
  --purge-data  Also remove leftover user data folder (~/.var/app/<APP_ID>)
EOF
}

cleanup_desktop_integration() {
  # Some install flows (e.g. older versions of build_flatpak.sh) copy a desktop
  # file and icons into ~/.local/share/* in addition to Flatpak exports.
  # Flatpak uninstall does not remove these extra copies, which can leave a
  # “ghost” launcher entry in the desktop environment.

  local desktop_file="${HOME}/.local/share/applications/${APP_ID}.desktop"

  if [[ -f "$desktop_file" ]]; then
    echo "Removing local desktop file: $desktop_file"
    rm -f "$desktop_file" || true
  fi

  # Remove any locally installed icons for this app id
  local icon_root="${HOME}/.local/share/icons/hicolor"
  if [[ -d "$icon_root" ]]; then
    # Typical locations used by build scripts
    find "$icon_root" -type f -path "*/apps/${APP_ID}.*" -print -delete 2>/dev/null || true
  fi

  # Refresh desktop db and icon cache (best-effort)
  if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "${HOME}/.local/share/applications" 2>/dev/null || true
  fi
  if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -f -t "${HOME}/.local/share/icons/hicolor" 2>/dev/null || true
  fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --user)
      MODE="--user"
      ;;
    --system)
      MODE="--system"
      ;;
    --all)
      MODE="--all"
      ;;
    --purge-data)
      PURGE_DATA=1
      ;;
    --kill)
      KILL_RUNNING=1
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      usage
      exit 2
      ;;
  esac
  shift
done

uninstall_one_scope() {
  local scope="$1" # --user or --system

  if flatpak info "$scope" "$APP_ID" >/dev/null 2>&1; then
    echo "Uninstalling $APP_ID ($scope)…"
    # --delete-data removes the app's data directory for that scope.
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

cleanup_lock_files() {
  # Remove any stale singleton lock files created by the app.
  # Note: these are *not* Flatpak-managed, so uninstall won't remove them.
  local tmp_lock="/tmp/trainer_app_ultra_early.lock"
  local runtime_lock=""
  if [[ -n "${XDG_RUNTIME_DIR:-}" ]]; then
    runtime_lock="${XDG_RUNTIME_DIR}/trainer_app_ultra_early.lock"
  fi

  if [[ -f "$tmp_lock" ]]; then
    echo "Removing lock file: $tmp_lock"
    rm -f "$tmp_lock" || true
  fi
  if [[ -n "$runtime_lock" && -f "$runtime_lock" ]]; then
    echo "Removing lock file: $runtime_lock"
    rm -f "$runtime_lock" || true
  fi
}

if [[ "$KILL_RUNNING" -eq 1 ]]; then
  echo "Attempting to stop any running instance (flatpak kill)…"
  flatpak kill "$APP_ID" 2>/dev/null || true
fi

case "$MODE" in
  --user|--system)
    uninstall_one_scope "$MODE"
    ;;
  --all)
    uninstall_one_scope "--user"
    uninstall_one_scope "--system"
    ;;
esac

# Always attempt to remove any extra desktop integration artifacts.
cleanup_desktop_integration

# Clean up any stale singleton lock files on the host.
cleanup_lock_files

if [[ "$PURGE_DATA" -eq 1 ]]; then
  data_dir="${HOME}/.var/app/${APP_ID}"
  if [[ -d "$data_dir" ]]; then
    echo "Removing leftover user data dir: $data_dir"
    rm -rf "$data_dir"
  fi
fi

echo "Done."
