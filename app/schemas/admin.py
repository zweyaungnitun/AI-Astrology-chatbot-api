from sqlmodel import SQLModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime

# Import enums from the models to ensure consistency
from app.models.admin import AdminRole, AdminPermission

# --- Input Schemas ---

class AdminUserCreate(SQLModel):
    """Schema for creating a new admin user."""
    user_id: UUID
    role: AdminRole = AdminRole.MODERATOR
    permissions: List[AdminPermission] = Field(default_factory=list)

class AdminUserUpdate(SQLModel):
    """Schema for updating an existing admin user's details."""
    role: Optional[AdminRole] = None
    is_active: Optional[bool] = None
    permissions: Optional[List[AdminPermission]] = None

# --- Output Schemas ---

class AdminUserResponse(SQLModel):
    """Schema for returning admin user information in an API response."""
    id: UUID
    user_id: UUID
    role: AdminRole
    is_active: bool
    permissions: List[AdminPermission]
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime]
    # Optional fields to enrich the response with related user data
    user_email: Optional[str] = None
    user_display_name: Optional[str] = None
