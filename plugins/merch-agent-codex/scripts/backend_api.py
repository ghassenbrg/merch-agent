#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any


def api_base() -> str:
    return os.environ.get("MERCH_AGENT_API_BASE", "http://127.0.0.1:8000").rstrip("/")


def headers() -> dict[str, str]:
    result = {"Content-Type": "application/json"}
    token = os.environ.get("MERCH_AGENT_API_TOKEN")
    if token:
        result["Authorization"] = f"Bearer {token}"
    return result


def request(method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{api_base()}{path}",
        data=data,
        method=method,
        headers=headers(),
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code} {exc.reason}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"Could not reach Merch Agent backend at {api_base()}: {exc}") from exc
    if not body:
        return None
    return json.loads(body)


def print_json(payload: Any) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def main() -> int:
    parser = argparse.ArgumentParser(description="Call the local Merch Agent backend API.")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("health")
    sub.add_parser("config")
    sub.add_parser("drafts")

    draft = sub.add_parser("draft")
    draft.add_argument("draft_id")

    run_local = sub.add_parser("run-local")
    run_local.add_argument("--count", type=int, default=1)
    run_local.add_argument("--product", default="standard_tshirt")
    run_local.add_argument("--production-mode", action="store_true")

    approve = sub.add_parser("approve")
    approve.add_argument("draft_id")

    dry_run = sub.add_parser("amazon-dry-run")
    dry_run.add_argument("draft_id")

    import_package = sub.add_parser("import-package")
    import_package.add_argument("json_path")

    args = parser.parse_args()

    if args.command == "health":
        print_json(request("GET", "/health/ready"))
    elif args.command == "config":
        print_json(request("GET", "/api/config"))
    elif args.command == "drafts":
        print_json(request("GET", "/api/drafts"))
    elif args.command == "draft":
        print_json(request("GET", f"/api/drafts/{args.draft_id}"))
    elif args.command == "run-local":
        print_json(
            request(
                "POST",
                "/api/workflows/autopilot/run",
                {
                    "count": args.count,
                    "default_product": args.product,
                    "explore_marketplaces": True,
                    "touch_amazon": False,
                    "production_mode": args.production_mode,
                },
            )
        )
    elif args.command == "approve":
        print_json(request("POST", f"/api/drafts/{args.draft_id}/approve", {}))
    elif args.command == "amazon-dry-run":
        print_json(
            request(
                "POST",
                f"/api/drafts/{args.draft_id}/amazon-draft",
                {"mode": "dry_run"},
            )
        )
    elif args.command == "import-package":
        with open(args.json_path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        print_json(request("POST", "/api/agent/packages", payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
