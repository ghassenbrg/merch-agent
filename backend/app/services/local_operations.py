from __future__ import annotations

import json
import io
import shutil
import tarfile
from datetime import UTC, datetime
from pathlib import Path

from app.core.paths import DATA_DIR, DATABASE_PATH, ensure_data_directories
from app.db.database import init_database, seed_database
from app.db.database import get_connection


def _stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def backup_database(label: str = "manual") -> Path | None:
    ensure_data_directories()
    if not DATABASE_PATH.exists():
        return None
    backup_path = DATA_DIR / "backups" / f"merch_agent_{label}_{_stamp()}.sqlite3"
    shutil.copy2(DATABASE_PATH, backup_path)
    return backup_path


def reset_database(*, force: bool, backup: bool = True) -> dict[str, str | None]:
    if not force:
        raise ValueError("reset_database requires force=True to protect local package data.")
    backup_path = backup_database("pre_reset") if backup else None
    if DATABASE_PATH.exists():
        DATABASE_PATH.unlink()
    init_database()
    seed_database()
    return {
        "database": str(DATABASE_PATH),
        "backup": str(backup_path) if backup_path else None,
    }


def export_local_packages(draft_ids: list[str] | None = None) -> Path:
    ensure_data_directories()
    selected_ids = set(draft_ids or [])
    with get_connection() as connection:
        if selected_ids:
            placeholders = ",".join("?" for _ in selected_ids)
            rows = connection.execute(
                f"SELECT draft_id, status, title, payload FROM drafts WHERE draft_id IN ({placeholders}) ORDER BY draft_id ASC",
                tuple(sorted(selected_ids)),
            ).fetchall()
        else:
            rows = connection.execute(
                "SELECT draft_id, status, title, payload FROM drafts ORDER BY draft_id ASC"
            ).fetchall()

    export_path = DATA_DIR / "exports" / f"merch_packages_{_stamp()}.tar.gz"
    manifest = {
        "created_at": datetime.now(UTC).isoformat(),
        "draft_count": len(rows),
        "drafts": [
            {
                "draft_id": row["draft_id"],
                "status": row["status"],
                "title": row["title"],
            }
            for row in rows
        ],
        "restore_note": (
            "This export is inspection-first. It includes draft payloads, package artifacts, "
            "and a database snapshot when present; restore by copying the database snapshot "
            "back to data/merch_agent.sqlite3 after taking a fresh backup."
        ),
    }
    manifest_bytes = json.dumps(manifest, indent=2, sort_keys=True).encode("utf-8")

    with tarfile.open(export_path, "w:gz") as archive:
        info = tarfile.TarInfo("manifest.json")
        info.size = len(manifest_bytes)
        info.mtime = int(datetime.now(UTC).timestamp())
        archive.addfile(info, fileobj=io.BytesIO(manifest_bytes))

        if DATABASE_PATH.exists():
            archive.add(DATABASE_PATH, arcname="database/merch_agent.sqlite3")

        for row in rows:
            draft_id = row["draft_id"]
            payload_bytes = row["payload"].encode("utf-8")
            payload_info = tarfile.TarInfo(f"drafts/{draft_id}/draft_payload.json")
            payload_info.size = len(payload_bytes)
            payload_info.mtime = int(datetime.now(UTC).timestamp())
            archive.addfile(payload_info, fileobj=io.BytesIO(payload_bytes))

            artifact_dir = DATA_DIR / "drafts" / draft_id
            if artifact_dir.is_dir():
                archive.add(artifact_dir, arcname=f"drafts/{draft_id}/artifacts")

    return export_path


def restore_local_package_export(
    export_path: Path,
    *,
    force: bool,
    backup: bool = True,
) -> dict[str, str | None]:
    if not force:
        raise ValueError("restore_local_package_export requires force=True to protect local package data.")
    ensure_data_directories()
    backup_path = backup_database("pre_restore") if backup else None
    with tarfile.open(export_path, "r:gz") as archive:
        database_member = archive.extractfile("database/merch_agent.sqlite3")
        if database_member is None:
            raise ValueError("Export does not contain database/merch_agent.sqlite3.")
        DATABASE_PATH.write_bytes(database_member.read())

        for member in archive.getmembers():
            if not member.name.startswith("drafts/") or not member.isfile():
                continue
            parts = Path(member.name).parts
            if len(parts) < 4 or parts[2] != "artifacts":
                continue
            draft_id = parts[1]
            relative_artifact_path = Path(*parts[3:])
            target_path = DATA_DIR / "drafts" / draft_id / relative_artifact_path
            target_path.parent.mkdir(parents=True, exist_ok=True)
            source = archive.extractfile(member)
            if source is not None:
                target_path.write_bytes(source.read())

    return {
        "database": str(DATABASE_PATH),
        "backup": str(backup_path) if backup_path else None,
    }
