"""API route definitions."""

import logging
from pathlib import Path
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse, JSONResponse

from app.api.dependencies import (
    get_cache_backend,
    get_pdf_generator,
    get_tracer_service,
    get_history_service,
    get_blockchain_provider,
)
from app.api.auth_middleware import check_rate_limit, get_current_user
from app.config import Settings, get_settings
from app.constants import SUPPORTED_CHAINS
from app.core.cache import CacheBackend
from app.core.provider import BlockchainProvider
from app.core.exceptions import (
    APIRateLimitError,
    InvalidTransactionError,
    SafeTraceError,
    TransactionNotFoundError,
    UnsupportedChainError,
)
from app.models.risk import HealthResponse, TraceRequest, TraceResponse
from app.models.auth import User, APIKey
from app.services.pdf_generator import PDFGeneratorService
from app.services.tracer import TransactionTracerService
from app.services.history_service import AnalysisHistoryService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["compliance"])


@router.post(
    "/compliance/trace",
    response_model=TraceResponse,
    summary="Trace Transaction Risk",
    description="Analyze a blockchain transaction for risk indicators by tracing fund origins.",
)
async def trace_transaction(
    request: TraceRequest,
    tracer: Annotated[TransactionTracerService, Depends(get_tracer_service)],
    pdf_generator: Annotated[PDFGeneratorService, Depends(get_pdf_generator)],
    settings: Annotated[Settings, Depends(get_settings)],
    user_and_key: Annotated[tuple[User, APIKey], Depends(get_current_user)],
    history_service: Annotated[AnalysisHistoryService, Depends(get_history_service)],
) -> TraceResponse:
    """
    Trace transaction risk and generate compliance report.
    
    **Authentication required:** Provide API key via X-API-Key header.

    - **tx_hash**: Transaction hash to analyze (hex string, e.g., 0x123...)
    - **chain**: Blockchain network (bitcoin, ethereum, etc.)
    - **depth**: Number of hops to trace (1-10, default: 3)
    """
    # Check rate limit
    user, api_key = user_and_key
    await check_rate_limit(user, api_key)
    
    try:
        # Validate chain
        chain = request.chain.lower()
        if chain not in SUPPORTED_CHAINS:
            raise UnsupportedChainError(chain)

        # Perform tracing
        report = await tracer.trace_transaction_risk(
            tx_hash=request.tx_hash,
            chain=chain,
            depth=request.depth,
        )

        # Generate PDF
        pdf_bytes, file_path = pdf_generator.generate_certificate(
            report, save_to_file=True
        )
        pdf_base64 = pdf_generator.generate_certificate_base64(report)

        # Build response
        pdf_url = None
        if file_path:
            filename = Path(file_path).name
            pdf_url = f"{settings.api_prefix}/compliance/download/{filename}"

        # Save to history
        try:
            if history_service:
                await history_service.save_analysis(
                    user_id=user.id,
                    tx_hash=request.tx_hash,
                    chain=chain,
                    depth=request.depth,
                    risk_score=report.risk_score.score,
                    risk_level=report.risk_score.level.value,
                    flagged_entities=[e.dict() if hasattr(e, 'dict') else str(e) for e in report.flagged_entities] if report.flagged_entities else None,
                    total_addresses=report.total_addresses_analyzed,
                    api_calls_used=report.api_calls_used,
                    pdf_url=pdf_url,
                )
        except Exception as e:
            logger.warning(f"Failed to save analysis to history: {e}")

        return TraceResponse(
            success=True,
            message=f"Analysis complete. Risk level: {report.risk_score.level.value}",
            report=report,
            pdf_url=pdf_url,
            pdf_base64=pdf_base64,
        )

    except TransactionNotFoundError as e:
        logger.warning(f"Transaction not found: {e.tx_hash}")
        return TraceResponse(
            success=False,
            message=f"Transaction not found: {e.tx_hash}",
        )

    except UnsupportedChainError as e:
        logger.warning(f"Unsupported chain: {e.chain}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported blockchain: {e.chain}. Supported chains: {list(SUPPORTED_CHAINS.keys())}",
        )

    except InvalidTransactionError as e:
        logger.warning(f"Invalid transaction: {e.tx_hash}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid transaction hash: {e.tx_hash}",
        )

    except APIRateLimitError as e:
        logger.error(f"Rate limit exceeded: {e.provider}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"API rate limit exceeded. Retry after {e.retry_after}s",
            headers={"Retry-After": str(int(e.retry_after or 60))},
        )

    except SafeTraceError as e:
        logger.error(f"SafeTrace error: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e.message,
        )

    except Exception as e:
        logger.exception(f"Unexpected error during tracing: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during analysis",
        )


