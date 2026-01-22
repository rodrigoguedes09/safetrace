"""Transaction tracing service implementing BFS algorithm."""

import asyncio
import logging
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.constants import (
    CACHEABLE_DEFINITIVE_TAGS,
    SUPPORTED_CHAINS,
    ChainType,
    RiskTag,
)
from app.core.cache import CacheBackend
from app.core.exceptions import (
    InvalidTransactionError,
    SafeTraceError,
    TransactionNotFoundError,
)
from app.core.provider import BlockchainProvider
from app.models.blockchain import AddressMetadata, Transaction
from app.models.risk import FlaggedEntity, RiskReport, RiskScore
from app.services.risk_scorer import RiskScorerService

logger = logging.getLogger(__name__)


@dataclass
class TraceNode:
    """Node in the transaction trace graph."""

    tx_hash: str
    address: str
    depth: int
    parent_tx: str | None = None


@dataclass
class TraceState:
    """State maintained during transaction tracing."""

    visited_addresses: set[str] = field(default_factory=set)
    visited_transactions: set[str] = field(default_factory=set)
    flagged_entities: list[FlaggedEntity] = field(default_factory=list)
    address_metadata_cache: dict[str, AddressMetadata] = field(default_factory=dict)
    api_calls: int = 0


class TransactionTracerService:
    """
    Service for tracing transaction risk using BFS algorithm.
    
    Traces the origin of funds up to N hops, identifying proximity
    to high-risk entities and computing a quantitative risk score.
    """

    def __init__(
        self,
        provider: BlockchainProvider,
        cache: CacheBackend,
        risk_scorer: RiskScorerService,
        max_concurrent_requests: int = 5,
    ) -> None:
        """
        Initialize the tracer service.

        Args:
            provider: Blockchain data provider.
            cache: Cache backend for optimization.
            risk_scorer: Risk scoring service.
            max_concurrent_requests: Maximum concurrent API requests.
        """
        self._provider = provider
        self._cache = cache
        self._risk_scorer = risk_scorer
        self._semaphore = asyncio.Semaphore(max_concurrent_requests)

    async def trace_transaction_risk(
        self,
        tx_hash: str,
        chain: str = "ethereum",
        depth: int = 3,
    ) -> RiskReport:
        """
        Trace transaction risk using BFS algorithm.

        Args:
            tx_hash: Transaction hash to trace.
            chain: Blockchain network.
            depth: Maximum number of hops to trace.

        Returns:
            RiskReport with complete analysis.

        Raises:
            TransactionNotFoundError: If transaction doesn't exist.
            UnsupportedChainError: If chain is not supported.
        """
        chain = chain.lower()
        
        # Check cache for existing result
        cache_key = self._cache.risk_key(chain, tx_hash, depth)
        cached_result = await self._cache.get(cache_key)
        if cached_result:
            logger.info(f"Cache hit for risk report: {tx_hash}")
            return RiskReport.model_validate(cached_result)

        state = TraceState()
        chain_config = SUPPORTED_CHAINS.get(chain)
        
        if not chain_config:
            raise InvalidTransactionError(tx_hash, chain)

        # Fetch initial transaction
        try:
            initial_tx = await self._fetch_transaction_cached(chain, tx_hash, state)
        except TransactionNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to fetch transaction {tx_hash}: {e}")
            raise InvalidTransactionError(tx_hash, chain) from e

        # Initialize BFS queue
        queue: deque[TraceNode] = deque()
        source_addresses = initial_tx.get_source_addresses()

        for address in source_addresses:
            if address:
                queue.append(
                    TraceNode(
                        tx_hash=tx_hash,
                        address=address,
                        depth=0,
                        parent_tx=None,
                    )
                )

        # Execute BFS
        await self._bfs_trace(chain, chain_config, queue, depth, state)

        # Calculate risk score
        risk_score = self._risk_scorer.calculate_score(
            state.flagged_entities,
            state.address_metadata_cache,
            depth,
        )

        # Build report
        report = RiskReport(
            tx_hash=tx_hash,
            chain=chain,
            analyzed_at=datetime.utcnow(),
            trace_depth=depth,
            total_addresses_analyzed=len(state.visited_addresses),
            total_transactions_analyzed=len(state.visited_transactions),
            risk_score=risk_score,
            flagged_entities=sorted(
                state.flagged_entities,
                key=lambda e: (e.distance, -e.contribution_score),
            ),
            api_calls_used=state.api_calls,
        )

        # Cache the result
        await self._cache.set(cache_key, report.model_dump(), ttl=86400)

        return report

    async def _bfs_trace(
        self,
        chain: str,
        chain_config: Any,
        queue: deque[TraceNode],
        max_depth: int,
        state: TraceState,
    ) -> None:
        """Execute BFS traversal for transaction tracing."""
        while queue:
            # Process nodes at current depth in parallel
            current_batch: list[TraceNode] = []
            current_depth = queue[0].depth if queue else 0

            while queue and queue[0].depth == current_depth:
                node = queue.popleft()
                
                # Skip if already visited
                address_key = f"{chain}:{node.address.lower()}"
                if address_key in state.visited_addresses:
                    continue
                    
                state.visited_addresses.add(address_key)
                current_batch.append(node)

            if not current_batch:
                continue

            # Process batch concurrently
            tasks = [
                self._process_trace_node(chain, chain_config, node, max_depth, state)
                for node in current_batch
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Add new nodes to queue
            for result in results:
                if isinstance(result, Exception):
                    logger.warning(f"Error processing node: {result}")
                    continue
                if isinstance(result, list):
                    for new_node in result:
                        if new_node.depth <= max_depth:
                            queue.append(new_node)

    async def _process_trace_node(
        self,
        chain: str,
        chain_config: Any,
        node: TraceNode,
        max_depth: int,
        state: TraceState,
    ) -> list[TraceNode]:
        """Process a single trace node."""
        new_nodes: list[TraceNode] = []

        async with self._semaphore:
            # Fetch address metadata
            metadata = await self._fetch_address_metadata_cached(
                chain, node.address, state
            )

            # Check if address should be flagged
            if metadata.tags:
                contribution = self._risk_scorer.calculate_entity_contribution(
                    metadata.tags, node.depth
                )
                flagged = FlaggedEntity(
                    address=node.address,
                    chain=chain,
                    tags=metadata.tags,
                    distance=node.depth,
                    tx_hash=node.tx_hash,
                    contribution_score=contribution,
                )
                state.flagged_entities.append(flagged)

                # Skip further tracing for definitive tags
                if set(metadata.tags) & CACHEABLE_DEFINITIVE_TAGS:
                    return new_nodes

            # Stop if max depth reached
            if node.depth >= max_depth:
                return new_nodes

            # Trace upstream transactions
            if chain_config.chain_type == ChainType.UTXO:
                new_nodes.extend(
                    await self._trace_utxo_inputs(chain, node, state)
                )
            else:
                new_nodes.extend(
                    await self._trace_account_inputs(chain, chain_config, node, state)
                )

        return new_nodes

    async def _trace_utxo_inputs(
        self,
        chain: str,
        node: TraceNode,
        state: TraceState,
    ) -> list[TraceNode]:
        """Trace inputs for UTXO-based chains."""
        new_nodes: list[TraceNode] = []

        try:
            inputs = await self._provider.get_transaction_inputs(chain, node.tx_hash)
            
            for address, prev_tx_hash in inputs:
                tx_key = f"{chain}:{prev_tx_hash.lower()}"
                if tx_key in state.visited_transactions:
                    continue
                    
                state.visited_transactions.add(tx_key)
                new_nodes.append(
                    TraceNode(
                        tx_hash=prev_tx_hash,
                        address=address,
                        depth=node.depth + 1,
                        parent_tx=node.tx_hash,
                    )
                )
        except Exception as e:
            logger.warning(f"Failed to trace UTXO inputs for {node.tx_hash}: {e}")

        return new_nodes

    async def _trace_account_inputs(
        self,
        chain: str,
        chain_config: Any,
        node: TraceNode,
        state: TraceState,
    ) -> list[TraceNode]:
        """Trace inputs for Account-based chains."""
        new_nodes: list[TraceNode] = []

        try:
            tx = await self._fetch_transaction_cached(chain, node.tx_hash, state)
            
            # Trace sender
            if tx.sender:
                sender_key = f"{chain}:{tx.sender.lower()}"
                if sender_key not in state.visited_addresses:
                    new_nodes.append(
                        TraceNode(
                            tx_hash=node.tx_hash,
                            address=tx.sender,
                            depth=node.depth + 1,
                            parent_tx=node.tx_hash,
                        )
                    )

            # Trace internal transactions if contract
            if tx.is_contract_call and chain_config.has_internal_txs:
                for itx in tx.internal_transactions:
                    if itx.from_address:
                        from_key = f"{chain}:{itx.from_address.lower()}"
                        if from_key not in state.visited_addresses:
                            new_nodes.append(
                                TraceNode(
                                    tx_hash=node.tx_hash,
                                    address=itx.from_address,
                                    depth=node.depth + 1,
                                    parent_tx=node.tx_hash,
                                )
                            )
        except Exception as e:
            logger.warning(f"Failed to trace account inputs for {node.tx_hash}: {e}")

        return new_nodes

    async def _fetch_transaction_cached(
        self,
        chain: str,
        tx_hash: str,
        state: TraceState,
    ) -> Transaction:
        """Fetch transaction with caching."""
        cache_key = self._cache.transaction_key(chain, tx_hash)
        
        # Check cache
        cached = await self._cache.get(cache_key)
        if cached:
            return Transaction.model_validate(cached)

        # Fetch from provider
        state.api_calls += 1
        tx = await self._provider.get_transaction(chain, tx_hash)
        
        # Cache result
        await self._cache.set(cache_key, tx.model_dump(), ttl=86400)
        
        return tx

    async def _fetch_address_metadata_cached(
        self,
        chain: str,
        address: str,
        state: TraceState,
    ) -> AddressMetadata:
        """Fetch address metadata with caching."""
        address_lower = address.lower()
        cache_key = self._cache.address_key(chain, address)

        # Check in-memory cache first
        if address_lower in state.address_metadata_cache:
            return state.address_metadata_cache[address_lower]

        # Check persistent cache
        cached = await self._cache.get(cache_key)
        if cached:
            metadata = AddressMetadata.model_validate(cached)
            state.address_metadata_cache[address_lower] = metadata
            return metadata

        # Fetch from provider
        state.api_calls += 1
        try:
            metadata = await self._provider.get_address_metadata(chain, address)
        except Exception as e:
            logger.warning(f"Failed to fetch metadata for {address}: {e}")
            metadata = AddressMetadata(address=address, chain=chain)

        # Cache results
        state.address_metadata_cache[address_lower] = metadata
        await self._cache.set(cache_key, metadata.model_dump(), ttl=86400)

        return metadata
