#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEFAULT_DATA_DIR="${ROOT_DIR}/data"
DATA_DIR="${MERCH_AGENT_DATA_DIR:-${DEFAULT_DATA_DIR}}"
FORCE=0
BACKUP_DATABASE=1
INCLUDE_BROWSER_PROFILES=0
KEEP_DATABASE=0

usage() {
  cat <<'USAGE'
Clean local Merch Agent runtime data.

Usage:
  ./scripts/clean_data.sh [options]

Options:
  --force                     Actually delete data. Without this, the script runs a dry-run.
  --no-backup                 Do not back up data/merch_agent.sqlite3 before deleting it.
  --keep-database             Keep the SQLite database and clean generated files only.
  --include-browser-profiles  Also remove data/browser-profiles contents.
  -h, --help                  Show this help.

Default cleanup removes:
  data/merch_agent.sqlite3
  data/merch_agent.sqlite3-*
  data/frontend-preview.log
  data/drafts/*
  data/designs/*
  data/research_snapshots/*
  data/screenshots/*
  data/logs/*
  data/exports/*

The script preserves .gitkeep files and data/backups/.
USAGE
}

log() {
  printf '[clean-data] %s\n' "$*"
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --force)
        FORCE=1
        ;;
      --no-backup)
        BACKUP_DATABASE=0
        ;;
      --keep-database)
        KEEP_DATABASE=1
        ;;
      --include-browser-profiles)
        INCLUDE_BROWSER_PROFILES=1
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        printf 'Unknown option: %s\n\n' "$1" >&2
        usage >&2
        exit 2
        ;;
    esac
    shift
  done
}

check_app_not_running() {
  if [[ "${FORCE}" != "1" ]]; then
    return
  fi

  if [[ "${DATA_DIR}" != "${DEFAULT_DATA_DIR}" ]]; then
    return
  fi

  if ! command -v lsof >/dev/null 2>&1; then
    return
  fi

  if lsof -nP -iTCP:8000 -sTCP:LISTEN >/dev/null 2>&1 || \
    lsof -nP -iTCP:3000 -sTCP:LISTEN >/dev/null 2>&1; then
    cat >&2 <<'ERROR'
Merch Agent appears to be running on port 3000 or 8000.
Stop it with Ctrl-C first, then run the cleanup again.
ERROR
    exit 1
  fi
}

ensure_directories() {
  mkdir -p \
    "${DATA_DIR}" \
    "${DATA_DIR}/backups" \
    "${DATA_DIR}/drafts" \
    "${DATA_DIR}/designs" \
    "${DATA_DIR}/research_snapshots" \
    "${DATA_DIR}/screenshots" \
    "${DATA_DIR}/logs" \
    "${DATA_DIR}/exports" \
    "${DATA_DIR}/browser-profiles"

  for directory in drafts designs research_snapshots screenshots logs exports backups; do
    touch "${DATA_DIR}/${directory}/.gitkeep"
  done
}

backup_database() {
  if [[ "${KEEP_DATABASE}" == "1" || "${BACKUP_DATABASE}" != "1" ]]; then
    return
  fi

  local database="${DATA_DIR}/merch_agent.sqlite3"
  if [[ ! -f "${database}" ]]; then
    return
  fi

  local backup_path="${DATA_DIR}/backups/merch_agent_before_clean_$(date -u +%Y%m%dT%H%M%SZ).sqlite3"
  if [[ "${FORCE}" == "1" ]]; then
    cp "${database}" "${backup_path}"
    log "Backed up database to ${backup_path}"
  else
    log "Would back up database to ${backup_path}"
  fi
}

remove_path() {
  local path="$1"
  if [[ ! -e "${path}" && ! -L "${path}" ]]; then
    return
  fi

  if [[ "${FORCE}" == "1" ]]; then
    rm -rf "${path}"
    log "Removed ${path}"
  else
    log "Would remove ${path}"
  fi
}

clear_directory() {
  local directory="$1"
  if [[ ! -d "${directory}" ]]; then
    return
  fi

  local found=0
  while IFS= read -r path; do
    found=1
    remove_path "${path}"
  done < <(find "${directory}" -mindepth 1 -maxdepth 1 ! -name '.gitkeep' -print | sort)

  if [[ "${found}" == "0" ]]; then
    log "No generated files in ${directory}"
  fi
}

clean_database_files() {
  if [[ "${KEEP_DATABASE}" == "1" ]]; then
    log "Keeping SQLite database"
    return
  fi

  remove_path "${DATA_DIR}/merch_agent.sqlite3"
  remove_path "${DATA_DIR}/merch_agent.sqlite3-shm"
  remove_path "${DATA_DIR}/merch_agent.sqlite3-wal"

  for path in "${DATA_DIR}"/merch_agent.sqlite3-*; do
    remove_path "${path}"
  done
}

main() {
  parse_args "$@"

  ensure_directories
  check_app_not_running

  if [[ "${FORCE}" != "1" ]]; then
    log "Dry-run only. Re-run with --force to delete data."
  fi

  backup_database
  clean_database_files
  remove_path "${DATA_DIR}/frontend-preview.log"

  clear_directory "${DATA_DIR}/drafts"
  clear_directory "${DATA_DIR}/designs"
  clear_directory "${DATA_DIR}/research_snapshots"
  clear_directory "${DATA_DIR}/screenshots"
  clear_directory "${DATA_DIR}/logs"
  clear_directory "${DATA_DIR}/exports"

  if [[ "${INCLUDE_BROWSER_PROFILES}" == "1" ]]; then
    clear_directory "${DATA_DIR}/browser-profiles"
  else
    log "Keeping browser profiles. Use --include-browser-profiles to remove them."
  fi

  if [[ "${FORCE}" == "1" ]]; then
    log "Clean complete. Next app startup may recreate seeded sample drafts."
  else
    log "Dry-run complete."
  fi
}

main "$@"
