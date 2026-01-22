"""Middleware for automatic metrics and audit logging."""

import time
from typing import Callable
from uuid import UUID

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.services.audit_logger import AuditAction, AuditLogger
from app.services.metrics_service import MetricsMiddleware, MetricsService


class MonitoringMiddleware(BaseHTTPMiddleware):
    """Middleware to track requests, metrics, and audit logs."""

    def __init__(self, app, cache_backend, db_pool=None):
        """Initialize monitoring middleware."""
        super().__init__(app)
        self.metrics_service = MetricsService(cache_backend)
        self.metrics_middleware = MetricsMiddleware(self.metrics_service)
        self.audit_logger = AuditLogger(db_pool) if db_pool else None

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and track metrics."""
        start_time = time.time()

        # Get user info if authenticated
        user_id = None
        api_key_id = None
        if hasattr(request.state, "user"):
            user_id = request.state.user.id
        if hasattr(request.state, "api_key"):
            api_key_id = request.state.api_key.id

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000

        # Track metrics
        await self.metrics_middleware.track_request(
            endpoint=request.url.path,
            method=request.method,
            status_code=response.status_code,
            duration_ms=duration_ms,
            user_id=user_id,
        )

        # Log certain actions to audit log
        if self.audit_logger and user_id:
            await self._maybe_audit_log(
                request=request,
                response=response,
                user_id=user_id,
                api_key_id=api_key_id,
            )

        # Add custom headers
        response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"

        return response

    async def _maybe_audit_log(
        self,
        request: Request,
        response: Response,
        user_id: UUID,
        api_key_id: UUID = None,
    ) -> None:
        """Log certain actions to audit log."""
        path = request.url.path
        method = request.method
        status_code = response.status_code

        # Get client info
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")

        action = None
        details = {}

        # Determine action type based on endpoint
        if path == "/api/v1/auth/register" and status_code == 201:
            action = AuditAction.USER_REGISTERED
        elif path == "/api/v1/auth/bootstrap" and status_code == 201:
            action = AuditAction.API_KEY_CREATED
        elif path.startswith("/api/v1/auth/api-keys") and method == "POST":
            action = AuditAction.API_KEY_CREATED
        elif path.startswith("/api/v1/auth/api-keys") and method == "DELETE":
            action = AuditAction.API_KEY_REVOKED
        elif path == "/api/v1/compliance/trace":
            if status_code == 200:
                action = AuditAction.TRACE_SUCCESS
            else:
                action = AuditAction.TRACE_FAILED
            details = {"endpoint": path, "method": method}
        elif status_code == 429:
            action = AuditAction.RATE_LIMIT_EXCEEDED

        # Log if action identified
        if action:
            await self.audit_logger.log(
                action=action,
                user_id=user_id,
                api_key_id=api_key_id,
                details=details,
                ip_address=ip_address,
                user_agent=user_agent,
            )
