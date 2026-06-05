"""
Amazon draft operator placeholder.

The live Playwright operator is intentionally not enabled in the first
implementation. Before implementing it, confirm Amazon policy/account readiness
and discover selectors from the live Merch UI.
"""

DANGEROUS_TEXT = [
    "publish",
    "submit",
    "submit for review",
    "make live",
    "create product",
]

SAFE_TEXT = [
    "save draft",
    "save as draft",
]


def is_safe_action(label: str) -> bool:
    normalized = label.strip().lower()
    if any(term in normalized for term in DANGEROUS_TEXT):
        return False
    return any(term in normalized for term in SAFE_TEXT)
