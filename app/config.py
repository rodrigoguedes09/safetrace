"""Application configuration and settings."""

import os
from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_name: str = "SafeTrace"
    app_version: str = "1.0.0"
    debug: bool = False
    port: int = Field(default=8000, description="Server port (Railway sets $PORT)")

    # API
    api_prefix: str = "/api/v1"

    # Blockchair API
    blockchair_api_key: SecretStr = Field(default=SecretStr(""))
    blockchair_base_url: str = "https://api.blockchair.com"
    blockchair_requests_per_second: float = 10.0
    blockchair_max_retries: int = 3
    blockchair_retry_delay: float = 1.0

    # Cache
    cache_backend: Literal["redis", "postgres", "memory"] = "redis"
    cache_ttl_seconds: int = 86400  # 24 hours

    # Redis - Railway injects REDIS_URL automatically
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis URL (Railway sets this automatically)"
    )

    # PostgreSQL - Railway injects DATABASE_URL automatically
    database_url: str = Field(
        default="",
        description="Database URL from Railway (renamed from DATABASE_URL)"
    )
    postgres_dsn: str = Field(
        default="postgresql://user:pass@localhost:5432/safetrace",
        description="PostgreSQL DSN"
    )

    # Tracing
    default_trace_depth: int = 3
    max_trace_depth: int = 10

    # PDF Generation - Use /tmp for Railway (ephemeral storage)
    pdf_output_dir: str = Field(
        default="./reports",
        description="PDF output directory"
    )

    # JWT Configuration
    jwt_secret_key: str = Field(
        default="",
        description="Secret key for JWT token signing (REQUIRED in production)"
    )
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 30 * 24 * 60  # 30 days

    # CORS Configuration
    allowed_origins: str = Field(
        default="",
        description="Comma-separated list of allowed origins for CORS"
    )

    # BFS Tracing Limits
    max_addresses_per_trace: int = Field(
        default=1000,
        description="Maximum addresses to visit during BFS tracing"
    )

    @field_validator("postgres_dsn")
    @classmethod
    def set_postgres_dsn(cls, v: str, info) -> str:
        """Use DATABASE_URL from Railway if available."""
        database_url = info.data.get("database_url") or os.getenv("DATABASE_URL", "")
        if database_url:
            return database_url
        return v

    @field_validator("pdf_output_dir")
    @classmethod
    def set_pdf_dir(cls, v: str) -> str:
        """Use /tmp for Railway ephemeral storage."""
        if os.getenv("RAILWAY_ENVIRONMENT"):
            return "/tmp/reports"
        return v

    @field_validator("port")
    @classmethod
    def set_port(cls, v: int) -> int:
        """Use PORT from Railway if available."""
        return int(os.getenv("PORT", v))


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()
