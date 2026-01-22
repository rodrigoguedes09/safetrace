"""Authentication middleware and dependencies."""

from typing import Optional
from uuid import UUID

from fastapi import Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.models.auth import User, APIKey

security = HTTPBearer(auto_error=False)


async def get_current_user(
    authorization: Optional[HTTPAuthorizationCredentials] = None,
    x_api_key: Optional[str] = Header(None),
) -> tuple[User, APIKey]:
    """
    Get current user from API key.
    Supports two methods:
    1. Bearer token in Authorization header
    2. X-API-Key header
    """
    from app.api.dependencies import get_auth_service

    auth_service = get_auth_service()

    # Get API key from either header
    api_key = None
    if authorization and authorization.credentials:
        api_key = authorization.credentials
    elif x_api_key:
        api_key = x_api_key

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Provide via Authorization header (Bearer token) or X-API-Key header.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify API key
    result = await auth_service.verify_api_key(api_key)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired API key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user, key = result

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    return user, key


async def check_rate_limit(user: User, api_key: APIKey) -> None:
    """Check if user has exceeded rate limit."""
    from app.api.dependencies import get_rate_limit_service

    rate_limit_service = get_rate_limit_service()

    # Check rate limit
    is_limited = await rate_limit_service.is_rate_limited(
        user.id, user.is_premium
    )

    if is_limited:
        rate_info = await rate_limit_service.check_rate_limit(
            user.id, user.is_premium
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Limit: {rate_info.requests_limit} requests per day. "
            f"Window resets at {rate_info.window_end.isoformat()}",
            headers={
                "X-RateLimit-Limit": str(rate_info.requests_limit),
                "X-RateLimit-Remaining": str(rate_info.requests_remaining),
                "X-RateLimit-Reset": str(int(rate_info.window_end.timestamp())),
            },
        )

    # Increment usage
    await rate_limit_service.increment_usage(user.id)


def get_optional_user() -> Optional[tuple[User, APIKey]]:
    """
    Dependency that optionally gets the current user.
    Returns None if no authentication is provided.
    Useful for endpoints that work both authenticated and unauthenticated.
    """

    async def optional_user_dependency(
        authorization: Optional[HTTPAuthorizationCredentials] = None,
        x_api_key: Optional[str] = Header(None),
    ) -> Optional[tuple[User, APIKey]]:
        if not authorization and not x_api_key:
            return None

        try:
            return await get_current_user(authorization, x_api_key)
        except HTTPException:
            return None

    return optional_user_dependency
