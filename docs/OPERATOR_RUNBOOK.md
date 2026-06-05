# Merch Agent Operator Runbook

This runbook is for the current local-first Merch Agent beta. It preserves the core boundary:

```text
Autopilot creates local packages only.
Amazon Draft Assist is a manual one-draft action.
Publishing is always a human Amazon-side decision.
```

## Safety Boundaries

- Do not publish, submit for review, batch upload, or edit live listings with Merch Agent.
- Do not run Amazon Draft Assist from a scheduler, script loop, or bulk action.
- Use Amazon Draft Assist only from the dashboard for one `READY_FOR_AMAZON_DRAFT` package.
- Use the visible controlled browser session for live draft save attempts.
- Stop immediately if Amazon shows warnings, unexpected selectors, account prompts, negative royalty, or a button that is not clearly `Save Draft` or `Save as Draft`.
- A human must review the Amazon draft manually before any later publish action inside Merch.

## Daily Startup

From the repo root:

```bash
cd /Users/ghassenbrg/git/merch-agent
```

Run the verification set before operating a beta session:

```bash
cd backend && . .venv/bin/activate && pytest -q
cd ../frontend && npm run build
cd .. && ./scripts/audit_dependencies.sh
```

Start a production-like authenticated preview:

```bash
export MERCH_AGENT_API_TOKEN="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
export MERCH_AGENT_ENV=production
export MERCH_AGENT_EXPOSED=false
export MERCH_AGENT_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
export MERCH_AGENT_TRUSTED_HOSTS=localhost,127.0.0.1,::1
export NUXT_PUBLIC_API_TOKEN="$MERCH_AGENT_API_TOKEN"
./scripts/production_preview.sh
```

Open:

```text
http://127.0.0.1:3000
```

Health checks:

```bash
curl -H "Authorization: Bearer $MERCH_AGENT_API_TOKEN" http://127.0.0.1:8000/health/live
curl -H "Authorization: Bearer $MERCH_AGENT_API_TOKEN" http://127.0.0.1:8000/health/ready
```

## Stop Services

If services were started with `scripts/production_preview.sh`, press `Ctrl-C` in that terminal. The script traps exit and stops the backend and frontend child processes.

If a service remains running, identify the port owner and stop only that process:

```bash
lsof -nP -iTCP:8000 -sTCP:LISTEN
lsof -nP -iTCP:3000 -sTCP:LISTEN
```

## Generate Local Packages

Preferred UI flow:

1. Open the dashboard at `/`.
2. Click the local autopilot package generation control.
3. Confirm the completion message says no Amazon interaction occurred.
4. Open `/runs` and inspect the latest run logs.
5. Open `/drafts` and review the newly created packages.

API smoke flow:

```bash
curl -sS \
  -H "Authorization: Bearer $MERCH_AGENT_API_TOKEN" \
  -H "Content-Type: application/json" \
  -X POST http://127.0.0.1:8000/api/workflows/autopilot/run \
  -d '{"count":1,"default_product":"standard_tshirt","explore_marketplaces":true,"touch_amazon":false}'
```

Expected result:

- `status` is `COMPLETED`.
- `createdDraftIds` contains local draft ids.
- response message states no Amazon interaction occurred.

Forbidden autopilot request:

```bash
curl -sS \
  -H "Authorization: Bearer $MERCH_AGENT_API_TOKEN" \
  -H "Content-Type: application/json" \
  -X POST http://127.0.0.1:8000/api/workflows/autopilot/run \
  -d '{"count":1,"touch_amazon":true}'
```

Expected result: the run is refused or failed with the message that autopilot cannot touch Amazon.

## Review And Approve Packages

For every package:

1. Open `/drafts`.
2. Filter or choose a draft.
3. Open the draft detail page.
4. Check final PNG preview and artifact links.
5. Check score, compliance, trademark/policy precheck, listing validation, price, royalty, selected products, selected marketplaces, and translation mode.
6. Confirm listing copy contains no product-type terms such as shirt, t-shirt, hoodie, mug, tote bag, phone case, tumbler, water bottle, hat, or visor.
7. Confirm every selected marketplace has reviewed copy for its language group.
8. Edit listing, marketplace, or price fields if needed.
9. Re-approve only after edits pass validation.
10. Reject or archive packages that are not usable.

The `Save as Amazon Draft` button must stay disabled unless the draft status is `READY_FOR_AMAZON_DRAFT`, validation gates pass, Amazon draft is unsaved, and exactly one selected product is present.

## Amazon Draft Assist

Use this only for a single human-selected draft. Do not use it as part of the beta cycle unless the operator has explicitly authorized controlled Amazon interaction for that exact package.

Preflight:

- Backend and frontend are running in production-like preview with bearer auth.
- The selected draft is `READY_FOR_AMAZON_DRAFT`.
- The draft has exactly one selected product.
- At least one marketplace is selected.
- Royalty is positive.
- Final PNG and artifacts exist.
- The operator is logged into Merch in the controlled browser profile.
- The operator is watching the visible browser.
- The operator has agreed to Save Draft only.

