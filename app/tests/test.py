# test_async.py
import asyncio
import asyncpg
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class TestModel(Base):
    __tablename__ = 'test_table'
    id = Column(Integer, primary_key=True)
    name = Column(String)

async def test_async():
    # Test asyncpg directly
    try:
        conn = await asyncpg.connect('postgresql://localhost:5432/aiAstrologerDb')
        print("✅ asyncpg connection successful")
        await conn.close()
    except Exception as e:
        print(f"❌ asyncpg error: {e}")
    
    # Test SQLAlchemy async
    try:
        engine = create_async_engine('postgresql+asyncpg://localhost:5432/aiAstrologerDb')
        async with engine.connect() as conn:
            print("✅ SQLAlchemy async connection successful")
    except Exception as e:
        print(f"❌ SQLAlchemy async error: {e}")

if __name__ == "__main__":
    asyncio.run(test_async())