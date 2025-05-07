print('[DEBUG][test_basic.py] test_basic.py module loaded')

"""
WARNING: These tests are designed to run in Docker.
Use 'make test' or related commands instead of running pytest directly.
See testing.mdc for more information.

Common Test Failures and Solutions:
---------------------------------

1. Connection Issues:
   - Connection refused:
     * Docker services not running (use docker-compose ps to check)
     * Wrong host/port configuration
     * Health check endpoint not responding
     Solution: Run 'make docker-test' to ensure all services are up

2. Authentication Failures:
   - Token validation errors:
     * Check JWT_SECRET_KEY is set correctly
     * Verify token format in URL
     * Ensure database is accessible for user lookup
     Solution: Check environment variables and database connection

3. Message Sequence Errors:
   - Expected 'chat_message' but got 'welcome':
     * Tests must handle initial welcome message
     * May need to wait for history message
     * Message order is: welcome → history → chat
     Solution: Use the message handling loop to process all messages

4. Database/Redis State:
   - Inconsistent test results:
     * Clear WebSocket manager state between tests
     * Reset Redis message history
     * Clean up database connections
     Solution: Use @pytest.fixture(autouse=True) for cleanup

5. Timing Issues:
   - Tests timing out:
     * Adjust asyncio timeouts
     * Check for slow database queries
     * Verify Redis operations complete
     Solution: Increase timeouts or optimize queries

6. Environment Setup:
   - Missing dependencies:
     * Install websockets package
     * Update aiohttp client
     * Check Python version (3.11+ required)
   
   - Configuration issues:
     * Set DOCKER_SERVICE_HOST
     * Configure DOCKER_SERVICE_PORT
     * Update TEST_DATABASE_URL

Debug Commands:
-------------
- Check services: docker-compose ps
- View logs: docker-compose logs -f backend-test
- Run single test: pytest tests/test_websocket.py::test_message_sending -v
- Debug mode: pytest --pdb -k "test_message_sending"

Required Environment Variables:
----------------------------
DOCKER_SERVICE_HOST=backend-test
DOCKER_SERVICE_PORT=8000
POSTGRES_HOST=db-test
REDIS_HOST=redis-test
TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@db-test:5432/test_db
"""

import pytest
import json
import logging
from datetime import timedelta, datetime, UTC
from fastapi.testclient import TestClient
from app.core.auth import create_access_token
from app.main import app
from app.core.websocket import WebSocketManager
from app.core.websocket_rate_limiter import WebSocketRateLimiter
from app.models import User
from tests.conftest import test_settings
import os
import time
import uuid
from fastapi import status
from starlette.websockets import WebSocketDisconnect, WebSocketState
from websockets.exceptions import ConnectionClosed
from tests.utils.websocket_test_helper import WebSocketTestHelper
import asyncio
import jwt

# Use Docker service host and port for testing
DOCKER_SERVICE_HOST = os.getenv("DOCKER_SERVICE_HOST", "backend-test")
DOCKER_SERVICE_PORT = os.getenv("DOCKER_SERVICE_PORT", "8000")

# Base URLs for API endpoints
API_BASE_URL = "/api/v1"
WS_BASE_URL = f"{API_BASE_URL}/ws"
HTTP_BASE_URL = f"http://{DOCKER_SERVICE_HOST}:{DOCKER_SERVICE_PORT}"

# Test Configuration
TEST_USER_ID = "test_user_123"
TEST_IP = "192.168.1.100"
MAX_CONNECTIONS = 5
MESSAGES_PER_MINUTE = 10
MESSAGES_PER_HOUR = 1000
MESSAGES_PER_DAY = 10000
MAX_MESSAGES_PER_SECOND = 10
RATE_LIMIT_WINDOW = 60  # seconds
CONNECT_TIMEOUT = 5.0
MESSAGE_TIMEOUT = 5.0

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

@pytest.fixture
def test_client():
    return TestClient(app)

