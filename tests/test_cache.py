"""Tests for cache backends."""

import pytest
import pytest_asyncio

from app.cache.memory import MemoryCacheBackend
from app.core.cache import CacheBackend


class TestMemoryCacheBackend:
    """Tests for MemoryCacheBackend."""

    @pytest_asyncio.fixture
    async def cache(self) -> MemoryCacheBackend:
        """Provide a fresh memory cache for each test."""
        return MemoryCacheBackend(default_ttl=3600)

    @pytest.mark.asyncio
    async def test_set_and_get(self, cache: MemoryCacheBackend) -> None:
        """Test basic set and get operations."""
        await cache.set("test_key", {"data": "value"})
        result = await cache.get("test_key")
        
        assert result == {"data": "value"}

    @pytest.mark.asyncio
    async def test_get_nonexistent(self, cache: MemoryCacheBackend) -> None:
        """Test getting a nonexistent key."""
        result = await cache.get("nonexistent")
        
        assert result is None

    @pytest.mark.asyncio
    async def test_exists(self, cache: MemoryCacheBackend) -> None:
        """Test exists operation."""
        await cache.set("exists_key", "value")
        
        assert await cache.exists("exists_key") is True
        assert await cache.exists("nonexistent") is False

    @pytest.mark.asyncio
    async def test_delete(self, cache: MemoryCacheBackend) -> None:
        """Test delete operation."""
        await cache.set("delete_key", "value")
        
        result = await cache.delete("delete_key")
        
        assert result is True
        assert await cache.exists("delete_key") is False

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, cache: MemoryCacheBackend) -> None:
        """Test deleting a nonexistent key."""
        result = await cache.delete("nonexistent")
        
        assert result is False

    @pytest.mark.asyncio
    async def test_clear(self, cache: MemoryCacheBackend) -> None:
        """Test clear operation."""
        await cache.set("safetrace:key1", "value1")
        await cache.set("safetrace:key2", "value2")
        await cache.set("other:key", "value3")
        
        await cache.clear()
        
        assert await cache.exists("safetrace:key1") is False
        assert await cache.exists("safetrace:key2") is False
        # Non-safetrace keys should remain
        assert await cache.exists("other:key") is True

    @pytest.mark.asyncio
    async def test_ping(self, cache: MemoryCacheBackend) -> None:
        """Test ping operation."""
        result = await cache.ping()
        
        assert result is True

    @pytest.mark.asyncio
    async def test_key_generation(self, cache: MemoryCacheBackend) -> None:
        """Test key generation methods."""
        address_key = cache.address_key("ethereum", "0x1234")
        tx_key = cache.transaction_key("bitcoin", "abc123")
        risk_key = cache.risk_key("polygon", "def456", 3)
        
        assert address_key == "safetrace:address:ethereum:0x1234"
        assert tx_key == "safetrace:tx:bitcoin:abc123"
        assert risk_key == "safetrace:risk:polygon:def456:3"

    @pytest.mark.asyncio
    async def test_complex_data_types(self, cache: MemoryCacheBackend) -> None:
        """Test storing complex data types."""
        data = {
            "string": "value",
            "number": 123,
            "float": 45.67,
            "bool": True,
            "list": [1, 2, 3],
            "nested": {"key": "value"},
        }
        
        await cache.set("complex", data)
        result = await cache.get("complex")
        
        assert result == data
