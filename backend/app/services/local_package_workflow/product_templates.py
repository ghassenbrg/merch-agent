from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class ProductResolution:
    code: str
    label: str
    template: str
    width: int
    height: int

    def to_payload(self, selected: bool = True) -> dict[str, Any]:
        return {
            **asdict(self),
            "selected": selected,
        }


def _label_for_product(code: str) -> str:
    return code.replace("_", " ").title().replace("Tshirt", "T-Shirt")


def resolve_product_template(
    product_config: dict[str, Any],
    requested_product: str | None,
) -> ProductResolution:
    products = product_config.get("products", {})
    default_products = product_config.get("default_products", [])
    product_code = requested_product or (default_products[0] if default_products else None)

    if not product_code or product_code not in products:
        raise ValueError(f"Unknown product template product: {product_code}")

    product = products[product_code]
    template_code = product.get("template")
    templates = product_config.get("product_templates", {})
    template = templates.get(template_code)
    if template is None:
        raise ValueError(f"Product {product_code} references missing template {template_code}")

    width = int(product.get("width", template.get("width")))
    height = int(product.get("height", template.get("height")))
    if width <= 0 or height <= 0:
        raise ValueError(f"Product {product_code} has invalid dimensions")

    return ProductResolution(
        code=product_code,
        label=_label_for_product(product_code),
        template=template_code,
        width=width,
        height=height,
    )

