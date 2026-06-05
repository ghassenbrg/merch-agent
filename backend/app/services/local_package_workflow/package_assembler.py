from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.core.paths import DATA_DIR
from app.models.schemas import Draft
from app.services.artwork_validation_service import (
    artwork_validation_flags,
    validate_artwork_png,
)
from app.services.local_package_workflow.candidates import (
    CandidateAuditRecord,
    NicheCandidate,
)
from app.services.local_package_workflow.compliance import ComplianceResult
from app.services.local_package_workflow.design import generate_design_brief
from app.services.local_package_workflow.listing import (
    ListingValidationResult,
    generate_listing_groups,
    validate_listing_groups,
)
from app.services.local_package_workflow.marketplaces import MarketplacePlan
from app.services.local_package_workflow.product_templates import ProductResolution


@dataclass(frozen=True)
class AssembledPackage:
    draft: Draft
    artifact_dir: Path
    artifacts: dict[str, str]


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _price_payload(
    product_code: str,
    selected_marketplaces: list[str],
    default_prices: dict[str, Any],
) -> dict[str, Any]:
    product_prices = default_prices.get(product_code, {})
    first_price = next(
        (
            product_prices[marketplace]
            for marketplace in selected_marketplaces
            if marketplace in product_prices
        ),
        {},
    )
    return {
        "currency": first_price.get("currency", "USD"),
        "amount": first_price.get("amount"),
        "royalty_positive": bool(first_price.get("amount")),
        "marketplace_prices": {
            marketplace: product_prices.get(marketplace)
            for marketplace in selected_marketplaces
        },
    }


def _validation_payload(
    compliance: ComplianceResult,
    listing_validation: ListingValidationResult,
    price_config_exists: bool,
    artwork_validation: dict[str, Any],
) -> dict[str, Any]:
    artwork_flags = artwork_validation_flags(artwork_validation)
    artwork_passed = all(artwork_flags.values())
    local_checks_pass = (
        compliance.passed
        and listing_validation.passed
        and price_config_exists
        and artwork_passed
    )
    return {
        **artwork_flags,
        "artwork_status": artwork_validation["status"],
        "artwork_pending": artwork_validation["status"] == "pending",
        "artwork": artwork_validation,
        "trademark_precheck": compliance.status,
        "amazon_policy_precheck": compliance.status,
        "human_review_required": compliance.human_review_required,
        "compliance_blocked": compliance.blocked,
        "product_type_terms_removed": not listing_validation.product_type_terms_found,
        "listing_min_lengths_passed": listing_validation.min_description_length_passed,
        "selected_marketplaces_have_copy": listing_validation.selected_marketplaces_have_copy,
        "listing_field_lengths_passed": listing_validation.field_lengths_passed,
        "listing_punctuation_passed": listing_validation.punctuation_passed,
        "marketplace_language_copy_passed": listing_validation.marketplace_language_copy_passed,
        "translation_checks_passed": listing_validation.translation_checks_passed,
        "price_config_exists": price_config_exists,
        "local_checks_pass": local_checks_pass,
        "notes": [
            "Deterministic local package only; no Amazon interaction occurred.",
            (
                "Design output is pending; final PNG validation has not passed yet."
                if artwork_validation["status"] == "pending"
                else "Final PNG was rendered and inspected locally by the artwork validation contract."
            ),
        ],
        "compliance_reasons": compliance.reasons,
        "blocked_policy_terms": compliance.blocked_terms or [],
        "human_review_policy_terms": compliance.review_terms or [],
    }


