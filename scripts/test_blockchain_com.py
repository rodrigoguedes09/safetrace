"""Test script for Blockchain.com API provider."""

import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.providers.blockchain_com import BlockchainComProvider

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def test_blockchain_com_provider():
    """Test the Blockchain.com provider with real Bitcoin transactions."""
    
    provider = BlockchainComProvider()
    
    # Famous Bitcoin transactions to test
    test_cases = [
        {
            "name": "Bitcoin Pizza Transaction (2010)",
            "tx_hash": "a1075db55d416d3ca199f55b6084e2115b9345e16c5cf302fc80e9d5fbf5d48d",
            "chain": "bitcoin",
        },
        {
            "name": "Recent Bitcoin Transaction",
            "tx_hash": "5e8d8e0e5b8d0e5b8d0e5b8d0e5b8d0e5b8d0e5b8d0e5b8d0e5b8d0e5b8d0e5b",  # Example
            "chain": "bitcoin",
        },
    ]
    
    print("\n" + "=" * 70)
    print("BLOCKCHAIN.COM API PROVIDER TEST")
    print("=" * 70)
    
    # Test 1: Health Check
    print("\n[Test 1] Health Check")
    print("-" * 50)
    try:
        health = await provider.health_check()
        print(f"Status: {health.get('status')}")
        print(f"Latest Block: {health.get('latest_block')}")
        print("✓ Health check passed!")
    except Exception as e:
        print(f"✗ Health check failed: {e}")
    
    # Test 2: Fetch Transaction
    print("\n[Test 2] Fetch Bitcoin Pizza Transaction")
    print("-" * 50)
    try:
        tx = await provider.get_transaction(
            chain="bitcoin",
            tx_hash="a1075db55d416d3ca199f55b6084e2115b9345e16c5cf302fc80e9d5fbf5d48d",
        )
        print(f"TX Hash: {tx.tx_hash[:32]}...")
        print(f"Block Height: {tx.block_height}")
        print(f"Timestamp: {tx.timestamp}")
        print(f"Inputs: {len(tx.inputs)}")
        print(f"Outputs: {len(tx.outputs)}")
        print(f"Fee: {tx.fee} BTC")
        
        total_value = sum(out.value for out in tx.outputs)
        print(f"Total Output Value: {total_value} BTC")
        
        print("\nInputs:")
        for i, inp in enumerate(tx.inputs[:5]):  # Show first 5
            print(f"  {i+1}. {inp.address[:20] if inp.address else 'unknown'}... - {inp.value} BTC")
        
        print("\nOutputs:")
        for i, out in enumerate(tx.outputs[:5]):  # Show first 5
            print(f"  {i+1}. {out.address[:20] if out.address else 'unknown'}... - {out.value} BTC")
        
        print("✓ Transaction fetch passed!")
    except Exception as e:
        print(f"✗ Transaction fetch failed: {e}")
    
    # Test 3: Get Transaction Inputs
    print("\n[Test 3] Get Transaction Inputs (UTXO tracing)")
    print("-" * 50)
    try:
        inputs = await provider.get_transaction_inputs(
            chain="bitcoin",
            tx_hash="a1075db55d416d3ca199f55b6084e2115b9345e16c5cf302fc80e9d5fbf5d48d",
        )
        print(f"Found {len(inputs)} input transactions")
        for addr, prev_tx in inputs[:5]:
            print(f"  Address: {addr[:20]}... -> TX: {prev_tx[:20] if prev_tx else 'N/A'}...")
        print("✓ Transaction inputs fetch passed!")
    except Exception as e:
        print(f"✗ Transaction inputs fetch failed: {e}")
    
    # Test 4: Get Address Metadata
    print("\n[Test 4] Get Address Metadata")
    print("-" * 50)
    try:
        # Satoshi's known address
        address = "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"  # Genesis block coinbase
        metadata = await provider.get_address_metadata("bitcoin", address)
        print(f"Address: {metadata.address[:30]}...")
        print(f"Balance: {metadata.balance} BTC")
        print(f"TX Count: {metadata.tx_count}")
        print(f"First Seen: {metadata.first_seen}")
        print(f"Last Seen: {metadata.last_seen}")
        print(f"Tags: {[tag.value for tag in metadata.tags] if metadata.tags else 'None'}")
        print("✓ Address metadata fetch passed!")
    except Exception as e:
        print(f"✗ Address metadata fetch failed: {e}")
    
    # Test 5: Get Address Transaction History (KEY FEATURE!)
    print("\n[Test 5] Get Address Transaction History")
    print("-" * 50)
    try:
        address = "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"
        transactions = await provider.get_address_transactions("bitcoin", address, limit=5)
        print(f"Found {len(transactions)} transactions")
        for tx in transactions[:3]:
            print(f"  TX: {tx.tx_hash[:32]}... Block: {tx.block_height}")
        print("✓ Address transaction history fetch passed!")
    except Exception as e:
        print(f"✗ Address transaction history fetch failed: {e}")
    
    # Test 6: Get UTXOs
    print("\n[Test 6] Get Unspent Outputs (UTXOs)")
    print("-" * 50)
    try:
        # This address might not have UTXOs, but we test the API
        address = "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"
        utxos = await provider.get_unspent_outputs("bitcoin", address)
        print(f"Found {len(utxos)} UTXOs")
        for utxo in utxos[:3]:
            value = int(utxo.get("value", 0)) / 1e8
            print(f"  TX: {utxo.get('tx_hash', 'unknown')[:20]}... Value: {value} BTC")
        print("✓ UTXO fetch passed!")
    except Exception as e:
        print(f"✗ UTXO fetch failed: {e}")
    
    # Summary
    print("\n" + "=" * 70)
    print(f"TOTAL API CALLS: {provider.get_request_count()}")
    print("=" * 70)
    
    # Cleanup
    await provider.close()


if __name__ == "__main__":
    asyncio.run(test_blockchain_com_provider())
