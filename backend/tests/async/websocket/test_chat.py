"""
WebSocket chat message streaming tests using async websockets library.
These tests verify the streaming behavior of chat messages in an async context.
"""

import pytest
import json
import logging
import asyncio
from datetime import timedelta, datetime, UTC
import os
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from typing import AsyncGenerator

from app.core.auth import create_access_token
from tests.conftest import test_settings
from app.core.config import settings
from app.models import User
from app.db.session import get_async_session
from app.core.security import pwd_context
from app.core.websocket import WebSocketManager
from app.core.redis import get_redis
from app.core.websocket_rate_limiter import WebSocketRateLimiter
from tests.utils.websocket_test_helper import WebSocketTestHelper

# Test configuration
WS_HOST = "backend-test"  # Use Docker service name
WS_PORT = 8000
WS_BASE_URL = f"ws://{WS_HOST}:{WS_PORT}/ws"  # WebSocket endpoint at /ws
HTTP_BASE_URL = f"http://{WS_HOST}:{WS_PORT}"

# Test timeouts
CONNECT_TIMEOUT = 5  # seconds
MESSAGE_TIMEOUT = 5  # seconds

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

@pytest.fixture
async def redis_client() -> AsyncGenerator:
    """Get Redis client for testing."""
    redis = await get_redis()
    try:
        yield redis
    finally:
        # Clean up any test data
        await redis.flushdb()
        await redis.aclose()

@pytest.fixture
async def websocket_manager(redis_client) -> AsyncGenerator:
    """Create a WebSocket manager instance for testing."""
    manager = WebSocketManager(redis_client)
    try:
        yield manager
    finally:
        await manager.clear_all_connections()

@pytest.fixture
async def rate_limiter(redis_client) -> AsyncGenerator:
    """Create a rate limiter instance for testing."""
    limiter = WebSocketRateLimiter(redis_client)
    try:
        yield limiter
    finally:
        await limiter.clear_all()

@pytest.fixture
async def test_user(request, test_settings) -> AsyncGenerator[User, None]:
    """Get or create a test user."""
    if request.node.get_closest_marker("real_service"):
        # For real service tests, use the predefined user ID
        user_id = os.getenv("MCP_USER_ID")
        if not user_id:
            pytest.skip("MCP_USER_ID environment variable not set")
        yield User(
            id=user_id,
            email=os.getenv("MCP_USER_EMAIL", "real_service@example.com"),
            username=os.getenv("MCP_USERNAME", "real_service_user"),
            is_active=True
        )
        return
    
    # For non-real service tests, create a test user
    user_id = str(uuid.uuid4())
    user = User(
        id=user_id,
        email=f"test_{user_id}@example.com",
        username=f"test_{user_id}",
        hashed_password=pwd_context.hash("testpassword123"),
        is_active=True
    )
    
    async for session in get_async_session():
        session.add(user)
        await session.commit()
        await session.refresh(user)
        yield user
        # Cleanup
        await session.delete(user)
        await session.commit()

@pytest.fixture
async def test_token(request, test_user, test_settings) -> str:
    """Create a test JWT token or use real API key for real service tests."""
    if request.node.get_closest_marker("real_service"):
        # Use the real API key for real service tests
        api_key = os.getenv("MCP_API_KEY")
        if not api_key:
            pytest.skip("MCP_API_KEY environment variable not set")
        return api_key
    
    # For non-real service tests, create a test token
    token = await create_access_token(
        {"sub": str(test_user.id)},
        settings=test_settings,
        expires_delta=timedelta(minutes=30)
    )
    return token

