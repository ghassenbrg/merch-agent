from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Lock
from typing import Any

from app.core.paths import DATA_DIR
from app.db.database import get_connection
from app.models.schemas import (
    AutopilotRequest,
    SchedulerRunResponse,
    SchedulerStatus,
    SettingsPatch,
)
from app.services.autopilot_service import run_autopilot
from app.services.config_service import get_config, update_settings


_SCHEDULER_LOCK = Lock()
logger = logging.getLogger("merch_agent.scheduler")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_sqlite_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace(" ", "T")).replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _format_utc(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _data_dir_size_mb(path: Path = DATA_DIR) -> float:
    total = 0
    if not path.exists():
        return 0.0
    for item in path.rglob("*"):
        try:
            if item.is_file():
                total += item.stat().st_size
        except OSError:
            continue
    return round(total / (1024 * 1024), 2)


def _operations_config() -> dict[str, Any]:
    settings = get_config().settings
    operations = settings.get("autopilot_operations", {})
    return operations if isinstance(operations, dict) else {}


def _last_scheduled_run() -> tuple[str | None, datetime | None]:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT run_id, completed_at, created_at
            FROM runs
            WHERE mode = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            ("scheduled_autopilot",),
        ).fetchone()
    if row is None:
        return None, None
    return row["run_id"], _parse_sqlite_timestamp(row["completed_at"] or row["created_at"])


def _scheduled_packages_today() -> int:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT COUNT(rd.draft_id) AS count
            FROM runs r
            JOIN run_drafts rd ON rd.run_id = r.run_id
            WHERE r.mode = ?
              AND date(r.created_at) = date('now')
            """,
            ("scheduled_autopilot",),
        ).fetchone()
    return int(row["count"] if row else 0)


def _bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def get_scheduler_status(running: bool | None = None) -> SchedulerStatus:
    operations = _operations_config()
    disk_usage_mb = _data_dir_size_mb()
    disk_limit_mb = float(operations.get("disk_usage_limit_mb", 2048) or 0)
    max_packages_per_day = _int(operations.get("max_packages_per_day"), 10)
    max_packages_per_run = _int(operations.get("max_packages_per_run"), 10)
    scheduled_packages_per_run = _int(operations.get("scheduled_packages_per_run"), 2)
    interval_minutes = _int(operations.get("interval_minutes"), 1440)
    cooldown_minutes = _int(operations.get("cooldown_minutes"), 60)
    last_run_id, last_completed_at = _last_scheduled_run()
    next_run_allowed_at = (
        last_completed_at + timedelta(minutes=max(0, cooldown_minutes, interval_minutes))
        if last_completed_at
        else None
    )
    now = _utc_now()
    packages_generated_today = _scheduled_packages_today()
    blocked_reasons: list[str] = []
    is_running = running if running is not None else _SCHEDULER_LOCK.locked()

    if not _bool(operations.get("scheduler_enabled"), False):
        blocked_reasons.append("scheduler disabled")
    if _bool(operations.get("stop_switch_engaged"), False):
        blocked_reasons.append("stop switch engaged")
    if is_running:
        blocked_reasons.append("scheduler job already running")
    if disk_limit_mb <= 0 or disk_usage_mb > disk_limit_mb:
        blocked_reasons.append("disk usage limit exceeded")
    if max_packages_per_run <= 0 or scheduled_packages_per_run <= 0:
        blocked_reasons.append("package run limit is zero")
    if max_packages_per_day <= 0 or packages_generated_today >= max_packages_per_day:
        blocked_reasons.append("daily package limit reached")
    if next_run_allowed_at and now < next_run_allowed_at:
        blocked_reasons.append("cooldown active")

    return SchedulerStatus(
        schedulerEnabled=_bool(operations.get("scheduler_enabled"), False),
        stopSwitchEngaged=_bool(operations.get("stop_switch_engaged"), False),
        running=is_running,
        diskUsageMb=disk_usage_mb,
        diskLimitMb=disk_limit_mb,
        packagesGeneratedToday=packages_generated_today,
        maxPackagesPerDay=max_packages_per_day,
        maxPackagesPerRun=max_packages_per_run,
        scheduledPackagesPerRun=scheduled_packages_per_run,
        intervalMinutes=interval_minutes,
        cooldownMinutes=cooldown_minutes,
        nextRunAllowedAt=_format_utc(next_run_allowed_at),
        lastScheduledRunId=last_run_id,
        blockedReasons=blocked_reasons,
    )


def _stop_requested() -> bool:
    operations = _operations_config()
    return _bool(operations.get("stop_switch_engaged"), False)


def run_scheduler_tick() -> SchedulerRunResponse:
    if not _SCHEDULER_LOCK.acquire(blocking=False):
        status = get_scheduler_status(running=True)
        return SchedulerRunResponse(
            status="RUNNING",
            message="A scheduled autopilot job is already running.",
            scheduler=status,
        )

    try:
        before = get_scheduler_status(running=True)
        actionable_blockers = [
            reason
            for reason in before.blocked_reasons
            if reason != "scheduler job already running"
        ]
        if actionable_blockers:
            return SchedulerRunResponse(
                status="SKIPPED",
                message=f"Scheduled autopilot skipped: {'; '.join(actionable_blockers)}.",
                scheduler=before,
            )

        operations = _operations_config()
        remaining_today = max(0, before.max_packages_per_day - before.packages_generated_today)
        requested_count = min(
            before.scheduled_packages_per_run,
            before.max_packages_per_run,
            remaining_today,
        )
        if requested_count <= 0:
            return SchedulerRunResponse(
                status="SKIPPED",
                message="Scheduled autopilot skipped: no package allowance remains.",
                scheduler=before,
            )

        response = run_autopilot(
            AutopilotRequest(
                count=requested_count,
                default_product=str(operations.get("default_product") or "standard_tshirt"),
                explore_marketplaces=_bool(operations.get("explore_marketplaces"), True),
                touch_amazon=False,
                production_mode=_bool(operations.get("production_mode"), False),
            ),
            mode="scheduled_autopilot",
            stop_requested=_stop_requested,
        )
        after = get_scheduler_status(running=False)
        return SchedulerRunResponse(
            status=response.status,
            runId=response.run_id,
            createdDraftIds=response.created_draft_ids,
            message=response.message,
            scheduler=after,
        )
    finally:
        _SCHEDULER_LOCK.release()


def set_stop_switch(engaged: bool) -> SchedulerStatus:
    operations = _operations_config()
    update_settings(
        SettingsPatch(
            autopilot_operations={
                **operations,
                "stop_switch_engaged": engaged,
            }
        )
    )
    return get_scheduler_status()


async def scheduler_loop(poll_seconds: int = 60) -> None:
    while True:
        await asyncio.sleep(poll_seconds)
        status = get_scheduler_status()
        if status.blocked_reasons:
            continue
        try:
            response = await asyncio.to_thread(run_scheduler_tick)
            logger.info(
                "Scheduled autopilot tick finished",
                extra={
                    "event": "scheduler_tick",
                    "status": response.status,
                    "run_id": response.run_id,
                    "created_draft_count": len(response.created_draft_ids),
                },
            )
        except Exception:
            logger.exception(
                "Scheduled autopilot tick failed",
                extra={"event": "scheduler_tick_failed"},
            )
