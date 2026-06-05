from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from app.core.paths import DATA_DIR, REPO_ROOT
from app.services.local_package_workflow.candidates import NicheCandidate, normalize_niche


REQUIRED_SIGNALS = ("demand", "trend", "competition", "saturation")


class ResearchUnavailableError(RuntimeError):
    pass


@dataclass(frozen=True)
class ResearchAdapterResult:
    adapter_id: str
    signal_type: str
    source_url: str
    raw: dict[str, Any]
    value: int
    confidence: float

    def to_payload(self) -> dict[str, Any]:
        return {
            "adapter_id": self.adapter_id,
            "signal_type": self.signal_type,
            "source_url": self.source_url,
            "raw": self.raw,
            "value": self.value,
            "confidence": self.confidence,
        }


@dataclass(frozen=True)
class ResearchSnapshot:
    snapshot_id: str
    candidate_id: str
    niche: str
    status: str
    collected_at: str
    mode: str
    source: str
    signals: dict[str, dict[str, Any]]
    adapter_results: list[dict[str, Any]]
    failures: list[str]

    @property
    def complete(self) -> bool:
        return self.status == "complete" and all(signal in self.signals for signal in REQUIRED_SIGNALS)

    def to_payload(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "candidate_id": self.candidate_id,
            "niche": self.niche,
            "status": self.status,
            "collected_at": self.collected_at,
            "mode": self.mode,
            "source": self.source,
            "signals": self.signals,
            "adapter_results": self.adapter_results,
            "failures": self.failures,
        }


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _signal_value(value: float) -> int:
    return max(0, min(100, round(value)))


def _snapshot_id(candidate: NicheCandidate, mode: str, run_id: str | None) -> str:
    seed = f"{candidate.candidate_id}|{normalize_niche(candidate.niche)}|{mode}|{run_id or 'manual'}"
    return hashlib.sha1(seed.encode("utf-8")).hexdigest()[:16]


def _snapshot_path(run_id: str, snapshot_id: str) -> Path:
    return DATA_DIR / "research_snapshots" / run_id / f"{snapshot_id}.json"


def _write_snapshot(run_id: str, snapshot: ResearchSnapshot) -> str:
    path = _snapshot_path(run_id, snapshot.snapshot_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snapshot.to_payload(), indent=2, sort_keys=True), encoding="utf-8")
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def load_research_snapshot(path: Path) -> ResearchSnapshot:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return ResearchSnapshot(
        snapshot_id=str(payload["snapshot_id"]),
        candidate_id=str(payload["candidate_id"]),
        niche=str(payload["niche"]),
        status=str(payload["status"]),
        collected_at=str(payload["collected_at"]),
        mode=str(payload["mode"]),
        source=str(payload["source"]),
        signals=dict(payload.get("signals", {})),
        adapter_results=list(payload.get("adapter_results", [])),
        failures=list(payload.get("failures", [])),
    )


def _fixture_snapshot_path(candidate: NicheCandidate, research_config: dict[str, Any]) -> Path | None:
    fixture_config = research_config.get("fixture_snapshots", {})
    base_dir = fixture_config.get("directory")
    if not base_dir:
        return None
    path = Path(str(base_dir))
    if not path.is_absolute():
        path = REPO_ROOT / path
    direct_path = path / f"{candidate.candidate_id}.json"
    if direct_path.is_file():
        return direct_path
    normalized_path = path / f"{normalize_niche(candidate.niche).replace(' ', '_')}.json"
    if normalized_path.is_file():
        return normalized_path
    return None


def load_fixture_research_snapshot(
    candidate: NicheCandidate,
    candidate_config: dict[str, Any],
) -> ResearchSnapshot:
    research_config = candidate_config.get("candidate_research", candidate_config).get(
        "research_evidence", {}
    )
    path = _fixture_snapshot_path(candidate, research_config)
    if path is None:
        raise ResearchUnavailableError(f"No fixture research snapshot for {candidate.candidate_id}.")
    snapshot = load_research_snapshot(path)
    if not snapshot.complete:
        raise ResearchUnavailableError(
            f"Fixture research snapshot for {candidate.candidate_id} is incomplete."
        )
    return snapshot