@pytest.mark.asyncio
@pytest.mark.real_websocket
@pytest.mark.db_test
async def test_websocket_chat_basic(
    test_user: User,
    test_token: str,
    websocket_helper: WebSocketTestHelper,
    websocket_manager: WebSocketManager,
    rate_limiter: WebSocketRateLimiter
):
    """Test basic WebSocket chat functionality."""
    try:
        # Connect to WebSocket
        await websocket_helper.connect(test_token)
        
        # Send a test message
        test_message = "Hello, world!"
        await websocket_helper.send_message(
            message_type="chat_message",
            content=test_message
        )
        
        # Wait for response
        response = await websocket_helper.wait_for_message("chat_message")
        
        # Verify response
        assert response["type"] == "chat_message"
        assert response["content"] == test_message
        assert "metadata" in response
        assert "timestamp" in response["metadata"]
        
    finally:
        await websocket_helper.disconnect()
        # Ensure cleanup
        await websocket_manager.clear_all_connections()
        await rate_limiter.clear_all()

@pytest.mark.asyncio
@pytest.mark.real_websocket
@pytest.mark.db_test
async def test_websocket_rate_limiting(
    test_user: User,
    test_token: str,
    websocket_helper: WebSocketTestHelper,
    websocket_manager: WebSocketManager,
    rate_limiter: WebSocketRateLimiter
):
    """Test WebSocket rate limiting functionality."""
    try:
        # Connect to WebSocket
        await websocket_helper.connect(test_token)
        
        # Send messages rapidly to trigger rate limit
        messages_sent = 0
        messages_rejected = 0
        
        # Send messages in quick succession
        for i in range(20):  # Send enough messages to hit rate limit
            try:
                response = await websocket_helper.send_message(
                    message_type="chat_message",
                    content=f"Test message {i}",
                    metadata={
                        "timestamp": datetime.now(UTC).isoformat(),
                        "sequence": i
                    },
                    expect_response=True
                )
                
                if response["type"] == "chat_message":
                    messages_sent += 1
                elif response["type"] == "error" and "rate limit" in response.get("message", "").lower():
                    messages_rejected += 1
                    logger.debug(f"Rate limit hit after {messages_sent} messages")
                    break
                    
            except RuntimeError as e:
                if "rate limit" in str(e).lower():
                    messages_rejected += 1
                    logger.debug(f"Rate limit hit after {messages_sent} messages")
                    break
                raise
                
        # Verify rate limiting occurred
        assert messages_rejected > 0, "Rate limiting did not trigger"
        assert messages_sent > 0, "No messages were sent successfully"
        logger.info(f"Rate limit test complete: {messages_sent} sent, {messages_rejected} rejected")
        
    finally:
        await websocket_helper.disconnect()
        await rate_limiter.clear_all()  # Clean up rate limit data

@pytest.mark.asyncio
@pytest.mark.real_websocket
@pytest.mark.db_test
async def test_websocket_authentication(
    test_user: User,
    websocket_helper: WebSocketTestHelper,
    websocket_manager: WebSocketManager,
    rate_limiter: WebSocketRateLimiter
):
    """Test WebSocket authentication handling."""
    # Try to connect with invalid token
    invalid_token = "invalid.token.here"
    
    with pytest.raises(ConnectionClosed) as exc_info:
        await websocket_helper.connect(auth_token=invalid_token)
    assert exc_info.value.rcvd.code == status.WS_1008_POLICY_VIOLATION
    assert "Invalid token" in str(exc_info.value.rcvd.reason)

@pytest.mark.asyncio
@pytest.mark.real_websocket
@pytest.mark.db_test
async def test_websocket_disconnect_cleanup(
    test_user: User,
    test_token: str,
    websocket_helper: WebSocketTestHelper,
    websocket_manager: WebSocketManager,
    rate_limiter: WebSocketRateLimiter
):
    """Test proper cleanup after WebSocket disconnection."""
    # Connect to WebSocket
    await websocket_helper.connect(test_token)
    client_id = websocket_helper.client_id
    
    # Verify connection is active
    assert len(websocket_manager.active_connections) == 1
    
    # Disconnect
    await websocket_helper.disconnect()
    
    # Verify cleanup
    assert len(websocket_manager.active_connections) == 0
    # Rate limiter should have cleared connection count
    assert await rate_limiter.check_connection_limit(
        client_id=client_id,
        user_id=str(test_user.id),
        ip_address="127.0.0.1"
    ) == (True, None)

