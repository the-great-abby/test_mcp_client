"""
Dependencies for FastAPI endpoints.
"""
from typing import Generator, Optional, AsyncGenerator
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import security
from app.core.config import settings
from app.db.session import get_db
from app.models.user import User
from app.schemas.token import TokenPayload

from sqlalchemy.ext.asyncio import AsyncSession
from app.core.redis import RedisClient
from app.core.websocket import WebSocketManager
from app.core.websocket_rate_limiter import WebSocketRateLimiter

from app.db.engine import get_engine, get_async_sessionmaker
from app.core.redis import get_redis as get_redis_client
from app.core.config import Settings

# Global WebSocket manager instance
_websocket_manager = None

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

async def get_websocket_manager() -> WebSocketManager:
    """Get WebSocket manager instance."""
    global _websocket_manager
    if not _websocket_manager:
        redis_client = await get_redis()
        _websocket_manager = WebSocketManager(redis_client)
    return _websocket_manager

# Alias for HTTP endpoints
get_websocket_manager_http = get_websocket_manager

# Alias for WebSocket endpoints
async def get_websocket_manager_ws() -> WebSocketManager:
    """Get WebSocket manager instance for WebSocket routes."""
    return await get_websocket_manager()

async def get_rate_limiter(redis: RedisClient = Depends(get_redis)) -> WebSocketRateLimiter:
    """Get WebSocket rate limiter."""
    return WebSocketRateLimiter(
        redis=redis,
        max_connections=settings.WS_MAX_CONNECTIONS_PER_USER
    )

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login"
)

async def get_current_request(request: Request = None) -> Request:
    """Get current FastAPI request object."""
    return request