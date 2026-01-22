"""Abstract cache backend interface."""

from abc import ABC, abstractmethod
from typing import Any


class CacheBackend(ABC):
    """Abstract base class for cache backends."""

    @abstractmethod
    async def get(self, key: str) -> Any | None:
        """
        Retrieve a value from the cache.

        Args:
            key: The cache key to retrieve.

        Returns:
            The cached value if found, None otherwise.
        """
        ...

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        """
        Store a value in the cache.

        Args:
            key: The cache key.
            value: The value to store.
            ttl: Time-to-live in seconds. None for no expiration.

        Returns:
            True if the value was stored successfully.
        """
        ...

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """
        Delete a value from the cache.

        Args:
            key: The cache key to delete.

        Returns:
            True if the key was deleted, False if it didn't exist.
        """
        ...

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """
        Check if a key exists in the cache.

        Args:
            key: The cache key to check.

        Returns:
            True if the key exists.
        """
        ...

    @abstractmethod
    async def clear(self) -> bool:
        """
        Clear all keys from the cache.

        Returns:
            True if the cache was cleared successfully.
        """
        ...

    @abstractmethod
    async def close(self) -> None:
        """Close the cache connection."""
        ...

    @abstractmethod
    async def ping(self) -> bool:
        """
        Check if the cache backend is healthy.

        Returns:
            True if the backend is responsive.
        """
        ...

    def _make_key(self, namespace: str, *parts: str) -> str:
        """
        Create a namespaced cache key.

        Args:
            namespace: The key namespace.
            parts: Additional key parts.

        Returns:
            A formatted cache key.
        """
        return f"safetrace:{namespace}:{':'.join(parts)}"

    def address_key(self, chain: str, address: str) -> str:
        """Generate cache key for address metadata."""
        return self._make_key("address", chain, address.lower())

    def transaction_key(self, chain: str, tx_hash: str) -> str:
        """Generate cache key for transaction data."""
        return self._make_key("tx", chain, tx_hash.lower())

    def risk_key(self, chain: str, tx_hash: str, depth: int) -> str:
        """Generate cache key for risk analysis results."""
        return self._make_key("risk", chain, tx_hash.lower(), str(depth))
