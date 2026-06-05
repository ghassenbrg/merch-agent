from fastapi import APIRouter

from app.models.schemas import AgentPackageRequest, AgentPackageResponse
from app.services.agent_import_service import import_agent_package


router = APIRouter()


@router.post("/agent/packages", response_model=AgentPackageResponse)
def import_package(request: AgentPackageRequest) -> AgentPackageResponse:
    return import_agent_package(request)
