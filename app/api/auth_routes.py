"""Authentication routes for user registration and API key management."""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Header, Query, status

from app.api.auth_middleware import get_current_user
from app.api.dependencies import get_auth_service, get_rate_limit_service, get_history_service
from app.models.auth import (
    APIKey,
    APIKeyCreate,
    APIKeyResponse,
    RateLimitInfo,
    User,
    UserCreate,
)
from app.services.auth_service import AuthService
from app.services.rate_limit_service import RateLimitService
from app.services.history_service import AnalysisHistoryService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=User,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def register_user(
    user_data: UserCreate,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> User:
    """
    Register a new user account.

    - **email**: Valid email address (must be unique)
    - **full_name**: User's full name (2-100 characters)
    - **password**: Strong password (8-72 chars, must include uppercase, lowercase, and digit)
    """
    try:
        user = await auth_service.create_user(user_data)
        return user
    except ValueError as e:
        error_detail = str(e)
        
        # Map specific errors to appropriate status codes
        if "already exists" in error_detail.lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=error_detail,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_detail,
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}",
        )


@router.post(
    "/bootstrap",
    response_model=APIKeyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Bootstrap first API key for a user (password required)",
)
async def bootstrap_api_key(
    email: str,
    password: str,
    key_data: APIKeyCreate,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> APIKeyResponse:
    """
    Create the first API key for a user using email and password.
    
    This endpoint allows creating an initial API key without already having one.
    After this, use the created key to generate additional keys.

    - **email**: User's email
    - **password**: User's password
    - **key_data**: API key name and description
    """
    try:
        # Normalize email
        email = email.lower().strip()
        
        # Verify user credentials
        user_in_db = await auth_service.get_user_by_email(email)
        if not user_in_db:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        if not auth_service.verify_password(password, user_in_db.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        if not user_in_db.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive",
            )

        # Create API key
        api_key, plain_key = await auth_service.create_api_key(user_in_db.id, key_data)

        return APIKeyResponse(
            id=api_key.id,
            user_id=api_key.user_id,
            name=api_key.name,
            description=api_key.description,
            key_prefix=api_key.key_prefix,
            is_active=api_key.is_active,
            last_used_at=api_key.last_used_at,
            created_at=api_key.created_at,
            expires_at=api_key.expires_at,
            key=plain_key,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create API key: {str(e)}",
        )


@router.post(
    "/api-keys",
    response_model=APIKeyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new API key",
)
async def create_api_key(
    key_data: APIKeyCreate,
    user_and_key: Annotated[tuple[User, APIKey], Depends(get_current_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> APIKeyResponse:
    """
    Create a new API key for the authenticated user.

    **Authentication required:** Provide existing API key or use initial setup.

    - **name**: Descriptive name for the key (e.g., "Production Server")
    - **description**: Optional description

    **Important:** The full API key is only shown once. Save it securely!
    """
    user, _ = user_and_key

    api_key, plain_key = await auth_service.create_api_key(user.id, key_data)

    return APIKeyResponse(
        id=api_key.id,
        user_id=api_key.user_id,
        name=api_key.name,
        description=api_key.description,
        key_prefix=api_key.key_prefix,
        is_active=api_key.is_active,
        last_used_at=api_key.last_used_at,
        created_at=api_key.created_at,
        expires_at=api_key.expires_at,
        key=plain_key,
    )


@router.get(
    "/api-keys",
    response_model=list[APIKey],
    summary="List all API keys",
)
async def list_api_keys(
    user_and_key: Annotated[tuple[User, APIKey], Depends(get_current_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> list[APIKey]:
    """
    List all API keys for the authenticated user.

    Shows key prefix, status, last used time, but not the full key.
    """
    user, _ = user_and_key
    return await auth_service.list_user_api_keys(user.id)


@router.delete(
    "/api-keys/{key_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke an API key",
)
async def revoke_api_key(
    key_id: str,
    user_and_key: Annotated[tuple[User, APIKey], Depends(get_current_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> None:
    """
    Revoke (deactivate) an API key.

    The key will no longer work for authentication.
    """
    user, _ = user_and_key

    try:
        from uuid import UUID

        key_uuid = UUID(key_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid key ID format",
        )

    success = await auth_service.revoke_api_key(user.id, key_uuid)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )


@router.get(
    "/me",
    response_model=User,
    summary="Get current user info",
)
async def get_current_user_info(
    user_and_key: Annotated[tuple[User, APIKey], Depends(get_current_user)],
) -> User:
    """
    Get information about the currently authenticated user.
    """
    user, _ = user_and_key
    return user


@router.get(
    "/rate-limit",
    response_model=RateLimitInfo,
    summary="Get rate limit status",
)
async def get_rate_limit_status(
    user_and_key: Annotated[tuple[User, APIKey], Depends(get_current_user)],
    rate_limit_service: Annotated[
        RateLimitService, Depends(get_rate_limit_service)
    ],
) -> RateLimitInfo:
    """
    Get current rate limit information for the authenticated user.

    Shows:
    - Requests made today
    - Total daily limit
    - Remaining requests
    - Window reset time
    """
    user, _ = user_and_key
    return await rate_limit_service.check_rate_limit(user.id, user.is_premium)


@router.get(
    "/usage",
    summary="Get usage statistics",
)
async def get_usage_stats(
    user_and_key: Annotated[tuple[User, APIKey], Depends(get_current_user)],
    rate_limit_service: Annotated[
        RateLimitService, Depends(get_rate_limit_service)
    ],
) -> dict:
    """
    Get usage statistics for the authenticated user.

    Returns:
    - requests_today: Number of requests made today
    - total_requests: Total number of requests (estimated)
    - high_risk_count: Number of high-risk analyses found
    - daily_limit: User's daily limit
    """
    user, _ = user_and_key
    rate_info = await rate_limit_service.check_rate_limit(user.id, user.is_premium)
    
    return {
        "requests_today": rate_info.requests_made,
        "total_requests": rate_info.requests_made,
        "high_risk_count": 0,  # Placeholder - would need DB tracking
        "daily_limit": rate_info.requests_limit,
        "remaining": rate_info.requests_remaining
    }


@router.get(
    "/history",
    summary="Get analysis history",
)
async def get_analysis_history(
    user_and_key: Annotated[tuple[User, APIKey], Depends(get_current_user)],
    history_service: Annotated[AnalysisHistoryService, Depends(get_history_service)],
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[dict]:
    """
    Get the authenticated user's analysis history.
    
    Returns a list of previous analyses ordered by most recent first.
    """
    user, _ = user_and_key
    return await history_service.get_user_history(user.id, limit, offset)


@router.get(
    "/history/stats",
    summary="Get analysis statistics",
)
async def get_history_stats(
    user_and_key: Annotated[tuple[User, APIKey], Depends(get_current_user)],
    history_service: Annotated[AnalysisHistoryService, Depends(get_history_service)],
) -> dict:
    """
    Get statistics about the user's analyses.
    
    Returns:
    - total_analyses: Total number of analyses run
    - high_risk_count: Number of analyses with risk > 50
    - chains_analyzed: List of unique chains analyzed
    - average_risk_score: Average risk score across all analyses
    """
    user, _ = user_and_key
    return await history_service.get_user_stats(user.id)


@router.get(
    "/history/{analysis_id}",
    summary="Get specific analysis",
)
async def get_analysis_detail(
    analysis_id: int,
    user_and_key: Annotated[tuple[User, APIKey], Depends(get_current_user)],
    history_service: Annotated[AnalysisHistoryService, Depends(get_history_service)],
) -> dict:
    """
    Get details of a specific analysis by ID.
    
    Only returns analyses owned by the authenticated user.
    """
    user, _ = user_and_key
    result = await history_service.get_analysis_by_id(analysis_id, user.id)
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis not found",
        )
    
    return result
