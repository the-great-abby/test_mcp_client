from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession
from app.core.redis import RedisClient

from app.db.session import AsyncSessionLocal
from app.core.redis import get_redis_client


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Get a database session.
    
    Yields:
        AsyncSession: The database session.
    """
    async with AsyncSessionLocal() as session:
        yield session

async def get_redis() -> AsyncGenerator[RedisClient, None]:
    """
    Get a Redis client.
    
    Yields:
        RedisClient: The Redis client.
    """
    client = await get_redis_client()
    yield client
    # Don't close the connection since it's a singleton 