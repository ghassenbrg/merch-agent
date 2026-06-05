from __future__ import annotations

import json
from typing import Any

import yaml

from app.core.paths import CONFIG_DIR
from app.db.database import get_connection
from app.models.schemas import ConfigResponse, SettingsPatch


CONFIG_FILES = {
    "product_templates": "product_templates.yaml",
    "marketplaces": "marketplaces.yaml",
    "pricing": "pricing.yaml",
    "validation": "validation.yaml",
    "amazon_upload_ui": "amazon_upload_ui.yaml",
    "candidate_sources": "candidate_sources.yaml",
}


class ConfigValidationError(RuntimeError):
    pass


def _read_yaml(filename: str) -> dict[str, Any]:
    with (CONFIG_DIR / filename).open() as file:
        data = yaml.safe_load(file) or {}
    return data


def _require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def validate_config_contracts() -> None:
    config = {key: _read_yaml(filename) for key, filename in CONFIG_FILES.items()}
    errors: list[str] = []

    products = config["product_templates"].get("default_products", [])
    _require(isinstance(products, list) and bool(products), "product_templates.default_products must be a non-empty list", errors)
    product_catalog = config["product_templates"].get("products", {})
    _require(isinstance(product_catalog, dict) and bool(product_catalog), "product_templates.products must be a non-empty mapping", errors)
    product_codes = set(product_catalog.keys())
    for product_code in products:
        _require(product_code in product_codes, f"default product {product_code} is missing from product_templates.products", errors)
    for product_code, product in product_catalog.items():
        width = product.get("width") if isinstance(product, dict) else None
        height = product.get("height") if isinstance(product, dict) else None
        template = product.get("template") if isinstance(product, dict) else None
        _require(bool(template), f"product {product_code} must include template", errors)
        _require(isinstance(width, int) and width > 0, f"product {product_code} width must be a positive integer", errors)
        _require(isinstance(height, int) and height > 0, f"product {product_code} height must be a positive integer", errors)

    marketplaces = config["marketplaces"].get("marketplaces", [])
    _require(isinstance(marketplaces, list) and bool(marketplaces), "marketplaces.marketplaces must be a non-empty list", errors)
    marketplace_codes: set[str] = set()
    for marketplace in marketplaces:
        code = marketplace.get("code") if isinstance(marketplace, dict) else None
        marketplace_codes.add(str(code))
        _require(bool(code), "every marketplace must include code", errors)
        _require(bool(marketplace.get("language_group")) if isinstance(marketplace, dict) else False, f"marketplace {code} must include language_group", errors)

    default_prices = config["pricing"].get("default_prices", {})
    _require(isinstance(default_prices, dict) and bool(default_prices), "pricing.default_prices must be a non-empty mapping", errors)
    for product_code, prices in default_prices.items():
        _require(product_code in product_codes, f"pricing.default_prices references unknown product {product_code}", errors)
        _require(isinstance(prices, dict) and bool(prices), f"pricing for {product_code} must be a non-empty mapping", errors)
        for marketplace_code, price in prices.items():
            _require(marketplace_code in marketplace_codes, f"pricing for {product_code} references unknown marketplace {marketplace_code}", errors)
            amount = price.get("amount") if isinstance(price, dict) else None
            _require(isinstance(amount, int | float) and amount > 0, f"pricing for {product_code}/{marketplace_code} must have positive amount", errors)

    constraints = config["validation"].get("listing_field_constraints", {})
    _require(isinstance(constraints, dict) and bool(constraints), "validation.listing_field_constraints must be configured", errors)
    for field_name in [
        "design_title",
        "brand",
        "feature_bullet_1",
        "feature_bullet_2",
        "product_description",
    ]:
        _require(field_name in constraints, f"validation constraints missing {field_name}", errors)

    amazon_upload_ui = config["amazon_upload_ui"].get("amazon_upload_ui", {})
    selector_map = amazon_upload_ui.get("selector_map", {}) if isinstance(amazon_upload_ui, dict) else {}
    _require(isinstance(selector_map, dict) and bool(selector_map), "amazon_upload_ui.selector_map must be configured", errors)
    for selector_key in [
        "upload_input",
        "upload_status",
        "product_type_select",
        "marketplace_checkbox",
        "price_input",
        "translation_own_radio",
        "language_section_toggle",
        "listing_input",
        "warnings_panel",
        "save_draft_button",
    ]:
        _require(bool(selector_map.get(selector_key)), f"amazon_upload_ui.selector_map missing {selector_key}", errors)
    live = amazon_upload_ui.get("live", {}) if isinstance(amazon_upload_ui, dict) else {}
    live_selector_map = live.get("selector_map", {}) if isinstance(live, dict) else {}
    _require(live.get("manual_ui_trigger_only") is True, "amazon_upload_ui.live.manual_ui_trigger_only must be true", errors)
    _require(live.get("one_package_per_run") is True, "amazon_upload_ui.live.one_package_per_run must be true", errors)
    _require(live.get("click_save_draft_only") is True, "amazon_upload_ui.live.click_save_draft_only must be true", errors)
    _require(live.get("headless") is False, "amazon_upload_ui.live.headless must be false", errors)
    _require(
        str(live.get("create_product_url", "")).startswith("https://merch.amazon."),
        "amazon_upload_ui.live.create_product_url must be an https://merch.amazon.* URL",
        errors,
    )
    for selector_key in [
        "upload_input",
        "upload_status",
        "product_type_select",
        "marketplace_checkbox",
        "price_input",
        "translation_own_radio",
        "language_section_toggle",
        "listing_input",
        "warnings_panel",
        "save_draft_button",
    ]:
        _require(bool(live_selector_map.get(selector_key)), f"amazon_upload_ui.live.selector_map missing {selector_key}", errors)
    dangerous_labels = amazon_upload_ui.get("dangerous_action_labels", []) if isinstance(amazon_upload_ui, dict) else []
    for label in [
        "Publish",
        "Submit",
        "Submit for review",
        "Make live",
        "Update live listing",
        "Create product",
    ]:
        _require(label in dangerous_labels, f"amazon_upload_ui.dangerous_action_labels missing {label}", errors)

    candidate_research = config["candidate_sources"].get("candidate_research", {})
    local_sources = candidate_research.get("local_sources", []) if isinstance(candidate_research, dict) else []
    seeded_generators = candidate_research.get("seeded_generators", []) if isinstance(candidate_research, dict) else []
    _require(
        (isinstance(local_sources, list) and bool(local_sources))
        or (isinstance(seeded_generators, list) and bool(seeded_generators)),
        "candidate_sources.candidate_research must define local_sources or seeded_generators",
        errors,
    )

    if errors:
        raise ConfigValidationError("Config validation failed: " + "; ".join(errors))



