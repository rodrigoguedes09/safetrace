"""
Script de verificação de conexões Redis e PostgreSQL
Execute: python scripts/verify_connections.py
"""

import asyncio
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import get_settings


async def verify_redis():
    """Verify Redis connection."""
    try:
        import redis.asyncio as redis
        settings = get_settings()
        
        print("\n🔍 Testando conexão Redis...")
        print(f"   URL: {settings.redis_url}")
        
        client = redis.from_url(settings.redis_url, decode_responses=True)
        
        # Test ping
        await client.ping()
        print("   ✅ Redis: Conexão OK")
        
        # Test set/get
        await client.set("test_key", "test_value", ex=10)
        value = await client.get("test_key")
        
        if value == "test_value":
            print("   ✅ Redis: Read/Write OK")
        else:
            print("   ❌ Redis: Read/Write FALHOU")
            
        await client.close()
        return True
        
    except Exception as e:
        print(f"   ❌ Redis: ERRO - {e}")
        return False


async def verify_postgres():
    """Verify PostgreSQL connection."""
    try:
        import asyncpg
        settings = get_settings()
        
        print("\n🔍 Testando conexão PostgreSQL...")
        print(f"   URL: {settings.postgres_dsn[:50]}...")
        
        # Create connection pool
        pool = await asyncpg.create_pool(
            settings.postgres_dsn,
            min_size=1,
            max_size=2,
            timeout=10
        )
        
        async with pool.acquire() as conn:
            # Test query
            version = await conn.fetchval("SELECT version()")
            print(f"   ✅ PostgreSQL: Conexão OK")
            print(f"   📌 Versão: {version[:60]}...")
            
            # Check if tables exist
            tables = await conn.fetch("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            
            table_names = [row['table_name'] for row in tables]
            
            print(f"\n   📋 Tabelas encontradas: {len(table_names)}")
            expected_tables = ['users', 'api_keys', 'audit_logs', 'analysis_history']
            
            for table in expected_tables:
                if table in table_names:
                    print(f"      ✅ {table}")
                else:
                    print(f"      ❌ {table} (não encontrada)")
        
        await pool.close()
        return True
        
    except Exception as e:
        print(f"   ❌ PostgreSQL: ERRO - {e}")
        return False


async def verify_blockchair():
    """Verify Blockchair API key."""
    try:
        settings = get_settings()
        
        print("\n🔍 Verificando API Key Blockchair...")
        
        if not settings.blockchair_api_key.get_secret_value():
            print("   ⚠️  BLOCKCHAIR_API_KEY não configurada")
            return False
        
        print(f"   ✅ API Key: {settings.blockchair_api_key.get_secret_value()[:12]}...")
        
        # Test API call
        import httpx
        url = f"{settings.blockchair_base_url}/bitcoin/dashboards/transaction/latest"
        params = {"key": settings.blockchair_api_key.get_secret_value()}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                print("   ✅ Blockchair API: Funcionando")
                return True
            else:
                print(f"   ❌ Blockchair API: Status {response.status_code}")
                return False
                
    except Exception as e:
        print(f"   ❌ Blockchair: ERRO - {e}")
        return False


async def main():
    """Run all verification checks."""
    print("=" * 60)
    print("🚀 SafeTrace - Verificação de Conexões")
    print("=" * 60)
    
    results = {
        'redis': await verify_redis(),
        'postgres': await verify_postgres(),
        'blockchair': await verify_blockchair()
    }
    
    print("\n" + "=" * 60)
    print("📊 RESUMO")
    print("=" * 60)
    
    for service, ok in results.items():
        status = "✅ OK" if ok else "❌ FALHOU"
        print(f"{service.upper():15} {status}")
    
    all_ok = all(results.values())
    
    if all_ok:
        print("\n🎉 Todas as conexões estão funcionando!")
        return 0
    else:
        print("\n⚠️  Algumas conexões falharam. Verifique as configurações.")
        print("\n💡 Dicas:")
        
        if not results['redis']:
            print("   - Redis: Verifique se a variável REDIS_URL está correta")
            print("   - Railway: Adicione o serviço Redis ao projeto")
        
        if not results['postgres']:
            print("   - PostgreSQL: Verifique se DATABASE_URL está correta")
            print("   - Railway: Adicione o serviço PostgreSQL ao projeto")
            print("   - Execute migrations: python scripts/init_db.py")
        
        if not results['blockchair']:
            print("   - Blockchair: Adicione BLOCKCHAIR_API_KEY ao .env")
            print("   - Obtenha uma chave em: https://blockchair.com/api")
        
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
