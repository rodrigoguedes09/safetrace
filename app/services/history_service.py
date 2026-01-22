"""Analysis history service for storing and retrieving trace results."""

import json
import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class AnalysisHistoryEntry(BaseModel):
    """Model for an analysis history entry."""
    
    id: int
    user_id: UUID
    tx_hash: str
    chain: str
    depth: int
    risk_score: int
    risk_level: str
    flagged_entities: Optional[list] = None
    total_addresses: Optional[int] = None
    api_calls_used: Optional[int] = None
    pdf_url: Optional[str] = None
    created_at: datetime


class AnalysisHistoryService:
    """Service for managing analysis history."""

    def __init__(self, db_pool):
        """Initialize the service with database pool."""
        self.db_pool = db_pool

    async def save_analysis(
        self,
        user_id: UUID,
        tx_hash: str,
        chain: str,
        depth: int,
        risk_score: int,
        risk_level: str,
        flagged_entities: Optional[list] = None,
        total_addresses: Optional[int] = None,
        api_calls_used: Optional[int] = None,
        pdf_url: Optional[str] = None,
    ) -> int:
        """
        Save an analysis result to history.
        
        Returns the ID of the created record.
        """
        try:
            async with self.db_pool.acquire() as conn:
                result = await conn.fetchrow(
                    """
                    INSERT INTO analysis_history 
                    (user_id, tx_hash, chain, depth, risk_score, risk_level, 
                     flagged_entities, total_addresses, api_calls_used, pdf_url)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    RETURNING id
                    """,
                    user_id,
                    tx_hash,
                    chain,
                    depth,
                    risk_score,
                    risk_level,
                    json.dumps(flagged_entities) if flagged_entities else None,
                    total_addresses,
                    api_calls_used,
                    pdf_url,
                )
                return result["id"]
        except Exception as e:
            logger.error(f"Failed to save analysis history: {e}")
            raise

    async def get_user_history(
        self,
        user_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        """
        Get analysis history for a user.
        
        Returns a list of analysis entries ordered by most recent first.
        """
        try:
            async with self.db_pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT id, tx_hash, chain, depth, risk_score, risk_level,
                           flagged_entities, total_addresses, api_calls_used,
                           pdf_url, created_at
                    FROM analysis_history
                    WHERE user_id = $1
                    ORDER BY created_at DESC
                    LIMIT $2 OFFSET $3
                    """,
                    user_id,
                    limit,
                    offset,
                )
                
                return [
                    {
                        "id": row["id"],
                        "tx_hash": row["tx_hash"],
                        "chain": row["chain"],
                        "depth": row["depth"],
                        "risk_score": row["risk_score"],
                        "risk_level": row["risk_level"],
                        "flagged_entities": json.loads(row["flagged_entities"]) if row["flagged_entities"] else [],
                        "total_addresses": row["total_addresses"],
                        "api_calls_used": row["api_calls_used"],
                        "pdf_url": row["pdf_url"],
                        "timestamp": row["created_at"].isoformat(),
                    }
                    for row in rows
                ]
        except Exception as e:
            logger.error(f"Failed to get user history: {e}")
            return []

    async def get_user_stats(self, user_id: UUID) -> dict:
        """
        Get statistics for a user's analyses.
        
        Returns total count, high risk count, chains analyzed, etc.
        """
        try:
            async with self.db_pool.acquire() as conn:
                # Total count
                total = await conn.fetchval(
                    "SELECT COUNT(*) FROM analysis_history WHERE user_id = $1",
                    user_id,
                )
                
                # High risk count (score > 50)
                high_risk = await conn.fetchval(
                    """
                    SELECT COUNT(*) FROM analysis_history 
                    WHERE user_id = $1 AND risk_score > 50
                    """,
                    user_id,
                )
                
                # Unique chains
                chains = await conn.fetch(
                    """
                    SELECT DISTINCT chain FROM analysis_history 
                    WHERE user_id = $1
                    """,
                    user_id,
                )
                
                # Average risk score
                avg_risk = await conn.fetchval(
                    """
                    SELECT AVG(risk_score) FROM analysis_history 
                    WHERE user_id = $1
                    """,
                    user_id,
                )
                
                return {
                    "total_analyses": total or 0,
                    "high_risk_count": high_risk or 0,
                    "chains_analyzed": [row["chain"] for row in chains],
                    "average_risk_score": round(avg_risk, 1) if avg_risk else 0,
                }
        except Exception as e:
            logger.error(f"Failed to get user stats: {e}")
            return {
                "total_analyses": 0,
                "high_risk_count": 0,
                "chains_analyzed": [],
                "average_risk_score": 0,
            }

    async def get_analysis_by_id(
        self,
        analysis_id: int,
        user_id: UUID,
    ) -> Optional[dict]:
        """
        Get a specific analysis by ID (only if owned by user).
        """
        try:
            async with self.db_pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT id, tx_hash, chain, depth, risk_score, risk_level,
                           flagged_entities, total_addresses, api_calls_used,
                           pdf_url, created_at
                    FROM analysis_history
                    WHERE id = $1 AND user_id = $2
                    """,
                    analysis_id,
                    user_id,
                )
                
                if not row:
                    return None
                
                return {
                    "id": row["id"],
                    "tx_hash": row["tx_hash"],
                    "chain": row["chain"],
                    "depth": row["depth"],
                    "risk_score": row["risk_score"],
                    "risk_level": row["risk_level"],
                    "flagged_entities": json.loads(row["flagged_entities"]) if row["flagged_entities"] else [],
                    "total_addresses": row["total_addresses"],
                    "api_calls_used": row["api_calls_used"],
                    "pdf_url": row["pdf_url"],
                    "timestamp": row["created_at"].isoformat(),
                }
        except Exception as e:
            logger.error(f"Failed to get analysis: {e}")
            return None
