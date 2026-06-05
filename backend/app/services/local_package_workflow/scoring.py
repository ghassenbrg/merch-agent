from __future__ import annotations

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

