# Beginner How-To: Use Merch Agent Safely

This guide is for a first local beta session. Merch Agent creates local Merch by Amazon review packages. It must not publish products, submit products for review, or run Amazon actions in bulk.

## Current Readiness

As of June 5, 2026, the app is ready for local beta production operation when you follow `docs/OPERATOR_RUNBOOK.md` and `docs/PRODUCTION_ACCEPTANCE.md`.

Use it with these boundaries:

- Autopilot creates local packages only.
- Scheduled autopilot creates local packages only.
- Amazon Draft Assist is manual, one package at a time, and save-draft-only.
- A human must review the Amazon draft and decide any later publish action inside Amazon Merch.

Items that are not finalized for broader production:

- Live research adapters are available for explicit live-research runs, but external source availability can still fail closed. Monitor run logs and snapshots before relying on the output.
- Amazon page selectors can change, so live Amazon Draft Assist needs visible browser confirmation for each beta cycle.
- This is local-first SQLite operation, not a multi-user hosted service.
- Runtime data under `data/` needs your own backup process.

## 1. Open The Project

```bash
cd /Users/ghassenbrg/git/merch-agent
```

## 2. Install Backend Dependencies

Fast path:

```bash
./scripts/ready.sh
```

That one command installs backend and frontend dependencies, builds the frontend, creates a temporary API token, and starts the app at `http://127.0.0.1:3000`.

Use this when you want it to run the safety checks before starting:

```bash
MERCH_AGENT_RUN_CHECKS=1 ./scripts/ready.sh
```

Manual backend setup:

```bash
cd /Users/ghassenbrg/git/merch-agent/backend
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

## 3. Install Frontend Dependencies

```bash
cd /Users/ghassenbrg/git/merch-agent/frontend
npm install
npm run build
```

## 4. Run The Safety Checks

Run these before a beta session:

```bash
cd /Users/ghassenbrg/git/merch-agent/backend
. .venv/bin/activate
pytest -q
```

```bash
cd /Users/ghassenbrg/git/merch-agent/frontend
npm run build
npm run typecheck
```

```bash
cd /Users/ghassenbrg/git/merch-agent
./scripts/audit_dependencies.sh
```

Do not continue if tests, build, typecheck, or audit fail.

## 5. Start Production-Like Preview

Use production-like preview even for local beta use because it turns on bearer-token protection.

```bash
cd /Users/ghassenbrg/git/merch-agent
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

Stop later with `Ctrl-C` in the terminal running `production_preview.sh`.

## 6. Check The Backend Is Protected

Open another terminal and run:

```bash
curl -i http://127.0.0.1:8000/api/drafts
```

Expected result: `401 Unauthorized`.

Then run:

```bash
curl -sS \
  -H "Authorization: Bearer $MERCH_AGENT_API_TOKEN" \
  http://127.0.0.1:8000/health/ready
```

Expected result: `"status":"ok"` with `auth_required` and `api_token_configured` set to `true`.

## 7. Generate Local Packages

In the dashboard:

1. Open `/`.
2. Choose the number of packages.
3. Leave `Live research` off for deterministic local generation, or turn it on to collect web evidence before scoring.
4. Click `Generate Local Packages`.
5. Confirm the message says no Amazon interaction occurred.
6. Open `/runs` and inspect the latest run logs.

API alternative:

```bash
curl -sS \
  -H "Authorization: Bearer $MERCH_AGENT_API_TOKEN" \
  -H "Content-Type: application/json" \
  -X POST http://127.0.0.1:8000/api/workflows/autopilot/run \
  -d '{"count":1,"default_product":"standard_tshirt","explore_marketplaces":true,"touch_amazon":false}'
```

Never set `touch_amazon` to `true`. The backend should refuse it, but the correct workflow is to keep local autopilot local.

To run the same API flow with live research snapshots:

```bash
curl -sS \
  -H "Authorization: Bearer $MERCH_AGENT_API_TOKEN" \
  -H "Content-Type: application/json" \
  -X POST http://127.0.0.1:8000/api/workflows/autopilot/run \
  -d '{"count":1,"default_product":"standard_tshirt","explore_marketplaces":true,"touch_amazon":false,"production_mode":true}'
```

Expected result when external sources respond: a completed run whose draft research artifact has `score_source` set to `live_research_snapshot` and a saved snapshot path under `data/research_snapshots/`.
Expected result when external sources fail: the run fails closed and no Amazon interaction occurs.

## 8. Review A Draft

In the dashboard:

1. Open `/drafts`.
2. Select a draft.
3. Open the draft detail page.
4. Check the final PNG preview.
5. Check validation, policy precheck, product terms, marketplace copy, price, and royalty.
6. Use `Review Edits` for marketplace, price, or status changes.
7. Use `Listing Editor` to edit listing copy.
8. Click `Manual Approve` only after every blocking check is clean.
9. Reject or archive packages you do not want to use.

The draft must be `READY_FOR_AMAZON_DRAFT` before Amazon Draft Assist is available.

## 9. Practice Amazon Draft Assist Without Touching Amazon

Use dry-run mode first. It opens a local mock page and does not click Save Draft.

Replace `<draft_id>` with a ready draft id:

```bash
curl -sS \
  -H "Authorization: Bearer $MERCH_AGENT_API_TOKEN" \
  -H "Content-Type: application/json" \
  -X POST http://127.0.0.1:8000/api/drafts/<draft_id>/amazon-draft \
  -d '{"mode":"dry_run"}'
```

Expected result: `AMAZON_DRAFT_DRY_RUN_COMPLETED`.

## 10. Optional Live Amazon Draft Save

Only do this when you intentionally want to save one Amazon Merch draft.

Before clicking the draft detail `Amazon Draft Assist` modal:

- Confirm you are logged into Amazon Merch in the controlled browser profile.
- Confirm the draft is `READY_FOR_AMAZON_DRAFT`.
- Confirm exactly one product is selected.
- Confirm selected marketplaces and price are correct.
- Watch the visible browser.
- Stop immediately if Amazon shows warnings, login prompts, missing fields, negative royalty, or any button that says Publish, Submit, Submit for review, Make live, Update live listing, or Create product.

The allowed live action is Save Draft only. Publishing remains manual inside Amazon Merch later.

## 11. Export Packages

```bash
cd /Users/ghassenbrg/git/merch-agent/backend
. .venv/bin/activate
python scripts/export_packages.py
```

Exports are written under:

```text
data/exports/
```

Keep exports, screenshots, logs, and the SQLite database backed up outside the repo.

## 12. Daily Beta Checklist

- Run backend tests.
- Run frontend build and typecheck.
- Run dependency audit.
- Start production-like preview with a fresh token.
- Generate local packages only.
- Review every package manually.
- Export packages after the session.
- Stop services.
- Rotate or discard the preview token.

For detailed recovery, backup, restore, and Amazon Draft Assist procedures, use `docs/OPERATOR_RUNBOOK.md`.
