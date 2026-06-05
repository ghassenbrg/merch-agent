from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class DraftSummary(BaseModel):
    draft_id: str
    status: str
    title: str
    niche: str
    score: float
    selected_marketplaces: list[str]
    product_label: str
    eligible_for_amazon_draft: bool


class Draft(BaseModel):
    draft_id: str
    status: str
    niche: str
    summary: str
    score: dict[str, float]
    products: list[dict[str, Any]]
    marketplaces: list[dict[str, Any]]
    translation_mode: str
    design: dict[str, Any]
    listing_groups: dict[str, dict[str, Any]]
    validation: dict[str, Any]
    listing_validation: dict[str, Any]
    amazon_draft: dict[str, Any]
    price: dict[str, Any]


class StatusResponse(BaseModel):
    draft_id: str
    status: str
    message: str


class JobResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    job_id: str = Field(alias="jobId")
    status: str
    message: str


class AutopilotRequest(BaseModel):
    count: int = 5
    default_product: str = "standard_tshirt"
    explore_marketplaces: bool = True
    touch_amazon: bool = False


class RunResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    run_id: str = Field(alias="runId")
    status: Literal["COMPLETED", "FAILED", "RUNNING"]
    created_draft_ids: list[str] = Field(alias="createdDraftIds")
    message: str


class RunLog(BaseModel):
    run_id: str
    level: str
    message: str
    created_at: str
