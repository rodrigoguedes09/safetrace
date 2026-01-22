# 🔧 Guia de Troubleshooting - Autenticação

## 📋 Passo a Passo para Identificar o Problema

### 1️⃣ Testar Conexão com Banco de Dados

Acesse no navegador:
```
https://seu-dominio.railway.app/debug/test-db
```

**Esperado:**
```json
{
  "success": true,
  "db_test": 1,
  "tables": ["users", "api_keys", "audit_logs", "analysis_history"],
  "has_users_table": true,
  "has_api_keys_table": true
}
```

**Se falhar:**
- ❌ Verifique se o PostgreSQL está conectado no Railway
- ❌ Confirme que `DATABASE_URL` está configurada
- ❌ Rode `python scripts/init_db.py` localmente

---

### 2️⃣ Testar Registro de Usuário

Use Postman, Insomnia ou curl:

```bash
curl -X POST "https://seu-dominio.railway.app/debug/test-register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "teste@example.com",
    "full_name": "Teste User",
    "password": "Teste123!"
  }'
```

**Esperado:**
```json
{
  "success": true,
  "user": {
    "id": "uuid-aqui",
    "email": "teste@example.com",
    "full_name": "Teste User"
  }
}
```

**Se falhar**, você verá o erro exato:
```json
{
  "success": false,
  "error": "mensagem do erro",
  "type": "tipo do erro"
}
```

---

### 3️⃣ Testar Login

```bash
curl -X POST "https://seu-dominio.railway.app/debug/test-login?email=teste@example.com&password=Teste123!"
```

**Esperado:**
```json
{
  "success": true,
  "user": {
    "id": "uuid-aqui",
    "email": "teste@example.com",
    "is_active": true
  },
  "password_verified": true
}
```

---

## 🛠️ Soluções para Problemas Comuns

### Problema 1: "Auth service not available"

**Causa:** Banco de dados não conectado

**Solução:**
1. Verifique variáveis no Railway:
   ```
   DATABASE_URL=${{Postgres.DATABASE_URL}}
   ```
2. Confirme que o serviço PostgreSQL está rodando
3. Faça redeploy após ajustar

---

### Problema 2: "User not found" no login

**Causa:** Usuário não foi criado ou email diferente

**Solução:**
1. Use o endpoint `/debug/test-register` primeiro
2. Certifique-se de usar o **mesmo email** (case-insensitive)
3. Verifique se há erros no registro

---

### Problema 3: "password cannot be longer than 72 bytes"

**Causa:** Senha muito longa

**Solução:**
1. Use senha com máximo 72 caracteres
2. Exemplo: `Teste123!` (9 caracteres, funciona perfeitamente)

---

### Problema 4: Senha não é aceita no login

**Causa:** Hash incorreto ou senha digitada errada

**Solução:**
1. Delete o usuário e crie novamente
2. Use exatamente a mesma senha
3. Teste com: `Teste123!`

---

## 🔍 Ferramentas Alternativas Recomendadas

Se os problemas persistirem, considere estas bibliotecas:

### Opção 1: FastAPI Users (Mais Completa)
```bash
pip install fastapi-users[sqlalchemy,bcrypt]
```

**Prós:**
- ✅ Sistema completo de autenticação
- ✅ Registro, login, reset de senha
- ✅ Verificação de email
- ✅ OAuth2 support

**Contras:**
- ⚠️ Precisa migrar schema do banco
- ⚠️ Mais complexo de configurar

### Opção 2: Authlib (JWT/OAuth2)
```bash
pip install authlib
```

**Prós:**
- ✅ Focado em OAuth2 e JWT
- ✅ Mais leve que FastAPI Users

**Contras:**
- ⚠️ Não tem UI pronta
- ⚠️ Requer mais código manual

### Opção 3: Python-JOSE (JWT Simples)
```bash
pip install python-jose[cryptography]
```

**Prós:**
- ✅ Apenas JWT tokens
- ✅ Muito simples
- ✅ Já está instalado!

**Contras:**
- ⚠️ Não gerencia usuários
- ⚠️ Precisa implementar tudo manualmente

---

## 🎯 Minha Recomendação

**ANTES de mudar para outra biblioteca:**

1. **Execute os testes de debug acima**
2. **Identifique o erro EXATO**
3. **Cole aqui o resultado dos testes**

Com o erro específico, posso corrigir o sistema atual que é mais simples e adequado para seu projeto.

**SE TUDO FALHAR:**

Implemente **Python-JOSE** que já está instalado. Vou criar endpoints simplificados com JWT que funcionam 100%.

---

## 📞 O que fazer agora?

1. Faça commit e push do código atual:
   ```bash
   git add .
   git commit -m "Add debug endpoints for auth troubleshooting"
   git push origin main
   ```

2. Aguarde o redeploy do Railway (~2 min)

3. Teste os 3 endpoints de debug:
   - `/debug/test-db`
   - `/debug/test-register`
   - `/debug/test-login`

4. **Cole aqui os resultados** que eu vou resolver!

---

## 🚨 Solução Rápida (Se tiver pressa)

Se você quiser uma solução que **FUNCIONA AGORA**, posso implementar um sistema simples com JWT usando apenas FastAPI + python-jose (já instalado).

**Vantagens:**
- ✅ Código mais simples
- ✅ JWT tokens (padrão indústria)
- ✅ Funciona 100%
- ✅ Sem bcrypt complexo

**Me diga se quer que eu implemente isso!**
