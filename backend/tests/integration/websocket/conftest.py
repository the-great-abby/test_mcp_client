"""
Shared fixtures for WebSocket integration tests.
"""
import pytest
import asyncio
import uuid
from datetime import timedelta
from typing import AsyncGenerator, List
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
async def redis_rate_limiter(redis_client) -> AsyncGenerator[WebSocketRateLimiter, None]:
    """Get WebSocket rate limiter with proper cleanup."""
    limiter = WebSocketRateLimiter(
        redis=redis_client,
        max_connections=50,  # Higher limit for stress tests
        messages_per_minute=100,  # Higher limit for stress tests
        messages_per_hour=1000,
        messages_per_day=10000
    )
    try:
        yield limiter
    finally:
        await limiter.clear_all()

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
    limiter = WebSocketRateLimiter(
        redis=redis_client,
        max_connections=5,
        messages_per_minute=60,
        messages_per_hour=1000,
        messages_per_day=10000,
        max_messages_per_second=10,
        rate_limit_window=60,
        connect_timeout=5.0,
        message_timeout=1.0
    )
    try:
        yield limiter
    finally:
        await limiter.clear_all()

@pytest.fixture
async def test_helpers(
    websocket_manager: WebSocketManager,
    rate_limiter: WebSocketRateLimiter,
    test_user: User
) -> List[WebSocketTestHelper]:
    """List to track test helpers for cleanup.
    
    Pre-initializes a pool of helpers for stress testing.
    """
    helpers = []
    # Pre-initialize 50 helpers for stress testing
    for i in range(50):
        helper = WebSocketTestHelper(
            websocket_manager=websocket_manager,
            rate_limiter=rate_limiter,
            test_user_id=test_user.id,
            test_ip=f"192.168.1.{i+1}"  # Use unique IPs for rate limiting
        )
        helpers.append(helper)
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
def auth_token(test_user: User) -> str:
    """Create an authentication token for testing."""
    return create_access_token(
        data={"sub": str(test_user.id)},
        expires_delta=timedelta(minutes=15)
    )

@pytest.fixture
async def ws_helper(
    websocket_manager: WebSocketManager,
    rate_limiter: WebSocketRateLimiter,
    test_helpers: List[WebSocketTestHelper],
    test_user: User,
    auth_token: str
) -> AsyncGenerator[WebSocketTestHelper, None]:
    """Get WebSocket test helper."""
    helper = WebSocketTestHelper(
        websocket_manager=websocket_manager,
        rate_limiter=rate_limiter,
        test_user_id=test_user.id,
        auth_token=auth_token
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