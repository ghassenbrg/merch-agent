from __future__ import annotations

import json
from typing import Any

from fastapi import HTTPException

from app.db.database import get_connection
from app.models.schemas import Draft, DraftEvent, DraftSummary, StatusResponse
from app.services.validation_service import compute_ready_for_amazon_draft


def _row_to_draft(row: Any) -> Draft:
    return Draft.model_validate(json.loads(row["payload"]))


def record_draft_event(
    draft_id: str,
    event_type: str,
    message: str,
    from_status: str | None = None,
    to_status: str | None = None,
) -> None:
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO draft_events (draft_id, event_type, from_status, to_status, message)
            VALUES (?, ?, ?, ?, ?)
            """,
            (draft_id, event_type, from_status, to_status, message),
        )


def _save_draft(draft: Draft, previous_status: str, event_type: str, message: str) -> None:
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE drafts
            SET status = ?, title = ?, score = ?, payload = ?, updated_at = CURRENT_TIMESTAMP
            WHERE draft_id = ?
            """,
            (
                draft.status,
                draft.listing_groups["English"]["design_title"],
                draft.score["overall"],
                draft.model_dump_json(),
                draft.draft_id,
            ),
        )
        connection.execute(
            """
            INSERT INTO draft_events (draft_id, event_type, from_status, to_status, message)
            VALUES (?, ?, ?, ?, ?)
            """,
            (draft.draft_id, event_type, previous_status, draft.status, message),
        )


def list_drafts() -> list[DraftSummary]:
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT draft_id, status, title, score, payload FROM drafts ORDER BY updated_at DESC"
        ).fetchall()

    summaries: list[DraftSummary] = []
    for row in rows:
        draft = _row_to_draft(row)
        selected_marketplaces = [
            marketplace["code"]
            for marketplace in draft.marketplaces
            if marketplace.get("selected")
        ]
        selected_product = next(
            (product for product in draft.products if product.get("selected")),
            draft.products[0],
        )
        summaries.append(
            DraftSummary(
                draft_id=draft.draft_id,
                status=draft.status,
                title=draft.listing_groups["English"]["design_title"],
                niche=draft.niche,
                score=draft.score["overall"],
                selected_marketplaces=selected_marketplaces,
                product_label=selected_product.get("label", selected_product["code"]),
                eligible_for_amazon_draft=draft.amazon_draft.get("eligible", False),
            )
        )
    return summaries


def get_draft(draft_id: str) -> Draft | None:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT payload FROM drafts WHERE draft_id = ?", (draft_id,)
        ).fetchone()
    if row is None:
        return None
    return _row_to_draft(row)


def get_draft_events(draft_id: str) -> list[DraftEvent]:
    draft = get_draft(draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found")

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT draft_id, event_type, from_status, to_status, message, created_at
            FROM draft_events
            WHERE draft_id = ?
            ORDER BY id ASC
            """,
            (draft_id,),
        ).fetchall()
    return [DraftEvent(**dict(row)) for row in rows]


def require_draft(draft_id: str) -> Draft:
    draft = get_draft(draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found")
    return draft


def approve_draft(draft_id: str) -> StatusResponse:
    draft = require_draft(draft_id)
    previous_status = draft.status
    ready, warnings = compute_ready_for_amazon_draft(draft)
    draft.amazon_draft["eligible"] = ready
    draft.listing_validation["warnings"] = warnings
    draft.status = "READY_FOR_AMAZON_DRAFT" if ready else "LISTING_READY"
    message = "Draft approved for Amazon draft assist." if ready else "Draft still has blocking checks."
    _save_draft(draft, previous_status, "approved", message)
    return StatusResponse(
        draft_id=draft_id,
        status=draft.status,
        message=message,
    )


def reject_draft(draft_id: str) -> StatusResponse:
    draft = require_draft(draft_id)
    previous_status = draft.status
    draft.status = "BLOCKED_COMPLIANCE"
    draft.amazon_draft["eligible"] = False
    message = "Draft rejected."
    _save_draft(draft, previous_status, "rejected", message)
    return StatusResponse(draft_id=draft_id, status=draft.status, message=message)


def archive_draft(draft_id: str) -> StatusResponse:
    draft = require_draft(draft_id)
    previous_status = draft.status
    draft.status = "ARCHIVED"
    draft.amazon_draft["eligible"] = False
    message = "Draft archived."
    _save_draft(draft, previous_status, "archived", message)
    return StatusResponse(draft_id=draft_id, status=draft.status, message=message)


def regenerate_design(draft_id: str) -> StatusResponse:
    draft = require_draft(draft_id)
    previous_status = draft.status
    draft.status = "DESIGN_GENERATED"
    draft.amazon_draft["eligible"] = False
    draft.design["theme"] = f"{draft.design['theme']} - regeneration requested"
    message = "Design regeneration queued."
    _save_draft(draft, previous_status, "regenerate_design", message)
    return StatusResponse(draft_id=draft_id, status=draft.status, message=message)


def regenerate_listing(draft_id: str) -> StatusResponse:
    draft = require_draft(draft_id)
    previous_status = draft.status
    draft.status = "LISTING_READY"
    draft.amazon_draft["eligible"] = False
    draft.listing_validation["warnings"] = ["Listing regeneration queued; re-approve after review."]
    message = "Listing regeneration queued."
    _save_draft(draft, previous_status, "regenerate_listing", message)
    return StatusResponse(draft_id=draft_id, status=draft.status, message=message)
