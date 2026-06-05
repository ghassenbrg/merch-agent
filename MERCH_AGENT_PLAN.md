# Merch Agent Plan

This plan is based on the shared ChatGPT discussion:

- Shared discussion: https://chatgpt.com/share/6a22307a-0720-83a5-910d-818dc54adaed
- Amazon Seller Forums BSA update, effective March 4, 2026: https://sellercentral.amazon.com/seller-forums/discussions/t/84e3f6b1-42f7-4cf3-a189-a5cc8d78d838
- Merch on Demand content policy reference: https://merch.amazon.com/resource/201858630

## Core Decision

The Merch agent must separate local automation from Amazon interaction.

```text
Autopilot = research + scoring + compliance + design + listing + validation + local ready package
UI button = explicit user decision to send one approved package to Amazon draft
Amazon operator = one-shot browser assistant that saves draft only
```

The scheduled/autopilot workflow must never touch Amazon. It can create multiple local packages, but it stops at:

```text
READY_FOR_AMAZON_DRAFT
```

Amazon draft creation happens only when the user clicks a button for one package in the dashboard. The browser operator must never publish, submit for review, or batch upload.

## Target Architecture

```text
merch-agent/
  backend/
    app/
      main.py
      api/
        drafts.py
        workflows.py
        amazon.py
      services/
        autopilot_service.py
        draft_service.py
        amazon_draft_service.py
      db/
        models.py
        migrations/

  frontend/
    nuxt.config.ts
    pages/
      index.vue
      drafts/index.vue
      drafts/[id].vue
      runs/[id].vue
      settings.vue
    components/
      DraftCard.vue
      ScoreBreakdown.vue
      CompliancePanel.vue
      ListingEditor.vue
      AmazonDraftButton.vue
      DesignPreview.vue

  agent/
    merch_agent/
      research/
      scoring/
      compliance/
      design/
      listing/
      png_pipeline/
      browser/
        amazon_draft_operator.py

  config/
    product_templates.yaml
    marketplaces.yaml
    pricing.yaml
    validation.yaml
    amazon_upload_ui.yaml

  data/
    drafts/
    designs/
    screenshots/
    logs/
```

## Technology Choices

- Frontend: Nuxt 3 / Vue
- Backend: FastAPI / Python
- Database: SQLite first, Postgres later
- Browser operator: Playwright, ideally with a controlled browser profile
- Agent executor: Python workflow scripts, callable from backend jobs
- Storage: local filesystem first under `data/`

## Operating Modes

```yaml
modes:
  autopilot:
    touches_amazon: false
    output: "local approved draft packages"
    schedule_allowed: true

  amazon_draft_assist:
    touches_amazon: true
    trigger: "manual UI button only"
    batch_size: 1
    publish_allowed: false
    save_draft_allowed: true
```

Default workflow when the user says "Start the Merch agent":

```yaml
workflow:
  count: 5
  default_product: "standard_tshirt"
  explore_marketplaces: true
  touch_amazon: false
  final_status: "READY_FOR_AMAZON_DRAFT"
```

## End-to-End Workflow

```text
Scheduled Autopilot
  -> Find niches
  -> Score demand / trend / saturation / compliance
  -> Choose products and marketplaces
  -> Generate art direction
  -> Generate design PNG
  -> Validate transparency / size / placement
  -> Generate listing copy and localized copy
  -> Run internal approval checks
  -> Save as READY_FOR_AMAZON_DRAFT
  -> Show in Nuxt dashboard
  -> User reviews
  -> User clicks Save as Amazon Draft for one package
  -> One-shot Playwright browser operator runs
  -> Amazon draft saved
  -> User manually reviews/publishes inside Merch
```

## Product Template Config

Create `config/product_templates.yaml`:

