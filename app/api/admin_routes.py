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
    """Get global application metrics."""
    metrics_service = MetricsService(cache)
    return await metrics_service.get_global_stats()


@router.get(
    "/metrics/user/{user_id}",
    summary="Get user-specific metrics",
    description="Get metrics for a specific user. Admin only.",
)
async def get_user_metrics(
    user_id: str,
    admin: Annotated[User, Depends(require_admin)],
    cache: Annotated[object, Depends(get_cache_backend)],
) -> dict:
    """Get metrics for a specific user."""
    from uuid import UUID
    
    try:
        user_uuid = UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format",
        )
    
    metrics_service = MetricsService(cache)
    return await metrics_service.get_user_metrics(user_uuid)


@router.get(
    "/audit/user/{user_id}",
    summary="Get user activity audit log",
    description="Get recent audit log entries for a user. Admin only.",
)
async def get_user_audit_log(
    user_id: str,
    admin: Annotated[User, Depends(require_admin)],
    db_pool: Annotated[object, Depends(get_db_pool)],
    limit: int = 100,
) -> list[dict]:
    """Get audit log for a specific user."""
    from uuid import UUID
    
    try:
        user_uuid = UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format",
        )
    
    audit_logger = AuditLogger(db_pool)
    return await audit_logger.get_user_activity(user_uuid, limit)


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


@router.post(
    "/users/{user_id}/upgrade",
    summary="Upgrade user to premium",
    description="Manually upgrade a user to premium tier. Admin only.",
)
async def upgrade_user(
    user_id: str,
    admin: Annotated[User, Depends(require_admin)],
    db_pool: Annotated[object, Depends(get_db_pool)],
) -> dict:
    """Upgrade a user to premium tier."""
    from uuid import UUID
    
    try:
        user_uuid = UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format",
        )
    
    async with db_pool.acquire() as conn:
        result = await conn.execute(
            "UPDATE users SET is_premium = true WHERE id = $1",
            user_uuid,
        )
        
        if result == "UPDATE 0":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
    
    # Log audit event
    from app.services.audit_logger import AuditAction
    audit_logger = AuditLogger(db_pool)
    await audit_logger.log(
        action=AuditAction.USER_UPGRADED,
        user_id=user_uuid,
        details={"upgraded_by": str(admin.id)},
    )
    
    return {"status": "success", "message": "User upgraded to premium"}
