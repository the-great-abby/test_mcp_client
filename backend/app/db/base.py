from sqlalchemy.orm import declarative_base
from sqlalchemy.ext.asyncio import AsyncSession
from typing import AsyncGenerator

# Create the SQLAlchemy declarative base
Base = declarative_base()

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting async database session."""
    from app.db.session import async_session
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close() 