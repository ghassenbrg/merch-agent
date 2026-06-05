#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_HOST="${MERCH_AGENT_BACKEND_HOST:-127.0.0.1}"
BACKEND_PORT="${MERCH_AGENT_BACKEND_PORT:-8000}"
FRONTEND_HOST="${FRONTEND_HOST:-127.0.0.1}"
FRONTEND_PORT="${PORT:-3000}"

export MERCH_AGENT_ENV="${MERCH_AGENT_ENV:-production}"
export MERCH_AGENT_EXPOSED="${MERCH_AGENT_EXPOSED:-false}"
export MERCH_AGENT_ALLOWED_ORIGINS="${MERCH_AGENT_ALLOWED_ORIGINS:-http://localhost:${FRONTEND_PORT},http://127.0.0.1:${FRONTEND_PORT}}"
export MERCH_AGENT_TRUSTED_HOSTS="${MERCH_AGENT_TRUSTED_HOSTS:-localhost,127.0.0.1,::1}"
export MERCH_AGENT_DATA_DIR="${MERCH_AGENT_DATA_DIR:-${ROOT_DIR}/data}"
export NUXT_PUBLIC_API_BASE="${NUXT_PUBLIC_API_BASE:-http://${BACKEND_HOST}:${BACKEND_PORT}}"
export NUXT_PUBLIC_API_TOKEN="${NUXT_PUBLIC_API_TOKEN:-${MERCH_AGENT_API_TOKEN:-}}"

if [[ "${MERCH_AGENT_ENV}" =~ ^(production|prod|staging)$ || "${MERCH_AGENT_EXPOSED}" == "true" ]]; then
  if [[ -z "${MERCH_AGENT_API_TOKEN:-}" ]]; then
    echo "MERCH_AGENT_API_TOKEN is required for production-like preview." >&2
    exit 2
  fi
fi

if [[ ! -f "${ROOT_DIR}/frontend/.output/server/index.mjs" ]]; then
  echo "Frontend build not found; running npm run build." >&2
  (cd "${ROOT_DIR}/frontend" && npm run build)
fi

cleanup() {
  jobs -p | xargs -r kill
}
trap cleanup EXIT

(cd "${ROOT_DIR}/backend" && . .venv/bin/activate && uvicorn app.main:app --host "${BACKEND_HOST}" --port "${BACKEND_PORT}") &
(cd "${ROOT_DIR}/frontend" && HOST="${FRONTEND_HOST}" PORT="${FRONTEND_PORT}" node .output/server/index.mjs) &

echo "Backend:  http://${BACKEND_HOST}:${BACKEND_PORT}"
echo "Frontend: http://${FRONTEND_HOST}:${FRONTEND_PORT}"
wait