Dashboard flow:

1. Open the draft detail page.
2. Click `Save as Amazon Draft`.
3. Read the modal and verify:
   - draft title
   - product
   - marketplaces
   - price
   - action is Save Draft only
   - browser control is expected
   - operator will never click Publish
4. Start Amazon Draft Assist only after the package-specific confirmation.
5. Watch the browser.
6. Stop if warnings, missing selectors, login prompts, or unsafe action labels appear.
7. After completion, verify the draft status is `AMAZON_DRAFT_SAVED` or `AMAZON_DRAFT_FAILED`.
8. Inspect event history, Amazon attempt metadata, and screenshot paths.

Never click or approve any flow that says Publish, Submit, Submit for review, Make live, Update live listing, or Create product.

## Recovery Procedures

### Backend Or Frontend Fails To Start

1. Confirm required env vars are set in production-like mode:

```bash
env | rg 'MERCH_AGENT_|NUXT_PUBLIC_API_'
```

2. Run readiness:

```bash
curl -i -H "Authorization: Bearer $MERCH_AGENT_API_TOKEN" http://127.0.0.1:8000/health/ready
```

3. Rebuild frontend if `.output` is stale:

```bash
cd frontend && npm run build
```

4. Run backend tests before continuing:

```bash
cd backend && . .venv/bin/activate && pytest -q
```

### Local Package Generation Fails

1. Open `/runs` and inspect the failed run.
2. Check backend logs:

```bash
tail -n 100 data/logs/backend.jsonl
```

3. Check candidate audit logs under `data/logs/*_candidate_audit.json`.
4. Fix config, disk space, stop switch, or validation inputs.
5. Re-run local autopilot with `touch_amazon:false`.

### Draft Is Not Ready

1. Open the draft detail page.
2. Review validation and listing warnings.
3. Use regenerate listing, regenerate design, edit listing, reject, archive, or approve as appropriate.
4. Do not force `READY_FOR_AMAZON_DRAFT` directly in the database. Manual approval is the intended readiness path.

### Amazon Draft Assist Fails

1. Do not retry immediately.
2. Confirm whether Amazon saved a draft in the visible browser.
3. Open the draft event history and Amazon attempt metadata.
4. Inspect screenshots under `data/screenshots/`.
5. If the draft is `AMAZON_DRAFT_FAILED`, fix the cause and re-approve or regenerate as needed before another attempt.
6. If an operator manually finds that Amazon saved the draft even though Merch Agent recorded a failure, archive local evidence and update the package status only after a human audit.

### Draft Is Stuck In Progress

This should be rare because the backend clears locks on handled failures. Use this only after confirming there is no running browser process for the job and no Amazon draft was saved.

1. Export all data first:

```bash
cd backend && . .venv/bin/activate && python scripts/export_packages.py
```

2. Back up the database:

```bash
cp data/merch_agent.sqlite3 "data/backups/merch_agent_manual_recovery_$(date -u +%Y%m%dT%H%M%SZ).sqlite3"
```

3. Prefer code-level recovery or a focused admin script over ad hoc SQL. If a direct database correction is unavoidable, record the reason in the incident notes and verify with backend tests afterward.

### Reset Local Demo Data

Reset is destructive and creates a backup by default:

```bash
cd backend
. .venv/bin/activate
python scripts/reset_database.py --force
```

Seed without resetting:

```bash
cd backend
. .venv/bin/activate
python scripts/seed_database.py
```

## Backup, Export, And Restore

Create an export of all local packages:

```bash
cd backend
. .venv/bin/activate
python scripts/export_packages.py
```

Export one draft:

```bash
cd backend
. .venv/bin/activate
python scripts/export_packages.py --draft-id drf_auto_example
```

Exports are written under `data/exports/` and include:

- `manifest.json`
- SQLite database snapshot when present
- draft payloads
- package artifacts under each draft folder

Restore an export:

```bash
cd backend
. .venv/bin/activate
python scripts/restore_export.py data/exports/<export>.tar.gz --force
```

Restore creates a pre-restore database backup by default. Use `--no-backup` only when data loss is intentional.

## Logs And Evidence

Primary evidence locations:

- `data/logs/backend.jsonl`
- `data/logs/<run_id>_candidate_audit.json`
- `data/drafts/<draft_id>/`
- `data/designs/<draft_id>/`
- `data/screenshots/amazon-draft-dry-run/`
- `data/screenshots/amazon-draft-live/`
- `data/exports/`
- `draft_events` and `amazon_draft_attempts` in SQLite

For every beta cycle, retain:

- run id
- generated draft ids
- rejected/approved draft ids
- Amazon Draft Assist job id if explicitly run
- screenshot paths
- export path
- verification command results

