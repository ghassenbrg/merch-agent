from __future__ import annotations

from dataclasses import dataclass

from app.services.local_package_workflow.candidates import NicheCandidate


BLOCKED_TERMS = {
    "adidas",
    "disney",
    "marvel",
    "mickey",
    "nike",
    "olympics",
    "pokemon",
    "star wars",
    "super bowl",
}


@dataclass(frozen=True)
class ComplianceResult:
    passed: bool
    reasons: list[str]


def run_compliance_gate(candidate: NicheCandidate) -> ComplianceResult:
    checked_text = " ".join(
        [
            candidate.niche,
            candidate.audience,
            candidate.design_angle,
            candidate.listing_angle,
            " ".join(candidate.keywords),
            " ".join(candidate.risk_terms),
        ]
    ).lower()

    blocked = sorted(term for term in BLOCKED_TERMS if term in checked_text)
    if blocked:
        return ComplianceResult(
            passed=False,
            reasons=[f"Blocked high-risk term: {term}" for term in blocked],
        )

    if candidate.compliance_signal < 70:
        return ComplianceResult(
            passed=False,
            reasons=["Compliance score below local conservative threshold."],
        )

    return ComplianceResult(passed=True, reasons=[])

