from __future__ import annotations

import json
from collections.abc import Callable
from uuid import uuid4

from app.core.paths import DATA_DIR
from app.db.database import get_connection
from app.db.repositories import insert_draft_event, upsert_draft_projection
from app.models.schemas import AutopilotRequest, RunResponse
from app.services.config_service import get_config
from app.services.local_package_workflow.candidates import discover_candidates
from app.services.local_package_workflow.compliance import run_compliance_gate
from app.services.local_package_workflow.marketplaces import resolve_marketplaces
from app.services.local_package_workflow.package_assembler import assemble_local_package
from app.services.local_package_workflow.product_templates import resolve_product_template
from app.services.local_package_workflow.research import (
    ResearchUnavailableError,
    collect_live_research_snapshot,
)
from app.services.local_package_workflow.scoring import (
    score_candidate,
    score_candidate_from_research_snapshot,
)


def _write_candidate_audit(run_id: str, audit_payload: list[dict]) -> str:
    path = DATA_DIR / "logs" / f"{run_id}_candidate_audit.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(audit_payload, indent=2, sort_keys=True), encoding="utf-8")
    return str(path.relative_to(DATA_DIR.parent))


def run_autopilot(
    request: AutopilotRequest,
    mode: str = "autopilot",
    stop_requested: Callable[[], bool] | None = None,
) -> RunResponse:
    run_id = f"run_{uuid4().hex[:12]}"

    if request.touch_amazon:
        with get_connection() as connection:
            connection.execute(
                "INSERT INTO runs (run_id, mode, status, completed_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
                (run_id, mode, "FAILED"),
            )
            connection.execute(
                "INSERT INTO run_logs (run_id, level, message) VALUES (?, ?, ?)",
                (
                    run_id,
                    "error",
                    "Autopilot refused Amazon interaction. Manual draft assist is required.",
                ),
            )
        return RunResponse(
            runId=run_id,
            status="FAILED",
            createdDraftIds=[],
            message="Autopilot cannot touch Amazon. Use manual Amazon draft assist from the UI.",
        )

    created_draft_ids: list[str] = []
    config = get_config()
    operations = config.settings.get("autopilot_operations", {})
    max_packages_per_run = 10
    if isinstance(operations, dict):
        try:
            max_packages_per_run = max(1, int(operations.get("max_packages_per_run", 10)))
        except (TypeError, ValueError):
            max_packages_per_run = 10
    requested_count = max(1, min(request.count, max_packages_per_run, 10))
    product = resolve_product_template(
        config.product_templates,
        request.default_product,
    )
    product_prices = config.settings.get("default_prices", {}).get(product.code, {})
    marketplace_plan = resolve_marketplaces(
        marketplace_config=config.marketplaces,
        enabled_marketplaces=config.settings.get("enabled_marketplaces", []),
        priced_marketplaces=list(product_prices.keys()),
        explore_marketplaces=request.explore_marketplaces,
    )

    with get_connection() as connection:
        connection.execute(
            "INSERT INTO runs (run_id, mode, status) VALUES (?, ?, ?)",
            (run_id, mode, "COMPLETED"),
        )
        connection.execute(
            "INSERT INTO run_logs (run_id, level, message) VALUES (?, ?, ?)",
            (run_id, "info", f"Autopilot requested for {request.count} draft package(s)."),
        )
        connection.execute(
            "INSERT INTO run_logs (run_id, level, message) VALUES (?, ?, ?)",
            (
                run_id,
                "info",
                (
                    f"Run mode {mode}; package cap allows {requested_count} local package(s). "
                    "Amazon Draft Assist is not available to this workflow."
                ),
            ),
        )
        connection.execute(
            "INSERT INTO run_logs (run_id, level, message) VALUES (?, ?, ?)",
            (
                run_id,
                "info",
                (
                    "Production mode enabled; research snapshots are required before scoring."
                    if request.production_mode
                    else "Local deterministic mode; candidate fixture signals may be used."
                ),
            ),
        )
        connection.execute(
            "INSERT INTO run_logs (run_id, level, message) VALUES (?, ?, ?)",
            (
                run_id,
                "info",
                f"Resolved product {product.code} to {product.width}x{product.height}.",
            ),
        )
        connection.execute(
            "INSERT INTO run_logs (run_id, level, message) VALUES (?, ?, ?)",
            (
                run_id,
                "info",
                f"Selected marketplaces: {', '.join(marketplace_plan.selected_codes) or 'none'}.",
            ),
        )

        max_attempts = requested_count * 5
        discovery = discover_candidates(
            config.candidate_sources,
            requested_count=max_attempts,
            seed=run_id,
        )
        audit_by_candidate_id = {
            record.candidate_id: record for record in discovery.audit_records
        }
        audit_path = _write_candidate_audit(run_id, discovery.audit_payload())
        connection.execute(
            "INSERT INTO run_logs (run_id, level, message) VALUES (?, ?, ?)",
            (
                run_id,
                "info",
                f"Candidate discovery audited {len(discovery.audit_records)} candidate decision(s) to {audit_path}.",
            ),
        )
        connection.execute(
            "INSERT INTO run_logs (run_id, level, message) VALUES (?, ?, ?)",
            (
                run_id,
                "info",
                (
                    "External research enabled by config."
                    if discovery.external_research_enabled
                    else "External research disabled by config; local sources only."
                ),
            ),
        )
        for audit_record in discovery.audit_records:
            if audit_record.decision == "skipped":
                connection.execute(
                    "INSERT INTO run_logs (run_id, level, message) VALUES (?, ?, ?)",
                    (
                        run_id,
                        "warning",
                        (
                            f"Skipped {audit_record.candidate_id} from "
                            f"{audit_record.source_id} ({audit_record.search_phrase}): "
                            f"{'; '.join(audit_record.reasons)}"
                        ),
                    ),
                )

        for candidate in discovery.candidates:
            if stop_requested and stop_requested():
                connection.execute(
                    "INSERT INTO run_logs (run_id, level, message) VALUES (?, ?, ?)",
                    (
                        run_id,
                        "warning",
                        "Stop switch engaged; local package generation halted before the next candidate.",
                    ),
                )
                break
            if len(created_draft_ids) >= requested_count:
                break
            compliance = run_compliance_gate(candidate)
            if compliance.blocked:
                connection.execute(
                    "INSERT INTO run_logs (run_id, level, message) VALUES (?, ?, ?)",
                    (
                        run_id,
                        "warning",
                        f"Skipped {candidate.candidate_id}: {'; '.join(compliance.reasons)}",
                    ),
                )
                continue
            if compliance.human_review_required:
                connection.execute(
                    "INSERT INTO run_logs (run_id, level, message) VALUES (?, ?, ?)",
                    (
                        run_id,
                        "warning",
                        f"{candidate.candidate_id} requires human review: {'; '.join(compliance.reasons)}",
                    ),
                )

            research_snapshot_payload = None
            research_snapshot_path = None
            if request.production_mode:
                try:
                    research_snapshot, research_snapshot_path = collect_live_research_snapshot(
                        candidate,
                        config.candidate_sources,
                        run_id=run_id,
                    )
                    research_snapshot_payload = research_snapshot.to_payload()
                except ResearchUnavailableError as exc:
                    connection.execute(
                        "INSERT INTO run_logs (run_id, level, message) VALUES (?, ?, ?)",
                        (
                            run_id,
                            "error",
                            f"Research unavailable for {candidate.candidate_id}: {exc}",
                        ),
                    )
                    continue
                score = score_candidate_from_research_snapshot(
                    candidate,
                    research_snapshot_payload,
                )
            else:
                score = score_candidate(candidate)
            draft_id = f"drf_auto_{uuid4().hex[:10]}"
            package = assemble_local_package(
                draft_id=draft_id,
                candidate=candidate,
                product=product,
                marketplace_plan=marketplace_plan,
                score=score,
                compliance=compliance,
                validation_config=config.validation,
                default_prices=config.settings.get("default_prices", {}),
                candidate_audit=audit_by_candidate_id.get(candidate.candidate_id),
                research_snapshot=research_snapshot_payload,
                research_snapshot_path=research_snapshot_path,
            )
            draft = package.draft
            created_draft_ids.append(draft_id)
            upsert_draft_projection(connection, draft)
            connection.execute(
                "INSERT INTO run_logs (run_id, level, message) VALUES (?, ?, ?)",
                (
                    run_id,
                    "info",
                    (
                        f"Created local package {draft_id} from {candidate.candidate_id} "
                        f"via {candidate.source_id}; score source "
                        f"{'research snapshot ' + str(research_snapshot_path) if research_snapshot_path else 'candidate fixture signals'}."
                    ),
                ),
            )
            connection.execute(
                "INSERT INTO run_logs (run_id, level, message) VALUES (?, ?, ?)",
                (
                    run_id,
                    "info",
                    f"Wrote package artifacts to {package.artifact_dir}.",
                ),
            )
            connection.execute(
                "INSERT INTO run_drafts (run_id, draft_id) VALUES (?, ?)",
                (run_id, draft_id),
            )
            insert_draft_event(
                connection,
                draft_id,
                "autopilot_created",
                f"Created by local autopilot run {run_id}.",
                None,
                draft.status,
            )

        stopped = bool(stop_requested and stop_requested())
        status = "COMPLETED" if created_draft_ids else "FAILED"
        if not created_draft_ids:
            connection.execute(
                "INSERT INTO run_logs (run_id, level, message) VALUES (?, ?, ?)",
                (
                    run_id,
                    "error",
                    (
                        "No packages assembled because production research evidence was unavailable."
                        if request.production_mode
                        else (
                            "Stop switch halted scheduled generation before a package was assembled."
                            if stopped
                            else "No compliant local candidates could be assembled."
                        )
                    ),
                ),
            )
        connection.execute(
            "UPDATE runs SET status = ? WHERE run_id = ?",
            (status, run_id),
        )
        connection.execute(
            "UPDATE runs SET completed_at = CURRENT_TIMESTAMP WHERE run_id = ?",
            (run_id,),
        )

    return RunResponse(
        runId=run_id,
        status=status,
        createdDraftIds=created_draft_ids,
        message=(
            "Autopilot completed live-research local package generation. "
            "Research snapshots were persisted before scoring. "
            "No Amazon interaction occurred."
            if created_draft_ids and request.production_mode
            else "Autopilot completed deterministic local package generation. "
            "No Amazon interaction occurred."
            if created_draft_ids
            else (
                "Autopilot could not assemble a package because production research evidence was unavailable."
                if request.production_mode
                else (
                    "Autopilot stopped before assembling a package because the stop switch was engaged."
                    if stopped
                    else "Autopilot could not assemble a compliant local package."
                )
            )
        ),
    )
