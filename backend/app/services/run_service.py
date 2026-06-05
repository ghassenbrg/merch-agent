from app.db.database import get_connection
from app.models.schemas import RunLog


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
