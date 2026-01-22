# 🚀 Railway Deployment Guide

## Seu projeto está pronto para deploy no Railway!

### ✅ Arquivos de Deploy Criados:
- **Procfile**: Comando para rodar o servidor uvicorn
- **railway.json**: Configuração do Railway (health checks, workers, etc.)
- **requirements.txt**: Dependências Python (apenas produção)
- **.env.example**: Template de variáveis de ambiente
- **app/config.py**: Ajustado para usar PORT, DATABASE_URL e REDIS_URL do Railway

---

## 📋 Passo a Passo para Deploy

### 1. **Commit e Push para GitHub**
```bash
git add .
git commit -m "Add Railway deployment configuration"
git push origin main
```

### 2. **Criar Projeto no Railway**
1. Acesse https://railway.app
2. Clique em "Start a New Project"
3. Selecione "Deploy from GitHub repo"
4. Conecte seu repositório `safetrace`

### 3. **Configurar Variável de Ambiente**
No dashboard do Railway, vá em **Variables** e adicione:
```
BLOCKCHAIR_API_KEY=sua_chave_aqui
CACHE_BACKEND=memory
```

**Importante**: 
- Obtenha sua API key gratuita em https://blockchair.com/api
- Usando `CACHE_BACKEND=memory` para começar (grátis)
- Railway injeta automaticamente `PORT`, `DATABASE_URL` e `REDIS_URL`

### 4. **Deploy Automático** ✨
Railway fará o deploy automaticamente! Aguarde ~2-3 minutos.

### 5. **Verificar Deploy**
Clique no botão **"View Deployment"** ou acesse a URL gerada:
```
https://seu-app.up.railway.app/docs
```

Teste os endpoints:
- `GET /` - Info da API
- `GET /api/v1/health` - Health check
- `GET /api/v1/chains` - 42 blockchains suportadas

---

## 🎯 Teste Rápido
Após o deploy, teste o trace de transação:

```bash
curl -X POST https://seu-app.up.railway.app/api/v1/compliance/trace \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_hash": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
    "chain": "bitcoin",
    "depth": 2
  }'
```

---

## 🔧 Upgrades Opcionais (Depois)

### Adicionar PostgreSQL (Cache Persistente):
1. No Railway, clique em "New" → "Database" → "PostgreSQL"
2. Railway injeta `DATABASE_URL` automaticamente
3. Altere variável: `CACHE_BACKEND=postgres`
4. Redeploy

### Adicionar Redis (Cache Rápido):
1. No Railway, clique em "New" → "Database" → "Redis"
2. Railway injeta `REDIS_URL` automaticamente
3. Altere variável: `CACHE_BACKEND=redis`
4. Redeploy

---

## 💡 Custos Estimados
- **Starter Plan** (grátis): 500 horas/mês + $5 crédito
- **Memory cache**: Sem custos extras
- **PostgreSQL**: ~$5/mês (500MB)
- **Redis**: ~$10/mês (256MB)

**Recomendação**: Comece com `memory` cache (grátis) e depois adicione PostgreSQL se precisar de persistência.

---

## 🆘 Troubleshooting

### Build falha:
- Verifique se `requirements.txt` tem versões compatíveis
- Railway usa Python 3.11 por padrão

### Health check falha:
- Railway testa `/api/v1/health` automaticamente
- Aguarde até 10 tentativas (railway.json configurado)

### Timeout errors:
- Blockchair API pode estar lento
- Reduza `depth` nos requests de trace

---

## 📊 Monitoramento
No Railway dashboard:
- **Logs**: Ver erros em tempo real
- **Metrics**: CPU, RAM, Network
- **Deployments**: Histórico de deploys

---

## 🎉 Pronto!
Seu SafeTrace está no ar! Compartilhe a URL com usuários para testar.

**Próximos passos para SaaS completo**: Ver `docs/SAAS_ROADMAP.md`
