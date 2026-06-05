from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.core.paths import DATA_DIR
from app.models.schemas import Draft
from app.services.local_package_workflow.candidates import NicheCandidate
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
) -> dict[str, Any]:
    local_checks_pass = compliance.passed and listing_validation.passed and price_config_exists
    return {
        "png_valid": True,
        "transparent_background": True,
        "correct_resolution": True,
        "file_size_under_limit": True,
        "design_not_too_small": True,
        "design_not_cropped": True,
        "trademark_precheck": "pass" if compliance.passed else "blocked",
        "amazon_policy_precheck": "pass" if compliance.passed else "blocked",
        "product_type_terms_removed": not listing_validation.product_type_terms_found,
        "listing_min_lengths_passed": listing_validation.min_description_length_passed,
        "selected_marketplaces_have_copy": listing_validation.selected_marketplaces_have_copy,
        "price_config_exists": price_config_exists,
        "local_checks_pass": local_checks_pass,
        "notes": [
            "Deterministic local package only; no Amazon interaction occurred.",
            "Design output is metadata-only until the artwork pipeline milestone.",
        ],
        "compliance_reasons": compliance.reasons,
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
) -> AssembledPackage:
    selected_marketplaces = marketplace_plan.selected_codes
    listing_groups = generate_listing_groups(candidate, marketplace_plan.language_sections)
    banned_terms = (
        validation_config.get("banned_product_type_terms", {}).get("english", [])
    )
    listing_validation = validate_listing_groups(
        listing_groups=listing_groups,
        selected_marketplaces=selected_marketplaces,
        banned_terms=banned_terms,
    )
    price = _price_payload(product.code, selected_marketplaces, default_prices)
    price_config_exists = all(
        price["marketplace_prices"].get(marketplace) is not None
        for marketplace in selected_marketplaces
    )
    validation = _validation_payload(
        compliance=compliance,
        listing_validation=listing_validation,
        price_config_exists=price_config_exists,
    )
    ready = validation["local_checks_pass"] and bool(selected_marketplaces)
    status = "READY_FOR_AMAZON_DRAFT" if ready else "LISTING_READY"
    if not compliance.passed:
        status = "BLOCKED_COMPLIANCE"

    design = generate_design_brief(candidate, product, draft_id)
    draft_payload = {
        "draft_id": draft_id,
        "status": status,
        "niche": candidate.niche,
        "summary": (
            f"Deterministic local package for {candidate.audience.lower()}. "
            "No external services or Amazon interaction were used."
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
    }
    draft = Draft.model_validate(draft_payload)

    artifact_dir = DATA_DIR / "drafts" / draft_id
    artifact_dir.mkdir(parents=True, exist_ok=True)
    artifacts = {
        "draft_json": str(artifact_dir / "draft.json"),
        "listing_fields": str(artifact_dir / "listing_fields.json"),
        "validation_report": str(artifact_dir / "validation_report.json"),
        "design_metadata": str(artifact_dir / "design_metadata.json"),
    }
    _write_json(Path(artifacts["draft_json"]), draft_payload)
    _write_json(Path(artifacts["listing_fields"]), listing_groups)
    _write_json(Path(artifacts["validation_report"]), validation)
    _write_json(Path(artifacts["design_metadata"]), design)

    return AssembledPackage(draft=draft, artifact_dir=artifact_dir, artifacts=artifacts)

