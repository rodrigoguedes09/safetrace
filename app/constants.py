"""Application constants and chain configurations."""

from enum import Enum
from typing import NamedTuple


class ChainType(str, Enum):
    """Blockchain type classification."""

    UTXO = "utxo"
    ACCOUNT = "account"


class ChainConfig(NamedTuple):
    """Configuration for a blockchain network."""

    slug: str
    name: str
    chain_type: ChainType
    symbol: str
    has_internal_txs: bool = False


# Supported blockchains with their configurations
SUPPORTED_CHAINS: dict[str, ChainConfig] = {
    # UTXO-based chains
    "bitcoin": ChainConfig("bitcoin", "Bitcoin", ChainType.UTXO, "BTC"),
    "bitcoin-cash": ChainConfig("bitcoin-cash", "Bitcoin Cash", ChainType.UTXO, "BCH"),
    "litecoin": ChainConfig("litecoin", "Litecoin", ChainType.UTXO, "LTC"),
    "dogecoin": ChainConfig("dogecoin", "Dogecoin", ChainType.UTXO, "DOGE"),
    "dash": ChainConfig("dash", "Dash", ChainType.UTXO, "DASH"),
    "zcash": ChainConfig("zcash", "Zcash", ChainType.UTXO, "ZEC"),
    "bitcoin-sv": ChainConfig("bitcoin-sv", "Bitcoin SV", ChainType.UTXO, "BSV"),
    "groestlcoin": ChainConfig("groestlcoin", "Groestlcoin", ChainType.UTXO, "GRS"),
    "ecash": ChainConfig("ecash", "eCash", ChainType.UTXO, "XEC"),
    # Account-based chains (EVM)
    "ethereum": ChainConfig("ethereum", "Ethereum", ChainType.ACCOUNT, "ETH", True),
    "binance-smart-chain": ChainConfig(
        "binance-smart-chain", "BNB Smart Chain", ChainType.ACCOUNT, "BNB", True
    ),
    "polygon": ChainConfig("polygon", "Polygon", ChainType.ACCOUNT, "MATIC", True),
    "arbitrum": ChainConfig("arbitrum", "Arbitrum", ChainType.ACCOUNT, "ETH", True),
    "optimism": ChainConfig("optimism", "Optimism", ChainType.ACCOUNT, "ETH", True),
    "avalanche": ChainConfig("avalanche", "Avalanche", ChainType.ACCOUNT, "AVAX", True),
    "fantom": ChainConfig("fantom", "Fantom", ChainType.ACCOUNT, "FTM", True),
    "gnosis": ChainConfig("gnosis", "Gnosis", ChainType.ACCOUNT, "xDAI", True),
    "base": ChainConfig("base", "Base", ChainType.ACCOUNT, "ETH", True),
    "moonbeam": ChainConfig("moonbeam", "Moonbeam", ChainType.ACCOUNT, "GLMR", True),
    "moonriver": ChainConfig("moonriver", "Moonriver", ChainType.ACCOUNT, "MOVR", True),
    "cronos": ChainConfig("cronos", "Cronos", ChainType.ACCOUNT, "CRO", True),
    "aurora": ChainConfig("aurora", "Aurora", ChainType.ACCOUNT, "ETH", True),
    "celo": ChainConfig("celo", "Celo", ChainType.ACCOUNT, "CELO", True),
    "klaytn": ChainConfig("klaytn", "Klaytn", ChainType.ACCOUNT, "KLAY", True),
    "harmony": ChainConfig("harmony", "Harmony", ChainType.ACCOUNT, "ONE", True),
    "boba": ChainConfig("boba", "Boba", ChainType.ACCOUNT, "ETH", True),
    "metis": ChainConfig("metis", "Metis", ChainType.ACCOUNT, "METIS", True),
    "zksync": ChainConfig("zksync", "zkSync Era", ChainType.ACCOUNT, "ETH", True),
    "scroll": ChainConfig("scroll", "Scroll", ChainType.ACCOUNT, "ETH", True),
    "linea": ChainConfig("linea", "Linea", ChainType.ACCOUNT, "ETH", True),
    "mantle": ChainConfig("mantle", "Mantle", ChainType.ACCOUNT, "MNT", True),
    "manta": ChainConfig("manta", "Manta Pacific", ChainType.ACCOUNT, "ETH", True),
    "blast": ChainConfig("blast", "Blast", ChainType.ACCOUNT, "ETH", True),
    # Non-EVM account-based
    "cardano": ChainConfig("cardano", "Cardano", ChainType.ACCOUNT, "ADA"),
    "solana": ChainConfig("solana", "Solana", ChainType.ACCOUNT, "SOL"),
    "tron": ChainConfig("tron", "Tron", ChainType.ACCOUNT, "TRX"),
    "ripple": ChainConfig("ripple", "Ripple", ChainType.ACCOUNT, "XRP"),
    "stellar": ChainConfig("stellar", "Stellar", ChainType.ACCOUNT, "XLM"),
    "tezos": ChainConfig("tezos", "Tezos", ChainType.ACCOUNT, "XTZ"),
    "cosmos": ChainConfig("cosmos", "Cosmos", ChainType.ACCOUNT, "ATOM"),
    "polkadot": ChainConfig("polkadot", "Polkadot", ChainType.ACCOUNT, "DOT"),
    "kusama": ChainConfig("kusama", "Kusama", ChainType.ACCOUNT, "KSM"),
}


class RiskTag(str, Enum):
    """Known risk tags for address classification."""

    MIXER = "mixer"
    HACK = "hack"
    DARKNET = "darknet"
    GAMBLING = "gambling"
    EXCHANGE = "exchange"
    WHALE = "whale"
    SCAM = "scam"
    SANCTIONED = "sanctioned"
    RANSOMWARE = "ransomware"
    TERRORIST_FINANCING = "terrorist_financing"
    UNKNOWN = "unknown"


# Risk tag weights for scoring
RISK_TAG_WEIGHTS: dict[RiskTag, float] = {
    RiskTag.MIXER: 1.0,
    RiskTag.DARKNET: 1.0,
    RiskTag.HACK: 0.9,
    RiskTag.SANCTIONED: 1.0,
    RiskTag.RANSOMWARE: 1.0,
    RiskTag.TERRORIST_FINANCING: 1.0,
    RiskTag.SCAM: 0.8,
    RiskTag.GAMBLING: 0.4,
    RiskTag.EXCHANGE: -0.2,
    RiskTag.WHALE: 0.0,
    RiskTag.UNKNOWN: 0.0,
}

# Tags that should skip re-querying
CACHEABLE_DEFINITIVE_TAGS: set[RiskTag] = {
    RiskTag.EXCHANGE,
    RiskTag.WHALE,
    RiskTag.HACK,
    RiskTag.MIXER,
    RiskTag.DARKNET,
    RiskTag.SANCTIONED,
}


class RiskLevel(str, Enum):
    """Risk level classification."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


# Risk level thresholds
RISK_THRESHOLDS: dict[RiskLevel, tuple[int, int]] = {
    RiskLevel.LOW: (0, 30),
    RiskLevel.MEDIUM: (31, 70),
    RiskLevel.HIGH: (71, 100),
}
