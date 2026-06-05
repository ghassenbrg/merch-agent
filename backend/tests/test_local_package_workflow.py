from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image

from app.core.paths import DATA_DIR
from app.main import app
from app.services.config_service import get_config
from app.services.local_package_workflow.candidates import LOCAL_FIXTURE_CANDIDATES
from app.services.local_package_workflow.compliance import run_compliance_gate
from app.services.local_package_workflow.listing import validate_listing_groups
from app.services.local_package_workflow.marketplaces import resolve_marketplaces
from app.services.local_package_workflow.package_assembler import assemble_local_package
from app.services.local_package_workflow.product_templates import resolve_product_template
from app.services.local_package_workflow.scoring import score_candidate


client = TestClient(app)


def test_product_template_resolver_uses_yaml_contract() -> None:
    config = get_config()
    product = resolve_product_template(config.product_templates, "standard_tshirt")

    assert product.code == "standard_tshirt"
    assert product.template == "tshirts_sweatshirts_long_sleeve_back_hoodie"
    assert product.width == 4500
    assert product.height == 5400


def test_marketplace_resolver_selects_enabled_priced_marketplaces() -> None:
    config = get_config()
    plan = resolve_marketplaces(
        marketplace_config=config.marketplaces,
        enabled_marketplaces=[".com", ".co.uk", ".de"],
        priced_marketplaces=[".com", ".co.uk"],
        explore_marketplaces=True,
    )

    assert plan.selected_codes == [".com", ".co.uk"]
    assert plan.language_sections[0].name == "English"
    german = next(marketplace for marketplace in plan.marketplaces if marketplace.code == ".de")
    assert german.selected is False
    assert german.excluded_reason == "No local price config for selected product."


def test_scoring_model_converts_saturation_to_positive_subscore() -> None:
    score = score_candidate(LOCAL_FIXTURE_CANDIDATES[0])

    assert score["demand"] == 82
    assert score["saturation"] == 32
    assert score["overall"] > 70


def test_compliance_gate_blocks_risky_fixture_before_assembly() -> None:
    blocked = run_compliance_gate(LOCAL_FIXTURE_CANDIDATES[-1])

    assert blocked.passed is False
    assert blocked.status == "blocked"
    assert blocked.reasons == ["Blocked policy phrase: brand_or_trademark:disney"]


def test_listing_validator_rejects_banned_product_type_terms() -> None:
    result = validate_listing_groups(
        listing_groups={
            "English": {
                "marketplaces": [".com"],
                "design_title": "Fishing Shirt",
                "brand": "River Studio",
                "feature_bullet_1": "Original outdoors design.",
                "feature_bullet_2": "Gift idea for quiet weekends.",
                "product_description": "A calm outdoors design for families and anglers who enjoy weekends near the river.",
            }
        },
        selected_marketplaces=[".com"],
        banned_terms=["shirt"],
    )

    assert result.passed is False
    assert result.product_type_terms_found == ["English.design_title:shirt"]


def test_package_assembler_writes_required_local_artifacts() -> None:
    config = get_config()
    candidate = LOCAL_FIXTURE_CANDIDATES[1]
    product = resolve_product_template(config.product_templates, "standard_tshirt")
    plan = resolve_marketplaces(
        marketplace_config=config.marketplaces,
        enabled_marketplaces=[".com", ".co.uk"],
        priced_marketplaces=[".com", ".co.uk"],
        explore_marketplaces=True,
    )
    package = assemble_local_package(
        draft_id="drf_test_local_package",
        candidate=candidate,
        product=product,
        marketplace_plan=plan,
        score=score_candidate(candidate),
        compliance=run_compliance_gate(candidate),
        validation_config=config.validation,
        default_prices=config.settings["default_prices"],
    )

    assert package.draft.status == "READY_FOR_AMAZON_DRAFT"
    assert package.draft.amazon_draft["eligible"] is True
    assert package.draft.design["brief"]["generation_status"] == "rendered_locally"
    assert package.draft.design["brief"]["external_services_used"] is False
    for artifact in [
        "draft.json",
        "listing_fields.json",
        "validation_report.json",
        "design_metadata.json",
        "candidate_research.json",
    ]:
        assert (DATA_DIR / "drafts" / "drf_test_local_package" / artifact).is_file()

    payload = json.loads(Path(package.artifacts["draft_json"]).read_text())
    assert payload["draft_id"] == "drf_test_local_package"
    assert payload["validation"]["local_checks_pass"] is True
    assert payload["validation"]["artwork_status"] == "passed"
    assert payload["validation"]["artwork_pending"] is False
    assert payload["validation"]["artwork"]["checks"]["png_present"]["passed"] is True
    assert payload["validation"]["png_valid"] is True

    final_png = DATA_DIR.parent / package.artifacts["final_png"]
    source = DATA_DIR.parent / package.artifacts["design_source"]
    render_metadata = DATA_DIR.parent / package.artifacts["render_metadata"]
    assert final_png.is_file()
    assert source.is_file()
    assert render_metadata.is_file()
    with Image.open(final_png) as image:
        assert image.mode == "RGBA"
        assert image.size == (4500, 5400)
        assert image.getchannel("A").getpixel((0, 0)) == 0


def test_autopilot_endpoint_creates_real_local_package_artifacts() -> None:
    response = client.post(
        "/api/workflows/autopilot/run",
        json={
            "count": 1,
            "default_product": "standard_tshirt",
            "explore_marketplaces": True,
            "touch_amazon": False,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "COMPLETED"
    draft_id = body["createdDraftIds"][0]

    draft_response = client.get(f"/api/drafts/{draft_id}")
    assert draft_response.status_code == 200
    draft = draft_response.json()
    assert draft["status"] == "READY_FOR_AMAZON_DRAFT"
    assert draft["design"]["brief"]["generation_status"] == "rendered_locally"
    assert draft["design"]["brief"]["external_services_used"] is False
    assert draft["amazon_draft"]["publish_allowed"] is False
    assert draft["amazon_draft"]["eligible"] is True
    assert draft["validation"]["artwork_status"] == "passed"
    assert draft["validation"]["png_valid"] is True
    assert draft["validation"]["artwork"]["checks"]["correct_resolution"]["passed"] is True

    png_response = client.get(f"/api/drafts/{draft_id}/design/final.png")
    assert png_response.status_code == 200
    assert png_response.headers["content-type"] == "image/png"

    artifact_dir = DATA_DIR / "drafts" / draft_id
    assert (artifact_dir / "draft.json").is_file()
    assert (artifact_dir / "listing_fields.json").is_file()
    assert (artifact_dir / "validation_report.json").is_file()
    assert (artifact_dir / "design_metadata.json").is_file()
    assert (artifact_dir / "candidate_research.json").is_file()
    assert (DATA_DIR / "designs" / draft_id / "source.json").is_file()
    assert (DATA_DIR / "designs" / draft_id / "render_metadata.json").is_file()
    assert (DATA_DIR / "designs" / draft_id / "final.png").is_file()
