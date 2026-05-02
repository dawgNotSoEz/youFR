from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from ai_hall.config import get_settings
from ai_hall.pipeline.types import PipelineRun
from ai_hall.utils.hashing import stable_hash


@dataclass
class MemoryTTLCache:
    ttl_seconds: int = field(default_factory=lambda: get_settings().cache_ttl_seconds)
    _items: dict[str, tuple[float, Any]] = field(default_factory=dict)

    def key(self, payload: dict[str, Any]) -> str:
        return stable_hash(payload)

    def get(self, key: str) -> Any | None:
        item = self._items.get(key)
        if not item:
            return None
        expires_at, value = item
        if expires_at < time.time():
            self._items.pop(key, None)
            return None
        return value

    def set(self, key: str, value: Any) -> None:
        self._items[key] = (time.time() + self.ttl_seconds, value)


cache = MemoryTTLCache()


class HybridCache:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.memory = cache
        self.redis = None
        if self.settings.redis_url:
            try:
                import redis

                self.redis = redis.Redis.from_url(self.settings.redis_url, decode_responses=True)
                self.redis.ping()
            except Exception:
                self.redis = None

    def key(self, payload: dict[str, Any]) -> str:
        return stable_hash(payload)

    def get(self, key: str) -> PipelineRun | None:
        if self.redis:
            raw = self.redis.get(key)
            if raw:
                return PipelineRun.model_validate_json(raw)
        return self.memory.get(key)

    def set(self, key: str, value: PipelineRun) -> None:
        if self.redis:
            self.redis.setex(key, self.settings.cache_ttl_seconds, value.model_dump_json())
        self.memory.set(key, value)


hybrid_cache = HybridCache()
