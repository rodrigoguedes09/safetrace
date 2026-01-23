# Blockchain Data Providers

SafeTrace uses multiple blockchain data providers to ensure reliable data access and optimal coverage across different blockchains.

## Providers Overview

| Provider | Chains | Free Tier | Best For |
|----------|--------|-----------|----------|
| **Blockchain.com** | Bitcoin | ✅ Unlimited | Bitcoin transaction history, UTXOs |
| **Blockchair** | 40+ chains | ⚠️ Limited | Multi-chain support, Ethereum, etc. |

## Provider Selection Logic

SafeTrace automatically selects the best provider for each blockchain:

```
Bitcoin → Blockchain.com (free, full transaction history)
Ethereum → Blockchair (EVM support, internal transactions)
Other chains → Blockchair (broad coverage)
```

## Blockchain.com API (Bitcoin)

**Documentation:** https://www.blockchain.com/explorer/api/blockchain_api

### Features
- ✅ **Free API** - No API key required
- ✅ **Full transaction history** per address
- ✅ **UTXO data** - Complete unspent outputs
- ✅ **Address metadata** - Balance, TX count, timestamps

### Endpoints Used
| Endpoint | Purpose |
|----------|---------|
| `/rawtx/{hash}` | Get transaction details |
| `/rawaddr/{address}` | Get address info + transactions |
| `/unspent?active={address}` | Get UTXOs |
| `/latestblock` | Health check |

### Rate Limits
- ~5 requests/second recommended
- No explicit quota
- CORS enabled with `?cors=true`

## Blockchair API

**Documentation:** https://blockchair.com/api/docs

### Features
- ✅ **40+ blockchain support** including Bitcoin, Ethereum, BSC, etc.
- ✅ **Internal transactions** for EVM chains
- ✅ **Contract detection**
- ⚠️ **Rate limits** on free tier (may require API key for production)

### Endpoints Used
| Endpoint | Purpose |
|----------|---------|
| `/{chain}/dashboards/transaction/{hash}` | Transaction details |
| `/{chain}/dashboards/address/{address}` | Address metadata |
| `/{chain}/raw/transaction/{hash}` | Raw transaction data |
| `/stats` | Health check |

### Rate Limits (Free Tier)
- 30 requests/minute without API key
- 10,000 requests/day with free API key
- Paid plans start at $49/month

## Configuration

### Environment Variables

```bash
# Blockchain.com (Bitcoin - FREE)
BLOCKCHAIN_COM_ENABLED=true
BLOCKCHAIN_COM_BASE_URL=https://blockchain.info
BLOCKCHAIN_COM_REQUESTS_PER_SECOND=5.0

# Blockchair (Multi-chain)
BLOCKCHAIR_API_KEY=your-api-key-here
BLOCKCHAIR_BASE_URL=https://api.blockchair.com
BLOCKCHAIR_REQUESTS_PER_SECOND=10.0
BLOCKCHAIR_MAX_RETRIES=3
```

### Default Settings

Without any configuration, SafeTrace will:
1. Use Blockchain.com for Bitcoin (free, no limits)
2. Use Blockchair without API key (limited requests)

### Recommended Production Setup

```bash
# Enable both providers
BLOCKCHAIN_COM_ENABLED=true
BLOCKCHAIR_API_KEY=your-paid-api-key
```

## Provider Fallback

If the primary provider fails, SafeTrace automatically falls back:

```
Bitcoin: blockchain.com → blockchair
Ethereum: blockchair only (no fallback yet)
```

Future improvements may include Etherscan as Ethereum fallback.

## Health Check Endpoint

Check provider status via API:

```bash
GET /api/v1/providers/health
```

Response:
```json
{
  "status": "healthy",
  "provider": "multi_provider",
  "total_request_count": 42,
  "providers": {
    "blockchair": {
      "status": "healthy",
      "request_count": 30,
      "circuit_breaker_state": "CLOSED"
    },
    "blockchain_com": {
      "status": "healthy",
      "request_count": 12,
      "latest_block": 933576
    }
  }
}
```

## Adding New Providers

To add a new provider (e.g., Etherscan):

1. Create provider class in `app/providers/`
2. Implement `BlockchainProvider` abstract interface
3. Update `MultiProviderManager` with fallback logic
4. Add configuration to `app/config.py`

See `app/providers/blockchain_com.py` as a reference implementation.
