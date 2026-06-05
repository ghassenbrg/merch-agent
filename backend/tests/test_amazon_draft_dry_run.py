import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.db.database import get_connection
from app.main import app
from app.services.amazon_draft_service import is_dangerous_action, is_safe_action


client = TestClient(app)


def test_dangerous_amazon_actions_are_blocked() -> None:
    for label in [
        "Publish",
        "Submit",
        "Submit for review",
        "Make live",
        "Update live listing",
        "Create product",
    ]:
        assert is_dangerous_action(label) is True
        assert is_safe_action(label) is False


def test_save_draft_is_the_only_safe_draft_action() -> None:
    assert is_safe_action("Save Draft") is True
    assert is_safe_action("Save as Draft") is True
    assert is_safe_action("Save Draft and Publish") is False


def test_amazon_draft_endpoint_runs_playwright_dry_run_without_saving() -> None:
    response = client.post("/api/drafts/drf_20260605_0001/amazon-draft")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "AMAZON_DRAFT_DRY_RUN_COMPLETED"
    assert "No Amazon draft was saved" in body["message"]

    draft = client.get("/api/drafts/drf_20260605_0001").json()
    assert draft["status"] == "READY_FOR_AMAZON_DRAFT"
    assert draft["amazon_draft"]["saved"] is False
    assert draft["amazon_draft"]["locked"] is False
    last_dry_run = draft["amazon_draft"]["last_dry_run"]
    assert last_dry_run["job_id"] == body["jobId"]
    assert last_dry_run["touch_amazon"] is False
    assert last_dry_run["save_draft_clicked"] is False
    assert len(last_dry_run["screenshots"]) == 10
    for screenshot in last_dry_run["screenshots"]:
        assert Path(screenshot).is_file()

    with get_connection() as connection:
        attempt = connection.execute(
            """
            SELECT mode, status, payload
            FROM amazon_draft_attempts
            WHERE draft_id = ? AND job_id = ?
            """,
            ("drf_20260605_0001", body["jobId"]),
        ).fetchone()

    assert attempt is not None
    payload = json.loads(attempt["payload"])
    assert attempt["mode"] == "playwright_dry_run"
    assert attempt["status"] == "AMAZON_DRAFT_DRY_RUN_COMPLETED"
    assert payload["mode"] == "playwright_dry_run_local_mock"
    assert payload["touch_amazon"] is False
    assert payload["save_draft_clicked"] is False
    assert "listing_input" in payload["selector_keys_used"]
    assert all(check["blocked"] for check in payload["dangerous_action_checks"])


def test_dry_run_records_started_and_completed_events() -> None:
    response = client.post("/api/drafts/drf_20260605_0001/amazon-draft")

    assert response.status_code == 200
    events = client.get("/api/drafts/drf_20260605_0001/events").json()
    event_types = [event["event_type"] for event in events]
    assert "amazon_draft_dry_run_started" in event_types
    assert "amazon_draft_dry_run_completed" in event_types