```yaml
product_templates:
  tshirts_sweatshirts_long_sleeve_back_hoodie:
    width: 4500
    height: 5400
    products:
      - standard_tshirt
      - premium_tshirt
      - sweatshirt
      - long_sleeve_tshirt
      - pullover_hoodie_back

  crop_tops_crop_sweatshirts_front_hoodies:
    width: 4500
    height: 4050
    products:
      - crop_top
      - crop_sweatshirt
      - pullover_hoodie_front
      - zip_hoodie_front

  performance_tops:
    width: 1200
    height: 1200
    products:
      - performance_polo
      - performance_quarter_zip

  hats_visors:
    width: 1500
    height: 675
    products:
      - printed_baseball_hat
      - printed_trucker_hat
      - sport_sun_visor

  popsockets:
    width: 485
    height: 485
    products:
      - popsockets_grip

  iphone_cases:
    width: 1800
    height: 3200
    products:
      - iphone_case

  tote_bags_throw_pillows:
    width: 2925
    height: 2925
    products:
      - tote_bag
      - throw_pillow

  tumblers_water_bottles:
    width: 3000
    height: 1400
    products:
      - tumbler
      - water_bottle

  mugs:
    width: 2700
    height: 1050
    products:
      - mug

default_products:
  - standard_tshirt

products:
  standard_tshirt:
    template: tshirts_sweatshirts_long_sleeve_back_hoodie
    width: 4500
    height: 5400
```

## Marketplace and Language Groups

Available marketplaces:

```text
.com
.co.uk
.de
.fr
.it
.es
.co.jp
```

Use one listing object per language section, not necessarily one per marketplace.

```yaml
language_sections:
  English:
    marketplaces: [".com", ".co.uk"]
    locale: "en"
  German:
    marketplaces: [".de"]
    locale: "de"
  French:
    marketplaces: [".fr"]
    locale: "fr"
  Italian:
    marketplaces: [".it"]
    locale: "it"
  Spanish:
    marketplaces: [".es"]
    locale: "es"
  Japanese:
    marketplaces: [".co.jp"]
    locale: "ja"
```

If the agent selects only `.com` and `.co.uk`, it fills only the English section. If it selects `.co.jp`, it must generate and fill Japanese copy itself.

## Amazon Upload UI Contract

Create `config/amazon_upload_ui.yaml`:

```yaml
amazon_upload_ui:
  translation_option:
    default: "provide_own_translations"
    radio_label: "No, I'll provide my own translations"
    never_use_auto_translation: true

  required_fields:
    - design_title
    - brand

  optional_but_recommended_fields:
    - feature_bullet_1
    - feature_bullet_2
    - product_description

  description:
    min_chars: 75
    max_chars: 2000

  hard_rules:
    - never_click_publish
    - save_draft_only
    - stop_on_warning
    - stop_on_missing_required_field
    - stop_on_negative_or_zero_royalty
```

The operator must always choose:

```text
No, I'll provide my own translations
```

It must never use Amazon auto-translation.

## Listing Text Rules

Amazon warns against product-type references in listing copy. The generator should remove product-type words from titles, bullets, and descriptions.

Example bad title:

```text
Funny Fly Fishing Grandpa Shirt
```

Better:

```text
Funny Fly Fishing Grandpa
```

Example bad bullet:

```text
Great fishing shirt for grandpas.
```

Better:

```text
Great gift idea for grandpas who love quiet weekends by the water.
```

Initial banned product-type terms:

```yaml
banned_product_type_terms:
  english:
    - shirt
    - t-shirt
    - tshirt
    - tee
    - hoodie
    - sweatshirt
    - long sleeve
    - tank top
    - mug
    - tote bag
    - pillow
    - popsocket
    - phone case
    - tumbler
    - water bottle
    - hat
    - visor
```

Any draft containing these terms in listing fields should be blocked:

```text
Status: LISTING_NEEDS_FIX
Reason: Product type term detected in English feature bullet 1: "shirt"
```

## Draft Statuses

