from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from app.services.local_package_workflow.candidates import NicheCandidate
from app.services.local_package_workflow.marketplaces import LanguageResolution


REQUIRED_LISTING_FIELDS = [
    "design_title",
    "brand",
    "feature_bullet_1",
    "feature_bullet_2",
    "product_description",
]


@dataclass(frozen=True)
class ListingValidationResult:
    product_type_terms_found: list[str]
    min_description_length_passed: bool
    required_fields_passed: bool
    selected_marketplaces_have_copy: bool
    warnings: list[str]

    @property
    def passed(self) -> bool:
        return (
            not self.product_type_terms_found
            and self.min_description_length_passed
            and self.required_fields_passed
            and self.selected_marketplaces_have_copy
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "product_type_terms_found": self.product_type_terms_found,
            "min_description_length_passed": self.min_description_length_passed,
            "required_fields_passed": self.required_fields_passed,
            "selected_marketplaces_have_copy": self.selected_marketplaces_have_copy,
            "warnings": self.warnings,
        }


def _brand_from_candidate(candidate: NicheCandidate) -> str:
    seed = candidate.niche.split()[0]
    return f"{seed.title()} Grove Studio"


def _title_from_candidate(candidate: NicheCandidate) -> str:
    words = re.sub(r"[^A-Za-z0-9 ]", "", candidate.niche).split()
    return " ".join(words[:5])


def generate_listing_groups(
    candidate: NicheCandidate,
    language_sections: list[LanguageResolution],
) -> dict[str, dict[str, Any]]:
    listing_groups: dict[str, dict[str, Any]] = {}
    for section in language_sections:
        listing_groups[section.name] = {
            "locale": section.locale,
            "marketplaces": section.marketplaces,
            "design_title": _title_from_candidate(candidate),
            "brand": _brand_from_candidate(candidate),
            "feature_bullet_1": (
                f"Original {candidate.listing_angle} with a clean, easygoing look."
            ),
            "feature_bullet_2": (
                "A thoughtful gift idea for birthdays, holidays, clubs, weekends, and everyday fans."
            ),
            "product_description": (
                f"This original design is made for {candidate.audience.lower()}. "
                "The concept uses simple artwork, readable lettering, and a general-interest theme "
                "that stays away from brands, events, characters, and protected references."
            ),
        }
    return listing_groups


def validate_listing_groups(
    listing_groups: dict[str, dict[str, Any]],
    selected_marketplaces: list[str],
    banned_terms: list[str],
    min_description_length: int = 80,
) -> ListingValidationResult:
    warnings: list[str] = []
    found_terms: list[str] = []
    required_fields_passed = True
    min_description_length_passed = True
    copied_marketplaces: set[str] = set()

    term_patterns = {
        term: re.compile(rf"(?<![a-z0-9]){re.escape(term.lower())}(?![a-z0-9])")
        for term in banned_terms
    }

    for language, listing in listing_groups.items():
        for field in REQUIRED_LISTING_FIELDS:
            value = str(listing.get(field, "")).strip()
            if not value:
                required_fields_passed = False
                warnings.append(f"{language}.{field} is required.")
            lowered = value.lower()
            for term, pattern in term_patterns.items():
                if pattern.search(lowered):
                    found_terms.append(f"{language}.{field}:{term}")

        description = str(listing.get("product_description", ""))
        if len(description) < min_description_length:
            min_description_length_passed = False
            warnings.append(f"{language}.product_description is too short.")

        copied_marketplaces.update(listing.get("marketplaces", []))

    missing_copy = sorted(set(selected_marketplaces) - copied_marketplaces)
    selected_marketplaces_have_copy = not missing_copy
    if missing_copy:
        warnings.append(f"Selected marketplaces missing listing copy: {', '.join(missing_copy)}.")

    if found_terms:
        warnings.append(f"Product type terms found: {', '.join(found_terms)}.")

    return ListingValidationResult(
        product_type_terms_found=found_terms,
        min_description_length_passed=min_description_length_passed,
        required_fields_passed=required_fields_passed,
        selected_marketplaces_have_copy=selected_marketplaces_have_copy,
        warnings=warnings,
    )

