---
name: merch-agent
description: "Use when the user asks Codex to run this repo's Merch Agent as an AI-controlled Amazon Merch workflow: research niches, analyze demand and saturation, score candidates, choose niches/subniches, generate creative direction or images, assemble local packages, validate artifacts, or coordinate the local FastAPI/Nuxt dashboard."
---

# Merch Agent

## Mission

Run Merch Agent as a Codex-native autonomous business workflow. The user should be able to provide preferences, start autopilot, leave, and return to review finished local packages with artwork, listing copy, marketplace/price decisions, validation reports, and a clear decision trace.

Codex/plugin owns the intelligence loop. The backend and UI are support systems:

- Codex/plugin: web/MCP research, opportunity discovery, trend and competitor analysis, scoring, niche/subniche decisions, creative direction, image generation, keyword/listing decisions, and run explanation.
- Backend: config, persistence, deterministic validation, package artifacts, status history, and Amazon draft-save guardrails.
- UI: review console for drafts, traces, edits, approvals, rejects, exports, and one-package save-draft assist.

## Default Autopilot Contract

When the user says "run autopilot", "find opportunities", "generate Merch packages", or similar:

- Use strong defaults instead of asking questions unless a missing choice would be risky.
- Default product: `standard_tshirt`.
- Default artboard: read `config/product_templates.yaml`; currently `standard_tshirt` requires `4500x5400`.
- Default output: local review-ready packages only.
- Default Amazon behavior: no Amazon interaction.
- Default quality bar: only deliver packages that pass deterministic validation or clearly label blockers.
- Default user role: review only, with optional edits/approval after generation.

## Autonomous Decision Contract

Operate as a policy-bounded autonomous merch strategist, not as a narrow config executor.

- Treat user preferences, local config defaults, scoring weights, and prior niche lists as guidance and operating context, not creative ceilings.
- The only hard creative/business stop is Amazon policy, IP/copyright/trademark safety, account safety, deterministic artifact requirements, and explicit user exclusions.
- Search beyond the configured niche universe when evidence suggests a stronger opportunity.
- Challenge weak user or config preferences in the trace instead of blindly following them.
- Adapt research depth, scoring emphasis, design direction, marketplace choice, pricing, product colors, and listing strategy to the evidence.
- Prefer the best compliant opportunity over the safest-looking mediocre one.
- Generate fewer than requested only when policy, evidence, or validation quality would make additional packages weak.
- Never loosen policy, trademark, copyright, listing-term, artwork-size, or Amazon account guardrails in the name of autonomy.
- Record every material deviation from defaults in `agent_trace.json` with the evidence and decision reason.

## E2E Flow

Follow this sequence:

1. Initialize run context and preferences. Use `scripts/init_autopilot_run.py` when starting a durable run folder.
2. Load backend/config context: products, marketplaces, prices, validation rules, and current drafts.
3. Research opportunities using current web/MCP evidence. Use multiple sources and record sources.
4. Normalize candidates into niches/subniches with buyer intent and design angles.
5. Compare demand, trend, saturation, competition, compliance risk, design feasibility, and marketplace fit.
6. Reject weak or risky candidates with reasons.
7. Select winners using `references/scoring-rubric.md`.
8. Build creative briefs using `references/creative-and-artwork.md`.
9. Generate or obtain artwork. Use the `imagegen` skill/tool for raster artwork when available.
10. Validate artwork: transparent background, exact dimensions, file size, margins, no cropping, sufficient design area.
11. Generate listing fields, keywords, marketplace choice, product colors, and price recommendations.
12. Persist packages through backend adapters when available; otherwise write agent trace and artifacts under `data/logs/agent_runs/` and report the missing backend adapter.
13. Run backend validation and return draft IDs/artifact paths.
14. Summarize what is ready, what was rejected, what needs human review, and what the user should inspect in the UI.

## Required Evidence And Trace

Every run must preserve:

- original user goal and defaults applied
- sources searched
- opportunity candidates
- competitor/design observations
- rejected candidates with reasons
- scoring table
- selected candidates
- creative briefs
- image prompts and generated image references
- listing fields and keyword strategy
- marketplace, price, and product color decisions
- compliance review
- validation results
- final draft IDs or package artifact paths

Use `references/output-contract.md` for the trace shape.

## Commands

From the plugin root:

```bash
python3 scripts/init_autopilot_run.py --goal "Find 3 safe evergreen US t-shirt opportunities" --count 3
python3 scripts/backend_api.py health
python3 scripts/backend_api.py config
python3 scripts/backend_api.py drafts
python3 scripts/backend_api.py run-local --count 1 --product standard_tshirt
python3 scripts/backend_api.py import-package path/to/agent_package.json
```

Environment:

```bash
export MERCH_AGENT_API_BASE=http://127.0.0.1:8000
export MERCH_AGENT_API_TOKEN=...
```

`run-local` calls the current deterministic backend endpoint. Use `import-package` for the Codex-agent path after candidate selection, creative direction, optional image generation, and listing decisions.

## References

Read these as needed:

- `references/workflow.md`: product architecture and authority split.
- `references/autopilot-flow.md`: detailed phase-by-phase autopilot procedure.
- `references/autonomous-decisioning.md`: policy-bounded autonomy rules for overriding weak config/defaults.
- `references/scoring-rubric.md`: candidate scoring and selection rules.
- `references/compliance.md`: conservative copyright, trademark, and Amazon policy gates.
- `references/creative-and-artwork.md`: image, shirt color, design, and upload requirements.
- `references/output-contract.md`: run trace and package output schema.

## Hard Safety Rules

- Do not publish, submit for review, create live products, update live listings, or run batch Amazon actions.
- Autopilot research and package generation must not touch Amazon account state.
- Amazon Draft Assist is only one reviewed package at a time, save-draft-only, after explicit user confirmation.
- Do not use copyrighted characters, celebrities, brands, logos, protected phrases, or style imitation of living artists.
- If evidence is weak or policy risk is unclear, mark human review required.

## Implementation Direction

If editing the repo, preserve this shape:

- Plugin/skill remains the Codex control plane.
- Add backend AI-run support under `/api/agent/...` for UI-triggered runs and traces.
- Add backend package import endpoints for AI-selected candidates/artwork/listings.
- Keep deterministic validation and Amazon guardrails in backend services.
