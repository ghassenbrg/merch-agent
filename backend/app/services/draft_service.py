from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from app.core.paths import DATA_DIR, REPO_ROOT, resolve_runtime_path
from app.db.database import get_connection
from app.db.repositories import insert_draft_event, upsert_draft_projection
from app.models.schemas import (
    Draft,
    DraftArtifact,
    DraftChange,
    DraftEvent,
    DraftPatch,
    StatusResponse,
    DraftSummary,
)
from app.services.config_service import get_config
from app.services.local_package_workflow.listing import validate_listing_groups
from app.services.validation_service import compute_ready_for_amazon_draft


MUTABLE_STATUSES = {
    "LISTING_READY",
    "HUMAN_REVIEW_REQUIRED",
    "BLOCKED_COMPLIANCE",
    "BLOCKED_ARTWORK",
    "ARTWORK_PENDING",
    "ARCHIVED",
}

LISTING_FIELDS = [
    "design_title",
    "brand",
    "feature_bullet_1",
    "feature_bullet_2",
    "product_description",
]


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
        insert_draft_event(
            connection,
            draft_id,
            event_type,
            message,
            from_status,
            to_status,
        )


def _save_artifact_snapshots(draft: Draft) -> None:
    artifact_dir = DATA_DIR / "drafts" / draft.draft_id
    artifact_dir.mkdir(parents=True, exist_ok=True)
    snapshots = {
        "draft.json": draft.model_dump(mode="json"),
        "listing_fields.json": draft.listing_groups,
        "validation_report.json": draft.validation,
        "change_history.json": [
            change.model_dump(mode="json") for change in draft.change_history
        ],
    }
    for filename, payload in snapshots.items():
        (artifact_dir / filename).write_text(
            json.dumps(payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )


def _save_draft(draft: Draft, previous_status: str, event_type: str, message: str) -> None:
    _save_artifact_snapshots(draft)
    with get_connection() as connection:
        upsert_draft_projection(connection, draft)
        insert_draft_event(
            connection,
            draft.draft_id,
            event_type,
            message,
            previous_status,
            draft.status,
        )


def _selected_marketplace_codes(draft: Draft) -> list[str]:
    return [
        marketplace["code"]
        for marketplace in draft.marketplaces
        if marketplace.get("selected")
    ]


def _marketplace_language_map(draft: Draft) -> dict[str, str]:
    return {
        marketplace["code"]: marketplace.get("language_group", "English")
        for marketplace in draft.marketplaces
    }


def _recompute_editable_validation(draft: Draft) -> None:
    config = get_config()
    selected_marketplaces = _selected_marketplace_codes(draft)
    listing_validation = validate_listing_groups(
        listing_groups=draft.listing_groups,
        selected_marketplaces=selected_marketplaces,
        banned_terms=config.validation.get("banned_product_type_terms", {}),
        field_constraints=config.validation.get("listing_field_constraints", {}),
        marketplace_language_map=_marketplace_language_map(draft),
        translation_required_locales=config.validation.get(
            "translation_required_locales",
            ["de", "fr", "it", "es", "ja"],
        ),
    )
    listing_payload = listing_validation.to_payload()
    draft.listing_validation = listing_payload
    draft.validation["product_type_terms_removed"] = not listing_validation.product_type_terms_found
    draft.validation["listing_min_lengths_passed"] = listing_validation.min_description_length_passed
    draft.validation["selected_marketplaces_have_copy"] = listing_validation.selected_marketplaces_have_copy
    draft.validation["listing_field_lengths_passed"] = listing_validation.field_lengths_passed
    draft.validation["listing_punctuation_passed"] = listing_validation.punctuation_passed
    draft.validation["marketplace_language_copy_passed"] = listing_validation.marketplace_language_copy_passed
    draft.validation["translation_checks_passed"] = listing_validation.translation_checks_passed

    amount = draft.price.get("amount")
    price_ready = isinstance(amount, int | float) and amount > 0
    draft.price["royalty_positive"] = price_ready
    marketplace_prices = draft.price.setdefault("marketplace_prices", {})
    for marketplace in selected_marketplaces:
        marketplace_prices[marketplace] = {
            "currency": draft.price.get("currency", "USD"),
            "amount": amount,
        } if price_ready else None
    draft.validation["price_config_exists"] = price_ready and bool(selected_marketplaces)

    ready, warnings = compute_ready_for_amazon_draft(draft)
    draft.listing_validation["warnings"] = warnings
    draft.amazon_draft["eligible"] = ready and draft.status == "READY_FOR_AMAZON_DRAFT"


def _append_change(
    draft: Draft,
    field: str,
    before: Any,
    after: Any,
    note: str,
) -> None:
    if before == after:
        return
    draft.change_history.append(
        DraftChange(
            field=field,
            before=before,
            after=after,
            created_at=datetime.now(UTC).isoformat(),
            note=note,
        )
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


def get_draft_changes(draft_id: str) -> list[DraftChange]:
    draft = require_draft(draft_id)
    return draft.change_history


def _artifact_path(path_value: str) -> Path:
    return resolve_runtime_path(path_value)


def _artifact_response(draft_id: str, key: str, label: str, kind: str, path: Path) -> DraftArtifact:
    display_path = str(path)
    try:
        display_path = str(path.relative_to(REPO_ROOT))
    except ValueError:
        pass
    return DraftArtifact(
        key=key,
        label=label,
        kind=kind,
        path=display_path,
        url=f"/api/drafts/{draft_id}/artifacts/{key}",
        exists=path.is_file(),
    )


def get_draft_artifacts(draft_id: str) -> list[DraftArtifact]:
    draft = require_draft(draft_id)
    artifact_dir = DATA_DIR / "drafts" / draft_id
    candidates = [
        ("final_png", "Final PNG", "image/png", _artifact_path(str(draft.design.get("final_png", "")))),
        ("draft_json", "Draft JSON", "application/json", artifact_dir / "draft.json"),
        ("listing_fields", "Listing Fields", "application/json", artifact_dir / "listing_fields.json"),
        ("validation_report", "Validation Report", "application/json", artifact_dir / "validation_report.json"),
        ("change_history", "Listing Change History", "application/json", artifact_dir / "change_history.json"),
    ]
    optional_design_paths = {
        "design_source": draft.design.get("source"),
        "render_metadata": draft.design.get("render_metadata"),
    }
    for key, path_value in optional_design_paths.items():
        if path_value:
            candidates.append(
                (
                    key,
                    "Design Source" if key == "design_source" else "Render Metadata",
                    "application/json",
                    _artifact_path(str(path_value)),
                )
            )
    return [
        _artifact_response(draft_id, key, label, kind, path)
        for key, label, kind, path in candidates
    ]


def resolve_draft_artifact(draft_id: str, key: str) -> tuple[Path, str, str]:
    artifacts = {artifact.key: artifact for artifact in get_draft_artifacts(draft_id)}
    if key not in artifacts:
        raise HTTPException(status_code=404, detail="Artifact not found")
    artifact = artifacts[key]
    path = _artifact_path(artifact.path)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Artifact file not found")
    filename = f"{draft_id}-{key}.png" if artifact.kind == "image/png" else f"{draft_id}-{key}.json"
    return path, artifact.kind, filename


def require_draft(draft_id: str) -> Draft:
    draft = get_draft(draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found")
    return draft


def patch_draft(draft_id: str, patch: DraftPatch) -> Draft:
    draft = require_draft(draft_id)
    previous_status = draft.status
    previous_eligible = draft.amazon_draft.get("eligible", False)
    changed_fields: list[str] = []

    if patch.listing_groups:
        for language, listing_patch in patch.listing_groups.items():
            if language not in draft.listing_groups:
                raise HTTPException(status_code=400, detail=f"Unknown listing group: {language}")
            listing = draft.listing_groups[language]
            for field in LISTING_FIELDS:
                value = getattr(listing_patch, field)
                if value is None:
                    continue
                cleaned = value.strip()
                before = listing.get(field)
                if before != cleaned:
                    listing[field] = cleaned
                    field_name = f"listing_groups.{language}.{field}"
                    _append_change(draft, field_name, before, cleaned, "Listing copy edited.")
                    changed_fields.append(field_name)

    if patch.selected_marketplaces is not None:
        selected = sorted(set(patch.selected_marketplaces))
        known = {marketplace["code"] for marketplace in draft.marketplaces}
        unknown = sorted(set(selected) - known)
        if unknown:
            raise HTTPException(status_code=400, detail=f"Unknown marketplaces: {', '.join(unknown)}")
        if not selected:
            raise HTTPException(status_code=400, detail="At least one marketplace must remain selected.")
        before = _selected_marketplace_codes(draft)
        for marketplace in draft.marketplaces:
            marketplace["selected"] = marketplace["code"] in selected
        for language, listing in draft.listing_groups.items():
            listing["marketplaces"] = [
                marketplace["code"]
                for marketplace in draft.marketplaces
                if marketplace["selected"] and marketplace.get("language_group") == language
            ]
        after = _selected_marketplace_codes(draft)
        _append_change(draft, "selected_marketplaces", before, after, "Marketplace selection edited.")
        changed_fields.append("selected_marketplaces")

    if patch.price:
        if patch.price.currency is not None:
            before = draft.price.get("currency")
            currency = patch.price.currency.strip().upper()
            draft.price["currency"] = currency
            _append_change(draft, "price.currency", before, currency, "Price currency edited.")
            changed_fields.append("price.currency")
        if patch.price.amount is not None:
            if patch.price.amount <= 0:
                raise HTTPException(status_code=400, detail="Price amount must be greater than zero.")
            before = draft.price.get("amount")
            amount = round(float(patch.price.amount), 2)
            draft.price["amount"] = amount
            _append_change(draft, "price.amount", before, amount, "Price amount edited.")
            changed_fields.append("price.amount")

    if patch.status is not None:
        status = patch.status.strip().upper()
        if status == "READY_FOR_AMAZON_DRAFT":
            raise HTTPException(
                status_code=400,
                detail="Use manual approval to set READY_FOR_AMAZON_DRAFT.",
            )
        if status == "AMAZON_DRAFT_SAVED":
            raise HTTPException(status_code=400, detail="Amazon saved status cannot be set manually.")
        if status not in MUTABLE_STATUSES:
            raise HTTPException(status_code=400, detail=f"Unsupported status: {status}")
        before = draft.status
        draft.status = status
        _append_change(draft, "status", before, status, "Manual status edited.")
        changed_fields.append("status")

    if not changed_fields:
        return draft

    if previous_eligible or previous_status == "READY_FOR_AMAZON_DRAFT":
        draft.status = "LISTING_READY"
    draft.amazon_draft["eligible"] = False
    _recompute_editable_validation(draft)
    message = f"Edited {', '.join(dict.fromkeys(changed_fields))}; manual approval required before Amazon Draft Assist."
    _save_draft(draft, previous_status, "draft_updated", message)
    return draft


def approve_draft(draft_id: str) -> StatusResponse:
    draft = require_draft(draft_id)
    previous_status = draft.status
    ready, warnings = compute_ready_for_amazon_draft(draft)
    draft.amazon_draft["eligible"] = ready
    draft.listing_validation["warnings"] = warnings
    if ready:
        draft.status = "READY_FOR_AMAZON_DRAFT"
    elif draft.validation.get("human_review_required"):
        draft.status = "HUMAN_REVIEW_REQUIRED"
    elif draft.validation.get("artwork_status") == "pending":
        draft.status = "ARTWORK_PENDING"
    elif draft.validation.get("artwork_status") == "failed":
        draft.status = "BLOCKED_ARTWORK"
    else:
        draft.status = "LISTING_READY"
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


def _remove_data_subtree(path: Path) -> None:
    data_root = DATA_DIR.resolve()
    resolved = path.resolve()
    if not resolved.is_relative_to(data_root):
        raise HTTPException(status_code=400, detail="Refusing to delete path outside data directory.")
    if resolved.is_dir():
        shutil.rmtree(resolved)
    elif resolved.exists():
        resolved.unlink()


def delete_draft(draft_id: str) -> StatusResponse:
    require_draft(draft_id)
    with get_connection() as connection:
        for table in [
            "listing_groups",
            "validation_results",
            "design_artifacts",
            "amazon_draft_attempts",
            "draft_events",
            "run_drafts",
            "drafts",
        ]:
            connection.execute(f"DELETE FROM {table} WHERE draft_id = ?", (draft_id,))

    _remove_data_subtree(DATA_DIR / "drafts" / draft_id)
    _remove_data_subtree(DATA_DIR / "designs" / draft_id)

    return StatusResponse(
        draft_id=draft_id,
        status="DELETED",
        message="Draft deleted locally.",
    )


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
