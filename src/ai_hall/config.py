from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    app_name: str = "AI Hall"
    environment: str = os.getenv("AI_HALL_ENV", "development")
    audit_log_path: Path = Path(os.getenv("AI_HALL_AUDIT_LOG", "logs/audit.jsonl"))
    cache_ttl_seconds: int = int(os.getenv("AI_HALL_CACHE_TTL_SECONDS", "300"))
    redis_url: str | None = os.getenv("REDIS_URL") or os.getenv("AI_HALL_REDIS_URL")
    database_url: str | None = os.getenv("DATABASE_URL") or os.getenv("AI_HALL_DATABASE_URL")
    api_keys: tuple[str, ...] = tuple(k.strip() for k in os.getenv("AI_HALL_API_KEYS", "").split(",") if k.strip())
    require_auth: bool = os.getenv("AI_HALL_REQUIRE_AUTH", "").lower() in {"1", "true", "yes"}
    dashboard_enabled: bool = os.getenv("AI_HALL_DASHBOARD_ENABLED", "false").lower() not in {"0", "false", "no"}


def get_settings() -> Settings:
    return Settings()
