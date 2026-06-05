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


class DraftEvent(BaseModel):
    draft_id: str
    event_type: str
    from_status: str | None = None
    to_status: str | None = None
    message: str
    created_at: str


class DraftChange(BaseModel):
    field: str
    before: Any
    after: Any
    created_at: str
    note: str


class DraftArtifact(BaseModel):
    key: str
    label: str
    kind: str
    path: str
    url: str
    exists: bool


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
    research: dict[str, Any] | None = None
    change_history: list[DraftChange] = Field(default_factory=list)


class ListingGroupPatch(BaseModel):
    design_title: str | None = None
    brand: str | None = None
    feature_bullet_1: str | None = None
    feature_bullet_2: str | None = None
    product_description: str | None = None


class PricePatch(BaseModel):
    currency: str | None = None
    amount: float | None = None


class DraftPatch(BaseModel):
    listing_groups: dict[str, ListingGroupPatch] | None = None
    selected_marketplaces: list[str] | None = None
    price: PricePatch | None = None
    status: str | None = None


class StatusResponse(BaseModel):
    draft_id: str
    status: str
    message: str


class AmazonDraftRequest(BaseModel):
    mode: Literal["dry_run", "controlled_live_save"] = "dry_run"
    manual_ui_triggered: bool = False
    save_draft_only_confirmed: bool = False
    visible_browser_confirmed: bool = False
    phase8_safety_confirmed: bool = False


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
    production_mode: bool = False


class RunResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    run_id: str = Field(alias="runId")
    status: Literal["COMPLETED", "FAILED", "RUNNING"]
    created_draft_ids: list[str] = Field(alias="createdDraftIds")
    message: str


class RunSummary(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    run_id: str = Field(alias="runId")
    mode: str
    status: str
    created_at: str
    completed_at: str | None = None
    generated_draft_count: int = Field(alias="generatedDraftCount")
    status_outcomes: dict[str, int] = Field(alias="statusOutcomes")


class RunDetail(RunSummary):
    created_draft_ids: list[str] = Field(alias="createdDraftIds")
    logs: list["RunLog"]


class RunLog(BaseModel):
    run_id: str
    level: str
    message: str
    created_at: str


class ConfigResponse(BaseModel):
    product_templates: dict[str, Any]
    marketplaces: dict[str, Any]
    pricing: dict[str, Any]
    validation: dict[str, Any]
    amazon_upload_ui: dict[str, Any]
    candidate_sources: dict[str, Any]
    settings: dict[str, Any]


class SettingsPatch(BaseModel):
    default_products: list[str] | None = None
    enabled_marketplaces: list[str] | None = None
    default_prices: dict[str, Any] | None = None
