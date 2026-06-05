from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app.core.paths import DATA_DIR
from app.main import app
from app.services.config_service import get_config
from app.services.local_package_workflow.candidates import discover_candidates


client = TestClient(app)


def _candidate(candidate_id: str, niche: str, **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "candidate_id": candidate_id,
        "niche": niche,
        "audience": "Local hobby gift buyers",
        "keywords": [niche.lower(), "weekend hobby"],
        "demand_signal": 74,
        "trend_signal": 68,
        "saturation_signal": 60,
        "compliance_signal": 95,
        "design_angle": f"Original line-art concept for {niche}",
        "listing_angle": f"low-risk {niche} gift idea",
        "risk_terms": [],
    }
    payload.update(overrides)
    return payload


def test_seeded_candidate_generation_is_deterministic_and_varied() -> None:
    config = get_config()

    first = discover_candidates(
        config.candidate_sources,
        requested_count=8,
        seed="fixed-test-seed",
    )
    second = discover_candidates(
        config.candidate_sources,
        requested_count=8,
        seed="fixed-test-seed",
    )

    assert [candidate.candidate_id for candidate in first.candidates] == [
        candidate.candidate_id for candidate in second.candidates
    ]
    generated = [
        candidate for candidate in first.candidates if candidate.source_type == "seed_generator"
    ]
    assert len(generated) >= 3
    assert len({candidate.niche for candidate in generated}) == len(generated)


def test_discovery_audits_duplicates_cooldowns_and_prechecks() -> None:
    candidate_config = {
        "candidate_research": {
            "local_sources": [
                {
                    "source_id": "unit_test_source",
                    "source_type": "fixture",
                    "search_phrase": "fixture research phrase",
                    "candidates": [
                        _candidate("safe", "Ceramic Garden Mornings"),
                        _candidate("duplicate", "Ceramic Garden Mornings"),
                        _candidate("cooldown", "Retired Kayak Weekend Crew"),
                        _candidate(
                            "blocked",
                            "Disney Fishing Crew",
                            risk_terms=["disney"],
                        ),
                        _candidate("trademark", "Super Bowl Snack Captain"),
                        _candidate("low_compliance", "Generic Hobby", compliance_signal=42),
                    ],
                }
            ],
            "seeded_generators": [],
            "duplicate_detection": {"enabled": True},
            "cooldowns": {
                "enabled": True,
                "normalized_niches": ["retired kayak weekend crew"],
            },
            "prechecks": {
                "min_compliance_signal": 70,
                "blocked_terms": ["disney"],
                "trademark_terms": ["super bowl"],
            },
            "external_research": {"enabled": False, "adapters": []},
        }
    }

    result = discover_candidates(candidate_config, requested_count=10, seed="unit")

    assert [candidate.candidate_id for candidate in result.candidates] == ["safe"]
    audit = {record.candidate_id: record for record in result.audit_records}
    assert audit["safe"].decision == "accepted"
    assert audit["duplicate"].reasons == [
        "Duplicate niche detected: Ceramic Garden Mornings",
        "Duplicate keyword signature detected.",
    ]
    assert audit["cooldown"].reasons == [
        "Niche cooldown active: Retired Kayak Weekend Crew"
    ]
    assert audit["blocked"].reasons == [
        "Precheck blocked high-risk term: disney"
    ]
    assert audit["trademark"].reasons == [
        "Trademark precheck blocked term: super bowl"
    ]
    assert audit["low_compliance"].reasons == [
        "Compliance signal below conservative precheck threshold."
    ]


def test_external_research_is_disabled_by_default() -> None:
    config = get_config()
    result = discover_candidates(config.candidate_sources, requested_count=6, seed="default")

    assert config.candidate_sources["candidate_research"]["external_research"]["enabled"] is False
    assert result.external_research_enabled is False
    assert all(
        not candidate.source_type.startswith("external")
        for candidate in result.candidates
    )


def test_autopilot_persists_candidate_audit_and_research_metadata() -> None:
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
    run_id = body["runId"]
    draft_id = body["createdDraftIds"][0]

    audit_path = DATA_DIR / "logs" / f"{run_id}_candidate_audit.json"
    assert audit_path.is_file()
    audit_payload = json.loads(audit_path.read_text())
    assert any(record["decision"] == "accepted" for record in audit_payload)
    assert any(record["decision"] == "skipped" for record in audit_payload)
    assert all(record["source_id"] for record in audit_payload)
    assert all("score_inputs" in record for record in audit_payload)

    detail_response = client.get(f"/api/runs/{run_id}")
    assert detail_response.status_code == 200
    logs = [entry["message"] for entry in detail_response.json()["logs"]]
    assert any("Candidate discovery audited" in message for message in logs)
    assert any("External research disabled by config" in message for message in logs)

    draft_response = client.get(f"/api/drafts/{draft_id}")
    assert draft_response.status_code == 200
    draft = draft_response.json()
    assert draft["research"]["source_id"]
    assert draft["research"]["external_research_used"] is False
    assert draft["research"]["score_source"] == "candidate_signal_fixture"
    assert draft["research"]["snapshot"] is None
    assert draft["research"]["audit_record"]["decision"] == "accepted"
    assert (DATA_DIR / "drafts" / draft_id / "candidate_research.json").is_file()
