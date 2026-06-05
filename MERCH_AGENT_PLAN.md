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

### Latest Completed Milestone: Research and Candidate Discovery Expansion

Completed after Production Readiness Roadmap Phase 4:

- Added `config/candidate_sources.yaml` with deterministic local candidate sources, a seedable local generator, duplicate/cooldown settings, conservative precheck terms, and default-off external research adapter stubs.
- `backend/app/services/local_package_workflow/candidates.py` now discovers varied local candidates without external services, records source/search phrase/score inputs, audits accepted and skipped candidates, detects duplicate niches and keyword signatures, applies niche cooldowns, and blocks conservative term/trademark risks before scoring.
- Autopilot now uses candidate discovery instead of cycling fixed fixtures, writes `data/logs/<run_id>_candidate_audit.json`, logs every skipped candidate reason, and stores accepted candidate research metadata in each draft.
- Added snapshot-backed research evidence enforcement for production autopilot mode: live research must be collected and persisted before scoring, and scoring consumes only saved snapshots.
- Added live, config-gated research adapters for demand, trend, competition, and saturation signals, with deterministic fixture snapshots used by tests.
- Production mode fails clearly without research evidence; unavailable external research cannot silently create packages.
- Package assembly writes `data/drafts/<draft_id>/candidate_research.json` alongside draft JSON, listing fields, validation report, and design metadata.
- External research remains optional, disabled by default, config-gated, and not required by tests.
- No Amazon interaction was added or performed.

Verification completed:

```bash
cd backend && . .venv/bin/activate && pytest -q
cd frontend && npm run build
cd frontend && npm audit --audit-level=moderate
```

Production-preview browser QA was run against desktop and mobile viewport routes:

```text
/
/drafts
/drafts/drf_auto_e66ee6a9be
/runs
/settings
```

Result: pages rendered nonblank, no framework overlays, no console warnings/errors, no horizontal overflow, app-shell navigation worked, the fresh generated draft detail loaded its real `4500x5400` PNG preview at a `390px` mobile viewport, and the local autopilot button completed with "No Amazon interaction occurred."

### Immediate Next Session Recommendation

Start Phase 6 from the Production Readiness Roadmap: dashboard review, editing, and approval workflow. Keep all Amazon Draft Assist work simulated and manual only; do not start Amazon dry-run or live automation work.

For every future session:

1. Read this file first.
2. Run baseline verification:
   - `cd backend && . .venv/bin/activate && pytest -q`
   - `cd frontend && npm run build`
   - `cd frontend && npm audit --audit-level=moderate`
3. Work only on Phase 6 unless the user explicitly changes scope.
4. Re-run backend tests, frontend build, audit, and production-preview browser QA.
5. Update this plan with completed phase notes and the next session recommendation.

## Production Readiness Roadmap

Use these phases sequentially across new Codex sessions. Do not skip a safety gate just because the implementation appears small.

### Phase 0: Session Baseline and Handoff Discipline

Status: ongoing requirement.

Goal: keep each session restartable and prevent accidental Amazon work.

Scope:

- Read `MERCH_AGENT_PLAN.md`.
- Inspect `git status --short --untracked-files=all`.
- Run backend tests, frontend production build, and frontend audit.
- Use production frontend preview for browser QA, not Nuxt dev mode.
- Keep generated runtime files ignored.

Exit criteria:

- Baseline commands pass or known failures are documented before edits.
- No unrelated user changes are reverted.
- The current phase and next phase are written down in this file.

Copy/paste prompt:

```text
We are continuing the Merch Agent project in /Users/ghassenbrg/git/merch-agent.
Read MERCH_AGENT_PLAN.md first. Work only on the next incomplete phase in the Production Readiness Roadmap.
First run:
cd backend && . .venv/bin/activate && pytest -q
cd frontend && npm run build
cd frontend && npm audit --audit-level=moderate
Then implement the phase, verify again, run production-preview browser QA, and update MERCH_AGENT_PLAN.md.
Never let autopilot touch Amazon. Do not publish, submit for review, batch upload, edit live listings, or click dangerous Amazon actions.
```

### Phase 1: Deterministic Local Package Workflow

Status: completed.

Goal: replace fake autopilot samples with deterministic local package generation and zero Amazon interaction.

Completed scope:

- Product template resolver using `config/product_templates.yaml`.
- Marketplace/language resolver using `config/marketplaces.yaml`.
- Fixture candidate model.
- Scoring model.
- Conservative compliance gate.
- Design brief metadata generator.
- Listing generator and validator.
- Package assembler writing artifacts under `data/drafts/`.
- SQLite draft/run records for dashboard.
- Focused backend tests.

Required behavior to preserve:

- `/api/workflows/autopilot/run` creates local packages only.
- `touch_amazon: true` is refused.
- Generated packages include draft JSON, listing fields, validation report, design metadata, and final status.
- No external services are required.

### Phase 2: Artwork Pipeline Contracts and PNG Validation

Status: completed.

Goal: validate artwork readiness locally before any upload workflow exists.

Completed scope:

- Add PNG validation service:
  - dimensions match selected product template
  - transparent background required
  - file size under configured limit
  - placement metadata exists and is valid
  - design not too small
  - design not cropped
- Add fixture PNGs for pass/fail cases.
- Add config-driven thresholds under `config/validation.yaml`.
- Store artwork validation output in package `validation_report.json`.
- Keep design generation metadata-only unless explicitly starting Phase 3.
- Add focused backend tests for each validation rule.

Completed notes:

- `backend/app/services/artwork_validation_service.py` validates final PNG dimensions, transparent background corners, file size, placement metadata, minimum visible bounds, and crop margins with Pillow.
- `config/validation.yaml` now owns artwork thresholds, including max file size, transparency threshold, minimum design ratios, crop margin, and allowed placements.
- Local package assembly writes structured artwork validation output into `validation_report.json`; metadata-only drafts now stop at `ARTWORK_PENDING` with `artwork_pending: true` and `png_valid: false`.
- Draft readiness and manual approval cannot mark a package `READY_FOR_AMAZON_DRAFT` unless artwork validation passes.
- Fixture PNGs cover valid, wrong dimensions, opaque background, too-small design, cropped design, missing PNG, file-size threshold, and placement metadata failures.

Exit criteria:

- A package cannot become `READY_FOR_AMAZON_DRAFT` unless artwork validation passes when final PNG is present.
- Missing PNGs are represented explicitly as "artwork pending" or equivalent, not silently treated as valid.
- Backend tests pass.
- Production-preview browser QA passes for `/`, `/drafts`, a generated draft detail route, `/runs`, and `/settings`.

Copy/paste prompt:

```text
Implement Phase 2 from MERCH_AGENT_PLAN.md: Artwork Pipeline Contracts and PNG Validation.
Do not implement image generation, Amazon dry-run, or live Amazon automation.
Add local PNG validation, fixture images, config thresholds, validation report wiring, and focused tests.
After implementation run backend tests, frontend build, audit, and production-preview browser QA.
```

### Phase 3: Local Artwork Generation and Design Asset Pipeline

Status: completed.

Goal: create real local printable artwork files without Amazon interaction.

Scope:

- Add a deterministic local artwork renderer first, preferably SVG-to-PNG or Pillow-based, so tests stay stable.
- Generate transparent PNGs at the selected product template size.
- Save design source, render metadata, final PNG, and validation result under local package folders.
- Keep image-generation APIs optional and disabled by default.
- Add tests that rendered PNGs pass Phase 2 validation.
- Update dashboard design preview to show real final PNG when present, with fallback to metadata preview.

Exit criteria:

- Autopilot can create reviewable local packages with real transparent PNGs.
- PNG validation gates status.
- No external image generation is required for tests or default operation.

Completed notes:

- Deterministic local artwork rendering is implemented with Pillow.
- The renderer writes source JSON, render metadata, and final transparent PNGs under `data/designs/<draft_id>/`.
- Package assembly validates generated PNGs with the Phase 2 validator before allowing `READY_FOR_AMAZON_DRAFT`.
- The dashboard design preview uses the real final PNG endpoint when present and falls back to metadata preview if the image is unavailable.
- Backend tests cover generated assets, PNG endpoint delivery, and readiness status.

### Phase 4: Research and Candidate Discovery Expansion

Status: completed.

Goal: move beyond fixed candidates while keeping deterministic, auditable behavior.

Completed scope:

