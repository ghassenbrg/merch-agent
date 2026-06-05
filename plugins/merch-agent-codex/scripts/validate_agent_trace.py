#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


REQUIRED_TOP_LEVEL = {
    "run_id",
    "goal",
    "created_at",
    "preferences",
    "autonomy_overrides",
    "sources",
    "candidates",
    "selected",
    "final_status",
    "next_actions",
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a Merch Agent trace JSON shape.")
    parser.add_argument("trace_path")
    args = parser.parse_args()

    path = Path(args.trace_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    missing = sorted(REQUIRED_TOP_LEVEL - set(payload))
    if missing:
        raise SystemExit(f"Missing required keys: {', '.join(missing)}")
    if not isinstance(payload["candidates"], list):
        raise SystemExit("candidates must be a list")
    if not isinstance(payload["selected"], list):
        raise SystemExit("selected must be a list")
    print(f"Trace valid: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
