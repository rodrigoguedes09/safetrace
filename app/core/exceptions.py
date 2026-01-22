"""Custom exceptions for SafeTrace."""


class SafeTraceError(Exception):
    """Base exception for all SafeTrace errors."""

    def __init__(self, message: str, code: str | None = None) -> None:
        self.message = message
        self.code = code or "SAFETRACE_ERROR"
        super().__init__(self.message)


class BlockchainError(SafeTraceError):
    """Base exception for blockchain-related errors."""

    def __init__(self, message: str, chain: str | None = None) -> None:
        self.chain = chain
        super().__init__(message, "BLOCKCHAIN_ERROR")


class UnsupportedChainError(BlockchainError):
    """Raised when an unsupported blockchain is requested."""

    def __init__(self, chain: str) -> None:
        super().__init__(f"Unsupported blockchain: {chain}", chain)
        self.code = "UNSUPPORTED_CHAIN"


class InvalidTransactionError(BlockchainError):
    """Raised when a transaction hash is invalid or not found."""

    def __init__(self, tx_hash: str, chain: str | None = None) -> None:
        self.tx_hash = tx_hash
        super().__init__(f"Invalid or not found transaction: {tx_hash}", chain)
        self.code = "INVALID_TRANSACTION"


class APIRateLimitError(SafeTraceError):
    """Raised when API rate limit is exceeded."""

    def __init__(
        self, provider: str, retry_after: float | None = None
    ) -> None:
        self.provider = provider
        self.retry_after = retry_after
        message = f"Rate limit exceeded for {provider}"
        if retry_after:
            message += f". Retry after {retry_after}s"
        super().__init__(message, "RATE_LIMIT_EXCEEDED")


class CacheError(SafeTraceError):
    """Raised when cache operations fail."""

    def __init__(self, message: str, operation: str | None = None) -> None:
        self.operation = operation
        super().__init__(message, "CACHE_ERROR")


class APITimeoutError(SafeTraceError):
    """Raised when API request times out."""

    def __init__(self, provider: str, timeout: float) -> None:
        self.provider = provider
        self.timeout = timeout
        super().__init__(f"API timeout for {provider} after {timeout}s", "API_TIMEOUT")


class TransactionNotFoundError(BlockchainError):
    """Raised when a transaction is not found on the blockchain."""

    def __init__(self, tx_hash: str, chain: str) -> None:
        self.tx_hash = tx_hash
        super().__init__(f"Transaction {tx_hash} not found on {chain}", chain)
        self.code = "TRANSACTION_NOT_FOUND"


class AddressNotFoundError(BlockchainError):
    """Raised when an address is not found or has no activity."""

    def __init__(self, address: str, chain: str) -> None:
        self.address = address
        super().__init__(f"Address {address} not found on {chain}", chain)
        self.code = "ADDRESS_NOT_FOUND"
