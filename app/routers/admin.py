from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta
import logging

from app.dependencies.admin import (
    get_current_admin, require_permission, require_role,
    require_view_users, require_edit_users, require_view_analytics,
    require_super_admin
)
from app.database.session import get_db_session
from app.services.admin_service import AdminService
from app.schemas.admin import (
    AdminUserCreate, AdminUserUpdate, AdminUserResponse, 
    AdminPermission, AdminRole, SystemSettings
)
from app.services.user_service import UserService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])

@router.get("/dashboard", response_model=Dict[str, Any])
async def admin_dashboard(
    admin_user: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db_session)
):
    """Get admin dashboard with system statistics."""
    admin_service = AdminService(db)
    stats = await admin_service.get_system_stats()
    return stats

@router.post("/users", response_model=AdminUserResponse)
async def create_admin_user(
    admin_data: AdminUserCreate,
    admin_user: dict = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db_session)
):
    """Create a new admin user (super admin only)."""
    admin_service = AdminService(db)
    
    try:
        new_admin = await admin_service.create_admin_user(admin_data)
        return new_admin
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/users", response_model=List[AdminUserResponse])
async def list_admin_users(
    skip: int = 0,
    limit: int = 100,
    admin_user: dict = Depends(require_view_users),
    db: AsyncSession = Depends(get_db_session)
):
    """List all admin users."""
    admin_service = AdminService(db)
    admins = await admin_service.list_admin_users(skip, limit)
    
    # Convert to response format with user details
    response = []
    for admin, user in admins:
        response.append(AdminUserResponse(
            id=admin.id,
            user_id=admin.user_id,
            role=admin.role,
            is_active=admin.is_active,
            permissions=admin.permissions,
            created_at=admin.created_at,
            updated_at=admin.updated_at,
            last_login_at=admin.last_login_at,
            user_email=user.email,
            user_display_name=user.display_name
        ))
    
    return response

@router.put("/users/{admin_id}", response_model=AdminUserResponse)
async def update_admin_user(
    admin_id: UUID,
    update_data: AdminUserUpdate,
    admin_user: dict = Depends(require_edit_users),
    db: AsyncSession = Depends(get_db_session)
):
    """Update an admin user."""
    admin_service = AdminService(db)
    
    updated_admin = await admin_service.update_admin_user(admin_id, update_data)
    if not updated_admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin user not found"
        )
    
    return updated_admin

@router.delete("/users/{admin_id}")
async def delete_admin_user(
    admin_id: UUID,
    admin_user: dict = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db_session)
):
    """Delete an admin user (super admin only)."""
    admin_service = AdminService(db)
    
    success = await admin_service.delete_admin_user(admin_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin user not found"
        )
    
    return {"message": "Admin user deleted successfully"}

@router.get("/audit-logs", response_model=List[Dict[str, Any]])
async def get_audit_logs(
    admin_id: Optional[UUID] = None,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    skip: int = 0,
    limit: int = 100,
    admin_user: dict = Depends(require_view_analytics),
    db: AsyncSession = Depends(get_db_session)
):
    """Get audit logs."""
    admin_service = AdminService(db)
    
    logs = await admin_service.get_audit_logs(
        admin_id, action, resource_type, start_date, end_date, skip, limit
    )
    
    return [
        {
            "id": log.id,
            "admin_id": log.admin_id,
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "details": log.details,
            "ip_address": log.ip_address,
            "user_agent": log.user_agent,
            "created_at": log.created_at.isoformat()
        } for log in logs
    ]

@router.get("/settings/{key}")
async def get_setting(
    key: str,
    admin_user: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db_session)
):
    """Get a system setting."""
    admin_service = AdminService(db)
    
    setting = await admin_service.get_setting(key)
    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Setting not found"
        )
    
    return setting

@router.put("/settings/{key}")
async def set_setting(
    key: str,
    value: Dict[str, Any],
    description: Optional[str] = None,
    is_public: bool = False,
    admin_user: dict = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db_session)
):
    """Set or update a system setting (super admin only)."""
    admin_service = AdminService(db)
    
    setting = await admin_service.set_setting(key, value, description, is_public)
    if not setting:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update setting"
        )
    
    return setting

@router.get("/users/stats")
async def get_user_statistics(
    timeframe: str = "7d",
    admin_user: dict = Depends(require_view_analytics),
    db: AsyncSession = Depends(get_db_session)
):
    """Get detailed user statistics."""
    user_service = UserService(db)
    admin_service = AdminService(db)
    
    # Calculate date range based on timeframe
    if timeframe == "24h":
        start_date = datetime.utcnow() - timedelta(hours=24)
    elif timeframe == "7d":
        start_date = datetime.utcnow() - timedelta(days=7)
    elif timeframe == "30d":
        start_date = datetime.utcnow() - timedelta(days=30)
    else:
        start_date = datetime.utcnow() - timedelta(days=7)
    
    # Get user registration stats
    # This would require additional querying in your UserService
    stats = await user_service.get_user_stats()
    
    return {
        "timeframe": timeframe,
        "total_users": stats.get("total_users", 0),
        "active_users": stats.get("active_users", 0),
        "users_with_birth_data": stats.get("users_with_birth_data", 0),
        # Add more detailed statistics here
    }

@router.post("/users/{user_id}/impersonate")
async def impersonate_user(
    user_id: UUID,
    admin_user: dict = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db_session)
):
    """Generate a temporary token to impersonate a user (super admin only)."""
    # This would require integration with your auth system
    # to generate temporary tokens
    
    return {
        "message": "Impersonation functionality would be implemented here",
        "user_id": str(user_id),
        "impersonator_id": str(admin_user.id)
    }