class DuckDuckGoInstantAnswerAdapter:
    adapter_id = "duckduckgo_instant_answer"
    source_url = "https://api.duckduckgo.com/"

    def collect(self, candidate: NicheCandidate, timeout_seconds: float) -> list[ResearchAdapterResult]:
        response = httpx.get(
            self.source_url,
            params={
                "q": candidate.niche,
                "format": "json",
                "no_html": "1",
                "skip_disambig": "1",
            },
            timeout=timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        related_topics = payload.get("RelatedTopics") or []
        abstract = str(payload.get("AbstractText") or "")
        heading = str(payload.get("Heading") or "")
        topic_count = len(related_topics)
        text_strength = len(abstract) + len(heading)
        demand = _signal_value(min(100, 35 + topic_count * 7 + min(text_strength, 300) / 10))
        competition = _signal_value(min(100, 20 + topic_count * 8))
        raw = {
            "heading_present": bool(heading),
            "abstract_chars": len(abstract),
            "related_topic_count": topic_count,
        }
        return [
            ResearchAdapterResult(
                adapter_id=self.adapter_id,
                signal_type="demand",
                source_url=self.source_url,
                raw=raw,
                value=demand,
                confidence=0.55,
            ),
            ResearchAdapterResult(
                adapter_id=self.adapter_id,
                signal_type="competition",
                source_url=self.source_url,
                raw=raw,
                value=competition,
                confidence=0.45,
            ),
        ]


class DuckDuckGoHtmlSaturationAdapter:
    adapter_id = "duckduckgo_html_saturation"
    source_url = "https://html.duckduckgo.com/html/"

    def collect(self, candidate: NicheCandidate, timeout_seconds: float) -> list[ResearchAdapterResult]:
        response = httpx.get(
            self.source_url,
            params={"q": f"{candidate.niche} gift design"},
            headers={"User-Agent": "MerchAgentResearch/0.1"},
            timeout=timeout_seconds,
            follow_redirects=True,
        )
        response.raise_for_status()
        html = response.text
        result_mentions = len(re.findall(r"result__", html))
        shopping_mentions = len(re.findall(r"shirt|tee|hoodie|etsy|redbubble|zazzle", html, re.I))
        saturation = _signal_value(min(100, result_mentions * 3 + shopping_mentions * 5))
        raw = {
            "result_marker_count": result_mentions,
            "marketplace_term_count": shopping_mentions,
        }
        return [
            ResearchAdapterResult(
                adapter_id=self.adapter_id,
                signal_type="saturation",
                source_url=self.source_url,
                raw=raw,
                value=saturation,
                confidence=0.5,
            )
        ]


class DuckDuckGoHtmlMarketSignalsAdapter:
    adapter_id = "duckduckgo_html_market_signals"
    source_url = "https://html.duckduckgo.com/html/"

    def collect(self, candidate: NicheCandidate, timeout_seconds: float) -> list[ResearchAdapterResult]:
        response = httpx.get(
            self.source_url,
            params={"q": f"{candidate.niche} gift idea merch design"},
            headers={"User-Agent": "MerchAgentResearch/0.1"},
            timeout=timeout_seconds,
            follow_redirects=True,
        )
        response.raise_for_status()
        html = response.text
        text = html.lower()
        current_year = datetime.now(UTC).year
        previous_year = current_year - 1
        terms = [normalize_niche(term) for term in [candidate.niche, *candidate.keywords]]
        tokens = {token for term in terms for token in term.split() if len(token) > 3}
        result_mentions = len(re.findall(r"result__", html))
        shopping_mentions = len(re.findall(r"shirt|tee|hoodie|etsy|redbubble|zazzle|amazon|gift", html, re.I))
        token_overlap = sum(1 for token in tokens if token in text)
        freshness_mentions = len(
            re.findall(
                rf"{current_year}|{previous_year}|new|trending|popular|best seller|gift guide",
                text,
            )
        )
        raw = {
            "result_marker_count": result_mentions,
            "marketplace_term_count": shopping_mentions,
            "candidate_token_count": len(tokens),
            "candidate_token_overlap": token_overlap,
            "freshness_marker_count": freshness_mentions,
        }
        demand = _signal_value(38 + result_mentions * 4 + token_overlap * 5)
        competition = _signal_value(24 + shopping_mentions * 4 + result_mentions * 2)
        saturation = _signal_value(18 + shopping_mentions * 5 + result_mentions * 2)
        trend = _signal_value(42 + freshness_mentions * 4 + token_overlap * 3)
        return [
            ResearchAdapterResult(
                adapter_id=self.adapter_id,
                signal_type="demand",
                source_url=self.source_url,
                raw=raw,
                value=demand,
                confidence=0.48,
            ),
            ResearchAdapterResult(
                adapter_id=self.adapter_id,
                signal_type="competition",
                source_url=self.source_url,
                raw=raw,
                value=competition,
                confidence=0.45,
            ),
            ResearchAdapterResult(
                adapter_id=self.adapter_id,
                signal_type="saturation",
                source_url=self.source_url,
                raw=raw,
                value=saturation,
                confidence=0.45,
            ),
            ResearchAdapterResult(
                adapter_id=self.adapter_id,
                signal_type="trend",
                source_url=self.source_url,
                raw=raw,
                value=trend,
                confidence=0.38,
            ),
        ]


class GoogleTrendsDailyRssAdapter:
    adapter_id = "google_trends_daily_rss"
    source_url = "https://trends.google.com/trending/rss"

    def collect(self, candidate: NicheCandidate, timeout_seconds: float) -> list[ResearchAdapterResult]:
        response = httpx.get(
            self.source_url,
            params={"geo": "US"},
            headers={"User-Agent": "MerchAgentResearch/0.1"},
            timeout=timeout_seconds,
            follow_redirects=True,
        )
        response.raise_for_status()
        text = response.text.lower()
        terms = [normalize_niche(term) for term in [candidate.niche, *candidate.keywords]]
        tokens = {token for term in terms for token in term.split() if len(token) > 3}
        overlap = sum(1 for token in tokens if token in text)
        trend = _signal_value(45 + overlap * 12)
        raw = {
            "candidate_token_count": len(tokens),
            "trend_feed_overlap": overlap,
        }
        return [
            ResearchAdapterResult(
                adapter_id=self.adapter_id,
                signal_type="trend",
                source_url=self.source_url,
                raw=raw,
                value=trend,
                confidence=0.4,
            )
        ]


LIVE_ADAPTERS = {
    DuckDuckGoInstantAnswerAdapter.adapter_id: DuckDuckGoInstantAnswerAdapter,
    DuckDuckGoHtmlMarketSignalsAdapter.adapter_id: DuckDuckGoHtmlMarketSignalsAdapter,
    DuckDuckGoHtmlSaturationAdapter.adapter_id: DuckDuckGoHtmlSaturationAdapter,
    GoogleTrendsDailyRssAdapter.adapter_id: GoogleTrendsDailyRssAdapter,
}


def _enabled_live_adapters(research_config: dict[str, Any]) -> list[Any]:
    live_config = research_config.get("live_adapters", {})
    if not live_config.get("enabled", False):
        return []
    adapters = []
    for adapter_config in live_config.get("adapters", []):
        if not adapter_config.get("enabled", False):
            continue
        adapter_id = str(adapter_config.get("adapter_id", ""))
        adapter_class = LIVE_ADAPTERS.get(adapter_id)
        if adapter_class is not None:
            adapters.append(adapter_class())
    return adapters


def _merge_signals(results: list[ResearchAdapterResult]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[ResearchAdapterResult]] = {}
    for result in results:
        grouped.setdefault(result.signal_type, []).append(result)

    merged: dict[str, dict[str, Any]] = {}
    for signal_type, signal_results in grouped.items():
        total_confidence = sum(max(result.confidence, 0.01) for result in signal_results)
        weighted_value = sum(
            result.value * max(result.confidence, 0.01) for result in signal_results
        ) / total_confidence
        merged[signal_type] = {
            "value": _signal_value(weighted_value),
            "confidence": round(min(1.0, total_confidence / len(signal_results)), 2),
            "adapters": [result.adapter_id for result in signal_results],
        }
    return merged


def collect_live_research_snapshot(
    candidate: NicheCandidate,
    candidate_config: dict[str, Any],
    *,
    run_id: str,
) -> tuple[ResearchSnapshot, str]:
    research_config = candidate_config.get("candidate_research", candidate_config).get(
        "research_evidence", {}
    )
    adapters = _enabled_live_adapters(research_config)
    if not adapters:
        raise ResearchUnavailableError(
            "Production research is required, but no live research adapters are enabled."
        )

    timeout_seconds = float(research_config.get("live_adapters", {}).get("timeout_seconds", 8))
    results: list[ResearchAdapterResult] = []
    failures: list[str] = []
    for adapter in adapters:
        try:
            results.extend(adapter.collect(candidate, timeout_seconds))
        except Exception as exc:  # noqa: BLE001 - adapter failures must be captured in snapshots.
            failures.append(f"{adapter.adapter_id}: {exc}")

    signals = _merge_signals(results)
    missing = [signal for signal in REQUIRED_SIGNALS if signal not in signals]
    if missing:
        failures.append(f"Missing required research signals: {', '.join(missing)}")

    snapshot = ResearchSnapshot(
        snapshot_id=_snapshot_id(candidate, "live", run_id),
        candidate_id=candidate.candidate_id,
        niche=candidate.niche,
        status="complete" if not missing and results else "failed",
        collected_at=_now_iso(),
        mode="live",
        source="live_adapters",
        signals=signals,
        adapter_results=[result.to_payload() for result in results],
        failures=failures,
    )
    snapshot_path = _write_snapshot(run_id, snapshot)
    if not snapshot.complete:
        raise ResearchUnavailableError(
            f"Research snapshot incomplete for {candidate.candidate_id}: {'; '.join(failures)}"
        )
    snapshot_file = Path(snapshot_path)
    if not snapshot_file.is_absolute():
        snapshot_file = REPO_ROOT / snapshot_file
    return load_research_snapshot(snapshot_file), snapshot_path


def persist_fixture_research_snapshot(
    snapshot: ResearchSnapshot,
    *,
    run_id: str,
) -> tuple[ResearchSnapshot, str]:
    path = _write_snapshot(run_id, snapshot)
    snapshot_file = Path(path)
    if not snapshot_file.is_absolute():
        snapshot_file = REPO_ROOT / snapshot_file
    return load_research_snapshot(snapshot_file), path