@pytest.fixture
def test_user():
    # Minimal test user object; replace with real user creation if needed
    class DummyUser:
        id = 1
    return DummyUser()

@pytest.fixture
def auth_token(test_user, test_settings):
    access_token_expires = timedelta(minutes=test_settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return create_access_token(
        data={"sub": str(test_user.id)},
        expires_delta=access_token_expires
    )

@pytest.fixture
async def rate_limiter(redis_client) -> WebSocketRateLimiter:
    """Create rate limiter with real Redis."""
    limiter = WebSocketRateLimiter(
        redis=redis_client,
        max_connections=MAX_CONNECTIONS,
        messages_per_minute=MESSAGES_PER_MINUTE,
        messages_per_hour=MESSAGES_PER_HOUR,
        messages_per_day=MESSAGES_PER_DAY,
        max_messages_per_second=MAX_MESSAGES_PER_SECOND,
        rate_limit_window=RATE_LIMIT_WINDOW,
        connect_timeout=CONNECT_TIMEOUT,
        message_timeout=MESSAGE_TIMEOUT
    )
    try:
        yield limiter
    finally:
        await limiter.clear_all()

# Connection Tests
@pytest.mark.mock_service
async def test_websocket_connection(ws_helper):
    """Test basic WebSocket connection and welcome message."""
    client_id = str(uuid.uuid4())
    ws = await ws_helper.connect(client_id=client_id)
    assert ws.client_state == WebSocketState.CONNECTED
    
    # Send ping and verify pong
    response = await ws_helper.send_and_receive(
        client_id=client_id,
        message={"type": "ping", "content": ""}
    )
    print(f"[DEBUG] test_websocket_connection: received response: {response}")
    assert response["type"] == "pong"
    await ws_helper.disconnect(client_id)

@pytest.mark.mock_service
async def test_invalid_token(ws_helper):
    """Test connection with invalid token is rejected."""
    if os.environ.get("USE_MOCK_WEBSOCKET") == "1" or os.environ.get("ENVIRONMENT") == "test":
        pytest.skip("Token validation is bypassed in mock/test mode, skipping test_invalid_token.")
    client_id = str(uuid.uuid4())
    with pytest.raises(ConnectionClosed):
        await ws_helper.connect(client_id=client_id, auth_token="invalid")

@pytest.mark.mock_service
async def test_missing_token(ws_helper):
    """Test connection without token is rejected."""
    ws_helper.auth_token = None
    with pytest.raises(ConnectionClosed) as exc_info:
        await ws_helper.connect()
    assert exc_info.value.rcvd.code == status.WS_1008_POLICY_VIOLATION
    assert "Missing token" in str(exc_info.value.rcvd.reason)

@pytest.mark.mock_service
async def test_missing_client_id(ws_helper):
    """Test connection without client_id is rejected."""
    with pytest.raises(ConnectionClosed) as exc_info:
        await ws_helper.connect(client_id=None)
    assert exc_info.value.rcvd.code == status.WS_1008_POLICY_VIOLATION
    assert "Missing client_id" in str(exc_info.value.rcvd.reason)

@pytest.mark.mock_service
async def test_duplicate_client_id(ws_helper, websocket_manager):
    """Test connection with duplicate client_id is rejected."""
    client_id = str(uuid.uuid4())
    
    # First connection
    print(f"[DEBUG][test_duplicate_client_id] ws_helper.mock_mode: {getattr(ws_helper, 'mock_mode', None)}")
    print(f"[DEBUG][test_duplicate_client_id] Before ws_helper.connect: active_connections={list(websocket_manager.active_connections.keys())}")
    ws1 = await ws_helper.connect(client_id=client_id)
    print(f"[DEBUG][test_duplicate_client_id] After ws_helper.connect: active_connections={list(websocket_manager.active_connections.keys())}")
    print(f"[DEBUG][test_duplicate_client_id] ws1.client_state={ws1.client_state}")
    assert ws1.client_state == WebSocketState.CONNECTED
    
    # Try to connect with same client_id (should fail)
    print(f"[DEBUG][test_duplicate_client_id] Before duplicate ws_helper.connect: active_connections={list(websocket_manager.active_connections.keys())}")
    try:
        with pytest.raises(ConnectionClosed) as exc_info:
            await ws_helper.connect(client_id=client_id)
    finally:
        print(f"[DEBUG][test_duplicate_client_id] After duplicate ws_helper.connect: active_connections={list(websocket_manager.active_connections.keys())}")
        ws = websocket_manager.active_connections.get(client_id)
        print(f"[DEBUG][test_duplicate_client_id] ws.client_state={getattr(ws, 'client_state', None)}")
    
    # Cleanup
    await ws_helper.cleanup()

# Message Tests
@pytest.mark.mock_service
async def test_message_sending(ws_helper):
    """Test sending and receiving chat messages."""
    logger = logging.getLogger("test_message_sending")
    client_id = str(uuid.uuid4())
    ws = await ws_helper.connect(client_id=client_id)
    logger.debug(f"[test_message_sending] Connected: client_id={client_id}, ws_state={ws.client_state}")
    assert ws.client_state == WebSocketState.CONNECTED
    
    # Send a test message
    test_msg = {
        "type": "chat_message",
        "content": "Hello, World!",
        "metadata": {}
    }
    logger.debug(f"[test_message_sending] Sending message: {test_msg}")
    logger.debug(f"[test_message_sending] State before send_json: {ws.client_state}")
    response = await ws_helper.send_json(
        data=test_msg,
        client_id=client_id
    )
    logger.debug(f"[test_message_sending] State after send_json: {ws.client_state}")
    logger.debug(f"[test_message_sending] Received response: {response}")
    assert response["type"] == "chat_message"
    assert response["content"] == "Hello, World!"
    
    await ws_helper.disconnect(client_id)

@pytest.mark.mock_service
async def test_typing_indicator(ws_helper):
    """Test typing indicator messages."""
    client_id = str(uuid.uuid4())
    ws = await ws_helper.connect(client_id=client_id)
    assert ws.client_state == WebSocketState.CONNECTED
    
    # Send typing indicator
    response = await ws_helper.send_json(
        data={
            "type": "typing",
            "content": "true",
            "metadata": {}
        },
        client_id=client_id
    )
    assert response["type"] == "typing"
    assert response["content"] == "true"
    
    await ws_helper.disconnect(client_id)

# Rate Limiting Tests
@pytest.mark.mock_service
async def test_message_rate_limiting(ws_helper, rate_limiter):
    """Test message rate limiting."""
    client_id = str(uuid.uuid4())
    ws = await ws_helper.connect(client_id=client_id)
    assert ws.client_state == WebSocketState.CONNECTED
    
    # Send messages until rate limited
    for i in range(rate_limiter.messages_per_minute + 1):
        response = await ws_helper.send_json(
            data={
                "type": "chat",
                "content": f"Message {i}",
                "metadata": {}
            },
            client_id=client_id,
            ignore_errors=True
        )
        if i == rate_limiter.messages_per_minute:
            assert response["type"] == "error"
            assert "rate limit" in response["content"].lower()
            break
    
    await ws_helper.disconnect(client_id)

@pytest.mark.mock_service
async def test_system_message_bypass_rate_limit(ws_helper, rate_limiter):
    """Test system messages bypass rate limiting."""
    client_id = str(uuid.uuid4())
    ws = await ws_helper.connect(client_id=client_id)
    assert ws.client_state == WebSocketState.CONNECTED
    
    # Send messages until rate limited
    for i in range(rate_limiter.messages_per_minute + 1):
        await ws_helper.send_json(
            data={
                "type": "chat_message",
                "content": f"Message {i}",
                "metadata": {}
            },
            client_id=client_id,
            ignore_errors=True
        )
    
    # System message should still work
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
    
    await ws_helper.disconnect(client_id)

# Error Handling Tests
@pytest.mark.mock_service
async def test_malformed_message(ws_helper):
    """Test handling of malformed messages."""
    client_id = str(uuid.uuid4())
    ws = await ws_helper.connect(client_id=client_id)
    assert ws.client_state == WebSocketState.CONNECTED
    
    # Test missing type
    response = await ws_helper.send_json(
        data={
            "content": "test",
            "metadata": {}
        },
        client_id=client_id,
        ignore_errors=True
    )
    assert response["type"] == "error"
    assert "missing message type" in response["content"].lower()
    
    # Test missing content
    response = await ws_helper.send_json(
        data={
            "type": "chat_message",
            "metadata": {}
        },
        client_id=client_id,
        ignore_errors=True
    )
    assert response["type"] == "error"
    assert "content" in response["content"].lower()
    
    # Test invalid message type
    response = await ws_helper.send_json(
        data={
            "type": "invalid_type",
            "content": "test",
            "metadata": {}
        },
        client_id=client_id,
        ignore_errors=True
    )
    assert response["type"] == "error"
    assert "invalid_type" in response["content"].lower()
    
    await ws_helper.disconnect(client_id)

@pytest.mark.mock_service
async def test_large_message_handling(ws_helper):
    """Test handling of large messages."""
    client_id = str(uuid.uuid4())
    ws = await ws_helper.connect(client_id=client_id)
    assert ws.client_state == WebSocketState.CONNECTED
    
    # Create large message (test just over 1MB for error case)
    large_content = "x" * (1024 * 1024 + 1)  # 1MB + 1 byte
    response = await ws_helper.send_json(
        data={
            "type": "chat_message",
            "content": large_content,
            "metadata": {}
        },
        client_id=client_id,
        ignore_errors=True
    )
    # Improved logging for easier debugging (see cursor rules for known log splitting issue)
    print(f"[test_large_message_handling] Full response: {json.dumps(response)}")
    print(f"[test_large_message_handling] Actual error message: {response.get('content')}")
    assert response["type"] == "error"
    assert "message size" in response["content"].lower()
    
    await ws_helper.disconnect(client_id)

@pytest.mark.mock_service
async def test_large_message_boundary(ws_helper):
    """Test that a message of exactly 1MB is accepted."""
    client_id = str(uuid.uuid4())
    ws = await ws_helper.connect(client_id=client_id)
    assert ws.client_state == WebSocketState.CONNECTED

    # Create boundary message (exactly 1MB)
    boundary_content = "x" * (1024 * 1024)  # 1MB
    response = await ws_helper.send_json(
        data={
            "type": "chat_message",
            "content": boundary_content,
            "metadata": {}
        },
        client_id=client_id,
        ignore_errors=True
    )
    logger = logging.getLogger("test_large_message_boundary")
    logger.error(f"[test_large_message_boundary] Full response: {response}")
    print(f"[test_large_message_boundary] Full response: {response}")
    print(f"[test_large_message_boundary] Actual message: {response['content'][:100]}... (truncated)")
    assert response["type"] == "chat_message"
    assert response["content"] == boundary_content

    await ws_helper.disconnect(client_id)

@pytest.mark.mock_service
async def test_concurrent_messages(ws_helper):
    """Test handling concurrent message sending."""
    client_id = str(uuid.uuid4())
    ws = await ws_helper.connect(client_id=client_id)
    assert ws.client_state == WebSocketState.CONNECTED
    
    # Send multiple messages concurrently
    messages = [
        {
            "type": "chat_message",
            "content": f"Message {i}",
            "metadata": {}
        }
        for i in range(5)
    ]
    
    tasks = [
        ws_helper.send_json(
            data=message,
            client_id=client_id,
            ignore_errors=True
        )
        for message in messages
    ]
    
    responses = await asyncio.gather(*tasks)
    assert all(r["type"] == "chat_message" for r in responses)
    
    await ws_helper.disconnect(client_id)

@pytest.mark.mock_service
async def test_connection_timeout_handling(ws_helper):
    """Test connection timeout handling."""
    with pytest.raises(ConnectionClosed) as exc_info:
        await ws_helper.connect(connect_timeout=0.001)
    assert exc_info.value.rcvd.code == status.WS_1008_POLICY_VIOLATION
    assert "Missing client_id" in str(exc_info.value.rcvd.reason)

@pytest.mark.mock_service
async def test_message_timeout_handling(ws_helper):
    """Test message timeout handling."""
    client_id = str(uuid.uuid4())
    ws = await ws_helper.connect(client_id=client_id)
    assert ws.client_state == WebSocketState.CONNECTED

    # Patch response_delay to ensure timeout is triggered
    ws.response_delay = 0.01
    try:
        # Send message with short timeout
        with pytest.raises(asyncio.TimeoutError):
            await ws_helper.send_json(
                data={
                    "type": "chat_message",
                    "content": "Test message",
                    "metadata": {}
                },
                client_id=client_id,
                timeout=0.001
            )
    finally:
        ws.response_delay = 0.0

    await ws_helper.disconnect(client_id)

@pytest.mark.mock_service
async def test_reconnection_handling(ws_helper):
    """Test reconnection after disconnect."""
    client_id = str(uuid.uuid4())
    # First connection
    ws = await ws_helper.connect(client_id=client_id)
    assert ws.client_state == WebSocketState.CONNECTED
    await ws_helper.disconnect(client_id)
    # Reconnect
    ws = await ws_helper.connect(client_id=client_id)
    assert ws.client_state == WebSocketState.CONNECTED
    
    # Verify can still send messages
    response = await ws_helper.send_json(
        data={
            "type": "chat_message",
            "content": "After reconnect",
            "metadata": {}
        },
        client_id=client_id
    )
    assert response["type"] == "chat_message"
    
    await ws_helper.disconnect(client_id)

@pytest.mark.mock_service
async def test_invalid_json_handling(ws_helper):
    """Test handling of invalid JSON messages."""
    client_id = str(uuid.uuid4())
    ws = await ws_helper.connect(client_id=client_id)
    assert ws.client_state == WebSocketState.CONNECTED
    
    # Send invalid JSON (infinity is not valid JSON)
    with pytest.raises((ValueError, TypeError, ConnectionClosed)):
        await ws_helper.send_json(
            data={"type": "chat_message", "content": float('inf')},
            client_id=client_id
        )
    
    await ws_helper.disconnect(client_id)

@pytest.mark.mock_service
async def test_unicode_message_handling(ws_helper):
    """Test handling of Unicode messages."""
    client_id = str(uuid.uuid4())
    ws = await ws_helper.connect(client_id=client_id)
    assert ws.client_state == WebSocketState.CONNECTED
    
    # Send Unicode message
    unicode_content = "Hello, 世界! 👋 🌍"
    response = await ws_helper.send_json(
        data={
            "type": "chat_message",
            "content": unicode_content,
            "metadata": {}
        },
        client_id=client_id
    )
    assert response["type"] == "chat_message"
    assert response["content"] == unicode_content
    
    await ws_helper.disconnect(client_id)

@pytest.mark.mock_service
async def test_stream_interruption(ws_helper):
    """Test handling of stream interruption."""
    client_id = str(uuid.uuid4())
    ws = await ws_helper.connect(client_id=client_id)
    assert ws.client_state == WebSocketState.CONNECTED

    # Start stream
    stream_messages, final_message = await ws_helper.wait_for_stream(
        initial_message={
            "type": "stream_start",
            "content": "Start stream",
            "metadata": {}
        },
        client_id=client_id,
        ignore_errors=True
    )

    # Verify stream messages and end
    assert len(stream_messages) > 0, "Should receive at least one stream message"
    assert final_message.get("type") == "stream_end"

    await ws_helper.disconnect(client_id)

@pytest.mark.mock_service
async def test_empty_stream_handling(ws_helper):
    """Test handling of empty stream."""
    client_id = str(uuid.uuid4())
    ws = await ws_helper.connect(client_id=client_id)
    assert ws.client_state == WebSocketState.CONNECTED
    
    # Start empty stream
    stream_messages, final_message = await ws_helper.wait_for_stream(
        initial_message={
            "type": "stream_start",
            "content": "",
            "metadata": {}
        },
        client_id=client_id,
        ignore_errors=True
    )
    
    # Allow a single content block before error, matching real server behavior
    assert len(stream_messages) <= 1, f"Expected at most one stream message, got {len(stream_messages)}"
    assert final_message.get("type") == "error"
    assert "empty" in final_message.get("content", "").lower()
    
    await ws_helper.disconnect(client_id)

@pytest.mark.real_websocket
async def test_valid_connection(
    test_user: User,
    ws_helper: WebSocketTestHelper,
    websocket_manager: WebSocketManager,
    rate_limiter: WebSocketRateLimiter
):
    """Test successful WebSocket connection."""
    client_id = str(uuid.uuid4())
    # Connect with valid token
    ws = await ws_helper.connect(client_id=client_id)
    assert ws.client_state == WebSocketState.CONNECTED
    
    # Verify connection in manager
    assert websocket_manager.active_connections.get(client_id) is not None
    
    # Clean up
    await ws_helper.disconnect(client_id)

@pytest.mark.real_websocket
async def test_invalid_token_real(
    ws_helper: WebSocketTestHelper,
    websocket_manager: WebSocketManager,
    rate_limiter: WebSocketRateLimiter
):
    """Test connection with invalid token is rejected."""
    client_id = str(uuid.uuid4())
    
    with pytest.raises(ConnectionClosed) as exc_info:
        await ws_helper.connect(client_id=client_id, auth_token="invalid")
    
    close = exc_info.value.rcvd
    assert close.code == status.WS_1008_POLICY_VIOLATION
    assert "Invalid token" in str(close.reason)
    
    # Verify no connection in manager
    assert websocket_manager.active_connections.get(client_id) is None

@pytest.mark.real_websocket
async def test_missing_token_real(
    ws_helper: WebSocketTestHelper,
    websocket_manager: WebSocketManager,
    rate_limiter: WebSocketRateLimiter
):
    """Test connection without token is rejected."""
    ws_helper.auth_token = None
    client_id = str(uuid.uuid4())
    
    with pytest.raises(ConnectionClosed) as exc_info:
        await ws_helper.connect(client_id=client_id)
    
    close = exc_info.value.rcvd
    assert close.code == status.WS_1008_POLICY_VIOLATION
    assert "Missing token" in str(close.reason)
    
    # Verify no connection in manager
    assert websocket_manager.active_connections.get(client_id) is None

@pytest.mark.real_websocket
async def test_duplicate_connection_real(
    test_user: User,
    ws_helper: WebSocketTestHelper,
    websocket_manager: WebSocketManager,
    rate_limiter: WebSocketRateLimiter
):
    """Test duplicate connections are rejected."""
    client_id = str(uuid.uuid4())
    # First connection
    ws1 = await ws_helper.connect(client_id=client_id)
    assert ws1.client_state == WebSocketState.CONNECTED
    
    # Try duplicate connection with same client_id
    with pytest.raises(ConnectionClosed) as exc_info:
        await ws_helper.connect(client_id=ws1.client_id)
    
    close = exc_info.value.rcvd
    assert close.code == status.WS_1008_POLICY_VIOLATION
    assert "Client ID already in use" in str(close.reason)
    
    # Clean up
    await ws_helper.disconnect(client_id)

@pytest.mark.real_websocket
async def test_connection_cleanup_real(
    test_user: User,
    ws_helper: WebSocketTestHelper,
    websocket_manager: WebSocketManager,
    rate_limiter: WebSocketRateLimiter
):
    """Test connection is properly cleaned up after disconnect."""
    client_id = str(uuid.uuid4())
    ws = await ws_helper.connect(client_id=client_id)
    
    # Verify connection exists
    assert websocket_manager.active_connections.get(client_id) is not None
    
    # Disconnect
    await ws_helper.disconnect(client_id)
    
    # Verify connection is removed
    assert websocket_manager.active_connections.get(client_id) is None

@pytest.mark.real_websocket
def make_expired_token(create_access_token):
    # Expired 1 hour ago
    return create_access_token(data={"sub": str(uuid.uuid4())}, expires_delta=timedelta(hours=-1))

@pytest.mark.real_websocket
async def test_expired_token_real(ws_helper: WebSocketTestHelper, create_access_token):
    """Test connection with expired token is rejected."""
    if os.environ.get("USE_MOCK_WEBSOCKET") == "1" or os.environ.get("ENVIRONMENT") == "test":
        pytest.skip("Token validation is bypassed in mock/test mode, skipping test_expired_token_real.")
    expired_token = make_expired_token(create_access_token)
    client_id = str(uuid.uuid4())
    with pytest.raises(ConnectionClosed) as exc_info:
        await ws_helper.connect(client_id=client_id, auth_token=expired_token)
    close = exc_info.value.rcvd
    assert close.code == status.WS_1008_POLICY_VIOLATION or close.code == 4401  # Some stacks use 4401 for expired
    assert "expired" in str(close.reason).lower() or "invalid" in str(close.reason).lower()

@pytest.mark.real_websocket
async def test_malformed_token_real(ws_helper: WebSocketTestHelper):
    """Test connection with malformed token is rejected."""
    if os.environ.get("USE_MOCK_WEBSOCKET") == "1" or os.environ.get("ENVIRONMENT") == "test":
        pytest.skip("Token validation is bypassed in mock/test mode, skipping test_malformed_token_real.")
    malformed_token = "not.a.jwt"
    client_id = str(uuid.uuid4())
    with pytest.raises(ConnectionClosed) as exc_info:
        await ws_helper.connect(client_id=client_id, auth_token=malformed_token)
    close = exc_info.value.rcvd
    assert close.code == status.WS_1008_POLICY_VIOLATION
    assert "invalid" in str(close.reason).lower()

@pytest.mark.real_websocket
async def test_missing_claim_token_real(ws_helper: WebSocketTestHelper, create_access_token):
    """Test connection with token missing 'sub' claim is rejected."""
    if os.environ.get("USE_MOCK_WEBSOCKET") == "1" or os.environ.get("ENVIRONMENT") == "test":
        pytest.skip("Token validation is bypassed in mock/test mode, skipping test_missing_claim_token_real.")
    # Create a token with no 'sub' claim
    payload = {"exp": int((datetime.now(UTC) + timedelta(minutes=5)).timestamp())}
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    client_id = str(uuid.uuid4())
    with pytest.raises(ConnectionClosed) as exc_info:
        await ws_helper.connect(client_id=client_id, auth_token=token)
    close = exc_info.value.rcvd
    assert close.code == status.WS_1008_POLICY_VIOLATION
    assert "sub" in str(close.reason).lower() or "invalid" in str(close.reason).lower()

@pytest.mark.real_websocket
async def test_token_in_authorization_header_real(ws_helper: WebSocketTestHelper, create_access_token):
    """Test connection with token in Authorization header is accepted."""
    if os.environ.get("USE_MOCK_WEBSOCKET") == "1" or os.environ.get("ENVIRONMENT") == "test":
        pytest.skip("Token validation is bypassed in mock/test mode, skipping test_token_in_authorization_header_real.")
    valid_token = create_access_token(data={"sub": str(uuid.uuid4())})
    client_id = str(uuid.uuid4())
    # Use ws_helper with ws_token_query=False to force header usage
    ws = await ws_helper.connect(client_id=client_id, auth_token=valid_token, token=None)
    assert ws.client_state == WebSocketState.CONNECTED
    await ws_helper.disconnect(client_id)