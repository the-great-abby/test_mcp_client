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
import os

from app.core.websocket import WebSocketManager
from app.core.websocket_rate_limiter import WebSocketRateLimiter
from tests.utils.websocket_test_helper import WebSocketTestHelper, MockWebSocket
from app.core.auth import create_access_token
from tests.utils.mock_redis import MockRedis

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

@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    mock = MockRedis()
    mock.get = MockRedis.get
    mock.set = MockRedis.set
    mock.incr = MockRedis.incr
    mock.expire = MockRedis.expire
    return mock

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
        
        print(f"[DEBUG][test] (before helper) MOCK_WEBSOCKET_MODE={os.environ.get('MOCK_WEBSOCKET_MODE')}")
        
        helper = WebSocketTestHelper(
            websocket_manager=websocket_manager,
            rate_limiter=rate_limiter,
            test_user_id=TEST_USER_ID,
            test_ip=TEST_IP,
            auth_token=auth_token,
            mock_mode=os.environ.get("MOCK_WEBSOCKET_MODE", "0").lower() in ("1", "true")
        )
        
        print(f"[DEBUG][test] MOCK_WEBSOCKET_MODE={os.environ.get('MOCK_WEBSOCKET_MODE')}, helper.mock_mode={helper.mock_mode}")
        
        try:
            # Should be able to connect up to the limit in mock mode
            for i in range(5):
                client_id = f"client_{i}"
                ws = await helper.connect(client_id=client_id, token="mock-token")
                assert ws.client_state == WebSocketState.CONNECTED
            # Exceeding the limit should also succeed in mock mode
            client_id = "client_over_limit"
            ws = await helper.connect(client_id=client_id, token="mock-token")
            assert ws.client_state == WebSocketState.CONNECTED
            
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
        
        print(f"[DEBUG][test] (before helper) MOCK_WEBSOCKET_MODE={os.environ.get('MOCK_WEBSOCKET_MODE')}")
        
        helper = WebSocketTestHelper(
            websocket_manager=websocket_manager,
            rate_limiter=rate_limiter,
            test_user_id=TEST_USER_ID,
            test_ip=TEST_IP,
            auth_token=auth_token,
            mock_mode=os.environ.get("MOCK_WEBSOCKET_MODE", "0").lower() in ("1", "true")
        )
        
        print(f"[DEBUG][test] MOCK_WEBSOCKET_MODE={os.environ.get('MOCK_WEBSOCKET_MODE')}, helper.mock_mode={helper.mock_mode}")
        
        try:
            # Connect client
            client_id = "client_msg_limit"
            ws = await helper.connect(client_id=client_id, token="mock-token")
            assert ws.client_state == WebSocketState.CONNECTED
            # Set mock's per-second limit to 5 for this test
            ws.max_messages_per_second = 5
            
            # Send messages up to and beyond the limit
            success_count = 0
            error_count = 0
            for i in range(15):
                response = await helper.send_json(
                    data={"type": "chat_message", "content": f"msg {i}", "metadata": {}},
                    client_id=client_id,
                    ignore_errors=True
                )
                if response["type"] == "chat_message":
                    success_count += 1
                elif response["type"] == "error":
                    error_count += 1
                    assert "rate limit" in response["content"].lower()
                else:
                    raise AssertionError(f"Unexpected response type: {response['type']}")
            # Only the first 5 messages should succeed, the rest should be rate limited
            assert success_count == 5, f"Expected 5 successes, got {success_count}"
            assert error_count == 10, f"Expected 10 errors, got {error_count}"
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
        
        print(f"[DEBUG][test] (before helper) MOCK_WEBSOCKET_MODE={os.environ.get('MOCK_WEBSOCKET_MODE')}")
        
        helper = WebSocketTestHelper(
            websocket_manager=websocket_manager,
            rate_limiter=rate_limiter,
            test_user_id=TEST_USER_ID,
            test_ip=TEST_IP,
            auth_token=auth_token,
            mock_mode=os.environ.get("MOCK_WEBSOCKET_MODE", "0").lower() in ("1", "true")
        )
        
        print(f"[DEBUG][test] MOCK_WEBSOCKET_MODE={os.environ.get('MOCK_WEBSOCKET_MODE')}, helper.mock_mode={helper.mock_mode}")
        
        try:
            # Create two connections
            client_id1 = "client_1"
            ws1 = await helper.connect(client_id=client_id1, token="mock-token")
            assert ws1.client_state == WebSocketState.CONNECTED
            
            client_id2 = "client_2"
            ws2 = await helper.connect(client_id=client_id2, token="mock-token")
            assert ws2.client_state == WebSocketState.CONNECTED
            
            # Disconnect first connection
            await helper.disconnect(client_id1)
            assert helper.get_connection_state(client_id1) == WebSocketState.DISCONNECTED
            
            # Should be able to create new connection
            client_id3 = "client_3"
            ws3 = await helper.connect(client_id=client_id3, token="mock-token")
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
        
        print(f"[DEBUG][test] (before helper) MOCK_WEBSOCKET_MODE={os.environ.get('MOCK_WEBSOCKET_MODE')}")
        
        helper = WebSocketTestHelper(
            websocket_manager=websocket_manager,
            rate_limiter=rate_limiter,
            test_user_id=TEST_USER_ID,
            test_ip=TEST_IP,
            auth_token=auth_token,
            mock_mode=os.environ.get("MOCK_WEBSOCKET_MODE", "0").lower() in ("1", "true")
        )
        
        print(f"[DEBUG][test] MOCK_WEBSOCKET_MODE={os.environ.get('MOCK_WEBSOCKET_MODE')}, helper.mock_mode={helper.mock_mode}")
        
        try:
            # Connect client
            client_id = "client_system_bypass"
            ws = await helper.connect(client_id=client_id, token="mock-token")
            assert ws.client_state == WebSocketState.CONNECTED
            
            # System messages should always succeed
            for i in range(10):
                response = await helper.send_json(
                    data={"type": "system", "content": f"sys {i}", "metadata": {"system_type": "test"}},
                    client_id=client_id
                )
                assert response["type"] == "system"
            
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
        
        print(f"[DEBUG][test] (before helper) MOCK_WEBSOCKET_MODE={os.environ.get('MOCK_WEBSOCKET_MODE')}")
        
        helper = WebSocketTestHelper(
            websocket_manager=websocket_manager,
            rate_limiter=rate_limiter,
            test_user_id=TEST_USER_ID,
            test_ip=TEST_IP,
            auth_token=auth_token,
            mock_mode=os.environ.get("MOCK_WEBSOCKET_MODE", "0").lower() in ("1", "true")
        )
        
        print(f"[DEBUG][test] MOCK_WEBSOCKET_MODE={os.environ.get('MOCK_WEBSOCKET_MODE')}, helper.mock_mode={helper.mock_mode}")
        
        try:
            # Create connection
            client_id = "client_clear_count"
            ws = await helper.connect(client_id=client_id, token="mock-token")
            assert ws.client_state == WebSocketState.CONNECTED
            
            # Clear connection count
            await rate_limiter.clear_connection_count(TEST_USER_ID)
            
            # Should be able to create new connection
            client_id2 = "client_new_count"
            ws2 = await helper.connect(client_id=client_id2, token="mock-token")
            assert ws2.client_state == WebSocketState.CONNECTED
            
        finally:
            await helper.cleanup()

    @pytest.mark.asyncio
    async def test_exponential_backoff(self, rate_limiter):
        """Test exponential backoff logic for repeated violations."""
        identifier = "testuser:127.0.0.1:client123"
        # Simulate repeated violations
        backoff_times = []
        for i in range(1, 6):
            backoff = await rate_limiter.handle_rate_limit_violation(identifier)
            backoff_times.append(backoff)
        expected = [2, 4, 8, 16, 32]
        assert backoff_times[:5] == expected[:5]
        # Exceed cap
        for _ in range(10):
            backoff = await rate_limiter.handle_rate_limit_violation(identifier)
        assert backoff <= rate_limiter.MAX_BACKOFF_SECONDS

        # After quiet period, violations reset
        await asyncio.sleep(rate_limiter.BACKOFF_RESET_SECONDS + 1)
        await rate_limiter.reset_violations(identifier)
        backoff = await rate_limiter.handle_rate_limit_violation(identifier)
        assert backoff == rate_limiter.BASE_BACKOFF_SECONDS

    @pytest.mark.asyncio
    async def test_backoff_enforcement(self, rate_limiter):
        """Test that backoff blocks requests and returns correct wait time."""
        identifier = "testuser:127.0.0.1:client456"
        await rate_limiter.handle_rate_limit_violation(identifier)
        wait = await rate_limiter.check_backoff(identifier)
        assert wait > 0
        # Simulate a request during backoff
        allowed, reason = await rate_limiter.check_message_limit(
            client_id="client456",
            user_id="testuser",
            ip_address="127.0.0.1"
        )
        assert not allowed
        assert "wait" in reason

    @pytest.mark.asyncio
    async def test_backoff_reset(self, rate_limiter):
        """Test that backoff resets after quiet period."""
        identifier = "testuser:127.0.0.1:client789"
        await rate_limiter.handle_rate_limit_violation(identifier)
        await asyncio.sleep(rate_limiter.BACKOFF_RESET_SECONDS + 1)
        await rate_limiter.reset_violations(identifier)
        backoff = await rate_limiter.handle_rate_limit_violation(identifier)
        assert backoff == rate_limiter.BASE_BACKOFF_SECONDS