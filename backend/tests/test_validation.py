from app.fixtures.sample_data import SAMPLE_DRAFTS
from app.models.schemas import Draft
from app.services.validation_service import compute_ready_for_amazon_draft, find_product_type_terms


def test_ready_sample_passes() -> None:
    draft = Draft.model_validate(SAMPLE_DRAFTS[0])
    ready, warnings = compute_ready_for_amazon_draft(draft)
    assert ready is True
    assert warnings == []


def test_product_type_terms_block_listing() -> None:
    data = SAMPLE_DRAFTS[0].copy()
    data["listing_groups"] = {
        "English": {
            **SAMPLE_DRAFTS[0]["listing_groups"]["English"],
            "feature_bullet_1": "Great fishing shirt for grandpas.",
        }
    }
    draft = Draft.model_validate(data)
    found = find_product_type_terms(draft)
    assert "English.feature_bullet_1:shirt" in found
