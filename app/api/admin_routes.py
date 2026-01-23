"""Admin routes for metrics and monitoring."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.auth_middleware import get_current_user
from app.api.dependencies import get_cache_backend, get_db_pool
from app.models.auth import User, APIKey
from app.services.metrics_service import MetricsService
from app.services.audit_logger import AuditLogger

router = APIRouter(prefix="/admin", tags=["Admin"])


async def require_admin(
    user_and_key: Annotated[tuple[User, APIKey], Depends(get_current_user)],
) -> User:
    """Dependency to require admin privileges."""
    user, _ = user_and_key
    
    # For now, check if user is premium (can be changed to is_admin field)
    if not user.is_premium:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    
    return user


@router.get(
    "/metrics",
    summary="Get global application metrics",
    description="Get aggregated metrics for the application. Admin only.",
)
async def get_metrics(
    admin: Annotated[User, Depends(require_admin)],
    cache: Annotated[object, Depends(get_cache_backend)],
) -> dict:
    """Get global application metrics - no user-specific data exposed."""
    metrics_service = MetricsService(cache)
    stats = await metrics_service.get_global_stats()
    
    # Only return aggregated, anonymized metrics
    return {
        "total_requests": stats.get("total_requests", 0),
        "total_users": stats.get("total_users", 0),
        "cache_hits": stats.get("cache_hits", 0),
        "cache_misses": stats.get("cache_misses", 0),
        "uptime": stats.get("uptime", 0)
    }


# User-specific metrics and audit routes removed - SafeTrace does not expose individual user data


@router.get(
    "/health/detailed",
    summary="Detailed health check",
    description="Get detailed health information. Admin only.",
)
async def detailed_health_check(
    admin: Annotated[User, Depends(require_admin)],
    cache: Annotated[object, Depends(get_cache_backend)],
    db_pool: Annotated[object, Depends(get_db_pool)],
) -> dict:
    """Get detailed health information."""
    health = {
        "status": "healthy",
        "checks": {},
    }
    
    # Check cache
    try:
        await cache.ping()
        health["checks"]["cache"] = {"status": "healthy"}
    except Exception as e:
        health["checks"]["cache"] = {"status": "unhealthy", "error": str(e)}
        health["status"] = "degraded"
    
    # Check database
    try:
        async with db_pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        health["checks"]["database"] = {"status": "healthy"}
    except Exception as e:
        health["checks"]["database"] = {"status": "unhealthy", "error": str(e)}
        health["status"] = "degraded"
    
    # Get metrics
    try:
        metrics_service = MetricsService(cache)
        stats = await metrics_service.get_global_stats()
        health["metrics"] = stats
    except Exception as e:
        health["checks"]["metrics"] = {"status": "unhealthy", "error": str(e)}
    
    return health


# User management routes removed - SafeTrace does not expose user administration endpoints publicly
