from __future__ import annotations

import json
from copy import deepcopy
from uuid import uuid4

from app.db.database import get_connection
from app.fixtures.sample_data import SAMPLE_DRAFTS
from app.models.schemas import AutopilotRequest, RunResponse


def run_autopilot(request: AutopilotRequest) -> RunResponse:
    if request.touch_amazon:
        return RunResponse(
            runId=f"run_{uuid4().hex[:12]}",
            status="FAILED",
            createdDraftIds=[],
            message="Autopilot cannot touch Amazon. Use manual Amazon draft assist from the UI.",
        )

    run_id = f"run_{uuid4().hex[:12]}"
    created_draft_ids: list[str] = []

    with get_connection() as connection:
        connection.execute(
            "INSERT INTO runs (run_id, mode, status) VALUES (?, ?, ?)",
            (run_id, "autopilot", "COMPLETED"),
        )
        connection.execute(
            "INSERT INTO run_logs (run_id, level, message) VALUES (?, ?, ?)",
            (run_id, "info", f"Autopilot requested for {request.count} draft package(s)."),
        )

        for index in range(max(1, min(request.count, 10))):
            template = deepcopy(SAMPLE_DRAFTS[index % len(SAMPLE_DRAFTS)])
            draft_id = f"drf_auto_{uuid4().hex[:10]}"
            template["draft_id"] = draft_id
            template["status"] = "READY_FOR_AMAZON_DRAFT"
            template["amazon_draft"]["eligible"] = True
            template["amazon_draft"]["saved"] = False
            template["amazon_draft"]["last_job_id"] = None
            template["summary"] = f"Autopilot sample package generated from seed candidate {index + 1}."
            created_draft_ids.append(draft_id)
            connection.execute(
                """
                INSERT INTO drafts (draft_id, status, title, score, payload)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    draft_id,
                    template["status"],
                    template["listing_groups"]["English"]["design_title"],
                    template["score"]["overall"],
                    json.dumps(template),
                ),
            )
            connection.execute(
                "INSERT INTO run_logs (run_id, level, message) VALUES (?, ?, ?)",
                (run_id, "info", f"Created local draft package {draft_id}."),
            )

        connection.execute(
            "UPDATE runs SET completed_at = CURRENT_TIMESTAMP WHERE run_id = ?",
            (run_id,),
        )

    return RunResponse(
        runId=run_id,
        status="COMPLETED",
        createdDraftIds=created_draft_ids,
        message="Autopilot completed locally. No Amazon interaction occurred.",
    )