```text
RESEARCHED
SCORED
BLOCKED_COMPLIANCE
DESIGN_GENERATED
PNG_VALIDATED
LISTING_READY
READY_FOR_AMAZON_DRAFT
AMAZON_DRAFT_IN_PROGRESS
AMAZON_DRAFT_SAVED
AMAZON_DRAFT_FAILED
MANUALLY_PUBLISHED
ARCHIVED
```

Only this status enables the Amazon button:

```text
READY_FOR_AMAZON_DRAFT
```

## Draft JSON Shape

```json
{
  "draft_id": "drf_20260605_0001",
  "status": "READY_FOR_AMAZON_DRAFT",
  "products": [
    {
      "code": "standard_tshirt",
      "template": "tshirts_sweatshirts_long_sleeve_back_hoodie",
      "width": 4500,
      "height": 5400,
      "selected": true
    }
  ],
  "marketplaces": [
    {
      "code": ".com",
      "language_group": "English",
      "selected": true
    },
    {
      "code": ".co.uk",
      "language_group": "English",
      "selected": true
    },
    {
      "code": ".co.jp",
      "language_group": "Japanese",
      "selected": false,
      "excluded_reason": "English humor does not translate naturally."
    }
  ],
  "translation_mode": "provide_own_translations",
  "design": {
    "final_png": "data/designs/drf_20260605_0001/final.png",
    "width": 4500,
    "height": 5400,
    "transparent": true,
    "file_size_mb": 12.4,
    "placement": "large_front"
  },
  "listing_groups": {
    "English": {
      "locale": "en",
      "marketplaces": [".com", ".co.uk"],
      "design_title": "Funny Fly Fishing Grandpa",
      "brand": "Quiet River Outfitters",
      "feature_bullet_1": "Original fly fishing design for grandpas who enjoy quiet weekends by the water.",
      "feature_bullet_2": "Great gift idea for birthdays, Father's Day, retirement, and fishing trips.",
      "product_description": "A vintage-inspired fly fishing design made for casual outdoor fans, grandpas, and families looking for a relaxed fishing-themed gift."
    }
  },
  "listing_validation": {
    "product_type_terms_found": [],
    "min_description_length_passed": true,
    "required_fields_passed": true,
    "warnings": []
  },
  "amazon_draft": {
    "eligible": true,
    "saved": false,
    "publish_allowed": false
  }
}
```

## Ready-for-Amazon-Draft Checks

The UI should show or enable `Save as Amazon Draft` only when all checks pass.

```yaml
ready_for_amazon_draft:
  png_valid: true
  transparent_background: true
  correct_resolution: true
  file_size_under_limit: true
  design_not_too_small: true
  design_not_cropped: true
  trademark_precheck: "pass"
  amazon_policy_precheck: "pass"
  product_type_terms_removed: true
  listing_min_lengths_passed: true
  selected_marketplaces_have_copy: true
  price_config_exists: true
```

## Backend API

```http
POST /api/workflows/autopilot/run
GET  /api/drafts
GET  /api/drafts/{draftId}
POST /api/drafts/{draftId}/approve
POST /api/drafts/{draftId}/reject
POST /api/drafts/{draftId}/regenerate-design
POST /api/drafts/{draftId}/regenerate-listing
POST /api/drafts/{draftId}/amazon-draft
GET  /api/runs/{runId}/logs
```

Critical endpoint behavior:

```python
@app.post("/api/drafts/{draft_id}/amazon-draft")
def start_amazon_draft(draft_id: str):
    draft = get_draft(draft_id)

    if draft.status != "READY_FOR_AMAZON_DRAFT":
        raise HTTPException(400, "Draft is not ready for Amazon.")

    if draft.amazon_draft_saved:
        raise HTTPException(400, "Draft already saved to Amazon.")

    lock_draft(draft_id)

    job_id = enqueue_amazon_draft_job(draft_id)

    return {
        "jobId": job_id,
        "status": "AMAZON_DRAFT_IN_PROGRESS"
    }
```

