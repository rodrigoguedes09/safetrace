"""Script to create initial admin user and API key."""

import asyncio
import asyncpg
from getpass import getpass

from app.config import get_settings
from app.db.schema import init_auth_tables
from app.models.auth import UserCreate, APIKeyCreate
from app.services.auth_service import AuthService


async def create_admin_user():
    """Create initial admin user with API key."""
    settings = get_settings()

    # Connect to database
    print("Connecting to database...")
    pool = await asyncpg.create_pool(dsn=settings.postgres_dsn)

    try:
        # Initialize tables
        print("Initializing database tables...")
        await init_auth_tables(pool)
        print("✅ Tables initialized")

        # Create auth service
        auth_service = AuthService(pool)

        # Get user details
        print("\n📝 Create Admin User")
        print("-" * 40)
        email = input("Email: ")
        full_name = input("Full Name: ")
        password = getpass("Password (min 8 chars, with uppercase, lowercase, digit): ")

        # Create user
        print("\n Creating user...")
        user_data = UserCreate(email=email, full_name=full_name, password=password)
        user = await auth_service.create_user(user_data)
        print(f"✅ User created: {user.email} (ID: {user.id})")

        # Create API key
        print("\nCreating API key...")
        key_data = APIKeyCreate(
            name="Initial Admin Key", description="First API key for admin"
        )
        api_key, plain_key = await auth_service.create_api_key(user.id, key_data)
        print(f"✅ API key created: {api_key.name}")

        # Display API key
        print("\n" + "=" * 60)
        print("🔑 YOUR API KEY (save this, it won't be shown again!):")
        print("=" * 60)
        print(f"\n{plain_key}\n")
        print("=" * 60)

        print("\n✅ Setup complete!")
        print("\nYou can now use this API key to authenticate:")
        print(f"  curl -H 'X-API-Key: {plain_key}' ...")

    except ValueError as e:
        print(f"\n❌ Error: {e}")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        raise
    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(create_admin_user())
