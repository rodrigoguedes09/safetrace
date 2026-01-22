# 🧪 Como Testar o Sistema de Autenticação

## 📋 Pré-requisitos

1. ✅ Código commitado e pushado para o GitHub
2. ✅ Railway fez redeploy (aguarde ~2 minutos)
3. ✅ PostgreSQL conectado no Railway

---

## 🚀 Opção 1: Testar Online (Railway)

### 1. Edite o script de teste:

Abra `scripts/test_endpoints.py` e mude a linha 11:

```python
# DE:
BASE_URL = "http://localhost:8000"

# PARA:
BASE_URL = "https://seu-dominio.railway.app"  # Seu domínio real
```

### 2. Execute o script:

```bash
python scripts/test_endpoints.py
```

### 3. Aguarde os resultados:

O script testará automaticamente:
- ✅ Conexão com PostgreSQL
- ✅ Registro de usuário
- ✅ Login de usuário
- ✅ Sistema JWT alternativo
- ✅ Endpoint protegido

---

## 💻 Opção 2: Testar Localmente

### 1. Configure variáveis de ambiente:

Crie arquivo `.env` na raiz do projeto:

```env
DATABASE_URL=postgresql://postgres:senha@localhost:5432/safetrace
REDIS_URL=redis://localhost:6379/0
BLOCKCHAIR_API_KEY=sua_chave_aqui
CACHE_BACKEND=redis
DEBUG=true
```

### 2. Inicie o servidor local:

```bash
uvicorn app.main:app --reload
```

### 3. Em outro terminal, execute os testes:

```bash
python scripts/test_endpoints.py
```

---

## 🌐 Opção 3: Testar via Browser/Postman

### Teste 1: Banco de Dados

Acesse no navegador:
```
https://seu-dominio.railway.app/debug/test-db
```

**Esperado:**
```json
{
  "success": true,
  "tables": ["users", "api_keys", ...],
  "has_users_table": true
}
```

### Teste 2: Registro (Postman/Insomnia)

**Endpoint:** `POST /debug/test-register`

**Body:**
```json
{
  "email": "teste@example.com",
  "full_name": "Teste User",
  "password": "Teste123!"
}
```

**Esperado:**
```json
{
  "success": true,
  "user": {
    "id": "uuid",
    "email": "teste@example.com",
    "full_name": "Teste User"
  }
}
```

### Teste 3: Login

**Endpoint:** `POST /debug/test-login?email=teste@example.com&password=Teste123!`

**Esperado:**
```json
{
  "success": true,
  "user": {...},
  "password_verified": true
}
```

### Teste 4: JWT Register (Sistema Alternativo)

**Endpoint:** `POST /auth-jwt/register`

**Body:**
```json
{
  "email": "teste2@example.com",
  "full_name": "Teste JWT",
  "password": "Teste123!"
}
```

**Esperado:**
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "user": {...}
}
```

---

## 📊 Interpretando Resultados

### ✅ Sucesso Total:
```
Total: 5/5 testes passaram
🎉 Todos os testes passaram! Sistema funcionando perfeitamente.
```

**Significa:** Tudo está funcionando! Pode usar o sistema.

---

### ❌ Falha no Teste 1 (DB):
```
❌ Conexão DB: FALHOU
```

**Problema:** PostgreSQL não conectado

**Solução:**
1. Verifique variável `DATABASE_URL` no Railway
2. Confirme que serviço PostgreSQL está rodando
3. Execute `python scripts/init_db.py`

---

### ❌ Falha no Teste 2 (Registro):
```
❌ Registro: FALHOU
Error: password cannot be longer than 72 bytes
```

**Problema:** Senha muito longa

**Solução:**
Use senha mais curta: `Teste123!` (9 caracteres)

---

### ❌ Falha no Teste 3 (Login):
```
❌ Login: FALHOU
Error: Invalid email or password
```

**Problema:** Senha não confere

**Solução:**
1. Delete o usuário e crie novamente
2. Certifique-se de usar exatamente a mesma senha
3. Teste com: `Teste123!`

---

## 🔧 Troubleshooting Rápido

### Erro: "Connection refused"
```bash
# Servidor não está rodando
# Solução: Inicie o servidor
uvicorn app.main:app --reload
```

### Erro: "Auth service not available"
```bash
# Banco não conectado
# Solução: Verifique DATABASE_URL e reinicie o servidor
```

### Erro: "User with this email already exists"
```bash
# Normal em testes repetidos
# Solução: Use outro email ou faça login
```

---

## 🎯 Próximos Passos Após Testes

### Se TODOS os testes passaram:
✅ Sistema está funcionando!
✅ Pode começar a usar na aplicação
✅ Considere usar o sistema JWT (mais simples)

### Se ALGUNS testes falharam:
1. **Anote quais testes falharam**
2. **Copie a mensagem de erro exata**
3. **Cole aqui** para que eu possa corrigir

---

## 💡 Dica Final

**Use o sistema JWT (`/auth-jwt/*`) que é mais simples:**

```javascript
// No frontend (auth.js)
const response = await fetch('/auth-jwt/login', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({email, password})
});

const {access_token, user} = await response.json();
localStorage.setItem('token', access_token);
```

**Quer que eu adapte o frontend para usar JWT?** É mais simples e funciona garantido! 🚀
