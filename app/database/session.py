# app/database/session.py
from sqlmodel import create_engine, SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.schemas.user import User
from app.schemas.admin import AdminUser
from app.schemas.chart import Chart
# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=True,  # Set to False in production
    future=True,
)

# Create async session factory
async_session = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def get_db_session() -> AsyncSession:
    """Dependency to get async database session."""
    async with async_session() as session:
        yield session

async def create_db_and_tables():
    """Create all database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(User.metadata.create_all)
        await conn.run_sync(AdminUser.metadata.create_all)
        await conn.run_sync(Chart.metadata.create_all)

     # Initialize Redis
    await initialize_redis()