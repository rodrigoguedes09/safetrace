"""
Script para testar o sistema de autenticação
Execute: python scripts/test_auth.py
"""

import asyncio
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import get_settings
from app.services.auth_service import AuthService
from app.models.auth import UserCreate, APIKeyCreate


async def test_auth():
    """Test authentication system."""
    try:
        import asyncpg
        settings = get_settings()
        
        print("=" * 60)
        print("🔐 SafeTrace - Teste de Autenticação")
        print("=" * 60)
        
        print(f"\n🔗 Conectando ao PostgreSQL...")
        
        # Create connection pool
        pool = await asyncpg.create_pool(
            settings.postgres_dsn,
            min_size=1,
            max_size=2,
            timeout=10
        )
        
        print("   ✅ Conexão estabelecida\n")
        
        # Initialize auth service
        auth_service = AuthService(pool)
        
        # Test 1: Create user
        print("📝 Teste 1: Criar usuário")
        print("-" * 60)
        
        test_email = "teste@safetrace.com"
        test_password = "Teste123!"
        
        try:
            user_data = UserCreate(
                email=test_email,
                full_name="Usuário Teste",
                password=test_password
            )
            
            user = await auth_service.create_user(user_data)
            print(f"   ✅ Usuário criado: {user.email}")
            print(f"   📧 Email: {user.email}")
            print(f"   👤 Nome: {user.full_name}")
            print(f"   🆔 ID: {user.id}")
            
        except ValueError as e:
            if "already exists" in str(e):
                print(f"   ℹ️  Usuário já existe (normal em testes repetidos)")
                user_in_db = await auth_service.get_user_by_email(test_email)
                user = await auth_service.get_user_by_id(user_in_db.id)
            else:
                raise
        
        # Test 2: Verify password
        print(f"\n🔑 Teste 2: Verificar senha")
        print("-" * 60)
        
        user_in_db = await auth_service.get_user_by_email(test_email)
        
        # Test correct password
        is_valid = auth_service.verify_password(test_password, user_in_db.hashed_password)
        if is_valid:
            print("   ✅ Senha correta verificada com sucesso")
        else:
            print("   ❌ ERRO: Senha correta não foi aceita!")
        
        # Test wrong password
        is_valid = auth_service.verify_password("SenhaErrada123!", user_in_db.hashed_password)
        if not is_valid:
            print("   ✅ Senha incorreta rejeitada corretamente")
        else:
            print("   ❌ ERRO: Senha incorreta foi aceita!")
        
        # Test 3: Create API key
        print(f"\n🔐 Teste 3: Criar API key")
        print("-" * 60)
        
        key_data = APIKeyCreate(
            name="Test Key",
            description="Created by test script"
        )
        
        api_key, plain_key = await auth_service.create_api_key(user.id, key_data)
        print(f"   ✅ API Key criada")
        print(f"   🔑 Key: {plain_key}")
        print(f"   📌 Prefix: {api_key.key_prefix}")
        print(f"   📝 Nome: {api_key.name}")
        
        # Test 4: Verify API key
        print(f"\n✅ Teste 4: Verificar API key")
        print("-" * 60)
        
        result = await auth_service.verify_api_key(plain_key)
        if result:
            verified_user, verified_key = result
            print(f"   ✅ API Key válida")
            print(f"   👤 Usuário: {verified_user.email}")
            print(f"   🔑 Key ID: {verified_key.id}")
        else:
            print("   ❌ ERRO: API Key não foi verificada!")
        
        # Test wrong key
        result = await auth_service.verify_api_key("sk_invalid_key_12345678901234567890")
        if not result:
            print("   ✅ API Key inválida rejeitada corretamente")
        else:
            print("   ❌ ERRO: API Key inválida foi aceita!")
        
        # Test 5: Long password (bcrypt limit)
        print(f"\n📏 Teste 5: Senha longa (limite bcrypt)")
        print("-" * 60)
        
        long_password = "A" * 80 + "1a"  # 82 caracteres
        
        try:
            user_data = UserCreate(
                email="teste.longo@safetrace.com",
                full_name="Teste Senha Longa",
                password=long_password
            )
            print("   ❌ ERRO: Senha muito longa foi aceita!")
        except ValueError as e:
            if "72 bytes" in str(e):
                print(f"   ✅ Senha muito longa rejeitada: {e}")
            else:
                print(f"   ℹ️  Erro de validação: {e}")
        
        # Test 6: Weak password
        print(f"\n🔒 Teste 6: Senha fraca")
        print("-" * 60)
        
        weak_passwords = [
            ("semNumero", "sem dígito"),
            ("semminuscula1", "sem maiúscula"),
            ("SEMMAIUSCULA1", "sem minúscula"),
            ("Curta1", "muito curta (< 8 chars)"),
        ]
        
        for weak_pass, reason in weak_passwords:
            try:
                user_data = UserCreate(
                    email=f"teste.{weak_pass}@safetrace.com",
                    full_name="Teste Senha Fraca",
                    password=weak_pass
                )
                print(f"   ❌ ERRO: Senha fraca aceita ({reason})")
            except ValueError as e:
                print(f"   ✅ Senha fraca rejeitada ({reason})")
        
        await pool.close()
        
        print("\n" + "=" * 60)
        print("🎉 Todos os testes concluídos!")
        print("=" * 60)
        
        print("\n💡 Teste manual:")
        print(f"   Email: {test_email}")
        print(f"   Senha: {test_password}")
        print(f"   API Key: {plain_key}")
        print()
        
        return 0
        
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(test_auth())
    sys.exit(exit_code)
