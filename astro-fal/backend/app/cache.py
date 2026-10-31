"""Async TTL cache with single-flight (one LLM call per key under concurrency).

Process-local; swap for Redis in multi-instance deployments (same interface).
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable, Hashable
from typing import Any


class TTLCache:
    def __init__(self, max_items: int = 10_000) -> None:
        self._data: dict[Hashable, tuple[float, Any]] = {}
        self._locks: dict[Hashable, asyncio.Lock] = {}
        self._max = max_items

    def _get(self, key: Hashable) -> Any | None:
        hit = self._data.get(key)
        if hit is None:
            return None
        expires, value = hit
        if expires < time.monotonic():
            self._data.pop(key, None)
            return None
        return value

    async def get_or_create(self, key: Hashable, factory: Callable[[], Awaitable[Any]], ttl_s: float) -> Any:
        value = self._get(key)
        if value is not None:
            return value
        lock = self._locks.setdefault(key, asyncio.Lock())
        async with lock:
            value = self._get(key)
            if value is None:
                value = await factory()
                if len(self._data) >= self._max:
                    # Evict the entry closest to expiry; O(n) but only on overflow.
                    self._data.pop(min(self._data, key=lambda k: self._data[k][0]), None)
                self._data[key] = (time.monotonic() + ttl_s, value)
        self._locks.pop(key, None)
        return value

    def __len__(self) -> int:
        return len(self._data)
