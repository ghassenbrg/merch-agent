# Merch Agent Production Acceptance

This checklist defines beta acceptance for the current local-first implementation. It does not authorize publishing automation.

## Production Acceptance Checklist

Before a beta session is accepted:

- [ ] Backend tests pass with `cd backend && . .venv/bin/activate && pytest -q`.
- [ ] Frontend production build passes with `cd frontend && npm run build`.
- [ ] Frontend typecheck passes with `cd frontend && npm run typecheck`.
- [ ] Dependency audit passes with `./scripts/audit_dependencies.sh`.
- [ ] Production-preview browser QA passes on desktop and mobile for `/`, `/drafts`, one generated `/drafts/<draft_id>`, `/runs`, and `/settings`.
- [ ] `/health/live` and `/health/ready` pass in production-like mode with bearer auth.
- [ ] Unauthenticated API access is rejected in production-like mode.
- [ ] Local autopilot can generate packages with `touch_amazon:false`.
- [ ] An attempted autopilot request with `touch_amazon:true` is refused.
- [ ] Scheduled autopilot creates local packages only and records no Amazon Draft Assist attempt.
- [ ] A generated package contains draft JSON, listing fields, validation report, design metadata/source, final PNG, run logs, and event history.
- [ ] Package export can be created and inspected.
- [ ] Amazon Draft Assist remains disabled unless the draft is `READY_FOR_AMAZON_DRAFT`.
- [ ] Amazon Draft Assist requires manual UI confirmation and one selected product.
- [ ] Dangerous Amazon actions are blocked by backend/runtime helpers and tests.
- [ ] The operator has read `docs/OPERATOR_RUNBOOK.md`.
- [ ] A human operator remains responsible for final Amazon review and publishing.

## Beta Cycle Checklist

Use one row per beta cycle in local notes or an issue tracker.

```text
Date:
Operator:
Commit or branch:
Production-preview token rotated after session: yes/no
Backend tests:
Frontend build:
Frontend typecheck:
Audit:
Browser QA desktop:
Browser QA mobile:
Export path:
```

Cycle steps:

- [ ] Start production-like preview with `MERCH_AGENT_API_TOKEN`.
- [ ] Verify health and readiness.
- [ ] Generate one to five local packages from the dashboard or API.
- [ ] Confirm run logs say no Amazon interaction occurred.
- [ ] Review every generated package.
- [ ] Reject at least one unsuitable package when available, or document why every package was acceptable.
- [ ] Edit one listing or marketplace selection when useful and verify the draft returns to a non-ready status until re-approved.
- [ ] Approve only packages whose validation gates pass.
- [ ] Export local packages.
- [ ] Verify generated artifacts are present in the export.
- [ ] Run desktop QA on `/`, `/drafts`, generated draft detail, `/runs`, and `/settings`.
- [ ] Run mobile QA on the same routes.
- [ ] Do not run controlled live Amazon Draft Assist unless explicitly authorized for one specific package.
- [ ] If controlled live Amazon Draft Assist is authorized, save one draft only, verify before/after screenshots, status history, and `AMAZON_DRAFT_SAVED`.
- [ ] If controlled live Amazon Draft Assist is not authorized, record `live_save_not_run` and keep acceptance limited to local-package production readiness.
- [ ] Stop services.

## Known Limitations

- Final publishing is not automated and must remain manual inside Amazon Merch.
- Actual Amazon DOM selectors can change; live selector confirmation must happen in the visible controlled browser before relying on a live save attempt.
- Production research adapters are config-gated and may fail closed when evidence is unavailable.
- The app is local-first and SQLite-backed; multi-user concurrent operation is not a supported production mode.
- Write rate limits are in-memory and reset on backend restart.
- Browser profiles, screenshots, logs, exports, and SQLite data are local runtime data and must be backed up outside the repo for durable retention.
- The Nuxt dev server has been unreliable on this local Node 24/macOS environment; use production build/preview.
- Recovery from an interrupted Amazon Draft Assist job may require manual evidence review before status correction.
- No Amazon live operation should be run by unattended scripts, scheduler ticks, or batch flows.

## Final Safety Criteria

The system is acceptable for beta production use only when all of these remain true:

- Autopilot cannot touch Amazon by design, UI, and test coverage.
- Scheduled autopilot cannot invoke Amazon Draft Assist.
- Amazon Draft Assist is manual, one draft at a time, save-draft-only, and guarded by explicit confirmations.
- Dangerous labels including Publish, Submit, Submit for review, Make live, Update live listing, and Create product are blocked.
- Draft readiness requires valid PNG, transparent background, correct resolution, file size limits, placement checks, compliance precheck, listing validation, marketplace copy, price config, and positive royalty.
- Product-type words are blocked from listing fields.
- Auto-translation is not used; own translations are required.
- Warnings or missing required Amazon fields stop the operator.
- Every package has local artifacts and can be exported.
- Tests, build, typecheck, audit, and production-preview browser QA pass.
- A human operator performs final Amazon review and any later publish action.

## Current Acceptance Status

Status is tracked in `MERCH_AGENT_PLAN.md` under Phase 12. Update that section after each beta cycle with exact verification results, generated draft id, browser QA result, export path, and whether controlled live Amazon Draft Assist was run.