@router.get(
    "/compliance/download/{filename}",
    summary="Download Compliance Certificate",
    description="Download a previously generated PDF compliance certificate.",
)
async def download_certificate(
    filename: str,
    settings: Annotated[Settings, Depends(get_settings)],
) -> FileResponse:
    """Download a generated compliance certificate PDF."""
    import re
    
    # Validação de segurança: apenas nomes de arquivo válidos (sem path traversal)
    # Aceita apenas: letras, números, hífens, underscores, e uma extensão .pdf
    if not re.match(r'^[a-zA-Z0-9_\-]+\.pdf$', filename):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename format",
        )
    
    # Construir path de forma segura
    base_dir = Path(settings.pdf_output_dir).resolve()
    file_path = (base_dir / filename).resolve()
    
    # Verificação adicional: garantir que o arquivo está dentro do diretório permitido
    try:
        file_path.relative_to(base_dir)
    except ValueError:
        # O arquivo está fora do diretório base (tentativa de path traversal)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename",
        )
    
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificate not found",
        )

    if not file_path.suffix == ".pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type",
        )

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/pdf",
    )


@router.get(
    "/chains",
    summary="List Supported Chains",
    description="Get list of all supported blockchain networks.",
)
async def list_supported_chains() -> JSONResponse:
    """List all supported blockchain networks."""
    chains = [
        {
            "slug": config.slug,
            "name": config.name,
            "symbol": config.symbol,
            "type": config.chain_type.value,
            "has_internal_txs": config.has_internal_txs,
        }
        for config in SUPPORTED_CHAINS.values()
    ]
    return JSONResponse(content={"chains": chains, "count": len(chains)})


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check",
    description="Check API and cache health status.",
)
async def health_check(
    cache: Annotated[CacheBackend, Depends(get_cache_backend)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> HealthResponse:
    """Check API health and cache connectivity."""
    cache_healthy = await cache.ping()
    
    overall_status = "healthy" if cache_healthy else "degraded"
    cache_status = "connected" if cache_healthy else "disconnected"

    return HealthResponse(
        status=overall_status,
        version=settings.app_version,
        cache_status=cache_status,
    )


@router.get(
    "/providers/health",
    summary="Provider Health Check",
    description="Check health status of all blockchain data providers.",
)
async def providers_health_check(
    provider: Annotated[BlockchainProvider, Depends(get_blockchain_provider)],
) -> JSONResponse:
    """Check health status of all blockchain providers."""
    try:
        health = await provider.health_check()
        return JSONResponse(content=health)
    except Exception as e:
        logger.error(f"Provider health check failed: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "error": str(e),
            }
        )


@router.get(
    "/stats",
    summary="API Statistics",
    description="Get current API usage statistics.",
)
async def get_stats(
    settings: Annotated[Settings, Depends(get_settings)],
) -> JSONResponse:
    """Get API usage statistics."""
    return JSONResponse(
        content={
            "app_name": settings.app_name,
            "version": settings.app_version,
            "cache_backend": settings.cache_backend,
            "max_trace_depth": settings.max_trace_depth,
            "cache_ttl_seconds": settings.cache_ttl_seconds,
            "supported_chains_count": len(SUPPORTED_CHAINS),
        }
    )
