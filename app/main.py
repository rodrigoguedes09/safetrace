"""FastAPI application factory and main entry point."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.dependencies import cleanup_dependencies, get_db_pool
from app.api.routes import router
from app.api.auth_routes import router as auth_router
from app.api.admin_routes import router as admin_router
from app.config import get_settings
from app.db.schema import init_auth_tables

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager for startup and shutdown events."""
    settings = get_settings()
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Cache backend: {settings.cache_backend}")
    logger.info(f"Max trace depth: {settings.max_trace_depth}")
    
    # Initialize database tables
    try:
        db_pool = await get_db_pool(settings)
        await init_auth_tables(db_pool)
        logger.info("Database tables initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
    
    yield
    
    logger.info("Shutting down SafeTrace...")
    await cleanup_dependencies()
    logger.info("Cleanup complete")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        description=(
            "Blockchain Compliance Tool (KYT) for tracing transaction risk "
            "across 41+ blockchains. Analyzes fund origins and identifies "
            "proximity to high-risk entities."
        ),
        version=settings.app_version,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include API routes
    app.include_router(router)
    app.include_router(auth_router)
    app.include_router(admin_router)

    @app.get("/", tags=["root"])
    async def root() -> dict[str, str]:
        """Root endpoint with API information."""
        return {
            "name": settings.app_name,
            "version": settings.app_version,
            "docs": "/docs",
            "health": f"{settings.api_prefix}/health",
        }

    return app


# Create application instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="info",
    )
