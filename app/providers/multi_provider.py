"""Multi-provider manager for blockchain data with automatic fallback."""

import asyncio
import logging
from typing import Any

from app.core.provider import BlockchainProvider
from app.models.blockchain import AddressMetadata, InternalTransaction, Transaction
from app.providers.blockchair import BlockchairProvider
from app.providers.blockchain_com import BlockchainComProvider

logger = logging.getLogger(__name__)


class MultiProviderManager(BlockchainProvider):
    """
    Manager that coordinates multiple blockchain data providers.
    
    Features:
    - Automatic selection of best provider per chain
    - Fallback when primary provider fails
    - Combined address transaction history from multiple sources
    - Aggregated health status
    
    Provider priority:
    - Bitcoin: blockchain_com (free, full tx history) > blockchair
    - Other chains: blockchair (supports 40+ chains)
    """

    def __init__(
        self,
        blockchair_provider: BlockchairProvider,
        blockchain_com_provider: BlockchainComProvider | None = None,
    ) -> None:
        """
        Initialize the multi-provider manager.

        Args:
            blockchair_provider: Primary provider for most chains.
            blockchain_com_provider: Optional Bitcoin-specific provider.
        """
        self._blockchair = blockchair_provider
        self._blockchain_com = blockchain_com_provider
        self._request_count = 0
        
        logger.info(
            f"[MultiProvider] Initialized with providers: "
            f"blockchair=True, blockchain_com={blockchain_com_provider is not None}"
        )

    @property
    def name(self) -> str:
        """Provider name identifier."""
        return "multi_provider"

    @property
    def supported_chains(self) -> list[str]:
        """List of supported blockchain identifiers."""
        chains = set(self._blockchair.supported_chains)
        if self._blockchain_com:
            chains.update(self._blockchain_com.supported_chains)
        return list(chains)

    def _get_provider_for_chain(self, chain: str) -> BlockchainProvider:
        """
        Get the best provider for a specific chain.
        
        Bitcoin uses Blockchain.com (free, full tx history) if available.
        Other chains use Blockchair.
        """
        chain_lower = chain.lower()
        
        # Prefer Blockchain.com for Bitcoin (free API, full tx history)
        if chain_lower in ("bitcoin", "btc") and self._blockchain_com:
            logger.debug(f"[MultiProvider] Using blockchain_com for {chain}")
            return self._blockchain_com
        
        logger.debug(f"[MultiProvider] Using blockchair for {chain}")
        return self._blockchair

    async def get_transaction(self, chain: str, tx_hash: str) -> Transaction:
        """Fetch transaction from the best available provider."""
        provider = self._get_provider_for_chain(chain)
        self._request_count += 1
        
        logger.info(f"[MultiProvider] get_transaction via {provider.name} for {tx_hash[:16]}... on {chain}")
        
        try:
            return await provider.get_transaction(chain, tx_hash)
        except Exception as e:
            # Fallback to alternative provider
            if provider != self._blockchair:
                logger.warning(f"[MultiProvider] {provider.name} failed, falling back to blockchair: {e}")
                return await self._blockchair.get_transaction(chain, tx_hash)
            raise

    async def get_transaction_inputs(
        self, chain: str, tx_hash: str
    ) -> list[tuple[str, str]]:
        """Get input transactions from the best available provider."""
        provider = self._get_provider_for_chain(chain)
        self._request_count += 1
        
        logger.debug(f"[MultiProvider] get_transaction_inputs via {provider.name}")
        
        try:
            return await provider.get_transaction_inputs(chain, tx_hash)
        except Exception as e:
            if provider != self._blockchair:
                logger.warning(f"[MultiProvider] {provider.name} failed, falling back: {e}")
                return await self._blockchair.get_transaction_inputs(chain, tx_hash)
            raise

    async def get_address_metadata(
        self, chain: str, address: str
    ) -> AddressMetadata:
        """Fetch address metadata from the best available provider."""
        provider = self._get_provider_for_chain(chain)
        self._request_count += 1
        
        logger.debug(f"[MultiProvider] get_address_metadata via {provider.name}")
        
        try:
            return await provider.get_address_metadata(chain, address)
        except Exception as e:
            if provider != self._blockchair:
                logger.warning(f"[MultiProvider] {provider.name} failed, falling back: {e}")
                return await self._blockchair.get_address_metadata(chain, address)
            raise

    async def get_internal_transactions(
        self, chain: str, tx_hash: str
    ) -> list[InternalTransaction]:
        """Get internal transactions from the best available provider."""
        provider = self._get_provider_for_chain(chain)
        self._request_count += 1
        
        logger.debug(f"[MultiProvider] get_internal_transactions via {provider.name}")
        
        try:
            return await provider.get_internal_transactions(chain, tx_hash)
        except Exception as e:
            if provider != self._blockchair:
                logger.warning(f"[MultiProvider] {provider.name} failed, falling back: {e}")
                return await self._blockchair.get_internal_transactions(chain, tx_hash)
            raise

    async def is_contract(self, chain: str, address: str) -> bool:
        """Check if an address is a smart contract."""
        provider = self._get_provider_for_chain(chain)
        self._request_count += 1
        
        logger.debug(f"[MultiProvider] is_contract via {provider.name}")
        
        try:
            return await provider.is_contract(chain, address)
        except Exception as e:
            if provider != self._blockchair:
                logger.warning(f"[MultiProvider] {provider.name} failed, falling back: {e}")
                return await self._blockchair.is_contract(chain, address)
            raise

    async def get_address_transactions(
        self, chain: str, address: str, limit: int = 50, offset: int = 0
    ) -> list[Transaction]:
        """
        Fetch transaction history for an address.
        
        This is where Blockchain.com shines for Bitcoin!
        """
        provider = self._get_provider_for_chain(chain)
        
        # Only Blockchain.com provider has this method
        if hasattr(provider, 'get_address_transactions'):
            logger.info(f"[MultiProvider] get_address_transactions via {provider.name}")
            return await provider.get_address_transactions(chain, address, limit, offset)
        
        logger.warning(f"[MultiProvider] Address transaction history not available for {chain}")
        return []

    async def get_unspent_outputs(
        self, chain: str, address: str
    ) -> list[dict[str, Any]]:
        """
        Fetch UTXOs for an address (Bitcoin only via Blockchain.com).
        """
        chain_lower = chain.lower()
        
        if chain_lower in ("bitcoin", "btc") and self._blockchain_com:
            logger.info(f"[MultiProvider] get_unspent_outputs via blockchain_com")
            return await self._blockchain_com.get_unspent_outputs(chain, address)
        
        logger.warning(f"[MultiProvider] UTXO fetch not available for {chain}")
        return []

    async def close(self) -> None:
        """Close all provider connections."""
        logger.info("[MultiProvider] Closing all provider connections...")
        
        close_tasks = [self._blockchair.close()]
        if self._blockchain_com:
            close_tasks.append(self._blockchain_com.close())
        
        await asyncio.gather(*close_tasks, return_exceptions=True)

    def get_request_count(self) -> int:
        """Get total number of API requests made across all providers."""
        total = self._request_count
        total += self._blockchair.get_request_count()
        if self._blockchain_com:
            total += self._blockchain_com.get_request_count()
        return total

    def reset_request_count(self) -> None:
        """Reset the request counter for all providers."""
        self._request_count = 0
        self._blockchair.reset_request_count()
        if self._blockchain_com:
            self._blockchain_com.reset_request_count()

    async def health_check(self) -> dict[str, Any]:
        """Check health status of all providers."""
        logger.info("[MultiProvider] Performing health check for all providers...")
        
        health_tasks = [self._blockchair.health_check()]
        if self._blockchain_com:
            health_tasks.append(self._blockchain_com.health_check())
        
        results = await asyncio.gather(*health_tasks, return_exceptions=True)
        
        provider_status = {}
        all_healthy = True
        
        # Blockchair status
        if isinstance(results[0], dict):
            provider_status["blockchair"] = results[0]
            if results[0].get("status") != "healthy":
                all_healthy = False
        else:
            provider_status["blockchair"] = {"status": "error", "error": str(results[0])}
            all_healthy = False
        
        # Blockchain.com status
        if self._blockchain_com and len(results) > 1:
            if isinstance(results[1], dict):
                provider_status["blockchain_com"] = results[1]
                if results[1].get("status") != "healthy":
                    all_healthy = False
            else:
                provider_status["blockchain_com"] = {"status": "error", "error": str(results[1])}
                all_healthy = False
        
        return {
            "status": "healthy" if all_healthy else "degraded",
            "provider": self.name,
            "total_request_count": self.get_request_count(),
            "providers": provider_status,
        }
