from __future__ import annotations

import json
import logging
import time
from typing import Any

LOGGER = logging.getLogger(__name__)


class MemoryTtlCache:
    """Process-local cache used when Redis is unavailable (Docker is forbidden here)."""

    def __init__(self) -> None:
        self._store: dict[str, tuple[float, str]] = {}

    def get(self, key: str) -> Any | None:
        item = self._store.get(key)
        if item is None:
            LOGGER.info("cache_miss", extra={"key": key})
            return None
        expires_at, raw = item
        if expires_at < time.time():
            self._store.pop(key, None)
            LOGGER.info("cache_expired", extra={"key": key})
            return None
        LOGGER.info("cache_hit", extra={"key": key})
        return json.loads(raw)

    def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        self._store[key] = (time.time() + ttl_seconds, json.dumps(value))
        LOGGER.info("cache_set", extra={"key": key, "ttl": ttl_seconds})

    def delete(self, key: str) -> None:
        self._store.pop(key, None)
        LOGGER.info("cache_delete", extra={"key": key})

    def clear(self) -> None:
        self._store.clear()

