# Output Contract

Use this shape for `agent_trace.json` under `data/logs/agent_runs/<run_id>/`.

```json
{
  "run_id": "agent_run_...",
  "goal": "...",
  "created_at": "...",
  "preferences": {
    "count": 3,
    "product": "standard_tshirt",
    "marketplaces": [".com"],
    "excluded_niches": [],
    "preferred_niches": [],
    "risk_tolerance": "policy_bounded_autonomous",
    "autonomy_mode": "policy_bounded"
  },
  "autonomy_overrides": [
    {
      "default_or_preference": "...",
      "chosen_path": "...",
      "reason": "...",
      "evidence_refs": []
    }
  ],
  "sources": [
    {
      "title": "...",
      "url": "...",
      "accessed_at": "...",
      "notes": "..."
    }
  ],
  "candidates": [
    {
      "candidate_id": "cand_001",
      "niche": "...",
      "subniche": "...",
      "audience": "...",
      "buyer_intent": "...",
      "evidence": [],
      "competitor_observations": [],
      "score": {
        "overall": 0,
        "demand": 0,
        "trend": 0,
        "competition": 0,
        "compliance": 0,
        "design": 0,
        "marketplace": 0,
        "keywords": 0
      },
      "decision": "selected|rejected|human_review_required",
      "decision_reason": "...",
      "config_deviation_reason": null
    }
  ],
  "selected": [
    {
      "candidate_id": "cand_001",
      "creative_brief": {},
      "image_prompt": "...",
      "image_artifacts": [],
      "listing": {},
      "marketplaces": [],
      "price": {},
      "recommended_product_colors": [],
      "compliance": {
        "status": "pass|human_review_required|blocked",
        "reasons": []
      },
      "validation": {},
      "draft_id": null,
      "artifact_dir": null
    }
  ],
  "final_status": "completed|blocked|partial",
  "next_actions": []
}
```

## Package Readiness

A package is review-ready only when:

- final PNG exists
- dimensions match selected product template
- transparent background passes
- file size is under limit
- listing fields meet length and punctuation rules
- listing fields exclude product type terms
- selected marketplaces have copy
- price and royalty are configured
- compliance status is `pass`
- backend validation report is saved

Otherwise mark it `human_review_required`, `blocked`, or `partial`.

## Backend Import Payload

Use this shape with:

```bash
python3 scripts/backend_api.py import-package agent_package.json
```

```json
{
  "candidate": {
    "candidate_id": "agent_candidate_001",
    "niche": "Garden Book Club Weekends",
    "audience": "Readers, gardeners, and cozy weekend gift buyers",
    "keywords": ["garden reader", "book club", "plant lover"],
    "demand_signal": 80,
    "trend_signal": 72,
    "saturation_signal": 45,
    "compliance_signal": 95,
    "design_angle": "Botanical book stack with original cozy lettering",
    "listing_angle": "quiet reading and gardening gift idea",
    "risk_terms": []
  },
  "product": "standard_tshirt",
  "marketplaces": [".com"],
  "score": {
    "overall": 86,
    "demand": 80,
    "trend": 72,
    "competition": 65,
    "compliance": 95
  },
  "artwork_path": "data/logs/agent_runs/<run_id>/artwork/final.png",
  "creative_brief": {},
  "listing_groups": {
    "English": {
      "locale": "en",
      "marketplaces": [".com"],
      "design_title": "Garden Book Club Weekends",
      "brand": "Quiet Grove Studio",
      "feature_bullet_1": "Original reading and gardening artwork for cozy weekend plans.",
      "feature_bullet_2": "Gift-ready botanical book design for readers, plant lovers, and clubs.",
      "product_description": "A calm reading and garden themed design for people who plan their weekends around books, plants, and quiet club conversations."
    }
  },
  "research_trace": {
    "goal": "...",
    "sources": [],
    "decision_reason": "..."
  }
}
```
