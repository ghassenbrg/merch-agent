from __future__ import annotations

from dataclasses import dataclass
from itertools import cycle
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

