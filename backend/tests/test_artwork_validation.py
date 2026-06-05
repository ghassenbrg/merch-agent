from __future__ import annotations

from pathlib import Path
from typing import Any

from app.services.artwork_validation_service import (
    artwork_validation_flags,
    validate_artwork_png,
)
from app.services.config_service import get_config


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "pngs"


def _metadata(width: int = 1200, height: int = 1200, placement: str = "large_front") -> dict[str, Any]:
    return {
        "placement": placement,
        "placement_metadata": {
            "placement": placement,
            "canvas": {"width": width, "height": height},
            "intended_design_bounds": {
                "x": int(width * 0.25),
                "y": int(height * 0.2),
                "width": int(width * 0.5),
                "height": int(height * 0.6),
            },
        },
    }


def _validation_config() -> dict[str, Any]:
    return get_config().validation


def _validate(filename: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    return validate_artwork_png(
        png_path=FIXTURE_DIR / filename,
        expected_width=1200,
        expected_height=1200,
        design_metadata=metadata or _metadata(),
        validation_config=_validation_config(),
    )


def test_valid_png_passes_all_artwork_checks() -> None:
    report = _validate("valid_1200.png")

    assert report["status"] == "passed"
    assert all(artwork_validation_flags(report).values())
    assert report["actual"]["design_bounds"] == {
        "x": 300,
        "y": 250,
        "width": 601,
        "height": 701,
    }


def test_wrong_dimensions_fail_resolution_check() -> None:
    report = _validate("wrong_dimensions.png")

    assert report["status"] == "failed"
    assert report["checks"]["correct_resolution"]["passed"] is False
    assert artwork_validation_flags(report)["correct_resolution"] is False


def test_opaque_background_fails_transparency_check() -> None:
    report = _validate("opaque_background.png")

    assert report["status"] == "failed"
    assert report["checks"]["transparent_background"]["passed"] is False
    assert artwork_validation_flags(report)["transparent_background"] is False


def test_file_size_limit_is_config_driven() -> None:
    config = _validation_config()
    strict_config = {
        **config,
        "artwork": {
            **config["artwork"],
            "max_file_size_mb": 0.000001,
        },
    }

    report = validate_artwork_png(
        png_path=FIXTURE_DIR / "valid_1200.png",
        expected_width=1200,
        expected_height=1200,
        design_metadata=_metadata(),
        validation_config=strict_config,
    )

    assert report["status"] == "failed"
    assert report["checks"]["file_size_under_limit"]["passed"] is False
    assert artwork_validation_flags(report)["file_size_under_limit"] is False


def test_missing_placement_metadata_fails_contract() -> None:
    report = _validate("valid_1200.png", metadata={"placement": "large_front"})

    assert report["status"] == "failed"
    assert report["checks"]["placement_metadata_valid"]["passed"] is False
    assert artwork_validation_flags(report)["placement_metadata_valid"] is False


def test_too_small_design_fails_minimum_bounds_check() -> None:
    report = _validate("too_small.png")

    assert report["status"] == "failed"
    assert report["checks"]["design_not_too_small"]["passed"] is False
    assert artwork_validation_flags(report)["design_not_too_small"] is False


def test_cropped_design_fails_edge_margin_check() -> None:
    report = _validate("cropped.png")

    assert report["status"] == "failed"
    assert report["checks"]["design_not_cropped"]["passed"] is False
    assert artwork_validation_flags(report)["design_not_cropped"] is False


def test_missing_png_is_explicit_artwork_pending() -> None:
    report = validate_artwork_png(
        png_path=FIXTURE_DIR / "missing.png",
        expected_width=1200,
        expected_height=1200,
        design_metadata=_metadata(),
        validation_config=_validation_config(),
    )

    assert report["status"] == "pending"
    assert report["checks"]["png_present"]["passed"] is False
    assert artwork_validation_flags(report)["png_valid"] is False
