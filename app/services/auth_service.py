"""Authentication service for user and API key management."""

import secrets
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from passlib.context import CryptContext

from app.models.auth import APIKey, APIKeyCreate, User, UserCreate, UserInDB

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    """Service for authentication operations."""

    def __init__(self, db_pool):
        """Initialize auth service with database pool."""
        self.db_pool = db_pool

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt."""
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def generate_api_key() -> str:
        """Generate a secure API key."""
        return f"sk_{''.join(secrets.token_urlsafe(32))}"

    @staticmethod
    def hash_api_key(api_key: str) -> str:
        """Hash an API key for storage."""
        return pwd_context.hash(api_key)

    @staticmethod
    def get_key_prefix(api_key: str) -> str:
        """Get the prefix of an API key for display."""
        return api_key[:12] if len(api_key) >= 12 else api_key

    async def create_user(self, user_data: UserCreate) -> User:
        """Create a new user."""
        async with self.db_pool.acquire() as conn:
            # Check if user exists
            existing = await conn.fetchrow(
                "SELECT id FROM users WHERE email = $1", user_data.email
            )
            if existing:
                raise ValueError("User with this email already exists")

            # Create user
            hashed_password = self.hash_password(user_data.password)
            row = await conn.fetchrow(
                """
                INSERT INTO users (email, full_name, hashed_password)
                VALUES ($1, $2, $3)
                RETURNING id, email, full_name, is_active, is_premium, created_at, updated_at
                """,
                user_data.email,
                user_data.full_name,
                hashed_password,
            )
            return User(**dict(row))

    async def get_user_by_email(self, email: str) -> Optional[UserInDB]:
        """Get user by email."""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM users WHERE email = $1", email
            )
            if not row:
                return None
            return UserInDB(**dict(row))

    async def get_user_by_id(self, user_id: UUID) -> Optional[User]:
        """Get user by ID."""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, email, full_name, is_active, is_premium, created_at, updated_at
                FROM users WHERE id = $1
                """,
                user_id,
            )
            if not row:
                return None
            return User(**dict(row))

    async def create_api_key(
        self, user_id: UUID, key_data: APIKeyCreate, expires_days: Optional[int] = None
    ) -> tuple[APIKey, str]:
        """Create a new API key for a user. Returns (APIKey, plain_key)."""
        plain_key = self.generate_api_key()
        hashed_key = self.hash_api_key(plain_key)
        key_prefix = self.get_key_prefix(plain_key)

        expires_at = None
        if expires_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_days)

        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO api_keys (user_id, name, description, hashed_key, key_prefix, expires_at)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id, user_id, name, description, key_prefix, is_active, 
                          last_used_at, created_at, expires_at
                """,
                user_id,
                key_data.name,
                key_data.description,
                hashed_key,
                key_prefix,
                expires_at,
            )
            api_key = APIKey(**dict(row))
            return api_key, plain_key

    async def verify_api_key(self, plain_key: str) -> Optional[tuple[User, APIKey]]:
        """Verify an API key and return the associated user and key info."""
        key_prefix = self.get_key_prefix(plain_key)

        async with self.db_pool.acquire() as conn:
            # Get all keys with matching prefix
            rows = await conn.fetch(
                """
                SELECT ak.*, u.id as user_id, u.email, u.full_name, 
                       u.is_active as user_is_active, u.is_premium, 
                       u.created_at as user_created_at, u.updated_at as user_updated_at
                FROM api_keys ak
                JOIN users u ON ak.user_id = u.id
                WHERE ak.key_prefix = $1 AND ak.is_active = true
                """,
                key_prefix,
            )

            for row in rows:
                # Verify the full key
                if self.verify_password(plain_key, row["hashed_key"]):
                    # Check expiration
                    if row["expires_at"] and row["expires_at"] < datetime.utcnow():
                        continue

                    # Update last_used_at
                    await conn.execute(
                        "UPDATE api_keys SET last_used_at = $1 WHERE id = $2",
                        datetime.utcnow(),
                        row["id"],
                    )

                    user = User(
                        id=row["user_id"],
                        email=row["email"],
                        full_name=row["full_name"],
                        is_active=row["user_is_active"],
                        is_premium=row["is_premium"],
                        created_at=row["user_created_at"],
                        updated_at=row["user_updated_at"],
                    )

                    api_key = APIKey(
                        id=row["id"],
                        user_id=row["user_id"],
                        name=row["name"],
                        description=row["description"],
                        key_prefix=row["key_prefix"],
                        is_active=row["is_active"],
                        last_used_at=row["last_used_at"],
                        created_at=row["created_at"],
                        expires_at=row["expires_at"],
                    )

                    return user, api_key

        return None

    async def list_user_api_keys(self, user_id: UUID) -> list[APIKey]:
        """List all API keys for a user."""
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, user_id, name, description, key_prefix, is_active,
                       last_used_at, created_at, expires_at
                FROM api_keys
                WHERE user_id = $1
                ORDER BY created_at DESC
                """,
                user_id,
            )
            return [APIKey(**dict(row)) for row in rows]

    async def revoke_api_key(self, user_id: UUID, key_id: UUID) -> bool:
        """Revoke (deactivate) an API key."""
        async with self.db_pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE api_keys
                SET is_active = false
                WHERE id = $1 AND user_id = $2
                """,
                key_id,
                user_id,
            )
            return result != "UPDATE 0"
