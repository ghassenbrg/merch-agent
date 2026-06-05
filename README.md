# Merch Agent

Merch Agent is a local-first workflow for creating Merch by Amazon review packages.

The intended boundary is strict:

- Autopilot creates local `READY_FOR_AMAZON_DRAFT` packages.
- The dashboard lets a human review, edit, approve, reject, and archive packages.
- Amazon draft creation is a separate manual action for one package at a time.
- Publishing is never automated.

See [MERCH_AGENT_PLAN.md](./MERCH_AGENT_PLAN.md) for the full implementation plan.

Phase 12 operations docs:

- [Beginner how-to](./docs/BEGINNER_HOW_TO.md)
- [Operator runbook](./docs/OPERATOR_RUNBOOK.md)
- [Production acceptance checklist](./docs/PRODUCTION_ACCEPTANCE.md)

## Current Implementation

This version includes:

- FastAPI backend with SQLite persistence.
- Seeded sample draft data.
- Draft list/detail APIs.
- Local package autopilot, scheduler controls, and run history.
- Optional live-research scoring snapshots for explicit production-mode runs.
- Manual Amazon draft assist endpoint with save-draft-only guardrails.
- Nuxt 3 dashboard connected to the backend.
- Product, marketplace, upload UI, pricing, and validation config contracts.
- Production-readiness controls for optional API auth, CORS/origin checks, write rate limits, health checks, and log retention.

## Run Locally

One-command setup and production-like preview:

```bash
./scripts/ready.sh
```

This creates/uses the backend virtualenv, installs backend and frontend dependencies, builds the frontend, generates a temporary API token when none is set, and starts the authenticated preview at `http://127.0.0.1:3000`.

Optional full checks before starting:

```bash
MERCH_AGENT_RUN_CHECKS=1 ./scripts/ready.sh
```

Backend:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run build
NUXT_PUBLIC_API_BASE=http://127.0.0.1:8000 HOST=0.0.0.0 PORT=3000 node .output/server/index.mjs
```

Open:

```text
http://localhost:3000
```

Note: in this local Node 24/macOS environment, Nuxt's dev server currently hits a Vite IPC socket error. The production build/preview path above is verified and is the one to use for now.

## Production-Like Preview

Production-like exposure requires an API token. Generate one outside the repo and export it:

```bash
export MERCH_AGENT_API_TOKEN="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
export MERCH_AGENT_ENV=production
export MERCH_AGENT_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
export NUXT_PUBLIC_API_TOKEN="$MERCH_AGENT_API_TOKEN"
./scripts/production_preview.sh
```

The script starts the backend on `127.0.0.1:8000` and the frontend on `127.0.0.1:3000`. Do not bind to `0.0.0.0` or expose through a reverse proxy unless `MERCH_AGENT_API_TOKEN`, `MERCH_AGENT_ALLOWED_ORIGINS`, and `MERCH_AGENT_TRUSTED_HOSTS` are set for that host.

Docker compose is also available:

```bash
export MERCH_AGENT_API_TOKEN="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
docker compose up --build
```

Compose binds both services to localhost by default. Keep `data/` mounted for persistence and backups.

## Security And Operations

- Local mode is intended for localhost only. Set `MERCH_AGENT_ENV=production` or `MERCH_AGENT_EXPOSED=true` when exposing beyond the local machine; the backend will refuse startup without `MERCH_AGENT_API_TOKEN`.
- API clients authenticate with `Authorization: Bearer <token>`. The Nuxt preview sends this when `NUXT_PUBLIC_API_TOKEN` is set.
- CORS allows only configured origins. Unsafe API methods reject browser requests with an untrusted `Origin`.
- Write endpoints have an in-memory per-client rate limit controlled by `MERCH_AGENT_WRITE_RATE_LIMIT_PER_MINUTE`.
- Runtime secrets belong in environment variables or an ignored `.env`, never in committed config. `data/browser-profiles/`, screenshots, logs, exports, and SQLite files are ignored.
- Backend logs rotate according to `MERCH_AGENT_LOG_MAX_BYTES`, `MERCH_AGENT_LOG_BACKUP_COUNT`, and `MERCH_AGENT_LOG_RETENTION_DAYS`.
- Dependency audit process:

```bash
./scripts/audit_dependencies.sh
```

This runs `pip check` for the backend environment and `npm audit --audit-level=moderate` for the frontend.
Frontend type checking is available with `cd frontend && npm run typecheck` after the Nuxt build/prepare files exist.

For beta operation, follow the operator runbook and production acceptance checklist in `docs/`. Keep Amazon Draft Assist manual, one draft at a time, and save-draft-only.

## API

Backend health:

```text
GET http://localhost:8000/health
GET http://localhost:8000/health/live
GET http://localhost:8000/health/ready
```

Drafts:

```text
GET  /api/drafts
GET  /api/drafts/{draft_id}
POST /api/drafts/{draft_id}/approve
POST /api/drafts/{draft_id}/reject
POST /api/drafts/{draft_id}/archive
POST /api/drafts/{draft_id}/regenerate-design
POST /api/drafts/{draft_id}/regenerate-listing
POST /api/drafts/{draft_id}/amazon-draft
```

Workflows:

```text
POST /api/workflows/autopilot/run
GET  /api/runs/{run_id}/logs
```
