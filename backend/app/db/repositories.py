from __future__ import annotations

import json
from typing import Any

import sqlite3

from app.models.schemas import Draft


def _json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True)


def upsert_draft_projection(connection: sqlite3.Connection, draft: Draft) -> None:
    """Project draft subdocuments into queryable local tables."""
    connection.execute(
        """
        INSERT INTO drafts (draft_id, status, title, score, payload)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(draft_id) DO UPDATE SET
            status = excluded.status,
            title = excluded.title,
            score = excluded.score,
            payload = excluded.payload,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            draft.draft_id,
            draft.status,
            draft.listing_groups["English"]["design_title"],
            draft.score["overall"],
            draft.model_dump_json(),
        ),
    )
    replace_listing_groups(connection, draft)
    replace_validation_results(connection, draft)
    replace_design_artifacts(connection, draft)


def replace_listing_groups(connection: sqlite3.Connection, draft: Draft) -> None:
    connection.execute("DELETE FROM listing_groups WHERE draft_id = ?", (draft.draft_id,))
    for language, listing in draft.listing_groups.items():
        connection.execute(
            """
            INSERT INTO listing_groups (
                draft_id, language, design_title, brand, feature_bullet_1,
                feature_bullet_2, product_description, marketplaces, payload
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                draft.draft_id,
                language,
                listing.get("design_title", ""),
                listing.get("brand", ""),
                listing.get("feature_bullet_1", ""),
                listing.get("feature_bullet_2", ""),
                listing.get("product_description", ""),
                _json(listing.get("marketplaces", [])),
                _json(listing),
            ),
        )


def replace_validation_results(connection: sqlite3.Connection, draft: Draft) -> None:
    connection.execute("DELETE FROM validation_results WHERE draft_id = ?", (draft.draft_id,))
    for check_name, passed in draft.validation.items():
        connection.execute(
            """
            INSERT INTO validation_results (draft_id, check_name, passed, severity, payload)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                draft.draft_id,
                check_name,
                int(bool(passed)),
                "error" if not bool(passed) else "info",
                _json({"source": "validation", "value": passed}),
            ),
        )
    for check_name, value in draft.listing_validation.items():
        if check_name == "warnings":
            continue
        connection.execute(
            """
            INSERT INTO validation_results (draft_id, check_name, passed, severity, payload)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                draft.draft_id,
                f"listing.{check_name}",
                int(bool(value)),
                "error" if not bool(value) else "info",
                _json({"source": "listing_validation", "value": value}),
            ),
        )


def replace_design_artifacts(connection: sqlite3.Connection, draft: Draft) -> None:
    connection.execute("DELETE FROM design_artifacts WHERE draft_id = ?", (draft.draft_id,))
    for artifact_type, path_key in [
        ("final_png", "final_png"),
        ("source", "source"),
        ("render_metadata", "render_metadata"),
    ]:
        path_value = draft.design.get(path_key)
        if not path_value:
            continue
        connection.execute(
            """
            INSERT INTO design_artifacts (draft_id, artifact_type, path, payload)
            VALUES (?, ?, ?, ?)
            """,
            (
                draft.draft_id,
                artifact_type,
                str(path_value),
                _json({"design": draft.design, "path_key": path_key}),
            ),
        )


def insert_draft_event(
    connection: sqlite3.Connection,
    draft_id: str,
    event_type: str,
    message: str,
    from_status: str | None = None,
    to_status: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    connection.execute(
        """
        INSERT INTO draft_events (
            draft_id, event_type, from_status, to_status, message, metadata
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (draft_id, event_type, from_status, to_status, message, _json(metadata or {})),
    )


def insert_run_log(
    connection: sqlite3.Connection,
    run_id: str,
    level: str,
    message: str,
    context: dict[str, Any] | None = None,
) -> None:
    connection.execute(
        "INSERT INTO run_logs (run_id, level, message, context) VALUES (?, ?, ?, ?)",
        (run_id, level, message, _json(context or {})),
    )


def insert_amazon_draft_attempt(
    connection: sqlite3.Connection,
    draft_id: str,
    job_id: str,
    mode: str,
    status: str,
    message: str,
    payload: dict[str, Any] | None = None,
) -> None:
    connection.execute(
        """
        INSERT INTO amazon_draft_attempts (draft_id, job_id, mode, status, message, payload)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (draft_id, job_id, mode, status, message, _json(payload or {})),
    )
