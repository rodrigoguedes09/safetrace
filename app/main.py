"""FastAPI application factory and main entry point."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.dependencies import cleanup_dependencies, get_db_pool
from app.api.routes import router
from app.api.auth_routes import router as auth_router
from app.api.auth_jwt_routes import router as auth_jwt_router
from app.api.admin_routes import router as admin_router
from app.api.frontend_routes import router as frontend_router
from app.api.debug_routes import debug_router
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


class DocsProtectionMiddleware(BaseHTTPMiddleware):
    """Middleware to protect API docs from public access."""
    
    PROTECTED_PATHS = ["/docs", "/redoc", "/openapi.json"]
    # Admin IPs permitidos (pode adicionar mais IPs conforme necessário)
    ALLOWED_IPS = ["127.0.0.1", "::1", "localhost"]
    
    async def dispatch(self, request: Request, call_next):
        """Check if request is trying to access protected docs."""
        path = request.url.path
        
        # Check if path is protected
        if any(path.startswith(protected) for protected in self.PROTECTED_PATHS):
            # Get client IP
            client_ip = request.client.host if request.client else None
            
            # Check if IP is allowed (localhost only)
            if client_ip not in self.ALLOWED_IPS:
                logger.warning(f"Blocked docs access attempt from {client_ip}")
                return RedirectResponse(url="/", status_code=302)
        
        return await call_next(request)


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

    # CORS middleware - restrito a origens configuradas
    allowed_origins = ["*"]  # Default para desenvolvimento
    if settings.allowed_origins:
        allowed_origins = [origin.strip() for origin in settings.allowed_origins.split(",") if origin.strip()]
    
    # Em produção, não permitir credenciais com wildcard
    allow_credentials = True
    if "*" in allowed_origins and not settings.debug:
        logger.warning("CORS: Using wildcard origins in production is not recommended")
        allow_credentials = False  # Desabilita credentials com wildcard
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=allow_credentials,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "X-API-Key", "Content-Type", "Accept"],
    )
    
    # Add docs protection middleware
    app.add_middleware(DocsProtectionMiddleware)

    # Mount static files from frontend directory
    static_dir = Path(__file__).parent.parent / "frontend" / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # Include API routes
    app.include_router(router)
    app.include_router(auth_router)
    app.include_router(auth_jwt_router)  # Alternativa JWT (mais simples)
    app.include_router(admin_router)
    
    # Debug endpoints - apenas em modo debug
    if settings.debug:
        app.include_router(debug_router)
        logger.warning("Debug endpoints enabled - do not use in production!")
    
    # Include frontend routes (must be last to avoid conflicts)
    app.include_router(frontend_router)

    # API info endpoint (different from root landing page)
    @app.get("/api", tags=["root"])
    async def api_info() -> dict[str, str]:
        """API information endpoint."""
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
