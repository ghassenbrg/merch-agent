from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.paths import DATA_DIR
from app.main import app
from app.services.config_service import get_config
from app.services.local_package_workflow.candidates import LOCAL_FIXTURE_CANDIDATES
from app.services import autopilot_service
from app.services.local_package_workflow import research as research_module
from app.services.local_package_workflow.research import (
    LIVE_ADAPTERS,
    REQUIRED_SIGNALS,
    ResearchAdapterResult,
    ResearchUnavailableError,
    load_fixture_research_snapshot,
    collect_live_research_snapshot,
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
        "duckduckgo_html_market_signals",
        "duckduckgo_instant_answer",
        "duckduckgo_html_saturation",
        "google_trends_daily_rss",
    }.issubset(adapter_ids)


def test_live_research_snapshot_can_be_collected_with_enabled_adapters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class UnitLiveAdapter:
        adapter_id = "unit_live_adapter"
        source_url = "https://example.test/research"

        def collect(self, candidate, timeout_seconds: float) -> list[ResearchAdapterResult]:
            return [
                ResearchAdapterResult(self.adapter_id, "demand", self.source_url, {"timeout": timeout_seconds}, 81, 0.8),
                ResearchAdapterResult(self.adapter_id, "trend", self.source_url, {"timeout": timeout_seconds}, 74, 0.7),
                ResearchAdapterResult(self.adapter_id, "competition", self.source_url, {"timeout": timeout_seconds}, 44, 0.7),
                ResearchAdapterResult(self.adapter_id, "saturation", self.source_url, {"timeout": timeout_seconds}, 38, 0.7),
            ]

    monkeypatch.setitem(research_module.LIVE_ADAPTERS, UnitLiveAdapter.adapter_id, UnitLiveAdapter)
    candidate = LOCAL_FIXTURE_CANDIDATES[0]
    candidate_config = {
        "candidate_research": {
            "research_evidence": {
                "live_adapters": {
                    "enabled": True,
                    "timeout_seconds": 3,
                    "adapters": [
                        {
                            "adapter_id": UnitLiveAdapter.adapter_id,
                            "enabled": True,
                            "signals": list(REQUIRED_SIGNALS),
                        }
                    ],
                }
            }
        }
    }

    snapshot, relative_path = collect_live_research_snapshot(
        candidate,
        candidate_config,
        run_id="run_unit_live_research",
    )

    assert snapshot.complete is True
    assert snapshot.source == "live_adapters"
    assert set(REQUIRED_SIGNALS).issubset(snapshot.signals)
    assert (DATA_DIR.parent / relative_path).is_file()


def test_production_autopilot_creates_package_from_mocked_live_research(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class UnitLiveAdapter:
        source_url = "https://example.test/research"

        def collect(self, candidate, timeout_seconds: float) -> list[ResearchAdapterResult]:
            return [
                ResearchAdapterResult(self.adapter_id, "demand", self.source_url, {}, 82, 0.8),
                ResearchAdapterResult(self.adapter_id, "trend", self.source_url, {}, 76, 0.7),
                ResearchAdapterResult(self.adapter_id, "competition", self.source_url, {}, 46, 0.7),
                ResearchAdapterResult(self.adapter_id, "saturation", self.source_url, {}, 42, 0.7),
            ]

    for adapter_id in list(research_module.LIVE_ADAPTERS):
        adapter_class = type(
            f"Unit{adapter_id.title().replace('_', '')}Adapter",
            (UnitLiveAdapter,),
            {"adapter_id": adapter_id},
        )
        monkeypatch.setitem(research_module.LIVE_ADAPTERS, adapter_id, adapter_class)

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
    assert body["status"] == "COMPLETED"
    assert len(body["createdDraftIds"]) == 1

    draft_response = client.get(f"/api/drafts/{body['createdDraftIds'][0]}")
    assert draft_response.status_code == 200
    draft = draft_response.json()
    assert draft["research"]["external_research_used"] is True
    assert draft["research"]["score_source"] == "live_research_snapshot"
    assert draft["research"]["snapshot"]["source"] == "live_adapters"
    assert set(REQUIRED_SIGNALS).issubset(draft["research"]["snapshot"]["signals"])


def test_production_autopilot_fails_without_research_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unavailable(*args, **kwargs):
        raise ResearchUnavailableError("unit live research unavailable")

    monkeypatch.setattr(autopilot_service, "collect_live_research_snapshot", unavailable)
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
