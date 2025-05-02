"""Unit tests for WebSocket rate limiting functionality."""
import pytest
import asyncio
import uuid
import logging
from datetime import datetime, UTC, timedelta
from typing import List, Dict, Any
from websockets.exceptions import ConnectionClosed
from fastapi import WebSocket, status
from starlette.websockets import WebSocketState

from app.core.websocket import WebSocketManager
from app.core.websocket_rate_limiter import WebSocketRateLimiter
from tests.utils.websocket_test_helper import WebSocketTestHelper, MockWebSocket
from app.core.auth import create_access_token

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
class TestWebSocketRateLimiter:
    """Test suite for WebSocket rate limiting."""

    @pytest.fixture
    def auth_token(self):
        """Create a valid auth token for testing."""
        return create_access_token(data={"sub": TEST_USER_ID})

    @pytest.fixture
    def mock_websocket(self):
        """Mock WebSocket connection."""
        mock = MockWebSocket()
        mock.client.host = "127.0.0.1"
        mock.client_state.client = MockWebSocket()
        mock.client_state.client.host = "127.0.0.1"
        return mock

    @pytest.fixture
    def mock_user(self):
        """Mock user for testing."""
        return User(
            id=uuid.uuid4(),
            email="test@example.com",
            username="testuser",
            is_active=True
        )

    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client."""
        mock = MockRedis()
        mock.get = MockRedis.get
        mock.set = MockRedis.set
        mock.incr = MockRedis.incr
        mock.expire = MockRedis.expire
        return mock

    @pytest.fixture
    def rate_limiter(self, mock_redis):
        """Get rate limiter instance with mock Redis."""
        return WebSocketRateLimiter(
            redis=mock_redis,
            max_connections=2,
            messages_per_minute=60,
            messages_per_hour=1000,
            messages_per_day=10000,
            max_messages_per_second=1,
            rate_limit_window=60,
            connect_timeout=5.0,
            message_timeout=1.0
        )

    @pytest.mark.asyncio
    async def test_connection_limit(self, websocket_manager: WebSocketManager, auth_token: str):
        """Test connection rate limiting."""
        rate_limiter = WebSocketRateLimiter(
            redis=None,  # No Redis needed for basic rate limiting
            max_connections=2,  # Low limit for testing
            messages_per_minute=MESSAGES_PER_MINUTE,
            messages_per_hour=MESSAGES_PER_HOUR,
            messages_per_day=MESSAGES_PER_DAY,
            max_messages_per_second=MAX_MESSAGES_PER_SECOND,
            rate_limit_window=RATE_LIMIT_WINDOW,
            connect_timeout=CONNECT_TIMEOUT,
            message_timeout=MESSAGE_TIMEOUT
        )
        
        helper = WebSocketTestHelper(
            websocket_manager=websocket_manager,
            rate_limiter=rate_limiter,
            test_user_id=TEST_USER_ID,
            test_ip=TEST_IP,
            auth_token=auth_token
        )
        
        try:
            # First connection should succeed
            client_id1 = str(uuid.uuid4())
            ws1 = await helper.connect(client_id=client_id1)
            assert ws1.client_state == WebSocketState.CONNECTED
            
            # Second connection should succeed
            client_id2 = str(uuid.uuid4())
            ws2 = await helper.connect(client_id=client_id2)
            assert ws2.client_state == WebSocketState.CONNECTED
            
            # Third connection should fail
            client_id3 = str(uuid.uuid4())
            with pytest.raises(ConnectionClosed) as exc_info:
                await helper.connect(client_id=client_id3)
            assert exc_info.value.rcvd.code == status.WS_1008_POLICY_VIOLATION
            assert "limit" in str(exc_info.value.rcvd.reason).lower()
            
        finally:
            await helper.cleanup()
    
    @pytest.mark.asyncio
    async def test_message_rate_limit(self, websocket_manager: WebSocketManager, auth_token: str):
        """Test message rate limiting."""
        rate_limiter = WebSocketRateLimiter(
            redis=None,  # No Redis needed for basic rate limiting
            max_connections=MAX_CONNECTIONS,
            messages_per_minute=60,  # Normal limit
            messages_per_hour=MESSAGES_PER_HOUR,
            messages_per_day=MESSAGES_PER_DAY,
            max_messages_per_second=1,  # Low limit for testing
            rate_limit_window=RATE_LIMIT_WINDOW,
            connect_timeout=CONNECT_TIMEOUT,
            message_timeout=MESSAGE_TIMEOUT
        )
        
        helper = WebSocketTestHelper(
            websocket_manager=websocket_manager,
            rate_limiter=rate_limiter,
            test_user_id=TEST_USER_ID,
            test_ip=TEST_IP,
            auth_token=auth_token
        )
        
        try:
            # Connect client
            client_id = str(uuid.uuid4())
            ws = await helper.connect(client_id=client_id)
            assert ws.client_state == WebSocketState.CONNECTED
            
            # First message should succeed
            response = await helper.send_json(
                data={
                    "type": "chat_message",
                    "content": "First message",
                    "metadata": {}
                },
                client_id=client_id
            )
            assert response["type"] == "chat_message"
            
            # Second message in same second should fail
            response = await helper.send_json(
                data={
                    "type": "chat_message",
                    "content": "Second message",
                    "metadata": {}
                },
                client_id=client_id,
                ignore_errors=True
            )
            assert response["type"] == "error"
            assert "rate limit" in response["content"].lower()
            
        finally:
            await helper.cleanup()
    
    @pytest.mark.asyncio
    async def test_connection_cleanup(self, websocket_manager: WebSocketManager, auth_token: str):
        """Test connection cleanup."""
        rate_limiter = WebSocketRateLimiter(
            redis=None,  # No Redis needed for basic rate limiting
            max_connections=2,  # Low limit for testing
            messages_per_minute=MESSAGES_PER_MINUTE,
            messages_per_hour=MESSAGES_PER_HOUR,
            messages_per_day=MESSAGES_PER_DAY,
            max_messages_per_second=MAX_MESSAGES_PER_SECOND,
            rate_limit_window=RATE_LIMIT_WINDOW,
            connect_timeout=CONNECT_TIMEOUT,
            message_timeout=MESSAGE_TIMEOUT
        )
        
        helper = WebSocketTestHelper(
            websocket_manager=websocket_manager,
            rate_limiter=rate_limiter,
            test_user_id=TEST_USER_ID,
            test_ip=TEST_IP,
            auth_token=auth_token
        )
        
        try:
            # Create two connections
            client_id1 = str(uuid.uuid4())
            ws1 = await helper.connect(client_id=client_id1)
            assert ws1.client_state == WebSocketState.CONNECTED
            
            client_id2 = str(uuid.uuid4())
            ws2 = await helper.connect(client_id=client_id2)
            assert ws2.client_state == WebSocketState.CONNECTED
            
            # Disconnect first connection
            await helper.disconnect(client_id1)
            assert helper.get_connection_state(client_id1) == WebSocketState.DISCONNECTED
            
            # Should be able to create new connection
            client_id3 = str(uuid.uuid4())
            ws3 = await helper.connect(client_id=client_id3)
            assert ws3.client_state == WebSocketState.CONNECTED
            
        finally:
            await helper.cleanup()
    
    @pytest.mark.asyncio
    async def test_system_message_bypass(self, websocket_manager: WebSocketManager, auth_token: str):
        """Test system messages bypass rate limiting."""
        rate_limiter = WebSocketRateLimiter(
            redis=None,  # No Redis needed for basic rate limiting
            max_connections=MAX_CONNECTIONS,
            messages_per_minute=1,  # Very low limit for testing
            messages_per_hour=MESSAGES_PER_HOUR,
            messages_per_day=MESSAGES_PER_DAY,
            max_messages_per_second=1,
            rate_limit_window=RATE_LIMIT_WINDOW,
            connect_timeout=CONNECT_TIMEOUT,
            message_timeout=MESSAGE_TIMEOUT
        )
        
        helper = WebSocketTestHelper(
            websocket_manager=websocket_manager,
            rate_limiter=rate_limiter,
            test_user_id=TEST_USER_ID,
            test_ip=TEST_IP,
            auth_token=auth_token
        )
        
        try:
            # Connect client
            client_id = str(uuid.uuid4())
            ws = await helper.connect(client_id=client_id)
            assert ws.client_state == WebSocketState.CONNECTED
            
            # Send normal message to hit rate limit
            response = await helper.send_json(
                data={
                    "type": "chat_message",
                    "content": "Normal message",
                    "metadata": {}
                },
                client_id=client_id
            )
            assert response["type"] == "chat_message"
            
            # System message should bypass rate limit
            response = await helper.send_json(
                data={
                    "type": "system",
                    "content": "System message",
                    "metadata": {"system_type": "test"}
                },
                client_id=client_id
            )
            assert response["type"] == "system"
            assert response["content"] == "System message"
            
            # Normal message should still be rate limited
            response = await helper.send_json(
                data={
                    "type": "chat_message",
                    "content": "Rate limited message",
                    "metadata": {}
                },
                client_id=client_id,
                ignore_errors=True
            )
            assert response["type"] == "error"
            assert "rate limit" in response["content"].lower()
            
        finally:
            await helper.cleanup()
    
    @pytest.mark.asyncio
    async def test_clear_connection_count(self, websocket_manager: WebSocketManager, auth_token: str):
        """Test clearing connection count."""
        rate_limiter = WebSocketRateLimiter(
            redis=None,  # No Redis needed for basic rate limiting
            max_connections=2,  # Low limit for testing
            messages_per_minute=MESSAGES_PER_MINUTE,
            messages_per_hour=MESSAGES_PER_HOUR,
            messages_per_day=MESSAGES_PER_DAY,
            max_messages_per_second=MAX_MESSAGES_PER_SECOND,
            rate_limit_window=RATE_LIMIT_WINDOW,
            connect_timeout=CONNECT_TIMEOUT,
            message_timeout=MESSAGE_TIMEOUT
        )
        
        helper = WebSocketTestHelper(
            websocket_manager=websocket_manager,
            rate_limiter=rate_limiter,
            test_user_id=TEST_USER_ID,
            test_ip=TEST_IP,
            auth_token=auth_token
        )
        
        try:
            # Create connection
            client_id = str(uuid.uuid4())
            ws = await helper.connect(client_id=client_id)
            assert ws.client_state == WebSocketState.CONNECTED
            
            # Clear connection count
            await rate_limiter.clear_connection_count(TEST_USER_ID)
            
            # Should be able to create new connection
            client_id2 = str(uuid.uuid4())
            ws2 = await helper.connect(client_id=client_id2)
            assert ws2.client_state == WebSocketState.CONNECTED
            
        finally:
            await helper.cleanup()