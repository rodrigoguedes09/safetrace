# 🚀 Configuração de Variáveis de Ambiente no Railway

## Variáveis Obrigatórias

No Railway dashboard → **Variables**, adicione:

```env
# Blockchair API Key (obtenha em https://blockchair.com/api)
BLOCKCHAIR_API_KEY=sua_chave_aqui

# Cache Backend (agora usando redis)
CACHE_BACKEND=redis
```

## Variáveis Auto-Injetadas pelo Railway

O Railway injeta automaticamente quando você adiciona os serviços:

- ✅ `DATABASE_URL` - Injetado ao adicionar PostgreSQL
- ✅ `REDIS_URL` - Injetado ao adicionar Redis  
- ✅ `PORT` - Injetado automaticamente pelo Railway

**Não precisa configurar manualmente!**

---

## ✅ Checklist

### 1. Serviços Adicionados
- [x] PostgreSQL (cria automaticamente DATABASE_URL)
- [x] Redis (cria automaticamente REDIS_URL)

### 2. Variáveis Configuradas
- [ ] BLOCKCHAIR_API_KEY=sua_chave
- [ ] CACHE_BACKEND=redis

---

## 🔧 Como Configurar

### No Railway Dashboard:

1. Vá no seu serviço **web3-sentinel**
2. Clique em **Variables**
3. Adicione as variáveis:
   - `BLOCKCHAIR_API_KEY` → Sua chave da Blockchair API
   - `CACHE_BACKEND` → `redis`
4. Clique em **"Deploy"** para aplicar

### Verificar Variáveis Auto-Injetadas:

1. Em **Variables**, você deve ver:
   - `DATABASE_URL` (referência ao PostgreSQL)
   - `REDIS_URL` (referência ao Redis)
   - `PORT` (geralmente 8000 ou auto)

---

## 📊 Valores de Produção Recomendados

```env
# Blockchair API
BLOCKCHAIR_API_KEY=sua_chave_aqui
BLOCKCHAIR_REQUESTS_PER_SECOND=10.0

# Cache
CACHE_BACKEND=redis
CACHE_TTL_SECONDS=86400

# Debug (desligado em produção)
DEBUG=false

# Trace
DEFAULT_TRACE_DEPTH=3
MAX_TRACE_DEPTH=10
```

---

## 🎯 Após Configurar

Commit as mudanças e faça push:

```bash
git add .
git commit -m "Add authentication system with PostgreSQL and Redis"
git push origin main
```

O Railway vai:
1. Detectar as mudanças
2. Rebuildar com novas dependências
3. Inicializar as tabelas do banco
4. Conectar ao Redis para cache
5. Deploy automático! 🚀

---

## 🧪 Testar Autenticação

Após o deploy, teste os novos endpoints:

### 1. Registrar usuário:
```bash
curl -X POST https://web3-sentinel-production.up.railway.app/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "seu@email.com",
    "full_name": "Seu Nome",
    "password": "SenhaForte123"
  }'
```

### 2. Criar API key:
```bash
curl -X POST https://web3-sentinel-production.up.railway.app/api/v1/auth/api-keys \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sua_primeira_key" \
  -d '{
    "name": "Production Key",
    "description": "Main API key"
  }'
```

### 3. Testar trace com autenticação:
```bash
curl -X POST https://web3-sentinel-production.up.railway.app/api/v1/compliance/trace \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sua_api_key" \
  -d '{
    "transaction_hash": "0x...",
    "chain": "ethereum",
    "depth": 2
  }'
```

---

## 🆘 Troubleshooting

### Erro: "Failed to connect to database"
- Verifique se o serviço PostgreSQL está ativo no Railway
- Verifique se DATABASE_URL está aparecendo nas variáveis

### Erro: "Failed to connect to Redis"
- Verifique se o serviço Redis está ativo
- Verifique se REDIS_URL está aparecendo nas variáveis
- Ou mude para `CACHE_BACKEND=memory` temporariamente

### Health check falha
- Aguarde o build completar (~3-5 minutos)
- Verifique logs no Railway dashboard
- Tabelas do banco são criadas automaticamente no startup
