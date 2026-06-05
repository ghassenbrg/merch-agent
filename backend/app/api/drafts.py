from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.core.paths import REPO_ROOT
from app.models.schemas import Draft, DraftEvent, DraftSummary, JobResponse, StatusResponse
from app.services.amazon_draft_service import start_amazon_draft
from app.services.draft_service import (
    archive_draft,
    approve_draft,
    get_draft,
    get_draft_events,
    list_drafts,
    regenerate_design,
    regenerate_listing,
    reject_draft,
)

router = APIRouter()


@router.get("", response_model=list[DraftSummary])
def index() -> list[DraftSummary]:
    return list_drafts()


@router.get("/{draft_id}", response_model=Draft)
def show(draft_id: str) -> Draft:
    draft = get_draft(draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found")
    return draft


@router.get("/{draft_id}/events", response_model=list[DraftEvent])
def events(draft_id: str) -> list[DraftEvent]:
    return get_draft_events(draft_id)


@router.get("/{draft_id}/design/final.png")
def final_png(draft_id: str) -> FileResponse:
    draft = get_draft(draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found")

    design_path = Path(str(draft.design.get("final_png", "")))
    if not design_path.is_absolute():
        design_path = REPO_ROOT / design_path
    design_path = design_path.resolve()

    if not design_path.is_file():
        raise HTTPException(status_code=404, detail="Final PNG not found")

    return FileResponse(
        design_path,
        media_type="image/png",
        filename=f"{draft.draft_id}-final.png",
    )


@router.post("/{draft_id}/approve", response_model=StatusResponse)
def approve(draft_id: str) -> StatusResponse:
    return approve_draft(draft_id)


@router.post("/{draft_id}/reject", response_model=StatusResponse)
def reject(draft_id: str) -> StatusResponse:
    return reject_draft(draft_id)


@router.post("/{draft_id}/archive", response_model=StatusResponse)
def archive(draft_id: str) -> StatusResponse:
    return archive_draft(draft_id)


@router.post("/{draft_id}/regenerate-design", response_model=StatusResponse)
def regenerate_draft_design(draft_id: str) -> StatusResponse:
    return regenerate_design(draft_id)


@router.post("/{draft_id}/regenerate-listing", response_model=StatusResponse)
def regenerate_draft_listing(draft_id: str) -> StatusResponse:
    return regenerate_listing(draft_id)


@router.post("/{draft_id}/amazon-draft", response_model=JobResponse)
def amazon_draft(draft_id: str) -> JobResponse:
    return start_amazon_draft(draft_id)