@pytest.mark.asyncio
@pytest.mark.real_websocket
@pytest.mark.db_test
async def test_chat_message_streaming_old(test_user, test_settings, websocket_helper: WebSocketTestHelper, websocket_manager, rate_limiter):
    """Test streaming response from a chat message using async websockets."""
    client_id = str(uuid.uuid4())
    ws = None
    try:
        # Connect using websocket_helper
        ws = await websocket_helper.connect(client_id=client_id)
        assert ws is not None, "WebSocket connection failed"
        
        # Send a test message
        test_message = {
            "type": "chat_message",
            "content": "What is the capital of France?",  # Simple factual question
            "metadata": {}
        }
        await websocket_helper.send_message(client_id, test_message)
        
        # Track what we've received
        got_stream_start = False
        got_stream_content = False
        got_stream_end = False
        received_content = []
        
        # Keep receiving messages until we get stream_end or timeout
        try:
            while True:
                msg = await websocket_helper.receive_message(client_id, timeout=10)
                if msg["type"] == "stream_start":
                    got_stream_start = True
                    continue
                if msg["type"] == "stream":
                    got_stream_content = True
                    received_content.append(msg["content"])
                    continue
                if msg["type"] == "stream_end":
                    got_stream_end = True
                    break
        except asyncio.TimeoutError:
            raise
        
        # Verify we got all message types
        assert got_stream_start, "Did not receive stream_start"
        assert got_stream_content, "Did not receive any stream content"
        assert got_stream_end, "Did not receive stream_end"
        
        # Verify content
        full_response = "".join(received_content)
        assert "Paris" in full_response, "Response should mention Paris"
        
    finally:
        if ws:
            await websocket_helper.disconnect(client_id)
        await websocket_manager.clear_all_connections()
        await rate_limiter.clear_all()

@pytest.mark.asyncio
@pytest.mark.real_websocket
@pytest.mark.db_test
async def test_websocket_streaming_chat(
    test_user: User,
    test_token: str,
    websocket_helper: WebSocketTestHelper,
    websocket_manager: WebSocketManager,
    rate_limiter: WebSocketRateLimiter
):
    """Test WebSocket streaming chat functionality."""
    try:
        # Connect to WebSocket
        await websocket_helper.connect(test_token)
        
        # Send a chat message that should trigger streaming response
        await websocket_helper.send_message(
            message_type="chat_message",
            content="What is the capital of France?",
            expect_response=False  # Don't wait for immediate response
        )
        
        # Wait for complete stream
        success, content_parts, final_message = await websocket_helper.wait_for_stream()
        
        # Verify streaming response
        assert success, "Stream did not complete successfully"
        assert content_parts, "No content received in stream"
        assert any("Paris" in part for part in content_parts), "Expected 'Paris' in response"
        assert final_message and final_message["type"] == "stream_end"
        
    finally:
        await websocket_helper.disconnect()
        await rate_limiter.clear_all()  # Clean up rate limit data 

@pytest.mark.asyncio
@pytest.mark.real_websocket
@pytest.mark.db_test
async def test_message_send_receive(
    test_user: User,
    websocket_helper: WebSocketTestHelper,
    websocket_manager: WebSocketManager,
    rate_limiter: WebSocketRateLimiter
):
    """Test sending and receiving chat messages."""
    # Connect two clients
    ws1 = await websocket_helper.connect()
    ws2 = await websocket_helper.connect()
    
    # Send message from client 1
    message = {"type": "chat", "content": "Hello from client 1"}
    await websocket_helper.send_message(message, ws1.client_id)
    
    # Receive message on client 2
    received = await websocket_helper.receive_message(ws2.client_id)
    assert received["type"] == "chat"
    assert received["content"] == "Hello from client 1"
    assert received["sender_id"] == test_user.id
    
    # Clean up
    await websocket_helper.disconnect(ws1.client_id)
    await websocket_helper.disconnect(ws2.client_id)

