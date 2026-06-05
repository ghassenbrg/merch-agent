from __future__ import annotations

from dataclasses import dataclass
import hashlib
from itertools import cycle
import random
import re
from typing import Any
from typing import Iterator


@dataclass(frozen=True)
class NicheCandidate:
    candidate_id: str
    niche: str
    audience: str
    keywords: list[str]
    demand_signal: int
    trend_signal: int
    saturation_signal: int
    compliance_signal: int
    design_angle: str
    listing_angle: str
    risk_terms: list[str]
    source_id: str = "local_fixture_candidates"
    source_type: str = "fixture"
    search_phrase: str = "fixture candidate"
    generator_seed: str | None = None

    def score_inputs(self) -> dict[str, int]:
        return {
            "demand_signal": self.demand_signal,
            "trend_signal": self.trend_signal,
            "saturation_signal": self.saturation_signal,
            "compliance_signal": self.compliance_signal,
        }

    def source_payload(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "source_id": self.source_id,
            "source_type": self.source_type,
            "search_phrase": self.search_phrase,
            "generator_seed": self.generator_seed,
            "score_inputs": self.score_inputs(),
        }


@dataclass(frozen=True)
class CandidateAuditRecord:
    candidate_id: str
    niche: str
    normalized_niche: str
    source_id: str
    source_type: str
    search_phrase: str
    score_inputs: dict[str, int]
    decision: str
    reasons: list[str]

    def to_payload(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "niche": self.niche,
            "normalized_niche": self.normalized_niche,
            "source_id": self.source_id,
            "source_type": self.source_type,
            "search_phrase": self.search_phrase,
            "score_inputs": self.score_inputs,
            "decision": self.decision,
            "reasons": self.reasons,
        }


@dataclass(frozen=True)
class CandidateDiscoveryResult:
    candidates: list[NicheCandidate]
    audit_records: list[CandidateAuditRecord]
    external_research_enabled: bool

    def audit_payload(self) -> list[dict[str, Any]]:
        return [record.to_payload() for record in self.audit_records]


LOCAL_FIXTURE_CANDIDATES = [
    NicheCandidate(
        candidate_id="cand_fishing_grandpa",
        niche="Fly fishing grandpas",
        audience="Older anglers and family gift buyers",
        keywords=["fly fishing", "grandpa gift", "river weekend", "outdoors"],
        demand_signal=82,
        trend_signal=74,
        saturation_signal=68,
        compliance_signal=96,
        design_angle="Vintage river badge with fly rod linework and calm outdoor typography",
        listing_angle="relaxed fishing-themed gift for grandpas and families",
        risk_terms=[],
    ),
    NicheCandidate(
        candidate_id="cand_garden_book_club",
        niche="Garden book club weekends",
        audience="Readers, gardeners, and cozy weekend gift shoppers",
        keywords=["garden reader", "book club", "weekend garden", "plant lover"],
        demand_signal=76,
        trend_signal=72,
        saturation_signal=62,
        compliance_signal=98,
        design_angle="Botanical book stack with small leaves, serif lettering, and soft ink texture",
        listing_angle="quiet reading and gardening design for weekend downtime",
        risk_terms=[],
    ),
    NicheCandidate(
        candidate_id="cand_chess_coach",
        niche="Chess coach endgame humor",
        audience="Chess coaches, club players, and tournament families",
        keywords=["chess coach", "endgame", "club player", "strategy gift"],
        demand_signal=71,
        trend_signal=70,
        saturation_signal=58,
        compliance_signal=95,
        design_angle="Minimal chessboard corner with king marker and clean coaching phrase",
        listing_angle="strategy game design for coaches, clubs, and patient problem solvers",
        risk_terms=[],
    ),
    NicheCandidate(
        candidate_id="cand_blocked_brand_trip",
        niche="Disney family vacation countdown",
        audience="Theme park travelers",
        keywords=["disney", "vacation", "countdown"],
        demand_signal=88,
        trend_signal=84,
        saturation_signal=42,
        compliance_signal=22,
        design_angle="Theme park vacation phrase",
        listing_angle="brand-connected travel design",
        risk_terms=["disney"],
    ),
]


def iter_fixture_candidates() -> Iterator[NicheCandidate]:
    yield from LOCAL_FIXTURE_CANDIDATES


def cycle_fixture_candidates() -> Iterator[NicheCandidate]:
    yield from cycle(LOCAL_FIXTURE_CANDIDATES)