- Added local YAML candidate sources and a seedable deterministic generator.
- Added default-off external research adapters behind explicit config flags.
- Recorded candidate source, search phrase, score inputs, accepted/skipped decisions, and rejection reasons.
- Added duplicate niche detection, duplicate keyword-signature detection, and niche cooldown checks.
- Added conservative blocked-term and trademark prechecks before scoring.
- Added fixture-driven tests for deterministic generation, precheck skips, default-off external research, and persisted candidate audit artifacts.
- Added production-mode research evidence enforcement: live research results are saved as local snapshots before scoring, scores can be computed from saved snapshots, and production runs fail clearly when research is unavailable.
- Added saved fixture research snapshots for deterministic tests and config-gated live adapters covering demand, trend, competition, and saturation signals.

Exit criteria:

- Autopilot can generate varied local candidates without external services.
- External research is off by default and never required for tests; fixture snapshots keep research scoring deterministic.
- Every skipped candidate has an auditable reason.
- Production mode cannot score or assemble packages without complete research evidence.

### Phase 5: Compliance, Policy, and Listing Hardening

Status: completed.

Goal: make local review strict enough for real Merch on Demand draft preparation.

Completed scope:

- Expanded deterministic blocked and risky policy dictionaries for brands/trademarks, protected events/leagues, public figures, copyrighted characters, medical claims, tragedy/disaster references, misleading product claims, and ambiguous review phrases.
- Added phrase-level compliance matching with three outcomes: `pass`, `blocked`, and `human_review_required`.
- Kept blocked policy hits out of package assembly while allowing ambiguous packages to assemble only as `HUMAN_REVIEW_REQUIRED` with Amazon draft eligibility disabled.
- Added config-driven listing field constraints, expanded product-type term dictionaries across supported language groups, punctuation checks, marketplace-language copy checks, and reviewed-translation checks for non-English locales.
- Added validation payload fields for human review, compliance block state, listing field lengths, punctuation, marketplace language copy, and translation checks.
- Updated manual approval readiness so human-review-required packages cannot become `READY_FOR_AMAZON_DRAFT`.
- Updated frontend validation/readiness surfaces to show the new local gates.
- Added focused backend tests for allowed, blocked, ambiguous, human-review status, product-term, length, punctuation, marketplace-language, and translation examples.

Exit criteria:

- Risky packages are blocked before draft assembly.
- Ambiguous packages cannot become Amazon-draft-ready without manual approval.
- Listing copy passes configured field constraints for every selected marketplace language section.

Verification:

```bash
cd backend && . .venv/bin/activate && pytest -q
# 40 passed

cd frontend && npm run build
# passed

cd frontend && npm audit --audit-level=moderate
# found 0 vulnerabilities
```

Production-preview browser QA:

```text
Backend:  http://127.0.0.1:8000
Frontend: http://127.0.0.1:3000
Generated draft checked: drf_auto_0541c8bff1
Routes: /, /drafts, /drafts/drf_auto_0541c8bff1, /runs, /settings
Viewports: 1280x720 desktop, 390x844 mobile
```

Result: in-app Browser DOM/console checks passed with nonblank content, no framework overlays, no console warnings/errors, and no mobile horizontal overflow. The local "Run Local Autopilot" button created a local package and reported completion without Amazon interaction. Browser screenshot capture timed out in the in-app Browser runtime, so screenshot evidence was captured with the repo's Playwright dev dependency and saved under `/tmp/merch-agent-phase5-*.png`.

### Phase 6: Dashboard Review, Editing, and Approval Workflow

Status: complete.

Goal: make the app usable for a human operator reviewing real local packages.

Scope:

- Add draft edit persistence for listing fields, selected marketplaces, price, and status.
- Add manual approval workflow with event history.
- Add artifact download/view links.
- Add package diff or change history for listing edits.
- Add bulk local generation controls, but no Amazon batch actions.
- Add better empty/error/loading states for generated package artifacts.

Exit criteria:

- A user can review, edit, reject, archive, and approve a package from the UI.
- UI cannot start Amazon draft assist unless status and validation gates pass.
- Browser QA covers dashboard, draft list, detail, runs, and settings on desktop/mobile.

Implemented:

- Added draft edit persistence through `PATCH /api/drafts/{draft_id}` for listing fields, selected marketplaces, price, and local mutable statuses.
- Direct status edits to `READY_FOR_AMAZON_DRAFT` and `AMAZON_DRAFT_SAVED` are rejected; manual approval remains the only path that recomputes gates and sets Amazon-draft readiness.
- Listing/marketplace/price/status edits append local change history, write draft events, update artifact snapshots, clear Amazon Draft Assist eligibility, and require manual re-approval.
- Added artifact list/download endpoints for final PNG, draft JSON, listing fields, validation report, change history, design source, and render metadata.
- Added dashboard bulk local generation controls that call local autopilot with `touch_amazon: false`; no Amazon batch actions were added.
- Added editable listing UI, review edit controls, artifact links, listing change history, archive action, and clearer empty/error/loading states.
- Hardened the Amazon Draft Assist UI button so it requires `READY_FOR_AMAZON_DRAFT`, backend eligibility, and unsaved Amazon state.
- Added focused backend tests for draft edit persistence, readiness bypass rejection, artifact links, and event/change history.

Verification:

```bash
cd backend && . .venv/bin/activate && pytest -q
# 43 passed

cd frontend && npm run build
# passed

cd frontend && npm audit --audit-level=moderate
# found 0 vulnerabilities
```

Production-preview browser QA:

```text
Backend:  http://127.0.0.1:8000
Frontend: http://127.0.0.1:3000
Generated draft checked: drf_auto_6854427f74
Generated run checked: run_dc13ae778ed0
Routes: /, /drafts, /drafts/drf_auto_6854427f74, /runs, /settings
Viewports: 1280x720 desktop, 390x844 mobile
```

Result: in-app Browser DOM/console checks passed with nonblank content, no framework overlays, no console warnings/errors, and no horizontal overflow on desktop or mobile. The generated draft edit flow was exercised: a listing title edit persisted locally, the draft changed from `READY_FOR_AMAZON_DRAFT` to `LISTING_READY`, draft event/change history appeared, and `Save as Amazon Draft` became disabled. Browser screenshot capture timed out in the in-app Browser runtime, so screenshot evidence was captured with the repo's Playwright dependency and saved under `/tmp/merch-agent-phase6-desktop.png` and `/tmp/merch-agent-phase6-mobile.png`.

### Phase 7: Data Model, Migrations, and Local Operations Hardening

Status: completed on 2026-06-05.

Goal: make backend data durable and maintainable before production use.

Scope:

- Replace JSON-only persistence with explicit tables or repositories for:
  - drafts
  - runs
  - draft events
  - validation results
  - listing groups
  - design artifacts
  - Amazon draft attempts
- Add migrations.
- Add database reset/seed scripts.
- Add backups/export for local packages.
- Add structured logs.
- Add config validation on startup.

Exit criteria:

- Existing data survives migrations.
- Tests cover migrations or repository behavior.
- Local package exports can be restored or inspected without the UI.

Implementation completed:

- Replaced the one-shot SQLite initializer with versioned `schema_migrations`.
- Kept draft JSON payloads as the backward-compatible API source of truth, and added explicit projection tables for listing groups, validation results, design artifacts, and Amazon draft attempts.
- Added repository helpers so seeded drafts, autopilot-created drafts, draft edits, and simulated Amazon draft attempts keep the projection tables current.
- Added structured JSON-line application logging to stdout and `data/logs/backend.jsonl`.
- Added startup config validation for product templates, marketplaces, pricing, listing validation constraints, and candidate research sources.
- Added force-gated local operations:
  - `backend/scripts/reset_database.py`
  - `backend/scripts/seed_database.py`
  - `backend/scripts/export_packages.py`
  - `backend/scripts/restore_export.py`
- Added `data/backups` and `data/exports` directory skeletons; generated backup/export contents are ignored by git.
- Hardened backend tests to use an isolated temporary `MERCH_AGENT_DATA_DIR` so verification no longer mutates the repo's local package database.

Data preservation and reset notes:

- Migrations are additive and backfill new tables from existing `drafts.payload` rows.
- No reset was run on the local repo database during implementation.
- `reset_database.py` and `restore_export.py` refuse to run without `--force`; both create a pre-operation SQLite backup by default unless `--no-backup` is explicitly provided.
- Package exports include a manifest, draft payloads, draft artifacts, and a database snapshot for offline inspection or restore.

Baseline verification before Phase 7 changes:

```bash
cd backend && . .venv/bin/activate && pytest -q
# 43 passed

cd frontend && npm run build
# passed

cd frontend && npm audit --audit-level=moderate
# found 0 vulnerabilities
```

Post-implementation verification:

