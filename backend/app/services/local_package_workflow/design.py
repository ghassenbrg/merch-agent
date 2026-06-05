from __future__ import annotations

import hashlib
import json
import math
import textwrap
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from app.core.paths import DATA_DIR, REPO_ROOT
from app.services.local_package_workflow.candidates import NicheCandidate
from app.services.local_package_workflow.product_templates import ProductResolution


FONT_CANDIDATES = {
    "bold": [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Supplemental/Helvetica Bold.ttf",
        "/Library/Fonts/Arial Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ],
    "regular": [
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Helvetica.ttf",
        "/Library/Fonts/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ],
}


def _relative_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path.resolve())


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _load_font(kind: str, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for font_path in FONT_CANDIDATES[kind]:
        path = Path(font_path)
        if path.is_file():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default(size=size)


def _text_size(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> tuple[int, int]:
    box = draw.textbbox((0, 0), text, font=font)
    return box[2] - box[0], box[3] - box[1]


def _fit_font(
    draw: ImageDraw.ImageDraw,
    text_lines: list[str],
    kind: str,
    max_width: int,
    max_height: int,
    initial_size: int,
    min_size: int,
) -> ImageFont.ImageFont:
    size = initial_size
    while size >= min_size:
        font = _load_font(kind, size)
        line_sizes = [_text_size(draw, line, font) for line in text_lines]
        total_height = sum(height for _, height in line_sizes) + int(size * 0.3) * (len(text_lines) - 1)
        widest = max((width for width, _ in line_sizes), default=0)
        if widest <= max_width and total_height <= max_height:
            return font
        size -= max(2, initial_size // 24)
    return _load_font(kind, min_size)


def _wrap_title(title: str) -> list[str]:
    words = title.upper().split()
    if len(words) <= 2:
        return [" ".join(words)]
    midpoint = math.ceil(len(words) / 2)
    return [" ".join(words[:midpoint]), " ".join(words[midpoint:])]


def _safe_text(text: str, max_chars: int) -> str:
    normalized = " ".join(text.replace("&", "AND").split())
    return normalized[:max_chars].rstrip()


def _palette_for(candidate: NicheCandidate) -> dict[str, tuple[int, int, int, int]]:
    seed = int(hashlib.sha256(candidate.candidate_id.encode("utf-8")).hexdigest()[:8], 16)
    palettes = [
        {
            "ink": (13, 52, 59, 255),
            "accent": (15, 143, 134, 255),
            "muted": (94, 113, 91, 255),
            "paper": (250, 252, 245, 255),
        },
        {
            "ink": (35, 45, 58, 255),
            "accent": (139, 90, 43, 255),
            "muted": (86, 116, 98, 255),
            "paper": (251, 248, 239, 255),
        },
        {
            "ink": (22, 43, 38, 255),
            "accent": (50, 101, 122, 255),
            "muted": (112, 99, 74, 255),
            "paper": (247, 251, 250, 255),
        },
    ]
    return palettes[seed % len(palettes)]


def _draw_centered_lines(
    draw: ImageDraw.ImageDraw,
    lines: list[str],
    center_x: int,
    top: int,
    font: ImageFont.ImageFont,
    fill: tuple[int, int, int, int],
    line_gap: int,
) -> int:
    y = top
    for line in lines:
        width, height = _text_size(draw, line, font)
        draw.text((center_x - width / 2, y), line, font=font, fill=fill)
        y += height + line_gap
    return y


def _draw_motif(
    draw: ImageDraw.ImageDraw,
    candidate: dict[str, Any],
    bounds: dict[str, int],
    palette: dict[str, tuple[int, int, int, int]],
) -> None:
    x = bounds["x"]
    y = bounds["y"]
    w = bounds["width"]
    h = bounds["height"]
    cx = x + w // 2
    motif_top = y + int(h * 0.63)
    motif_bottom = y + int(h * 0.82)
    ink = palette["ink"]
    accent = palette["accent"]
    muted = palette["muted"]
    niche = str(candidate.get("niche", "")).lower()

    if "fishing" in niche:
        for offset in [0, int(h * 0.045), int(h * 0.09)]:
            points = []
            for step in range(0, 13):
                px = x + int(w * (0.18 + step * 0.055))
                py = motif_top + offset + int(math.sin(step / 1.5) * h * 0.012)
                points.append((px, py))
            draw.line(points, fill=accent, width=max(8, w // 170), joint="curve")
        rod_start = (x + int(w * 0.25), motif_bottom)
        rod_end = (x + int(w * 0.76), motif_top - int(h * 0.04))
        draw.line([rod_start, rod_end], fill=ink, width=max(8, w // 180))
        draw.arc(
            [cx - int(w * 0.18), motif_top - int(h * 0.1), cx + int(w * 0.25), motif_top + int(h * 0.2)],
            200,
            340,
            fill=muted,
            width=max(5, w // 260),
        )
    elif "garden" in niche or "book" in niche:
        book_w = int(w * 0.42)
        book_h = int(h * 0.05)
        for index in range(3):
            top = motif_top + index * int(book_h * 1.2)
            draw.rounded_rectangle(
                [cx - book_w // 2, top, cx + book_w // 2, top + book_h],
                radius=max(8, book_h // 5),
                outline=ink,
                width=max(6, w // 220),
                fill=None,
            )
        stem_x = cx + int(w * 0.24)
        draw.line(
            [(stem_x, motif_top + int(h * 0.01)), (stem_x, motif_bottom)],
            fill=accent,
            width=max(5, w // 260),
        )
        for index in range(4):
            leaf_y = motif_top + index * int(h * 0.04)
            direction = -1 if index % 2 else 1
            leaf_x2 = stem_x + direction * int(w * 0.11)
            draw.ellipse(
                [
                    min(stem_x, leaf_x2),
                    leaf_y,
                    max(stem_x, leaf_x2),
                    leaf_y + int(h * 0.05),
                ],
                outline=accent,
                width=max(5, w // 280),
            )
    elif "chess" in niche:
        square = int(min(w, h) * 0.065)
        board_x = cx - square * 3
        board_y = motif_top
        for row in range(2):
            for col in range(6):
                fill = accent if (row + col) % 2 == 0 else None
                draw.rectangle(
                    [
                        board_x + col * square,
                        board_y + row * square,
                        board_x + (col + 1) * square,
                        board_y + (row + 1) * square,
                    ],
                    outline=ink,
                    fill=fill,
                    width=max(3, square // 14),
                )
        crown_y = board_y - int(square * 1.3)
        draw.polygon(
            [
                (cx - square, board_y),
                (cx - int(square * 0.65), crown_y),
                (cx, board_y - int(square * 0.55)),
                (cx + int(square * 0.65), crown_y),
                (cx + square, board_y),
            ],
            outline=ink,
            fill=None,
        )
        draw.line([(cx, crown_y - square // 3), (cx, crown_y + square // 2)], fill=ink, width=max(4, square // 12))
        draw.line([(cx - square // 3, crown_y), (cx + square // 3, crown_y)], fill=ink, width=max(4, square // 12))
    else:
        radius = int(min(w, h) * 0.05)
        for index, keyword in enumerate(candidate.get("keywords", [])[:3]):
            label = keyword.upper()[:12]
            font = _load_font("regular", max(24, w // 45))
            text_w, text_h = _text_size(draw, label, font)
            chip_w = text_w + radius * 2
            chip_x = cx - chip_w // 2
            chip_y = motif_top + index * int(radius * 1.8)
            draw.rounded_rectangle(
                [chip_x, chip_y, chip_x + chip_w, chip_y + text_h + radius],
                radius=radius,
                outline=accent,
                width=max(4, w // 260),
            )
            draw.text((chip_x + radius, chip_y + radius // 2), label, font=font, fill=ink)


def _render_design(source: dict[str, Any], final_png_path: Path) -> dict[str, Any]:
    canvas = source["canvas"]
    width = int(canvas["width"])
    height = int(canvas["height"])
    image = Image.new("RGBA", (width, height), (255, 255, 255, 0))
    draw = ImageDraw.Draw(image)
    bounds = source["placement_metadata"]["intended_design_bounds"]
    palette = {
        key: tuple(value)
        for key, value in source["palette"].items()
    }
    x = int(bounds["x"])
    y = int(bounds["y"])
    w = int(bounds["width"])
    h = int(bounds["height"])
    cx = x + w // 2

    line_width = max(16, width // 140)
    inner_inset = max(42, width // 70)
    draw.rounded_rectangle(
        [x, y, x + w, y + h],
        radius=max(80, width // 28),
        outline=palette["ink"],
        width=line_width,
        fill=palette["paper"],
    )
    draw.rounded_rectangle(
        [x + inner_inset, y + inner_inset, x + w - inner_inset, y + h - inner_inset],
        radius=max(60, width // 36),
        outline=palette["accent"],
        width=max(8, line_width // 2),
    )

    title_lines = source["text"]["title_lines"]
    title_font = _fit_font(
        draw,
        title_lines,
        "bold",
        max_width=int(w * 0.72),
        max_height=int(h * 0.27),
        initial_size=max(56, width // 12),
        min_size=max(32, width // 42),
    )
    eyebrow_font = _load_font("regular", max(28, width // 58))
    subtitle_font = _fit_font(
        draw,
        [source["text"]["subtitle"]],
        "regular",
        max_width=int(w * 0.72),
        max_height=int(h * 0.08),
        initial_size=max(34, width // 45),
        min_size=max(24, width // 75),
    )

    eyebrow = source["text"]["eyebrow"]
    eyebrow_w, eyebrow_h = _text_size(draw, eyebrow, eyebrow_font)
    eyebrow_y = y + int(h * 0.15)
    draw.text((cx - eyebrow_w / 2, eyebrow_y), eyebrow, font=eyebrow_font, fill=palette["muted"])
    draw.line(
        [(cx - int(w * 0.26), eyebrow_y + eyebrow_h + int(h * 0.025)), (cx + int(w * 0.26), eyebrow_y + eyebrow_h + int(h * 0.025))],
        fill=palette["accent"],
        width=max(6, width // 350),
    )

    title_top = y + int(h * 0.27)
    title_gap = max(16, width // 95)
    after_title = _draw_centered_lines(
        draw,
        title_lines,
        cx,
        title_top,
        title_font,
        palette["ink"],
        title_gap,
    )

    subtitle = source["text"]["subtitle"]
    wrapped_subtitle = textwrap.wrap(subtitle.upper(), width=28)[:2] or [subtitle.upper()]
    subtitle_top = after_title + int(h * 0.035)
    _draw_centered_lines(
        draw,
        wrapped_subtitle,
        cx,
        subtitle_top,
        subtitle_font,
        palette["muted"],
        max(8, width // 180),
    )

    _draw_motif(draw, source["candidate"], bounds, palette)

    final_png_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(final_png_path, format="PNG", optimize=True)

    file_size_bytes = final_png_path.stat().st_size
    return {
        "renderer": "local_pillow_v1",
        "rendered_at": "deterministic",
        "final_png": _relative_path(final_png_path),
        "width": width,
        "height": height,
        "file_size_bytes": file_size_bytes,
        "file_size_mb": round(file_size_bytes / (1024 * 1024), 3),
        "transparent": True,
        "alpha_mode": "RGBA",
        "external_services_used": False,
    }


def generate_design_brief(
    candidate: NicheCandidate,
    product: ProductResolution,
    draft_id: str,
) -> dict[str, Any]:
    margin_x = int(product.width * 0.12)
    margin_y = int(product.height * 0.15)
    design_dir = DATA_DIR / "designs" / draft_id
    source_path = design_dir / "source.json"
    render_metadata_path = design_dir / "render_metadata.json"
    final_png_path = design_dir / "final.png"
    palette = _palette_for(candidate)
    source = {
        "draft_id": draft_id,
        "generator": "local_deterministic_artwork_v1",
        "canvas": {"width": product.width, "height": product.height},
        "placement": "large_front",
        "placement_metadata": {
            "placement": "large_front",
            "canvas": {"width": product.width, "height": product.height},
            "intended_design_bounds": {
                "x": margin_x,
                "y": margin_y,
                "width": product.width - (margin_x * 2),
                "height": product.height - (margin_y * 2),
            },
        },
        "palette": {key: list(value) for key, value in palette.items()},
        "candidate": {
            "candidate_id": candidate.candidate_id,
            "niche": candidate.niche,
            "audience": candidate.audience,
            "keywords": candidate.keywords,
            "design_angle": candidate.design_angle,
        },
        "text": {
            "eyebrow": "ORIGINAL LOCAL DESIGN",
            "title": _safe_text(candidate.niche, 48),
            "title_lines": _wrap_title(_safe_text(candidate.niche, 48)),
            "subtitle": _safe_text(candidate.audience, 64),
        },
        "safety": {
            "external_image_generation_used": False,
            "amazon_interaction_used": False,
            "must_avoid": [
                "trademarks",
                "brand names",
                "celebrity likeness",
                "product type words in artwork",
            ],
        },
    }
    design_dir.mkdir(parents=True, exist_ok=True)
    _write_json(source_path, source)
    render_metadata = _render_design(source, final_png_path)
    _write_json(render_metadata_path, render_metadata)

    return {
        "final_png": render_metadata["final_png"],
        "source": _relative_path(source_path),
        "render_metadata": _relative_path(render_metadata_path),
        "width": product.width,
        "height": product.height,
        "transparent": True,
        "file_size_mb": render_metadata["file_size_mb"],
        "placement": "large_front",
        "placement_metadata": {
            "placement": "large_front",
            "canvas": {"width": product.width, "height": product.height},
            "intended_design_bounds": {
                "x": margin_x,
                "y": margin_y,
                "width": product.width - (margin_x * 2),
                "height": product.height - (margin_y * 2),
            },
        },
        "theme": candidate.design_angle,
        "brief": {
            "candidate_id": candidate.candidate_id,
            "niche": candidate.niche,
            "audience": candidate.audience,
            "style": "clean printable illustration with transparent background",
            "palette": list(palette.keys()),
            "must_avoid": [
                "trademarks",
                "brand names",
                "celebrity likeness",
                "product type words in artwork",
            ],
            "generation_status": "rendered_locally",
            "renderer": render_metadata["renderer"],
            "external_services_used": False,
        },
    }
