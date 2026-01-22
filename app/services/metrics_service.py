"""Metrics tracking service."""

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID


class MetricsService:
    """Service for tracking application metrics."""

    def __init__(self, cache_backend):
        """Initialize metrics service with cache backend."""
        self.cache = cache_backend

    async def increment_counter(self, metric_name: str, value: int = 1) -> None:
        """Increment a counter metric."""
        key = f"metrics:counter:{metric_name}"
        current = await self.cache.get(key)
        current_value = int(current) if current else 0
        await self.cache.set(key, str(current_value + value), ttl=86400)

    async def record_duration(self, metric_name: str, duration_ms: float) -> None:
        """Record a duration metric (in milliseconds)."""
        key = f"metrics:duration:{metric_name}"
        # Store as simple average for now (can be improved with histograms)
        current = await self.cache.get(key)
        if current:
            parts = current.split(":")
            count = int(parts[0])
            total = float(parts[1])
            new_count = count + 1
            new_total = total + duration_ms
        else:
            new_count = 1
            new_total = duration_ms

        await self.cache.set(key, f"{new_count}:{new_total}", ttl=86400)

    async def get_counter(self, metric_name: str) -> int:
        """Get current value of a counter metric."""
        key = f"metrics:counter:{metric_name}"
        value = await self.cache.get(key)
        return int(value) if value else 0

    async def get_average_duration(self, metric_name: str) -> Optional[float]:
        """Get average duration for a metric."""
        key = f"metrics:duration:{metric_name}"
        value = await self.cache.get(key)
        if not value:
            return None

        parts = value.split(":")
        count = int(parts[0])
        total = float(parts[1])
        return total / count if count > 0 else None

    async def get_user_metrics(self, user_id: UUID) -> dict:
        """Get metrics for a specific user."""
        prefix = f"metrics:user:{user_id}:"
        
        # Get requests count
        requests_key = f"{prefix}requests"
        requests = await self.cache.get(requests_key)
        
        # Get success rate
        success_key = f"{prefix}success"
        success = await self.cache.get(success_key)
        
        # Get errors
        errors_key = f"{prefix}errors"
        errors = await self.cache.get(errors_key)

        total_requests = int(requests) if requests else 0
        total_success = int(success) if success else 0
        total_errors = int(errors) if errors else 0

        success_rate = (
            (total_success / total_requests * 100) if total_requests > 0 else 0
        )

        return {
            "total_requests": total_requests,
            "successful_requests": total_success,
            "failed_requests": total_errors,
            "success_rate": round(success_rate, 2),
        }

    async def increment_user_metric(
        self, user_id: UUID, metric_type: str, value: int = 1
    ) -> None:
        """Increment a user-specific metric."""
        key = f"metrics:user:{user_id}:{metric_type}"
        current = await self.cache.get(key)
        current_value = int(current) if current else 0
        await self.cache.set(key, str(current_value + value), ttl=86400)

    async def get_global_stats(self) -> dict:
        """Get global application statistics."""
        stats = {}

        # API Requests
        stats["total_api_requests"] = await self.get_counter("api.requests.total")
        stats["successful_traces"] = await self.get_counter("trace.success")
        stats["failed_traces"] = await self.get_counter("trace.failed")

        # Rate Limits
        stats["rate_limit_hits"] = await self.get_counter("rate_limit.exceeded")

        # Authentication
        stats["new_users"] = await self.get_counter("auth.user_registered")
        stats["api_keys_created"] = await self.get_counter("auth.api_key_created")

        # Performance
        stats["avg_trace_duration_ms"] = await self.get_average_duration(
            "trace.duration"
        )

        # Calculate success rate
        total = stats["successful_traces"] + stats["failed_traces"]
        if total > 0:
            stats["success_rate"] = round(
                (stats["successful_traces"] / total * 100), 2
            )
        else:
            stats["success_rate"] = 0

        return stats

    async def reset_daily_metrics(self) -> None:
        """Reset daily metrics (should be called by a cron job)."""
        # This would typically be done by letting cache TTL expire
        # Or by using a time-based key like "metrics:2024-01-22:counter:..."
        pass


class MetricsMiddleware:
    """Middleware to track request metrics."""

    def __init__(self, metrics_service: MetricsService):
        """Initialize with metrics service."""
        self.metrics = metrics_service

    async def track_request(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        duration_ms: float,
        user_id: Optional[UUID] = None,
    ) -> None:
        """Track a request."""
        # Global metrics
        await self.metrics.increment_counter("api.requests.total")
        await self.metrics.increment_counter(f"api.{method.lower()}")
        await self.metrics.increment_counter(f"api.status.{status_code}")

        # Endpoint metrics
        safe_endpoint = endpoint.replace("/", "_").strip("_")
        await self.metrics.increment_counter(f"endpoint.{safe_endpoint}")

        # Duration
        await self.metrics.record_duration("api.request.duration", duration_ms)

        # User metrics
        if user_id:
            await self.metrics.increment_user_metric(user_id, "requests")
            if 200 <= status_code < 300:
                await self.metrics.increment_user_metric(user_id, "success")
            else:
                await self.metrics.increment_user_metric(user_id, "errors")
