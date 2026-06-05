from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image, UnidentifiedImageError

from app.core.paths import REPO_ROOT


ARTWORK_FLAG_KEYS = [
    "png_valid",
    "transparent_background",
    "correct_resolution",
    "file_size_under_limit",
    "placement_metadata_valid",
    "design_not_too_small",
    "design_not_cropped",
]


def _resolve_path(png_path: str | Path | None) -> Path | None:
    if not png_path:
        return None
    path = Path(png_path)
    if not path.is_absolute():
        path = REPO_ROOT / path
    return path.resolve()


def _artwork_config(validation_config: dict[str, Any]) -> dict[str, Any]:
    return validation_config.get("artwork", {})


def _thresholds(validation_config: dict[str, Any]) -> dict[str, Any]:
    artwork = _artwork_config(validation_config)
    return {
        "max_file_size_mb": float(artwork.get("max_file_size_mb", 25)),
        "min_design_width_ratio": float(artwork.get("min_design_width_ratio", 0.25)),
        "min_design_height_ratio": float(artwork.get("min_design_height_ratio", 0.25)),
        "min_design_area_ratio": float(artwork.get("min_design_area_ratio", 0.08)),
        "min_edge_margin_px": int(artwork.get("min_edge_margin_px", 20)),
        "transparent_alpha_threshold": int(artwork.get("transparent_alpha_threshold", 0)),
        "allowed_placements": list(artwork.get("allowed_placements", ["large_front"])),
    }


def _check(passed: bool, message: str) -> dict[str, Any]:
    return {"passed": passed, "message": message}


def _empty_checks(message: str) -> dict[str, dict[str, Any]]:
    return {
        "png_present": _check(False, message),
        "correct_resolution": _check(False, "PNG dimensions were not inspected."),
        "transparent_background": _check(False, "PNG transparency was not inspected."),
        "file_size_under_limit": _check(False, "PNG file size was not inspected."),
        "placement_metadata_valid": _check(False, "Placement metadata was not inspected."),
        "design_not_too_small": _check(False, "Design bounds were not inspected."),
        "design_not_cropped": _check(False, "Design bounds were not inspected."),
    }


def _placement_metadata_check(
    design_metadata: dict[str, Any],
    expected_width: int,
    expected_height: int,
    allowed_placements: list[str],
) -> dict[str, Any]:
    placement = design_metadata.get("placement")
    metadata = design_metadata.get("placement_metadata")
    if placement not in allowed_placements:
        return _check(False, f"Placement {placement!r} is not allowed.")
    if not isinstance(metadata, dict):
        return _check(False, "Placement metadata is missing.")
    if metadata.get("placement") not in (None, placement):
        return _check(False, "Placement metadata does not match design placement.")
    canvas = metadata.get("canvas")
    if not isinstance(canvas, dict):
        return _check(False, "Placement metadata canvas is missing.")
    if canvas.get("width") != expected_width or canvas.get("height") != expected_height:
        return _check(False, "Placement metadata canvas does not match the product template.")
    return _check(True, "Placement metadata matches the product template.")


def _alpha_bounds(image: Image.Image) -> tuple[int, int, int, int] | None:
    rgba = image.convert("RGBA")
    return rgba.getchannel("A").getbbox()


def _background_transparency_check(image: Image.Image, alpha_threshold: int) -> dict[str, Any]:
    rgba = image.convert("RGBA")
    alpha = rgba.getchannel("A")
    min_alpha, max_alpha = alpha.getextrema()
    width, height = rgba.size
    corners = [
        alpha.getpixel((0, 0)),
        alpha.getpixel((width - 1, 0)),
        alpha.getpixel((0, height - 1)),
        alpha.getpixel((width - 1, height - 1)),
    ]
    transparent_corners = all(value <= alpha_threshold for value in corners)
    has_transparency = min_alpha <= alpha_threshold and max_alpha > alpha_threshold
    passed = transparent_corners and has_transparency
    message = (
        "PNG has transparent background corners and visible artwork."
        if passed
        else "PNG must have transparent background corners and visible non-transparent artwork."
    )
    return _check(passed, message)


