"""Tests for risk scoring service."""

import pytest

from app.constants import RiskLevel, RiskTag
from app.models.risk import FlaggedEntity
from app.services.risk_scorer import RiskScorerService


class TestRiskScorerService:
    """Tests for RiskScorerService."""

    def test_calculate_score_no_entities(self, risk_scorer: RiskScorerService) -> None:
        """Test scoring with no flagged entities."""
        result = risk_scorer.calculate_score([], {}, 3)
        
        assert result.score == 0
        assert result.level == RiskLevel.LOW
        assert len(result.reasons) > 0

    def test_calculate_score_mixer_direct(self, risk_scorer: RiskScorerService) -> None:
        """Test scoring with direct mixer connection."""
        entities = [
            FlaggedEntity(
                address="0x1234567890abcdef",
                chain="ethereum",
                tags=[RiskTag.MIXER],
                distance=0,
            )
        ]
        
        result = risk_scorer.calculate_score(entities, {}, 3)
        
        assert result.score > 50
        assert result.level in (RiskLevel.MEDIUM, RiskLevel.HIGH)

    def test_calculate_score_distance_decay(self, risk_scorer: RiskScorerService) -> None:
        """Test that distance reduces risk contribution."""
        entity_close = FlaggedEntity(
            address="0x1234567890abcdef",
            chain="ethereum",
            tags=[RiskTag.MIXER],
            distance=0,
        )
        
        entity_far = FlaggedEntity(
            address="0xabcdef1234567890",
            chain="ethereum",
            tags=[RiskTag.MIXER],
            distance=3,
        )
        
        score_close = risk_scorer.calculate_score([entity_close], {}, 3)
        score_far = risk_scorer.calculate_score([entity_far], {}, 3)
        
        assert score_close.score > score_far.score

    def test_calculate_score_exchange_reduces_risk(
        self, risk_scorer: RiskScorerService
    ) -> None:
        """Test that exchange proximity reduces risk."""
        entities = [
            FlaggedEntity(
                address="0x1234567890abcdef",
                chain="ethereum",
                tags=[RiskTag.EXCHANGE],
                distance=1,
            )
        ]
        
        result = risk_scorer.calculate_score(entities, {}, 3)
        
        # Exchange should reduce or maintain low risk
        assert result.score <= 30
        assert result.level == RiskLevel.LOW

    def test_calculate_entity_contribution(
        self, risk_scorer: RiskScorerService
    ) -> None:
        """Test individual entity contribution calculation."""
        contribution = risk_scorer.calculate_entity_contribution(
            [RiskTag.MIXER], distance=0
        )
        
        assert contribution > 0

    def test_calculate_entity_contribution_decay(
        self, risk_scorer: RiskScorerService
    ) -> None:
        """Test contribution decay with distance."""
        contrib_0 = risk_scorer.calculate_entity_contribution([RiskTag.HACK], 0)
        contrib_1 = risk_scorer.calculate_entity_contribution([RiskTag.HACK], 1)
        contrib_2 = risk_scorer.calculate_entity_contribution([RiskTag.HACK], 2)
        
        assert contrib_0 > contrib_1 > contrib_2

    def test_get_risk_level_thresholds(
        self, risk_scorer: RiskScorerService
    ) -> None:
        """Test risk level determination."""
        assert risk_scorer.get_risk_level(0) == RiskLevel.LOW
        assert risk_scorer.get_risk_level(30) == RiskLevel.LOW
        assert risk_scorer.get_risk_level(31) == RiskLevel.MEDIUM
        assert risk_scorer.get_risk_level(70) == RiskLevel.MEDIUM
        assert risk_scorer.get_risk_level(71) == RiskLevel.HIGH
        assert risk_scorer.get_risk_level(100) == RiskLevel.HIGH

    def test_multiple_tags_additive(self, risk_scorer: RiskScorerService) -> None:
        """Test that multiple tags increase risk additively."""
        single_tag = [
            FlaggedEntity(
                address="0x1234567890abcdef",
                chain="ethereum",
                tags=[RiskTag.MIXER],
                distance=0,
            )
        ]
        
        multiple_tags = [
            FlaggedEntity(
                address="0x1234567890abcdef",
                chain="ethereum",
                tags=[RiskTag.MIXER, RiskTag.DARKNET],
                distance=0,
            )
        ]
        
        score_single = risk_scorer.calculate_score(single_tag, {}, 3)
        score_multiple = risk_scorer.calculate_score(multiple_tags, {}, 3)
        
        assert score_multiple.score >= score_single.score
