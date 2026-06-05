from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

import app.services.amazon_draft_service as amazon_draft_service
from app.db.database import get_connection
from app.db.repositories import upsert_draft_projection
from app.main import app
from app.services.draft_service import require_draft


client = TestClient(app)


LIVE_CONFIRMATION = {
    "mode": "controlled_live_save",
    "manual_ui_triggered": True,
    "save_draft_only_confirmed": True,
    "visible_browser_confirmed": True,
    "phase8_safety_confirmed": True,
}


def _create_ready_draft() -> str:
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
    return response.json()["createdDraftIds"][0]


def _live_report(job_id: str, draft_id: str, tmp_path: Path) -> dict:
    before = tmp_path / "before-save-draft.png"
    after = tmp_path / "after-save-draft.png"
    before.write_bytes(b"before")
    after.write_bytes(b"after")
    return {
        "job_id": job_id,
        "mode": "controlled_live_amazon_save_draft",
        "status": "AMAZON_DRAFT_SAVED",
        "browser_profile": str(tmp_path / "profile"),
        "visible_browser": True,
        "headless": False,
        "touch_amazon": True,
        "save_draft_clicked": True,
        "publish_allowed": False,
        "selected_product": "standard_tshirt",
        "selected_marketplaces": [".com"],
        "screenshots": [
            {"step": "before-save-draft", "screenshot": str(before)},
            {"step": "after-save-draft", "screenshot": str(after)},
        ],
        "draft_id": draft_id,
    }


def test_controlled_live_save_requires_explicit_ui_confirmations() -> None:
    response = client.post(
        "/api/drafts/drf_20260605_0001/amazon-draft",
        json={"mode": "controlled_live_save"},
    )

    assert response.status_code == 400
    assert "manual_ui_triggered" in response.json()["detail"]

    draft = client.get("/api/drafts/drf_20260605_0001").json()
    assert draft["status"] == "READY_FOR_AMAZON_DRAFT"
    assert draft["amazon_draft"]["saved"] is False


def test_controlled_live_save_marks_saved_and_records_attempt(monkeypatch, tmp_path: Path) -> None:
    draft_id = _create_ready_draft()

    def fake_live_save(draft, job_id, ui_contract):
        return _live_report(job_id, draft.draft_id, tmp_path)

    monkeypatch.setattr(amazon_draft_service, "_run_playwright_live_save", fake_live_save)

    response = client.post(f"/api/drafts/{draft_id}/amazon-draft", json=LIVE_CONFIRMATION)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "AMAZON_DRAFT_SAVED"

    draft = client.get(f"/api/drafts/{draft_id}").json()
    assert draft["status"] == "AMAZON_DRAFT_SAVED"
    assert draft["amazon_draft"]["saved"] is True
    assert draft["amazon_draft"]["eligible"] is False
    assert draft["amazon_draft"]["locked"] is False
    assert draft["amazon_draft"]["last_live_save"]["save_draft_clicked"] is True
    assert len(draft["amazon_draft"]["last_live_save"]["screenshots"]) == 2

    events = client.get(f"/api/drafts/{draft_id}/events").json()
    assert "amazon_draft_live_save_started" in [event["event_type"] for event in events]
    assert "amazon_draft_live_save_completed" in [event["event_type"] for event in events]

    with get_connection() as connection:
        attempt = connection.execute(
            """
            SELECT mode, status, payload
            FROM amazon_draft_attempts
            WHERE draft_id = ? AND job_id = ?
            """,
            (draft_id, body["jobId"]),
        ).fetchone()

    assert attempt is not None
    payload = json.loads(attempt["payload"])
    assert attempt["mode"] == "controlled_live_save"
    assert attempt["status"] == "AMAZON_DRAFT_SAVED"
    assert payload["touch_amazon"] is True
    assert payload["save_draft_clicked"] is True
    assert payload["publish_allowed"] is False


def test_controlled_live_save_failure_marks_failed(monkeypatch) -> None:
    draft_id = _create_ready_draft()

    def failing_live_save(draft, job_id, ui_contract):
        raise RuntimeError("selector confirmation failed")

    monkeypatch.setattr(amazon_draft_service, "_run_playwright_live_save", failing_live_save)

    response = client.post(f"/api/drafts/{draft_id}/amazon-draft", json=LIVE_CONFIRMATION)

    assert response.status_code == 500
    assert "Controlled live Amazon draft save failed" in response.json()["detail"]

    draft = client.get(f"/api/drafts/{draft_id}").json()
    assert draft["status"] == "AMAZON_DRAFT_FAILED"
    assert draft["amazon_draft"]["saved"] is False
    assert draft["amazon_draft"]["eligible"] is False
    assert draft["amazon_draft"]["locked"] is False
    assert draft["amazon_draft"]["last_live_save"]["save_draft_clicked"] is False


def test_amazon_draft_assist_rejects_multiple_selected_products() -> None:
    draft_id = _create_ready_draft()
    draft = require_draft(draft_id)
    draft.products.append({**draft.products[0], "code": "premium_tshirt", "selected": True})
    with get_connection() as connection:
        upsert_draft_projection(connection, draft)

    response = client.post(f"/api/drafts/{draft_id}/amazon-draft", json=LIVE_CONFIRMATION)

    assert response.status_code == 400
    assert response.json()["detail"] == "Amazon Draft Assist requires exactly one selected product."
