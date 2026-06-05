from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class MarketplaceResolution:
    code: str
    language_group: str
    locale: str
    selected: bool
    excluded_reason: str | None = None

    def to_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        if self.excluded_reason is None:
            payload.pop("excluded_reason")
        return payload


@dataclass(frozen=True)
class LanguageResolution:
    name: str
    locale: str
    marketplaces: list[str]


@dataclass(frozen=True)
class MarketplacePlan:
    marketplaces: list[MarketplaceResolution]
    language_sections: list[LanguageResolution]

    @property
    def selected_codes(self) -> list[str]:
        return [marketplace.code for marketplace in self.marketplaces if marketplace.selected]


def resolve_marketplaces(
    marketplace_config: dict[str, Any],
    enabled_marketplaces: list[str],
    priced_marketplaces: list[str],
    explore_marketplaces: bool,
) -> MarketplacePlan:
    enabled = set(enabled_marketplaces)
    priced = set(priced_marketplaces)
    selected_codes: set[str] = set()

    for marketplace in marketplace_config.get("marketplaces", []):
        code = marketplace["code"]
        if code in enabled and code in priced:
            selected_codes.add(code)
        if selected_codes and not explore_marketplaces:
            break

    marketplace_resolutions: list[MarketplaceResolution] = []
    language_to_codes: dict[str, list[str]] = {}

    for marketplace in marketplace_config.get("marketplaces", []):
        code = marketplace["code"]
        selected = code in selected_codes
        excluded_reason = None
        if code not in enabled:
            excluded_reason = "Marketplace disabled in local settings."
        elif code not in priced:
            excluded_reason = "No local price config for selected product."
        elif not selected:
            excluded_reason = "Skipped because marketplace exploration is disabled."

        resolution = MarketplaceResolution(
            code=code,
            language_group=marketplace["language_group"],
            locale=marketplace["locale"],
            selected=selected,
            excluded_reason=excluded_reason,
        )
        marketplace_resolutions.append(resolution)
        if selected:
            language_to_codes.setdefault(resolution.language_group, []).append(code)

    language_sections: list[LanguageResolution] = []
    configured_sections = marketplace_config.get("language_sections", {})
    for language, codes in language_to_codes.items():
        section = configured_sections.get(language, {})
        language_sections.append(
            LanguageResolution(
                name=language,
                locale=section.get("locale", codes[0].lstrip(".")),
                marketplaces=codes,
            )
        )

    return MarketplacePlan(
        marketplaces=marketplace_resolutions,
        language_sections=language_sections,
    )

