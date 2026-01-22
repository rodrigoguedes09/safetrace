"""Dependency injection for FastAPI."""

from functools import lru_cache
from typing import Annotated, Optional

from fastapi import Depends
import asyncpg

from app.cache.memory import MemoryCacheBackend
from app.cache.postgres import PostgresCacheBackend
from app.cache.redis import RedisCacheBackend
from app.config import Settings, get_settings
from app.core.cache import CacheBackend
from app.core.provider import BlockchainProvider
from app.providers.blockchair import BlockchairProvider
from app.services.pdf_generator import PDFGeneratorService
from app.services.risk_scorer import RiskScorerService
from app.services.tracer import TransactionTracerService
from app.services.auth_service import AuthService
from app.services.rate_limit_service import RateLimitService
from app.services.history_service import AnalysisHistoryService


_cache_instance: CacheBackend | None = None
_provider_instance: BlockchainProvider | None = None
_db_pool: Optional[asyncpg.Pool] = None
_auth_service: Optional[AuthService] = None
_rate_limit_service: Optional[RateLimitService] = None
_history_service: Optional[AnalysisHistoryService] = None


async def get_db_pool(
    settings: Annotated[Settings, Depends(get_settings)]
) -> asyncpg.Pool:
    """Get or create database connection pool."""
    global _db_pool
    
    if _db_pool is None:
        _db_pool = await asyncpg.create_pool(
            dsn=settings.postgres_dsn,
            min_size=2,
            max_size=10,
        )
    
    return _db_pool


async def get_cache_backend(
    settings: Annotated[Settings, Depends(get_settings)]
) -> CacheBackend:
    """Get or create cache backend instance."""
    global _cache_instance
    
    if _cache_instance is None:
        if settings.cache_backend == "redis":
            _cache_instance = RedisCacheBackend(
                redis_url=settings.redis_url,
                default_ttl=settings.cache_ttl_seconds,
            )
        elif settings.cache_backend == "postgres":
            _cache_instance = PostgresCacheBackend(
                dsn=settings.postgres_dsn,
                default_ttl=settings.cache_ttl_seconds,
            )
        else:
            _cache_instance = MemoryCacheBackend(
                default_ttl=settings.cache_ttl_seconds,
            )
    
    return _cache_instance


async def get_blockchain_provider(
    settings: Annotated[Settings, Depends(get_settings)]
) -> BlockchainProvider:
    """Get or create blockchain provider instance."""
    global _provider_instance
    
    if _provider_instance is None:
        _provider_instance = BlockchairProvider(
            api_key=settings.blockchair_api_key.get_secret_value(),
            base_url=settings.blockchair_base_url,
            requests_per_second=settings.blockchair_requests_per_second,
            max_retries=settings.blockchair_max_retries,
            retry_delay=settings.blockchair_retry_delay,
        )
    
    return _provider_instance


def get_risk_scorer() -> RiskScorerService:
    """Get risk scorer service instance."""
    return RiskScorerService()


def get_pdf_generator(
    settings: Annotated[Settings, Depends(get_settings)]
) -> PDFGeneratorService:
    """Get PDF generator service instance."""
    return PDFGeneratorService(output_dir=settings.pdf_output_dir)


async def get_tracer_service(
    cache: Annotated[CacheBackend, Depends(get_cache_backend)],
    provider: Annotated[BlockchainProvider, Depends(get_blockchain_provider)],
    risk_scorer: Annotated[RiskScorerService, Depends(get_risk_scorer)],
) -> TransactionTracerService:
    """Get transaction tracer service instance."""
    return TransactionTracerService(
        provider=provider,
        cache=cache,
        risk_scorer=risk_scorer,
    )


def get_auth_service() -> AuthService:
    """Get authentication service instance."""
    global _auth_service, _db_pool
    
    if _auth_service is None and _db_pool is not None:
        _auth_service = AuthService(_db_pool)
    
    return _auth_service


def get_rate_limit_service() -> RateLimitService:
    """Get rate limiting service instance."""
    global _rate_limit_service, _cache_instance
    
    if _rate_limit_service is None and _cache_instance is not None:
        _rate_limit_service = RateLimitService(_cache_instance)
    
    return _rate_limit_service


def get_history_service() -> AnalysisHistoryService:
    """Get analysis history service instance."""
    global _history_service, _db_pool
    
    if _history_service is None and _db_pool is not None:
        _history_service = AnalysisHistoryService(_db_pool)
    
    return _history_service


async def cleanup_dependencies() -> None:
    """Cleanup dependency instances on shutdown."""
    global _cache_instance, _provider_instance, _db_pool, _auth_service, _rate_limit_service, _history_service
    
    if _cache_instance:
        await _cache_instance.close()
        _cache_instance = None
    
    if _provider_instance:
        await _provider_instance.close()
        _provider_instance = None
    
    if _db_pool:
        await _db_pool.close()
        _db_pool = None
    
    _auth_service = None
    _rate_limit_service = None
    _history_service = None
