# SafeTrace - Blockchain Compliance Tool (KYT)

A production-ready blockchain compliance tool for Know Your Transaction (KYT) analysis. Traces transaction risk across 41+ blockchains by analyzing fund origins and identifying proximity to high-risk entities.

## 🚀 Quick Deploy to Railway

**Ready to deploy?** This project is pre-configured for Railway:

```bash
# Option 1: Use the deploy script (Windows)
deploy.bat

# Option 2: Manual deployment
git add .
git commit -m "Railway deployment"
git push origin main
```

Then:
1. Go to [railway.app](https://railway.app)
2. Deploy from your GitHub repo
3. Add env vars: `BLOCKCHAIR_API_KEY` and `CACHE_BACKEND=memory`
4. Done! 🎉

**📖 Detailed Guide**: See [RAILWAY_DEPLOY.md](RAILWAY_DEPLOY.md)

---

## Features

- **Multi-Chain Support**: 41+ blockchains including Bitcoin, Ethereum, BSC, Polygon, and more
- **BFS Transaction Tracing**: Trace fund origins up to N hops
- **Risk Scoring**: Quantitative risk assessment (0-100) based on entity proximity
- **Entity Detection**: Identifies Mixers, Hacks, Darknet, Gambling, and more
- **PDF Compliance Certificates**: Professional-grade compliance documentation
- **API Credit Optimization**: Intelligent caching to minimize API usage
- **Async Architecture**: High-performance async-first design

## Tech Stack

- **Python 3.11+**
- **FastAPI** - Web framework
- **Pydantic v2** - Data validation
- **httpx** - Async HTTP client
- **Redis/PostgreSQL** - Caching layer
- **ReportLab** - PDF generation
- **Blockchair API** - Blockchain data provider

## Installation

```bash
# Clone the repository
git clone https://github.com/rodrigoguedes09/safetrace.git
cd safetrace

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or
.\venv\Scripts\activate  # Windows

# Install dependencies
pip install -e .

# Copy environment configuration
cp .env.example .env
# Edit .env with your configuration
```

## Configuration

Edit `.env` file with your settings:

```env
# Blockchair API Key (recommended for higher limits)
BLOCKCHAIR_API_KEY=your_api_key_here

# Cache backend: redis, postgres, or memory
CACHE_BACKEND=redis
REDIS_URL=redis://localhost:6379/0

# Tracing configuration
MAX_TRACE_DEPTH=10
CACHE_TTL_SECONDS=86400
```

## Usage

### Start the Server

```bash
# Development
uvicorn app.main:app --reload

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### API Endpoints

#### Trace Transaction Risk

```http
POST /api/v1/compliance/trace
Content-Type: application/json

{
  "tx_hash": "0x...",
  "chain": "ethereum",
  "depth": 3
}
```

**Response:**
```json
{
  "success": true,
  "message": "Analysis complete. Risk level: LOW",
  "report": {
    "tx_hash": "0x...",
    "chain": "ethereum",
    "risk_score": {
      "score": 15,
      "level": "LOW",
      "reasons": ["No suspicious entities detected"]
    },
    "flagged_entities": [],
    "total_addresses_analyzed": 12,
    "api_calls_used": 8
  },
  "pdf_url": "/api/v1/compliance/download/compliance_ethereum_xxx.pdf",
  "pdf_base64": "..."
}
```

#### List Supported Chains

```http
GET /api/v1/chains
```

#### Health Check

```http
GET /api/v1/health
```

### Interactive Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Project Structure

```
safetrace/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── config.py            # Settings and configuration
│   ├── constants.py         # Chain configs and risk tags
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes.py        # API endpoints
│   │   └── dependencies.py  # Dependency injection
│   ├── core/
│   │   ├── __init__.py
│   │   ├── cache.py         # Cache interface
│   │   ├── provider.py      # Blockchain provider interface
│   │   └── exceptions.py    # Custom exceptions
│   ├── cache/
│   │   ├── __init__.py
│   │   ├── redis.py         # Redis backend
│   │   ├── postgres.py      # PostgreSQL backend
│   │   └── memory.py        # In-memory backend
│   ├── providers/
│   │   ├── __init__.py
│   │   └── blockchair.py    # Blockchair API provider
│   ├── models/
│   │   ├── __init__.py
│   │   ├── blockchain.py    # Blockchain models
│   │   └── risk.py          # Risk assessment models
│   └── services/
│       ├── __init__.py
│       ├── tracer.py        # BFS tracing engine
│       ├── risk_scorer.py   # Risk scoring algorithm
│       └── pdf_generator.py # PDF certificate generator
├── tests/
├── reports/                 # Generated PDFs
├── pyproject.toml
├── .env.example
└── README.md
```

## Risk Scoring Algorithm

The risk score is calculated using a weighted formula:

```
R = Σ(Vi × Wi × Di)
```

Where:
- **Vi**: Risk factor presence (1 if detected)
- **Wi**: Weight for the risk factor
- **Di**: Distance decay factor (0.5^distance)

### Risk Factor Weights

| Factor | Weight |
|--------|--------|
| Mixer/Tumbler | 1.0 |
| Darknet | 1.0 |
| Sanctioned | 1.0 |
| Hack | 0.9 |
| Scam | 0.8 |
| Gambling | 0.4 |
| Exchange | -0.2 (reduces risk) |

## Supported Blockchains

### UTXO-based
- Bitcoin (BTC)
- Bitcoin Cash (BCH)
- Litecoin (LTC)
- Dogecoin (DOGE)
- Dash (DASH)
- Zcash (ZEC)
- Bitcoin SV (BSV)
- And more...

### Account-based (EVM)
- Ethereum (ETH)
- BNB Smart Chain (BNB)
- Polygon (MATIC)
- Arbitrum
- Optimism
- Avalanche (AVAX)
- Base
- And 30+ more...

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=app

# Type checking
mypy app

# Linting
ruff check app
```

## License

MIT License

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request
