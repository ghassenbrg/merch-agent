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
}


def _read_yaml(filename: str) -> dict[str, Any]:
    with (CONFIG_DIR / filename).open() as file:
        data = yaml.safe_load(file) or {}
    return data


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
