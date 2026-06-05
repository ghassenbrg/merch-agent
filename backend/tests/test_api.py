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


def test_draft_edit_persists_and_requires_reapproval() -> None:
    response = client.patch(
        "/api/drafts/drf_20260605_0001",
        json={
            "listing_groups": {
                "English": {
                    "design_title": "Funny Fly Fishing Grandpa Gift",
                    "brand": "Quiet River Workshop",
                }
            },
            "selected_marketplaces": [".com"],
            "price": {"currency": "USD", "amount": 20.99},
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["listing_groups"]["English"]["design_title"] == "Funny Fly Fishing Grandpa Gift"
    assert body["listing_groups"]["English"]["brand"] == "Quiet River Workshop"
    assert body["status"] == "LISTING_READY"
    assert body["amazon_draft"]["eligible"] is False
    assert body["price"]["amount"] == 20.99
    assert [
        marketplace["code"]
        for marketplace in body["marketplaces"]
        if marketplace["selected"]
    ] == [".com"]

    persisted = client.get("/api/drafts/drf_20260605_0001").json()
    assert persisted["listing_groups"]["English"]["design_title"] == "Funny Fly Fishing Grandpa Gift"

    events = client.get("/api/drafts/drf_20260605_0001/events").json()
    assert any(event["event_type"] == "draft_updated" for event in events)

    changes = client.get("/api/drafts/drf_20260605_0001/changes").json()
    assert any(change["field"] == "listing_groups.English.design_title" for change in changes)


def test_draft_patch_cannot_set_ready_status_directly() -> None:
    response = client.patch(
        "/api/drafts/drf_20260605_0002",
        json={"status": "READY_FOR_AMAZON_DRAFT"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Use manual approval to set READY_FOR_AMAZON_DRAFT."


def test_draft_artifact_links_are_available() -> None:
    response = client.get("/api/drafts/drf_20260605_0001/artifacts")
    assert response.status_code == 200
    artifacts = response.json()
    assert any(artifact["key"] == "listing_fields" for artifact in artifacts)
    assert any(artifact["key"] == "change_history" for artifact in artifacts)


def test_draft_events_are_available() -> None:
    response = client.get("/api/drafts/drf_20260605_0001/events")
    assert response.status_code == 200
    events = response.json()
    assert len(events) >= 1
    assert events[0]["draft_id"] == "drf_20260605_0001"


def test_run_history_and_detail() -> None:
    run_response = client.post(
        "/api/workflows/autopilot/run",
        json={
            "count": 1,
            "default_product": "standard_tshirt",
            "explore_marketplaces": True,
            "touch_amazon": False,
        },
    )
    assert run_response.status_code == 200
    run_id = run_response.json()["runId"]

    list_response = client.get("/api/runs")
    assert list_response.status_code == 200
    assert any(run["runId"] == run_id for run in list_response.json())

    detail_response = client.get(f"/api/runs/{run_id}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["generatedDraftCount"] == 1
    assert detail["createdDraftIds"]
    assert detail["logs"]


def test_config_and_settings_patch() -> None:
    config_response = client.get("/api/config")
    assert config_response.status_code == 200
    config = config_response.json()
    assert ".com" in config["settings"]["enabled_marketplaces"]
    assert "ready_for_amazon_draft" in config["validation"]

    patch_response = client.patch(
        "/api/settings",
        json={"enabled_marketplaces": [".com", ".co.uk"]},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["enabled_marketplaces"] == [".com", ".co.uk"]
