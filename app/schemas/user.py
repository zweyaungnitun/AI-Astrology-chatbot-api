from sqlmodel import SQLModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID
from pydantic import EmailStr, field_validator

# --- Input Schemas ---

class UserRegister(SQLModel):
    """
    Schema for user registration with email and password.
    User will be created in both Firebase and the local database.
    """
    email: EmailStr = Field(description="User's email address")
    password: str = Field(min_length=6, description="User's password (minimum 6 characters)")
    display_name: Optional[str] = Field(default=None, description="User's display name")
    photo_url: Optional[str] = Field(default=None, description="Profile photo URL")
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError('Password must be at least 6 characters long')
        return v

class UserCreate(SQLModel):
    """
    Schema for creating a new user.
    Represents the data received in a POST request.
    """
    firebase_uid: str
    email: str
    display_name: Optional[str] = None
    photo_url: Optional[str] = None
    email_verified: bool = False

class UserUpdate(SQLModel):
    """
    Schema for updating an existing user.
    Represents the data received in a PUT or PATCH request.
    All fields are optional.
    """
    display_name: Optional[str] = None
    photo_url: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None
    birth_date: Optional[str] = None
    birth_time: Optional[str] = None
    birth_location: Optional[str] = None


# --- Output Schemas ---

class UserResponse(SQLModel):
    """
    Schema for returning user data in an API response.
    This is the public representation of a user.
    """
    id: UUID
    firebase_uid: str
    email: str
    email_verified: bool
    is_active: bool
    subscription_tier: str
    display_name: Optional[str] = None
    photo_url: Optional[str] = None
    has_birth_data: bool = Field(description="Computed field: True if user has provided birth data")
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime] = None
    login_count: int

class UserWithPreferences(UserResponse):
    """
    Extends UserResponse to include the user's preferences.
    Used for endpoints where detailed settings are required.
    """
    preferences: Dict[str, Any]
