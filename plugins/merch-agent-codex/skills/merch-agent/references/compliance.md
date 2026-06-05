# Compliance Gates

Use conservative review. The goal is review-ready packages, not risky uploads.

## Copyright And Trademark

Block or require human review for:

- brand names, logos, slogans, mascots, and product names
- sports teams, schools, military units, clubs with protected marks
- celebrities, influencers, politicians used for endorsement or likeness
- movies, TV, games, anime, comics, books, song lyrics, album titles, and famous quotes
- current memes with unclear ownership
- competitor listing text or artwork copying
- references that need a real person, franchise, or brand to make sense

Prefer generic, original concepts:

- relationship gifts
- hobbies
- jobs without employer marks
- pets and animals as generic subjects
- original puns
- decorative typography
- abstract or invented characters

## Amazon-Sensitive Content

Block or mark human review for:

- hate, harassment, slurs, protected class targeting
- tragedy exploitation
- medical, legal, financial, or safety claims
- adult sexual content
- graphic violence
- illegal drug promotion
- political persuasion or impersonation
- misleading claims such as official, certified, endorsed, or licensed

## Listing Copy Rules

Remove product type terms from listing fields. The backend config bans terms such as:

- shirt, t-shirt, tshirt, tee
- hoodie, sweatshirt, long sleeve, tank top
- mug, tote bag, pillow
- phone case, tumbler, water bottle, hat, visor

Use niche/audience/occasion keywords instead.

## Decision Labels

Use one of:

- `pass`: low-risk enough for local package generation
- `human_review_required`: uncertain or needs manual trademark/policy review
- `blocked`: do not generate/upload

When unsure, choose `human_review_required`.
