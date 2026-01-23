"""Blockchair API provider implementation."""

import asyncio
import logging
from datetime import datetime
from decimal import Decimal
from typing import Any

import httpx

from app.constants import SUPPORTED_CHAINS, ChainType, RiskTag
from app.core.exceptions import (
    APIRateLimitError,
    APITimeoutError,
    InvalidTransactionError,
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


class CircuitBreaker:
    """Circuit breaker pattern for API resilience.
    
    States:
    - CLOSED: Normal operation
    - OPEN: Too many failures, reject requests
    - HALF_OPEN: Testing if service recovered
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: type = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time: float | None = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def call(self, func):
        """Decorator to wrap function calls with circuit breaker."""
        async def wrapper(*args, **kwargs):
            if self.state == "OPEN":
                if self._should_attempt_reset():
                    self.state = "HALF_OPEN"
                else:
                    raise Exception("Circuit breaker is OPEN - API unavailable")
            
            try:
                result = await func(*args, **kwargs)
                self._on_success()
                return result
            except self.expected_exception as e:
                self._on_failure()
                raise e
        
        return wrapper
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to try recovery."""
        if not self.last_failure_time:
            return True
        return (asyncio.get_event_loop().time() - self.last_failure_time) >= self.recovery_timeout
    
    def _on_success(self):
        """Reset circuit breaker on successful call."""
        self.failure_count = 0
        self.state = "CLOSED"
    
    def _on_failure(self):
        """Record failure and potentially open circuit."""
        self.failure_count += 1
        self.last_failure_time = asyncio.get_event_loop().time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            logger.error(f"Circuit breaker OPEN after {self.failure_count} failures")


class BlockchairProvider(BlockchainProvider):
    """
    Blockchair API provider supporting 41+ blockchains.
    
    Features:
    - Rate limiting and retries
    - Circuit breaker for resilience
    - Response normalization across UTXO and Account-based chains
    - Health checking
    """

    def __init__(
        self,
        api_key: str = "",
        base_url: str = "https://api.blockchair.com",
        requests_per_second: float = 10.0,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        timeout: float = 30.0,
    ) -> None:
        """
        Initialize Blockchair provider.

        Args:
            api_key: Blockchair API key (optional but recommended).
            base_url: Base URL for Blockchair API.
            requests_per_second: Rate limit for requests.
            max_retries: Maximum number of retries on failure.
            retry_delay: Base delay between retries (exponential backoff).
            timeout: Request timeout in seconds.
        """
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._requests_per_second = requests_per_second
        self._max_retries = max_retries
        self._retry_delay = retry_delay
        self._timeout = timeout
        self._request_count = 0
        self._last_request_time: float = 0
        self._lock = asyncio.Lock()
        self._client: httpx.AsyncClient | None = None
        
        # Circuit breaker for API resilience
        self._circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60.0,
            expected_exception=Exception
        )

    @property
    def name(self) -> str:
        """Provider name identifier."""
        return "blockchair"

    @property
    def supported_chains(self) -> list[str]:
        """List of supported blockchain identifiers."""
        return list(SUPPORTED_CHAINS.keys())

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
                await asyncio.sleep(min_interval - elapsed)
            self._last_request_time = asyncio.get_event_loop().time()

    async def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Make an HTTP request with retry logic.

        Args:
            method: HTTP method.
            path: API path.
            params: Query parameters.

        Returns:
            JSON response data.

        Raises:
            APIRateLimitError: If rate limit is exceeded.
            APITimeoutError: If request times out.
        """
        await self._rate_limit()
        
        url = f"{self._base_url}/{path.lstrip('/')}"
        query_params = params or {}
        if self._api_key:
            query_params["key"] = self._api_key

        client = await self._get_client()
        last_error: Exception | None = None

        for attempt in range(self._max_retries):
            try:
                self._request_count += 1
                response = await client.request(method, url, params=query_params)

                if response.status_code == 429:
                    retry_after = float(response.headers.get("Retry-After", self._retry_delay))
                    if attempt < self._max_retries - 1:
                        await asyncio.sleep(retry_after * (2**attempt))
                        continue
                    raise APIRateLimitError("blockchair", retry_after)

                if response.status_code == 404:
                    return {"data": None, "context": {}}

                response.raise_for_status()
                # Success - reset circuit breaker
                self._circuit_breaker._on_success()
                return response.json()

            except httpx.TimeoutException as e:
                last_error = e
                self._circuit_breaker._on_failure()
                if attempt < self._max_retries - 1:
                    await asyncio.sleep(self._retry_delay * (2**attempt))
                    continue
                raise APITimeoutError("blockchair", self._timeout) from e

            except httpx.HTTPStatusError as e:
                last_error = e
                if e.response.status_code >= 500:
                    self._circuit_breaker._on_failure()
                    if attempt < self._max_retries - 1:
                        await asyncio.sleep(self._retry_delay * (2**attempt))
                        continue
                raise

        if last_error:
            raise last_error
        return {}

    def _get_chain_config(self, chain: str) -> Any:
        """Get chain configuration or raise error."""
        chain_lower = chain.lower()
        if chain_lower not in SUPPORTED_CHAINS:
            raise UnsupportedChainError(chain)
        return SUPPORTED_CHAINS[chain_lower]

    async def get_transaction(self, chain: str, tx_hash: str) -> Transaction:
        """Fetch transaction details from Blockchair."""
        config = self._get_chain_config(chain)
        
        path = f"{config.slug}/dashboards/transaction/{tx_hash}"
        data = await self._request("GET", path)

        tx_data = data.get("data", {})
        if not tx_data or tx_hash.lower() not in [k.lower() for k in tx_data.keys()]:
            raise TransactionNotFoundError(tx_hash, chain)

        raw_tx = tx_data.get(tx_hash) or tx_data.get(tx_hash.lower()) or {}
        tx_info = raw_tx.get("transaction", {})

        if config.chain_type == ChainType.UTXO:
            return self._parse_utxo_transaction(tx_hash, chain, config, raw_tx, tx_info)
        else:
            return self._parse_account_transaction(tx_hash, chain, config, raw_tx, tx_info)

    def _parse_utxo_transaction(
        self,
        tx_hash: str,
        chain: str,
        config: Any,
        raw_tx: dict[str, Any],
        tx_info: dict[str, Any],
    ) -> Transaction:
        """Parse UTXO-based transaction."""
        inputs = []
        for inp in raw_tx.get("inputs", []):
            inputs.append(
                TransactionInput(
                    address=inp.get("recipient", ""),
                    value=Decimal(str(inp.get("value", 0))) / Decimal("1e8"),
                    tx_hash=inp.get("spending_transaction_hash"),
                    output_index=inp.get("spending_index"),
                )
            )

        outputs = []
        for idx, out in enumerate(raw_tx.get("outputs", [])):
            outputs.append(
                TransactionOutput(
                    address=out.get("recipient", ""),
                    value=Decimal(str(out.get("value", 0))) / Decimal("1e8"),
                    output_index=idx,
                )
            )

        timestamp = None
        if tx_info.get("time"):
            try:
                timestamp = datetime.fromisoformat(tx_info["time"].replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                pass

        return Transaction(
            tx_hash=tx_hash,
            chain=chain,
            chain_type=ChainType.UTXO,
            block_height=tx_info.get("block_id"),
            timestamp=timestamp,
            fee=Decimal(str(tx_info.get("fee", 0))) / Decimal("1e8"),
            size=tx_info.get("size"),
            inputs=inputs,
            outputs=outputs,
            raw_data=raw_tx,
        )

    def _parse_account_transaction(
        self,
        tx_hash: str,
        chain: str,
        config: Any,
        raw_tx: dict[str, Any],
        tx_info: dict[str, Any],
    ) -> Transaction:
        """Parse Account-based transaction."""
        timestamp = None
        if tx_info.get("time"):
            try:
                timestamp = datetime.fromisoformat(tx_info["time"].replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                pass

        # Parse internal transactions if available
        internal_txs = []
        for idx, itx in enumerate(raw_tx.get("calls", [])):
            internal_txs.append(
                InternalTransaction(
                    from_address=itx.get("sender", ""),
                    to_address=itx.get("recipient", ""),
                    value=Decimal(str(itx.get("value", 0))) / Decimal("1e18"),
                    call_type=itx.get("call_type", "call"),
                    trace_index=idx,
                )
            )

        # Determine if it's a contract call
        is_contract = bool(tx_info.get("input_hex") and tx_info.get("input_hex") != "0x")

        value_divisor = Decimal("1e18")
        if chain in ("tron",):
            value_divisor = Decimal("1e6")

        return Transaction(
            tx_hash=tx_hash,
            chain=chain,
            chain_type=ChainType.ACCOUNT,
            block_height=tx_info.get("block_id"),
            timestamp=timestamp,
            fee=Decimal(str(tx_info.get("fee", 0))) / value_divisor,
            sender=tx_info.get("sender"),
            recipient=tx_info.get("recipient"),
            value=Decimal(str(tx_info.get("value", 0))) / value_divisor,
            gas_used=tx_info.get("gas_used"),
            gas_price=Decimal(str(tx_info.get("gas_price", 0))) / Decimal("1e9")
            if tx_info.get("gas_price")
            else None,
            nonce=tx_info.get("nonce"),
            is_contract_call=is_contract,
            internal_transactions=internal_txs,
            raw_data=raw_tx,
        )

    async def get_transaction_inputs(
        self, chain: str, tx_hash: str
    ) -> list[tuple[str, str]]:
        """Get input transactions for UTXO chains."""
        config = self._get_chain_config(chain)
        
        if config.chain_type != ChainType.UTXO:
            return []

        tx = await self.get_transaction(chain, tx_hash)
        result = []
        for inp in tx.inputs:
            if inp.address and inp.tx_hash:
                result.append((inp.address, inp.tx_hash))
        return result

    async def get_internal_transactions(
        self, chain: str, tx_hash: str
    ) -> list[InternalTransaction]:
        """Get internal transactions for EVM chains."""
        config = self._get_chain_config(chain)
        
        if not config.has_internal_txs:
            return []

        tx = await self.get_transaction(chain, tx_hash)
        return tx.internal_transactions

    async def get_address_metadata(
        self, chain: str, address: str
    ) -> AddressMetadata:
        """Fetch metadata for a blockchain address."""
        config = self._get_chain_config(chain)
        
        path = f"{config.slug}/dashboards/address/{address}"
        data = await self._request("GET", path)

        addr_data = data.get("data", {})
        if not addr_data:
            return AddressMetadata(address=address, chain=chain)

        addr_info = addr_data.get(address, {}) or addr_data.get(address.lower(), {})
        if not addr_info:
            first_key = next(iter(addr_data.keys()), None)
            if first_key:
                addr_info = addr_data[first_key]

        address_obj = addr_info.get("address", {})
        
        # Parse tags from Blockchair context
        tags = self._parse_address_tags(addr_info)
        labels = self._parse_address_labels(addr_info)

        # Parse balance based on chain type
        balance = Decimal("0")
        if config.chain_type == ChainType.UTXO:
            balance = Decimal(str(address_obj.get("balance", 0))) / Decimal("1e8")
        else:
            divisor = Decimal("1e18")
            if chain in ("tron",):
                divisor = Decimal("1e6")
            balance = Decimal(str(address_obj.get("balance", 0))) / divisor

        # Parse timestamps
        first_seen = None
        last_seen = None
        if address_obj.get("first_seen_receiving"):
            try:
                first_seen = datetime.fromisoformat(
                    address_obj["first_seen_receiving"].replace("Z", "+00:00")
                )
            except (ValueError, AttributeError):
                pass
        if address_obj.get("last_seen_receiving"):
            try:
                last_seen = datetime.fromisoformat(
                    address_obj["last_seen_receiving"].replace("Z", "+00:00")
                )
            except (ValueError, AttributeError):
                pass

        return AddressMetadata(
            address=address,
            chain=chain,
            tags=tags,
            labels=labels,
            balance=balance,
            tx_count=address_obj.get("transaction_count", 0),
            first_seen=first_seen,
            last_seen=last_seen,
            is_contract=address_obj.get("type") == "contract",
            context=addr_info,
        )

    def _parse_address_tags(self, addr_info: dict[str, Any]) -> list[RiskTag]:
        """Parse risk tags from address info."""
        tags: list[RiskTag] = []
        
        # Check for various tag sources in Blockchair response
        address_obj = addr_info.get("address", {})
        
        # Check script type for contract detection
        if address_obj.get("type") == "contract":
            pass  # Not a risk tag itself

        # Check context for labels
        context = addr_info.get("context", {})
        
        # Check for known entity classifications
        entity_type = address_obj.get("type", "").lower()
        
        tag_mapping = {
            "mixer": RiskTag.MIXER,
            "mixing": RiskTag.MIXER,
            "tumbler": RiskTag.MIXER,
            "darknet": RiskTag.DARKNET,
            "dark": RiskTag.DARKNET,
            "hack": RiskTag.HACK,
            "hacker": RiskTag.HACK,
            "stolen": RiskTag.HACK,
            "gambling": RiskTag.GAMBLING,
            "casino": RiskTag.GAMBLING,
            "exchange": RiskTag.EXCHANGE,
            "whale": RiskTag.WHALE,
            "scam": RiskTag.SCAM,
            "phishing": RiskTag.SCAM,
            "sanctioned": RiskTag.SANCTIONED,
            "ofac": RiskTag.SANCTIONED,
            "ransomware": RiskTag.RANSOMWARE,
            "ransom": RiskTag.RANSOMWARE,
            "terrorist": RiskTag.TERRORIST_FINANCING,
            "terrorism": RiskTag.TERRORIST_FINANCING,
        }

        # Check all string fields for keywords
        for key, value in addr_info.items():
            if isinstance(value, str):
                value_lower = value.lower()
                for keyword, tag in tag_mapping.items():
                    if keyword in value_lower and tag not in tags:
                        tags.append(tag)

        # Check nested structures
        for key in ["labels", "tags", "context"]:
            nested = addr_info.get(key, [])
            if isinstance(nested, list):
                for item in nested:
                    if isinstance(item, str):
                        item_lower = item.lower()
                        for keyword, tag in tag_mapping.items():
                            if keyword in item_lower and tag not in tags:
                                tags.append(tag)
            elif isinstance(nested, dict):
                for v in nested.values():
                    if isinstance(v, str):
                        v_lower = v.lower()
                        for keyword, tag in tag_mapping.items():
                            if keyword in v_lower and tag not in tags:
                                tags.append(tag)

        return tags

    def _parse_address_labels(self, addr_info: dict[str, Any]) -> list[str]:
        """Parse human-readable labels from address info."""
        labels: list[str] = []
        
        # Check various label sources
        for key in ["labels", "name", "entity", "owner"]:
            value = addr_info.get(key)
            if isinstance(value, str) and value:
                labels.append(value)
            elif isinstance(value, list):
                labels.extend([v for v in value if isinstance(v, str) and v])

        address_obj = addr_info.get("address", {})
        for key in ["label", "name", "entity"]:
            value = address_obj.get(key)
            if isinstance(value, str) and value and value not in labels:
                labels.append(value)

        return labels

    async def is_contract(self, chain: str, address: str) -> bool:
        """Check if an address is a smart contract."""
        config = self._get_chain_config(chain)
        
        if config.chain_type == ChainType.UTXO:
            return False

        metadata = await self.get_address_metadata(chain, address)
        return metadata.is_contract

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    def get_request_count(self) -> int:
        """Get total number of API requests made."""
        return self._request_count

    def reset_request_count(self) -> None:
        """Reset the request counter."""
        self._request_count = 0

    async def health_check(self) -> dict[str, Any]:
        """Check provider health status.
        
        Returns:
            Dictionary with health status information
        """
        try:
            # Try a simple request to check API availability
            response = await self._request("GET", "stats")
            
            return {
                "status": "healthy",
                "provider": self.name,
                "circuit_breaker": self._circuit_breaker.state,
                "request_count": self._request_count,
                "api_responsive": True,
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "provider": self.name,
                "circuit_breaker": self._circuit_breaker.state,
                "request_count": self._request_count,
                "error": str(e),
                "api_responsive": False,
            }
