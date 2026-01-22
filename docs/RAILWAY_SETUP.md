# Railway Setup Guide - Conectar Redis e PostgreSQL

## 1. Adicionar Redis ao Projeto

1. Acesse o dashboard do Railway: https://railway.app/
2. Selecione seu projeto **safetrace**
3. Clique em **"+ New"** → **"Database"** → **"Add Redis"**
4. O Railway irá automaticamente:
   - Criar uma instância Redis
   - Gerar a variável de ambiente `REDIS_URL`
   - Injetar essa variável no seu serviço web

## 2. Adicionar PostgreSQL ao Projeto

1. No mesmo projeto, clique em **"+ New"** → **"Database"** → **"Add PostgreSQL"**
2. O Railway irá automaticamente:
   - Criar uma instância PostgreSQL
   - Gerar a variável de ambiente `DATABASE_URL`
   - Injetar essa variável no seu serviço web

## 3. Verificar Variáveis de Ambiente

1. Clique no seu serviço web (safetrace)
2. Vá para a aba **"Variables"**
3. Você deve ver essas variáveis injetadas automaticamente:
   - `DATABASE_URL` (PostgreSQL connection string)
   - `REDIS_URL` (Redis connection string)
   - `PORT` (porta do servidor)

## 4. Configurar Outras Variáveis Necessárias

Adicione manualmente as seguintes variáveis clicando em **"+ New Variable"**:

### Obrigatórias:
- `BLOCKCHAIR_API_KEY`: Sua chave da API Blockchair (obtenha em https://blockchair.com/api)
- `CACHE_BACKEND`: `redis` (para usar Redis em produção)

### Opcionais:
- `DEBUG`: `false` (já é o padrão)
- `DEFAULT_TRACE_DEPTH`: `3` (já é o padrão)
- `MAX_TRACE_DEPTH`: `10` (já é o padrão)

## 5. Formato das Variáveis (Referência)

```bash
# Auto-injetadas pelo Railway:
DATABASE_URL=postgresql://postgres:senha@containers-us-west-123.railway.app:6543/railway
REDIS_URL=redis://default:senha@containers-us-west-123.railway.app:7890
PORT=8000

# Você precisa adicionar:
BLOCKCHAIR_API_KEY=seu_api_key_aqui
CACHE_BACKEND=redis
```

## 6. Verificar Conexões

Após adicionar Redis e PostgreSQL, o Railway fará um **redeploy automático**. Verifique os logs:

1. Clique no seu serviço web
2. Vá para a aba **"Deployments"**
3. Clique no deployment mais recente
4. Verifique os logs para mensagens como:
   ```
   INFO - Database tables initialized
   INFO - Cache backend: redis
   ```

## 7. Testar a Aplicação

1. Acesse seu domínio Railway (ex: `https://web3-sentinel-production.up.railway.app`)
2. Tente registrar um novo usuário
3. Faça login
4. Teste uma análise KYT

## 8. Troubleshooting

### Erro: "Connection refused" para PostgreSQL
- Verifique se o serviço PostgreSQL está rodando no Railway
- Confirme que a variável `DATABASE_URL` está presente

### Erro: "Connection refused" para Redis
- Verifique se o serviço Redis está rodando no Railway
- Confirme que a variável `REDIS_URL` está presente

### Erro: "No module named 'psycopg'"
- Adicione ao `requirements.txt`: `asyncpg>=0.29.0`
- Faça commit e push para redeploy

### Tabelas não são criadas automaticamente
- A aplicação cria as tabelas automaticamente no startup
- Verifique os logs para confirmar: "Database tables initialized"
- Se necessário, você pode executar SQL manualmente:
  1. No Railway, clique no serviço PostgreSQL
  2. Vá para "Data" → "Query"
  3. Execute o SQL do arquivo `app/db/schema.py`

## 9. Arquitetura Final

```
┌─────────────────────────────────────┐
│     Railway Project: safetrace      │
├─────────────────────────────────────┤
│                                     │
│  ┌─────────────────────────────┐   │
│  │   Web Service (FastAPI)     │   │
│  │   - API Backend             │   │
│  │   - Frontend (HTML/JS)      │   │
│  │   - Porta: $PORT            │   │
│  └──────────┬──────────────────┘   │
│             │                       │
│    ┌────────┴────────┐             │
│    ▼                 ▼             │
│  ┌──────────┐   ┌─────────┐       │
│  │PostgreSQL│   │  Redis  │       │
│  │(users,   │   │(cache,  │       │
│  │api_keys, │   │rate     │       │
│  │history)  │   │limit)   │       │
│  └──────────┘   └─────────┘       │
└─────────────────────────────────────┘
```

## 10. Custo Estimado

- **PostgreSQL**: $5/mês (500 MB)
- **Redis**: $5/mês (25 MB)
- **Web Service**: $5/mês (512 MB RAM)
- **Total**: ~$15/mês

Railway oferece $5 de crédito grátis por mês para hobbyists.

## 11. Próximos Passos

- [ ] Configurar custom domain (opcional)
- [ ] Adicionar monitoring/alertas
- [ ] Configurar backups automáticos do PostgreSQL
- [ ] Implementar sistema de pagamentos (Stripe)
