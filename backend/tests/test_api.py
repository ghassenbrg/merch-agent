from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_list_drafts() -> None:
    response = client.get("/api/drafts")
    assert response.status_code == 200
    drafts = response.json()
    assert len(drafts) >= 1
    assert "draft_id" in drafts[0]


def test_autopilot_refuses_amazon_touch() -> None:
    response = client.post(
        "/api/workflows/autopilot/run",
        json={
            "count": 1,
            "default_product": "standard_tshirt",
            "explore_marketplaces": True,
            "touch_amazon": True,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "FAILED"
    assert "cannot touch Amazon" in body["message"]


def test_amazon_draft_rejects_unready_draft() -> None:
    response = client.post("/api/drafts/drf_20260605_0002/amazon-draft")
    assert response.status_code == 400
    assert response.json()["detail"] == "Draft is not ready for Amazon."
