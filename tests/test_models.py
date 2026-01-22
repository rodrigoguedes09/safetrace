"""Tests for Pydantic models."""

from datetime import datetime
from decimal import Decimal

import pytest

from app.constants import ChainType, RiskLevel, RiskTag
from app.models.blockchain import AddressMetadata, Transaction, TransactionInput
from app.models.risk import FlaggedEntity, RiskReport, RiskScore, TraceRequest


class TestTransactionModel:
    """Tests for Transaction model."""

    def test_utxo_transaction(self) -> None:
        """Test UTXO transaction creation."""
        tx = Transaction(
            tx_hash="abc123",
            chain="bitcoin",
            chain_type=ChainType.UTXO,
            inputs=[
                TransactionInput(address="1abc", value=Decimal("0.5")),
                TransactionInput(address="1def", value=Decimal("0.3")),
            ],
        )
        
        addresses = tx.get_source_addresses()
        
        assert len(addresses) == 2
        assert "1abc" in addresses
        assert "1def" in addresses

    def test_account_transaction(self) -> None:
        """Test account-based transaction creation."""
        tx = Transaction(
            tx_hash="0xabc123",
            chain="ethereum",
            chain_type=ChainType.ACCOUNT,
            sender="0x1234",
            recipient="0x5678",
            value=Decimal("1.5"),
        )
        
        addresses = tx.get_source_addresses()
        
        assert len(addresses) == 1
        assert addresses[0] == "0x1234"


class TestAddressMetadataModel:
    """Tests for AddressMetadata model."""

    def test_is_high_risk(self) -> None:
        """Test high risk detection."""
        high_risk = AddressMetadata(
            address="0x1234",
            chain="ethereum",
            tags=[RiskTag.MIXER],
        )
        
        low_risk = AddressMetadata(
            address="0x5678",
            chain="ethereum",
            tags=[RiskTag.EXCHANGE],
        )
        
        assert high_risk.is_high_risk() is True
        assert low_risk.is_high_risk() is False

    def test_is_exchange(self) -> None:
        """Test exchange detection."""
        exchange = AddressMetadata(
            address="0x1234",
            chain="ethereum",
            tags=[RiskTag.EXCHANGE],
        )
        
        not_exchange = AddressMetadata(
            address="0x5678",
            chain="ethereum",
            tags=[RiskTag.WHALE],
        )
        
        assert exchange.is_exchange() is True
        assert not_exchange.is_exchange() is False


class TestRiskScoreModel:
    """Tests for RiskScore model."""

    def test_from_score_low(self) -> None:
        """Test low risk score creation."""
        score = RiskScore.from_score(15, ["Test reason"])
        
        assert score.score == 15
        assert score.level == RiskLevel.LOW
        assert "Test reason" in score.reasons

    def test_from_score_medium(self) -> None:
        """Test medium risk score creation."""
        score = RiskScore.from_score(50)
        
        assert score.score == 50
        assert score.level == RiskLevel.MEDIUM

    def test_from_score_high(self) -> None:
        """Test high risk score creation."""
        score = RiskScore.from_score(85)
        
        assert score.score == 85
        assert score.level == RiskLevel.HIGH

    def test_from_score_clamped(self) -> None:
        """Test score clamping."""
        score_low = RiskScore.from_score(-10)
        score_high = RiskScore.from_score(150)
        
        assert score_low.score == 0
        assert score_high.score == 100


class TestTraceRequestModel:
    """Tests for TraceRequest model."""

    def test_valid_request(self) -> None:
        """Test valid trace request."""
        request = TraceRequest(
            tx_hash="0x" + "a" * 64,
            chain="ethereum",
            depth=3,
        )
        
        assert request.tx_hash.startswith("0x")
        assert request.chain == "ethereum"
        assert request.depth == 3

    def test_default_values(self) -> None:
        """Test default values."""
        request = TraceRequest(tx_hash="0x" + "b" * 64)
        
        assert request.chain == "ethereum"
        assert request.depth == 3

    def test_depth_validation(self) -> None:
        """Test depth validation."""
        with pytest.raises(ValueError):
            TraceRequest(tx_hash="0x" + "c" * 64, depth=0)
        
        with pytest.raises(ValueError):
            TraceRequest(tx_hash="0x" + "d" * 64, depth=11)


class TestRiskReportModel:
    """Tests for RiskReport model."""

    def test_has_high_risk_entities(self) -> None:
        """Test high risk entity detection."""
        report_with_risk = RiskReport(
            tx_hash="0xabc",
            chain="ethereum",
            trace_depth=3,
            risk_score=RiskScore(score=75, level=RiskLevel.HIGH),
            flagged_entities=[
                FlaggedEntity(
                    address="0x1234",
                    chain="ethereum",
                    tags=[RiskTag.MIXER],
                    distance=1,
                )
            ],
        )
        
        report_without_risk = RiskReport(
            tx_hash="0xdef",
            chain="ethereum",
            trace_depth=3,
            risk_score=RiskScore(score=10, level=RiskLevel.LOW),
            flagged_entities=[
                FlaggedEntity(
                    address="0x5678",
                    chain="ethereum",
                    tags=[RiskTag.EXCHANGE],
                    distance=1,
                )
            ],
        )
        
        assert report_with_risk.has_high_risk_entities() is True
        assert report_without_risk.has_high_risk_entities() is False
