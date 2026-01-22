"""
Script para testar análise de transações blockchain
Execute: python scripts/test_trace.py
"""

import asyncio
import httpx
import sys

# URL base
BASE_URL = "https://safetrace.up.railway.app"

# Exemplos de transações reais para testar
EXAMPLES = {
    "bitcoin": {
        "tx_hash": "4d3e5b2b8f1c4b2a8e8e5b2b8f1c4b2a8e8e5b2b8f1c4b2a8e8e5b2b8f1c4b2a",
        "chain": "bitcoin"
    },
    "ethereum": {
        "tx_hash": "0x5c504ed432cb51138bcf09aa5e8a410dd4a1e204ef84bfed1be16dfba1b22060",
        "chain": "ethereum"
    },
    "simple": {
        "tx_hash": "abc123def456",
        "chain": "bitcoin"
    }
}


async def test_trace(api_key: str, example_name: str = "simple"):
    """Testa análise de transação."""
    
    example = EXAMPLES.get(example_name, EXAMPLES["simple"])
    
    print(f"\n{'='*60}")
    print(f"🔍 Testando Análise de Transação")
    print(f"{'='*60}")
    print(f"Exemplo: {example_name}")
    print(f"TX Hash: {example['tx_hash']}")
    print(f"Chain: {example['chain']}")
    print(f"{'='*60}\n")
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Fazer requisição
            response = await client.post(
                f"{BASE_URL}/api/v1/compliance/trace",
                json={
                    "tx_hash": example["tx_hash"],
                    "chain": example["chain"],
                    "depth": 3
                },
                headers={
                    "X-API-Key": api_key,
                    "Content-Type": "application/json"
                }
            )
            
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"\n✅ Análise bem-sucedida!")
                print(f"\nRelatório:")
                print(f"  - Sucesso: {data.get('success')}")
                print(f"  - Mensagem: {data.get('message')}")
                
                if data.get('report'):
                    report = data['report']
                    print(f"\n📊 Risk Report:")
                    print(f"  - Risk Score: {report.get('risk_score')}/100")
                    print(f"  - Risk Level: {report.get('risk_level')}")
                    print(f"  - Total Addresses: {report.get('total_addresses')}")
                    print(f"  - Flagged Entities: {len(report.get('flagged_entities', []))}")
                
                if data.get('pdf_url'):
                    print(f"\n📄 PDF: {data['pdf_url']}")
                
                return True
            elif response.status_code == 422:
                data = response.json()
                print(f"\n❌ Erro de validação:")
                print(f"  {data.get('detail')}")
                
                # Mostrar formato correto
                print(f"\n💡 Formato correto:")
                print(f"  {{")
                print(f'    "tx_hash": "0x123...",  // String de pelo menos 10 caracteres')
                print(f'    "chain": "bitcoin",      // Nome da blockchain')
                print(f'    "depth": 3               // Número entre 1-10')
                print(f"  }}")
                return False
            elif response.status_code == 401:
                print(f"\n❌ Não autenticado. Verifique sua API key.")
                return False
            else:
                print(f"\n❌ Erro: {response.status_code}")
                print(f"  {response.text}")
                return False
                
    except Exception as e:
        print(f"\n❌ Erro na requisição: {e}")
        return False


async def main():
    """Executa testes."""
    print(f"{'='*60}")
    print(f"🚀 SafeTrace - Teste de Análise de Transações")
    print(f"{'='*60}")
    print(f"URL Base: {BASE_URL}\n")
    
    # Solicitar API key
    print("Para testar, você precisa de uma API key.")
    print("Obtenha uma em: https://safetrace.up.railway.app/dashboard\n")
    
    api_key = input("Digite sua API key: ").strip()
    
    if not api_key:
        print("\n❌ API key não fornecida!")
        return 1
    
    # Testar exemplo simples
    success = await test_trace(api_key, "simple")
    
    if success:
        print(f"\n✅ Teste concluído com sucesso!")
        
        # Perguntar se quer testar com transação real
        test_more = input("\nDeseja testar com uma transação real do Ethereum? (s/n): ").strip().lower()
        if test_more == 's':
            await test_trace(api_key, "ethereum")
    
    return 0 if success else 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print(f"\n\nTeste interrompido pelo usuário")
        sys.exit(1)
