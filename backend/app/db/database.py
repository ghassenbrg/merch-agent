from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from typing import Iterator

from app.core.paths import DATABASE_PATH, ensure_data_directories
from app.fixtures.sample_data import SAMPLE_DRAFTS


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
            """
        )


def seed_database() -> None:
    with get_connection() as connection:
        existing = connection.execute("SELECT COUNT(*) AS count FROM drafts").fetchone()
        if existing and existing["count"] > 0:
            return

        for draft in SAMPLE_DRAFTS:
            connection.execute(
                """
                INSERT INTO drafts (draft_id, status, title, score, payload)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    draft["draft_id"],
                    draft["status"],
                    draft["listing_groups"]["English"]["design_title"],
                    draft["score"]["overall"],
                    json.dumps(draft),
                ),
            )
