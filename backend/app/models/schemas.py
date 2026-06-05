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
    design_title: str | None = Field(default=None, min_length=1, max_length=60)
    brand: str | None = Field(default=None, min_length=1, max_length=50)
    feature_bullet_1: str | None = Field(default=None, min_length=1, max_length=256)
    feature_bullet_2: str | None = Field(default=None, min_length=1, max_length=256)
    product_description: str | None = Field(default=None, min_length=1, max_length=2000)


class PricePatch(BaseModel):
    currency: str | None = Field(default=None, min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")
    amount: float | None = Field(default=None, gt=0, le=1000)


class DraftPatch(BaseModel):
    listing_groups: dict[str, ListingGroupPatch] | None = None
    selected_marketplaces: list[str] | None = Field(default=None, max_length=20)
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
    count: int = Field(default=5, ge=1, le=10)
    default_product: str = Field(default="standard_tshirt", min_length=1, max_length=80, pattern=r"^[a-z0-9_]+$")
    explore_marketplaces: bool = True
    touch_amazon: bool = False
    production_mode: bool = False


class AgentCandidatePayload(BaseModel):
    candidate_id: str | None = Field(default=None, min_length=1, max_length=120, pattern=r"^[a-zA-Z0-9_\\-]+$")
    niche: str = Field(min_length=3, max_length=160)
    audience: str = Field(min_length=3, max_length=240)
    keywords: list[str] = Field(default_factory=list, max_length=30)
    demand_signal: int = Field(default=70, ge=0, le=100)
    trend_signal: int = Field(default=70, ge=0, le=100)
    saturation_signal: int = Field(default=50, ge=0, le=100)
    compliance_signal: int = Field(default=90, ge=0, le=100)
    design_angle: str = Field(min_length=3, max_length=500)
    listing_angle: str = Field(min_length=3, max_length=500)
    risk_terms: list[str] = Field(default_factory=list, max_length=50)


class AgentPackageRequest(BaseModel):
    candidate: AgentCandidatePayload
    product: str = Field(default="standard_tshirt", min_length=1, max_length=80, pattern=r"^[a-z0-9_]+$")
    marketplaces: list[str] | None = Field(default=None, max_length=20)
    score: dict[str, float] | None = None
    listing_groups: dict[str, dict[str, Any]] | None = None
    artwork_path: str | None = Field(default=None, max_length=2000)
    creative_brief: dict[str, Any] | None = None
    research_trace: dict[str, Any] | None = None


class AgentPackageResponse(BaseModel):
    draft_id: str
    status: str
    artifact_dir: str
    message: str
    validation: dict[str, Any]


class RunResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    run_id: str = Field(alias="runId")
    status: Literal["COMPLETED", "FAILED", "RUNNING"]
    created_draft_ids: list[str] = Field(alias="createdDraftIds")
    message: str


class SchedulerStatus(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    scheduler_enabled: bool = Field(alias="schedulerEnabled")
    stop_switch_engaged: bool = Field(alias="stopSwitchEngaged")
    running: bool
    disk_usage_mb: float = Field(alias="diskUsageMb")
    disk_limit_mb: float = Field(alias="diskLimitMb")
    packages_generated_today: int = Field(alias="packagesGeneratedToday")
    max_packages_per_day: int = Field(alias="maxPackagesPerDay")
    max_packages_per_run: int = Field(alias="maxPackagesPerRun")
    scheduled_packages_per_run: int = Field(alias="scheduledPackagesPerRun")
    interval_minutes: int = Field(alias="intervalMinutes")
    cooldown_minutes: int = Field(alias="cooldownMinutes")
    next_run_allowed_at: str | None = Field(alias="nextRunAllowedAt")
    last_scheduled_run_id: str | None = Field(alias="lastScheduledRunId")
    blocked_reasons: list[str] = Field(alias="blockedReasons")


class SchedulerRunResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    status: Literal["COMPLETED", "FAILED", "SKIPPED", "RUNNING"]
    run_id: str | None = Field(default=None, alias="runId")
    created_draft_ids: list[str] = Field(default_factory=list, alias="createdDraftIds")
    message: str
    scheduler: SchedulerStatus


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
    autopilot_operations: dict[str, Any] | None = None
