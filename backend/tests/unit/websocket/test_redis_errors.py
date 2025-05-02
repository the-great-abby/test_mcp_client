"""Unit tests for WebSocket Redis error handling.

These tests verify the system's behavior when Redis encounters errors or becomes unavailable.
"""
import pytest
import asyncio
import uuid
from datetime import datetime, UTC, timedelta
from typing import List, Dict, Any
import logging
from websockets.exceptions import ConnectionClosed
from fastapi import status
from redis.exceptions import ConnectionError, TimeoutError, RedisError
from starlette.websockets import WebSocketState

from app.core.websocket import WebSocketManager
from app.core.websocket_rate_limiter import WebSocketRateLimiter
from tests.utils.websocket_test_helper import WebSocketTestHelper
from tests.utils.mock_websocket import MockWebSocket

logger = logging.getLogger(__name__)

# Test Configuration
TEST_USER_ID = "test_user_123"
TEST_IP = "192.168.1.100"
RATE_LIMIT_WINDOW = 60  # seconds
MAX_CONNECTIONS = 5
MESSAGES_PER_MINUTE = 60
MESSAGES_PER_HOUR = 1000
MESSAGES_PER_DAY = 10000
MAX_MESSAGES_PER_SECOND = 10
CONNECT_TIMEOUT = 5.0
MESSAGE_TIMEOUT = 1.0