@pytest.mark.asyncio
@pytest.mark.real_websocket
@pytest.mark.db_test
async def test_message_broadcast(
    test_user: User,
    websocket_helper: WebSocketTestHelper,
    websocket_manager: WebSocketManager,
    rate_limiter: WebSocketRateLimiter
):
    """Test message broadcasting to all connected clients."""
    # Connect multiple clients
    clients = []
    for i in range(3):
        ws = await websocket_helper.connect()
        clients.append(ws)
    
    # Send broadcast message from first client
    message = {"type": "broadcast", "content": "Hello everyone!"}
    await websocket_helper.send_message(message, clients[0].client_id)
    
    # Verify all other clients receive the message
    for client in clients[1:]:
        received = await websocket_helper.receive_message(client.client_id)
        assert received["type"] == "broadcast"
        assert received["content"] == "Hello everyone!"
        assert received["sender_id"] == test_user.id
    
    # Clean up
    for client in clients:
        await websocket_helper.disconnect(client.client_id)

@pytest.mark.asyncio
@pytest.mark.real_websocket
@pytest.mark.db_test
async def test_message_validation(
    test_user: User,
    websocket_helper: WebSocketTestHelper,
    websocket_manager: WebSocketManager,
    rate_limiter: WebSocketRateLimiter
):
    """Test message validation and error handling."""
    ws = await websocket_helper.connect()
    
    # Test invalid message type
    invalid_message = {"type": "invalid", "content": "test"}
    with pytest.raises(ConnectionClosed) as exc_info:
        await websocket_helper.send_message(invalid_message)
    
    close = exc_info.value.rcvd
    assert close.code == status.WS_1003_UNSUPPORTED_DATA
    assert "Invalid message type" in str(close.reason)
    
    # Test missing required fields
    invalid_message = {"type": "chat"}  # Missing content
    with pytest.raises(ConnectionClosed) as exc_info:
        await websocket_helper.send_message(invalid_message)
    
    close = exc_info.value.rcvd
    assert close.code == status.WS_1003_UNSUPPORTED_DATA
    assert "Missing required field" in str(close.reason)
    
    await websocket_helper.disconnect()

@pytest.mark.asyncio
@pytest.mark.real_websocket
@pytest.mark.db_test
async def test_message_order(
    test_user: User,
    websocket_helper: WebSocketTestHelper,
    websocket_manager: WebSocketManager,
    rate_limiter: WebSocketRateLimiter
):
    """Test message ordering is preserved."""
    # Connect two clients
    ws1 = await websocket_helper.connect()
    ws2 = await websocket_helper.connect()
    
    # Send multiple messages from client 1
    messages = []
    for i in range(5):
        message = {"type": "chat", "content": f"Message {i}"}
        await websocket_helper.send_message(message, ws1.client_id)
        messages.append(message)
    
    # Verify messages are received in order by client 2
    for i, sent_message in enumerate(messages):
        received = await websocket_helper.receive_message(ws2.client_id)
        assert received["type"] == "chat"
        assert received["content"] == f"Message {i}"
        assert received["sender_id"] == test_user.id
    
    # Clean up
    await websocket_helper.disconnect(ws1.client_id)
    await websocket_helper.disconnect(ws2.client_id)

@pytest.mark.asyncio
@pytest.mark.real_websocket
@pytest.mark.db_test
async def test_client_disconnect_handling(
    test_user: User,
    websocket_helper: WebSocketTestHelper,
    websocket_manager: WebSocketManager,
    rate_limiter: WebSocketRateLimiter
):
    """Test proper handling of client disconnections."""
    # Connect two clients
    ws1 = await websocket_helper.connect()
    ws2 = await websocket_helper.connect()
    
    # Disconnect client 1
    await websocket_helper.disconnect(ws1.client_id)
    
    # Verify client 1 is removed from manager
    assert websocket_manager.get_connection(ws1.client_id) is None
    
    # Verify client 2 can still send/receive messages
    message = {"type": "chat", "content": "Still connected"}
    await websocket_helper.send_message(message, ws2.client_id)
    
    received = await websocket_helper.receive_message(ws2.client_id)
    assert received["type"] == "chat"
    assert received["content"] == "Still connected"
    
    # Clean up
    await websocket_helper.disconnect(ws2.client_id) 