from __future__ import annotations

from app.services.config_service import get_config
from app.services.local_package_workflow.candidates import NicheCandidate
from app.services.local_package_workflow.compliance import run_compliance_gate
from app.services.local_package_workflow.listing import validate_listing_groups
from app.services.local_package_workflow.marketplaces import resolve_marketplaces
from app.services.local_package_workflow.package_assembler import assemble_local_package
from app.services.local_package_workflow.product_templates import resolve_product_template
from app.services.local_package_workflow.scoring import score_candidate


def _candidate(**overrides: object) -> NicheCandidate:
    payload = {
        "candidate_id": "cand_policy_test",
        "niche": "Garden reading weekends",
        "audience": "Readers and gardeners",
        "keywords": ["garden reader", "quiet weekend"],
        "demand_signal": 75,
        "trend_signal": 72,
        "saturation_signal": 55,
        "compliance_signal": 96,
        "design_angle": "Botanical book stack with general weekend typography",
        "listing_angle": "quiet reading and gardening design for weekend downtime",
        "risk_terms": [],
    }
    payload.update(overrides)
    return NicheCandidate(**payload)


def _english_listing(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "locale": "en",
        "marketplaces": [".com"],
        "design_title": "Garden Reading Weekend",
        "brand": "Quiet Grove Studio",
        "feature_bullet_1": "Original reading and gardening design for quiet weekend downtime.",
        "feature_bullet_2": "Gift idea for readers, gardeners, book clubs, and relaxed family days.",
        "product_description": (
            "A calm botanical reading design for gardeners, book lovers, and families shopping "
            "for a relaxed general-interest gift."
        ),
    }
    payload.update(overrides)
    return payload


def test_compliance_allows_generic_low_risk_candidate() -> None:
    result = run_compliance_gate(_candidate())

    assert result.passed is True
    assert result.status == "pass"
    assert result.reasons == []


def test_compliance_blocks_protected_phrase_level_references() -> None:
    result = run_compliance_gate(
        _candidate(
            niche="Officially licensed Disney marathon",
            keywords=["officially licensed", "disney"],
            design_angle="Theme park castle vacation countdown",
            listing_angle="official merchandise style family trip design",
        )
    )

    assert result.passed is False
    assert result.blocked is True
    assert "brand_or_trademark:disney" in result.blocked_terms
    assert "misleading_product_claim:official merchandise" in result.blocked_terms


def test_compliance_marks_ambiguous_phrases_for_human_review() -> None:
    result = run_compliance_gate(
        _candidate(
            niche="Big game grilling weekend",
            keywords=["big game", "championship sunday"],
            listing_angle="tailgate-inspired grilling design for championship sunday",
        )
    )

    assert result.passed is False
    assert result.human_review_required is True
    assert "ambiguous_event_reference:big game" in result.review_terms


def test_ambiguous_compliance_package_is_not_amazon_draft_ready() -> None:
    config = get_config()
    candidate = _candidate(
        niche="Big game grilling weekend",
        keywords=["big game"],
        listing_angle="grilling design for championship sunday",
    )
    product = resolve_product_template(config.product_templates, "standard_tshirt")
    plan = resolve_marketplaces(
        marketplace_config=config.marketplaces,
        enabled_marketplaces=[".com"],
        priced_marketplaces=[".com"],
        explore_marketplaces=True,
    )

    package = assemble_local_package(
        draft_id="drf_test_human_review_required",
        candidate=candidate,
        product=product,
        marketplace_plan=plan,
        score=score_candidate(candidate),
        compliance=run_compliance_gate(candidate),
        validation_config=config.validation,
        default_prices=config.settings["default_prices"],
    )

    assert package.draft.status == "HUMAN_REVIEW_REQUIRED"
    assert package.draft.amazon_draft["eligible"] is False
    assert package.draft.validation["human_review_required"] is True
    assert package.draft.validation["amazon_policy_precheck"] == "human_review_required"


def test_listing_validator_allows_clean_english_listing() -> None:
    result = validate_listing_groups(
        listing_groups={"English": _english_listing()},
        selected_marketplaces=[".com"],
        banned_terms={"english": ["shirt", "hoodie"]},
        marketplace_language_map={".com": "English"},
    )

    assert result.passed is True
    assert result.warnings == []


def test_listing_validator_blocks_product_terms_length_and_punctuation() -> None:
    result = validate_listing_groups(
        listing_groups={
            "English": _english_listing(
                design_title="Fishing Shirt!!! " + ("x" * 70),
                feature_bullet_1="Great shirt!!!",
            )
        },
        selected_marketplaces=[".com"],
        banned_terms={"english": ["shirt"]},
        marketplace_language_map={".com": "English"},
    )

    assert result.passed is False
    assert "English.design_title:shirt" in result.product_type_terms_found
    assert result.field_lengths_passed is False
    assert result.punctuation_passed is False


def test_listing_validator_requires_matching_marketplace_language_copy() -> None:
    result = validate_listing_groups(
        listing_groups={"English": _english_listing(marketplaces=[".de"])},
        selected_marketplaces=[".de"],
        banned_terms={"english": ["shirt"]},
        marketplace_language_map={".de": "German"},
    )

    assert result.passed is False
    assert result.marketplace_language_copy_passed is False
    assert any("German" in warning for warning in result.warnings)


def test_listing_validator_requires_reviewed_non_english_translation() -> None:
    result = validate_listing_groups(
        listing_groups={
            "German": {
                **_english_listing(marketplaces=[".de"]),
                "locale": "de",
            }
        },
        selected_marketplaces=[".de"],
        banned_terms={"german": ["shirt"]},
        marketplace_language_map={".de": "German"},
    )

    assert result.passed is False
    assert result.translation_checks_passed is False
    assert "German listing requires reviewed de copy." in result.warnings