## Nuxt Dashboard

Pages:

```text
/dashboard
  Overview of generated opportunities

/drafts
  List of draft packages

/drafts/:id
  Full review page

/settings
  Marketplaces, products, pricing, thresholds, API keys

/runs
  Workflow logs and reports
```

Draft detail page should show:

```text
Design preview
Final PNG download
Niche explanation
Score breakdown
Compliance report
Trademark precheck result
Selected products
Selected marketplaces
Excluded marketplaces + reasons
Translation mode
Listing copy per language group
Price recommendation
Royalty check status
Warnings
Amazon draft action button
```

Draft actions:

```text
Approve locally
Reject
Regenerate design
Regenerate listing
Edit listing manually
Save as Amazon Draft
Archive
```

The `Save as Amazon Draft` button should be disabled unless:

```text
draft.status == READY_FOR_AMAZON_DRAFT
```

## Amazon Draft Assist Flow

When the user clicks `Save as Amazon Draft`, the backend should:

```text
1. Lock this draft.
2. Re-check status = READY_FOR_AMAZON_DRAFT.
3. Open browser with an approved profile/session.
4. Open Merch create-product URL.
5. Upload final PNG.
6. Select product type.
7. Select marketplace(s).
8. Set price.
9. Check royalty is positive.
10. Go to translation options.
11. Select "No, I'll provide my own translations."
12. Expand selected language sections.
13. Fill design title.
14. Fill brand.
15. Fill feature bullet 1.
16. Fill feature bullet 2.
17. Fill description.
18. Take screenshot.
19. Check no warnings.
20. If warning exists, stop and mark AMAZON_DRAFT_FAILED.
21. Click Save Draft only.
22. Take final screenshot.
23. Mark status AMAZON_DRAFT_SAVED.
```

The confirmation modal should make the boundary explicit:

```text
You are about to create an Amazon Merch draft for:

Draft: Funny Fly Fishing Grandpa
Product: Standard T-Shirt
Marketplaces: .com, .co.uk
Price: $19.99
Action: Save Draft only

This will open/control the browser.
The operator will never click Publish.

[Cancel] [Start Amazon Draft Assist]
```

## Browser Operator Guardrails

Dangerous text:

```python
DANGEROUS_TEXT = [
    "publish",
    "submit",
    "submit for review",
    "make live",
    "create product",
]
```

Safe text:

```python
SAFE_TEXT = [
    "save draft",
    "save as draft",
]
```

Before any click:

```python
def safe_click(button):
    text = button.inner_text().strip().lower()

    if any(x in text for x in DANGEROUS_TEXT):
        raise RuntimeError(f"Blocked dangerous button: {text}")

    if not any(x in text for x in SAFE_TEXT):
        raise RuntimeError(f"Blocked unknown action button: {text}")

    button.click()
```

The Amazon draft operator should only click a button matching:

```text
Save Draft
Save as Draft
```

Exact selectors must be confirmed from the live page because screenshots are not enough to guarantee DOM selectors.

## Implementation Phases

### Phase 1: Repo Scaffold and Contracts

Deliverables:

- Backend FastAPI skeleton.
- Nuxt 3 frontend skeleton.
- Python agent package skeleton.
- Config files for products, marketplaces, validation, pricing, and upload UI.
- Draft JSON/schema definitions.
- Local `data/` directories.
- README with setup commands.

Goal:

Have a runnable app shell with sample data and agreed contracts.

### Phase 2: Draft Store and API

Deliverables:

- SQLite models for drafts, runs, artifacts, logs, and statuses.
- API endpoints for listing drafts, viewing draft detail, updating status, and reading logs.
- Validation service for status transitions.
- Seed command that creates sample `READY_FOR_AMAZON_DRAFT` drafts.

Goal:

The backend can persist and serve review-ready draft packages.

### Phase 3: Nuxt Review Dashboard

Deliverables:

- Draft list page.
- Draft detail page.
- Design preview.
- Listing editor.
- Score and compliance panels.
- Status badges and warnings.
- Disabled/enabled Amazon draft button based on eligibility.

Goal:

The user can inspect and edit local packages before any Amazon interaction exists.

### Phase 4: Fake Autopilot

Deliverables:

- `POST /api/workflows/autopilot/run`.
- Mock pipeline that creates realistic local draft packages.
- Run logs and artifact folders.
- End-to-end local run visible in the UI.

Goal:

Prove the workflow lifecycle before connecting external services.

### Phase 5: Validation Engine

Deliverables:

- PNG validation: dimensions, transparency, file size, placement.
- Listing validation: required fields, min/max lengths, banned product terms.
- Marketplace validation: every selected marketplace has matching language copy.
- Pricing validation: configured price exists and royalty check is represented.
- Compliance precheck result model.

Goal:

Only valid packages can become `READY_FOR_AMAZON_DRAFT`.

### Phase 6: Real Agent Modules

Deliverables:

- Niche discovery.
- Candidate scoring.
- Conservative compliance review.
- Design brief generation.
- Artwork generation/import pipeline.
- Listing generation and localization.
- Package assembler.

Goal:

Replace the fake autopilot with real candidate-to-package generation.

### Phase 7: Amazon Draft Assist, Dry Run First

Deliverables:

- Backend job for one draft only.
- Draft locking.
- Confirmation modal.
- Playwright operator with dry-run mode.
- Selector discovery workflow.
- Screenshot capture.
- Strict safe-click rules.
- Mocked tests for dangerous button blocking.

Goal:

Prove the operator cannot publish and cannot run in batch.

### Phase 8: Controlled Live Amazon Draft Save

Deliverables:

- Manual policy/account readiness checklist.
- Live selector confirmation.
- One manually selected package saved as Amazon draft.
- Screenshots before and after.
- Status update to `AMAZON_DRAFT_SAVED`.
- Error handling to `AMAZON_DRAFT_FAILED`.

Goal:

Safely create one Amazon draft only after user confirmation.

## Testing Plan

Backend:

- Unit tests for draft status transitions.
- Unit tests for banned product-type term detection.
- Unit tests for marketplace-to-language grouping.
- Unit tests for ready-for-Amazon validation.
- API tests for draft and workflow endpoints.

Agent:

- Tests for product template resolution.
- Tests for listing validation.
- Tests for package assembly.
- PNG validation fixture tests.

Frontend:

- Draft list rendering.
- Draft detail rendering.
- Listing edit flow.
- Amazon button disabled unless eligible.
- Confirmation modal behavior.

Browser operator:

- Mock page tests for safe-click.
- Tests that dangerous actions are blocked.
- Dry-run test with no Amazon writes.
- Screenshot capture tests.

## Key Safety Rules

- Autopilot never opens Amazon.
- Scheduled jobs never create Amazon drafts.
- Amazon draft assist is manual, one draft at a time.
- Amazon draft assist requires `READY_FOR_AMAZON_DRAFT`.
- Draft is locked before browser work starts.
- Auto-translation is never used.
- Product-type words are blocked from listing copy.
- Browser operator stops on warnings.
- Browser operator clicks only Save Draft / Save as Draft.
- Browser operator never clicks Publish / Submit / Submit for review / Make live.
- User manually reviews and publishes later inside Merch.

## First Milestone Recommendation

Start with Phase 1 through Phase 4:

```text
Scaffold app
Add config contracts
Create draft schema
Build API
Build Nuxt dashboard
Create fake autopilot sample packages
```

This gives us a working local product before we connect real research, image generation, or Amazon browser automation.

## Next Session Handoff Plan

Updated after the initial implementation and UI redesign.

### Current Implemented State