```bash
cd backend && . .venv/bin/activate && pytest -q
# 50 passed

cd frontend && npm run build
# passed

cd frontend && npm audit --audit-level=moderate
# found 0 vulnerabilities

cd backend && . .venv/bin/activate && python scripts/reset_database.py
# refused without --force

cd backend && . .venv/bin/activate && python scripts/seed_database.py
# seeded=true

cd backend && . .venv/bin/activate && python scripts/export_packages.py --draft-id drf_20260605_0001
# export created under data/exports
```

Production-preview browser QA:

```text
Backend:  http://127.0.0.1:8000
Frontend: http://127.0.0.1:3000
Routes: /, /drafts, /runs, /settings
Viewports: 1280x720 desktop, 390x844 mobile
Interaction: dashboard search for "garden" filtered the draft queue from 98 total to 4 shown.
```

Result: in-app Browser DOM/console checks passed with meaningful rendered content, no framework overlays, no console warnings/errors, and no horizontal overflow on desktop or mobile. Browser screenshot capture timed out in this runtime, so screenshot evidence was captured with the repo's Playwright dependency and saved under `/tmp/merch-agent-phase7-desktop.png` and `/tmp/merch-agent-phase7-mobile.png`.

### Phase 8: Amazon Draft Assist Dry Run

Status: completed on 2026-06-05.

Goal: prove browser automation safety without touching a live Amazon draft.

Hard gate before starting:

- Phases 2 through 7 must be complete.
- User must explicitly request Amazon dry-run work.

Scope:

- Implement Playwright dry-run operator with a controlled browser profile.
- Use selector map from `config/amazon_upload_ui.yaml`.
- Add draft lock before starting.
- Capture screenshots at each dry-run step.
- Add dangerous-action blocker tests for labels including:
  - Publish
  - Submit
  - Submit for review
  - Make live
  - Update live listing
  - Create product
- Add UI confirmation modal with exact safety copy.
- Never click live Amazon actions.

Exit criteria:

- Dry-run proves the operator would fill one package only.
- Dangerous action blocker tests pass.
- No live Amazon draft is saved in this phase.

Implementation completed:

- Added a config-driven Amazon upload selector map, dry-run controlled browser profile path, dry-run screenshot path, dangerous action labels, and safe action labels in `config/amazon_upload_ui.yaml`.
- Replaced the placeholder browser operator with shared dangerous-action safety helpers and a Playwright dry-run runner under `agent/merch_agent/browser/`.
- The dry-run runner launches a persistent controlled Playwright browser profile, opens a local mock Merch create-product page, fills one selected package through configured selectors, checks warnings, verifies the Save Draft button label, captures 10 screenshots, and stops before clicking Save Draft.
- Updated the backend Amazon Draft Assist endpoint to run dry-run mode only:
  - rejects unready, saved, publish-enabled, locked, marketplace-missing, or non-positive-royalty drafts
  - locks the draft as `AMAZON_DRAFT_IN_PROGRESS` before the run
  - records dry-run started/completed events
  - writes an `amazon_draft_attempts` row with mode `playwright_dry_run`
  - restores the draft to `READY_FOR_AMAZON_DRAFT`
  - keeps `amazon_draft.saved` false
- Added focused dangerous-action blocker tests for `Publish`, `Submit`, `Submit for review`, `Make live`, `Update live listing`, and `Create product`.
- Added endpoint tests proving dry-run completion records screenshots and attempt metadata while leaving the Amazon saved flag false.
- Replaced the browser `confirm()` with a UI confirmation modal containing the required safety copy:

```text
You are about to create an Amazon Merch draft for:

Draft: Funny Fly Fishing Grandpa
Product: Standard T-Shirt
Marketplaces: .com, .co.uk
Price: $19.99
Action: Save Draft only

This will open/control the browser.
The operator will never click Publish.
```

Phase 8 behavior note:

- The modal includes an additional dry-run note outside the required safety copy.
- The backend does not navigate to Amazon and does not save a live Amazon draft.
- The dry-run stops before clicking Save Draft, even on the local mock page.

Baseline verification before Phase 8 changes:

```bash
cd backend && . .venv/bin/activate && pytest -q
# 50 passed

cd frontend && npm run build
# passed

cd frontend && npm audit --audit-level=moderate
# found 0 vulnerabilities
```

Post-implementation verification:

