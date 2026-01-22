"""
Script para inicializar o banco de dados PostgreSQL
Execute: python scripts/init_db.py
"""

import asyncio
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import get_settings
from app.db.schema import INIT_SCHEMA


async def init_database():
    """Initialize database tables."""
    try:
        import asyncpg
        settings = get_settings()
        
        print("=" * 60)
        print("🗄️  SafeTrace - Inicialização do Banco de Dados")
        print("=" * 60)
        
        print(f"\n🔗 Conectando ao PostgreSQL...")
        print(f"   URL: {settings.postgres_dsn[:50]}...")
        
        # Create connection
        conn = await asyncpg.connect(settings.postgres_dsn)
        
        print("   ✅ Conexão estabelecida\n")
        
        print("📝 Executando schema SQL...")
        print("-" * 60)
        
        # Execute schema
        await conn.execute(INIT_SCHEMA)
        
        print("✅ Schema executado com sucesso!\n")
        
        # Verify tables
        tables = await conn.fetch("""
            SELECT table_name, 
                   (SELECT COUNT(*) FROM information_schema.columns 
                    WHERE table_name = t.table_name 
                    AND table_schema = 'public') as column_count
            FROM information_schema.tables t
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        
        print("📋 Tabelas criadas:")
        print("-" * 60)
        
        for row in tables:
            table_name = row['table_name']
            col_count = row['column_count']
            print(f"   ✅ {table_name:25} ({col_count} colunas)")
        
        # Verify indexes
        indexes = await conn.fetch("""
            SELECT tablename, indexname
            FROM pg_indexes
            WHERE schemaname = 'public'
            ORDER BY tablename, indexname
        """)
        
        print(f"\n📊 Índices criados: {len(indexes)}")
        print("-" * 60)
        
        current_table = None
        for row in indexes:
            table = row['tablename']
            index = row['indexname']
            
            if table != current_table:
                print(f"\n   {table}:")
                current_table = table
            
            print(f"      • {index}")
        
        await conn.close()
        
        print("\n" + "=" * 60)
        print("🎉 Banco de dados inicializado com sucesso!")
        print("=" * 60)
        
        print("\n💡 Próximos passos:")
        print("   1. Registre um usuário: POST /auth/register")
        print("   2. Crie uma API key: POST /auth/bootstrap")
        print("   3. Teste uma análise: POST /api/v1/trace")
        print()
        
        return 0
        
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        print("\n💡 Dicas:")
        print("   - Verifique se o PostgreSQL está rodando")
        print("   - Confirme que DATABASE_URL está correta no .env")
        print("   - No Railway, verifique se o serviço PostgreSQL foi adicionado")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(init_database())
    sys.exit(exit_code)
