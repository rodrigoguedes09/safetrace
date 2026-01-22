# Deployment Guide - Railway.app

## Por que Railway?

- Deploy em minutos
- PostgreSQL + Redis inclusos
- Scaling automático
- $5 de crédito grátis
- Perfeito para MVP

## Passo 1: Preparar o Projeto

### 1.1 Criar requirements.txt

```bash
cd C:\Users\rodri\OneDrive\Documentos\GitHub\safetrace
pip freeze > requirements.txt
```

### 1.2 Criar Procfile

Criar `Procfile` na raiz:
```
web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

### 1.3 Criar railway.json

```json
{
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "uvicorn app.main:app --host 0.0.0.0 --port $PORT",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

### 1.4 Atualizar .gitignore

Verificar se tem:
```
.env
__pycache__/
*.pyc
.venv/
reports/
```

## Passo 2: Setup Railway

### 2.1 Criar Conta
1. Acesse https://railway.app
2. Login com GitHub
3. Conecte o repositório safetrace

### 2.2 Criar Projeto
```bash
# Instalar Railway CLI (opcional)
npm i -g @railway/cli

# Login
railway login

# Init projeto
railway init
```

### 2.3 Adicionar PostgreSQL
1. No dashboard Railway: "New" → "Database" → "PostgreSQL"
2. Railway cria automaticamente a variável `DATABASE_URL`

### 2.4 Adicionar Redis
1. "New" → "Database" → "Redis"
2. Railway cria automaticamente a variável `REDIS_URL`

## Passo 3: Configurar Variáveis de Ambiente

No Railway Dashboard → Variables:

```env
# Application
APP_NAME=SafeTrace
APP_VERSION=1.0.0
DEBUG=false

# API
API_PREFIX=/api/v1

# Blockchair
BLOCKCHAIR_API_KEY=<sua_chave>
BLOCKCHAIR_BASE_URL=https://api.blockchair.com
BLOCKCHAIR_REQUESTS_PER_SECOND=10.0
BLOCKCHAIR_MAX_RETRIES=3
BLOCKCHAIR_RETRY_DELAY=1.0

# Cache (Railway injeta automaticamente)
CACHE_BACKEND=redis
CACHE_TTL_SECONDS=86400

# PostgreSQL (Railway injeta DATABASE_URL)
POSTGRES_DSN=${{DATABASE_URL}}

# Redis (Railway injeta REDIS_URL)
# REDIS_URL já está disponível

# Tracing
DEFAULT_TRACE_DEPTH=3
MAX_TRACE_DEPTH=10

# PDF
PDF_OUTPUT_DIR=/tmp/reports
```

## Passo 4: Ajustar o Código para Produção

### 4.1 Atualizar config.py para Railway

```python
# Em app/config.py, adicionar suporte para DATABASE_URL
import os

class Settings(BaseSettings):
    # ... campos existentes ...
    
    # Railway injeta DATABASE_URL automaticamente
    database_url: str = Field(default="")
    
    @property
    def postgres_dsn(self) -> str:
        """Get PostgreSQL DSN from DATABASE_URL or env."""
        if self.database_url:
            return self.database_url
        return os.getenv("POSTGRES_DSN", "postgresql://user:pass@localhost:5432/safetrace")
```

### 4.2 Criar script de health check

Criar `app/utils/health.py`:
```python
import asyncio
from app.core.cache import CacheBackend

async def check_health(cache: CacheBackend) -> dict:
    """Health check for Railway."""
    try:
        cache_ok = await cache.ping()
        return {
            "status": "healthy" if cache_ok else "degraded",
            "cache": "connected" if cache_ok else "disconnected"
        }
    except Exception:
        return {"status": "unhealthy", "cache": "error"}
```

## Passo 5: Deploy

### Opção A: Deploy Automático (Recomendado)

1. Commit e push para GitHub:
```bash
git add .
git commit -m "Prepare for Railway deployment"
git push origin main
```

2. Railway detecta automaticamente e faz deploy!

### Opção B: Deploy via CLI

```bash
railway up
```

## Passo 6: Configurar Domínio

### 6.1 Domínio Railway (Grátis)
1. Settings → Networking
2. "Generate Domain"
3. Você recebe: `safetrace-production.up.railway.app`

### 6.2 Domínio Customizado
1. Comprar domínio (Namecheap, GoDaddy)
2. Railway → Settings → Networking → Custom Domain
3. Adicionar: `api.safetrace.io`
4. Configurar DNS:
   - Tipo: CNAME
   - Nome: api
   - Valor: (fornecido pelo Railway)

## Passo 7: Verificar Deploy

```bash
# Health check
curl https://safetrace-production.up.railway.app/api/v1/health

# Teste básico
curl https://safetrace-production.up.railway.app/api/v1/chains
```

## Passo 8: Monitoramento

### 8.1 Railway Logs
- Dashboard → Deployments → View Logs

### 8.2 Adicionar Sentry (Recomendado)
```bash
pip install sentry-sdk[fastapi]
```

Em `app/main.py`:
```python
import sentry_sdk

if not settings.debug:
    sentry_sdk.init(
        dsn="https://your-sentry-dsn",
        traces_sample_rate=1.0,
    )
```

## Passo 9: CI/CD (Opcional mas Recomendado)

Criar `.github/workflows/deploy.yml`:
```yaml
name: Deploy to Railway

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Use Railway CLI
        run: |
          npm i -g @railway/cli
          railway up --service safetrace
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
```

## Troubleshooting

### Erro: Port already in use
- Railway injeta $PORT automaticamente
- Use: `--port $PORT` no comando uvicorn

### Erro: Database connection refused
- Verificar se PostgreSQL foi adicionado
- Verificar variável `DATABASE_URL`

### Erro: Redis connection timeout
- Verificar se Redis foi adicionado
- Verificar variável `REDIS_URL`

### App não responde
- Verificar logs: Railway Dashboard → Logs
- Verificar health check: `/api/v1/health`

## Custos Estimados

- **Free Tier:** $5 de crédito + 500h grátis/mês
- **Pro Plan:** $20/mês (para produção)
- **PostgreSQL:** Incluído
- **Redis:** Incluído

## Próximos Passos

Após o deploy:
1. Testar todos os endpoints
2. Configurar SSL (automático no Railway)
3. Adicionar monitoramento (Sentry)
4. Configurar backups do PostgreSQL
5. Implementar autenticação (próximo doc)

## Alternativa: Deploy via Docker

Se preferir usar Docker, criar `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

E `docker-compose.yml` para testes locais:

```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - REDIS_URL=redis://redis:6379
      - POSTGRES_DSN=postgresql://user:pass@postgres:5432/safetrace
    depends_on:
      - redis
      - postgres

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: safetrace
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
    ports:
      - "5432:5432"
```

Teste local:
```bash
docker-compose up
```