- Root planning doc exists: `MERCH_AGENT_PLAN.md`.
- README exists with setup and production-preview instructions.
- Backend is scaffolded with FastAPI, SQLite, seeded draft data, draft APIs, workflow APIs, validation service, fake autopilot service, and simulated Amazon Draft Assist.
- Backend tests pass: `cd backend && . .venv/bin/activate && pytest -q`.
- Frontend is scaffolded with Nuxt 3, Vue, lucide icons, app layout, dashboard, draft queue, detail review, listing view, validation panel, score breakdown, and basic pages for Drafts, Runs, and Settings.
- Frontend production build passes: `cd frontend && npm run build`.
- Frontend audit passes: `cd frontend && npm audit --audit-level=moderate`.
- Dashboard UI has been redesigned with a dark sidebar, cool workspace, white panels, teal selected states, semantic safety colors, stronger metric cards, and a clearer Amazon Draft Assist panel.
- Sidebar selected menu state is route-driven and verified for `/runs` and `/settings`.
- Browser QA was done with Playwright because the direct in-app Browser control tool was not exposed in the session.

### Known Runtime Notes

- Use production preview for the frontend. Nuxt dev mode previously had a Vite IPC socket issue under the local Node 24/macOS environment.
- Start backend:

```bash
cd backend
. .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

- Start frontend after build:

```bash
cd frontend
NUXT_PUBLIC_API_BASE=http://127.0.0.1:8000 HOST=0.0.0.0 PORT=3000 node .output/server/index.mjs
```

- Open app: `http://localhost:3000`.
- If seeded data becomes noisy from tests or UI actions, reset the demo DB:

```bash
rm -f data/merch_agent.sqlite3
find data -maxdepth 1 -name 'merch_agent.sqlite3-*' -delete
```

Then restart the backend so it reseeds.

### Next Work Sequence

#### 1. Repo Hygiene and Baseline Verification

Goal: make the current implementation easy to continue safely.

- Inspect `.gitignore` and ensure generated artifacts are excluded:
  - `frontend/node_modules/`
  - `frontend/.nuxt/`
  - `frontend/.output/`
  - `backend/.venv/`
  - `backend/.pytest_cache/`
  - `data/*.sqlite3`
  - `data/*.sqlite3-*`
  - `data/frontend-preview.log`
  - generated screenshots
- Run full verification:

```bash
cd backend && . .venv/bin/activate && pytest -q
cd frontend && npm run build
cd frontend && npm audit --audit-level=moderate
```

- Run Playwright smoke QA on desktop and mobile.
- Do not implement Amazon live automation yet.

#### 2. Finish Core Dashboard Workflow

Goal: make the local review dashboard usable beyond the first screen.

- Build real Drafts page:
  - list all drafts
  - filters by status, product, marketplace
  - link to individual draft detail route
- Add draft detail route:
  - `frontend/pages/drafts/[id].vue`
  - reuse the current dashboard detail components
  - keep actions route-safe and status-aware
- Build Runs page:
  - show autopilot run history from API
  - show generated draft count and status outcomes
  - show started/completed timestamps
- Build Settings page:
  - display config from YAML-derived backend endpoints
  - marketplace toggles
  - default product selection
  - pricing display
  - validation thresholds
- Add empty/loading/error states that match the redesigned UI.

#### 3. Strengthen Backend Data Model

Goal: move from JSON payload persistence toward clear app contracts.

- Add explicit SQLite tables or a stronger repository layer for:
  - drafts
  - runs
  - draft events/status history
  - validation results
  - listing groups
  - Amazon draft attempts
- Add backend endpoints:
  - `GET /api/runs`
  - `GET /api/runs/{run_id}`
  - `GET /api/config`
  - `PATCH /api/settings`
  - `GET /api/drafts/{draft_id}/events`
- Add tests for all new endpoints.

#### 4. Replace Fake Autopilot With Real Local Package Workflow

Goal: create real local `READY_FOR_AMAZON_DRAFT` packages without touching Amazon.

