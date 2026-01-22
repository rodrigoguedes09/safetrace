"""Authentication and user models."""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserBase(BaseModel):
    """Base user model."""

    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=100)


class UserCreate(UserBase):
    """User creation model."""

    password: str = Field(..., min_length=8, max_length=100)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength."""
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class User(UserBase):
    """User model with database fields."""

    id: UUID = Field(default_factory=uuid4)
    is_active: bool = True
    is_premium: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"from_attributes": True}


class UserInDB(User):
    """User model with hashed password for database storage."""

    hashed_password: str


class APIKeyCreate(BaseModel):
    """API key creation model."""

    name: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = Field(None, max_length=200)


class APIKey(BaseModel):
    """API key model."""

    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    name: str
    description: Optional[str] = None
    key_prefix: str = Field(..., description="First 8 characters of the key")
    is_active: bool = True
    last_used_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class APIKeyResponse(APIKey):
    """API key response with full key (only shown once)."""

    key: str = Field(..., description="Full API key (shown only on creation)")


class RateLimitInfo(BaseModel):
    """Rate limit information for a user."""

    requests_made: int
    requests_limit: int
    window_start: datetime
    window_end: datetime
    requests_remaining: int


class TokenData(BaseModel):
    """Token payload data."""

    user_id: UUID
    api_key_id: UUID