def _default_settings(config: dict[str, dict[str, Any]]) -> dict[str, Any]:
    marketplaces = config["marketplaces"].get("marketplaces", [])
    products = config["product_templates"].get("default_products", [])
    return {
        "default_products": products,
        "enabled_marketplaces": [marketplace["code"] for marketplace in marketplaces],
        "default_prices": config["pricing"].get("default_prices", {}),
    }


def _load_settings(defaults: dict[str, Any]) -> dict[str, Any]:
    settings = dict(defaults)
    with get_connection() as connection:
        rows = connection.execute("SELECT key, payload FROM settings").fetchall()
    for row in rows:
        settings[row["key"]] = json.loads(row["payload"])
    return settings


def get_config() -> ConfigResponse:
    config = {key: _read_yaml(filename) for key, filename in CONFIG_FILES.items()}
    settings = _load_settings(_default_settings(config))
    return ConfigResponse(**config, settings=settings)


def update_settings(patch: SettingsPatch) -> dict[str, Any]:
    config = {key: _read_yaml(filename) for key, filename in CONFIG_FILES.items()}
    settings = _load_settings(_default_settings(config))
    updates = patch.model_dump(exclude_unset=True)
    settings.update(updates)

    with get_connection() as connection:
        for key, value in updates.items():
            connection.execute(
                """
                INSERT INTO settings (key, payload, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(key) DO UPDATE SET
                    payload = excluded.payload,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (key, json.dumps(value)),
            )

    return settings
