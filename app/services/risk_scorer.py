"""Risk scoring service implementing weighted scoring algorithm."""

import logging
from typing import Any

from app.constants import RISK_TAG_WEIGHTS, RiskLevel, RiskTag
from app.models.blockchain import AddressMetadata
from app.models.risk import FlaggedEntity, RiskScore

logger = logging.getLogger(__name__)


class RiskScorerService:
    """
    Service for calculating transaction risk scores.
    
    Implements a weighted scoring model based on:
    - Presence of high-risk tags (Mixer, Darknet, etc.)
    - Proximity to flagged entities
    - Transaction patterns
    """

    def __init__(
        self,
        tag_weights: dict[RiskTag, float] | None = None,
        proximity_decay: float = 0.5,
        max_score: int = 100,
    ) -> None:
        """
        Initialize the risk scorer.

        Args:
            tag_weights: Custom weights for risk tags.
            proximity_decay: Decay factor per hop distance.
            max_score: Maximum possible risk score.
        """
        self._tag_weights = tag_weights or RISK_TAG_WEIGHTS
        self._proximity_decay = proximity_decay
        self._max_score = max_score

    def calculate_score(
        self,
        flagged_entities: list[FlaggedEntity],
        address_metadata: dict[str, AddressMetadata],
        trace_depth: int,
    ) -> RiskScore:
        """
        Calculate the overall risk score for a transaction.

        The scoring formula is:
        R = sum(V_i * W_i * D_i)
        
        Where:
        - V_i: Risk factor value (1 if present, 0 otherwise)
        - W_i: Weight for the risk factor
        - D_i: Distance decay factor (proximity_decay ^ distance)

        Args:
            flagged_entities: List of flagged entities from tracing.
            address_metadata: Metadata for analyzed addresses.
            trace_depth: Maximum depth that was traced.

        Returns:
            RiskScore with score, level, and reasons.
        """
        if not flagged_entities:
            return RiskScore.from_score(0, ["No suspicious entities detected"])

        total_score = 0.0
        reasons: list[str] = []
        processed_addresses: set[str] = set()

        # Calculate contribution from each flagged entity
        for entity in flagged_entities:
            address_key = entity.address.lower()
            if address_key in processed_addresses:
                continue
            processed_addresses.add(address_key)

            entity_contribution = self._calculate_entity_score(entity)
            total_score += entity_contribution

            # Generate reason string
            if entity_contribution != 0:
                tag_names = [tag.value for tag in entity.tags]
                direction = "increases" if entity_contribution > 0 else "decreases"
                reasons.append(
                    f"Address {entity.address[:10]}... with tags [{', '.join(tag_names)}] "
                    f"at distance {entity.distance} {direction} risk by {abs(entity_contribution):.1f}"
                )

        # Apply proximity bonus for exchanges (reduces risk)
        exchange_proximity_bonus = self._calculate_exchange_proximity_bonus(
            flagged_entities
        )
        if exchange_proximity_bonus != 0:
            total_score += exchange_proximity_bonus
            reasons.append(
                f"Proximity to exchange reduces risk by {abs(exchange_proximity_bonus):.1f}"
            )

        # Apply volume analysis if available
        volume_adjustment = self._calculate_volume_adjustment(address_metadata)
        if volume_adjustment != 0:
            total_score += volume_adjustment
            reasons.append(
                f"Transaction volume pattern adjustment: {volume_adjustment:+.1f}"
            )

        # Normalize to 0-100
        normalized_score = self._normalize_score(total_score)

        if not reasons:
            reasons.append("Risk score based on traced transaction patterns")

        return RiskScore.from_score(normalized_score, reasons)

    def calculate_entity_contribution(
        self,
        tags: list[RiskTag],
        distance: int,
    ) -> float:
        """
        Calculate the risk contribution of a single entity.

        Args:
            tags: Risk tags associated with the entity.
            distance: Number of hops from the original transaction.

        Returns:
            Risk contribution value.
        """
        if not tags:
            return 0.0

        # Get the highest weight tag
        max_weight = max(self._tag_weights.get(tag, 0.0) for tag in tags)
        
        # Apply distance decay
        decay_factor = self._proximity_decay ** distance
        
        return max_weight * decay_factor * 100

    def _calculate_entity_score(self, entity: FlaggedEntity) -> float:
        """Calculate score contribution from a flagged entity."""
        if not entity.tags:
            return 0.0

        # Sum weights for all tags (allowing additive risk)
        tag_score = sum(
            self._tag_weights.get(tag, 0.0) for tag in entity.tags
        )
        
        # Apply distance decay
        decay_factor = self._proximity_decay ** entity.distance
        
        return tag_score * decay_factor * 50

    def _calculate_exchange_proximity_bonus(
        self,
        flagged_entities: list[FlaggedEntity],
    ) -> float:
        """Calculate risk reduction from proximity to exchanges."""
        exchange_entities = [
            e for e in flagged_entities
            if RiskTag.EXCHANGE in e.tags
        ]
        
        if not exchange_entities:
            return 0.0

        # Closest exchange provides the most risk reduction
        min_distance = min(e.distance for e in exchange_entities)
        
        # Exchange proximity reduces risk
        exchange_weight = self._tag_weights.get(RiskTag.EXCHANGE, -0.2)
        decay_factor = self._proximity_decay ** min_distance
        
        return exchange_weight * decay_factor * 100

    def _calculate_volume_adjustment(
        self,
        address_metadata: dict[str, AddressMetadata],
    ) -> float:
        """
        Calculate risk adjustment based on transaction volume patterns.
        
        High-value transactions from low-volume wallets are suspicious.
        """
        if not address_metadata:
            return 0.0

        suspicious_count = 0
        total_analyzed = 0

        for metadata in address_metadata.values():
            if metadata.tx_count < 10 and metadata.balance > 0:
                # Low activity wallet with balance
                suspicious_count += 1
            total_analyzed += 1

        if total_analyzed == 0:
            return 0.0

        # Calculate suspicion ratio
        suspicion_ratio = suspicious_count / total_analyzed
        
        # Weight factor for volume analysis (0.5 as specified)
        volume_weight = 0.5
        
        return suspicion_ratio * volume_weight * 20

    def _normalize_score(self, raw_score: float) -> int:
        """Normalize raw score to 0-100 range."""
        # Apply sigmoid-like normalization for extreme values
        if raw_score <= 0:
            return 0
        if raw_score >= 100:
            return 100
        
        # Linear scaling for mid-range
        return int(min(max(raw_score, 0), 100))

    def get_risk_level(self, score: int) -> RiskLevel:
        """Determine risk level from numeric score."""
        if score <= 30:
            return RiskLevel.LOW
        if score <= 70:
            return RiskLevel.MEDIUM
        return RiskLevel.HIGH

    def get_level_description(self, level: RiskLevel) -> str:
        """Get human-readable description for risk level."""
        descriptions = {
            RiskLevel.LOW: "Transaction appears to have low risk. "
                          "No significant connections to high-risk entities detected.",
            RiskLevel.MEDIUM: "Transaction has moderate risk indicators. "
                             "Some connections to flagged entities detected within trace depth.",
            RiskLevel.HIGH: "Transaction has high risk indicators. "
                           "Direct or close connections to high-risk entities detected.",
        }
        return descriptions.get(level, "Unknown risk level")
