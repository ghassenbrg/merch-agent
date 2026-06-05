#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

(cd "${ROOT_DIR}/backend" && . .venv/bin/activate && python -m pip check)
(cd "${ROOT_DIR}/frontend" && npm audit --audit-level=moderate)
