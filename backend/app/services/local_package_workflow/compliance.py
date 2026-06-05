from __future__ import annotations

from dataclasses import dataclass
import re

from app.services.local_package_workflow.candidates import NicheCandidate


BLOCKED_POLICY_TERMS: dict[str, set[str]] = {
    "brand_or_trademark": {
        "adidas",
        "amazon",
        "apple",
        "barbie",
        "coca cola",
        "disney",
        "harley davidson",
        "lego",
        "marvel",
        "netflix",
        "nike",
        "nintendo",
        "playstation",
        "pokemon",
        "star wars",
        "tesla",
        "xbox",
    },
    "protected_event_or_league": {
        "fifa world cup",
        "kentucky derby",
        "march madness",
        "nba finals",
        "olympics",
        "stanley cup",
        "super bowl",
        "uefa champions league",
        "world cup",
    },
    "public_figure": {
        "biden",
        "donald trump",
        "elon musk",
        "joe biden",
        "taylor swift",
        "trump",
    },
    "copyrighted_character": {
        "batman",
        "darth vader",
        "harry potter",
        "mickey",
        "minnie mouse",
        "snoopy",
        "spider man",
        "spiderman",
        "superman",
        "yoda",
    },
    "medical_claim": {
        "autism cure",
        "cancer cure",
        "cure cancer",
        "cures anxiety",
        "diabetes cure",
        "heals depression",
        "treats diabetes",
    },
    "tragedy_or_disaster": {
        "9/11",
        "covid-19 survivor",
        "hurricane katrina",
        "never forget 9/11",
        "school shooting",
        "titanic disaster",
    },
    "misleading_product_claim": {
        "100% organic",
        "certified organic",
        "made in usa",
        "official merchandise",
        "officially licensed",
    },
}

RISKY_REVIEW_TERMS: dict[str, set[str]] = {
    "ambiguous_brand_reference": {
        "inspired by disney",
        "nike style",
        "pixar inspired",
        "star wars inspired",
        "theme park inspired",
    },
    "ambiguous_event_reference": {
        "big game",
        "championship sunday",
        "game day champs",
        "summer games",
        "world championship",
    },
    "ambiguous_claim": {
        "anti anxiety",
        "doctor approved",
        "healing energy",
        "immune support",
        "therapy vibes",
    },
    "ambiguous_tragedy_or_disaster": {
        "pandemic survivor",
        "storm survivor",
        "wildfire survivor",
    },
}


@dataclass(frozen=True)
class ComplianceResult:
    passed: bool
    reasons: list[str]
    status: str = "pass"
    blocked_terms: list[str] | None = None
    review_terms: list[str] | None = None

    @property
    def blocked(self) -> bool:
        return self.status == "blocked"

    @property
    def human_review_required(self) -> bool:
        return self.status == "human_review_required"


def _term_pattern(term: str) -> re.Pattern[str]:
    normalized = re.escape(term.lower()).replace(r"\ ", r"[\s\-_]+")
    return re.compile(rf"(?<![a-z0-9]){normalized}(?![a-z0-9])")


def _policy_hits(text: str, terms_by_category: dict[str, set[str]]) -> list[str]:
    hits: list[str] = []
    for category, terms in terms_by_category.items():
        for term in sorted(terms):
            if _term_pattern(term).search(text):
                hits.append(f"{category}:{term}")
    return hits


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

    blocked = _policy_hits(checked_text, BLOCKED_POLICY_TERMS)
    if blocked:
        return ComplianceResult(
            passed=False,
            status="blocked",
            blocked_terms=blocked,
            review_terms=[],
            reasons=[f"Blocked policy phrase: {term}" for term in blocked],
        )

    if candidate.compliance_signal < 70:
        return ComplianceResult(
            passed=False,
            status="blocked",
            blocked_terms=[],
            review_terms=[],
            reasons=["Compliance score below local conservative threshold."],
        )

    review = _policy_hits(checked_text, RISKY_REVIEW_TERMS)
    if review:
        return ComplianceResult(
            passed=False,
            status="human_review_required",
            blocked_terms=[],
            review_terms=review,
            reasons=[f"Human review required for ambiguous phrase: {term}" for term in review],
        )

    return ComplianceResult(
        passed=True,
        status="pass",
        blocked_terms=[],
        review_terms=[],
        reasons=[],
    )
