"""
Script para testar os endpoints de autenticação localmente
Execute: python scripts/test_endpoints.py
"""

import asyncio
import httpx
import sys

# URL base (altere para seu domínio Railway após deploy)
# BASE_URL = "http://localhost:8001"  # Testando localmente
BASE_URL = "https://safetrace.up.railway.app"  # Testando no Railway

# Cores para output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'


def print_test(name: str):
    """Imprime o nome do teste."""
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}🧪 {name}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")


def print_success(message: str):
    """Imprime mensagem de sucesso."""
    print(f"{GREEN}✅ {message}{RESET}")


def print_error(message: str):
    """Imprime mensagem de erro."""
    print(f"{RED}❌ {message}{RESET}")


def print_info(message: str):
    """Imprime mensagem informativa."""
    print(f"{YELLOW}ℹ️  {message}{RESET}")


async def test_db_connection():
    """Testa conexão com o banco de dados."""
    print_test("Teste 1: Conexão com Banco de Dados")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{BASE_URL}/debug/test-db")
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("success"):
                    print_success("Conexão com PostgreSQL OK")
                    print_info(f"Tabelas encontradas: {len(data.get('tables', []))}")
                    
                    if data.get('has_users_table'):
                        print_success("Tabela 'users' existe")
                    else:
                        print_error("Tabela 'users' não encontrada")
                    
                    if data.get('has_api_keys_table'):
                        print_success("Tabela 'api_keys' existe")
                    else:
                        print_error("Tabela 'api_keys' não encontrada")
                    
                    return True
                else:
                    print_error(f"Falha na conexão: {data.get('error')}")
                    return False
            else:
                print_error(f"Status {response.status_code}: {response.text}")
                return False
                
    except httpx.ConnectError:
        print_error("Não foi possível conectar ao servidor")
        print_info("Certifique-se de que o servidor está rodando:")
        print_info("  uvicorn app.main:app --reload")
        return False
    except Exception as e:
        print_error(f"Erro: {e}")
        return False


