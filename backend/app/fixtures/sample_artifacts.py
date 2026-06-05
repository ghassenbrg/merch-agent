from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from app.core.paths import DATA_DIR, resolve_runtime_path


def _write_json_if_missing(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for font_name in ["Helvetica.ttc", "Arial.ttf", "DejaVuSans.ttf"]:
        try:
            return ImageFont.truetype(font_name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _centered_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    fill: tuple[int, int, int, int],
) -> None:
    bbox = draw.textbbox((0, 0), text, font=font)
    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]
    draw.text((xy[0] - width // 2, xy[1] - height // 2), text, font=font, fill=fill)


def _render_sample_png(draft: dict[str, Any], final_png_path: Path) -> None:
    design = draft["design"]
    width = int(design["width"])
    height = int(design["height"])
    title = draft["listing_groups"]["English"]["design_title"]
    niche = draft["niche"]

    final_png_path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGBA", (width, height), (255, 255, 255, 0))
    draw = ImageDraw.Draw(image)

    accent = (18, 128, 119, 255)
    dark = (29, 47, 54, 255)
    muted = (86, 105, 112, 255)
    soft = (232, 247, 245, 230)

    bounds = (
        int(width * 0.16),
        int(height * 0.22),
        int(width * 0.84),
        int(height * 0.78),
    )
    draw.rounded_rectangle(bounds, radius=80, fill=soft, outline=accent, width=18)
    draw.ellipse(
        (
            int(width * 0.40),
            int(height * 0.30),
            int(width * 0.60),
            int(height * 0.47),
        ),
        outline=accent,
        width=18,
    )
    draw.line(
        (
            int(width * 0.28),
            int(height * 0.58),
            int(width * 0.72),
            int(height * 0.58),
        ),
        fill=accent,
        width=16,
    )

    _centered_text(draw, (width // 2, int(height * 0.50)), title.upper(), _font(190), dark)
    _centered_text(draw, (width // 2, int(height * 0.64)), niche, _font(96), muted)
    _centered_text(draw, (width // 2, int(height * 0.72)), "LOCAL SAMPLE ARTWORK", _font(64), accent)

    image.save(final_png_path, format="PNG", optimize=True)


def ensure_sample_artifacts(drafts: list[dict[str, Any]]) -> None:
    for draft in drafts:
        draft_id = draft["draft_id"]
        final_png_path = resolve_runtime_path(str(draft["design"].get("final_png", "")))
        if not final_png_path.is_file():
            _render_sample_png(draft, final_png_path)

        artifact_dir = DATA_DIR / "drafts" / draft_id
        _write_json_if_missing(artifact_dir / "draft.json", draft)
        _write_json_if_missing(artifact_dir / "listing_fields.json", draft["listing_groups"])
        _write_json_if_missing(artifact_dir / "validation_report.json", draft["validation"])
        _write_json_if_missing(artifact_dir / "change_history.json", draft.get("change_history", []))
