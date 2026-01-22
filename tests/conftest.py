"""Test configuration and fixtures."""

import asyncio
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio

from app.cache.memory import MemoryCacheBackend
from app.core.cache import CacheBackend
from app.services.risk_scorer import RiskScorerService


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def cache_backend() -> AsyncGenerator[CacheBackend, None]:
    """Provide a memory cache backend for tests."""
    cache = MemoryCacheBackend(default_ttl=3600)
    yield cache
    await cache.close()


@pytest.fixture
def risk_scorer() -> RiskScorerService:
    """Provide a risk scorer service for tests."""
    return RiskScorerService()
