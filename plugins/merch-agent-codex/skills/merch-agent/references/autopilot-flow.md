# Autopilot Flow

## Phase 0: Run Setup

Collect or default:

- package count
- marketplaces
- product type
- excluded niches
- preferred niches
- tone/style preferences
- risk tolerance
- whether live research is required
- whether artwork should be generated now

Default to `standard_tshirt`, safe evergreen opportunities, local package generation, and no Amazon interaction.

Treat these defaults as launch settings, not limits. Unless the user explicitly marks a preference as mandatory, the agent may override it when evidence supports a better compliant choice. Record overrides in the trace.

Create a run folder with:

```bash
python3 scripts/init_autopilot_run.py --goal "<goal>" --count <n>
```

## Phase 1: Config And Existing State

Read:

- `config/product_templates.yaml`
- `config/marketplaces.yaml`
- `config/pricing.yaml`
- `config/validation.yaml`

If backend is running:

```bash
python3 scripts/backend_api.py health
python3 scripts/backend_api.py config
python3 scripts/backend_api.py drafts
```

Do not repeat existing draft concepts unless the user asks for variants.

Use config as a contract for valid products, marketplaces, prices, validation, and blocked listing terms. Do not treat config as the full opportunity universe. If config lacks a strong niche, search outside it.

## Phase 2: Opportunity Discovery

Search broadly across unrelated opportunity pools before narrowing:

- evergreen buyer identities and hobbies
- seasonal moments only if timing is current
- emerging phrases or behavior patterns
- giftable relationships
- job, hobby, club, and lifestyle niches
- low-risk humorous or aesthetic angles
- underserved combinations of two safe interests
- recent behavior shifts with fresh evidence
- marketplace-specific gift intent

For each opportunity, capture:

- source
- evidence date
- observed buyer intent
- examples of existing offers
- saturation signals
- design pattern observations
- obvious policy/trademark risks

Use current web/MCP evidence where possible. For time-sensitive trends, never rely only on memory.

Do not stop discovery after the first plausible idea. Keep searching until the candidate pool contains enough variety to compare demand, saturation, originality, and compliance tradeoffs.

## Phase 3: Candidate Normalization

Convert raw ideas into candidates:

- niche
- subniche
- audience
- buyer occasion
- core phrase or visual premise
- product fit
- marketplace fit
- design feasibility

Avoid candidates that depend on protected brands, celebrities, sports teams, movies, games, memes with unclear ownership, or current-event tragedy.

## Phase 4: Competitor And Design Review

For each serious candidate:

- inspect competing listing patterns
- note common colors, motifs, typography, and composition
- identify oversaturated layouts to avoid
- identify a differentiated original angle
- decide whether text-only, illustration-first, badge, emblem, mascot, or pattern design fits

Do not copy competitor artwork or listing text.

## Phase 5: Scoring And Selection

Use `scoring-rubric.md`. Reject any candidate with blocking compliance risk even if demand is strong.

The scoring rubric is a baseline, not a cage. Adapt weighting to the context when justified by evidence, but never adapt away compliance gates. Prefer one excellent compliant package over several weak packages.

The selected candidate set should include:

- why it was selected
- why close alternatives were rejected
- confidence level
- human-review notes
- any autonomy overrides, such as ignored default niche, changed marketplace, changed product color strategy, or fewer-than-requested packages

## Phase 6: Creative Direction

For each selected candidate, write a creative brief:

- design objective
- buyer emotion
- shirt color recommendations
- palette
- typography direction
- illustration motifs
- composition
- negative prompt
- policy/copyright exclusions
- upload dimensions

Use `creative-and-artwork.md`.

## Phase 7: Image Generation

Use the image generation capability when available. Requirements:

- original design
- transparent-background-friendly composition
- no mockup, hanger, model, product photo, watermark, or background scene
- no brand names, copyrighted characters, logos, famous people, or living-artist style imitation
- enough margin for print area

After generation, validate against backend rules.

## Phase 8: Listing, Keywords, Marketplace, Price

Generate:

- design title
- brand
- feature bullet 1
- feature bullet 2
- product description
- keyword strategy
- selected marketplaces
- price recommendation
- product color recommendations

Remove product type terms such as shirt, t-shirt, hoodie, mug, and similar banned terms from listing copy.

## Phase 9: Package Persistence And Validation

Preferred end state:

- draft row in backend
- artifacts under `data/drafts/<draft_id>/`
- final PNG under `data/designs/<draft_id>/`
- validation report
- agent trace

If backend import support is missing, save the trace and generated assets under `data/logs/agent_runs/<run_id>/` and clearly report that package import is the blocking backend gap.

## Phase 10: User Review

Return a short report:

- ready draft IDs
- packages needing human review
- rejected candidates
- artifact paths
- why each winner was chosen
- exact next review action in the UI
