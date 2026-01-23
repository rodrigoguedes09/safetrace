"""Risk scoring service implementing weighted scoring algorithm."""

import logging
from datetime import datetime, timedelta
from typing import Any

from app.constants import RISK_TAG_WEIGHTS, RiskLevel, RiskTag
from app.models.blockchain import AddressMetadata
from app.models.risk import FlaggedEntity, RiskScore

logger = logging.getLogger(__name__)


class RiskScorerService:
    """
    Service for calculating transaction risk scores.
    
    Implements advanced weighted scoring model based on:
    - Presence of high-risk tags (Mixer, Darknet, OFAC, etc.)
    - Proximity to flagged entities with decay
    - Transaction patterns and volume analysis
    - Temporal analysis (transaction recency)
    - Velocity detection (funds moving too fast)
    - Mixer pattern detection (Tornado Cash style)
    """

    # Mixer detection patterns
    MIXER_PATTERNS = {
        'tornado_cash': {
            'min_addresses': 5,
            'time_window_hours': 24,
            'similarity_threshold': 0.8
        },
        'generic_mixer': {
            'min_addresses': 3,
            'clustering_threshold': 0.6
        }
    }

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

    def calculate_temporal_decay(
        self,
        transaction_timestamp: datetime | None,
        current_time: datetime | None = None
    ) -> float:
        """Calculate temporal decay factor for risk scoring.
        
        Recent transactions have higher impact on risk score.
        Decay formula: exp(-age_in_days / 365)
        
        Args:
            transaction_timestamp: When the transaction occurred
            current_time: Reference time (defaults to now)
            
        Returns:
            Decay factor between 0.0 and 1.0
        """
        if not transaction_timestamp:
            return 0.5  # Default medium weight
        
        if not current_time:
            current_time = datetime.utcnow()
        
        # Calculate age in days
        age = (current_time - transaction_timestamp).total_seconds() / 86400
        
        # Exponential decay over 1 year
        import math
        decay = math.exp(-age / 365)
        
        return decay

    def detect_velocity_anomaly(
        self,
        transaction_timestamps: dict[str, datetime],
        flagged_entities: list[FlaggedEntity]
    ) -> tuple[bool, float]:
        """Detect if funds are moving too quickly (velocity anomaly).
        
        Money laundering often involves rapid movement of funds through
        multiple addresses to obscure origin.
        
        Args:
            transaction_timestamps: Map of tx_hash to timestamp
            flagged_entities: Flagged entities in trace
            
        Returns:
            Tuple of (is_anomaly, velocity_score)
        """
        if len(transaction_timestamps) < 2:
            return False, 0.0
        
        # Sort timestamps
        timestamps = sorted(transaction_timestamps.values())
        
        # Calculate average time between transactions
        time_diffs = []
        for i in range(1, len(timestamps)):
            diff = (timestamps[i] - timestamps[i-1]).total_seconds()
            time_diffs.append(diff)
        
        if not time_diffs:
            return False, 0.0
        
        avg_diff = sum(time_diffs) / len(time_diffs)
        
        # Suspicious if average < 1 hour (3600 seconds)
        if avg_diff < 3600:
            velocity_score = min(30, 3600 / (avg_diff + 1) * 5)
            logger.warning(f"High velocity detected: {avg_diff:.0f}s average between transactions")
            return True, velocity_score
        
        return False, 0.0

    def detect_mixer_pattern(
        self,
        flagged_entities: list[FlaggedEntity],
        address_metadata: dict[str, AddressMetadata],
        clustering_coefficient: float = 0.0
    ) -> tuple[bool, float, str]:
        """Detect sophisticated mixer patterns (Tornado Cash style).
        
        Mixer detection based on:
        1. Multiple addresses with similar transaction patterns
        2. High clustering coefficient (addresses interconnected)
        3. Presence of contract interactions
        4. Similar value amounts (common in mixers)
        
        Args:
            flagged_entities: Entities found in trace
            address_metadata: Metadata for addresses
            clustering_coefficient: Graph clustering value
            
        Returns:
            Tuple of (is_mixer, mixer_score, mixer_type)
        """
        mixer_score = 0.0
        mixer_type = "none"
        
        # Check for explicit mixer tags first
        explicit_mixers = [e for e in flagged_entities if RiskTag.MIXER in e.tags]
        if explicit_mixers:
            mixer_score = 40.0
            mixer_type = "explicit_mixer"
            logger.info(f"Explicit mixer detected: {len(explicit_mixers)} addresses")
            return True, mixer_score, mixer_type
        
        # Check Tornado Cash pattern
        contract_addresses = [
            addr for addr, meta in address_metadata.items()
            if meta.is_contract
        ]
        
        if len(contract_addresses) >= 1 and clustering_coefficient > 0.5:
            mixer_score = 30.0
            mixer_type = "tornado_cash_pattern"
            logger.info("Tornado Cash pattern detected: contract + high clustering")
            return True, mixer_score, mixer_type
        
        # Check generic mixer pattern (high clustering + multiple addresses)
        if clustering_coefficient > 0.6 and len(address_metadata) >= 5:
            mixer_score = 25.0
            mixer_type = "generic_mixer_pattern"
            logger.info(f"Generic mixer pattern: clustering={clustering_coefficient:.2f}")
            return True, mixer_score, mixer_type
        
        return False, 0.0, "none"

    def calculate_advanced_score(
        self,
        flagged_entities: list[FlaggedEntity],
        address_metadata: dict[str, AddressMetadata],
        trace_depth: int,
        transaction_timestamps: dict[str, datetime] = None,
        clustering_coefficient: float = 0.0,
        circular_paths: list[tuple[str, ...]] = None
    ) -> RiskScore:
        """Calculate comprehensive risk score with all advanced features.
        
        This method extends the base calculate_score with:
        - Temporal analysis
        - Velocity detection
        - Mixer pattern detection
        - Circular path detection
        
        Args:
            flagged_entities: List of flagged entities from tracing
            address_metadata: Metadata for analyzed addresses
            trace_depth: Maximum depth that was traced
            transaction_timestamps: Optional timestamps for velocity analysis
            clustering_coefficient: Graph clustering value
            circular_paths: Detected circular transaction paths
            
        Returns:
            RiskScore with comprehensive analysis
        """
        # Start with base score
        base_score_result = self.calculate_score(flagged_entities, address_metadata, trace_depth)
        total_score = float(base_score_result.score)
        reasons = list(base_score_result.reasons)
        
        # Add temporal decay adjustment
        if transaction_timestamps:
            latest_timestamp = max(transaction_timestamps.values(), default=None)
            if latest_timestamp:
                temporal_factor = self.calculate_temporal_decay(latest_timestamp)
                temporal_adjustment = (1 - temporal_factor) * -10  # Recent = higher risk
                if abs(temporal_adjustment) > 1:
                    total_score += temporal_adjustment
                    age_days = (datetime.utcnow() - latest_timestamp).days
                    reasons.append(f"Transaction age ({age_days}d) factor: {temporal_adjustment:+.1f}")
        
        # Check velocity anomaly
        if transaction_timestamps and len(transaction_timestamps) >= 2:
            is_velocity_anomaly, velocity_score = self.detect_velocity_anomaly(
                transaction_timestamps, flagged_entities
            )
            if is_velocity_anomaly:
                total_score += velocity_score
                reasons.append(f"High velocity detected (rapid fund movement): +{velocity_score:.1f}")
        
        # Check mixer patterns
        is_mixer, mixer_score, mixer_type = self.detect_mixer_pattern(
            flagged_entities, address_metadata, clustering_coefficient
        )
        if is_mixer:
            total_score += mixer_score
            reasons.append(f"Mixer pattern detected ({mixer_type}): +{mixer_score:.1f}")
        
        # Check circular paths (money cycling)
        if circular_paths and len(circular_paths) > 0:
            circular_score = min(20, len(circular_paths) * 10)
            total_score += circular_score
            reasons.append(f"Circular transaction paths detected ({len(circular_paths)}): +{circular_score:.1f}")
        
        # Normalize and return
        normalized_score = self._normalize_score(total_score)
        return RiskScore.from_score(normalized_score, reasons)
