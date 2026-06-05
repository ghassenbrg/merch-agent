from __future__ import annotations

from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

from app.main import app


client = TestClient(app)


def _write_valid_artwork(path) -> None:
    image = Image.new("RGBA", (4500, 5400), (255, 255, 255, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(
        [900, 1000, 3600, 4100],
        radius=120,
        fill=(22, 90, 82, 255),
    )
    draw.rectangle([1450, 1900, 3050, 2150], fill=(255, 246, 210, 255))
    draw.rectangle([1450, 2300, 3050, 2550], fill=(255, 246, 210, 255))
    image.save(path, format="PNG", optimize=True)


def test_agent_package_import_accepts_codex_selected_artwork(tmp_path) -> None:
    artwork_path = tmp_path / "agent-artwork.png"
    _write_valid_artwork(artwork_path)

    response = client.post(
        "/api/agent/packages",
        json={
            "candidate": {
                "candidate_id": "agent_garden_reader",
                "niche": "Garden Book Club Weekends",
                "audience": "Readers, gardeners, and cozy weekend gift buyers",
                "keywords": ["garden reader", "book club", "plant lover"],
                "demand_signal": 82,
                "trend_signal": 74,
                "saturation_signal": 40,
                "compliance_signal": 96,
                "design_angle": "Botanical book stack with original cozy lettering",
                "listing_angle": "quiet reading and gardening gift idea",
                "risk_terms": [],
            },
            "product": "standard_tshirt",
            "marketplaces": [".com"],
            "score": {
                "overall": 88,
                "demand": 82,
                "trend": 74,
                "competition": 60,
                "compliance": 96,
            },
            "artwork_path": str(artwork_path),
            "creative_brief": {
                "design_concept": "Botanical book club emblem",
                "recommended_product_colors": ["black", "navy", "dark heather"],
            },
            "listing_groups": {
                "English": {
                    "locale": "en",
                    "marketplaces": [".com"],
                    "design_title": "Garden Book Club Weekends",
                    "brand": "Quiet Grove Studio",
                    "feature_bullet_1": "Original reading and gardening artwork for cozy weekend plans.",
                    "feature_bullet_2": "Gift-ready botanical book design for readers, plant lovers, and clubs.",
                    "product_description": (
                        "A calm reading and garden themed design for people who plan their weekends "
                        "around books, plants, and quiet club conversations."
                    ),
                }
            },
            "research_trace": {
                "goal": "Find safe garden reader opportunities",
                "decision_reason": "Strong gift intent with low IP risk.",
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "READY_FOR_AMAZON_DRAFT"
    draft_id = body["draft_id"]

    draft_response = client.get(f"/api/drafts/{draft_id}")
    assert draft_response.status_code == 200
    draft = draft_response.json()
    assert draft["research"]["agent_import"] is True
    assert draft["research"]["agent_trace"]["source"] == "codex_agent"
    assert draft["design"]["brief"]["generation_status"] == "imported_from_codex_agent"
    assert draft["design"]["brief"]["external_services_used"] is True
    assert draft["validation"]["png_valid"] is True
    assert draft["validation"]["correct_resolution"] is True
    assert draft["validation"]["transparent_background"] is True


def test_agent_package_import_preserves_compliance_block() -> None:
    response = client.post(
        "/api/agent/packages",
        json={
            "candidate": {
                "candidate_id": "agent_blocked_brand",
                "niche": "Disney Vacation Countdown",
                "audience": "Theme park travelers",
                "keywords": ["disney", "vacation", "countdown"],
                "demand_signal": 90,
                "trend_signal": 85,
                "saturation_signal": 42,
                "compliance_signal": 20,
                "design_angle": "Brand-connected vacation phrase",
                "listing_angle": "theme park family travel idea",
                "risk_terms": ["disney"],
            },
            "product": "standard_tshirt",
            "marketplaces": [".com"],
            "research_trace": {
                "goal": "Confirm blocked candidates stay blocked",
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "BLOCKED_COMPLIANCE"
    assert body["validation"]["compliance_blocked"] is True
