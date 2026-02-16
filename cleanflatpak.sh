#!/usr/bin/env bash
set -euo pipefail

APP_ID="com.oliverernster.Trainer"

if ! command -v flatpak >/dev/null 2>&1; then
  echo "flatpak is not installed or not on PATH"
  exit 1
fi

MODE="--user"  # default
PURGE_DATA=0

usage() {
  cat <<'EOF'
Usage: ./cleanflatpak.sh [--user|--system|--all] [--purge-data]

Removes the installed Trainer Flatpak(s): com.oliverernster.Trainer

Options:
  --user        Uninstall the per-user install (default)
  --system      Uninstall the system-wide install (may prompt for auth)
  --all         Try both --user and --system
  --purge-data  Also remove leftover user data folder (~/.var/app/<APP_ID>)
EOF
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

case "$MODE" in
  --user|--system)
    uninstall_one_scope "$MODE"
    ;;
  --all)
    uninstall_one_scope "--user"
    uninstall_one_scope "--system"
    ;;
esac

if [[ "$PURGE_DATA" -eq 1 ]]; then
  data_dir="${HOME}/.var/app/${APP_ID}"
  if [[ -d "$data_dir" ]]; then
    echo "Removing leftover user data dir: $data_dir"
    rm -rf "$data_dir"
  fi
fi

echo "Done."

