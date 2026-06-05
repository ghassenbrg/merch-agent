#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize a Merch Agent Codex autopilot run folder.")
    parser.add_argument("--goal", required=True)
    parser.add_argument("--count", type=int, default=3)
    parser.add_argument("--product", default="standard_tshirt")
    parser.add_argument("--marketplaces", nargs="*", default=[".com"])
    parser.add_argument("--preferred-niches", nargs="*", default=[])
    parser.add_argument("--excluded-niches", nargs="*", default=[])
    parser.add_argument("--risk-tolerance", default="policy_bounded_autonomous")
    args = parser.parse_args()

    now = datetime.now(timezone.utc).replace(microsecond=0)
    run_id = f"agent_run_{now.strftime('%Y%m%dT%H%M%SZ')}_{uuid4().hex[:8]}"
    run_dir = repo_root() / "data" / "logs" / "agent_runs" / run_id
    for name in ["research", "candidates", "creative", "artwork", "packages"]:
        (run_dir / name).mkdir(parents=True, exist_ok=True)

    config = {
        "run_id": run_id,
        "goal": args.goal,
        "created_at": now.isoformat().replace("+00:00", "Z"),
        "preferences": {
            "count": max(1, args.count),
            "product": args.product,
            "marketplaces": args.marketplaces,
            "preferred_niches": args.preferred_niches,
            "excluded_niches": args.excluded_niches,
            "risk_tolerance": args.risk_tolerance,
            "autonomy_mode": "policy_bounded",
            "touch_amazon": False,
            "final_output": "local_review_ready_packages",
        },
        "status": "initialized",
        "paths": {
            "run_dir": str(run_dir),
            "research_dir": str(run_dir / "research"),
            "candidates_dir": str(run_dir / "candidates"),
            "creative_dir": str(run_dir / "creative"),
            "artwork_dir": str(run_dir / "artwork"),
            "packages_dir": str(run_dir / "packages"),
            "agent_trace": str(run_dir / "agent_trace.json"),
        },
    }

    (run_dir / "run_config.json").write_text(
        json.dumps(config, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    trace = {
        **{key: config[key] for key in ["run_id", "goal", "created_at", "preferences"]},
        "autonomy_overrides": [],
        "sources": [],
        "candidates": [],
        "selected": [],
        "final_status": "initialized",
        "next_actions": ["Run research and candidate scoring."],
    }
    (run_dir / "agent_trace.json").write_text(
        json.dumps(trace, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(json.dumps(config, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
