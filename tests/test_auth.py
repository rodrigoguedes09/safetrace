"""Test script for authentication system."""

import asyncio
import httpx

BASE_URL = "https://web3-sentinel-production.up.railway.app/api/v1"


async def test_authentication():
    """Test complete authentication flow."""
    async with httpx.AsyncClient() as client:
        print("🧪 Testing SafeTrace Authentication System\n")
        print("=" * 60)

        # 1. Register a new user
        print("\n1️⃣  Registering new user...")
        register_data = {
            "email": "test@safetrace.com",
            "full_name": "Test User",
            "password": "SecurePass123",
        }

        try:
            response = await client.post(
                f"{BASE_URL}/auth/register", json=register_data
            )
            response.raise_for_status()
            user = response.json()
            print(f"✅ User registered: {user['email']} (ID: {user['id']})")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 400:
                print("⚠️  User already exists, continuing...")
                user = {"email": register_data["email"]}
            else:
                print(f"❌ Registration failed: {e}")
                return

        # 2. Create first API key (manually for now)
        print("\n2️⃣  Creating API key...")
        print("   Note: For first key, you need to:")
        print("   - Use database access to insert initial key, or")
        print("   - Create a special endpoint for initial setup")
        print("")
        print("   For production, create via database:")
        print(f"   INSERT INTO api_keys (user_id, name, hashed_key, key_prefix)")
        print("   VALUES ('{user_id}', 'Initial', '{hashed}', 'sk_test...')")

        # For testing, you would provide an initial API key
        api_key = input("\n   Enter API key to continue tests: ").strip()

        if not api_key:
            print("\n⚠️  No API key provided. Skipping authenticated tests.")
            return

        # 3. Get current user info
        print("\n3️⃣  Getting current user info...")
        try:
            response = await client.get(
                f"{BASE_URL}/auth/me", headers={"X-API-Key": api_key}
            )
            response.raise_for_status()
            user_info = response.json()
            print(f"✅ Authenticated as: {user_info['email']}")
            print(f"   Premium: {user_info['is_premium']}")
        except httpx.HTTPStatusError as e:
            print(f"❌ Auth failed: {e}")
            return

        # 4. Check rate limit
        print("\n4️⃣  Checking rate limit...")
        try:
            response = await client.get(
                f"{BASE_URL}/auth/rate-limit", headers={"X-API-Key": api_key}
            )
            response.raise_for_status()
            rate_info = response.json()
            print(f"✅ Rate limit: {rate_info['requests_made']}/{rate_info['requests_limit']}")
            print(f"   Remaining: {rate_info['requests_remaining']}")
        except httpx.HTTPStatusError as e:
            print(f"❌ Rate limit check failed: {e}")

        # 5. List API keys
        print("\n5️⃣  Listing API keys...")
        try:
            response = await client.get(
                f"{BASE_URL}/auth/api-keys", headers={"X-API-Key": api_key}
            )
            response.raise_for_status()
            keys = response.json()
            print(f"✅ Found {len(keys)} API key(s):")
            for key in keys:
                print(f"   - {key['name']} ({key['key_prefix']}...)")
                print(f"     Created: {key['created_at']}")
                print(f"     Active: {key['is_active']}")
        except httpx.HTTPStatusError as e:
            print(f"❌ List keys failed: {e}")

        # 6. Create additional API key
        print("\n6️⃣  Creating additional API key...")
        key_data = {"name": "Test Key 2", "description": "Created by test script"}
        try:
            response = await client.post(
                f"{BASE_URL}/auth/api-keys",
                json=key_data,
                headers={"X-API-Key": api_key},
            )
            response.raise_for_status()
            new_key = response.json()
            print(f"✅ New key created: {new_key['name']}")
            print(f"   Key: {new_key['key']} (save this!)")
            print(f"   ID: {new_key['id']}")

            # 7. Test trace with new key
            print("\n7️⃣  Testing trace endpoint with authentication...")
            trace_data = {
                "transaction_hash": "f4184fc596403b9d638783cf57adfe4c75c605f6356fbc91338530e9831e9e16",
                "chain": "bitcoin",
                "depth": 1,
            }
            try:
                response = await client.post(
                    f"{BASE_URL}/compliance/trace",
                    json=trace_data,
                    headers={"X-API-Key": new_key["key"]},
                )
                response.raise_for_status()
                result = response.json()
                print(f"✅ Trace completed!")
                print(f"   Transaction: {result['transaction_hash']}")
                print(f"   Risk Score: {result['risk_score']['score']}/100")
                print(f"   Risk Level: {result['risk_score']['level']}")
            except httpx.HTTPStatusError as e:
                print(f"❌ Trace failed: {e.response.status_code}")
                print(f"   {e.response.text}")

        except httpx.HTTPStatusError as e:
            print(f"❌ Create key failed: {e}")

        print("\n" + "=" * 60)
        print("✅ Authentication system tests completed!\n")


if __name__ == "__main__":
    asyncio.run(test_authentication())
