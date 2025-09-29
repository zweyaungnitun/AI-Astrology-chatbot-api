from sqlmodel import SQLModel, Field, Relationship, Column, JSON
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID, uuid4
from enum import Enum

# --- Enums ---

class AdminRole(str, Enum):
    """Enumeration for admin user roles."""
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    MODERATOR = "moderator"
    SUPPORT = "support"

class AdminPermission(str, Enum):
    """Enumeration for specific admin permissions."""
    # User management
    VIEW_USERS = "view_users"
    EDIT_USERS = "edit_users"
    DELETE_USERS = "delete_users"
    # Content management
    VIEW_CONTENT = "view_content"
    EDIT_CONTENT = "edit_content"
    DELETE_CONTENT = "delete_content"
    # System management
    VIEW_ANALYTICS = "view_analytics"
    MANAGE_SYSTEM = "manage_system"
    MANAGE_SETTINGS = "manage_settings"
    # Financial
    VIEW_PAYMENTS = "view_payments"
    PROCESS_REFUNDS = "process_refunds"

# --- Database Models ---

class AdminUser(SQLModel, table=True):
    """Represents the 'adminuser' table in the database."""
    __tablename__ = "adminuser"

    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", unique=True, index=True)
    role: AdminRole = Field(default=AdminRole.MODERATOR)
    is_active: bool = Field(default=True)
    permissions: List[AdminPermission] = Field(sa_column=Column(JSON), default_factory=list)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_login_at: Optional[datetime] = Field(default=None)
    
    # Relationship to main User table (ensure 'admin_profile' is on User model)
    user: Optional["User"] = Relationship(back_populates="admin_profile")

class AdminAuditLog(SQLModel, table=True):
    """Represents the 'adminauditlog' table for tracking admin actions."""
    __tablename__ = "adminauditlog"

    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    admin_id: UUID = Field(foreign_key="adminuser.id")
    action: str = Field(description="Action performed by the admin")
    resource_type: str = Field(description="Type of resource affected (e.g., 'user', 'chart')")
    resource_id: Optional[str] = Field(default=None, description="ID of the affected resource")
    details: Dict[str, Any] = Field(sa_column=Column(JSON), default_factory=dict)
    ip_address: Optional[str] = Field(default=None)
    user_agent: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class SystemSettings(SQLModel, table=True):
    """Represents the 'systemsettings' table for key-value system config."""
    __tablename__ = "systemsettings"

    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    key: str = Field(unique=True, index=True)
    value: Dict[str, Any] = Field(sa_column=Column(JSON), default_factory=dict)
    description: Optional[str] = Field(default=None)
    is_public: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
