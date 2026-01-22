"""In-memory cache backend implementation."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, NamedTuple

from app.core.cache import CacheBackend

logger = logging.getLogger(__name__)


class CacheEntry(NamedTuple):
    """Cache entry with value and expiration."""

    value: Any
    expires_at: datetime | None


class MemoryCacheBackend(CacheBackend):
    """In-memory cache backend with TTL support. For development/testing only."""

    def __init__(self, default_ttl: int = 86400) -> None:
        """
        Initialize memory cache backend.

        Args:
            default_ttl: Default TTL in seconds (24 hours).
        """
        self._default_ttl = default_ttl
        self._store: dict[str, CacheEntry] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Any | None:
        """Retrieve a value from memory."""
        async with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            if entry.expires_at and entry.expires_at < datetime.utcnow():
                del self._store[key]
                return None
            return entry.value

    async def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        """Store a value in memory with optional TTL."""
        async with self._lock:
            expire_time = ttl if ttl is not None else self._default_ttl
            expires_at = None
            if expire_time:
                expires_at = datetime.utcnow() + timedelta(seconds=expire_time)
            self._store[key] = CacheEntry(value=value, expires_at=expires_at)
            return True

    async def delete(self, key: str) -> bool:
        """Delete a key from memory."""
        async with self._lock:
            if key in self._store:
                del self._store[key]
                return True
            return False

    async def exists(self, key: str) -> bool:
        """Check if a key exists in memory."""
        async with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return False
            if entry.expires_at and entry.expires_at < datetime.utcnow():
                del self._store[key]
                return False
            return True

    async def clear(self) -> bool:
        """Clear all SafeTrace keys from memory."""
        async with self._lock:
            keys_to_delete = [k for k in self._store if k.startswith("safetrace:")]
            for key in keys_to_delete:
                del self._store[key]
            return True

    async def close(self) -> None:
        """Clear the in-memory store."""
        async with self._lock:
            self._store.clear()

    async def ping(self) -> bool:
        """Memory cache is always available."""
        return True

    async def cleanup_expired(self) -> int:
        """Remove expired cache entries."""
        async with self._lock:
            now = datetime.utcnow()
            expired_keys = [
                k
                for k, v in self._store.items()
                if v.expires_at and v.expires_at < now
            ]
            for key in expired_keys:
                del self._store[key]
            return len(expired_keys)
