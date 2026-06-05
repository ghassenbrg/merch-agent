# Merch Agent

Merch Agent is a local-first workflow for creating Merch by Amazon review packages.

The intended boundary is strict:

- Autopilot creates local `READY_FOR_AMAZON_DRAFT` packages.
- The dashboard lets a human review, edit, approve, reject, and archive packages.
- Amazon draft creation is a separate manual action for one package at a time.
- Publishing is never automated.

See [MERCH_AGENT_PLAN.md](./MERCH_AGENT_PLAN.md) for the full implementation plan.

## Current Implementation

This first version includes:

- FastAPI backend with SQLite persistence.
- Seeded sample draft data.
- Draft list/detail APIs.
- Mock autopilot run endpoint.
- Manual Amazon draft assist endpoint with guardrails and simulated completion.
- Nuxt 3 dashboard connected to the backend.
- Product, marketplace, upload UI, pricing, and validation config contracts.

## Run Locally

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
npm run dev
```

Open:

```text
http://localhost:3000
```

## API

Backend health:

```text
GET http://localhost:8000/health
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
