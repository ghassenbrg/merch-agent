from fastapi import APIRouter, HTTPException

from app.models.schemas import (
    AutopilotRequest,
    RunResponse,
    RunLog,
    SchedulerRunResponse,
    SchedulerStatus,
)
from app.services.autopilot_service import run_autopilot
from app.services.run_service import get_run_logs
from app.services.scheduler_service import (
    get_scheduler_status,
    run_scheduler_tick,
    set_stop_switch,
)

router = APIRouter()


@router.post("/workflows/autopilot/run", response_model=RunResponse)
def start_autopilot(request: AutopilotRequest) -> RunResponse:
    return run_autopilot(request)


@router.get("/workflows/autopilot/scheduler", response_model=SchedulerStatus)
def scheduler_status() -> SchedulerStatus:
    return get_scheduler_status()


@router.post("/workflows/autopilot/scheduler/tick", response_model=SchedulerRunResponse)
def tick_scheduler() -> SchedulerRunResponse:
    return run_scheduler_tick()


@router.post("/workflows/autopilot/scheduler/stop", response_model=SchedulerStatus)
def stop_scheduler() -> SchedulerStatus:
    return set_stop_switch(True)


@router.post("/workflows/autopilot/scheduler/resume", response_model=SchedulerStatus)
def resume_scheduler() -> SchedulerStatus:
    return set_stop_switch(False)


@router.get("/runs/{run_id}/logs", response_model=list[RunLog])
def logs(run_id: str) -> list[RunLog]:
    run_logs = get_run_logs(run_id)
    if not run_logs:
        raise HTTPException(status_code=404, detail="Run logs not found")
    return run_logs
