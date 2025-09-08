# app/schemas/user.py
from sqlmodel import SQLModel, Field, Column, JSON
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID, uuid4
import json

class UserBase(SQLModel):
    firebase_uid: str = Field(unique=True, index=True, description="Firebase User ID")
    email: str = Field(unique=True, index=True, description="User's email address")
    email_verified: bool = Field(default=False, description="Whether email is verified")
    is_active: bool = Field(default=True, description="Whether user account is active")
    subscription_tier: str = Field(default="free", description="User's subscription level")

class User(UserBase, table=True):
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    display_name: Optional[str] = Field(default=None, description="User's display name")
    photo_url: Optional[str] = Field(default=None, description="Profile photo URL")
    
    # Birth data (encrypted in production)
    birth_date: Optional[str] = Field(default=None, description="Encrypted birth date")
    birth_time: Optional[str] = Field(default=None, description="Encrypted birth time")
    birth_location: Optional[str] = Field(default=None, description="Encrypted birth location")
    
    # Preferences
    preferences: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        description="User preferences and settings"
    )
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_login_at: Optional[datetime] = Field(default=None)
    login_count: int = Field(default=0, description="Number of times user has logged in")

    class Config:
        table_name = "users"

class UserCreate(SQLModel):
    firebase_uid: str
    email: str
    display_name: Optional[str] = None
    photo_url: Optional[str] = None
    email_verified: bool = False

class UserUpdate(SQLModel):
    display_name: Optional[str] = None
    photo_url: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None
    birth_date: Optional[str] = None
    birth_time: Optional[str] = None
    birth_location: Optional[str] = None

class UserResponse(SQLModel):
    id: UUID
    firebase_uid: str
    email: str
    email_verified: bool
    is_active: bool
    subscription_tier: str
    display_name: Optional[str] = None
    photo_url: Optional[str] = None
    has_birth_data: bool = Field(description="Whether user has provided birth data")
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime] = None
    login_count: int

class UserWithPreferences(UserResponse):
    preferences: Dict[str, Any] = Field(default_factory=dict)