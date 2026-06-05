from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import HTTPException
from PIL import Image

from app.core.paths import DATA_DIR, REPO_ROOT, resolve_runtime_path
from app.db.database import get_connection
from app.db.repositories import insert_draft_event, upsert_draft_projection
from app.models.schemas import AgentPackageRequest, AgentPackageResponse
from app.services.config_service import get_config
from app.services.local_package_workflow.candidates import NicheCandidate
from app.services.local_package_workflow.compliance import run_compliance_gate
from app.services.local_package_workflow.marketplaces import resolve_marketplaces
from app.services.local_package_workflow.package_assembler import assemble_local_package
from app.services.local_package_workflow.product_templates import resolve_product_template
from app.services.local_package_workflow.scoring import score_candidate


def _relative_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path.resolve())


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _write_updated_agent_artifacts(artifact_dir: Path, draft_payload: dict[str, Any]) -> None:
    _write_json(artifact_dir / "draft.json", draft_payload)
    _write_json(artifact_dir / "candidate_research.json", draft_payload.get("research") or {})


def _candidate_from_request(request: AgentPackageRequest) -> NicheCandidate:
    payload = request.candidate
    candidate_id = payload.candidate_id or f"agent_{uuid4().hex[:10]}"
    return NicheCandidate(
        candidate_id=candidate_id,
        niche=payload.niche,
        audience=payload.audience,
        keywords=payload.keywords,
        demand_signal=payload.demand_signal,
        trend_signal=payload.trend_signal,
        saturation_signal=payload.saturation_signal,
        compliance_signal=payload.compliance_signal,
        design_angle=payload.design_angle,
        listing_angle=payload.listing_angle,
        risk_terms=payload.risk_terms,
        source_id="codex_agent",
        source_type="codex_agent",
        search_phrase=str((request.research_trace or {}).get("goal", "codex agent selected candidate")),
    )


def _merge_score(candidate: NicheCandidate, provided: dict[str, float] | None) -> dict[str, float]:
    score = score_candidate(candidate)
    if provided:
        for key, value in provided.items():
            score[str(key)] = float(value)
    if "overall" not in score:
        score["overall"] = round(
            sum(value for key, value in score.items() if key != "overall") / max(1, len(score)),
            1,
        )
    return score


def _import_agent_artwork(
    *,
    artwork_path: str,
    draft_id: str,
    product_width: int,
    product_height: int,
    creative_brief: dict[str, Any] | None,
) -> dict[str, Any]:
    source_artwork = resolve_runtime_path(artwork_path)
    if not source_artwork.is_file():
        raise HTTPException(status_code=400, detail="Agent artwork path does not exist.")

    design_dir = DATA_DIR / "designs" / draft_id
    design_dir.mkdir(parents=True, exist_ok=True)
    final_png_path = design_dir / "final.png"
    source_path = design_dir / "source.json"
    render_metadata_path = design_dir / "render_metadata.json"
    shutil.copyfile(source_artwork, final_png_path)

    try:
        with Image.open(final_png_path) as image:
            image.load()
            width, height = image.size
            mode = image.mode
            transparent = mode == "RGBA"
    except OSError as exc:
        raise HTTPException(status_code=400, detail="Agent artwork is not a readable image.") from exc

    margin_x = int(product_width * 0.12)
    margin_y = int(product_height * 0.15)
    placement_metadata = {
        "placement": "large_front",
        "canvas": {"width": product_width, "height": product_height},
        "intended_design_bounds": {
            "x": margin_x,
            "y": margin_y,
            "width": product_width - (margin_x * 2),
            "height": product_height - (margin_y * 2),
        },
    }
    source = {
        "draft_id": draft_id,
        "generator": "codex_agent_import_v1",
        "original_artwork_path": _relative_path(source_artwork),
        "creative_brief": creative_brief or {},
        "safety": {
            "external_image_generation_used": True,
            "amazon_interaction_used": False,
            "must_avoid": [
                "trademarks",
                "brand names",
                "celebrity likeness",
                "copyrighted characters",
                "living artist style imitation",
            ],
        },
    }
    render_metadata = {
        "renderer": "codex_agent_artwork_import_v1",
        "rendered_at": "agent_import",
        "final_png": _relative_path(final_png_path),
        "width": width,
        "height": height,
        "file_size_bytes": final_png_path.stat().st_size,
        "file_size_mb": round(final_png_path.stat().st_size / (1024 * 1024), 3),
        "transparent": transparent,
        "alpha_mode": mode,
        "external_services_used": True,
    }
    _write_json(source_path, source)
    _write_json(render_metadata_path, render_metadata)

    return {
        "final_png": render_metadata["final_png"],
        "source": _relative_path(source_path),
        "render_metadata": _relative_path(render_metadata_path),
        "width": product_width,
        "height": product_height,
        "transparent": transparent,
        "file_size_mb": render_metadata["file_size_mb"],
        "placement": "large_front",
        "placement_metadata": placement_metadata,
        "theme": str((creative_brief or {}).get("design_concept", "Codex agent generated artwork")),
        "brief": {
            **(creative_brief or {}),
            "generation_status": "imported_from_codex_agent",
            "renderer": render_metadata["renderer"],
            "external_services_used": True,
        },
    }


def import_agent_package(request: AgentPackageRequest) -> AgentPackageResponse:
    config = get_config()
    draft_id = f"drf_agent_{uuid4().hex[:10]}"
    candidate = _candidate_from_request(request)
    product = resolve_product_template(config.product_templates, request.product)
    product_prices = config.settings.get("default_prices", {}).get(product.code, {})
    enabled_marketplaces = request.marketplaces or config.settings.get("enabled_marketplaces", [])
    marketplace_plan = resolve_marketplaces(
        marketplace_config=config.marketplaces,
        enabled_marketplaces=enabled_marketplaces,
        priced_marketplaces=list(product_prices.keys()),
        explore_marketplaces=True,
    )
    compliance = run_compliance_gate(candidate)
    score = _merge_score(candidate, request.score)
    research_trace = {
        "source": "codex_agent",
        **(request.research_trace or {}),
    }
    design_override = None
    if request.artwork_path:
        design_override = _import_agent_artwork(
            artwork_path=request.artwork_path,
            draft_id=draft_id,
            product_width=product.width,
            product_height=product.height,
            creative_brief=request.creative_brief,
        )

    package = assemble_local_package(
        draft_id=draft_id,
        candidate=candidate,
        product=product,
        marketplace_plan=marketplace_plan,
        score=score,
        compliance=compliance,
        validation_config=config.validation,
        default_prices=config.settings.get("default_prices", {}),
        research_snapshot=research_trace,
        listing_groups_override=request.listing_groups,
        design_override=design_override,
    )
    draft = package.draft
    draft.research = {
        **(draft.research or {}),
        "agent_trace": research_trace,
        "creative_brief": request.creative_brief,
        "agent_import": True,
    }
    _write_updated_agent_artifacts(package.artifact_dir, draft.model_dump(mode="json"))

    with get_connection() as connection:
        upsert_draft_projection(connection, draft)
        insert_draft_event(
            connection,
            draft_id,
            "agent_package_imported",
            "Imported from Codex Merch Agent candidate package.",
            None,
            draft.status,
            {"source": "codex_agent", "artifact_dir": _relative_path(package.artifact_dir)},
        )

    return AgentPackageResponse(
        draft_id=draft_id,
        status=draft.status,
        artifact_dir=_relative_path(package.artifact_dir),
        message="Codex agent package imported and validated locally.",
        validation=draft.validation,
    )