def assemble_local_package(
    draft_id: str,
    candidate: NicheCandidate,
    product: ProductResolution,
    marketplace_plan: MarketplacePlan,
    score: dict[str, float],
    compliance: ComplianceResult,
    validation_config: dict[str, Any],
    default_prices: dict[str, Any],
    candidate_audit: CandidateAuditRecord | None = None,
    research_snapshot: dict[str, Any] | None = None,
    research_snapshot_path: str | None = None,
    listing_groups_override: dict[str, dict[str, Any]] | None = None,
    design_override: dict[str, Any] | None = None,
) -> AssembledPackage:
    selected_marketplaces = marketplace_plan.selected_codes
    listing_groups = listing_groups_override or generate_listing_groups(candidate, marketplace_plan.language_sections)
    banned_terms = validation_config.get("banned_product_type_terms", {})
    field_constraints = validation_config.get("listing_field_constraints", {})
    translation_required_locales = validation_config.get(
        "translation_required_locales",
        ["de", "fr", "it", "es", "ja"],
    )
    listing_validation = validate_listing_groups(
        listing_groups=listing_groups,
        selected_marketplaces=selected_marketplaces,
        banned_terms=banned_terms,
        field_constraints=field_constraints,
        marketplace_language_map={
            marketplace.code: marketplace.language_group
            for marketplace in marketplace_plan.marketplaces
        },
        translation_required_locales=translation_required_locales,
    )
    price = _price_payload(product.code, selected_marketplaces, default_prices)
    price_config_exists = all(
        price["marketplace_prices"].get(marketplace) is not None
        for marketplace in selected_marketplaces
    )
    design = design_override or generate_design_brief(candidate, product, draft_id)
    artwork_validation = validate_artwork_png(
        png_path=design.get("final_png"),
        expected_width=product.width,
        expected_height=product.height,
        design_metadata=design,
        validation_config=validation_config,
    )
    validation = _validation_payload(
        compliance=compliance,
        listing_validation=listing_validation,
        price_config_exists=price_config_exists,
        artwork_validation=artwork_validation,
    )
    ready = validation["local_checks_pass"] and bool(selected_marketplaces)
    if ready:
        status = "READY_FOR_AMAZON_DRAFT"
    elif compliance.human_review_required:
        status = "HUMAN_REVIEW_REQUIRED"
    elif validation["artwork_status"] == "pending":
        status = "ARTWORK_PENDING"
    elif validation["artwork_status"] == "failed":
        status = "BLOCKED_ARTWORK"
    else:
        status = "LISTING_READY"
    if compliance.blocked:
        status = "BLOCKED_COMPLIANCE"
    has_research_snapshot = research_snapshot is not None
    score_source = (
        "live_research_snapshot"
        if has_research_snapshot and research_snapshot.get("source") == "live_adapters"
        else "research_snapshot"
        if has_research_snapshot
        else "candidate_signal_fixture"
    )

    draft_payload = {
        "draft_id": draft_id,
        "status": status,
        "niche": candidate.niche,
        "summary": (
            f"Deterministic local package for {candidate.audience.lower()}. "
            "Live research evidence was persisted before scoring. "
            "No Amazon interaction was used."
            if has_research_snapshot
            else (
                f"Deterministic local package for {candidate.audience.lower()}. "
                "No external services or Amazon interaction were used."
            )
        ),
        "score": score,
        "products": [product.to_payload(selected=True)],
        "marketplaces": [marketplace.to_payload() for marketplace in marketplace_plan.marketplaces],
        "translation_mode": "provide_own_translations",
        "design": design,
        "listing_groups": listing_groups,
        "validation": validation,
        "listing_validation": listing_validation.to_payload(),
        "amazon_draft": {
            "eligible": ready,
            "saved": False,
            "publish_allowed": False,
            "last_job_id": None,
            "safety_mode": "manual_one_draft_save_only",
        },
        "price": price,
        "research": {
            **candidate.source_payload(),
            "external_research_used": has_research_snapshot or candidate.source_type.startswith("external"),
            "audit_record": (
                candidate_audit.to_payload() if candidate_audit is not None else None
            ),
            "snapshot": research_snapshot,
            "snapshot_path": research_snapshot_path,
            "score_source": score_source,
        },
    }
    draft = Draft.model_validate(draft_payload)

    artifact_dir = DATA_DIR / "drafts" / draft_id
    artifact_dir.mkdir(parents=True, exist_ok=True)
    artifacts = {
        "draft_json": str(artifact_dir / "draft.json"),
        "listing_fields": str(artifact_dir / "listing_fields.json"),
        "validation_report": str(artifact_dir / "validation_report.json"),
        "design_metadata": str(artifact_dir / "design_metadata.json"),
        "candidate_research": str(artifact_dir / "candidate_research.json"),
        "design_source": design["source"],
        "render_metadata": design["render_metadata"],
        "final_png": design["final_png"],
    }
    _write_json(Path(artifacts["draft_json"]), draft_payload)
    _write_json(Path(artifacts["listing_fields"]), listing_groups)
    _write_json(Path(artifacts["validation_report"]), validation)
    _write_json(Path(artifacts["design_metadata"]), design)
    _write_json(Path(artifacts["candidate_research"]), draft_payload["research"])

    return AssembledPackage(draft=draft, artifact_dir=artifact_dir, artifacts=artifacts)