- Implement agent modules in this order:
  - product template resolver
  - marketplace/language resolver
  - niche candidate model
  - scoring model
  - conservative compliance gate
  - design brief generator
  - listing generator
  - listing validator
  - package assembler
- Keep external research/image generation optional at first; support deterministic local fixtures so tests are stable.
- Every generated package must produce:
  - draft JSON
  - listing fields
  - validation report
  - design metadata
  - final status

#### 5. Artwork Pipeline

Goal: validate artwork contracts before any upload workflow exists.

- Add PNG validation service:
  - dimensions match selected product template
  - transparent background required
  - file size threshold
  - safe placement metadata
  - no cropped design signal
- Add fixture PNGs for pass/fail cases.
- Add tests for every validation rule.
- Keep actual design generation as a separate step after validation contracts are solid.

#### 6. Amazon Draft Assist Dry Run

Goal: prove safety before any live Amazon interaction.

- Keep Amazon interaction manual, one draft only, and save-draft only.
- Implement dry-run Playwright operator with:
  - controlled browser profile path
  - selector map from `config/amazon_upload_ui.yaml`
  - draft lock before starting
  - screenshot capture at each step
  - dangerous action blocker
  - no live submit/publish paths
- Add tests that blocked labels cannot be clicked:
  - Publish
  - Submit
  - Submit for review
  - Make live
  - Update live listing
- Add UI confirmation modal with exact safety copy.

#### 7. Controlled Live Draft Save

Goal: only after dry-run safety is tested, save one Amazon draft manually.

- Require user confirmation in UI.
- Require draft status `READY_FOR_AMAZON_DRAFT`.
- Fill one package only.
- Select “No, I’ll provide my own translations.”
- Save as draft only.
- Capture screenshots before and after.
- Update local status to `AMAZON_DRAFT_SAVED` or `AMAZON_DRAFT_FAILED`.
- Never publish or submit for review.

### Latest Completed Milestone: Local Dashboard Workflow

Completed after the initial dashboard redesign:

- Repo hygiene was checked and generated artifacts are ignored, including Nuxt build output, Python caches, SQLite files, generated screenshots, and `data/frontend-preview.log`.
- Backend now exposes the dashboard support APIs:
  - `GET /api/runs`
  - `GET /api/runs/{run_id}`
  - `GET /api/config`
  - `PATCH /api/settings`
  - `GET /api/drafts/{draft_id}/events`
  - `GET /api/drafts/{draft_id}/design/final.png`
- SQLite now records run-to-draft links, draft events/status history, and local settings overrides.
- The Nuxt dashboard has real data-backed pages:
  - `frontend/pages/drafts/index.vue`
  - `frontend/pages/drafts/[id].vue`
  - `frontend/pages/runs/index.vue`
  - `frontend/pages/settings.vue`
- Draft detail review includes products, selected/excluded marketplaces, validation, score, listing groups, draft events, readiness checks, and the simulated Amazon Draft Assist action.
- Runs page shows run history, generated draft counts, outcomes, logs, and draft links.
- Settings page shows YAML-derived config/contracts for marketplaces, products, prices, validation, language sections, and Amazon Draft Assist guardrails.
- Focused backend tests were added for the new endpoints.

Verification completed:

```bash
cd backend && . .venv/bin/activate && pytest -q
cd frontend && npm run build
cd frontend && npm audit --audit-level=moderate
```

Playwright QA was run against production preview on desktop and mobile for:

```text
/
/drafts
/drafts/drf_20260605_0001
/runs
/settings
```

Result: all routes returned 200, no console/page errors, and no horizontal overflow after the mobile table-row fix.

### Immediate Next Session Recommendation

Start item 4 from the Next Work Sequence: replace the fake autopilot with a real deterministic local package workflow. Keep it fixture-driven first so tests are stable and the UI has real local packages before any external research, image generation, or Amazon browser work exists.

Do the next session in this order:

1. Baseline verify:
   - `cd backend && . .venv/bin/activate && pytest -q`
   - `cd frontend && npm run build`
   - `cd frontend && npm audit --audit-level=moderate`
2. Add deterministic agent/domain modules:
   - product template resolver
   - marketplace/language resolver
   - niche candidate model
   - scoring model
   - conservative compliance gate
   - design brief generator
   - listing generator
   - listing validator
   - package assembler
3. Replace the fake autopilot service path so `/api/workflows/autopilot/run` creates real local draft package artifacts under `data/drafts/`, while continuing to write SQLite draft/run records for the dashboard.
4. Keep all new workflow tests fixture-driven and deterministic.
5. Ensure generated packages include:
   - draft JSON
   - listing fields
   - validation report
   - design metadata
   - final status
6. Re-run backend tests, frontend build, audit, and Playwright desktop/mobile QA.

Out of scope for the next session:

- Do not implement live Amazon browser automation.
- Do not connect external research APIs yet unless explicitly requested.
- Do not connect real image generation yet; use deterministic design metadata/briefs and placeholder-safe package contracts.
- Do not publish, submit for review, batch upload, edit live listings, or click dangerous Amazon actions.

## Copy/Paste Prompt For Next Session

Use this prompt in a new Codex session from `/Users/ghassenbrg/git/merch-agent`:

```text
We are continuing the Merch Agent project in /Users/ghassenbrg/git/merch-agent.

Read MERCH_AGENT_PLAN.md first, especially "Next Session Handoff Plan", "Latest Completed Milestone: Local Dashboard Workflow", and "Immediate Next Session Recommendation".

Current state:
- FastAPI backend has SQLite seed data, draft APIs, workflow API, validation, simulated Amazon Draft Assist, run history APIs, config/settings APIs, draft event APIs, and focused tests.
- Nuxt 3 frontend has the redesigned dashboard UI plus real Drafts, draft detail, Runs, and Settings pages backed by the API.
- Production frontend preview should be used, not Nuxt dev mode, because dev mode previously had a Vite IPC socket issue on this machine.
- Generated build/runtime artifacts are ignored.

Hard safety constraints:
- Autopilot must never touch Amazon.
- Amazon Draft Assist remains manual, one draft at a time, save draft only, and simulated until dry-run safety work is explicitly started.
- Never publish, submit for review, batch upload, edit live listings, or click dangerous Amazon actions.
- Do not implement live Amazon browser automation in this session.

First verify:
cd backend && . .venv/bin/activate && pytest -q
cd frontend && npm run build
cd frontend && npm audit --audit-level=moderate

Next milestone:
Replace the fake autopilot with a real deterministic local package workflow, still with zero Amazon interaction and no external services required.

Implement in this order:
1. Product template resolver using config/product_templates.yaml.
2. Marketplace/language resolver using config/marketplaces.yaml.
3. Deterministic niche candidate model with local fixture candidates.
4. Scoring model that produces demand/trend/saturation/compliance/overall values.
5. Conservative compliance gate that blocks risky candidates before package assembly.
6. Design brief generator that creates auditable design metadata, not real image generation yet.
7. Listing generator and listing validator that enforce banned product-type terms and required fields.
8. Package assembler that writes local artifacts under data/drafts/ and creates SQLite draft/run records for the existing dashboard.
9. Focused backend tests for each resolver/generator/gate plus the autopilot endpoint.

Generated local packages must include:
- draft JSON
- listing fields
- validation report
- design metadata
- final status, preferably READY_FOR_AMAZON_DRAFT only when all local checks pass

After implementation:
cd backend && . .venv/bin/activate && pytest -q
cd frontend && npm run build
cd frontend && npm audit --audit-level=moderate

Then run Playwright desktop/mobile QA against production preview for:
/
/drafts
/drafts/<new_generated_draft_id>
/runs
/settings

Do not start Amazon dry-run or live automation work unless explicitly instructed after this local package workflow is complete.
```
