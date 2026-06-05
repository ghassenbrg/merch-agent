from fastapi import APIRouter

from app.models.schemas import ConfigResponse, SettingsPatch
from app.services.config_service import get_config, update_settings

router = APIRouter()


@router.get("/config", response_model=ConfigResponse)
def show_config() -> ConfigResponse:
    return get_config()


@router.patch("/settings", response_model=dict)
def patch_settings(patch: SettingsPatch) -> dict:
    return update_settings(patch)
