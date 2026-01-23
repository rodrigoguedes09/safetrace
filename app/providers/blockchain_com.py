"""Blockchain.com API provider implementation for Bitcoin."""

import asyncio
import logging
from datetime import datetime
from decimal import Decimal
from typing import Any

import httpx

from app.constants import ChainType, RiskTag
from app.core.exceptions import (
    APIRateLimitError,
    APITimeoutError,
    TransactionNotFoundError,
    UnsupportedChainError,
)
from app.core.provider import BlockchainProvider
from app.models.blockchain import (
    AddressMetadata,
    InternalTransaction,
    Transaction,
    TransactionInput,
    TransactionOutput,
)

logger = logging.getLogger(__name__)


class BlockchainComProvider(BlockchainProvider):
    """
    Blockchain.com API provider for Bitcoin.
    
    Features:
    - Free API with no key required
    - Full transaction history per address
    - Complete UTXO data
    - Rate limiting (built-in)
    
    Supported chains:
    - Bitcoin (BTC) only
    
    API Documentation: https://www.blockchain.com/explorer/api
    """

    SUPPORTED_CHAINS = {"bitcoin", "btc"}
    
    def __init__(
        self,
        base_url: str = "https://blockchain.info",
        requests_per_second: float = 5.0,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        timeout: float = 30.0,
    ) -> None:
        """
        Initialize Blockchain.com provider.

        Args:
            base_url: Base URL for Blockchain.com API.
            requests_per_second: Rate limit for requests.
            max_retries: Maximum number of retries on failure.
            retry_delay: Base delay between retries (exponential backoff).
            timeout: Request timeout in seconds.
        """
        self._base_url = base_url.rstrip("/")
        self._requests_per_second = requests_per_second
        self._max_retries = max_retries
        self._retry_delay = retry_delay
        self._timeout = timeout
        self._request_count = 0
        self._last_request_time: float = 0
        self._lock = asyncio.Lock()
        self._client: httpx.AsyncClient | None = None

    @property
    def name(self) -> str:
        """Provider name identifier."""
        return "blockchain_com"

    @property
    def supported_chains(self) -> list[str]:
        """List of supported blockchain identifiers."""
        return ["bitcoin"]

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self._timeout),
                headers={
                    "Accept": "application/json",
                    "User-Agent": "SafeTrace/1.0",
                },
            )
        return self._client

    async def _rate_limit(self) -> None:
        """Apply rate limiting between requests."""
        async with self._lock:
            now = asyncio.get_event_loop().time()
            min_interval = 1.0 / self._requests_per_second
            elapsed = now - self._last_request_time
            if elapsed < min_interval:
                wait_time = min_interval - elapsed
                logger.debug(f"[Blockchain.com API] Rate limiting: waiting {wait_time:.3f}s")
                await asyncio.sleep(wait_time)
            self._last_request_time = asyncio.get_event_loop().time()

    async def _request(
        self,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Make an HTTP GET request with retry logic.

        Args:
            path: API path.
            params: Query parameters.

        Returns:
            JSON response data.
        """
        await self._rate_limit()
        
        url = f"{self._base_url}/{path.lstrip('/')}"
        query_params = params or {}
        query_params["cors"] = "true"  # Enable CORS

        logger.info(f"[Blockchain.com API] GET {url}")
        logger.debug(f"[Blockchain.com API] Query params: {query_params}")

        client = await self._get_client()
        last_error: Exception | None = None

        for attempt in range(self._max_retries):
            try:
                self._request_count += 1
                logger.debug(f"[Blockchain.com API] Attempt {attempt + 1}/{self._max_retries} - Request #{self._request_count}")
                response = await client.get(url, params=query_params)

                if response.status_code == 429:
                    retry_after = float(response.headers.get("Retry-After", self._retry_delay))
                    logger.warning(f"[Blockchain.com API] Rate limit hit (429) - Retry after: {retry_after}s")
                    if attempt < self._max_retries - 1:
                        wait_time = retry_after * (2**attempt)
                        logger.info(f"[Blockchain.com API] Waiting {wait_time:.2f}s before retry")
                        await asyncio.sleep(wait_time)
                        continue
                    raise APIRateLimitError("blockchain_com", retry_after)

                if response.status_code == 404:
                    logger.warning(f"[Blockchain.com API] Resource not found (404): {url}")
                    return {}

                if response.status_code == 500:
                    logger.error(f"[Blockchain.com API] Server error (500)")
                    if attempt < self._max_retries - 1:
                        wait_time = self._retry_delay * (2**attempt)
                        logger.info(f"[Blockchain.com API] Retrying in {wait_time:.2f}s")
                        await asyncio.sleep(wait_time)
                        continue

                response.raise_for_status()
                logger.info(f"[Blockchain.com API] ✓ Success - Status {response.status_code}")
                return response.json()

            except httpx.TimeoutException as e:
                last_error = e
                logger.warning(f"[Blockchain.com API] Request timeout after {self._timeout}s")
                if attempt < self._max_retries - 1:
                    wait_time = self._retry_delay * (2**attempt)
                    logger.info(f"[Blockchain.com API] Retrying after timeout - waiting {wait_time:.2f}s")
                    await asyncio.sleep(wait_time)
                    continue
                raise APITimeoutError("blockchain_com", self._timeout) from e

            except httpx.HTTPStatusError as e:
                last_error = e
                logger.error(f"[Blockchain.com API] HTTP error {e.response.status_code}")
                raise

        if last_error:
            raise last_error
        return {}

    def _validate_chain(self, chain: str) -> None:
        """Validate that the chain is supported."""
        if chain.lower() not in self.SUPPORTED_CHAINS:
            raise UnsupportedChainError(chain)

    async def get_transaction(self, chain: str, tx_hash: str) -> Transaction:
        """Fetch transaction details from Blockchain.com."""
        self._validate_chain(chain)
        
        logger.info(f"[Blockchain.com] Fetching transaction {tx_hash[:16]}... on {chain}")
        
        data = await self._request(f"rawtx/{tx_hash}")
        
        if not data or "hash" not in data:
            logger.error(f"[Blockchain.com] Transaction {tx_hash[:16]}... not found")
            raise TransactionNotFoundError(tx_hash, chain)

        return self._parse_transaction(tx_hash, chain, data)

    def _parse_transaction(
        self,
        tx_hash: str,
        chain: str,
        data: dict[str, Any],
    ) -> Transaction:
        """Parse Blockchain.com transaction data."""
        logger.debug(f"[Blockchain.com] Parsing transaction - hash: {tx_hash[:16]}...")
        
        # Parse inputs
        inputs_data = data.get("inputs", [])
        logger.debug(f"[Blockchain.com] Found {len(inputs_data)} inputs")
        
        inputs = []
        for inp in inputs_data:
            prev_out = inp.get("prev_out", {})
            address = prev_out.get("addr", "")
            value = Decimal(str(prev_out.get("value", 0))) / Decimal("1e8")
            
            # Get the previous transaction hash (spending_outpoints may have it)
            # tx_index is an internal integer ID, not the actual tx hash
            # For proper tracing, we need to fetch the actual hash separately
            # For now, use tx_index as a string reference
            prev_tx_index = prev_out.get("tx_index")
            prev_tx_hash = str(prev_tx_index) if prev_tx_index else None
            
            inputs.append(
                TransactionInput(
                    address=address,
                    value=value,
                    tx_hash=prev_tx_hash,
                    output_index=prev_out.get("n"),
                )
            )

        # Parse outputs
        outputs_data = data.get("out", [])
        logger.debug(f"[Blockchain.com] Found {len(outputs_data)} outputs")
        
        outputs = []
        for idx, out in enumerate(outputs_data):
            address = out.get("addr", "")
            value = Decimal(str(out.get("value", 0))) / Decimal("1e8")
            
            outputs.append(
                TransactionOutput(
                    address=address,
                    value=value,
                    output_index=idx,
                )
            )

        # Parse timestamp
        timestamp = None
        if data.get("time"):
            try:
                timestamp = datetime.fromtimestamp(data["time"])
            except (ValueError, OSError):
                pass

        # Calculate fee
        total_in = sum(inp.value for inp in inputs)
        total_out = sum(out.value for out in outputs)
        fee = max(Decimal("0"), total_in - total_out)

        tx_value = sum(out.value for out in outputs)
        logger.info(f"[Blockchain.com] ✓ Transaction parsed - {len(inputs)} inputs, {len(outputs)} outputs, value: {tx_value:.8f} BTC")

        return Transaction(
            tx_hash=tx_hash,
            chain=chain,
            chain_type=ChainType.UTXO,
            block_height=data.get("block_height"),
            timestamp=timestamp,
            fee=fee,
            size=data.get("size"),
            inputs=inputs,
            outputs=outputs,
            raw_data=data,
        )

    async def get_transaction_inputs(
        self, chain: str, tx_hash: str
    ) -> list[tuple[str, str]]:
        """Get input transactions for Bitcoin."""
        self._validate_chain(chain)
        
        logger.debug(f"[Blockchain.com] Getting transaction inputs for {tx_hash[:16]}...")
        
        tx = await self.get_transaction(chain, tx_hash)
        result = []
        
        for inp in tx.inputs:
            if inp.address and inp.tx_hash:
                result.append((inp.address, str(inp.tx_hash)))
        
        logger.debug(f"[Blockchain.com] Found {len(result)} input transactions")
        return result

    async def get_address_metadata(
        self, chain: str, address: str
    ) -> AddressMetadata:
        """Fetch metadata for a Bitcoin address."""
        self._validate_chain(chain)
        
        logger.info(f"[Blockchain.com] Fetching address metadata for {address[:16]}... on {chain}")
        
        data = await self._request(f"rawaddr/{address}", {"limit": 50})
        
        if not data or "address" not in data:
            logger.warning(f"[Blockchain.com] Address {address[:16]}... not found")
            return AddressMetadata(address=address, chain=chain)

        # Parse balance
        balance = Decimal(str(data.get("final_balance", 0))) / Decimal("1e8")
        total_received = Decimal(str(data.get("total_received", 0))) / Decimal("1e8")
        total_sent = Decimal(str(data.get("total_sent", 0))) / Decimal("1e8")
        tx_count = data.get("n_tx", 0)

        # Analyze transactions for risk tags
        tags = self._analyze_address_for_tags(data)

        # Get first/last seen from transactions
        first_seen = None
        last_seen = None
        txs = data.get("txs", [])
        if txs:
            # Transactions are ordered newest first
            if txs[-1].get("time"):
                try:
                    first_seen = datetime.fromtimestamp(txs[-1]["time"])
                except (ValueError, OSError):
                    pass
            if txs[0].get("time"):
                try:
                    last_seen = datetime.fromtimestamp(txs[0]["time"])
                except (ValueError, OSError):
                    pass

        logger.info(f"[Blockchain.com] ✓ Address metadata retrieved - balance: {balance}, tx_count: {tx_count}, tags: {len(tags)}")

        return AddressMetadata(
            address=address,
            chain=chain,
            tags=tags,
            labels=[],
            balance=balance,
            tx_count=tx_count,
            first_seen=first_seen,
            last_seen=last_seen,
            is_contract=False,  # Bitcoin doesn't have contracts
            context={
                "total_received": str(total_received),
                "total_sent": str(total_sent),
                "n_unredeemed": data.get("n_unredeemed", 0),
            },
        )

    def _analyze_address_for_tags(self, data: dict[str, Any]) -> list[RiskTag]:
        """Analyze address data for risk tags."""
        tags: list[RiskTag] = []
        
        tx_count = data.get("n_tx", 0)
        total_received = Decimal(str(data.get("total_received", 0))) / Decimal("1e8")
        
        # Whale detection (>1000 BTC total received)
        if total_received > 1000:
            tags.append(RiskTag.WHALE)
        
        # High volume address (>10000 transactions)
        if tx_count > 10000:
            # Could be an exchange
            tags.append(RiskTag.EXCHANGE)
        
        return tags

    async def get_address_transactions(
        self, chain: str, address: str, limit: int = 50, offset: int = 0
    ) -> list[Transaction]:
        """
        Fetch transaction history for an address.
        
        This is a KEY feature that Blockchair doesn't provide easily!
        
        Args:
            chain: Blockchain (must be bitcoin)
            address: Bitcoin address
            limit: Number of transactions to fetch (max 50)
            offset: Offset for pagination
            
        Returns:
            List of transactions
        """
        self._validate_chain(chain)
        
        logger.info(f"[Blockchain.com] Fetching transactions for address {address[:16]}... (limit={limit}, offset={offset})")
        
        data = await self._request(
            f"rawaddr/{address}",
            {"limit": min(limit, 50), "offset": offset}
        )
        
        if not data or "txs" not in data:
            logger.warning(f"[Blockchain.com] No transactions found for {address[:16]}...")
            return []

        transactions = []
        for tx_data in data.get("txs", []):
            try:
                tx = self._parse_transaction(tx_data["hash"], chain, tx_data)
                transactions.append(tx)
            except Exception as e:
                logger.warning(f"[Blockchain.com] Failed to parse transaction: {e}")
                continue

        logger.info(f"[Blockchain.com] ✓ Found {len(transactions)} transactions for {address[:16]}...")
        return transactions

    async def get_unspent_outputs(
        self, chain: str, address: str
    ) -> list[dict[str, Any]]:
        """
        Fetch unspent transaction outputs (UTXOs) for an address.
        
        Args:
            chain: Blockchain (must be bitcoin)
            address: Bitcoin address
            
        Returns:
            List of UTXOs
        """
        self._validate_chain(chain)
        
        logger.info(f"[Blockchain.com] Fetching UTXOs for address {address[:16]}...")
        
        data = await self._request(f"unspent", {"active": address})
        
        if not data or "unspent_outputs" not in data:
            logger.warning(f"[Blockchain.com] No UTXOs found for {address[:16]}...")
            return []

        utxos = data.get("unspent_outputs", [])
        logger.info(f"[Blockchain.com] ✓ Found {len(utxos)} UTXOs for {address[:16]}...")
        
        return utxos

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def get_internal_transactions(
        self, chain: str, tx_hash: str
    ) -> list[InternalTransaction]:
        """
        Get internal transactions for Bitcoin.
        
        Bitcoin doesn't have internal transactions like EVM chains.
        This method always returns an empty list for Bitcoin.
        """
        self._validate_chain(chain)
        logger.debug(f"[Blockchain.com] Bitcoin has no internal transactions - returning empty list")
        return []

    async def is_contract(self, chain: str, address: str) -> bool:
        """
        Check if an address is a smart contract.
        
        Bitcoin doesn't have smart contracts in the traditional sense.
        This method always returns False for Bitcoin.
        """
        self._validate_chain(chain)
        logger.debug(f"[Blockchain.com] Bitcoin has no smart contracts - returning False")
        return False

    def get_request_count(self) -> int:
        """Get total number of API requests made."""
        return self._request_count

    def reset_request_count(self) -> None:
        """Reset the request counter."""
        self._request_count = 0

    async def health_check(self) -> dict[str, Any]:
        """Check provider health status."""
        logger.info("[Blockchain.com] Performing health check...")
        try:
            data = await self._request("latestblock")
            
            logger.info(f"[Blockchain.com] ✓ Health check passed - Latest block: {data.get('height', 'unknown')}")
            return {
                "status": "healthy",
                "provider": self.name,
                "request_count": self._request_count,
                "api_responsive": True,
                "latest_block": data.get("height"),
            }
        except Exception as e:
            logger.error(f"[Blockchain.com] ✗ Health check failed - Error: {str(e)}")
            return {
                "status": "unhealthy",
                "provider": self.name,
                "request_count": self._request_count,
                "error": str(e),
                "api_responsive": False,
            }