async def test_register():
    """Testa registro de usuário."""
    print_test("Teste 2: Registro de Usuário")
    
    test_user = {
        "email": "teste@example.com",
        "full_name": "Teste User",
        "password": "Teste123!"
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{BASE_URL}/debug/test-register",
                json=test_user
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("success"):
                    print_success("Usuário criado com sucesso")
                    user = data.get("user", {})
                    print_info(f"ID: {user.get('id')}")
                    print_info(f"Email: {user.get('email')}")
                    print_info(f"Nome: {user.get('full_name')}")
                    return True, test_user
                else:
                    error = data.get("error", "Unknown error")
                    if "already exists" in error.lower():
                        print_info("Usuário já existe (normal em testes repetidos)")
                        return True, test_user
                    else:
                        print_error(f"Erro ao criar usuário: {error}")
                        print_info(f"Tipo: {data.get('type')}")
                        return False, test_user
            else:
                print_error(f"Status {response.status_code}: {response.text}")
                return False, test_user
                
    except Exception as e:
        print_error(f"Erro: {e}")
        return False, test_user


async def test_login(email: str, password: str):
    """Testa login de usuário."""
    print_test("Teste 3: Login de Usuário")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{BASE_URL}/debug/test-login",
                params={"email": email, "password": password}
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("success"):
                    print_success("Login bem-sucedido")
                    user = data.get("user", {})
                    print_info(f"ID: {user.get('id')}")
                    print_info(f"Email: {user.get('email')}")
                    print_info(f"Ativo: {user.get('is_active')}")
                    return True
                else:
                    print_error(f"Login falhou: {data.get('error')}")
                    return False
            else:
                print_error(f"Status {response.status_code}: {response.text}")
                return False
                
    except Exception as e:
        print_error(f"Erro: {e}")
        return False


async def test_jwt_register():
    """Testa registro JWT."""
    print_test("Teste 4: Registro JWT (Sistema Alternativo)")
    
    test_user = {
        "email": "teste.jwt@example.com",
        "full_name": "Teste JWT User",
        "password": "Teste123!"
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{BASE_URL}/auth-jwt/register",
                json=test_user
            )
            
            if response.status_code == 200:
                data = response.json()
                print_success("Registro JWT bem-sucedido")
                print_info(f"Token: {data.get('access_token', '')[:50]}...")
                print_info(f"Email: {data.get('user', {}).get('email')}")
                return True, data.get('access_token')
            elif response.status_code == 409:
                print_info("Usuário já existe (normal em testes repetidos)")
                # Tenta fazer login
                response = await client.post(
                    f"{BASE_URL}/auth-jwt/login",
                    json={"email": test_user["email"], "password": test_user["password"]}
                )
                if response.status_code == 200:
                    data = response.json()
                    print_success("Login JWT bem-sucedido")
                    return True, data.get('access_token')
                return False, None
            else:
                data = response.json()
                print_error(f"Status {response.status_code}: {data.get('detail')}")
                return False, None
                
    except Exception as e:
        print_error(f"Erro: {e}")
        return False, None


async def test_jwt_protected(token: str):
    """Testa endpoint protegido JWT."""
    print_test("Teste 5: Acesso a Endpoint Protegido (JWT)")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{BASE_URL}/auth-jwt/me",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            if response.status_code == 200:
                data = response.json()
                print_success("Acesso autorizado")
                print_info(f"Email: {data.get('email')}")
                print_info(f"Nome: {data.get('full_name')}")
                print_info(f"Premium: {data.get('is_premium')}")
                return True
            else:
                print_error(f"Status {response.status_code}: {response.text}")
                return False
                
    except Exception as e:
        print_error(f"Erro: {e}")
        return False


async def main():
    """Executa todos os testes."""
    print(f"{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}🚀 SafeTrace - Teste de Autenticação{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")
    print(f"\n{YELLOW}URL Base: {BASE_URL}{RESET}\n")
    
    results = []
    
    # Teste 1: Banco de dados
    db_ok = await test_db_connection()
    results.append(("Conexão DB", db_ok))
    
    if not db_ok:
        print_error("\n⚠️  Banco de dados não conectado. Verifique:")
        print_info("  1. PostgreSQL está rodando no Railway?")
        print_info("  2. DATABASE_URL está configurada?")
        print_info("  3. Tabelas foram criadas? (python scripts/init_db.py)")
        return 1
    
    # Teste 2: Registro
    register_ok, test_user = await test_register()
    results.append(("Registro", register_ok))
    
    # Teste 3: Login
    if register_ok:
        login_ok = await test_login(test_user["email"], test_user["password"])
        results.append(("Login", login_ok))
    else:
        print_info("\nPulando teste de login (registro falhou)")
        results.append(("Login", False))
    
    # Teste 4: JWT Register
    jwt_ok, token = await test_jwt_register()
    results.append(("JWT Registro", jwt_ok))
    
    # Teste 5: JWT Protected
    if jwt_ok and token:
        jwt_protected_ok = await test_jwt_protected(token)
        results.append(("JWT Protegido", jwt_protected_ok))
    else:
        print_info("\nPulando teste JWT protegido (registro JWT falhou)")
        results.append(("JWT Protegido", False))
    
    # Resumo
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}📊 RESUMO DOS TESTES{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")
    
    for name, result in results:
        status = f"{GREEN}✅ PASSOU{RESET}" if result else f"{RED}❌ FALHOU{RESET}"
        print(f"  {name:20} {status}")
    
    total = len(results)
    passed = sum(1 for _, r in results if r)
    
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}Total: {passed}/{total} testes passaram{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")
    
    if passed == total:
        print_success("🎉 Todos os testes passaram! Sistema funcionando perfeitamente.")
        return 0
    else:
        print_error(f"⚠️  {total - passed} teste(s) falharam. Veja os detalhes acima.")
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Testes interrompidos pelo usuário{RESET}")
        sys.exit(1)
