# app/routers/users.py
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import List, Dict, Any
from uuid import UUID
import logging
from firebase_admin import auth

from app.dependencies.auth import get_current_user, require_email_verified
from app.database.session import get_db_session
from app.schemas.user import UserCreate, UserUpdate, UserResponse, UserWithPreferences, UserRegister
from app.services.user_service import UserService
from app.services.firebase_admin import create_firebase_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["Users"])

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserRegister,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Public user registration endpoint - No authentication required.
    
    Allows users to create their own account by providing:
    - Email address
    - Password (minimum 6 characters)
    - Optional display name and photo URL
    
    This endpoint will:
    1. Create a user account in Firebase Authentication
    2. Create a corresponding user profile in the local database
    3. Return the created user information
    
    The user can immediately log in using the email and password provided.
    Note: Email verification may be required depending on Firebase configuration.
    
    Returns 201 Created on success with user details.
    Returns 400 Bad Request if email already exists or validation fails.
    """
    user_service = UserService(db)
    
    # Check if email already exists in database
    existing_user = await user_service.get_user_by_email(user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists"
        )
    
    try:
        # Step 1: Create user in Firebase
        firebase_user = create_firebase_user(
            email=user_data.email,
            password=user_data.password,
            display_name=user_data.display_name,
            email_verified=False  # Email verification will be handled by Firebase
        )
        
        # Step 2: Create user in local database
        db_user_data = UserCreate(
            firebase_uid=firebase_user['uid'],
            email=firebase_user['email'],
            display_name=firebase_user.get('display_name'),
            email_verified=firebase_user.get('email_verified', False)
        )
        
        new_user = await user_service.create_user(db_user_data)
        
        if not new_user:
            # If database creation fails, try to clean up Firebase user
            try:
                auth.delete_user(firebase_user['uid'])
                logger.warning(f"Cleaned up Firebase user {firebase_user['uid']} after database creation failure")
            except Exception as cleanup_error:
                logger.error(f"Failed to clean up Firebase user after database error: {str(cleanup_error)}")
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user profile in database"
            )
        
        logger.info(f"User successfully self-registered: {user_data.email} (Firebase UID: {firebase_user['uid']})")
        return new_user
        
    except ValueError as e:
        # Handle Firebase-specific errors
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error during user registration: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during registration"
        )

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
    
    existing_user = await user_service.get_user_by_firebase_uid(firebase_user['uid'])
    if existing_user:
        if existing_user.id is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="User record is missing an ID"
            )
        updated_user = await user_service.update_login_stats(existing_user.id)
        return updated_user
    
    user_data = UserCreate(
        firebase_uid=firebase_user['uid'],
        email=firebase_user.get('email', ''),
        display_name=firebase_user.get('name'),
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
    if user.id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User record is missing an ID"
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
    if user.id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User record is missing an ID"
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
    if user.id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User record is missing an ID"
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
    background_tasks: BackgroundTasks,
    firebase_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Delete the user's account and all associated data."""
    user_service = UserService(db)
    
    user = await user_service.get_user_by_firebase_uid(firebase_user['uid'])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found"
        )
    if user.id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User record is missing an ID"
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