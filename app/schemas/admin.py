# app/schemas/admin.py
from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID, uuid4
from enum import Enum
import json

class AdminRole(str, Enum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    MODERATOR = "moderator"
    SUPPORT = "support"

class AdminPermission(str, Enum):
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

class AdminUserBase(SQLModel):
    user_id: UUID = Field(foreign_key="users.id", unique=True, index=True)
    role: AdminRole = Field(default=AdminRole.MODERATOR)
    is_active: bool = Field(default=True)
    permissions: List[AdminPermission] = Field(default_factory=list)

class AdminUser(AdminUserBase, table=True):
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_login_at: Optional[datetime] = Field(default=None)
    
    # Relationship to main User table
    user: Optional["User"] = Relationship(back_populates="admin_profile")

class AdminUserCreate(SQLModel):
    user_id: UUID
    role: AdminRole = AdminRole.MODERATOR
    permissions: List[AdminPermission] = Field(default_factory=list)

class AdminUserUpdate(SQLModel):
    role: Optional[AdminRole] = None
    is_active: Optional[bool] = None
    permissions: Optional[List[AdminPermission]] = None

class AdminUserResponse(SQLModel):
    id: UUID
    user_id: UUID
    role: AdminRole
    is_active: bool
    permissions: List[AdminPermission]
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime]
    user_email: Optional[str] = None
    user_display_name: Optional[str] = None

class AdminAuditLog(SQLModel, table=True):
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    admin_id: UUID = Field(foreign_key="adminuser.id")
    action: str = Field(..., description="Action performed")
    resource_type: str = Field(..., description="Type of resource affected")
    resource_id: Optional[str] = Field(default=None, description="ID of affected resource")
    details: Dict[str, Any] = Field(default_factory=dict, sa_column=Field(JSON))
    ip_address: Optional[str] = Field(default=None)
    user_agent: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class SystemSettings(SQLModel, table=True):
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    key: str = Field(unique=True, index=True)
    value: Dict[str, Any] = Field(default_factory=dict, sa_column=Field(JSON))
    description: Optional[str] = Field(default=None)
    is_public: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)