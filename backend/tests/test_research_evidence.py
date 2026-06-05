from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.paths import DATA_DIR
from app.main import app
from app.services.config_service import get_config
from app.services.local_package_workflow.candidates import LOCAL_FIXTURE_CANDIDATES
from app.services.local_package_workflow.research import (
    LIVE_ADAPTERS,
    REQUIRED_SIGNALS,
    load_fixture_research_snapshot,
    persist_fixture_research_snapshot,
)
from app.services.local_package_workflow.scoring import score_candidate_from_research_snapshot


client = TestClient(app)


def test_research_fixture_snapshot_scores_all_required_signals() -> None:
    candidate = LOCAL_FIXTURE_CANDIDATES[0]
    config = get_config()
    snapshot = load_fixture_research_snapshot(candidate, config.candidate_sources)

    assert snapshot.complete is True
    assert set(REQUIRED_SIGNALS).issubset(snapshot.signals)

    score = score_candidate_from_research_snapshot(candidate, snapshot.to_payload())

    assert score["demand"] == 84
    assert score["trend"] == 76
    assert score["competition"] == 46
    assert score["saturation"] == 42
    assert score["overall"] > 70


def test_fixture_research_snapshot_can_be_persisted_before_scoring() -> None:
    candidate = LOCAL_FIXTURE_CANDIDATES[0]
    config = get_config()
    snapshot = load_fixture_research_snapshot(candidate, config.candidate_sources)

    persisted, relative_path = persist_fixture_research_snapshot(
        snapshot,
        run_id="run_test_research_fixture",
    )

    path = DATA_DIR.parent / relative_path
    assert path.is_file()
    payload = json.loads(path.read_text())
    assert payload["snapshot_id"] == "fixture_cand_fishing_grandpa"
    assert persisted.complete is True


def test_live_adapter_registry_covers_required_research_signals() -> None:
    adapter_ids = set(LIVE_ADAPTERS)

    assert {
        "duckduckgo_instant_answer",
        "duckduckgo_html_saturation",
        "google_trends_daily_rss",
    }.issubset(adapter_ids)


def test_production_autopilot_fails_without_research_evidence() -> None:
    response = client.post(
        "/api/workflows/autopilot/run",
        json={
            "count": 1,
            "default_product": "standard_tshirt",
            "explore_marketplaces": True,
            "touch_amazon": False,
            "production_mode": True,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "FAILED"
    assert body["createdDraftIds"] == []
    assert "production research evidence was unavailable" in body["message"]

    detail_response = client.get(f"/api/runs/{body['runId']}")
    assert detail_response.status_code == 200
    logs = [entry["message"] for entry in detail_response.json()["logs"]]
    assert any("Production mode enabled" in message for message in logs)
    assert any("Research unavailable" in message for message in logs)

    snapshot_root = DATA_DIR / "research_snapshots" / body["runId"]
    assert not any(Path(snapshot_root).glob("*.json"))
