from typing import AsyncGenerator
from fastapi import Request, Depends, WebSocket

from sqlalchemy.ext.asyncio import AsyncSession
from app.core.redis import RedisClient
from app.core.websocket import WebSocketManager
from app.core.websocket_rate_limiter import WebSocketRateLimiter

from app.db.engine import get_engine, get_async_sessionmaker
from app.core.redis import get_redis as get_redis_client
from app.core.config import settings, Settings


async def get_settings() -> Settings:
    """Dependency function to get the application settings."""
    return settings

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Get a database session.
    
    Yields:
        AsyncSession: The database session.
    """
    engine = get_engine()
    async_session = get_async_sessionmaker(engine)
    async with async_session() as session:
        yield session

async def get_redis() -> RedisClient:
    """
    Get a Redis client (async, singleton).
    """
    return await get_redis_client()

async def get_websocket_manager(redis: RedisClient = Depends(get_redis)) -> WebSocketManager:
    """Get WebSocket manager instance."""
    return WebSocketManager(
        redis_client=redis
    )

# Alias for HTTP endpoints
get_websocket_manager_http = get_websocket_manager

# Alias for WebSocket endpoints
async def get_websocket_manager_ws(
    websocket: WebSocket,
    manager: WebSocketManager = Depends(get_websocket_manager)
) -> WebSocketManager:
    """Get WebSocket manager for WebSocket endpoints."""
    return manager

async def get_rate_limiter(redis: RedisClient = Depends(get_redis)) -> WebSocketRateLimiter:
    """Get WebSocket rate limiter."""
    return WebSocketRateLimiter(
        redis=redis,
        max_connections_per_user=settings.WS_MAX_CONNECTIONS_PER_USER,
        max_connections_per_ip=20,  # Default from rate limiter
        connection_window_seconds=60,  # 1 minute window
        max_connections_per_window=50,  # Default from rate limiter
        message_window_seconds=1,  # 1 second window for message rate limiting
        max_messages_per_window=settings.WS_RATE_LIMIT
    )