import re

from app.models.schemas import Draft


BANNED_PRODUCT_TYPE_TERMS = [
    "shirt",
    "t-shirt",
    "tshirt",
    "tee",
    "hoodie",
    "sweatshirt",
    "long sleeve",
    "tank top",
    "mug",
    "tote bag",
    "pillow",
    "popsocket",
    "phone case",
    "tumbler",
    "water bottle",
    "hat",
    "visor",
    "baseball cap",
    "case",
    "phone cover",
    "zip hoodie",
]


REQUIRED_READY_CHECKS = [
    "png_valid",
    "transparent_background",
    "correct_resolution",
    "file_size_under_limit",
    "placement_metadata_valid",
    "design_not_too_small",
    "design_not_cropped",
    "product_type_terms_removed",
    "listing_min_lengths_passed",
    "selected_marketplaces_have_copy",
    "listing_field_lengths_passed",
    "listing_punctuation_passed",
    "marketplace_language_copy_passed",
    "translation_checks_passed",
    "price_config_exists",
]


def find_product_type_terms(draft: Draft) -> list[str]:
    found: list[str] = []
    for language, listing in draft.listing_groups.items():
        for field in [
            "design_title",
            "brand",
            "feature_bullet_1",
            "feature_bullet_2",
            "product_description",
        ]:
            value = str(listing.get(field, "")).lower()
            for term in BANNED_PRODUCT_TYPE_TERMS:
                pattern = re.compile(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])")
                if pattern.search(value):
                    found.append(f"{language}.{field}:{term}")
    return found


def compute_ready_for_amazon_draft(draft: Draft) -> tuple[bool, list[str]]:
    warnings: list[str] = []

    for check in REQUIRED_READY_CHECKS:
        if draft.validation.get(check) is not True:
            warnings.append(f"Blocking validation failed: {check}")

    if draft.validation.get("human_review_required") is True:
        warnings.append("Human policy review is required before Amazon draft readiness.")

    for policy_check in ["trademark_precheck", "amazon_policy_precheck"]:
        if draft.validation.get(policy_check) != "pass":
            warnings.append(f"Policy validation failed: {policy_check}")

    product_terms = find_product_type_terms(draft)
    if product_terms:
        warnings.append(f"Product type terms found: {', '.join(product_terms)}")

    if not draft.price.get("royalty_positive"):
        warnings.append("Royalty check is not positive.")

    if draft.translation_mode != "provide_own_translations":
        warnings.append("Translation mode must be provide_own_translations.")

    return len(warnings) == 0, warnings
