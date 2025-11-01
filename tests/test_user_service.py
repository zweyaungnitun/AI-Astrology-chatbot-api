"""
Test cases for UserService using pytest with PostgreSQL.
"""

import pytest
import pytest_asyncio
from uuid import uuid4
from datetime import datetime

from app.services.user_service import UserService
from app.schemas.user import UserCreate, UserUpdate
from app.models.user import User

class TestUserService:
    """Test cases for UserService class."""

    @pytest.mark.asyncio
    async def test_create_user_success(self, user_service: UserService, sample_user_data: UserCreate):
        """Test successful user creation."""
        # Act
        created_user = await user_service.create_user(sample_user_data)
        # Assert
        assert created_user is not None
        assert created_user.email == sample_user_data.email
        assert created_user.firebase_uid == sample_user_data.firebase_uid
        assert created_user.display_name == sample_user_data.display_name
        assert created_user.photo_url == sample_user_data.photo_url
        assert created_user.email_verified == sample_user_data.email_verified
        assert created_user.is_active is True
        assert created_user.subscription_tier == "free"
        assert created_user.id is not None
        assert created_user.created_at is not None
        assert created_user.updated_at is not None

    @pytest.mark.asyncio
    async def test_create_user_already_exists(self, user_service: UserService, sample_user_data: UserCreate):
        """Test that creating a user with existing Firebase UID returns existing user."""
        # Arrange - Create user first time
        first_user = await user_service.create_user(sample_user_data)
        assert first_user is not None
        
        # Act - Try to create same user again
        second_user = await user_service.create_user(sample_user_data)
        
        # Assert - Should return the same user
        assert second_user is not None
        assert second_user.id == first_user.id
        assert second_user.email == first_user.email
        assert second_user.firebase_uid == first_user.firebase_uid

    @pytest.mark.asyncio
    async def test_get_user_by_id(self, user_service: UserService, sample_user_data: UserCreate):
        """Test fetching a user by their UUID."""
        # Arrange
        created_user = await user_service.create_user(sample_user_data)
        assert created_user is not None
        
        # Act
        fetched_user = await user_service.get_user_by_id(created_user.id)
        
        # Assert
        assert fetched_user is not None
        assert fetched_user.id == created_user.id
        assert fetched_user.email == created_user.email
        assert fetched_user.firebase_uid == created_user.firebase_uid

    @pytest.mark.asyncio
    async def test_get_user_by_firebase_uid(self, user_service: UserService, sample_user_data: UserCreate):
        """Test fetching a user by their Firebase UID."""
        # Arrange
        created_user = await user_service.create_user(sample_user_data)
        assert created_user is not None
        
        # Act
        fetched_user = await user_service.get_user_by_firebase_uid(sample_user_data.firebase_uid)
        
        # Assert
        assert fetched_user is not None
        assert fetched_user.id == created_user.id
        assert fetched_user.email == created_user.email
        assert fetched_user.firebase_uid == created_user.firebase_uid

    @pytest.mark.asyncio
    async def test_get_user_by_email(self, user_service: UserService, sample_user_data: UserCreate):
        """Test fetching a user by their email address."""
        # Arrange
        created_user = await user_service.create_user(sample_user_data)
        assert created_user is not None
        
        # Act
        fetched_user = await user_service.get_user_by_email(sample_user_data.email)
        
        # Assert
        assert fetched_user is not None
        assert fetched_user.id == created_user.id
        assert fetched_user.email == created_user.email
        assert fetched_user.firebase_uid == created_user.firebase_uid

    @pytest.mark.asyncio
    async def test_get_user_by_id_not_found(self, user_service: UserService):
        """Test fetching a non-existent user by ID returns None."""
        # Act
        non_existent_id = uuid4()
        fetched_user = await user_service.get_user_by_id(non_existent_id)
        
        # Assert
        assert fetched_user is None

    @pytest.mark.asyncio
    async def test_get_user_by_firebase_uid_not_found(self, user_service: UserService):
        """Test fetching a non-existent user by Firebase UID returns None."""
        # Act
        fetched_user = await user_service.get_user_by_firebase_uid("non_existent_uid")
        
        # Assert
        assert fetched_user is None

    @pytest.mark.asyncio
    async def test_get_user_by_email_not_found(self, user_service: UserService):
        """Test fetching a non-existent user by email returns None."""
        # Act
        fetched_user = await user_service.get_user_by_email("nonexistent@example.com")
        
        # Assert
        assert fetched_user is None

    @pytest.mark.asyncio
    async def test_update_user(self, user_service: UserService, sample_user_data: UserCreate):
        """Test updating user information."""
        # Arrange
        created_user = await user_service.create_user(sample_user_data)
        assert created_user is not None
        
        update_data = UserUpdate(
            display_name="Updated Display Name",
            photo_url="https://example.com/updated_photo.jpg"
        )
        
        # Act
        updated_user = await user_service.update_user(created_user.id, update_data)
        
        # Assert
        assert updated_user is not None
        assert updated_user.id == created_user.id
        assert updated_user.display_name == "Updated Display Name"
        assert updated_user.photo_url == "https://example.com/updated_photo.jpg"
        assert updated_user.email == created_user.email  # Should remain unchanged
        assert updated_user.updated_at > created_user.updated_at

    @pytest.mark.asyncio
    async def test_update_user_not_found(self, user_service: UserService):
        """Test updating a non-existent user returns None."""
        # Arrange
        non_existent_id = uuid4()
        update_data = UserUpdate(display_name="New Name")
        
        # Act
        updated_user = await user_service.update_user(non_existent_id, update_data)
        
        # Assert
        assert updated_user is None

    @pytest.mark.asyncio
    async def test_update_login_stats(self, user_service: UserService, sample_user_data: UserCreate):
        """Test updating user login statistics."""
        # Arrange
        created_user = await user_service.create_user(sample_user_data)
        assert created_user is not None
        original_login_count = created_user.login_count
        original_last_login = created_user.last_login_at
        
        # Act
        updated_user = await user_service.update_login_stats(created_user.id)
        
        # Assert
        assert updated_user is not None
        assert updated_user.id == created_user.id
        assert updated_user.login_count == original_login_count + 1
        assert updated_user.last_login_at is not None
        assert updated_user.last_login_at > original_last_login if original_last_login else True

    @pytest.mark.asyncio
    async def test_update_login_stats_not_found(self, user_service: UserService):
        """Test updating login stats for non-existent user returns None."""
        # Act
        non_existent_id = uuid4()
        updated_user = await user_service.update_login_stats(non_existent_id)
        
        # Assert
        assert updated_user is None

    @pytest.mark.asyncio
    async def test_deactivate_user(self, user_service: UserService, sample_user_data: UserCreate):
        """Test deactivating a user account."""
        # Arrange
        created_user = await user_service.create_user(sample_user_data)
        assert created_user is not None
        assert created_user.is_active is True
        
        # Act
        result = await user_service.deactivate_user(created_user.id)
        
        # Assert
        assert result is True
        
        # Verify user is deactivated
        deactivated_user = await user_service.get_user_by_id(created_user.id)
        assert deactivated_user is not None
        assert deactivated_user.is_active is False
        assert deactivated_user.updated_at > created_user.updated_at

    @pytest.mark.asyncio
    async def test_deactivate_user_not_found(self, user_service: UserService):
        """Test deactivating a non-existent user returns False."""
        # Act
        non_existent_id = uuid4()
        result = await user_service.deactivate_user(non_existent_id)
        
        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_deactivate_already_inactive_user(self, user_service: UserService, sample_user_data: UserCreate):
        """Test deactivating an already inactive user returns False."""
        # Arrange
        created_user = await user_service.create_user(sample_user_data)
        assert created_user is not None
        
        # First deactivation
        await user_service.deactivate_user(created_user.id)
        
        # Act - Try to deactivate again
        result = await user_service.deactivate_user(created_user.id)
        
        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_user(self, user_service: UserService, sample_user_data: UserCreate):
        """Test permanently deleting a user."""
        # Arrange
        created_user = await user_service.create_user(sample_user_data)
        assert created_user is not None
        
        # Act
        result = await user_service.delete_user(created_user.id)
        
        # Assert
        assert result is True
        
        # Verify user is deleted
        deleted_user = await user_service.get_user_by_id(created_user.id)
        assert deleted_user is None

    @pytest.mark.asyncio
    async def test_delete_user_not_found(self, user_service: UserService):
        """Test deleting a non-existent user returns False."""
        # Act
        non_existent_id = uuid4()
        result = await user_service.delete_user(non_existent_id)
        
        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_list_users(self, user_service: UserService, sample_user_data: UserCreate, sample_user_data_2: UserCreate):
        """Test listing users with pagination."""
        # Arrange - Create multiple users
        user1 = await user_service.create_user(sample_user_data)
        user2 = await user_service.create_user(sample_user_data_2)
        assert user1 is not None
        assert user2 is not None
        
        # Act
        users = await user_service.list_users()
        
        # Assert
        assert len(users) >= 2
        user_ids = [user.id for user in users]
        assert user1.id in user_ids
        assert user2.id in user_ids

    @pytest.mark.asyncio
    async def test_list_users_pagination(self, user_service: UserService, sample_user_data: UserCreate, sample_user_data_2: UserCreate):
        """Test listing users with pagination parameters."""
        # Arrange - Create users
        user1 = await user_service.create_user(sample_user_data)
        user2 = await user_service.create_user(sample_user_data_2)
        
        # Act - Test pagination
        users_page1 = await user_service.list_users(skip=0, limit=1)
        users_page2 = await user_service.list_users(skip=1, limit=1)
        
        # Assert
        assert len(users_page1) <= 1
        assert len(users_page2) <= 1
        
        if len(users_page1) > 0 and len(users_page2) > 0:
            assert users_page1[0].id != users_page2[0].id

    @pytest.mark.asyncio
    async def test_user_exists(self, user_service: UserService, sample_user_data: UserCreate):
        """Test checking if a user exists by Firebase UID."""
        # Arrange
        created_user = await user_service.create_user(sample_user_data)
        assert created_user is not None
        
        # Act & Assert
        assert await user_service.user_exists(sample_user_data.firebase_uid) is True
        assert await user_service.user_exists("non_existent_uid") is False

    @pytest.mark.asyncio
    async def test_get_user_stats(self, user_service: UserService, sample_user_data: UserCreate, sample_user_data_2: UserCreate):
        """Test getting user statistics."""
        # Arrange - Create users
        user1 = await user_service.create_user(sample_user_data)
        user2 = await user_service.create_user(sample_user_data_2)
        
        # Deactivate one user
        await user_service.deactivate_user(user1.id)
        
        # Act
        stats = await user_service.get_user_stats()
        
        # Assert
        assert "total_users" in stats
        assert "active_users" in stats
        assert "users_with_birth_data" in stats
        assert stats["total_users"] >= 2
        assert stats["active_users"] >= 1  # At least user2 should be active

    @pytest.mark.asyncio
    async def test_create_user_with_minimal_data(self, user_service: UserService):
        """Test creating a user with minimal required data."""
        # Arrange
        minimal_data = UserCreate(
            firebase_uid="minimal_test_uid",
            email="minimal@example.com",
            email_verified=True
        )
        
        # Act
        created_user = await user_service.create_user(minimal_data)
        
        # Assert
        assert created_user is not None
        assert created_user.email == minimal_data.email
        assert created_user.firebase_uid == minimal_data.firebase_uid
        assert created_user.email_verified == minimal_data.email_verified
        assert created_user.display_name is None
        assert created_user.photo_url is None

    @pytest.mark.asyncio
    async def test_multiple_users_isolation(self, user_service: UserService):
        """Test that multiple users can be created and managed independently."""
        # Arrange - Create multiple users with different data
        users_data = [
            UserCreate(firebase_uid=f"uid_{i}", email=f"user{i}@example.com", email_verified=True)
            for i in range(3)
        ]
        
        # Act - Create all users
        created_users = []
        for user_data in users_data:
            user = await user_service.create_user(user_data)
            assert user is not None
            created_users.append(user)
        
        # Assert - Each user should be independent
        assert len(created_users) == 3
        for i, user in enumerate(created_users):
            assert user.email == f"user{i}@example.com"
            assert user.firebase_uid == f"uid_{i}"
            
            # Test that each user can be retrieved independently
            retrieved_user = await user_service.get_user_by_id(user.id)
            assert retrieved_user is not None
            assert retrieved_user.id == user.id
            assert retrieved_user.email == user.email

    @pytest.mark.asyncio
    async def test_update_user_partial_data(self, user_service: UserService, sample_user_data: UserCreate):
        """Test updating user with only some fields."""
        # Arrange
        created_user = await user_service.create_user(sample_user_data)
        assert created_user is not None
        original_email = created_user.email
        original_photo_url = created_user.photo_url
        
        # Act - Update only display name
        update_data = UserUpdate(display_name="New Display Name")
        updated_user = await user_service.update_user(created_user.id, update_data)
        
        # Assert
        assert updated_user is not None
        assert updated_user.display_name == "New Display Name"
        assert updated_user.email == original_email  # Should remain unchanged
        assert updated_user.photo_url == original_photo_url  # Should remain unchanged