def normalize_niche(value: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", value.lower()).split())


def _candidate_text(candidate: NicheCandidate) -> str:
    return " ".join(
        [
            candidate.niche,
            candidate.audience,
            candidate.design_angle,
            candidate.listing_angle,
            " ".join(candidate.keywords),
            " ".join(candidate.risk_terms),
        ]
    ).lower()


def _term_hits(candidate: NicheCandidate, terms: list[str]) -> list[str]:
    text = _candidate_text(candidate)
    return sorted(term for term in terms if term.lower() in text)


def _audit_record(
    candidate: NicheCandidate,
    decision: str,
    reasons: list[str],
) -> CandidateAuditRecord:
    return CandidateAuditRecord(
        candidate_id=candidate.candidate_id,
        niche=candidate.niche,
        normalized_niche=normalize_niche(candidate.niche),
        source_id=candidate.source_id,
        source_type=candidate.source_type,
        search_phrase=candidate.search_phrase,
        score_inputs=candidate.score_inputs(),
        decision=decision,
        reasons=reasons,
    )


def _candidate_from_payload(
    payload: dict[str, Any],
    *,
    source_id: str,
    source_type: str,
    search_phrase: str,
) -> NicheCandidate:
    return NicheCandidate(
        candidate_id=str(payload["candidate_id"]),
        niche=str(payload["niche"]),
        audience=str(payload["audience"]),
        keywords=[str(keyword) for keyword in payload.get("keywords", [])],
        demand_signal=int(payload.get("demand_signal", 0)),
        trend_signal=int(payload.get("trend_signal", 0)),
        saturation_signal=int(payload.get("saturation_signal", 100)),
        compliance_signal=int(payload.get("compliance_signal", 0)),
        design_angle=str(payload["design_angle"]),
        listing_angle=str(payload["listing_angle"]),
        risk_terms=[str(term) for term in payload.get("risk_terms", [])],
        source_id=source_id,
        source_type=source_type,
        search_phrase=search_phrase,
    )


def _local_source_candidates(candidate_config: dict[str, Any]) -> list[NicheCandidate]:
    research_config = candidate_config.get("candidate_research", candidate_config)
    candidates: list[NicheCandidate] = []
    for source in research_config.get("local_sources", []):
        source_id = str(source.get("source_id", "local_source"))
        source_type = str(source.get("source_type", "local_yaml"))
        search_phrase = str(source.get("search_phrase", "local candidate source"))
        candidates.extend(
            _candidate_from_payload(
                payload,
                source_id=source_id,
                source_type=source_type,
                search_phrase=search_phrase,
            )
            for payload in source.get("candidates", [])
        )
    return candidates


def _stable_candidate_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()[:10]
    return f"{prefix}_{digest}"


def _clamp_signal(value: int) -> int:
    return max(0, min(100, value))


def _seeded_candidates(
    candidate_config: dict[str, Any],
    seed_override: str | None = None,
) -> list[NicheCandidate]:
    research_config = candidate_config.get("candidate_research", candidate_config)
    candidates: list[NicheCandidate] = []
    for generator in research_config.get("seeded_generators", []):
        if not generator.get("enabled", True):
            continue

        generator_id = str(generator.get("generator_id", "local_seed_generator"))
        generator_seed = str(seed_override or generator.get("seed", "merch-agent-local"))
        source_type = str(generator.get("source_type", "seed_generator"))
        search_phrase = str(generator.get("search_phrase", "local seed generator"))
        max_candidates = int(generator.get("max_candidates", 12))
        base_signals = generator.get("base_signals", {})
        combinations = [
            (activity, audience, context)
            for activity in generator.get("activities", [])
            for audience in generator.get("audiences", [])
            for context in generator.get("contexts", [])
        ]
        rng = random.Random(generator_seed)
        rng.shuffle(combinations)

        for activity, audience, context in combinations[:max_candidates]:
            jitter = {
                "demand_signal": rng.randint(-4, 6),
                "trend_signal": rng.randint(-3, 5),
                "saturation_signal": rng.randint(-5, 5),
                "compliance_signal": rng.randint(-2, 2),
            }
            niche = f"{str(activity).title()} {str(audience)} {context}"
            candidates.append(
                NicheCandidate(
                    candidate_id=_stable_candidate_id(
                        "gen",
                        generator_id,
                        generator_seed,
                        normalize_niche(niche),
                    ),
                    niche=niche,
                    audience=f"{str(audience).title()}, hobby fans, and local gift shoppers",
                    keywords=[
                        str(activity),
                        str(audience),
                        str(context),
                        "weekend hobby",
                    ],
                    demand_signal=_clamp_signal(
                        int(base_signals.get("demand_signal", 70))
                        + jitter["demand_signal"]
                    ),
                    trend_signal=_clamp_signal(
                        int(base_signals.get("trend_signal", 68))
                        + jitter["trend_signal"]
                    ),
                    saturation_signal=_clamp_signal(
                        int(base_signals.get("saturation_signal", 60))
                        + jitter["saturation_signal"]
                    ),
                    compliance_signal=_clamp_signal(
                        int(base_signals.get("compliance_signal", 95))
                        + jitter["compliance_signal"]
                    ),
                    design_angle=(
                        f"Original {activity} motif with simple linework and calm weekend typography"
                    ),
                    listing_angle=(
                        f"{activity} design for {audience} who enjoy a {context}"
                    ),
                    risk_terms=[],
                    source_id=generator_id,
                    source_type=source_type,
                    search_phrase=search_phrase,
                    generator_seed=generator_seed,
                )
            )
    return candidates


def _external_adapter_candidates(
    candidate_config: dict[str, Any],
) -> tuple[list[NicheCandidate], bool, list[CandidateAuditRecord]]:
    research_config = candidate_config.get("candidate_research", candidate_config)
    external_config = research_config.get("external_research", {})
    enabled = bool(external_config.get("enabled", False))
    audit_records: list[CandidateAuditRecord] = []
    if not enabled:
        return [], False, audit_records

    for adapter in external_config.get("adapters", []):
        if not adapter.get("enabled", False):
            continue
        adapter_id = str(adapter.get("adapter_id", "external_stub"))
        stub_candidate = NicheCandidate(
            candidate_id=f"{adapter_id}_stub",
            niche="External research adapter stub",
            audience="Not used by default",
            keywords=[],
            demand_signal=0,
            trend_signal=0,
            saturation_signal=100,
            compliance_signal=0,
            design_angle="No network call performed.",
            listing_angle="No external candidates returned.",
            risk_terms=[],
            source_id=adapter_id,
            source_type="external_stub",
            search_phrase="external research disabled in tests",
        )
        audit_records.append(
            _audit_record(
                stub_candidate,
                "skipped",
                ["External adapter stub is configured but does not perform network research."],
            )
        )
    return [], True, audit_records


def discover_candidates(
    candidate_config: dict[str, Any],
    *,
    requested_count: int,
    seed: str | None = None,
    cooldown_niches: list[str] | None = None,
) -> CandidateDiscoveryResult:
    research_config = candidate_config.get("candidate_research", candidate_config)
    prechecks = research_config.get("prechecks", {})
    duplicate_detection = research_config.get("duplicate_detection", {}).get("enabled", True)
    cooldown_config = research_config.get("cooldowns", {})
    configured_cooldowns = cooldown_config.get("normalized_niches", [])
    active_cooldowns = {
        normalize_niche(niche)
        for niche in [*(cooldown_niches or []), *configured_cooldowns]
        if niche
    }
    min_compliance_signal = int(prechecks.get("min_compliance_signal", 70))
    blocked_terms = [str(term).lower() for term in prechecks.get("blocked_terms", [])]
    trademark_terms = [str(term).lower() for term in prechecks.get("trademark_terms", [])]

    raw_candidates = [
        *_local_source_candidates(candidate_config),
        *_seeded_candidates(candidate_config, seed_override=seed),
    ]
    external_candidates, external_enabled, external_audit = _external_adapter_candidates(
        candidate_config
    )
    raw_candidates.extend(external_candidates)

    accepted: list[NicheCandidate] = []
    audit_records: list[CandidateAuditRecord] = [*external_audit]
    seen_niches: set[str] = set()
    seen_keyword_signatures: set[tuple[str, ...]] = set()

    for candidate in raw_candidates:
        reasons: list[str] = []
        normalized_niche = normalize_niche(candidate.niche)
        keyword_signature = tuple(sorted(normalize_niche(keyword) for keyword in candidate.keywords))

        if normalized_niche in active_cooldowns and cooldown_config.get("enabled", True):
            reasons.append(f"Niche cooldown active: {candidate.niche}")

        if duplicate_detection and normalized_niche in seen_niches:
            reasons.append(f"Duplicate niche detected: {candidate.niche}")

        if duplicate_detection and keyword_signature and keyword_signature in seen_keyword_signatures:
            reasons.append("Duplicate keyword signature detected.")

        blocked = _term_hits(candidate, blocked_terms)
        if blocked:
            reasons.extend(f"Precheck blocked high-risk term: {term}" for term in blocked)

        trademark = _term_hits(candidate, trademark_terms)
        if trademark:
            reasons.extend(f"Trademark precheck blocked term: {term}" for term in trademark)

        if candidate.compliance_signal < min_compliance_signal:
            reasons.append("Compliance signal below conservative precheck threshold.")

        if not reasons and len(accepted) >= requested_count:
            reasons.append("Candidate pool limit reached for this run.")

        if reasons:
            audit_records.append(_audit_record(candidate, "skipped", reasons))
            continue

        seen_niches.add(normalized_niche)
        if keyword_signature:
            seen_keyword_signatures.add(keyword_signature)
        accepted.append(candidate)
        audit_records.append(_audit_record(candidate, "accepted", ["Passed local discovery prechecks."]))

    return CandidateDiscoveryResult(
        candidates=accepted,
        audit_records=audit_records,
        external_research_enabled=external_enabled,
    )
