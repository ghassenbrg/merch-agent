from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.core.paths import REPO_ROOT
from app.models.schemas import (
    AmazonDraftRequest,
    Draft,
    DraftArtifact,
    DraftChange,
    DraftEvent,
    DraftPatch,
    DraftSummary,
    JobResponse,
    StatusResponse,
)
from app.services.amazon_draft_service import start_amazon_draft
from app.services.draft_service import (
    archive_draft,
    approve_draft,
    get_draft_artifacts,
    get_draft_changes,
    get_draft,
    get_draft_events,
    list_drafts,
    patch_draft,
    regenerate_design,
    regenerate_listing,
    reject_draft,
    resolve_draft_artifact,
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


@router.get("/{draft_id}/changes", response_model=list[DraftChange])
def changes(draft_id: str) -> list[DraftChange]:
    return get_draft_changes(draft_id)


@router.get("/{draft_id}/artifacts", response_model=list[DraftArtifact])
def artifacts(draft_id: str) -> list[DraftArtifact]:
    return get_draft_artifacts(draft_id)


@router.get("/{draft_id}/artifacts/{artifact_key}")
def artifact_file(draft_id: str, artifact_key: str) -> FileResponse:
    path, media_type, filename = resolve_draft_artifact(draft_id, artifact_key)
    return FileResponse(path, media_type=media_type, filename=filename)


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


@router.patch("/{draft_id}", response_model=Draft)
def update(draft_id: str, patch: DraftPatch) -> Draft:
    return patch_draft(draft_id, patch)


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
def amazon_draft(draft_id: str, request: AmazonDraftRequest | None = None) -> JobResponse:
    return start_amazon_draft(draft_id, request or AmazonDraftRequest())
