from __future__ import annotations

from typing import Any

from app.services.local_package_workflow.candidates import NicheCandidate


def score_candidate(candidate: NicheCandidate) -> dict[str, float]:
    demand = float(candidate.demand_signal)
    trend = float(candidate.trend_signal)
    saturation = float(100 - candidate.saturation_signal)
    compliance = float(candidate.compliance_signal)
    overall = round(
        (demand * 0.32)
        + (trend * 0.22)
        + (saturation * 0.18)
        + (compliance * 0.28),
        1,
    )

    return {
        "overall": overall,
        "demand": demand,
        "trend": trend,
        "saturation": saturation,
        "compliance": compliance,
    }


def score_candidate_from_research_snapshot(
    candidate: NicheCandidate,
    snapshot_payload: dict[str, Any],
) -> dict[str, float]:
    signals = snapshot_payload.get("signals", {})
    required = ["demand", "trend", "competition", "saturation"]
    missing = [signal for signal in required if signal not in signals]
    if missing:
        raise ValueError(f"Research snapshot missing required signal(s): {', '.join(missing)}")

    demand = float(signals["demand"]["value"])
    trend = float(signals["trend"]["value"])
    competition = float(100 - signals["competition"]["value"])
    saturation = float(100 - signals["saturation"]["value"])
    compliance = float(candidate.compliance_signal)
    overall = round(
        (demand * 0.28)
        + (trend * 0.2)
        + (competition * 0.16)
        + (saturation * 0.14)
        + (compliance * 0.22),
        1,
    )

    return {
        "overall": overall,
        "demand": demand,
        "trend": trend,
        "competition": competition,
        "saturation": saturation,
        "compliance": compliance,
    }
