from __future__ import annotations

from uuid import uuid4

from app.db.database import get_connection
from app.models.schemas import AutopilotRequest, RunResponse
from app.services.config_service import get_config
from app.services.local_package_workflow.candidates import cycle_fixture_candidates
from app.services.local_package_workflow.compliance import run_compliance_gate
from app.services.local_package_workflow.marketplaces import resolve_marketplaces
from app.services.local_package_workflow.package_assembler import assemble_local_package
from app.services.local_package_workflow.product_templates import resolve_product_template
from app.services.local_package_workflow.scoring import score_candidate


def run_autopilot(request: AutopilotRequest) -> RunResponse:
    run_id = f"run_{uuid4().hex[:12]}"

    if request.touch_amazon:
        with get_connection() as connection:
            connection.execute(
                "INSERT INTO runs (run_id, mode, status, completed_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
                (run_id, "autopilot", "FAILED"),
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

    requested_count = max(1, min(request.count, 10))
    created_draft_ids: list[str] = []
    config = get_config()
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
            (run_id, "autopilot", "COMPLETED"),
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

        candidate_iter = cycle_fixture_candidates()
        attempts = 0
        max_attempts = requested_count * 5
        while len(created_draft_ids) < requested_count and attempts < max_attempts:
            attempts += 1
            candidate = next(candidate_iter)
            compliance = run_compliance_gate(candidate)
            if not compliance.passed:
                connection.execute(
                    "INSERT INTO run_logs (run_id, level, message) VALUES (?, ?, ?)",
                    (
                        run_id,
                        "warning",
                        f"Skipped {candidate.candidate_id}: {'; '.join(compliance.reasons)}",
                    ),
                )
                continue

            draft_id = f"drf_auto_{uuid4().hex[:10]}"
            package = assemble_local_package(
                draft_id=draft_id,
                candidate=candidate,
                product=product,
                marketplace_plan=marketplace_plan,
                score=score_candidate(candidate),
                compliance=compliance,
                validation_config=config.validation,
                default_prices=config.settings.get("default_prices", {}),
            )
            draft = package.draft
            created_draft_ids.append(draft_id)
            connection.execute(
                """
                INSERT INTO drafts (draft_id, status, title, score, payload)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    draft_id,
                    draft.status,
                    draft.listing_groups["English"]["design_title"],
                    draft.score["overall"],
                    draft.model_dump_json(),
                ),
            )
            connection.execute(
                "INSERT INTO run_logs (run_id, level, message) VALUES (?, ?, ?)",
                (
                    run_id,
                    "info",
                    f"Created local package {draft_id} from {candidate.candidate_id}.",
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
            connection.execute(
                """
                INSERT INTO draft_events (draft_id, event_type, from_status, to_status, message)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    draft_id,
                    "autopilot_created",
                    None,
                    draft.status,
                    f"Created by local autopilot run {run_id}.",
                ),
            )

        status = "COMPLETED" if created_draft_ids else "FAILED"
        if not created_draft_ids:
            connection.execute(
                "INSERT INTO run_logs (run_id, level, message) VALUES (?, ?, ?)",
                (
                    run_id,
                    "error",
                    "No compliant local candidates could be assembled.",
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
            "Autopilot completed deterministic local package generation. "
            "No Amazon interaction occurred."
            if created_draft_ids
            else "Autopilot could not assemble a compliant local package."
        ),
    )
