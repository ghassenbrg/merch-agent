from fastapi import APIRouter, HTTPException

from app.models.schemas import RunDetail, RunLog, RunSummary
from app.services.run_service import get_run, get_run_logs, list_runs

router = APIRouter()


@router.get("", response_model=list[RunSummary])
def index() -> list[RunSummary]:
    return list_runs()


@router.get("/{run_id}", response_model=RunDetail)
def show(run_id: str) -> RunDetail:
    run = get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.get("/{run_id}/logs", response_model=list[RunLog])
def logs(run_id: str) -> list[RunLog]:
    run_logs = get_run_logs(run_id)
    if not run_logs:
        raise HTTPException(status_code=404, detail="Run logs not found")
    return run_logs
