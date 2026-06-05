from __future__ import annotations

import json
import tarfile

import pytest
from fastapi.testclient import TestClient

from app.db.database import get_connection
from app.main import app
from app.services.config_service import validate_config_contracts
from app.services.local_operations import (
    export_local_packages,
    reset_database,
    restore_local_package_export,
)


client = TestClient(app)


def test_phase7_migrations_create_projection_tables_and_backfill_seed_data() -> None:
    with get_connection() as connection:
        tables = {
            row["name"]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        assert {
            "schema_migrations",
            "drafts",
            "runs",
            "draft_events",
            "validation_results",
            "listing_groups",
            "design_artifacts",
            "amazon_draft_attempts",
        }.issubset(tables)

        migrations = {
            row["version"]
            for row in connection.execute("SELECT version FROM schema_migrations").fetchall()
        }
        assert {1, 2}.issubset(migrations)

        listing_count = connection.execute(
            "SELECT COUNT(*) AS count FROM listing_groups WHERE draft_id = ?",
            ("drf_20260605_0001",),
        ).fetchone()["count"]
        validation_count = connection.execute(
            "SELECT COUNT(*) AS count FROM validation_results WHERE draft_id = ?",
            ("drf_20260605_0001",),
        ).fetchone()["count"]

    assert listing_count >= 1
    assert validation_count >= 1


def test_autopilot_created_package_is_projected_into_phase7_tables() -> None:
    response = client.post(
        "/api/workflows/autopilot/run",
        json={
            "count": 1,
            "default_product": "standard_tshirt",
            "explore_marketplaces": True,
            "touch_amazon": False,
        },
    )
    assert response.status_code == 200
    draft_id = response.json()["createdDraftIds"][0]

    with get_connection() as connection:
        listing = connection.execute(
            "SELECT design_title FROM listing_groups WHERE draft_id = ? AND language = ?",
            (draft_id, "English"),
        ).fetchone()
        validation = connection.execute(
            "SELECT passed FROM validation_results WHERE draft_id = ? AND check_name = ?",
            (draft_id, "png_valid"),
        ).fetchone()
        artifact = connection.execute(
            "SELECT path FROM design_artifacts WHERE draft_id = ? AND artifact_type = ?",
            (draft_id, "final_png"),
        ).fetchone()

    assert listing is not None
    assert listing["design_title"]
    assert validation is not None
    assert validation["passed"] == 1
    assert artifact is not None
    assert artifact["path"].endswith("/final.png")


def test_amazon_draft_dry_run_attempt_is_audited_locally_only() -> None:
    run_response = client.post(
        "/api/workflows/autopilot/run",
        json={
            "count": 1,
            "default_product": "standard_tshirt",
            "explore_marketplaces": True,
            "touch_amazon": False,
        },
    )
    assert run_response.status_code == 200
    draft_id = run_response.json()["createdDraftIds"][0]

    response = client.post(f"/api/drafts/{draft_id}/amazon-draft")
    assert response.status_code == 200
    job_id = response.json()["jobId"]

    with get_connection() as connection:
        attempt = connection.execute(
            """
            SELECT mode, status, payload
            FROM amazon_draft_attempts
            WHERE draft_id = ? AND job_id = ?
            """,
            (draft_id, job_id),
        ).fetchone()

    assert attempt is not None
    payload = json.loads(attempt["payload"])
    assert attempt["mode"] == "playwright_dry_run"
    assert attempt["status"] == "AMAZON_DRAFT_DRY_RUN_COMPLETED"
    assert payload["touch_amazon"] is False
    assert payload["save_draft_clicked"] is False


def test_config_validation_accepts_current_yaml_contracts() -> None:
    validate_config_contracts()


def test_export_local_packages_contains_manifest_and_payload() -> None:
    export_path = export_local_packages(["drf_20260605_0001"])

    assert export_path.is_file()
    with tarfile.open(export_path, "r:gz") as archive:
        names = set(archive.getnames())
        assert "manifest.json" in names
        assert "drafts/drf_20260605_0001/draft_payload.json" in names
        manifest_file = archive.extractfile("manifest.json")
        assert manifest_file is not None
        manifest = json.loads(manifest_file.read().decode("utf-8"))

    assert manifest["draft_count"] == 1
    assert manifest["drafts"][0]["draft_id"] == "drf_20260605_0001"
    assert "restore" in manifest["restore_note"].lower()


def test_reset_database_requires_explicit_force_flag() -> None:
    with pytest.raises(ValueError):
        reset_database(force=False)


def test_restore_export_requires_explicit_force_flag() -> None:
    with pytest.raises(ValueError):
        restore_local_package_export(export_local_packages(["drf_20260605_0001"]), force=False)
