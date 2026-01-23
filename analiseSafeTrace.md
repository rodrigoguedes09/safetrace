# 📊 Análise Completa do Projeto SafeTrace

**Data da análise:** Janeiro de 2026  
**Versão analisada:** 1.0.0  
**Analista:** GitHub Copilot (Claude Opus 4.5)

---

## 📑 Índice

1. [Resumo Executivo](#resumo-executivo)
2. [O que o Projeto Faz](#o-que-o-projeto-faz)
3. [Riscos Identificados](#riscos-identificados)
   - [Riscos Críticos de Segurança](#riscos-críticos-de-segurança)
   - [Riscos de Funcionamento](#riscos-de-funcionamento)
   - [Riscos de Performance](#riscos-de-performance)
   - [Riscos de Manutenção](#riscos-de-manutenção)
4. [Melhorias Recomendadas](#melhorias-recomendadas)
   - [Melhorias de Segurança](#melhorias-de-segurança)
   - [Melhorias de Código](#melhorias-de-código)
   - [Melhorias de Funcionalidade](#melhorias-de-funcionalidade)
5. [Arquivos e Pastas Não Utilizados](#arquivos-e-pastas-não-utilizados)
6. [Análise Detalhada por Componente](#análise-detalhada-por-componente)
7. [Conclusão](#conclusão)

---

## 🎯 Resumo Executivo

O **SafeTrace** é uma ferramenta de compliance blockchain (Know Your Transaction - KYT) que analisa transações em 41+ blockchains, identificando proximidade com entidades de alto risco como mixers, exchanges hackeadas, endereços sancionados, etc.

### Pontos Fortes
- Arquitetura bem estruturada com separação de responsabilidades
- Suporte amplo de blockchains (41+ redes)
- Sistema de cache robusto com múltiplos backends
- Algoritmo BFS eficiente para rastreamento
- Sistema de autenticação funcional com API Keys
- Geração de PDFs de compliance profissional

### Pontos Fracos
- Riscos de segurança críticos em produção
- Código duplicado entre sistemas de autenticação
- Pastas e arquivos vazios/sem uso
- Dependência única do Blockchair como provider
- Testes incompletos

---

## 📋 O que o Projeto Faz

### 1. **Funcionalidade Principal: Rastreamento de Transações (KYT)**

O sistema recebe um hash de transação blockchain e realiza:

1. **Busca da transação** via API Blockchair
2. **Rastreamento BFS** (Breadth-First Search) dos endereços de origem até N hops
3. **Análise de metadados** de cada endereço encontrado
4. **Classificação de risco** baseada em tags (mixer, darknet, hack, sancionado, etc.)
5. **Cálculo de score** ponderado por distância e severidade
6. **Geração de relatório PDF** profissional

**Fórmula de risco:**
```
R = Σ(V_i × W_i × D_i)
Onde:
- V_i = Fator de risco (1 se presente)
- W_i = Peso da tag de risco
- D_i = Fator de decay por distância (0.5^distância)
```

### 2. **Sistema de Autenticação**

- Registro de usuários com validação de senha forte
- Gerenciamento de API Keys (criação, listagem, revogação)
- Rate limiting por tier (Free: 100/dia, Premium: 1000/dia)
- Bootstrap de API key com email/senha

### 3. **Sistema de Cache**

Três backends suportados:
- **Redis** (padrão para produção)
- **PostgreSQL** (fallback)
- **Memory** (desenvolvimento)

### 4. **Frontend Web**

Páginas HTML renderizadas via Jinja2:
- Landing page
- Página de preços
- Dashboard do usuário
- Página de análise
- Documentação

### 5. **Funcionalidades Admin**

- Métricas globais e por usuário
- Audit logs
- Health checks detalhados
- Upgrade de usuários para premium

---

## 🚨 Riscos Identificados

### Riscos Críticos de Segurança

#### **1. SECRET_KEY Hardcoded no Código** ⚠️ CRÍTICO

**Arquivo:** `app/api/auth_jwt_routes.py` (linhas 14-15)

```python
SECRET_KEY = "your-secret-key-here-change-in-production"  # EXPOSTO!
ALGORITHM = "HS256"
```

**Impacto:** Qualquer pessoa com acesso ao código fonte pode forjar tokens JWT válidos.

**Remediação:** Mover para variável de ambiente:
```python
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("JWT_SECRET_KEY not configured")
```

---

#### **2. CORS Configurado como `allow_origins=["*"]`** ⚠️ CRÍTICO

**Arquivo:** `app/main.py` (linhas 68-74)

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # PERIGOSO!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Impacto:** Qualquer site malicioso pode fazer requisições autenticadas em nome do usuário.

**Remediação:**
```python
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS or ["https://safetrace.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "X-API-Key", "Content-Type"],
)
```

---

#### **3. Debug Router Exposto em Produção** ⚠️ ALTO

**Arquivo:** `app/main.py` (linha 85)

```python
app.include_router(debug_router)  # Debug endpoints expostos!
```

O endpoint `/debug/test-register` permite criar usuários sem validações completas.

**Remediação:** Condicionar ao ambiente:
```python
if settings.debug:
    app.include_router(debug_router)
```

---

#### **4. SQL Injection Potencial no Audit Logger** ⚠️ MÉDIO

**Arquivo:** `app/services/audit_logger.py`

Os parâmetros são passados via `$1::uuid` etc., porém o campo `details` aceita JSONB sem sanitização adequada.

**Remediação:** Validar estrutura do JSONB antes de inserção.

---

#### **5. Path Traversal na Rota de Download** ⚠️ MÉDIO

**Arquivo:** `app/api/routes.py` (linhas 157-176)

```python
async def download_certificate(filename: str, ...):
    file_path = Path(settings.pdf_output_dir) / filename
```

Não há validação suficiente contra path traversal (ex: `../../../etc/passwd`).

**Remediação:**
```python
from pathlib import PurePath

def is_safe_path(basedir: Path, path: Path) -> bool:
    return basedir.resolve() in path.resolve().parents or path.resolve() == basedir.resolve()

if not is_safe_path(Path(settings.pdf_output_dir), file_path):
    raise HTTPException(status_code=400, detail="Invalid filename")
```

---

#### **6. Exposição de Stack Traces em Erros** ⚠️ MÉDIO

**Arquivo:** `app/api/debug_routes.py`

```python
return {"success": False, "error": str(e), "type": type(e).__name__}
```

Informações internas são expostas ao cliente.

---

### Riscos de Funcionamento

#### **7. Imports Inválidos no auth_jwt_routes.py** ⚠️ ALTO

**Arquivo:** `app/api/auth_jwt_routes.py` (linhas 103-106)

```python
from app.config.settings import get_settings  # INCORRETO!
from app.db.postgresql import get_db_pool      # ARQUIVO NÃO EXISTE!
```

Os imports corretos são:
```python
from app.config import get_settings
from app.api.dependencies import get_db_pool
```

**Impacto:** Os endpoints `/auth-jwt/register` e `/auth-jwt/login` falham com ImportError.

---

#### **8. Dependência Única do Blockchair** ⚠️ ALTO

O projeto depende 100% da API Blockchair. Se o serviço ficar indisponível ou mudar:

- Nenhum fallback existe
- Rate limits (10 req/s) podem ser um gargalo
- Algumas chains podem não ter dados completos

**Remediação:** Implementar providers alternativos (Etherscan, Mempool.space, etc.)

---

#### **9. Cache Backend None Check Incompleto** ⚠️ MÉDIO

**Arquivo:** `app/api/dependencies.py` (linhas 111-116)

```python
def get_auth_service() -> AuthService:
    global _auth_service, _db_pool
    if _auth_service is None and _db_pool is not None:
        _auth_service = AuthService(_db_pool)
    return _auth_service  # Pode retornar None!
```

O mesmo ocorre com `get_rate_limit_service()` e `get_history_service()`.

**Impacto:** Se o pool não foi inicializado, retorna `None` causando `AttributeError`.

---

#### **10. Trigger SQL Pode Não Funcionar** ⚠️ BAIXO

**Arquivo:** `app/db/schema.py` (linhas 82-90)

O `CREATE TRIGGER` no PostgreSQL pode falhar silenciosamente se já existir com definição diferente. Falta `CREATE OR REPLACE TRIGGER`.

---

### Riscos de Performance

#### **11. Cache sem Estratégia de Eviction** ⚠️ MÉDIO

O `MemoryCacheBackend` cresce indefinidamente se não houver expiração.

**Remediação:** Implementar LRU ou limite máximo de entradas.

---

#### **12. BFS Sem Limite de Nós Visitados** ⚠️ MÉDIO

**Arquivo:** `app/services/tracer.py`

O BFS pode visitar milhares de endereços em transações com muitos inputs (ex: consolidações de exchange).

**Remediação:** Adicionar `max_addresses_visited` como limite.

---

#### **13. PDF Gerado Sincronamente** ⚠️ BAIXO

A geração de PDF bloqueia a thread. Para relatórios grandes, pode degradar performance.

**Remediação:** Usar background task ou worker.

---

### Riscos de Manutenção

#### **14. Dois Sistemas de Autenticação Paralelos** ⚠️ ALTO

Existem dois sistemas de auth:
1. `auth_routes.py` - API Keys com bcrypt
2. `auth_jwt_routes.py` - JWT tokens

Isso causa:
- Duplicação de lógica de hash de senha
- Confusão sobre qual usar
- Manutenção duplicada

**Remediação:** Unificar em um único sistema (recomendado: manter API Keys para B2B, JWT para frontend).

---

#### **15. Docstrings e Comentários Inconsistentes** ⚠️ BAIXO

Alguns arquivos têm excelente documentação, outros quase nenhuma.

---

#### **16. Testes com URL de Produção Hardcoded** ⚠️ BAIXO

**Arquivo:** `tests/test_auth.py` (linha 6)

```python
BASE_URL = "https://web3-sentinel-production.up.railway.app/api/v1"
```

Deveria usar variável de ambiente ou fixture.

---

## 💡 Melhorias Recomendadas

### Melhorias de Segurança

| Prioridade | Melhoria | Esforço |
|------------|----------|---------|
| 🔴 Alta | Mover SECRET_KEY para env var | 15 min |
| 🔴 Alta | Restringir CORS | 30 min |
| 🔴 Alta | Remover debug_router em prod | 5 min |
| 🟡 Média | Validar path traversal em downloads | 30 min |
| 🟡 Média | Sanitizar JSONB em audit logs | 1h |
| 🟢 Baixa | Implementar rate limiting por IP | 2h |

### Melhorias de Código

| Prioridade | Melhoria | Esforço |
|------------|----------|---------|
| 🔴 Alta | Corrigir imports em auth_jwt_routes.py | 10 min |
| 🔴 Alta | Adicionar null checks em dependencies.py | 30 min |
| 🟡 Média | Unificar sistemas de autenticação | 4h |
| 🟡 Média | Adicionar type hints faltantes | 2h |
| 🟢 Baixa | Padronizar docstrings | 2h |

### Melhorias de Funcionalidade

| Prioridade | Melhoria | Esforço |
|------------|----------|---------|
| 🔴 Alta | Implementar provider fallback (Etherscan) | 8h |
| 🟡 Média | Adicionar limite de nós no BFS | 2h |
| 🟡 Média | Background task para geração de PDF | 4h |
| 🟡 Média | Webhook para notificação de análise concluída | 4h |
| 🟢 Baixa | Cache LRU para memory backend | 2h |
| 🟢 Baixa | Export de relatórios em CSV/JSON | 3h |

---

## 🗑️ Arquivos e Pastas Não Utilizados

### Pastas Vazias (Sem Funcionalidade)

| Pasta | Status | Recomendação |
|-------|--------|--------------|
| `app/static/css/` | ⚪ Vazia | Remover ou adicionar estilos CSS |
| `app/static/images/` | ⚪ Vazia | Remover ou adicionar imagens |
| `reports/` | ⚪ Vazia | Manter (PDFs são gerados aqui) |

### Arquivos com Problemas

| Arquivo | Problema | Recomendação |
|---------|----------|--------------|
| `app/api/auth_jwt_routes.py` | Imports quebrados, não funciona | Corrigir imports ou remover |
| `app/api/debug_routes.py` | Debug em produção | Condicionar ao ambiente |
| `app/middleware/monitoring.py` | Middleware não está sendo usado no main.py | Integrar ou remover |

### Código Morto / Duplicado

#### **1. MonitoringMiddleware Não Integrado**

**Arquivo:** `app/middleware/monitoring.py`

O middleware existe mas não é adicionado à aplicação em `main.py`. As classes `MetricsMiddleware` e `MetricsService` são chamadas, mas o middleware como um todo não está ativo.

**Recomendação:** Integrar no main.py ou remover se métricas são coletadas de outra forma.

---

#### **2. Método `get_optional_user` Retorna Função, Não É Usado**

**Arquivo:** `app/api/auth_middleware.py` (linhas 90-108)

```python
def get_optional_user() -> Optional[tuple[User, APIKey]]:
    async def optional_user_dependency(...):
        ...
    return optional_user_dependency  # Retorna função, não é usado em nenhum lugar
```

**Recomendação:** Remover ou implementar em rotas que precisam de auth opcional.

---

#### **3. Scripts de Teste Manuais vs Pytest**

Os scripts em `scripts/` são úteis para testes manuais, mas duplicam funcionalidade do pytest:

| Script | Pytest Equivalent |
|--------|-------------------|
| `scripts/test_trace.py` | `tests/test_api.py::TestTraceEndpoint` |
| `scripts/test_auth.py` | `tests/test_auth.py` |
| `scripts/test_endpoints.py` | `tests/test_api.py` |

**Recomendação:** Manter scripts para teste manual em produção, mas garantir que testes pytest cobrem a mesma funcionalidade.

---

#### **4. Duplicação de Hash de Senha**

A função de hash de senha está implementada em 3 lugares:

1. `app/services/auth_service.py` - `hash_password()`, `verify_password()`
2. `app/api/auth_jwt_routes.py` - `hash_password()`, `verify_password()`
3. Lógica inline em alguns lugares

**Recomendação:** Centralizar em um único módulo `app/core/security.py`.

---

### Dependências Não Utilizadas

Analisando `requirements.txt` vs uso real:

| Pacote | Status | Uso |
|--------|--------|-----|
| `aiofiles` | ⚠️ Declarado mas não importado | Remover ou usar para file I/O async |
| `psycopg[binary]` | ⚠️ Redundante | Já usa `asyncpg`, psycopg não é usado |
| `aioredis` | ⚠️ Listado em pip install | Deprecated, já usa `redis.asyncio` |

---

## 🔍 Análise Detalhada por Componente

### 1. Core (`app/core/`)

| Arquivo | Qualidade | Observações |
|---------|-----------|-------------|
| `cache.py` | ✅ Excelente | ABC bem definido com type hints |
| `provider.py` | ✅ Excelente | Interface clara para providers |
| `exceptions.py` | ✅ Boa | Hierarquia de exceções bem estruturada |

### 2. Services (`app/services/`)

| Arquivo | Qualidade | Observações |
|---------|-----------|-------------|
| `tracer.py` | ✅ Excelente | BFS implementado corretamente, bem documentado |
| `risk_scorer.py` | ✅ Boa | Fórmula de scoring clara, falta alguns edge cases |
| `pdf_generator.py` | ✅ Boa | PDF profissional, código longo mas funcional |
| `auth_service.py` | 🟡 Regular | Funcional, mas incompleto (falta list_user_api_keys) |
| `rate_limit_service.py` | ✅ Boa | Simples e efetivo |
| `history_service.py` | ✅ Boa | CRUD completo |
| `metrics_service.py` | 🟡 Regular | Básico, poderia ter mais métricas |
| `audit_logger.py` | ✅ Boa | Estruturado, suporta DB e stdout |

### 3. API (`app/api/`)

| Arquivo | Qualidade | Observações |
|---------|-----------|-------------|
| `routes.py` | ✅ Boa | Endpoints principais bem implementados |
| `auth_routes.py` | ✅ Boa | Sistema de API Key funcional |
| `auth_jwt_routes.py` | ❌ Quebrado | Imports incorretos, não funciona |
| `auth_middleware.py` | ✅ Boa | Rate limiting integrado |
| `admin_routes.py` | 🟡 Regular | Verificação de admin via is_premium (incorreto) |
| `frontend_routes.py` | ✅ Boa | Simples e funcional |
| `debug_routes.py` | ⚠️ Perigoso | Não deveria estar em produção |
| `dependencies.py` | 🟡 Regular | Singletons globais, null checks faltando |

### 4. Cache (`app/cache/`)

| Arquivo | Qualidade | Observações |
|---------|-----------|-------------|
| `redis.py` | ✅ Boa | Implementação completa |
| `postgres.py` | ✅ Boa | Fallback funcional |
| `memory.py` | ✅ Boa | Bom para desenvolvimento |

### 5. Models (`app/models/`)

| Arquivo | Qualidade | Observações |
|---------|-----------|-------------|
| `auth.py` | ✅ Excelente | Validações Pydantic robustas |
| `risk.py` | ✅ Excelente | Models claros e bem tipados |
| `blockchain.py` | ✅ Excelente | Suporta UTXO e Account-based |

### 6. Providers (`app/providers/`)

| Arquivo | Qualidade | Observações |
|---------|-----------|-------------|
| `blockchair.py` | ✅ Excelente | Rate limiting, retry, parsing robusto |

### 7. Tests (`tests/`)

| Arquivo | Cobertura | Observações |
|---------|-----------|-------------|
| `test_api.py` | 🟡 Média | Endpoints básicos testados |
| `test_cache.py` | ✅ Boa | Memory backend bem testado |
| `test_models.py` | 🟡 Média | Modelos principais testados |
| `test_risk_scorer.py` | ✅ Boa | Lógica de scoring testada |
| `test_auth.py` | ❌ Script manual | Não é pytest, é script httpx |
| `conftest.py` | 🟡 Básico | Fixtures mínimas |

**Cobertura estimada:** ~40-50%

### 8. Scripts (`scripts/`)

| Arquivo | Útil | Observações |
|---------|------|-------------|
| `create_admin.py` | ✅ Sim | Script de setup inicial |
| `init_db.py` | ✅ Sim | Inicialização do banco |
| `test_trace.py` | 🟡 Parcial | Teste manual, poderia ser pytest |
| `test_auth.py` | 🟡 Parcial | Teste manual, poderia ser pytest |
| `test_endpoints.py` | 🟡 Parcial | Teste manual |
| `verify_connections.py` | ✅ Sim | Útil para debug de infra |

---

## 📌 Conclusão

### Estado Geral do Projeto

O SafeTrace é um projeto **bem estruturado** com funcionalidades avançadas de compliance blockchain. A arquitetura está correta, os algoritmos são eficientes, e o código é geralmente de boa qualidade.

### Ações Imediatas Necessárias

1. **🔴 URGENTE:** Mover `SECRET_KEY` para variável de ambiente
2. **🔴 URGENTE:** Restringir CORS para domínios específicos
3. **🔴 URGENTE:** Desabilitar `debug_router` em produção
4. **🔴 URGENTE:** Corrigir imports em `auth_jwt_routes.py`
5. **🟡 IMPORTANTE:** Adicionar null checks em dependencies.py

### Roadmap de Melhorias Sugerido

**Fase 1 (1-2 semanas):**
- Corrigir todos os riscos de segurança críticos
- Corrigir imports quebrados
- Unificar sistema de autenticação

**Fase 2 (2-4 semanas):**
- Implementar provider fallback (Etherscan)
- Aumentar cobertura de testes para 80%+
- Adicionar limite de nós no BFS

**Fase 3 (1-2 meses):**
- Background tasks para PDF
- Webhooks de notificação
- Dashboard de métricas em tempo real

### Arquivos para Remoção/Cleanup

```
# Pastas vazias
app/static/css/
app/static/images/

# Código não funcional (corrigir ou remover)
app/api/auth_jwt_routes.py  # Corrigir imports

# Middleware não integrado
app/middleware/monitoring.py  # Integrar ou remover
```

---

**Documento gerado por análise automatizada.**  
**Recomenda-se revisão humana antes de implementar mudanças.**