def validate_artwork_png(
    png_path: str | Path | None,
    expected_width: int,
    expected_height: int,
    design_metadata: dict[str, Any],
    validation_config: dict[str, Any],
) -> dict[str, Any]:
    resolved_path = _resolve_path(png_path)
    thresholds = _thresholds(validation_config)
    report: dict[str, Any] = {
        "status": "pending",
        "png_path": str(resolved_path) if resolved_path else None,
        "expected": {"width": expected_width, "height": expected_height},
        "actual": {},
        "thresholds": thresholds,
        "checks": {},
    }

    if resolved_path is None or not resolved_path.is_file():
        report["checks"] = _empty_checks("Final PNG is missing; artwork is pending.")
        return report

    file_size_bytes = resolved_path.stat().st_size
    max_file_size_bytes = int(thresholds["max_file_size_mb"] * 1024 * 1024)
    try:
        with Image.open(resolved_path) as image:
            image.load()
            width, height = image.size
            bounds = _alpha_bounds(image)
            report["actual"] = {
                "width": width,
                "height": height,
                "file_size_bytes": file_size_bytes,
                "design_bounds": (
                    None
                    if bounds is None
                    else {
                        "x": bounds[0],
                        "y": bounds[1],
                        "width": bounds[2] - bounds[0],
                        "height": bounds[3] - bounds[1],
                    }
                ),
            }

            correct_resolution = width == expected_width and height == expected_height
            file_size_under_limit = file_size_bytes <= max_file_size_bytes
            transparent_background = _background_transparency_check(
                image,
                thresholds["transparent_alpha_threshold"],
            )
            placement_metadata_valid = _placement_metadata_check(
                design_metadata,
                expected_width,
                expected_height,
                thresholds["allowed_placements"],
            )

            if bounds is None:
                design_not_too_small = _check(False, "No visible artwork pixels found.")
                design_not_cropped = _check(False, "No visible artwork bounds found.")
            else:
                left, top, right, bottom = bounds
                design_width = right - left
                design_height = bottom - top
                design_area_ratio = (design_width * design_height) / (width * height)
                width_ratio = design_width / width
                height_ratio = design_height / height
                min_margin = thresholds["min_edge_margin_px"]
                too_small_passed = (
                    width_ratio >= thresholds["min_design_width_ratio"]
                    and height_ratio >= thresholds["min_design_height_ratio"]
                    and design_area_ratio >= thresholds["min_design_area_ratio"]
                )
                cropped_passed = (
                    left >= min_margin
                    and top >= min_margin
                    and (width - right) >= min_margin
                    and (height - bottom) >= min_margin
                )
                design_not_too_small = _check(
                    too_small_passed,
                    (
                        "Visible design bounds meet minimum size thresholds."
                        if too_small_passed
                        else "Visible design bounds are smaller than configured thresholds."
                    ),
                )
                design_not_cropped = _check(
                    cropped_passed,
                    (
                        "Visible design bounds stay inside the configured edge margin."
                        if cropped_passed
                        else "Visible design bounds touch or cross the configured edge margin."
                    ),
                )

            report["checks"] = {
                "png_present": _check(True, "Final PNG exists."),
                "correct_resolution": _check(
                    correct_resolution,
                    (
                        "PNG dimensions match the selected product template."
                        if correct_resolution
                        else "PNG dimensions do not match the selected product template."
                    ),
                ),
                "transparent_background": transparent_background,
                "file_size_under_limit": _check(
                    file_size_under_limit,
                    (
                        "PNG file size is under the configured limit."
                        if file_size_under_limit
                        else "PNG file size exceeds the configured limit."
                    ),
                ),
                "placement_metadata_valid": placement_metadata_valid,
                "design_not_too_small": design_not_too_small,
                "design_not_cropped": design_not_cropped,
            }
    except (OSError, UnidentifiedImageError) as exc:
        report["status"] = "failed"
        report["checks"] = _empty_checks(f"Final PNG could not be inspected: {exc}.")
        return report

    passed = all(check["passed"] for check in report["checks"].values())
    report["status"] = "passed" if passed else "failed"
    return report


def artwork_validation_flags(report: dict[str, Any]) -> dict[str, bool]:
    checks = report.get("checks", {})
    return {
        "png_valid": report.get("status") == "passed",
        "transparent_background": checks.get("transparent_background", {}).get("passed") is True,
        "correct_resolution": checks.get("correct_resolution", {}).get("passed") is True,
        "file_size_under_limit": checks.get("file_size_under_limit", {}).get("passed") is True,
        "placement_metadata_valid": checks.get("placement_metadata_valid", {}).get("passed") is True,
        "design_not_too_small": checks.get("design_not_too_small", {}).get("passed") is True,
        "design_not_cropped": checks.get("design_not_cropped", {}).get("passed") is True,
    }
