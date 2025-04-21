from sqlalchemy.orm import declarative_base
from sqlalchemy.ext.asyncio import AsyncSession
from typing import AsyncGenerator
from app.db.engine import async_session

# Create the SQLAlchemy declarative base
Base = declarative_base()

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting async database session."""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close() 