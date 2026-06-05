from fastapi.testclient import TestClient

from app.db.database import get_connection
from app.main import app


client = TestClient(app)


def _set_operations(**overrides):
    operations = {
        "scheduler_enabled": True,
        "stop_switch_engaged": False,
        "interval_minutes": 0,
        "cooldown_minutes": 0,
        "scheduled_packages_per_run": 2,
        "max_packages_per_run": 10,
        "max_packages_per_day": 100,
        "disk_usage_limit_mb": 4096,
        "default_product": "standard_tshirt",
        "explore_marketplaces": True,
        "production_mode": False,
    }
    operations.update(overrides)
    response = client.patch(
        "/api/settings",
        json={"autopilot_operations": operations},
    )
    assert response.status_code == 200
    return operations


def _amazon_attempt_count() -> int:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT COUNT(*) AS count FROM amazon_draft_attempts",
        ).fetchone()
    return int(row["count"])


def _scheduled_package_count_today() -> int:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT COUNT(rd.draft_id) AS count
            FROM runs r
            JOIN run_drafts rd ON rd.run_id = r.run_id
            WHERE r.mode = 'scheduled_autopilot'
              AND date(r.created_at) = date('now')
            """,
        ).fetchone()
    return int(row["count"])


def test_scheduled_autopilot_creates_local_packages_only() -> None:
    _set_operations(scheduled_packages_per_run=3, max_packages_per_run=1)
    before_attempts = _amazon_attempt_count()

    response = client.post("/api/workflows/autopilot/scheduler/tick")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "COMPLETED"
    assert len(body["createdDraftIds"]) == 1
    assert "No Amazon interaction occurred" in body["message"]
    assert _amazon_attempt_count() == before_attempts

    run = client.get(f"/api/runs/{body['runId']}").json()
    assert run["mode"] == "scheduled_autopilot"
    assert run["generatedDraftCount"] == 1
    assert any(
        "Amazon Draft Assist is not available" in log["message"]
        for log in run["logs"]
    )

    draft = client.get(f"/api/drafts/{body['createdDraftIds'][0]}").json()
    assert draft["status"] == "READY_FOR_AMAZON_DRAFT"
    assert draft["amazon_draft"]["saved"] is False


def test_scheduler_stop_switch_skips_local_jobs() -> None:
    _set_operations(stop_switch_engaged=True)
    before_packages = _scheduled_package_count_today()

    response = client.post("/api/workflows/autopilot/scheduler/tick")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "SKIPPED"
    assert "stop switch engaged" in body["message"]
    assert body["createdDraftIds"] == []
    assert _scheduled_package_count_today() == before_packages


def test_scheduler_respects_daily_package_limit() -> None:
    current_count = _scheduled_package_count_today()
    _set_operations(max_packages_per_day=current_count)

    response = client.post("/api/workflows/autopilot/scheduler/tick")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "SKIPPED"
    assert "daily package limit reached" in body["message"]
    assert body["createdDraftIds"] == []


def test_scheduler_respects_disk_usage_limit() -> None:
    _set_operations(disk_usage_limit_mb=0)

    response = client.post("/api/workflows/autopilot/scheduler/tick")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "SKIPPED"
    assert "disk usage limit exceeded" in body["message"]
    assert body["createdDraftIds"] == []


def test_scheduler_cooldown_blocks_immediate_second_run() -> None:
    _set_operations(cooldown_minutes=0, max_packages_per_day=100)
    first = client.post("/api/workflows/autopilot/scheduler/tick").json()
    assert first["status"] == "COMPLETED"

    _set_operations(cooldown_minutes=1440, max_packages_per_day=100)
    second = client.post("/api/workflows/autopilot/scheduler/tick")

    assert second.status_code == 200
    body = second.json()
    assert body["status"] == "SKIPPED"
    assert "cooldown active" in body["message"]
    assert body["createdDraftIds"] == []
