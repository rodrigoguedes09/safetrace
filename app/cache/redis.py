"""Redis cache backend implementation."""

import json
import logging
from typing import Any

from app.core.cache import CacheBackend
from app.core.exceptions import CacheError

logger = logging.getLogger(__name__)


class RedisCacheBackend(CacheBackend):
    """Redis-based cache backend with TTL support."""

    def __init__(self, redis_url: str, default_ttl: int = 86400) -> None:
        """
        Initialize Redis cache backend.

        Args:
            redis_url: Redis connection URL.
            default_ttl: Default TTL in seconds (24 hours).
        """
        self._redis_url = redis_url
        self._default_ttl = default_ttl
        self._client: Any = None

    async def _get_client(self) -> Any:
        """Get or create Redis client."""
        if self._client is None:
            try:
                import redis.asyncio as redis

                self._client = redis.from_url(
                    self._redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                )
            except ImportError as e:
                raise CacheError("Redis package not installed", "connect") from e
            except Exception as e:
                raise CacheError(f"Failed to connect to Redis: {e}", "connect") from e
        return self._client

    async def get(self, key: str) -> Any | None:
        """Retrieve a value from Redis."""
        try:
            client = await self._get_client()
            data = await client.get(key)
            if data is None:
                return None
            return json.loads(data)
        except json.JSONDecodeError:
            return data
        except Exception as e:
            logger.warning(f"Redis GET error for key {key}: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        """Store a value in Redis with optional TTL."""
        try:
            client = await self._get_client()
            serialized = json.dumps(value, default=str)
            expire = ttl if ttl is not None else self._default_ttl
            if expire:
                await client.setex(key, expire, serialized)
            else:
                await client.set(key, serialized)
            return True
        except Exception as e:
            logger.warning(f"Redis SET error for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete a key from Redis."""
        try:
            client = await self._get_client()
            result = await client.delete(key)
            return result > 0
        except Exception as e:
            logger.warning(f"Redis DELETE error for key {key}: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """Check if a key exists in Redis."""
        try:
            client = await self._get_client()
            return await client.exists(key) > 0
        except Exception as e:
            logger.warning(f"Redis EXISTS error for key {key}: {e}")
            return False

    async def clear(self) -> bool:
        """Clear all SafeTrace keys from Redis."""
        try:
            client = await self._get_client()
            cursor = 0
            while True:
                cursor, keys = await client.scan(cursor, match="safetrace:*", count=100)
                if keys:
                    await client.delete(*keys)
                if cursor == 0:
                    break
            return True
        except Exception as e:
            logger.warning(f"Redis CLEAR error: {e}")
            return False

    async def close(self) -> None:
        """Close the Redis connection."""
        if self._client:
            await self._client.close()
            self._client = None

    async def ping(self) -> bool:
        """Check Redis connectivity."""
        try:
            client = await self._get_client()
            return await client.ping()
        except Exception:
            return False
