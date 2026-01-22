"""Blockchain-related domain models."""

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

from app.constants import ChainType, RiskTag


class TransactionInput(BaseModel):
    """Model representing a transaction input (UTXO chains)."""

    address: str
    value: Decimal
    tx_hash: str | None = None
    output_index: int | None = None


class TransactionOutput(BaseModel):
    """Model representing a transaction output."""

    address: str
    value: Decimal
    output_index: int


class InternalTransaction(BaseModel):
    """Model representing an internal transaction (EVM chains)."""

    from_address: str
    to_address: str
    value: Decimal
    call_type: str = "call"
    trace_index: int = 0


class Transaction(BaseModel):
    """Normalized transaction model supporting both UTXO and Account-based chains."""

    tx_hash: str
    chain: str
    chain_type: ChainType
    block_height: int | None = None
    block_hash: str | None = None
    timestamp: datetime | None = None
    fee: Decimal = Decimal("0")
    size: int | None = None

    # UTXO-specific
    inputs: list[TransactionInput] = Field(default_factory=list)
    outputs: list[TransactionOutput] = Field(default_factory=list)

    # Account-based specific
    sender: str | None = None
    recipient: str | None = None
    value: Decimal = Decimal("0")
    gas_used: int | None = None
    gas_price: Decimal | None = None
    nonce: int | None = None
    is_contract_call: bool = False

    # Internal transactions (EVM)
    internal_transactions: list[InternalTransaction] = Field(default_factory=list)

    # Raw data for extensibility
    raw_data: dict[str, Any] = Field(default_factory=dict)

    def get_source_addresses(self) -> list[str]:
        """Get all source addresses for this transaction."""
        if self.chain_type == ChainType.UTXO:
            return [inp.address for inp in self.inputs if inp.address]
        addresses = []
        if self.sender:
            addresses.append(self.sender)
        for itx in self.internal_transactions:
            if itx.from_address and itx.from_address not in addresses:
                addresses.append(itx.from_address)
        return addresses


class AddressMetadata(BaseModel):
    """Metadata for a blockchain address."""

    address: str
    chain: str
    tags: list[RiskTag] = Field(default_factory=list)
    labels: list[str] = Field(default_factory=list)
    balance: Decimal = Decimal("0")
    tx_count: int = 0
    first_seen: datetime | None = None
    last_seen: datetime | None = None
    is_contract: bool = False
    context: dict[str, Any] = Field(default_factory=dict)

    def is_high_risk(self) -> bool:
        """Check if address has any high-risk tags."""
        high_risk_tags = {
            RiskTag.MIXER,
            RiskTag.DARKNET,
            RiskTag.HACK,
            RiskTag.SANCTIONED,
            RiskTag.RANSOMWARE,
            RiskTag.TERRORIST_FINANCING,
        }
        return bool(set(self.tags) & high_risk_tags)

    def is_exchange(self) -> bool:
        """Check if address belongs to an exchange."""
        return RiskTag.EXCHANGE in self.tags
