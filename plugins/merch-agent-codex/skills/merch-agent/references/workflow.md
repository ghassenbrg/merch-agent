# Merch Agent Codex Workflow

## Product Shape

Merch Agent is a Codex plugin-backed workflow with a local app attached to it.

```text
Codex prompt / UI trigger / scheduler
  -> Merch Agent Codex skill
  -> web + MCP research
  -> AI candidate analysis and decisioning
  -> AI creative direction and image generation
  -> local backend package persistence and validation
  -> Nuxt dashboard review
  -> optional one-package Amazon Draft Assist
```

## Authority Split

Codex/plugin owns flexible intelligence:

- market research strategy
- evidence synthesis
- niche and subniche choice
- candidate ranking
- design concept selection
- prompt writing for image generation
- run narrative and trace explanation

Backend owns deterministic guarantees:

- config contracts
- artifact paths
- package schema
- listing validation
- artwork validation
- compliance flags
- status transitions
- Amazon draft-save guardrails

UI owns human operations:

- run visibility
- draft queue
- artifact preview
- edit/approve/reject/archive
- explicit one-draft Amazon assist

## Required Agent Trace

Every AI run should preserve enough trace for review:

- input goal and constraints
- sources searched
- candidates considered
- candidates rejected and why
- score dimensions
- final selected candidates
- creative brief per candidate
- generated image prompt or image artifact reference
- validation result
- final draft IDs

Store traces in backend persistence when possible. Until a dedicated table exists, save JSON under `data/logs/agent_runs/`.

## Backend Gap To Close

The current backend has `/api/workflows/autopilot/run`, but it generates from deterministic candidate sources. The plugin can call it for smoke tests and persistence checks, but real AI-selected packages need one of these:

- a backend endpoint that accepts an agent-selected candidate, listing groups, design metadata, image path, and research trace;
- or a plugin script that writes the same package schema and calls existing repository helpers safely.

Do not claim the full AI agent is complete until one of those exists and is validated by tests.
