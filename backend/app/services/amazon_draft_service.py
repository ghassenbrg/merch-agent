from __future__ import annotations

from uuid import uuid4

from fastapi import HTTPException

from app.models.schemas import JobResponse
from app.services.draft_service import require_draft
from app.db.database import get_connection


DANGEROUS_TEXT = [
    "publish",
    "submit",
    "submit for review",
    "make live",
    "create product",
]

SAFE_TEXT = [
    "save draft",
    "save as draft",
]


def start_amazon_draft(draft_id: str) -> JobResponse:
    draft = require_draft(draft_id)

    if draft.status != "READY_FOR_AMAZON_DRAFT":
        raise HTTPException(status_code=400, detail="Draft is not ready for Amazon.")

    if draft.amazon_draft.get("saved"):
        raise HTTPException(status_code=400, detail="Draft already saved to Amazon.")

    if draft.amazon_draft.get("publish_allowed") is not False:
        raise HTTPException(status_code=400, detail="Publish must remain disabled.")

    job_id = f"job_{uuid4().hex[:12]}"
    draft.status = "AMAZON_DRAFT_SAVED"
    draft.amazon_draft["saved"] = True
    draft.amazon_draft["last_job_id"] = job_id

    # This first implementation is intentionally simulated. The live Playwright
    # operator will replace this after policy/account review and selector discovery.
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE drafts
            SET status = ?, payload = ?, updated_at = CURRENT_TIMESTAMP
            WHERE draft_id = ?
            """,
            (draft.status, draft.model_dump_json(), draft.draft_id),
        )

    return JobResponse(
        jobId=job_id,
        status=draft.status,
        message="Simulated Amazon draft assist completed. Live browser operator is not enabled yet.",
    )
