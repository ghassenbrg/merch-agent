from __future__ import annotations

import os
from dataclasses import dataclass


LOCAL_ORIGINS = (
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
)


class RuntimeConfigError(RuntimeError):
    pass


def _bool_env(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _int_env(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _csv_env(name: str, default: tuple[str, ...]) -> list[str]:
    value = os.environ.get(name)
    if value is None:
        return list(default)
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class AppSettings:
    environment: str
    exposed: bool
    api_token: str
    allowed_origins: list[str]
    trusted_hosts: list[str]
    rate_limit_per_minute: int
    write_rate_limit_per_minute: int
    log_max_bytes: int
    log_backup_count: int
    log_retention_days: int

    @property
    def production_like(self) -> bool:
        return self.exposed or self.environment in {"production", "prod", "staging"}

    @property
    def auth_required(self) -> bool:
        return self.production_like or bool(self.api_token)

    def public_status(self) -> dict[str, object]:
        return {
            "environment": self.environment,
            "exposed": self.exposed,
            "auth_required": self.auth_required,
            "api_token_configured": bool(self.api_token),
            "allowed_origins": self.allowed_origins,
            "trusted_hosts": self.trusted_hosts,
            "rate_limit_per_minute": self.rate_limit_per_minute,
            "write_rate_limit_per_minute": self.write_rate_limit_per_minute,
            "log_retention_days": self.log_retention_days,
        }


def get_settings() -> AppSettings:
    return AppSettings(
        environment=os.environ.get("MERCH_AGENT_ENV", "local").strip().lower() or "local",
        exposed=_bool_env("MERCH_AGENT_EXPOSED", False),
        api_token=os.environ.get("MERCH_AGENT_API_TOKEN", ""),
        allowed_origins=_csv_env("MERCH_AGENT_ALLOWED_ORIGINS", LOCAL_ORIGINS),
        trusted_hosts=_csv_env(
            "MERCH_AGENT_TRUSTED_HOSTS",
            ("localhost", "127.0.0.1", "::1", "testserver"),
        ),
        rate_limit_per_minute=max(1, _int_env("MERCH_AGENT_RATE_LIMIT_PER_MINUTE", 240)),
        write_rate_limit_per_minute=max(1, _int_env("MERCH_AGENT_WRITE_RATE_LIMIT_PER_MINUTE", 60)),
        log_max_bytes=max(10_000, _int_env("MERCH_AGENT_LOG_MAX_BYTES", 1_000_000)),
        log_backup_count=max(1, _int_env("MERCH_AGENT_LOG_BACKUP_COUNT", 5)),
        log_retention_days=max(1, _int_env("MERCH_AGENT_LOG_RETENTION_DAYS", 30)),
    )


def validate_runtime_settings(settings: AppSettings | None = None) -> AppSettings:
    settings = settings or get_settings()
    errors: list[str] = []
    if settings.production_like and not settings.api_token:
        errors.append(
            "MERCH_AGENT_API_TOKEN is required when MERCH_AGENT_ENV is production/staging "
            "or MERCH_AGENT_EXPOSED=true"
        )
    if settings.production_like and not settings.allowed_origins:
        errors.append("MERCH_AGENT_ALLOWED_ORIGINS must include the frontend origin")
    if "*" in settings.allowed_origins:
        errors.append("MERCH_AGENT_ALLOWED_ORIGINS must not use '*'")
    if errors:
        raise RuntimeConfigError("; ".join(errors))
    return settings
