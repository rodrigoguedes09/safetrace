"""Abstract blockchain provider interface."""

from abc import ABC, abstractmethod

from app.models.blockchain import AddressMetadata, InternalTransaction, Transaction


class BlockchainProvider(ABC):
    """Abstract base class for blockchain data providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name identifier."""
        ...

    @property
    @abstractmethod
    def supported_chains(self) -> list[str]:
        """List of supported blockchain identifiers."""
        ...

    @abstractmethod
    async def get_transaction(self, chain: str, tx_hash: str) -> Transaction:
        """
        Fetch transaction details from the blockchain.

        Args:
            chain: Blockchain identifier (e.g., 'bitcoin', 'ethereum').
            tx_hash: Transaction hash.

        Returns:
            Normalized Transaction object.

        Raises:
            TransactionNotFoundError: If the transaction doesn't exist.
            UnsupportedChainError: If the chain is not supported.
            APIRateLimitError: If rate limit is exceeded.
        """
        ...

    @abstractmethod
    async def get_transaction_inputs(
        self, chain: str, tx_hash: str
    ) -> list[tuple[str, str]]:
        """
        Get the input transactions for a given transaction (UTXO chains).

        Args:
            chain: Blockchain identifier.
            tx_hash: Transaction hash.

        Returns:
            List of tuples (address, previous_tx_hash).
        """
        ...

    @abstractmethod
    async def get_internal_transactions(
        self, chain: str, tx_hash: str
    ) -> list[InternalTransaction]:
        """
        Get internal transactions for a given transaction (EVM chains).

        Args:
            chain: Blockchain identifier.
            tx_hash: Transaction hash.

        Returns:
            List of InternalTransaction objects.
        """
        ...

    @abstractmethod
    async def get_address_metadata(
        self, chain: str, address: str
    ) -> AddressMetadata:
        """
        Fetch metadata for a blockchain address.

        Args:
            chain: Blockchain identifier.
            address: Blockchain address.

        Returns:
            AddressMetadata object with tags, labels, and statistics.

        Raises:
            AddressNotFoundError: If the address has no activity.
            UnsupportedChainError: If the chain is not supported.
        """
        ...

    @abstractmethod
    async def is_contract(self, chain: str, address: str) -> bool:
        """
        Check if an address is a smart contract.

        Args:
            chain: Blockchain identifier.
            address: Address to check.

        Returns:
            True if the address is a contract.
        """
        ...

    @abstractmethod
    async def close(self) -> None:
        """Close the provider and release resources."""
        ...

    def supports_chain(self, chain: str) -> bool:
        """Check if the provider supports a given chain."""
        return chain.lower() in [c.lower() for c in self.supported_chains]
