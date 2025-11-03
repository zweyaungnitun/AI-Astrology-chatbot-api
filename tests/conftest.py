import asyncio
from typing import AsyncGenerator
from uuid import uuid4
from datetime import date, time

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, func

from app.main import app
from app.database.session import get_db_session, async_session
from app.schemas.user import UserCreate
from app.schemas.chart import ChartCreate
from app.services.user_service import UserService
from app.services.chart_service import ChartService
from app.services.chat_service import ChatService
from app.services.admin_service import AdminService
from app.services.ai_service import AIService
from app.models.user import User
from app.models.chart import Chart, ChartType, HouseSystem, ZodiacSystem
from app.models.chat import ChatSession, ChatMessage, MessageRole
from app.models.admin import AdminUser

# -----------------------
# Event Loop Fixture
# -----------------------
@pytest.fixture(scope="session")
def event_loop():
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()

# -----------------------
# Database Session Fixture
# -----------------------
@pytest_asyncio.fixture(scope="function")
async def test_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session

# -----------------------
# Service Fixtures
# -----------------------
@pytest_asyncio.fixture(scope="function")
async def chart_service(test_db_session: AsyncSession) -> ChartService:
    return ChartService(test_db_session)

@pytest_asyncio.fixture(scope="function")
async def chat_service(test_db_session: AsyncSession) -> ChatService:
    return ChatService(test_db_session)

@pytest_asyncio.fixture(scope="function")
async def admin_service(test_db_session: AsyncSession) -> AdminService:
    return AdminService(test_db_session)

@pytest_asyncio.fixture(scope="function")
async def user_service(test_db_session: AsyncSession) -> UserService:
    return UserService(test_db_session)

# ✅ NEW: AI Service Fixture
@pytest_asyncio.fixture(scope="function")
async def ai_service() -> AIService:
    """Provide an instance of the AIService for testing."""
    return AIService()

# -----------------------
# HTTP Client Fixture
# -----------------------
@pytest_asyncio.fixture(scope="function")
async def client(test_db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db_session() -> AsyncGenerator[AsyncSession, None]:
        yield test_db_session

    app.dependency_overrides[get_db_session] = override_get_db_session
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()

# -----------------------
# Sample Data Fixtures
# -----------------------
@pytest.fixture(scope="session")
def sample_user_data() -> UserCreate:
    return UserCreate(
        firebase_uid="id_2",
        email="test00@example.com",
        display_name="Test User",
        photo_url="https://example.com/photo.jpg",
        email_verified=True,
    )

@pytest.fixture(scope="function")
def sample_chart_data(created_user: User) -> ChartCreate:
    return ChartCreate(
        user_id=created_user.id,
        chart_type=ChartType.BIRTH_CHART,
        chart_name="Test Chart",
        birth_date=date(1990, 1, 1),
        birth_time=time(12, 0, 0),
        birth_location="New York, USA",
        birth_timezone="UTC",
        birth_latitude=40.7128,
        birth_longitude=-74.0060,
        house_system=HouseSystem.PLACIDUS,
        zodiac_system=ZodiacSystem.TROPICAL,
        ayanamsa=0.0,
        is_primary=False,
    )

# -----------------------
# Created Entities Fixtures
# -----------------------
@pytest_asyncio.fixture(scope="function")
async def created_user(user_service: UserService, sample_user_data: UserCreate) -> User:
    user = await user_service.create_user(sample_user_data)
    return user

@pytest_asyncio.fixture(scope="function")
async def created_chart(chart_service: ChartService, sample_chart_data: ChartCreate) -> Chart:
    chart = await chart_service.calculate_and_save_chart(sample_chart_data)
    return chart
