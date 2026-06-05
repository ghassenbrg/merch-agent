from __future__ import annotations

import re


DANGEROUS_TEXT = [
    "publish",
    "submit",
    "submit for review",
    "make live",
    "update live listing",
    "create product",
]

SAFE_TEXT = [
    "save draft",
    "save as draft",
]


def normalize_action_label(label: str) -> str:
    return re.sub(r"\s+", " ", label.strip().lower())


def is_dangerous_action(label: str) -> bool:
    normalized = normalize_action_label(label)
    return any(term in normalized for term in DANGEROUS_TEXT)


def is_safe_action(label: str) -> bool:
    normalized = normalize_action_label(label)
    if is_dangerous_action(normalized):
        return False
    return any(term in normalized for term in SAFE_TEXT)


def assert_safe_action(label: str) -> None:
    if not is_safe_action(label):
        raise ValueError(f"Blocked unsafe Amazon action: {label}")
