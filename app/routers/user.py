# app/routers/users.py
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import List, Dict, Any
from uuid import UUID
import logging
from firebase_admin import auth

from app.dependencies.auth import get_current_user, require_email_verified
from app.database.session import get_db_session
from app.schemas.user import UserCreate, UserUpdate, UserResponse, UserWithPreferences
from app.services.user_service import UserService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["Users"])

@router.post("/sync", response_model=UserResponse)
async def sync_user_with_firebase(
    firebase_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Sync Firebase user with local database. Creates user if they don't exist.
    This should be called after successful Firebase authentication.
    """
    user_service = UserService(db)
    
    # Check if user already exists
    existing_user = await user_service.get_user_by_firebase_uid(firebase_user['uid'])
    if existing_user:
        # Update login stats for existing user
        updated_user = await user_service.update_login_stats(existing_user.id)
        return updated_user
    
    # Create new user from Firebase data
    user_data = UserCreate(
        firebase_uid=firebase_user['uid'],
        email=firebase_user.get('email', ''),
        display_name=firebase_user.get('name'),
        photo_url=firebase_user.get('picture'),
        email_verified=firebase_user.get('email_verified', False)
    )
    
    new_user = await user_service.create_user(user_data)
    if not new_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create user profile"
        )
    
    return new_user

@router.get("/me", response_model=UserWithPreferences)
async def get_current_user_profile(
    firebase_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Get the complete profile of the currently authenticated user."""
    user_service = UserService(db)
    
    user = await user_service.get_user_by_firebase_uid(firebase_user['uid'])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found"
        )
    
    return user

@router.put("/me", response_model=UserResponse)
async def update_current_user_profile(
    update_data: UserUpdate,
    firebase_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Update the profile of the currently authenticated user."""
    user_service = UserService(db)
    
    user = await user_service.get_user_by_firebase_uid(firebase_user['uid'])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found"
        )
    
    updated_user = await user_service.update_user(user.id, update_data)
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update user profile"
        )
    
    return updated_user

@router.post("/me/birth-data")
async def update_user_birth_data(
    birth_data: Dict[str, str],
    firebase_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Update user's birth data (required for astrology features)."""
    user_service = UserService(db)
    
    user = await user_service.get_user_by_firebase_uid(firebase_user['uid'])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found"
        )
    
    required_fields = ['birth_date', 'birth_time', 'birth_location']
    for field in required_fields:
        if field not in birth_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing required field: {field}"
            )
    
    updated_user = await user_service.update_birth_data(
        user.id,
        birth_data['birth_date'],
        birth_data['birth_time'],
        birth_data['birth_location']
    )
    
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update birth data"
        )
    
    return {"message": "Birth data updated successfully"}

@router.get("/me/birth-data")
async def get_user_birth_data(
    firebase_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Get user's decrypted birth data."""
    user_service = UserService(db)
    
    user = await user_service.get_user_by_firebase_uid(firebase_user['uid'])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found"
        )
    
    birth_data = await user_service.get_birth_data(user.id)
    if not birth_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Birth data not found"
        )
    
    return birth_data

@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_account(
    firebase_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    background_tasks: BackgroundTasks = None
):
    """Delete the user's account and all associated data."""
    user_service = UserService(db)
    
    user = await user_service.get_user_by_firebase_uid(firebase_user['uid'])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found"
        )
    
    # First deactivate the user
    await user_service.deactivate_user(user.id)
    
    # Then delete from Firebase (this would be done in a background task)
    try:
        auth.delete_user(firebase_user['uid'])
    except Exception as e:
        logger.error(f"Error deleting Firebase user {firebase_user['uid']}: {str(e)}")
    
    # Finally delete from our database (optional - you might want to keep for analytics)
    # await user_service.delete_user(user.id)
    
    return None

@router.get("/stats")
async def get_user_statistics(
    admin_user: Dict = Depends(require_email_verified),
    db: AsyncSession = Depends(get_db_session)
):
    """Get user statistics (admin only)."""
    user_service = UserService(db)
    stats = await user_service.get_user_stats()
    return stats

@router.get("/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: UUID,
    admin_user: Dict = Depends(require_email_verified),
    db: AsyncSession = Depends(get_db_session)
):
    """Get user by ID (admin only)."""
    user_service = UserService(db)
    user = await user_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user

@router.get("", response_model=List[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    admin_user: Dict = Depends(require_email_verified),
    db: AsyncSession = Depends(get_db_session)
):
    """List all users with pagination (admin only)."""
    user_service = UserService(db)
    users = await user_service.list_users(skip, limit, active_only=False)
    return users

@router.post("/{user_id}/deactivate")
async def deactivate_user(
    user_id: UUID,
    admin_user: Dict = Depends(require_email_verified),
    db: AsyncSession = Depends(get_db_session)
):
    """Deactivate a user account (admin only)."""
    user_service = UserService(db)
    success = await user_service.deactivate_user(user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return {"message": "User deactivated successfully"}