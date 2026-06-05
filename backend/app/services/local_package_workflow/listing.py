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

DEFAULT_FIELD_CONSTRAINTS = {
    "design_title": {"min": 3, "max": 60},
    "brand": {"min": 3, "max": 50},
    "feature_bullet_1": {"min": 10, "max": 256},
    "feature_bullet_2": {"min": 10, "max": 256},
    "product_description": {"min": 80, "max": 2000},
}

TRANSLATION_MARKERS = {
    "de": [" der ", " die ", " das ", " und ", " fuer ", " für ", " geschenk "],
    "fr": [" le ", " la ", " les ", " et ", " pour ", " cadeau "],
    "it": [" il ", " lo ", " gli ", " e ", " per ", " regalo "],
    "es": [" el ", " la ", " los ", " y ", " para ", " regalo "],
}

ENGLISH_BOILERPLATE_PHRASES = [
    "original",
    "gift idea",
    "this original design",
    "made for",
    "weekends",
    "everyday fans",
]


@dataclass(frozen=True)
class ListingValidationResult:
    product_type_terms_found: list[str]
    min_description_length_passed: bool
    required_fields_passed: bool
    selected_marketplaces_have_copy: bool
    field_lengths_passed: bool
    punctuation_passed: bool
    marketplace_language_copy_passed: bool
    translation_checks_passed: bool
    warnings: list[str]

    @property
    def passed(self) -> bool:
        return (
            not self.product_type_terms_found
            and self.min_description_length_passed
            and self.required_fields_passed
            and self.selected_marketplaces_have_copy
            and self.field_lengths_passed
            and self.punctuation_passed
            and self.marketplace_language_copy_passed
            and self.translation_checks_passed
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "product_type_terms_found": self.product_type_terms_found,
            "min_description_length_passed": self.min_description_length_passed,
            "required_fields_passed": self.required_fields_passed,
            "selected_marketplaces_have_copy": self.selected_marketplaces_have_copy,
            "field_lengths_passed": self.field_lengths_passed,
            "punctuation_passed": self.punctuation_passed,
            "marketplace_language_copy_passed": self.marketplace_language_copy_passed,
            "translation_checks_passed": self.translation_checks_passed,
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
    banned_terms: list[str] | dict[str, list[str]],
    min_description_length: int = 80,
    field_constraints: dict[str, dict[str, int]] | None = None,
    marketplace_language_map: dict[str, str] | None = None,
    translation_required_locales: list[str] | None = None,
) -> ListingValidationResult:
    warnings: list[str] = []
    found_terms: list[str] = []
    required_fields_passed = True
    min_description_length_passed = True
    field_lengths_passed = True
    punctuation_passed = True
    marketplace_language_copy_passed = True
    translation_checks_passed = True
    copied_marketplaces: set[str] = set()

    constraints = field_constraints or DEFAULT_FIELD_CONSTRAINTS
    translation_required = set(translation_required_locales or ["de", "fr", "it", "es", "ja"])
    if isinstance(banned_terms, dict):
        terms_by_language = {
            language.lower(): terms for language, terms in banned_terms.items()
        }
    else:
        terms_by_language = {"all": banned_terms}

    for language, listing in listing_groups.items():
        locale = str(listing.get("locale", "")).lower()
        listing_marketplaces = list(listing.get("marketplaces", []))
        copied_marketplaces.update(listing_marketplaces)

        expected_languages = {
            marketplace_language_map.get(marketplace)
            for marketplace in listing_marketplaces
            if marketplace_language_map and marketplace in marketplace_language_map
        }
        expected_languages.discard(None)
        if expected_languages and language not in expected_languages:
            marketplace_language_copy_passed = False
            warnings.append(
                f"{language} listing is assigned to marketplace language(s): {', '.join(sorted(expected_languages))}."
            )

        language_terms = [
            *terms_by_language.get("all", []),
            *terms_by_language.get(language.lower(), []),
            *terms_by_language.get(locale, []),
        ]
        term_patterns = {
            term: re.compile(rf"(?<![a-z0-9]){re.escape(term.lower())}(?![a-z0-9])")
            for term in language_terms
        }

        listing_text_parts: list[str] = []
        for field in REQUIRED_LISTING_FIELDS:
            value = str(listing.get(field, "")).strip()
            listing_text_parts.append(value)
            if not value:
                required_fields_passed = False
                warnings.append(f"{language}.{field} is required.")
            field_limits = constraints.get(field, {})
            min_length = int(field_limits.get("min", 1))
            max_length = int(field_limits.get("max", 2000))
            if value and len(value) < min_length:
                field_lengths_passed = False
                warnings.append(f"{language}.{field} is shorter than {min_length} characters.")
            if len(value) > max_length:
                field_lengths_passed = False
                warnings.append(f"{language}.{field} exceeds {max_length} characters.")
            if re.search(r"[!?.,]{3,}", value):
                punctuation_passed = False
                warnings.append(f"{language}.{field} has repeated punctuation.")
            if value.count("!") > 1:
                punctuation_passed = False
                warnings.append(f"{language}.{field} has too many exclamation marks.")
            lowered = value.lower()
            for term, pattern in term_patterns.items():
                if pattern.search(lowered):
                    found_terms.append(f"{language}.{field}:{term}")

        description = str(listing.get("product_description", ""))
        if len(description) < min_description_length:
            min_description_length_passed = False
            warnings.append(f"{language}.product_description is too short.")

        if locale in translation_required:
            text = f" {' '.join(listing_text_parts).lower()} "
            if locale == "ja":
                has_locale_signal = bool(re.search(r"[\u3040-\u30ff\u3400-\u9fff]", text))
            else:
                has_locale_signal = any(marker in text for marker in TRANSLATION_MARKERS.get(locale, []))
            copied_english = any(phrase in text for phrase in ENGLISH_BOILERPLATE_PHRASES)
            if not has_locale_signal or copied_english:
                translation_checks_passed = False
                warnings.append(f"{language} listing requires reviewed {locale} copy.")

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
        field_lengths_passed=field_lengths_passed,
        punctuation_passed=punctuation_passed,
        marketplace_language_copy_passed=marketplace_language_copy_passed,
        translation_checks_passed=translation_checks_passed,
        warnings=warnings,
    )
