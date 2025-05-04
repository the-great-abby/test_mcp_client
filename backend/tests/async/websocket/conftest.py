"""
Shared fixtures for WebSocket async tests.
"""
import pytest
import asyncio
import uuid
from typing import AsyncGenerator, List
from datetime import timedelta
from app.core.websocket import WebSocketManager
from app.core.websocket_rate_limiter import WebSocketRateLimiter
from app.core.redis import get_redis
from app.core.auth import create_access_token
from app.models import User
from tests.utils.websocket_test_helper import WebSocketTestHelper

@pytest.fixture
async def redis_client() -> AsyncGenerator:
    """Get Redis client for testing."""
    redis = await get_redis()
    try:
        yield redis
    finally:
        await redis.flushdb()
        await redis.aclose()

@pytest.fixture
async def websocket_manager(redis_client) -> AsyncGenerator[WebSocketManager, None]:
    """Get WebSocket manager instance."""
    manager = WebSocketManager(redis_client=redis_client)
    try:
        yield manager
    finally:
        await manager.clear_all_connections()

@pytest.fixture
async def rate_limiter(redis_client) -> AsyncGenerator[WebSocketRateLimiter, None]:
    """Get rate limiter instance."""
    limiter = WebSocketRateLimiter(redis=redis_client)
    try:
        yield limiter
    finally:
        await limiter.clear_all()

@pytest.fixture
def test_helpers() -> List[WebSocketTestHelper]:
    """List to track test helpers for cleanup."""
    helpers = []
    return helpers

@pytest.fixture
async def test_user() -> User:
    """Create a test user."""
    return User(
        id=str(uuid.uuid4()),
        email="test@example.com",
        hashed_password="test_hash",
        is_active=True
    )

@pytest.fixture
def test_token(test_user: User) -> str:
    """Create a test token."""
    return create_access_token(
        subject=test_user.id,
        expires_delta=timedelta(minutes=15)
    )

@pytest.fixture
async def websocket_helper(
    websocket_manager: WebSocketManager,
    rate_limiter: WebSocketRateLimiter,
    test_helpers: List[WebSocketTestHelper],
    test_user: User,
    test_token: str
) -> AsyncGenerator[WebSocketTestHelper, None]:
    """Get WebSocket test helper with auth."""
    helper = WebSocketTestHelper(
        websocket_manager=websocket_manager,
        rate_limiter=rate_limiter,
        test_user_id=test_user.id,
        auth_token=test_token
    )
    test_helpers.append(helper)
    try:
        yield helper
    finally:
        await helper.cleanup()

@pytest.fixture(autouse=True)
async def cleanup_helpers(test_helpers: List[WebSocketTestHelper]):
    """Automatically clean up all test helpers."""
    try:
        yield
    finally:
        for helper in test_helpers:
            await helper.cleanup() 