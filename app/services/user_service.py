# app/services/user_service.py
from sqlmodel import func, select, update, delete
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import Optional, Dict, Any, List
from uuid import UUID
import logging
from datetime import datetime
from app.schemas.user import UserCreate, UserUpdate, UserResponse
from app.models.user import User
from app.utils.encryption import encrypt_data, decrypt_data

logger = logging.getLogger(__name__)

class UserService:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def get_user_by_id(self, user_id: UUID) -> Optional[User]:
        """Get user by their internal UUID."""
        try:
            statement = select(User).where(User.id == user_id)
            result = await self.db.execute(statement)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting user by ID {user_id}: {str(e)}")
            return None

    async def get_user_by_firebase_uid(self, firebase_uid: str) -> Optional[User]:
        """Get user by their Firebase UID."""
        try:
            statement = select(User).where(User.firebase_uid == firebase_uid)
            result = await self.db.execute(statement)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting user by Firebase UID {firebase_uid}: {str(e)}")
            return None

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email address."""
        try:
            statement = select(User).where(User.email == email)
            result = await self.db.execute(statement)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting user by email {email}: {str(e)}")
            return None

    async def create_user(self, user_data: UserCreate) -> Optional[User]:
        """Create a new user in the database."""
        try:
            # Check if user already exists
            existing_user = await self.get_user_by_firebase_uid(user_data.firebase_uid)
            if existing_user:
                logger.warning(f"User with Firebase UID {user_data.firebase_uid} already exists")
                return existing_user

            # Create new user
            db_user = User(**user_data.model_dump())
            self.db.add(db_user)
            await self.db.flush()  # Flush to get the ID without committing
            await self.db.commit()
            await self.db.refresh(db_user)
            
            logger.info(f"Created new user: {db_user.email} (ID: {db_user.id})")
            return db_user
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating user {user_data.email}: {str(e)}")
            return None

    async def update_user(
        self, 
        user_id: UUID, 
        update_data: UserUpdate
    ) -> Optional[User]:
        """Update user information."""
        try:
            # Get existing user
            user = await self.get_user_by_id(user_id)
            if not user:
                return None

            # Update fields
            update_dict = update_data.model_dump(exclude_unset=True)
            for field, value in update_dict.items():
                setattr(user, field, value)
            
            user.updated_at = datetime.utcnow()
            
            await self.db.commit()
            await self.db.refresh(user)
            
            logger.info(f"Updated user {user_id}")
            return user
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating user {user_id}: {str(e)}")
            return None

    async def update_login_stats(self, user_id: UUID) -> Optional[User]:
        """Update user login statistics."""
        try:
            user = await self.get_user_by_id(user_id)
            if not user:
                return None

            user.last_login_at = datetime.utcnow()
            user.login_count += 1
            user.updated_at = datetime.utcnow()
            
            await self.db.commit()
            await self.db.refresh(user)
            
            return user
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating login stats for user {user_id}: {str(e)}")
            return None

    async def deactivate_user(self, user_id: UUID) -> bool:
        """Deactivate a user account."""
        try:
            user = await self.get_user_by_id(user_id)
            if not user:
                return False

            user.is_active = False
            user.updated_at = datetime.utcnow()
            
            await self.db.commit()
            logger.info(f"Deactivated user {user_id}")
            return True
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error deactivating user {user_id}: {str(e)}")
            return False

    async def delete_user(self, user_id: UUID) -> bool:
        """Permanently delete a user from the database."""
        try:
            user = await self.get_user_by_id(user_id)
            if not user:
                return False

            # Use delete statement for async session
            statement = delete(User).where(User.id == user_id)
            await self.db.execute(statement)
            await self.db.commit()

            logger.info(f"Deleted user {user_id}")
            return True

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error deleting user {user_id}: {str(e)}")
            return False


    async def update_birth_data(
        self, 
        user_id: UUID, 
        birth_date: str, 
        birth_time: str, 
        birth_location: str
    ) -> Optional[User]:
        """Update user's birth data with encryption."""
        try:
            user = await self.get_user_by_id(user_id)
            if not user:
                return None

            # Encrypt sensitive data (implementation depends on your encryption utils)
            user.birth_date = encrypt_data(birth_date)
            user.birth_time = encrypt_data(birth_time)
            user.birth_location = encrypt_data(birth_location)
            user.updated_at = datetime.utcnow()
            
            await self.db.commit()
            await self.db.refresh(user)
            
            logger.info(f"Updated birth data for user {user_id}")
            return user
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating birth data for user {user_id}: {str(e)}")
            return None

    async def get_birth_data(self, user_id: UUID) -> Optional[Dict[str, str]]:
        """Get decrypted birth data for a user."""
        try:
            user = await self.get_user_by_id(user_id)
            if not user or not user.birth_date:
                return None

            return {
                "birth_date": decrypt_data(user.birth_date or ""),
                "birth_time": decrypt_data(user.birth_time or ""),
                "birth_location": decrypt_data(user.birth_location or "")
            }
            
        except Exception as e:
            logger.error(f"Error getting birth data for user {user_id}: {str(e)}")
            return None

    async def list_users(
        self, 
        skip: int = 0, 
        limit: int = 100,
        active_only: bool = True
    ) -> List[User]:
        """List users with pagination."""
        try:
            query = select(User)
            if active_only:
                query = query.where(User.is_active == True)
            
            query = query.offset(skip).limit(limit)
            result = await self.db.execute(query)
            users = result.scalars().all()
            return list(users) if users else []
            
        except Exception as e:
            logger.error(f"Error listing users: {str(e)}")
            return []

    async def user_exists(self, firebase_uid: str) -> bool:
        """Check if a user exists by Firebase UID."""
        user = await self.get_user_by_firebase_uid(firebase_uid)
        return user is not None

    async def get_user_stats(self) -> Dict[str, int]:
        """Get user statistics."""
        try:
            # total users
            res = await self.db.execute(select(func.count()).select_from(User))
            total_users = int(res.scalar_one())

            # active users
            res = await self.db.execute(
                select(func.count()).select_from(User).where(User.is_active == True)
            )
            active_users = int(res.scalar_one())

            # users with birth data: treat NULL as missing; if you store empty string, use `!= ""` instead
            res = await self.db.execute(
                select(func.count()).select_from(User).where(User.birth_date != None)  # generates IS NOT NULL
            )
            users_with_birth_data = int(res.scalar_one())

            return {
                "total_users": total_users,
                "active_users": active_users,
                "users_with_birth_data": users_with_birth_data,
            }

        except Exception as e:
            logger.error(f"Error getting user stats: {str(e)}")
            return {}