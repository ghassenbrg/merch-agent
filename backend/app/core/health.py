from __future__ import annotations

from app.core.paths import DATA_DIR, ensure_data_directories
from app.core.settings import get_settings
from app.db.database import get_connection
from app.services.config_service import validate_config_contracts


def readiness_status() -> dict[str, object]:
    checks: dict[str, object] = {}
    try:
        ensure_data_directories()
        checks["data_dir"] = DATA_DIR.is_dir()
    except OSError as exc:
        checks["data_dir"] = str(exc)

    try:
        validate_config_contracts()
        checks["config"] = True
    except Exception as exc:
        checks["config"] = str(exc)

    try:
        with get_connection() as connection:
            connection.execute("SELECT 1").fetchone()
        checks["database"] = True
    except Exception as exc:
        checks["database"] = str(exc)

    status = "ok" if all(value is True for value in checks.values()) else "degraded"
    return {
        "status": status,
        "checks": checks,
        "runtime": get_settings().public_status(),
    }
