from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler
from typing import Any

from app.core.paths import DATA_DIR, ensure_data_directories
from app.core.settings import get_settings


class JsonLineFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname.lower(),
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        for key in ("run_id", "draft_id", "event", "phase"):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        return json.dumps(payload, sort_keys=True)


def _prune_old_logs(retention_days: int) -> None:
    cutoff = datetime.now(UTC).timestamp() - (retention_days * 24 * 60 * 60)
    for path in (DATA_DIR / "logs").glob("*.json*"):
        try:
            if path.stat().st_mtime < cutoff:
                path.unlink()
        except OSError:
            continue


def configure_logging() -> None:
    ensure_data_directories()
    settings = get_settings()
    _prune_old_logs(settings.log_retention_days)
    root_logger = logging.getLogger("merch_agent")
    root_logger.setLevel(logging.INFO)
    root_logger.propagate = False
    if root_logger.handlers:
        return

    formatter = JsonLineFormatter()
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    file_handler = RotatingFileHandler(
        DATA_DIR / "logs" / "backend.jsonl",
        maxBytes=settings.log_max_bytes,
        backupCount=settings.log_backup_count,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    root_logger.addHandler(stream_handler)
    root_logger.addHandler(file_handler)
