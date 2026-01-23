"""Audit logging service for tracking user actions."""

import json
import logging
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID

logger = logging.getLogger(__name__)


# Maximum size for details JSONB (in characters)
MAX_DETAILS_SIZE = 10000
# Allowed keys in details dict (whitelist for security)
ALLOWED_DETAIL_KEYS = {
    "endpoint", "method", "tx_hash", "chain", "depth", "risk_score", 
    "error", "message", "status_code", "api_calls_used", "addresses_analyzed"
}


class AuditAction(str, Enum):
    """Audit action types."""

    # Authentication
    USER_REGISTERED = "user.registered"
    USER_LOGIN = "user.login"
    API_KEY_CREATED = "api_key.created"
    API_KEY_REVOKED = "api_key.revoked"
    
    # API Usage
    TRACE_REQUEST = "trace.request"
    TRACE_SUCCESS = "trace.success"
    TRACE_FAILED = "trace.failed"
    
    # Rate Limiting
    RATE_LIMIT_EXCEEDED = "rate_limit.exceeded"
    RATE_LIMIT_RESET = "rate_limit.reset"
    
    # Admin
    USER_UPGRADED = "user.upgraded"
    USER_DOWNGRADED = "user.downgraded"
    USER_DEACTIVATED = "user.deactivated"


class AuditLogger:
    """Service for audit logging."""

    def __init__(self, db_pool=None):
        """Initialize audit logger with optional database pool."""
        self.db_pool = db_pool

    def _sanitize_details(self, details: Optional[dict[str, Any]]) -> dict[str, Any]:
        """
        Sanitize details dict to prevent injection and limit size.
        
        - Only allows whitelisted keys
        - Converts all values to safe string representations
        - Truncates to max size
        """
        if not details:
            return {}
        
        if not isinstance(details, dict):
            logger.warning(f"Invalid details type: {type(details)}, expected dict")
            return {"_invalid": "details was not a dict"}
        
        sanitized = {}
        for key, value in details.items():
            # Only allow whitelisted keys (or log unknown keys with prefix)
            if key in ALLOWED_DETAIL_KEYS:
                sanitized[key] = self._sanitize_value(value)
            else:
                # Log unknown keys with a prefix for debugging
                sanitized[f"_extra_{key[:50]}"] = self._sanitize_value(value)
        
        # Check total size
        try:
            serialized = json.dumps(sanitized)
            if len(serialized) > MAX_DETAILS_SIZE:
                logger.warning(f"Details truncated from {len(serialized)} to {MAX_DETAILS_SIZE}")
                sanitized = {"_truncated": True, "_message": "Details too large"}
        except (TypeError, ValueError) as e:
            logger.error(f"Failed to serialize details: {e}")
            sanitized = {"_error": "Failed to serialize details"}
        
        return sanitized

    def _sanitize_value(self, value: Any, max_str_len: int = 500) -> Any:
        """Sanitize a single value to safe types."""
        if value is None:
            return None
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value
        if isinstance(value, str):
            # Truncate long strings and remove control characters
            safe_str = value[:max_str_len]
            # Remove null bytes and other control chars
            safe_str = ''.join(c for c in safe_str if ord(c) >= 32 or c in '\n\r\t')
            return safe_str
        if isinstance(value, (list, tuple)):
            # Limit list size and sanitize each item
            return [self._sanitize_value(v, max_str_len) for v in value[:50]]
        if isinstance(value, dict):
            # Recursively sanitize nested dicts (limited depth)
            return {str(k)[:100]: self._sanitize_value(v, max_str_len) for k, v in list(value.items())[:20]}
        # Convert unknown types to string representation
        return str(value)[:max_str_len]

    async def log(
        self,
        action: AuditAction,
        user_id: Optional[UUID] = None,
        api_key_id: Optional[UUID] = None,
        details: Optional[dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        """
        Log an audit event.

        Args:
            action: The action being audited
            user_id: ID of the user performing the action
            api_key_id: ID of the API key used
            details: Additional details about the action
            ip_address: Client IP address
            user_agent: Client user agent
        """
        timestamp = datetime.utcnow()
        
        # Sanitize details before storing
        sanitized_details = self._sanitize_details(details)
        
        log_entry = {
            "timestamp": timestamp.isoformat(),
            "action": action.value,
            "user_id": str(user_id) if user_id else None,
            "api_key_id": str(api_key_id) if api_key_id else None,
            "details": sanitized_details,
            "ip_address": ip_address,
            "user_agent": user_agent,
        }

        # Log to stdout (structured logging)
        logger.info(
            f"AUDIT: {action.value}",
            extra={
                "audit": True,
                "audit_data": log_entry,
            },
        )

        # Optionally store in database for compliance
        if self.db_pool:
            try:
                await self._store_in_database(log_entry)
            except Exception as e:
                logger.error(f"Failed to store audit log in database: {e}")

    async def _store_in_database(self, log_entry: dict[str, Any]) -> None:
        """Store audit log in database."""
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO audit_logs 
                (timestamp, action, user_id, api_key_id, details, ip_address, user_agent)
                VALUES ($1, $2, $3::uuid, $4::uuid, $5::jsonb, $6, $7)
                """,
                log_entry["timestamp"],
                log_entry["action"],
                log_entry["user_id"],
                log_entry["api_key_id"],
                log_entry["details"],
                log_entry["ip_address"],
                log_entry["user_agent"],
            )

    async def get_user_activity(
        self, user_id: UUID, limit: int = 100
    ) -> list[dict[str, Any]]:
        """Get recent activity for a user."""
        if not self.db_pool:
            return []

        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT timestamp, action, details, ip_address
                FROM audit_logs
                WHERE user_id = $1
                ORDER BY timestamp DESC
                LIMIT $2
                """,
                user_id,
                limit,
            )
            return [dict(row) for row in rows]

    async def get_failed_attempts(
        self, user_id: Optional[UUID] = None, minutes: int = 60
    ) -> int:
        """Get count of failed authentication attempts."""
        if not self.db_pool:
            return 0

        async with self.db_pool.acquire() as conn:
            query = """
                SELECT COUNT(*)
                FROM audit_logs
                WHERE action = 'trace.failed'
                AND timestamp > NOW() - INTERVAL '{} minutes'
            """.format(minutes)

            if user_id:
                query += " AND user_id = $1"
                count = await conn.fetchval(query, user_id)
            else:
                count = await conn.fetchval(query)

            return count or 0


# Create audit log table schema
AUDIT_SCHEMA = """
CREATE TABLE IF NOT EXISTS audit_logs (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    action VARCHAR(100) NOT NULL,
    user_id UUID,
    api_key_id UUID,
    details JSONB,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_api_key_id ON audit_logs(api_key_id);
"""
