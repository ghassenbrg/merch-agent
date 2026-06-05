#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PLUGIN="$ROOT/plugins/merch-agent-codex"
MARKETPLACE="$ROOT/.agents/plugins/marketplace.json"
CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
PYTHON="$ROOT/backend/.venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  PYTHON="python3"
fi

echo "== Validating Codex plugin =="
python3 "$CODEX_HOME/skills/.system/skill-creator/scripts/quick_validate.py" \
  "$PLUGIN/skills/merch-agent"
python3 "$CODEX_HOME/skills/.system/plugin-creator/scripts/validate_plugin.py" \
  "$PLUGIN"

echo "== Checking marketplace =="
python3 - "$MARKETPLACE" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
payload = json.loads(path.read_text(encoding="utf-8"))
assert payload["name"] == "merch-agent-local"
plugins = {plugin["name"]: plugin for plugin in payload["plugins"]}
assert plugins["merch-agent-codex"]["source"]["path"] == "./plugins/merch-agent-codex"
print(f"Marketplace valid: {path}")
PY

if [[ -f "$ROOT/marketplace.json" ]]; then
  cmp -s "$MARKETPLACE" "$ROOT/marketplace.json" \
    || echo "WARN: root marketplace.json differs from .agents/plugins/marketplace.json"
fi

CONFIG="$CODEX_HOME/config.toml"
if [[ -f "$CONFIG" ]]; then
  grep -q '\[marketplaces\.merch-agent-local\]' "$CONFIG" \
    || echo "WARN: merch-agent-local marketplace is not registered in $CONFIG"
  grep -q '\[plugins\."merch-agent-codex@merch-agent-local"\]' "$CONFIG" \
    || echo "WARN: merch-agent-codex plugin is not enabled in $CONFIG"
fi

echo "== Running backend bridge tests =="
cd "$ROOT"
"$PYTHON" -m pytest backend/tests/test_agent_import.py backend/tests/test_local_package_workflow.py -q

echo "== Smoke-testing agent run trace =="
RUN_JSON="$("$PLUGIN/scripts/init_autopilot_run.py" \
  --goal "Production readiness smoke test" \
  --count 1)"
TRACE_PATH="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["paths"]["agent_trace"])' <<<"$RUN_JSON")"
"$PLUGIN/scripts/validate_agent_trace.py" "$TRACE_PATH"

echo "Merch Agent Codex plugin is ready."
