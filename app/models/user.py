from sqlmodel import SQLModel, Field, Column, JSON, Relationship
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID, uuid4

class User(SQLModel, table=True):
    """
    Represents the 'users' table in the database.
    This is the internal representation of a user.
    """
    __tablename__ = "users"

    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    firebase_uid: str = Field(unique=True, index=True, description="Firebase User ID")
    email: str = Field(unique=True, index=True, description="User's email address")
    email_verified: bool = Field(default=False, description="Whether email is verified")
    is_active: bool = Field(default=True, description="Whether user account is active")
    subscription_tier: str = Field(default="free", description="User's subscription level")
    display_name: Optional[str] = Field(default=None, description="User's display name")
    
    # Birth data (should be encrypted in a real application)
    birth_date: Optional[str] = Field(default=None, description="Encrypted birth date")
    birth_time: Optional[str] = Field(default=None, description="Encrypted birth time")
    birth_location: Optional[str] = Field(default=None, description="Encrypted birth location")
    
    # User-specific settings
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

    # Relationships to other tables
    admin_profile: Optional["AdminUser"] = Relationship(back_populates="user")
    chat_sessions: List["ChatSession"] = Relationship(back_populates="user")
    charts: List["Chart"] = Relationship(back_populates="user")
