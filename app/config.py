"""Application configuration and settings."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
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

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # PostgreSQL
    postgres_dsn: str = "postgresql://user:pass@localhost:5432/safetrace"

    # Tracing
    default_trace_depth: int = 3
    max_trace_depth: int = 10

    # PDF Generation
    pdf_output_dir: str = "./reports"


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()
