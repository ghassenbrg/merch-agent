#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="${ROOT_DIR}/backend"
FRONTEND_DIR="${ROOT_DIR}/frontend"

PYTHON_BIN="${PYTHON_BIN:-python3}"
BACKEND_VENV="${BACKEND_VENV:-${BACKEND_DIR}/.venv}"
RUN_CHECKS="${MERCH_AGENT_RUN_CHECKS:-0}"
SKIP_BACKEND_INSTALL="${MERCH_AGENT_SKIP_BACKEND_INSTALL:-0}"
SKIP_FRONTEND_INSTALL="${MERCH_AGENT_SKIP_FRONTEND_INSTALL:-0}"
SKIP_FRONTEND_BUILD="${MERCH_AGENT_SKIP_FRONTEND_BUILD:-0}"
INSTALL_PLAYWRIGHT="${MERCH_AGENT_INSTALL_PLAYWRIGHT:-0}"

log() {
  printf '\n[%s] %s\n' "$(date +%H:%M:%S)" "$*"
}

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    printf 'Missing required command: %s\n' "$1" >&2
    exit 127
  fi
}

create_backend_venv() {
  if [[ ! -x "${BACKEND_VENV}/bin/python" ]]; then
    log "Creating backend virtualenv"
    "${PYTHON_BIN}" -m venv "${BACKEND_VENV}"
  fi
}

install_backend() {
  if [[ "${SKIP_BACKEND_INSTALL}" == "1" ]]; then
    log "Skipping backend dependency install"
    return
  fi
  create_backend_venv
  log "Installing backend dependencies"
  "${BACKEND_VENV}/bin/python" -m pip install --upgrade pip
  "${BACKEND_VENV}/bin/python" -m pip install -r "${BACKEND_DIR}/requirements.txt"
}

install_frontend() {
  if [[ "${SKIP_FRONTEND_INSTALL}" == "1" ]]; then
    log "Skipping frontend dependency install"
    return
  fi
  log "Installing frontend dependencies"
  (cd "${FRONTEND_DIR}" && npm install)
  if [[ "${INSTALL_PLAYWRIGHT}" == "1" ]]; then
    log "Installing Playwright Chromium browser"
    (cd "${FRONTEND_DIR}" && npx playwright install chromium)
  fi
}

build_frontend() {
  if [[ "${SKIP_FRONTEND_BUILD}" == "1" ]]; then
    log "Skipping frontend build"
    return
  fi
  log "Building frontend"
  (cd "${FRONTEND_DIR}" && npm run build)
}

run_checks() {
  if [[ "${RUN_CHECKS}" != "1" ]]; then
    return
  fi
  log "Running backend tests"
  (cd "${BACKEND_DIR}" && "${BACKEND_VENV}/bin/python" -m pytest -q)
  log "Running frontend typecheck"
  (cd "${FRONTEND_DIR}" && npm run typecheck)
  log "Running dependency audit"
  (cd "${ROOT_DIR}" && ./scripts/audit_dependencies.sh)
}

configure_runtime_env() {
  if [[ -z "${MERCH_AGENT_API_TOKEN:-}" ]]; then
    export MERCH_AGENT_API_TOKEN
    MERCH_AGENT_API_TOKEN="$("${PYTHON_BIN}" -c 'import secrets; print(secrets.token_urlsafe(32))')"
    log "Generated ephemeral MERCH_AGENT_API_TOKEN for this session"
  fi

  export MERCH_AGENT_ENV="${MERCH_AGENT_ENV:-production}"
  export MERCH_AGENT_EXPOSED="${MERCH_AGENT_EXPOSED:-false}"
  export MERCH_AGENT_ALLOWED_ORIGINS="${MERCH_AGENT_ALLOWED_ORIGINS:-http://localhost:3000,http://127.0.0.1:3000}"
  export MERCH_AGENT_TRUSTED_HOSTS="${MERCH_AGENT_TRUSTED_HOSTS:-localhost,127.0.0.1,::1}"
  export MERCH_AGENT_DATA_DIR="${MERCH_AGENT_DATA_DIR:-${ROOT_DIR}/data}"
  export NUXT_PUBLIC_API_BASE="${NUXT_PUBLIC_API_BASE:-http://127.0.0.1:8000}"
  export NUXT_PUBLIC_API_TOKEN="${NUXT_PUBLIC_API_TOKEN:-${MERCH_AGENT_API_TOKEN}}"
}

main() {
  require_command "${PYTHON_BIN}"
  require_command npm
  require_command node

  install_backend
  install_frontend
  build_frontend
  run_checks
  configure_runtime_env

  log "Starting Merch Agent production-like preview"
  printf 'Frontend: http://127.0.0.1:3000\n'
  printf 'Backend:  http://127.0.0.1:8000\n'
  printf 'Stop with Ctrl-C.\n'
  exec "${ROOT_DIR}/scripts/production_preview.sh"
}

main "$@"
