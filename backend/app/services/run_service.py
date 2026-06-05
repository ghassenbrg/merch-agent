from app.db.database import get_connection
from app.models.schemas import RunDetail, RunLog, RunSummary


def _status_outcomes(run_id: str) -> dict[str, int]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT d.status, COUNT(*) AS count
            FROM run_drafts rd
            JOIN drafts d ON d.draft_id = rd.draft_id
            WHERE rd.run_id = ?
            GROUP BY d.status
            ORDER BY d.status ASC
            """,
            (run_id,),
        ).fetchall()
    return {row["status"]: row["count"] for row in rows}


def list_runs() -> list[RunSummary]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                r.run_id,
                r.mode,
                r.status,
                r.created_at,
                r.completed_at,
                COUNT(rd.draft_id) AS generated_draft_count
            FROM runs r
            LEFT JOIN run_drafts rd ON rd.run_id = r.run_id
            GROUP BY r.run_id
            ORDER BY r.created_at DESC
            """
        ).fetchall()

    return [
        RunSummary(
            runId=row["run_id"],
            mode=row["mode"],
            status=row["status"],
            created_at=row["created_at"],
            completed_at=row["completed_at"],
            generatedDraftCount=row["generated_draft_count"],
            statusOutcomes=_status_outcomes(row["run_id"]),
        )
        for row in rows
    ]


def get_run(run_id: str) -> RunDetail | None:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT
                r.run_id,
                r.mode,
                r.status,
                r.created_at,
                r.completed_at,
                COUNT(rd.draft_id) AS generated_draft_count
            FROM runs r
            LEFT JOIN run_drafts rd ON rd.run_id = r.run_id
            WHERE r.run_id = ?
            GROUP BY r.run_id
            """,
            (run_id,),
        ).fetchone()
        draft_rows = connection.execute(
            "SELECT draft_id FROM run_drafts WHERE run_id = ? ORDER BY draft_id ASC",
            (run_id,),
        ).fetchall()

    if row is None:
        return None

    return RunDetail(
        runId=row["run_id"],
        mode=row["mode"],
        status=row["status"],
        created_at=row["created_at"],
        completed_at=row["completed_at"],
        generatedDraftCount=row["generated_draft_count"],
        statusOutcomes=_status_outcomes(run_id),
        createdDraftIds=[draft_row["draft_id"] for draft_row in draft_rows],
        logs=get_run_logs(run_id),
    )


def get_run_logs(run_id: str) -> list[RunLog]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT run_id, level, message, created_at
            FROM run_logs
            WHERE run_id = ?
            ORDER BY id ASC
            """,
            (run_id,),
        ).fetchall()
    return [RunLog(**dict(row)) for row in rows]
