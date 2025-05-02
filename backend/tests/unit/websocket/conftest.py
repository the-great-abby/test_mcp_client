"""
Shared fixtures for WebSocket unit tests.
"""
import pytest
import asyncio
from typing import AsyncGenerator, List
from unittest.mock import MagicMock, AsyncMock
from app.core.websocket import WebSocketManager
from app.core.websocket_rate_limiter import WebSocketRateLimiter
from tests.utils.websocket_test_helper import WebSocketTestHelper, MockWebSocket

@pytest.fixture
def mock_redis():
    """Get mock Redis client."""
    redis = AsyncMock()
    redis.get.return_value = None
    redis.set.return_value = True
    redis.delete.return_value = 1
    redis.exists.return_value = 0
    redis.incr.return_value = 1
    redis.expire.return_value = True
    redis.flushdb.return_value = True
    return redis

@pytest.fixture
async def websocket_manager(mock_redis) -> AsyncGenerator[WebSocketManager, None]:
    """Get WebSocket manager instance with mock Redis."""
    manager = WebSocketManager(redis_client=mock_redis)
    try:
        yield manager
    finally:
        await manager.clear_all_connections()

@pytest.fixture
async def rate_limiter(mock_redis) -> AsyncGenerator[WebSocketRateLimiter, None]:
    """Get rate limiter instance with mock Redis."""
    limiter = WebSocketRateLimiter(
        redis=mock_redis,
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
def test_helpers() -> List[WebSocketTestHelper]:
    """List to track test helpers for cleanup."""
    helpers = []
    return helpers

@pytest.fixture
async def ws_helper(
    websocket_manager: WebSocketManager,
    rate_limiter: WebSocketRateLimiter,
    test_helpers: List[WebSocketTestHelper]
) -> AsyncGenerator[WebSocketTestHelper, None]:
    """Get WebSocket test helper."""
    helper = WebSocketTestHelper(
        websocket_manager=websocket_manager,
        rate_limiter=rate_limiter
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

@pytest.fixture
def mock_websocket():
    """Get mock WebSocket instance."""
    return MockWebSocket()

class ErrorInjectingRedis:
    """Redis mock that can inject errors for testing."""
    
    def __init__(self):
        self.store = {}
        self.error_queue = []
        
    def inject_error(self, error: Exception, count: int = 1):
        """Inject an error to be raised on next operations."""
        for _ in range(count):
            self.error_queue.append(error)
            
    async def _maybe_raise_error(self):
        """Raise error if one is queued."""
        if self.error_queue:
            raise self.error_queue.pop(0)
            
    async def get(self, key: str):
        await self._maybe_raise_error()
        return self.store.get(key)
        
    async def set(self, key: str, value: str):
        await self._maybe_raise_error()
        self.store[key] = value
        return True
        
    async def delete(self, key: str):
        await self._maybe_raise_error()
        if key in self.store:
            del self.store[key]
            return 1
        return 0
        
    async def exists(self, key: str):
        await self._maybe_raise_error()
        return int(key in self.store)
        
    async def incr(self, key: str):
        await self._maybe_raise_error()
        if key not in self.store:
            self.store[key] = "0"
        value = int(self.store[key]) + 1
        self.store[key] = str(value)
        return value
        
    async def expire(self, key: str, seconds: int):
        await self._maybe_raise_error()
        return True
        
    async def flushdb(self):
        await self._maybe_raise_error()
        self.store.clear()
        return True
        
    async def aclose(self):
        await self._maybe_raise_error()

@pytest.fixture
def error_redis():
    """Get error injecting Redis instance."""
    return ErrorInjectingRedis() 