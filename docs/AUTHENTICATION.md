# Sistema de Autenticação e API Keys

## Visão Geral

Sistema de autenticação baseado em API Keys para controlar acesso e uso do SafeTrace.

## Arquitetura

```
User → API Key → Rate Limiter → SafeTrace API → Response
          ↓
    Usage Tracking
```

## Implementação

### 1. Modelo de Usuário e API Keys

Criar `app/models/user.py`:

```python
from datetime import datetime
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, EmailStr, Field


class PlanType(str, Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    email: EmailStr
    name: str
    plan: PlanType = PlanType.FREE
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True


class APIKey(BaseModel):
    key: str = Field(default_factory=lambda: f"sk_live_{uuid4().hex}")
    user_id: str
    name: str = "Default Key"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_used_at: datetime | None = None
    is_active: bool = True
    
    # Limites por plano
    requests_per_month: int = 1000
    requests_used: int = 0
    reset_date: datetime = Field(
        default_factory=lambda: datetime.utcnow().replace(day=1, hour=0, minute=0)
    )


class UsageRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    api_key: str
    endpoint: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    tx_hash: str | None = None
    chain: str | None = None
    trace_depth: int | None = None
    api_calls_used: int = 0
    success: bool = True
```

### 2. Database Schema (PostgreSQL)

Criar `migrations/001_initial.sql`:

```sql
-- Users table
CREATE TABLE users (
    id VARCHAR(36) PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    plan VARCHAR(20) DEFAULT 'free',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);

-- API Keys table
CREATE TABLE api_keys (
    key VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(36) REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) DEFAULT 'Default Key',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_used_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE,
    requests_per_month INTEGER DEFAULT 1000,
    requests_used INTEGER DEFAULT 0,
    reset_date TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Usage records table
CREATE TABLE usage_records (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) REFERENCES users(id) ON DELETE CASCADE,
    api_key VARCHAR(64) REFERENCES api_keys(key),
    endpoint VARCHAR(255),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    tx_hash VARCHAR(128),
    chain VARCHAR(50),
    trace_depth INTEGER,
    api_calls_used INTEGER DEFAULT 0,
    success BOOLEAN DEFAULT TRUE
);

-- Indexes for performance
CREATE INDEX idx_api_keys_user ON api_keys(user_id);
CREATE INDEX idx_usage_user ON usage_records(user_id);
CREATE INDEX idx_usage_timestamp ON usage_records(timestamp);
CREATE INDEX idx_api_keys_active ON api_keys(is_active) WHERE is_active = TRUE;
```

### 3. Repository Layer

Criar `app/repositories/user_repository.py`:

```python
from typing import List, Optional
import asyncpg
from app.models.user import User, APIKey, UsageRecord


class UserRepository:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool
    
    async def create_user(self, user: User) -> User:
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO users (id, email, name, plan, created_at, is_active)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                user.id, user.email, user.name, user.plan.value,
                user.created_at, user.is_active
            )
        return user
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM users WHERE email = $1", email
            )
            if row:
                return User(**dict(row))
        return None
    
    async def create_api_key(self, api_key: APIKey) -> APIKey:
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO api_keys 
                (key, user_id, name, created_at, is_active, 
                 requests_per_month, requests_used, reset_date)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                api_key.key, api_key.user_id, api_key.name,
                api_key.created_at, api_key.is_active,
                api_key.requests_per_month, api_key.requests_used,
                api_key.reset_date
            )
        return api_key
    
    async def get_api_key(self, key: str) -> Optional[APIKey]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM api_keys WHERE key = $1 AND is_active = TRUE",
                key
            )
            if row:
                return APIKey(**dict(row))
        return None
    
    async def increment_usage(self, key: str) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE api_keys 
                SET requests_used = requests_used + 1,
                    last_used_at = NOW()
                WHERE key = $1
                """,
                key
            )
    
    async def record_usage(self, usage: UsageRecord) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO usage_records
                (id, user_id, api_key, endpoint, timestamp, 
                 tx_hash, chain, trace_depth, api_calls_used, success)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                """,
                usage.id, usage.user_id, usage.api_key, usage.endpoint,
                usage.timestamp, usage.tx_hash, usage.chain,
                usage.trace_depth, usage.api_calls_used, usage.success
            )
```

### 4. Authentication Dependency

Criar `app/api/auth.py`:

```python
from typing import Annotated
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from app.models.user import APIKey, User
from app.repositories.user_repository import UserRepository

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_user_repository() -> UserRepository:
    # Inject database pool
    from app.api.dependencies import get_db_pool
    pool = await get_db_pool()
    return UserRepository(pool)


async def verify_api_key(
    api_key: str = Security(api_key_header),
    repo: UserRepository = Depends(get_user_repository),
) -> APIKey:
    """Verify API key and return key info."""
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key required. Include 'X-API-Key' header.",
        )
    
    if not api_key.startswith("sk_"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key format",
        )
    
    key_info = await repo.get_api_key(api_key)
    
    if not key_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key",
        )
    
    if not key_info.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API Key is disabled",
        )
    
    # Check usage limits
    if key_info.requests_used >= key_info.requests_per_month:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Monthly limit reached ({key_info.requests_per_month} requests)",
        )
    
    return key_info


async def get_current_user(
    api_key_info: APIKey = Depends(verify_api_key),
    repo: UserRepository = Depends(get_user_repository),
) -> User:
    """Get user from API key."""
    # Implementation to fetch user
    pass
```

### 5. Proteger Endpoints

Atualizar `app/api/routes.py`:

```python
from fastapi import Depends
from app.api.auth import verify_api_key, get_current_user
from app.models.user import APIKey, User

@router.post(
    "/compliance/trace",
    response_model=TraceResponse,
)
async def trace_transaction(
    request: TraceRequest,
    api_key: APIKey = Depends(verify_api_key),  # Adicionar autenticação
    tracer: Annotated[TransactionTracerService, Depends(get_tracer_service)],
    pdf_generator: Annotated[PDFGeneratorService, Depends(get_pdf_generator)],
    repo: UserRepository = Depends(get_user_repository),
) -> TraceResponse:
    """Trace transaction with authentication."""
    try:
        # Increment usage counter
        await repo.increment_usage(api_key.key)
        
        # Existing logic...
        report = await tracer.trace_transaction_risk(
            tx_hash=request.tx_hash,
            chain=request.chain,
            depth=request.depth,
        )
        
        # Record usage
        await repo.record_usage(
            UsageRecord(
                user_id=api_key.user_id,
                api_key=api_key.key,
                endpoint="/compliance/trace",
                tx_hash=request.tx_hash,
                chain=request.chain,
                trace_depth=request.depth,
                api_calls_used=report.api_calls_used,
                success=True,
            )
        )
        
        # Rest of the code...
```

### 6. Endpoints de Gerenciamento

Adicionar em `app/api/routes.py`:

```python
@router.post("/auth/register")
async def register_user(
    email: EmailStr,
    name: str,
    repo: UserRepository = Depends(get_user_repository),
):
    """Register new user and generate API key."""
    existing = await repo.get_user_by_email(email)
    if existing:
        raise HTTPException(400, "Email already registered")
    
    user = User(email=email, name=name, plan=PlanType.FREE)
    await repo.create_user(user)
    
    # Create first API key
    api_key = APIKey(
        user_id=user.id,
        name="Default Key",
        requests_per_month=1000,  # Free tier
    )
    await repo.create_api_key(api_key)
    
    return {
        "user_id": user.id,
        "api_key": api_key.key,
        "requests_per_month": api_key.requests_per_month,
    }


@router.get("/auth/usage")
async def get_usage(
    api_key: APIKey = Depends(verify_api_key),
):
    """Get current usage stats."""
    return {
        "requests_used": api_key.requests_used,
        "requests_limit": api_key.requests_per_month,
        "requests_remaining": api_key.requests_per_month - api_key.requests_used,
        "reset_date": api_key.reset_date,
    }
```

## Limites por Plano

```python
PLAN_LIMITS = {
    PlanType.FREE: {
        "requests_per_month": 1000,
        "max_trace_depth": 3,
        "api_calls_per_trace": 50,
        "rate_limit_per_minute": 10,
    },
    PlanType.PRO: {
        "requests_per_month": 10000,
        "max_trace_depth": 10,
        "api_calls_per_trace": 500,
        "rate_limit_per_minute": 100,
    },
    PlanType.ENTERPRISE: {
        "requests_per_month": 100000,
        "max_trace_depth": 20,
        "api_calls_per_trace": 5000,
        "rate_limit_per_minute": 1000,
    },
}
```

## Rate Limiting

Usar `slowapi`:

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/compliance/trace")
@limiter.limit("10/minute")  # Free tier
async def trace_transaction(...):
    pass
```

## Próximos Passos

1. Implementar sistema completo
2. Adicionar dashboard de usuário
3. Integrar Stripe para pagamentos
4. Webhooks para eventos
