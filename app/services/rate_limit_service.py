"""Rate limiting service for API usage control."""

from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from app.models.auth import RateLimitInfo


class RateLimitService:
    """Service for rate limiting operations."""

    # Rate limits by tier
    FREE_TIER_LIMIT = 100  # requests per day
    PREMIUM_TIER_LIMIT = 1000  # requests per day

    def __init__(self, cache_backend):
        """Initialize rate limit service with cache backend."""
        self.cache = cache_backend

    def _get_rate_limit_key(self, user_id: UUID) -> str:
        """Generate cache key for rate limiting."""
        date_str = datetime.utcnow().strftime("%Y-%m-%d")
        return f"rate_limit:{user_id}:{date_str}"

    def _get_window_times(self) -> tuple[datetime, datetime]:
        """Get current rate limit window start and end times."""
        now = datetime.utcnow()
        window_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        window_end = window_start + timedelta(days=1)
        return window_start, window_end

    async def check_rate_limit(
        self, user_id: UUID, is_premium: bool = False
    ) -> RateLimitInfo:
        """Check if user has exceeded rate limit."""
        limit = self.PREMIUM_TIER_LIMIT if is_premium else self.FREE_TIER_LIMIT
        key = self._get_rate_limit_key(user_id)
        window_start, window_end = self._get_window_times()

        # Get current count
        count_str = await self.cache.get(key)
        requests_made = int(count_str) if count_str else 0

        requests_remaining = max(0, limit - requests_made)

        return RateLimitInfo(
            requests_made=requests_made,
            requests_limit=limit,
            window_start=window_start,
            window_end=window_end,
            requests_remaining=requests_remaining,
        )

    async def increment_usage(self, user_id: UUID) -> None:
        """Increment API usage count for a user."""
        key = self._get_rate_limit_key(user_id)

        # Get current count
        count_str = await self.cache.get(key)
        count = int(count_str) if count_str else 0

        # Increment and store with TTL until end of day
        _, window_end = self._get_window_times()
        ttl = int((window_end - datetime.utcnow()).total_seconds())

        await self.cache.set(key, str(count + 1), ttl)

    async def is_rate_limited(self, user_id: UUID, is_premium: bool = False) -> bool:
        """Check if user is rate limited."""
        info = await self.check_rate_limit(user_id, is_premium)
        return info.requests_remaining <= 0

    async def reset_user_limit(self, user_id: UUID) -> None:
        """Reset rate limit for a user (admin function)."""
        key = self._get_rate_limit_key(user_id)
        await self.cache.delete(key)
