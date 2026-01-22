"""Risk assessment domain models."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.constants import RiskLevel, RiskTag


class RiskScore(BaseModel):
    """Risk score with level classification."""

    score: int = Field(ge=0, le=100)
    level: RiskLevel
    reasons: list[str] = Field(default_factory=list)

    @classmethod
    def from_score(cls, score: int, reasons: list[str] | None = None) -> "RiskScore":
        """Create RiskScore from a numeric score."""
        clamped_score = max(0, min(100, score))
        if clamped_score <= 30:
            level = RiskLevel.LOW
        elif clamped_score <= 70:
            level = RiskLevel.MEDIUM
        else:
            level = RiskLevel.HIGH
        return cls(score=clamped_score, level=level, reasons=reasons or [])


class FlaggedEntity(BaseModel):
    """Entity flagged during risk analysis."""

    address: str
    chain: str
    tags: list[RiskTag]
    distance: int = Field(ge=0, description="Number of hops from original transaction")
    tx_hash: str | None = None
    contribution_score: float = Field(
        default=0.0, description="Contribution to overall risk score"
    )


class RiskReport(BaseModel):
    """Complete risk analysis report for a transaction."""

    tx_hash: str
    chain: str
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)
    trace_depth: int
    total_addresses_analyzed: int = 0
    total_transactions_analyzed: int = 0
    risk_score: RiskScore
    flagged_entities: list[FlaggedEntity] = Field(default_factory=list)
    api_calls_used: int = 0

    def has_high_risk_entities(self) -> bool:
        """Check if any high-risk entities were found."""
        high_risk_tags = {RiskTag.MIXER, RiskTag.DARKNET, RiskTag.HACK, RiskTag.SANCTIONED}
        for entity in self.flagged_entities:
            if set(entity.tags) & high_risk_tags:
                return True
        return False


class TraceRequest(BaseModel):
    """Request model for transaction tracing."""

    tx_hash: str = Field(..., min_length=10, description="Transaction hash to trace")
    chain: str = Field(default="ethereum", description="Blockchain network")
    depth: int = Field(default=3, ge=1, le=10, description="Tracing depth (hops)")


class TraceResponse(BaseModel):
    """Response model for transaction tracing."""

    success: bool
    message: str = ""
    report: RiskReport | None = None
    pdf_url: str | None = None
    pdf_base64: str | None = None


class HealthResponse(BaseModel):
    """Health check response model."""

    status: Literal["healthy", "degraded", "unhealthy"]
    version: str
    cache_status: Literal["connected", "disconnected"]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