@pytest.mark.unit
@pytest.mark.mock_service
class TestWebSocketRedisErrors:
    """Test suite for WebSocket Redis error handling."""

    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client that raises errors."""
        class MockRedisWithErrors:
            def __init__(self):
                self.error_mode = False
                self.store = {}
                
            async def get(self, key: str) -> str | None:
                if self.error_mode:
                    raise ConnectionError("Redis connection error")
                return self.store.get(key)
                
            async def set(self, key: str, value: str, ex: int | None = None) -> bool:
                if self.error_mode:
                    raise ConnectionError("Redis connection error")
                self.store[key] = value
                return True
                
            async def incr(self, key: str) -> int:
                if self.error_mode:
                    raise ConnectionError("Redis connection error")
                if key not in self.store:
                    self.store[key] = "0"
                self.store[key] = str(int(self.store[key]) + 1)
                return int(self.store[key])
                
            async def expire(self, key: str, seconds: int) -> bool:
                if self.error_mode:
                    raise ConnectionError("Redis connection error")
                return True
                
            def enable_errors(self):
                self.error_mode = True
                
            def disable_errors(self):
                self.error_mode = False
                
            async def clear_all(self):
                self.store.clear()
                self.error_mode = False
                
        return MockRedisWithErrors()

    @pytest.fixture
    def rate_limiter(self, mock_redis) -> WebSocketRateLimiter:
        """Create rate limiter with mock Redis."""
        return WebSocketRateLimiter(
            redis=mock_redis,
            max_connections=MAX_CONNECTIONS,
            messages_per_minute=MESSAGES_PER_MINUTE,
            messages_per_hour=MESSAGES_PER_HOUR,
            messages_per_day=MESSAGES_PER_DAY,
            max_messages_per_second=MAX_MESSAGES_PER_SECOND,
            rate_limit_window=RATE_LIMIT_WINDOW,
            connect_timeout=CONNECT_TIMEOUT,
            message_timeout=MESSAGE_TIMEOUT
        )

    @pytest.fixture
    async def ws_helper(self, websocket_manager, rate_limiter) -> WebSocketTestHelper:
        """Create WebSocket test helper."""
        helper = WebSocketTestHelper(
            websocket_manager=websocket_manager,
            rate_limiter=rate_limiter,
            test_user_id=TEST_USER_ID,
            test_ip=TEST_IP,
            connect_timeout=CONNECT_TIMEOUT,
            message_timeout=MESSAGE_TIMEOUT
        )
        try:
            yield helper
        finally:
            await helper.cleanup()

    async def test_redis_connection_error(self, ws_helper: WebSocketTestHelper, mock_redis):
        """Test handling of Redis connection errors."""
        client_id = str(uuid.uuid4())
        
        # Initial connection should work
        ws = await ws_helper.connect(client_id=client_id)
        assert ws.client_state == WebSocketState.CONNECTED
        
        # Enable Redis errors
        mock_redis.enable_errors()
        
        # Send message during Redis error
        response = await ws_helper.send_json(
            data={
                "type": "chat_message",
                "content": "Test message",
                "metadata": {}
            },
            client_id=client_id,
            ignore_errors=True
        )
        assert response["type"] == "error"
        assert "redis" in response["content"].lower()
        
        # Disable Redis errors
        mock_redis.disable_errors()
        
        # Send message after recovery
        response = await ws_helper.send_json(
            data={
                "type": "chat_message",
                "content": "Recovery message",
                "metadata": {}
            },
            client_id=client_id
        )
        assert response["type"] == "chat_message"
        assert response["content"] == "Recovery message"

    async def test_redis_rate_limit_error(self, ws_helper: WebSocketTestHelper, mock_redis):
        """Test rate limit handling during Redis errors."""
        client_id = str(uuid.uuid4())
        
        # Initial connection should work
        ws = await ws_helper.connect(client_id=client_id)
        assert ws.client_state == WebSocketState.CONNECTED
        
        # Enable Redis errors
        mock_redis.enable_errors()
        
        # Try to connect during Redis error
        client_id2 = str(uuid.uuid4())
        with pytest.raises(ConnectionClosed) as exc_info:
            await ws_helper.connect(client_id=client_id2)
        assert exc_info.value.rcvd.code == status.WS_1008_POLICY_VIOLATION
        assert "redis" in str(exc_info.value.rcvd.reason).lower()
        
        # Disable Redis errors
        mock_redis.disable_errors()
        
        # Should be able to connect after recovery
        ws2 = await ws_helper.connect(client_id=client_id2)
        assert ws2.client_state == WebSocketState.CONNECTED

    async def test_redis_cleanup_error(self, ws_helper: WebSocketTestHelper, mock_redis):
        """Test cleanup handling during Redis errors."""
        client_id = str(uuid.uuid4())
        
        # Initial connection should work
        ws = await ws_helper.connect(client_id=client_id)
        assert ws.client_state == WebSocketState.CONNECTED
        
        # Enable Redis errors
        mock_redis.enable_errors()
        
        # Disconnect during Redis error
        await ws_helper.disconnect(client_id)
        assert ws_helper.get_connection_state(client_id) == WebSocketState.DISCONNECTED
        
        # Disable Redis errors
        mock_redis.disable_errors()
        
        # Should be able to connect after recovery
        ws2 = await ws_helper.connect(client_id=client_id)
        assert ws2.client_state == WebSocketState.CONNECTED

    async def test_redis_message_tracking_error(self, ws_helper: WebSocketTestHelper, mock_redis):
        """Test message tracking during Redis errors."""
        client_id = str(uuid.uuid4())
        
        # Initial connection should work
        ws = await ws_helper.connect(client_id=client_id)
        assert ws.client_state == WebSocketState.CONNECTED
        
        # Send message before error
        response = await ws_helper.send_json(
            data={
                "type": "chat_message",
                "content": "Before error",
                "metadata": {}
            },
            client_id=client_id
        )
        assert response["type"] == "chat_message"
        
        # Enable Redis errors
        mock_redis.enable_errors()
        
        # Send message during error
        response = await ws_helper.send_json(
            data={
                "type": "chat_message",
                "content": "During error",
                "metadata": {}
            },
            client_id=client_id,
            ignore_errors=True
        )
        assert response["type"] == "error"
        assert "redis" in response["content"].lower()
        
        # Disable Redis errors
        mock_redis.disable_errors()
        
        # Send message after recovery
        response = await ws_helper.send_json(
            data={
                "type": "chat_message",
                "content": "After recovery",
                "metadata": {}
            },
            client_id=client_id
        )
        assert response["type"] == "chat_message"
        assert response["content"] == "After recovery"

    async def test_redis_system_message_error(self, ws_helper: WebSocketTestHelper, mock_redis):
        """Test system message handling during Redis errors."""
        client_id = str(uuid.uuid4())
        
        # Initial connection should work
        ws = await ws_helper.connect(client_id=client_id)
        assert ws.client_state == WebSocketState.CONNECTED
        
        # Enable Redis errors
        mock_redis.enable_errors()
        
        # System messages should still work during Redis errors
        response = await ws_helper.send_json(
            data={
                "type": "system",
                "content": "System message",
                "metadata": {"system_type": "test"}
            },
            client_id=client_id
        )
        assert response["type"] == "system"
        assert response["content"] == "System message"
        
        # Regular messages should fail
        response = await ws_helper.send_json(
            data={
                "type": "chat_message",
                "content": "Regular message",
                "metadata": {}
            },
            client_id=client_id,
            ignore_errors=True
        )
        assert response["type"] == "error"
        assert "redis" in response["content"].lower()
        
        # Disable Redis errors
        mock_redis.disable_errors()
        
        # Regular messages should work again
        response = await ws_helper.send_json(
            data={
                "type": "chat_message",
                "content": "After recovery",
                "metadata": {}
            },
            client_id=client_id
        )
        assert response["type"] == "chat_message"
        assert response["content"] == "After recovery" 