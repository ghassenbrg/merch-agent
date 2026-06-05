from __future__ import annotations

from typing import Any

from app.services.local_package_workflow.candidates import NicheCandidate
from app.services.local_package_workflow.product_templates import ProductResolution


def generate_design_brief(
    candidate: NicheCandidate,
    product: ProductResolution,
    draft_id: str,
) -> dict[str, Any]:
    return {
        "final_png": f"data/designs/{draft_id}/final.png",
        "width": product.width,
        "height": product.height,
        "transparent": True,
        "file_size_mb": 0.0,
        "placement": "large_front",
        "theme": candidate.design_angle,
        "brief": {
            "candidate_id": candidate.candidate_id,
            "niche": candidate.niche,
            "audience": candidate.audience,
            "style": "clean printable illustration with transparent background",
            "palette": ["deep green", "warm off-white", "charcoal", "muted accent"],
            "must_avoid": [
                "trademarks",
                "brand names",
                "celebrity likeness",
                "product type words in artwork",
            ],
            "generation_status": "metadata_only_no_image_generation",
        },
    }

