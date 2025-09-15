from fastapi import Depends, HTTPException, status
from typing import Optional, List
from uuid import UUID
from app.dependencies.auth import get_current_user
from app.database.session import get_db_session
from app.services.admin_service import AdminService
from app.schemas.admin import AdminPermission, AdminRole
from sqlmodel.ext.asyncio.session import AsyncSession

async def get_current_admin(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Dependency to get current admin user."""
    admin_service = AdminService(db)
    
    # Get user ID from Firebase token
    user_id = current_user.get('uid')
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User ID not found in token"
        )
    internal_user_id = await _get_internal_user_id(db, user_id)
    
    admin_user = await admin_service.get_admin_by_user_id(internal_user_id)
    if not admin_user or not admin_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    return admin_user

def require_permission(permission: AdminPermission):
    """Dependency factory to require specific permission."""
    async def permission_dependency(
        admin_user: dict = Depends(get_current_admin),
        db: AsyncSession = Depends(get_db_session)
    ):
        admin_service = AdminService(db)
        
        has_perm = await admin_service.has_permission(admin_user.id, permission)
        if not has_perm:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission.value}"
            )
        
        return admin_user
    
    return permission_dependency

def require_role(role: AdminRole):
    """Dependency factory to require specific role."""
    async def role_dependency(
        admin_user: dict = Depends(get_current_admin),
        db: AsyncSession = Depends(get_db_session)
    ):
        admin_service = AdminService(db)
        
        has_role = await admin_service.has_role(admin_user.id, role)
        if not has_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role required: {role.value}"
            )
        
        return admin_user
    
    return role_dependency

# Common permission dependencies
require_view_users = require_permission(AdminPermission.VIEW_USERS)
require_edit_users = require_permission(AdminPermission.EDIT_USERS)
require_view_analytics = require_permission(AdminPermission.VIEW_ANALYTICS)
require_manage_system = require_permission(AdminPermission.MANAGE_SYSTEM)

# Common role dependencies
require_super_admin = require_role(AdminRole.SUPER_ADMIN)
require_admin = require_role(AdminRole.ADMIN)

async def _get_internal_user_id(db: AsyncSession, firebase_uid: str) -> UUID:
    """Helper to get internal user ID from Firebase UID."""
    from app.services.user_service import UserService
    user_service = UserService(db)
    user = await user_service.get_user_by_firebase_uid(firebase_uid)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in database"
        )
    return user.id