"""WebSocket rate limiting integration tests."""
import asyncio
import pytest
from fastapi import status
from websockets.exceptions import ConnectionClosed
from websockets.frames import Close
import uuid

from app.core.websocket import WebSocketManager, WebSocketState
from app.core.websocket_rate_limiter import WebSocketRateLimiter
from app.models.user import User
from tests.utils.websocket_test_helper import WebSocketTestHelper

# Constants for rate limiting
MAX_CONNECTIONS = 3
MESSAGES_PER_MINUTE = 60
MESSAGES_PER_HOUR = 1000
MESSAGES_PER_DAY = 10000
MAX_MESSAGES_PER_SECOND = 10
RATE_LIMIT_WINDOW = 60
CONNECT_TIMEOUT = 5.0
MESSAGE_TIMEOUT = 5.0

@pytest.mark.real_websocket
async def test_connection_rate_limit(
    test_user: User,
    ws_helper: WebSocketTestHelper,
    websocket_manager: WebSocketManager
):
    """Test connection rate limiting."""
    # Patch the rate limiter for this test
    websocket_manager.rate_limiter.max_connections = 3
    print(f"[DEBUG] max_connections: {websocket_manager.rate_limiter.max_connections}")
    
    # Create multiple connections up to limit
    connections = []
    for i in range(MAX_CONNECTIONS):
        client_id = str(uuid.uuid4())
        ws = await ws_helper.connect(client_id=client_id)
        assert ws.client_state == WebSocketState.CONNECTED
        ws.client_id = client_id  # Store for disconnect
        connections.append(ws)
        # Print current connection count for the user
        count = await websocket_manager.rate_limiter.get_connection_count(test_user.id)
        print(f"[DEBUG] After connection {i+1}: connection count for user {test_user.id} = {count}")
    
    # Print connection count before exceeding limit
    count = await websocket_manager.rate_limiter.get_connection_count(test_user.id)
    print(f"[DEBUG] Before exceeding limit: connection count for user {test_user.id} = {count}")
    
    # Try to exceed connection limit
    with pytest.raises(ConnectionClosed) as exc_info:
        await ws_helper.connect(client_id=str(uuid.uuid4()))
    
    close = exc_info.value.rcvd
    assert close.code == status.WS_1008_POLICY_VIOLATION
    assert "Connection limit exceeded" in str(close.reason)
    
    # Clean up
    for ws in connections:
        await ws_helper.disconnect(ws.client_id)

@pytest.mark.real_websocket
async def test_message_rate_limit_per_second(
    test_user: User,
    ws_helper: WebSocketTestHelper,
    websocket_manager: WebSocketManager,
    rate_limiter: WebSocketRateLimiter
):
    """Test message rate limiting per second."""
    client_id = str(uuid.uuid4())
    ws = await ws_helper.connect(client_id=client_id)
    
    # Send messages up to per-second limit
    for i in range(MAX_MESSAGES_PER_SECOND):
        await ws_helper.send_message(client_id, {"type": "test", "content": f"message {i}"})
    
    # Try to exceed per-second limit
    with pytest.raises(ConnectionClosed) as exc_info:
        await ws_helper.send_message(client_id, {"type": "test", "content": "over limit"})
    
    close = exc_info.value.rcvd
    assert close.code == status.WS_1008_POLICY_VIOLATION
    assert "Message rate limit exceeded" in str(close.reason)
    
    await ws_helper.disconnect(client_id)

@pytest.mark.real_websocket
async def test_message_rate_limit_per_minute(
    test_user: User,
    ws_helper: WebSocketTestHelper,
    websocket_manager: WebSocketManager,
    rate_limiter: WebSocketRateLimiter
):
    """Test message rate limiting per minute."""
    client_id = str(uuid.uuid4())
    ws = await ws_helper.connect(client_id=client_id)
    
    # Send messages up to per-minute limit with delay to avoid per-second limit
    for i in range(MESSAGES_PER_MINUTE):
        await ws_helper.send_message(client_id, {"type": "test", "content": f"message {i}"})
        await asyncio.sleep(0.1)  # Add delay to avoid per-second limit
    
    # Try to exceed per-minute limit
    with pytest.raises(ConnectionClosed) as exc_info:
        await ws_helper.send_message(client_id, {"type": "test", "content": "over limit"})
    
    close = exc_info.value.rcvd
    assert close.code == status.WS_1008_POLICY_VIOLATION
    assert "Message rate limit exceeded" in str(close.reason)
    
    await ws_helper.disconnect(client_id)

@pytest.mark.real_websocket
async def test_rate_limit_reset(
    test_user: User,
    ws_helper: WebSocketTestHelper,
    websocket_manager: WebSocketManager,
    rate_limiter: WebSocketRateLimiter
):
    """Test rate limit counters reset after window."""
    client_id = str(uuid.uuid4())
    ws = await ws_helper.connect(client_id=client_id)
    
    # Send messages up to half the per-minute limit
    for i in range(MESSAGES_PER_MINUTE // 2):
        await ws_helper.send_message(client_id, {"type": "test", "content": f"message {i}"})
        await asyncio.sleep(0.1)
    
    # Wait for rate limit window to expire
    await asyncio.sleep(RATE_LIMIT_WINDOW)
    
    # Should be able to send messages again
    for i in range(MESSAGES_PER_MINUTE // 2):
        await ws_helper.send_message(client_id, {"type": "test", "content": f"message {i}"})
        await asyncio.sleep(0.1)
    
    await ws_helper.disconnect(client_id)

@pytest.mark.real_websocket
async def test_message_rate_limit_by_client_type(
    ws_helper: WebSocketTestHelper,
    websocket_manager: WebSocketManager,
    rate_limiter: WebSocketRateLimiter
):
    # Set up different limits for each type
    rate_limiter.client_type_limits = {
        "authenticated": {"second": 5, "minute": 10, "hour": 100, "day": 1000},
        "anonymous": {"second": 2, "minute": 3, "hour": 10, "day": 20},
    }

    # Authenticated user
    auth_token = "valid-token"
    client_id_auth = str(uuid.uuid4())
    ws_auth = await ws_helper.connect(client_id=client_id_auth, token=auth_token)
    for i in range(5):
        await ws_helper.send_message(client_id_auth, {"type": "chat", "content": f"auth {i}"})
    with pytest.raises(ConnectionClosed):
        await ws_helper.send_message(client_id_auth, {"type": "chat", "content": "over limit"})

    # Anonymous user
    client_id_anon = str(uuid.uuid4())
    ws_anon = await ws_helper.connect(client_id=client_id_anon)
    for i in range(2):
        await ws_helper.send_message(client_id_anon, {"type": "chat", "content": f"anon {i}"})
    with pytest.raises(ConnectionClosed):
        await ws_helper.send_message(client_id_anon, {"type": "chat", "content": "over limit"}) 