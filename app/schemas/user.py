from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

# ---------------------------------------------------------------------
# Input Schemas
# ---------------------------------------------------------------------

class UserRegister(BaseModel):
    """
    Schema for user registration with email and password.
    User will be created in Firebase first, then persisted locally.
    """
    email: EmailStr = Field(description="User's email address")
    password: str = Field(min_length=6, description="User's password (minimum 6 characters)")
    display_name: Optional[str] = Field(default=None, description="User's display name")

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if len(value) < 6:
            raise ValueError("Password must be at least 6 characters long")
        return value


class UserCreate(BaseModel):
    """
    Schema for creating a user record in the local database
    after Firebase authentication succeeds.
    """
    firebase_uid: str
    email: EmailStr
    display_name: Optional[str] = None
    email_verified: bool = False
    is_active: bool = True
    subscription_tier: str = "free"


class UserUpdate(BaseModel):
    """
    Schema for updating user profile data.
    All fields are optional.
    """
    display_name: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None
    birth_date: Optional[str] = None
    birth_time: Optional[str] = None
    birth_location: Optional[str] = None


# ---------------------------------------------------------------------
# Output Schemas
# ---------------------------------------------------------------------

class UserResponse(BaseModel):
    """
    Public user representation returned by the API.
    """
    model_config = {"from_attributes": True}

    id: UUID
    firebase_uid: str
    email: EmailStr
    email_verified: bool
    is_active: bool
    subscription_tier: str
    display_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime] = None
    login_count: int


class UserWithPreferences(UserResponse):
    """
    Extended user response including preferences.
    """
    preferences: Dict[str, Any]
