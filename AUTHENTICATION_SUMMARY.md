# ✅ Sistema de Autenticação Implementado

## 🎯 O que foi Desenvolvido

### **Fase 2 - Autenticação Completa** ✅

Sistema de autenticação baseado em API Keys com rate limiting e controle de usuários.

---

## 📦 Novos Arquivos Criados

### **1. Models**
- `app/models/auth.py` - User, APIKey, RateLimitInfo, TokenData

### **2. Services**
- `app/services/auth_service.py` - Gerenciamento de usuários e API keys
- `app/services/rate_limit_service.py` - Rate limiting por usuário/tier

### **3. Database**
- `app/db/schema.py` - Schema SQL para tabelas users e api_keys

### **4. API**
- `app/api/auth_middleware.py` - Middleware de autenticação
- `app/api/auth_routes.py` - Endpoints de autenticação

### **5. Tests & Docs**
- `test_auth.py` - Script de teste completo
- `RAILWAY_ENV_SETUP.md` - Guia de configuração no Railway

---

## 🔐 Endpoints de Autenticação

### **Públicos (Sem Autenticação)**

#### `POST /api/v1/auth/register`
Registra novo usuário
```json
{
  "email": "user@example.com",
  "full_name": "Nome Completo",
  "password": "SenhaForte123"
}
```

#### `POST /api/v1/auth/bootstrap`
Cria primeira API key usando email/senha
```json
{
  "email": "user@example.com",
  "password": "SenhaForte123",
  "key_data": {
    "name": "Production Key",
    "description": "Main API key"
  }
}
```

### **Protegidos (Requerem API Key)**

#### `GET /api/v1/auth/me`
Retorna informações do usuário autenticado

#### `GET /api/v1/auth/rate-limit`
Mostra status do rate limit (requests usados/limite)

#### `POST /api/v1/auth/api-keys`
Cria nova API key
```json
{
  "name": "Dev Key",
  "description": "Para desenvolvimento"
}
```

#### `GET /api/v1/auth/api-keys`
Lista todas as API keys do usuário

#### `DELETE /api/v1/auth/api-keys/{key_id}`
Revoga uma API key

---

## 🛡️ Rate Limiting

### **Free Tier**
- **100 requests/dia**
- Reset diário às 00:00 UTC

### **Premium Tier**
- **1000 requests/dia**
- Reset diário às 00:00 UTC

### **Headers de Rate Limit**
Toda resposta autenticada inclui:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1706400000
```

---

## 🔑 Como Usar API Keys

### **Método 1: Authorization Header (Bearer)**
```bash
curl -H "Authorization: Bearer sk_sua_api_key_aqui" \
  https://web3-sentinel-production.up.railway.app/api/v1/compliance/trace
```

### **Método 2: X-API-Key Header**
```bash
curl -H "X-API-Key: sk_sua_api_key_aqui" \
  https://web3-sentinel-production.up.railway.app/api/v1/compliance/trace
```

---

## 🗄️ Estrutura do Banco de Dados

### **Tabela: users**
```sql
- id: UUID (PK)
- email: VARCHAR(255) UNIQUE
- full_name: VARCHAR(100)
- hashed_password: VARCHAR(255)
- is_active: BOOLEAN
- is_premium: BOOLEAN
- created_at: TIMESTAMP
- updated_at: TIMESTAMP
```

### **Tabela: api_keys**
```sql
- id: UUID (PK)
- user_id: UUID (FK -> users.id)
- name: VARCHAR(50)
- description: VARCHAR(200)
- hashed_key: VARCHAR(255)
- key_prefix: VARCHAR(12)
- is_active: BOOLEAN
- last_used_at: TIMESTAMP
- created_at: TIMESTAMP
- expires_at: TIMESTAMP
```

---

## 📊 Fluxo de Autenticação

```
1. User Registration
   POST /auth/register
   → Create user in database
   → Return user info

2. Bootstrap First Key
   POST /auth/bootstrap
   → Verify email/password
   → Generate API key
   → Return full key (only time shown)

3. Use API Key
   Any protected endpoint
   → Extract key from header
   → Verify key against database
   → Check expiration
   → Check rate limit
   → Process request

4. Create Additional Keys
   POST /auth/api-keys
   → Use existing key
   → Generate new key
   → Return full key
```

---

## 🔒 Segurança

### **Senha**
- Min 8 caracteres
- Requer: maiúscula, minúscula, dígito
- Hash: bcrypt

### **API Keys**
- Formato: `sk_` + 32 bytes aleatórios (URL-safe)
- Armazenamento: Hash bcrypt
- Prefix: Primeiros 12 chars para identificação

### **Rate Limiting**
- Por usuário (não por IP)
- Cache Redis para performance
- Reset diário automático

---

## 🚀 Deploy no Railway

### **1. Variáveis de Ambiente**
Adicione no Railway:
```env
BLOCKCHAIR_API_KEY=sua_chave
CACHE_BACKEND=redis
```

### **2. Serviços Necessários**
- ✅ PostgreSQL (para users e api_keys)
- ✅ Redis (para cache e rate limiting)

### **3. Auto-Configurado**
Railway injeta automaticamente:
- `DATABASE_URL`
- `REDIS_URL`
- `PORT`

### **4. Deploy**
```bash
git add .
git commit -m "Add authentication system"
git push origin main
```

Railway vai:
- ✅ Instalar dependências (`passlib`, `python-jose`)
- ✅ Criar tabelas no PostgreSQL (startup automático)
- ✅ Conectar ao Redis
- ✅ Iniciar servidor com autenticação ativa

---

## 🧪 Testes

### **Local**
```bash
python test_auth.py
```

### **Produção**
```bash
# 1. Registrar
curl -X POST https://web3-sentinel-production.up.railway.app/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","full_name":"Test","password":"Test123"}'

# 2. Bootstrap key
curl -X POST https://web3-sentinel-production.up.railway.app/api/v1/auth/bootstrap?email=test@test.com&password=Test123 \
  -H "Content-Type: application/json" \
  -d '{"name":"First Key","description":"Initial key"}'

# 3. Testar trace
curl -X POST https://web3-sentinel-production.up.railway.app/api/v1/compliance/trace \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk_sua_key" \
  -d '{"transaction_hash":"0x...","chain":"ethereum","depth":2}'
```

---

## 📈 Próximos Passos (Fase 3)

1. **Frontend Dashboard**
   - React/Next.js
   - Gerenciar API keys
   - Visualizar histórico de traces
   - Monitorar rate limit

2. **Stripe Integration**
   - Planos Free/Premium
   - Webhook de pagamentos
   - Upgrade automático de tier

3. **Analytics**
   - Requests por dia/hora
   - Chains mais usadas
   - Risk scores médios

4. **Webhooks**
   - Notificar quando rate limit próximo do limite
   - Alertas de transações de alto risco

---

## ✅ Status do Projeto

- ✅ **Fase 1**: Arquitetura base e tracing (Completo)
- ✅ **Fase 2**: Autenticação e rate limiting (Completo)
- ⏳ **Fase 3**: Monetização e frontend (Próximo)

**SafeTrace está pronto para receber usuários com autenticação completa!** 🎉
