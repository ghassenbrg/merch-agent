from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from typing import Iterator

from app.core.paths import DATABASE_PATH, ensure_data_directories
from app.fixtures.sample_data import SAMPLE_DRAFTS
from app.fixtures.sample_artifacts import ensure_sample_artifacts
from app.models.schemas import Draft
from app.db.repositories import insert_draft_event, upsert_draft_projection


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    ensure_data_directories()
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def init_database() -> None:
    ensure_data_directories()
    with get_connection() as connection:
        _apply_migrations(connection)


def _apply_migrations(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    applied = {
        row["version"]
        for row in connection.execute("SELECT version FROM schema_migrations").fetchall()
    }
    migrations = [
        (1, "initial_core_tables", _migration_initial_core_tables),
        (2, "project_draft_subdocuments", _migration_project_draft_subdocuments),
    ]
    for version, name, migration in migrations:
        if version in applied:
            continue
        migration(connection)
        connection.execute(
            "INSERT INTO schema_migrations (version, name) VALUES (?, ?)",
            (version, name),
        )


def _table_columns(connection: sqlite3.Connection, table_name: str) -> set[str]:
    return {
        row["name"]
        for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    }


def _add_column_if_missing(
    connection: sqlite3.Connection,
    table_name: str,
    column_name: str,
    column_sql: str,
) -> None:
    if column_name not in _table_columns(connection, table_name):
        connection.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_sql}")


def _migration_initial_core_tables(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS drafts (
            draft_id TEXT PRIMARY KEY,
            status TEXT NOT NULL,
            title TEXT NOT NULL,
            score REAL NOT NULL,
            payload TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS runs (
            run_id TEXT PRIMARY KEY,
            mode TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            completed_at TEXT
        );

        CREATE TABLE IF NOT EXISTS run_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            level TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS run_drafts (
            run_id TEXT NOT NULL,
            draft_id TEXT NOT NULL,
            PRIMARY KEY (run_id, draft_id)
        );

        CREATE TABLE IF NOT EXISTS draft_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            draft_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            from_status TEXT,
            to_status TEXT,
            message TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            payload TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """
    )


def _migration_project_draft_subdocuments(connection: sqlite3.Connection) -> None:
    _add_column_if_missing(
        connection,
        "run_logs",
        "context",
        "context TEXT NOT NULL DEFAULT '{}'",
    )
    _add_column_if_missing(
        connection,
        "draft_events",
        "metadata",
        "metadata TEXT NOT NULL DEFAULT '{}'",
    )
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS listing_groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            draft_id TEXT NOT NULL,
            language TEXT NOT NULL,
            design_title TEXT NOT NULL,
            brand TEXT NOT NULL,
            feature_bullet_1 TEXT NOT NULL,
            feature_bullet_2 TEXT NOT NULL,
            product_description TEXT NOT NULL,
            marketplaces TEXT NOT NULL,
            payload TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(draft_id, language)
        );

        CREATE TABLE IF NOT EXISTS validation_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            draft_id TEXT NOT NULL,
            check_name TEXT NOT NULL,
            passed INTEGER NOT NULL,
            severity TEXT NOT NULL,
            payload TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(draft_id, check_name)
        );

        CREATE TABLE IF NOT EXISTS design_artifacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            draft_id TEXT NOT NULL,
            artifact_type TEXT NOT NULL,
            path TEXT NOT NULL,
            payload TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(draft_id, artifact_type, path)
        );

        CREATE TABLE IF NOT EXISTS amazon_draft_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            draft_id TEXT NOT NULL,
            job_id TEXT NOT NULL,
            mode TEXT NOT NULL,
            status TEXT NOT NULL,
            message TEXT NOT NULL,
            payload TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_listing_groups_draft_id
            ON listing_groups(draft_id);
        CREATE INDEX IF NOT EXISTS idx_validation_results_draft_id
            ON validation_results(draft_id);
        CREATE INDEX IF NOT EXISTS idx_design_artifacts_draft_id
            ON design_artifacts(draft_id);
        CREATE INDEX IF NOT EXISTS idx_amazon_draft_attempts_draft_id
            ON amazon_draft_attempts(draft_id);
        """
    )
    _backfill_draft_projections(connection)


def _backfill_draft_projections(connection: sqlite3.Connection) -> None:
    rows = connection.execute("SELECT payload FROM drafts").fetchall()
    for row in rows:
        draft = Draft.model_validate(json.loads(row["payload"]))
        upsert_draft_projection(connection, draft)


def seed_database() -> None:
    with get_connection() as connection:
        existing = connection.execute("SELECT COUNT(*) AS count FROM drafts").fetchone()
        if existing and existing["count"] > 0:
            rows = connection.execute("SELECT draft_id, status FROM drafts").fetchall()
            for row in rows:
                event = connection.execute(
                    "SELECT id FROM draft_events WHERE draft_id = ? LIMIT 1",
                    (row["draft_id"],),
                ).fetchone()
                if event is None:
                    connection.execute(
                        """
                        INSERT INTO draft_events (draft_id, event_type, from_status, to_status, message)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            row["draft_id"],
                            "backfilled",
                            None,
                            row["status"],
                            "Existing draft imported into status history.",
                        ),
                    )
            sample_ids = {draft["draft_id"] for draft in SAMPLE_DRAFTS}
            sample_rows = connection.execute(
                "SELECT payload FROM drafts WHERE draft_id IN (?, ?)",
                tuple(sorted(sample_ids)),
            ).fetchall()
            ensure_sample_artifacts([json.loads(row["payload"]) for row in sample_rows])
            return

        for draft in SAMPLE_DRAFTS:
            draft_model = Draft.model_validate(draft)
            upsert_draft_projection(connection, draft_model)
            insert_draft_event(
                connection,
                draft_model.draft_id,
                "seeded",
                "Seed draft loaded for local dashboard review.",
                None,
                draft_model.status,
            )
        ensure_sample_artifacts(SAMPLE_DRAFTS)
