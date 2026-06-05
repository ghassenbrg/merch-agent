# Scoring Rubric

Score each candidate from 0 to 100.

## Weights

These weights are the default baseline. The agent may adapt them for a specific run when current evidence shows a different weighting would select better compliant packages. Any adaptation must be written to the trace with the reason. Compliance and IP safety remain non-negotiable.

- Demand and buyer intent: 20
- Trend or evergreen strength: 15
- Competition/saturation advantage: 15
- Compliance and IP safety: 20
- Design feasibility and originality: 15
- Marketplace/product fit: 10
- Listing/keyword clarity: 5

## Automatic Rejects

Reject before scoring if the candidate depends on:

- brand, logo, trademark, team, school, or celebrity references
- copyrighted characters, movies, TV, games, books, songs, or quote origins
- living artist style imitation
- tragedy, hate, harassment, protected class targeting, medical claims, political persuasion, or adult/violent content
- exact competitor phrase/artwork copying
- misleading product terms or unavailable marketplace copy

## Scoring Guidance

Demand and buyer intent:

- 18-20: clear gift/purchase intent, repeated evidence, multiple buyer occasions
- 12-17: plausible audience and occasion
- 0-11: vague identity or weak purchase reason

Trend or evergreen strength:

- 13-15: evergreen or currently supported by fresh evidence
- 8-12: seasonal but still timely
- 0-7: stale, too brief, or unsupported

Competition/saturation advantage:

- 13-15: demand exists but competitors are generic or weak
- 8-12: competitive but differentiated angle exists
- 0-7: saturated with strong incumbents

Compliance and IP safety:

- 18-20: generic/original, no obvious protected terms
- 12-17: low risk with human-review notes
- 0-11: risky; normally reject

Design feasibility and originality:

- 13-15: strong visual angle, feasible at upload dimensions
- 8-12: workable but may need careful execution
- 0-7: depends on tiny detail, copyrighted likeness, or unclear art

Marketplace/product fit:

- 8-10: audience and language fit selected marketplaces
- 4-7: one marketplace fits but translations or pricing need work
- 0-3: poor marketplace/product match

Listing/keyword clarity:

- 4-5: clear title, long-tail keywords, no banned product terms
- 2-3: workable with edits
- 0-1: unclear or keyword-stuffed

## Selection Thresholds

- 85-100: strong candidate; generate package if compliance is clean.
- 75-84: usable; generate only if it beats alternatives.
- 65-74: hold unless the user requested that niche.
- below 65: reject.

Never let a high score override a blocking compliance issue.

## Autonomy Rules

- A candidate below 85 can still win if it is the best compliant option and the trace explains why it beats higher-scoring but weaker alternatives.
- A candidate above 85 can still be rejected if it is generic, hard to execute, saturated, or less compelling than a lower-scoring candidate with better buyer intent and originality.
- Do not fill the requested count with mediocre ideas. Return fewer packages when the remaining candidates do not clear the quality bar.
- Do not let preferred niches, seed lists, or marketplace defaults suppress stronger compliant opportunities discovered during research.
- Use `human_review_required` when uncertainty is rights/policy related; use `rejected` when the issue is weak demand, saturation, poor originality, or bad product fit.
