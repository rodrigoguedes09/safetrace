"""PostgreSQL cache backend implementation."""

import json
import logging
from datetime import datetime, timedelta
from typing import Any

from app.core.cache import CacheBackend
from app.core.exceptions import CacheError

logger = logging.getLogger(__name__)

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS cache (
    key VARCHAR(512) PRIMARY KEY,
    value TEXT NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_cache_expires ON cache(expires_at);
"""


class PostgresCacheBackend(CacheBackend):
    """PostgreSQL-based cache backend with TTL support."""

    def __init__(self, dsn: str, default_ttl: int = 86400) -> None:
        """
        Initialize PostgreSQL cache backend.

        Args:
            dsn: PostgreSQL connection string.
            default_ttl: Default TTL in seconds (24 hours).
        """
        self._dsn = dsn
        self._default_ttl = default_ttl
        self._pool: Any = None

    async def _get_pool(self) -> Any:
        """Get or create connection pool."""
        if self._pool is None:
            try:
                import asyncpg

                self._pool = await asyncpg.create_pool(self._dsn, min_size=2, max_size=10)
                async with self._pool.acquire() as conn:
                    await conn.execute(CREATE_TABLE_SQL)
            except ImportError as e:
                raise CacheError("asyncpg package not installed", "connect") from e
            except Exception as e:
                raise CacheError(f"Failed to connect to PostgreSQL: {e}", "connect") from e
        return self._pool

    async def get(self, key: str) -> Any | None:
        """Retrieve a value from PostgreSQL."""
        try:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT value FROM cache 
                    WHERE key = $1 AND (expires_at IS NULL OR expires_at > NOW())
                    """,
                    key,
                )
                if row is None:
                    return None
                try:
                    return json.loads(row["value"])
                except json.JSONDecodeError:
                    return row["value"]
        except Exception as e:
            logger.warning(f"PostgreSQL GET error for key {key}: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        """Store a value in PostgreSQL with optional TTL."""
        try:
            pool = await self._get_pool()
            serialized = json.dumps(value, default=str)
            expire_time = ttl if ttl is not None else self._default_ttl
            expires_at = None
            if expire_time:
                expires_at = datetime.utcnow() + timedelta(seconds=expire_time)

            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO cache (key, value, expires_at)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (key) DO UPDATE SET value = $2, expires_at = $3
                    """,
                    key,
                    serialized,
                    expires_at,
                )
            return True
        except Exception as e:
            logger.warning(f"PostgreSQL SET error for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete a key from PostgreSQL."""
        try:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                result = await conn.execute("DELETE FROM cache WHERE key = $1", key)
                return "DELETE 1" in result
        except Exception as e:
            logger.warning(f"PostgreSQL DELETE error for key {key}: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """Check if a key exists in PostgreSQL."""
        try:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT 1 FROM cache 
                    WHERE key = $1 AND (expires_at IS NULL OR expires_at > NOW())
                    """,
                    key,
                )
                return row is not None
        except Exception as e:
            logger.warning(f"PostgreSQL EXISTS error for key {key}: {e}")
            return False

    async def clear(self) -> bool:
        """Clear all SafeTrace keys from PostgreSQL."""
        try:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                await conn.execute("DELETE FROM cache WHERE key LIKE 'safetrace:%'")
            return True
        except Exception as e:
            logger.warning(f"PostgreSQL CLEAR error: {e}")
            return False

    async def close(self) -> None:
        """Close the PostgreSQL connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None

    async def ping(self) -> bool:
        """Check PostgreSQL connectivity."""
        try:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                await conn.execute("SELECT 1")
            return True
        except Exception:
            return False

    async def cleanup_expired(self) -> int:
        """Remove expired cache entries."""
        try:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                result = await conn.execute(
                    "DELETE FROM cache WHERE expires_at IS NOT NULL AND expires_at < NOW()"
                )
                count = int(result.split()[-1]) if result else 0
                return count
        except Exception as e:
            logger.warning(f"PostgreSQL cleanup error: {e}")
            return 0
