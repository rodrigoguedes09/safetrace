"""Frontend routes for serving HTML pages."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.constants import SUPPORTED_CHAINS

router = APIRouter(tags=["Frontend"])

# Initialize templates
templates = Jinja2Templates(directory="frontend/templates")


@router.get("/", response_class=HTMLResponse)
async def landing_page(request: Request) -> HTMLResponse:
    """Serve the landing page."""
    # Get first 16 chains for display
    chains = list(SUPPORTED_CHAINS.keys())[:16]
    return templates.TemplateResponse(
        "landing.html",
        {"request": request, "chains": chains}
    )


@router.get("/pricing", response_class=HTMLResponse)
async def pricing_page(request: Request) -> HTMLResponse:
    """Serve the pricing page."""
    return templates.TemplateResponse(
        "pricing.html",
        {"request": request}
    )


@router.get("/analyze", response_class=HTMLResponse)
async def analyze_page(request: Request) -> HTMLResponse:
    """Serve the KYT analysis page."""
    return templates.TemplateResponse(
        "analyze.html",
        {"request": request}
    )


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request) -> HTMLResponse:
    """Serve the user dashboard page."""
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request}
    )


@router.get("/documentation", response_class=HTMLResponse)
async def docs_page(request: Request) -> HTMLResponse:
    """Serve the documentation page."""
    return templates.TemplateResponse(
        "documentation.html",
        {"request": request}
    )
