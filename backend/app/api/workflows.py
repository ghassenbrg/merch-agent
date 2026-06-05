from fastapi import APIRouter, HTTPException

from app.models.schemas import AutopilotRequest, RunResponse, RunLog
from app.services.autopilot_service import run_autopilot
from app.services.run_service import get_run_logs

router = APIRouter()


@router.post("/workflows/autopilot/run", response_model=RunResponse)
def start_autopilot(request: AutopilotRequest) -> RunResponse:
    return run_autopilot(request)


@router.get("/runs/{run_id}/logs", response_model=list[RunLog])
def logs(run_id: str) -> list[RunLog]:
    run_logs = get_run_logs(run_id)
    if not run_logs:
        raise HTTPException(status_code=404, detail="Run logs not found")
    return run_logs
