# Codex Plugin First Run

Merch Agent is now a Codex plugin workflow with the local backend/dashboard as support services.

## One-Time Setup

From the repo root:

```bash
cd /Users/ghassenbrg/git/merch-agent
codex plugin marketplace add /Users/ghassenbrg/git/merch-agent
```

Codex discovers this local marketplace from:

```text
/Users/ghassenbrg/git/merch-agent/.agents/plugins/marketplace.json
```

The marketplace name is:

```text
merch-agent-local
```

The plugin name is:

```text
merch-agent-codex
```

If the current Codex CLI rejects the existing global `service_tier = "default"` setting, use:

```bash
codex -c service_tier='"fast"' plugin marketplace add /Users/ghassenbrg/git/merch-agent
```

The plugin is enabled in `~/.codex/config.toml` with:

```toml
[plugins."merch-agent-codex@merch-agent-local"]
enabled = true
```

Start a new Codex thread after plugin changes so Codex reloads the skill.

## Verify Readiness

```bash
./scripts/check_codex_plugin_ready.sh
```

This validates the plugin, marketplace, backend bridge tests, package workflow tests, and agent trace shape.

## Optional Backend/UI

For dashboard review, start the app:

```bash
./scripts/ready.sh
```

The dashboard opens at:

```text
http://127.0.0.1:3000
```

## First Run Prompt

Paste this into a fresh Codex thread from `/Users/ghassenbrg/git/merch-agent`:

```text
Use the Merch Agent Codex plugin and run full autopilot for my first production-safe package.

Goal:
Find 1 low-risk, evergreen Amazon Merch opportunity for a standard_tshirt, US marketplace only (.com). Use current web research, compare competing listings/design patterns, score candidates, reject risky or weak ideas, choose the best niche/subniche, create the artistic direction, generate original transparent-background artwork suitable for the configured 4500x5400 upload template, decide recommended shirt colors, write listing fields and keyword strategy, choose price from local config, import the package through the local backend agent package endpoint, run validation, and return the draft ID plus artifact paths.

Preferences:
- Conservative compliance.
- No brands, celebrities, copyrighted characters, protected phrases, living-artist style imitation, politics, tragedy, adult content, or medical claims.
- No Amazon interaction.
- Package must be local-review-ready only.
- If image generation or backend import is unavailable, stop at the exact blocker and preserve the agent trace under data/logs/agent_runs/.

After completion, summarize:
- selected candidate and why it won
- rejected candidates and why
- sources used
- final artwork path
- draft ID
- validation status
- what I should review in the dashboard
```

## CLI First Run

If using Codex CLI instead of the app:

```bash
codex -c service_tier='"fast"' --search -C /Users/ghassenbrg/git/merch-agent "Use the Merch Agent Codex plugin and run full autopilot for 1 conservative, US-only standard_tshirt package. No Amazon interaction. Generate or import artwork, validate locally, and return the draft ID/artifact paths."
```

## Hard Stop

The autopilot must never publish, submit for review, create live products, update live listings, or batch-touch Amazon. Amazon Draft Assist remains a separate one-package, save-draft-only human action.
