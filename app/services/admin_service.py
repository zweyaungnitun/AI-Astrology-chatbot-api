# app/services/admin_service.py
from sqlmodel import select, update, delete, and_
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import Optional, Dict, Any, List
from uuid import UUID
import logging
from datetime import datetime, timedelta

from app.schemas.admin import (
    AdminUserCreate, AdminUserUpdate,
    AdminRole, AdminPermission
)
from app.models.admin import AdminUser, AdminAuditLog, SystemSettings
from app.models.user import User

logger = logging.getLogger(__name__)

class AdminService:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    # Admin User Management
    async def create_admin_user(self, admin_data: AdminUserCreate) -> Optional[AdminUser]:
        """Create a new admin user."""
        try:
            # Check if user exists and is not already an admin
            user = await self.db.exec(select(User).where(User.id == admin_data.user_id))
            user = user.first()
            if not user:
                raise ValueError("User not found")
            
            existing_admin = await self.get_admin_by_user_id(admin_data.user_id)
            if existing_admin:
                raise ValueError("User is already an admin")
            
            admin_user = AdminUser(**admin_data.dict())
            self.db.add(admin_user)
            await self.db.commit()
            await self.db.refresh(admin_user)
            
            await self.log_audit(
                admin_user.id, 
                "create_admin", 
                "admin_user", 
                str(admin_user.id),
                {"role": admin_data.role.value, "permissions": [p.value for p in admin_data.permissions]}
            )
            
            return admin_user
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating admin user: {str(e)}")
            raise

    async def get_admin_by_id(self, admin_id: UUID) -> Optional[AdminUser]:
        """Get admin user by ID."""
        try:
            result = await self.db.exec(
                select(AdminUser).where(AdminUser.id == admin_id)
            )
            return result.first()
        except Exception as e:
            logger.error(f"Error getting admin by ID {admin_id}: {str(e)}")
            return None

    async def get_admin_by_user_id(self, user_id: UUID) -> Optional[AdminUser]:
        """Get admin user by user ID."""
        try:
            result = await self.db.exec(
                select(AdminUser).where(AdminUser.user_id == user_id)
            )
            return result.first()
        except Exception as e:
            logger.error(f"Error getting admin by user ID {user_id}: {str(e)}")
            return None

    async def update_admin_user(self, admin_id: UUID, update_data: AdminUserUpdate) -> Optional[AdminUser]:
        """Update admin user information."""
        try:
            admin_user = await self.get_admin_by_id(admin_id)
            if not admin_user:
                return None

            update_dict = update_data.dict(exclude_unset=True)
            for field, value in update_dict.items():
                setattr(admin_user, field, value)
            
            admin_user.updated_at = datetime.utcnow()
            
            await self.db.commit()
            await self.db.refresh(admin_user)
            
            await self.log_audit(
                admin_user.id, 
                "update_admin", 
                "admin_user", 
                str(admin_user.id),
                update_dict
            )
            
            return admin_user
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating admin user {admin_id}: {str(e)}")
            return None

    async def delete_admin_user(self, admin_id: UUID) -> bool:
        """Delete an admin user."""
        try:
            admin_user = await self.get_admin_by_id(admin_id)
            if not admin_user:
                return False

            await self.db.exec(delete(AdminUser).where(AdminUser.id == admin_id))
            await self.db.commit()
            
            await self.log_audit(
                admin_id, 
                "delete_admin", 
                "admin_user", 
                str(admin_id),
                {"deleted_user_id": str(admin_user.user_id)}
            )
            
            return True
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error deleting admin user {admin_id}: {str(e)}")
            return False

    async def list_admin_users(self, skip: int = 0, limit: int = 100) -> List[AdminUser]:
        """List all admin users with user information."""
        try:
            result = await self.db.exec(
                select(AdminUser, User)
                .join(User, AdminUser.user_id == User.id)
                .offset(skip)
                .limit(limit)
            )
            return result.all()
        except Exception as e:
            logger.error(f"Error listing admin users: {str(e)}")
            return []

    # Permission checking
    async def has_permission(self, admin_id: UUID, permission: AdminPermission) -> bool:
        """Check if admin has specific permission."""
        admin_user = await self.get_admin_by_id(admin_id)
        if not admin_user or not admin_user.is_active:
            return False
        
        # Super admins have all permissions
        if admin_user.role == AdminRole.SUPER_ADMIN:
            return True
            
        return permission in admin_user.permissions

    async def has_role(self, admin_id: UUID, role: AdminRole) -> bool:
        """Check if admin has specific role."""
        admin_user = await self.get_admin_by_id(admin_id)
        if not admin_user or not admin_user.is_active:
            return False
            
        return admin_user.role == role

    # Audit Logging
    async def log_audit(
        self, 
        admin_id: UUID, 
        action: str, 
        resource_type: str, 
        resource_id: Optional[str] = None,
        details: Optional[Dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> None:
        """Log an admin action to audit log."""
        try:
            audit_log = AdminAuditLog(
                admin_id=admin_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                details=details or {},
                ip_address=ip_address,
                user_agent=user_agent
            )
            self.db.add(audit_log)
            await self.db.commit()
        except Exception as e:
            logger.error(f"Error logging audit event: {str(e)}")

    async def get_audit_logs(
        self, 
        admin_id: Optional[UUID] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        skip: int = 0, 
        limit: int = 100
    ) -> List[AdminAuditLog]:
        """Get audit logs with filtering."""
        try:
            query = select(AdminAuditLog)
            
            if admin_id:
                query = query.where(AdminAuditLog.admin_id == admin_id)
            if action:
                query = query.where(AdminAuditLog.action == action)
            if resource_type:
                query = query.where(AdminAuditLog.resource_type == resource_type)
            if start_date:
                query = query.where(AdminAuditLog.created_at >= start_date)
            if end_date:
                query = query.where(AdminAuditLog.created_at <= end_date)
                
            query = query.order_by(AdminAuditLog.created_at.desc()).offset(skip).limit(limit)
            
            result = await self.db.exec(query)
            return result.all()
        except Exception as e:
            logger.error(f"Error getting audit logs: {str(e)}")
            return []

    # System Settings
    async def get_setting(self, key: str) -> Optional[SystemSettings]:
        """Get a system setting."""
        try:
            result = await self.db.exec(
                select(SystemSettings).where(SystemSettings.key == key)
            )
            return result.first()
        except Exception as e:
            logger.error(f"Error getting setting {key}: {str(e)}")
            return None

    async def set_setting(self, key: str, value: Dict, description: Optional[str] = None, is_public: bool = False) -> Optional[SystemSettings]:
        """Set or update a system setting."""
        try:
            existing_setting = await self.get_setting(key)
            
            if existing_setting:
                existing_setting.value = value
                existing_setting.description = description or existing_setting.description
                existing_setting.is_public = is_public
                existing_setting.updated_at = datetime.utcnow()
            else:
                setting = SystemSettings(
                    key=key,
                    value=value,
                    description=description,
                    is_public=is_public
                )
                self.db.add(setting)
            
            await self.db.commit()
            return await self.get_setting(key)
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error setting {key}: {str(e)}")
            return None

    # Analytics and Reports
    async def get_system_stats(self) -> Dict[str, Any]:
        """Get comprehensive system statistics."""
        from app.services.user_service import UserService
        
        user_service = UserService(self.db)
        user_stats = await user_service.get_user_stats()
        
        # Get admin stats
        total_admins = await self.db.exec(select(AdminUser))
        active_admins = await self.db.exec(select(AdminUser).where(AdminUser.is_active == True))
        
        # Get recent activity
        recent_activity = await self.get_audit_logs(limit=10)
        
        return {
            "users": user_stats,
            "admins": {
                "total": len(total_admins.all()),
                "active": len(active_admins.all()),
                "by_role": {
                    "super_admin": len([a for a in total_admins.all() if a.role == AdminRole.SUPER_ADMIN]),
                    "admin": len([a for a in total_admins.all() if a.role == AdminRole.ADMIN]),
                    "moderator": len([a for a in total_admins.all() if a.role == AdminRole.MODERATOR]),
                    "support": len([a for a in total_admins.all() if a.role == AdminRole.SUPPORT]),
                }
            },
            "recent_activity": [
                {
                    "action": log.action,
                    "resource_type": log.resource_type,
                    "timestamp": log.created_at.isoformat()
                } for log in recent_activity
            ]
        }