```bash
cd backend && . .venv/bin/activate && pytest -q
# 54 passed

cd frontend && npm run build
# passed

cd frontend && npm audit --audit-level=moderate
# found 0 vulnerabilities
```

Production-preview browser QA:

```text
Backend:  http://127.0.0.1:8000
Frontend: http://127.0.0.1:3000
Draft checked: drf_auto_02fc664bda
Flow: draft detail -> Amazon Draft Assist Dry Run -> confirmation modal -> Start Amazon Draft Assist -> local dry-run completion
Viewports: 1280x720 desktop, 390x844 mobile
Screenshot evidence: /tmp/merch-agent-phase8-desktop.png, /tmp/merch-agent-phase8-modal.png, /tmp/merch-agent-phase8-mobile.png
```

Result: in-app Browser checks passed with meaningful rendered content, no framework overlays, no console warnings/errors, no mobile horizontal overflow, exact confirmation modal safety copy present, and UI-triggered dry-run completion visible. Backend state after the UI run remained `READY_FOR_AMAZON_DRAFT`, `amazon_draft.saved` stayed false, `amazon_draft.locked` stayed false after completion, and the dry-run metadata recorded 10 screenshots.

### Phase 9: Controlled Live Amazon Draft Save

Status: completed on 2026-06-05.

Goal: save exactly one Amazon draft after explicit user action.

Hard gate before starting:

- Phase 8 must pass.
- User must explicitly request controlled live draft save.
- The selected package must be `READY_FOR_AMAZON_DRAFT`.

Scope:

- Manual UI trigger only.
- One package per run.
- Browser profile and session are visible/controlled.
- Fill selected product, artwork, price, marketplaces, and listing fields.
- Select "No, I'll provide my own translations" where applicable.
- Save as draft only.
- Capture screenshots before and after save.
- Update local status to `AMAZON_DRAFT_SAVED` or `AMAZON_DRAFT_FAILED`.

Non-negotiable prohibitions:

- Never publish.
- Never submit for review.
- Never batch upload.
- Never edit live listings.
- Never click dangerous Amazon actions.

Exit criteria:

- One controlled live draft save succeeds or fails with screenshots and logs.
- Local status and event history are accurate.
- User still manually reviews/publishes inside Merch.

Implementation completed:

- Kept Phase 8 dry-run available as explicit regression mode while adding `controlled_live_save` mode to `POST /api/drafts/{draftId}/amazon-draft`.
- Added request-level live gates requiring:
  - `manual_ui_triggered`
  - `save_draft_only_confirmed`
  - `visible_browser_confirmed`
  - `phase8_safety_confirmed`
- Added one-package guard requiring exactly one selected product and at least one selected marketplace before any Amazon Draft Assist mode can lock a draft.
- Added a controlled live Playwright operator at `agent/merch_agent/browser/amazon_draft_live_save.mjs` that:
  - launches a persistent visible browser profile with `headless: false`
  - opens the configured Merch create-product URL
  - uploads the final PNG
  - selects the configured product, marketplaces, price, own-translation option, and listing fields
  - stops on warning text
  - verifies the Save Draft button label is safe before clicking
  - captures `before-save-draft` and `after-save-draft` screenshots
  - returns a structured report with `touch_amazon: true`, `save_draft_clicked: true`, and `publish_allowed: false`
- Added live-save status transitions:
  - success marks the draft `AMAZON_DRAFT_SAVED`, clears the lock, sets `amazon_draft.saved = true`, stores screenshot paths, and records a `controlled_live_save` attempt
  - failure marks the draft `AMAZON_DRAFT_FAILED`, clears the lock, keeps `amazon_draft.saved = false`, stores failure metadata, and records a failed attempt
- Updated the dashboard button and confirmation modal from Phase 8 dry-run copy to Phase 9 controlled live save copy.
- Added config validation for live mode requiring visible browser, one package per run, manual UI trigger only, Save Draft only, and a full live selector map.

Selector confirmation note:

- Live selectors are config-driven under `config/amazon_upload_ui.yaml`.
- The live operator fails closed if a configured selector is missing, resolves to warnings, or resolves the Save Draft action to an unsafe label.
- Actual Amazon DOM selectors still need to be confirmed in the controlled browser session before a real live save attempt; screenshots alone are not treated as selector proof.

Baseline verification before Phase 9 changes:

```bash
cd backend && . .venv/bin/activate && pytest -q
# 54 passed

cd frontend && npm run build
# passed

cd frontend && npm audit --audit-level=moderate
# found 0 vulnerabilities
```

Post-implementation verification:

```bash
cd backend && . .venv/bin/activate && pytest -q
# 58 passed

cd frontend && npm run build
# passed

cd frontend && npm audit --audit-level=moderate
# found 0 vulnerabilities
```

Additional check:

```bash
cd frontend && npm run typecheck
# blocked: Nuxt could not find a root frontend/tsconfig.json
```

Production-preview browser QA:

```text
Backend:  http://127.0.0.1:8000
Frontend: http://127.0.0.1:3000
Draft checked: drf_auto_02fc664bda
Flow: draft detail -> Save as Amazon Draft -> confirmation modal only
Live save was not started during QA.
Viewports: 1280x720 desktop, 390x844 mobile
Screenshot evidence: /tmp/merch-agent-phase9-modal-desktop.png, /tmp/merch-agent-phase9-modal-mobile.png
```

Result: in-app Browser checks passed with meaningful rendered content, enabled Amazon Draft Assist button on a `READY_FOR_AMAZON_DRAFT` package, exact save-draft-only confirmation copy present, no console warnings/errors, and no mobile horizontal overflow. The Start Amazon Draft Assist action was intentionally not clicked during QA because it is the guarded live Amazon side-effect trigger.

### Phase 10: Scheduling and Autopilot Operations

Status: completed.

Goal: support unattended local package generation while preserving Amazon separation.

Scope:

- Add local scheduler for autopilot package generation.
- Add run limits, cooldowns, stop switches, and disk usage limits.
- Add notification or dashboard indicators for completed local packages.
- Add config for max packages per run/day.
- Ensure scheduled jobs never invoke Amazon Draft Assist.

Exit criteria:

- Scheduled autopilot produces local packages only.
- Stop switch halts queued/running local jobs.
- Run history clearly distinguishes scheduled vs manual runs.

Completed after Phase 10:

- Added a local scheduler status/tick service and in-process scheduler loop for scheduled autopilot generation. Scheduled ticks always construct `AutopilotRequest` with `touch_amazon=false` and use the existing local package workflow only.
- Added config-backed operations settings for scheduler enablement, stop switch, interval minutes, cooldown minutes, scheduled packages per run, max packages per run, max packages per day, disk usage limit, default product, marketplace exploration, and production mode.
- Added run-history distinction with `scheduled_autopilot` mode and run logs that state Amazon Draft Assist is unavailable to the workflow.
- Added scheduler gates for disabled scheduler, stop switch, concurrent job lock, disk usage limit, zero package allowance, daily package limit, and cooldown.
- Added dashboard indicators and controls on Runs, Settings, and the main dashboard for scheduler state, stop/resume, package counts, disk usage, cooldown, and scheduled local package generation.
- Added focused Phase 10 tests proving scheduled jobs create local `READY_FOR_AMAZON_DRAFT` packages only, do not create Amazon Draft Assist attempt records, and honor stop switch, daily limit, disk limit, cooldown, and per-run cap.

Baseline verification before Phase 10 changes:

```bash
cd backend && . .venv/bin/activate && pytest -q
# 58 passed in 8.53s

cd frontend && npm run build
# passed

cd frontend && npm audit --audit-level=moderate
# found 0 vulnerabilities
```

Post-implementation verification:

```bash
cd backend && . .venv/bin/activate && pytest -q
# 63 passed in 10.31s

cd frontend && npm run build
# passed

cd frontend && npm audit --audit-level=moderate
# found 0 vulnerabilities
```

Production-preview browser QA:

```bash
cd backend && . .venv/bin/activate && uvicorn app.main:app --host 127.0.0.1 --port 8000
cd frontend && NUXT_PUBLIC_API_BASE=http://127.0.0.1:8000 HOST=127.0.0.1 PORT=3000 node .output/server/index.mjs
```

Routes checked: `/runs`, `/`, `/settings`
Viewports: 1280x720 desktop, 390x844 mobile

