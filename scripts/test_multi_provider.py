"""Test script for MultiProvider with Bitcoin analysis."""

import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.providers.blockchair import BlockchairProvider
from app.providers.blockchain_com import BlockchainComProvider
from app.providers.multi_provider import MultiProviderManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def test_multi_provider():
    """Test the multi-provider manager with Bitcoin transactions."""
    
    # Create providers
    blockchair = BlockchairProvider()  # No API key, limited but works
    blockchain_com = BlockchainComProvider()
    
    # Create multi-provider
    provider = MultiProviderManager(
        blockchair_provider=blockchair,
        blockchain_com_provider=blockchain_com,
    )
    
    print("\n" + "=" * 70)
    print("MULTI-PROVIDER MANAGER TEST")
    print("=" * 70)
    
    # Test 1: Health Check
    print("\n[Test 1] Health Check (All Providers)")
    print("-" * 50)
    try:
        health = await provider.health_check()
        print(f"Overall Status: {health.get('status')}")
        print(f"Total Requests: {health.get('total_request_count')}")
        for name, status in health.get('providers', {}).items():
            print(f"  - {name}: {status.get('status')}")
        print("✓ Health check passed!")
    except Exception as e:
        print(f"✗ Health check failed: {e}")
    
    # Test 2: Bitcoin Transaction via Blockchain.com
    print("\n[Test 2] Bitcoin Transaction (should use Blockchain.com)")
    print("-" * 50)
    try:
        tx = await provider.get_transaction(
            chain="bitcoin",
            tx_hash="a1075db55d416d3ca199f55b6084e2115b9345e16c5cf302fc80e9d5fbf5d48d",
        )
        print(f"Provider Used: {provider._get_provider_for_chain('bitcoin').name}")
        print(f"TX Hash: {tx.tx_hash[:32]}...")
        print(f"Inputs: {len(tx.inputs)}")
        print(f"Outputs: {len(tx.outputs)}")
        print("✓ Bitcoin transaction fetch passed!")
    except Exception as e:
        print(f"✗ Bitcoin transaction fetch failed: {e}")
    
    # Test 3: Bitcoin Address Metadata
    print("\n[Test 3] Bitcoin Address Metadata")
    print("-" * 50)
    try:
        metadata = await provider.get_address_metadata(
            chain="bitcoin",
            address="1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
        )
        print(f"Address: {metadata.address[:30]}...")
        print(f"Balance: {metadata.balance} BTC")
        print(f"TX Count: {metadata.tx_count}")
        print("✓ Bitcoin address metadata passed!")
    except Exception as e:
        print(f"✗ Bitcoin address metadata failed: {e}")
    
    # Test 4: Address Transaction History (unique to Blockchain.com)
    print("\n[Test 4] Address Transaction History (Blockchain.com Feature)")
    print("-" * 50)
    try:
        transactions = await provider.get_address_transactions(
            chain="bitcoin",
            address="1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
            limit=5
        )
        print(f"Found {len(transactions)} transactions")
        for tx in transactions[:3]:
            print(f"  TX: {tx.tx_hash[:32]}...")
        print("✓ Address transaction history passed!")
    except Exception as e:
        print(f"✗ Address transaction history failed: {e}")
    
    # Test 5: UTXOs (Blockchain.com Feature)
    print("\n[Test 5] Unspent Outputs (UTXOs)")
    print("-" * 50)
    try:
        utxos = await provider.get_unspent_outputs(
            chain="bitcoin",
            address="1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"
        )
        print(f"Found {len(utxos)} UTXOs")
        print("✓ UTXOs fetch passed!")
    except Exception as e:
        print(f"✗ UTXOs fetch failed: {e}")
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("-" * 50)
    print(f"Total API Calls: {provider.get_request_count()}")
    print(f"Blockchair Calls: {blockchair.get_request_count()}")
    print(f"Blockchain.com Calls: {blockchain_com.get_request_count()}")
    print("\nProvider Selection:")
    print(f"  - Bitcoin: {provider._get_provider_for_chain('bitcoin').name}")
    print(f"  - Ethereum: {provider._get_provider_for_chain('ethereum').name}")
    print(f"  - Litecoin: {provider._get_provider_for_chain('litecoin').name}")
    print("=" * 70)
    
    # Cleanup
    await provider.close()


if __name__ == "__main__":
    asyncio.run(test_multi_provider())