Result: in-app Browser checks passed with meaningful rendered content, no framework overlays, no console warnings/errors, and no mobile horizontal overflow. The desktop Runs interaction clicked "Run Due Scheduled Job" and created `run_8f12ced75906` in `scheduled_autopilot` mode with one local `READY_FOR_AMAZON_DRAFT` package and the message "No Amazon interaction occurred." A final desktop/mobile pass confirmed interval/cooldown scheduler indicators render correctly. Local database QA confirmed the latest Amazon Draft Assist attempt remained `job_cd8d7e6a1855` from `2026-06-05 08:07:16`, before the scheduled QA run at `2026-06-05 08:49:50`.

### Phase 11: Security, Access Control, and Deployment Readiness

Status: pending.

Goal: make the app safe to run beyond a local development shell.

Scope:

- Add environment config for production.
- Add authentication if exposed beyond localhost.
- Add CSRF/CORS hardening.
- Add secrets handling.
- Add dependency audit process.
- Add API input validation and rate limits where needed.
- Add deployment scripts or Docker setup.
- Add health checks.
- Add log retention.

Exit criteria:

- App can run from a documented production-like command or container.
- Secrets are not committed.
- Localhost-only assumptions are documented or removed.
- Basic security review passes.

### Phase 12: Beta Runbook and Production Acceptance

Status: pending.

Goal: define when the system is production-ready to use.

Scope:

- Create operator runbook:
  - start/stop services
  - generate local packages
  - review and approve packages
  - run Amazon Draft Assist
  - recover from failed draft attempts
  - backup/export data
- Add production acceptance checklist.
- Run a beta cycle:
  - generate packages locally
  - review and reject/approve
  - save one draft manually through controlled assist
  - verify logs/screenshots/status history
- Document known limitations.

Production-ready criteria:

- All tests pass.
- Frontend production build and audit pass.
- Production-preview browser QA passes on desktop and mobile.
- Autopilot cannot touch Amazon by design and by test.
- Amazon Draft Assist is manual, one draft at a time, save-draft-only, and guarded by tests.
- Dangerous Amazon actions are blocked by tests and runtime checks.
- Local package artifacts are complete and restorable.
- Operator runbook is accurate.
- A human remains responsible for final Amazon review and publishing.

## Copy/Paste Prompt For Next Session

Use this prompt in a new Codex session from `/Users/ghassenbrg/git/merch-agent`:

```text
We are continuing the Merch Agent project in /Users/ghassenbrg/git/merch-agent.

Read MERCH_AGENT_PLAN.md first, especially:
- "Immediate Next Session Recommendation"
- "Production Readiness Roadmap"
- the next incomplete phase

Current state:
- FastAPI backend has SQLite seed data, draft APIs, workflow APIs, validation, Amazon Draft Assist guardrails, run history APIs, config/settings APIs, draft event APIs, deterministic local package workflow, local artwork PNG validation contracts, deterministic local PNG rendering, Phase 4 candidate discovery/auditing, production-mode research snapshot enforcement, Phase 5 compliance/listing hardening, Phase 10 scheduler/autopilot operations, and focused tests.
- Nuxt 3 frontend has the redesigned dashboard UI plus real Drafts, draft detail, Runs, and Settings pages backed by the API; draft detail shows the real generated final PNG when present, and Runs/Settings expose scheduler operations indicators and controls.
- Production frontend preview should be used, not Nuxt dev mode, because dev mode previously had a Vite IPC socket issue on this machine.
- Generated build/runtime artifacts are ignored.

Hard safety constraints:
- Autopilot must never touch Amazon.
- Scheduled autopilot must never invoke Amazon Draft Assist.
- Amazon Draft Assist remains manual, one draft at a time, save draft only, and guarded by dry-run/live-save safety checks.
- Never publish, submit for review, batch upload, edit live listings, or click dangerous Amazon actions.
- Do not expand Amazon browser automation in this session.

First verify:
cd backend && . .venv/bin/activate && pytest -q
cd frontend && npm run build
cd frontend && npm audit --audit-level=moderate

Next milestone:
Implement Phase 11 from the Production Readiness Roadmap: Security, Access Control, and Deployment Readiness.

Implement in this order:
1. Add environment config for local vs production mode.
2. Add localhost-safe default access controls and document exposure risks.
3. Harden CORS/CSRF behavior for any non-localhost deployment path.
4. Add secret/config handling for browser profiles and future external integrations.
5. Add operation audit checks for scheduler and Amazon Draft Assist boundaries.
6. Update the runbook and deployment notes.

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

Do not expand Amazon dry-run or live automation work unless explicitly instructed.
```
