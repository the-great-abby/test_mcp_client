"""WebSocket rate limiting integration tests."""
import asyncio
import pytest
from fastapi import status
from websockets.exceptions import ConnectionClosed
from websockets.frames import Close

from app.core.websocket import WebSocketManager
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

@pytest.mark.asyncio
@pytest.mark.real_service
async def test_connection_rate_limit(
    test_user: User,
    websocket_helper: WebSocketTestHelper,
    websocket_manager: WebSocketManager
):
    """Test connection rate limiting."""
    rate_limiter = WebSocketRateLimiter(
        redis=None,  # No Redis needed for basic rate limiting
        max_connections=MAX_CONNECTIONS,
        messages_per_minute=MESSAGES_PER_MINUTE,
        messages_per_hour=MESSAGES_PER_HOUR,
        messages_per_day=MESSAGES_PER_DAY,
        max_messages_per_second=MAX_MESSAGES_PER_SECOND,
        rate_limit_window=RATE_LIMIT_WINDOW,
        connect_timeout=CONNECT_TIMEOUT,
        message_timeout=MESSAGE_TIMEOUT
    )
    
    # Create multiple connections up to limit
    connections = []
    for i in range(MAX_CONNECTIONS):
        ws = await websocket_helper.connect()
        assert ws.client_state.state == "CONNECTED"
        connections.append(ws)
    
    # Try to exceed connection limit
    with pytest.raises(ConnectionClosed) as exc_info:
        await websocket_helper.connect()
    
    close = exc_info.value.rcvd
    assert close.code == status.WS_1008_POLICY_VIOLATION
    assert "Connection limit exceeded" in str(close.reason)
    
    # Clean up
    for ws in connections:
        await websocket_helper.disconnect(ws.client_id)

@pytest.mark.asyncio
@pytest.mark.real_service
async def test_message_rate_limit_per_second(
    test_user: User,
    websocket_helper: WebSocketTestHelper,
    websocket_manager: WebSocketManager,
    rate_limiter: WebSocketRateLimiter
):
    """Test message rate limiting per second."""
    ws = await websocket_helper.connect()
    
    # Send messages up to per-second limit
    for i in range(MAX_MESSAGES_PER_SECOND):
        await websocket_helper.send_message({"type": "test", "content": f"message {i}"})
    
    # Try to exceed per-second limit
    with pytest.raises(ConnectionClosed) as exc_info:
        await websocket_helper.send_message({"type": "test", "content": "over limit"})
    
    close = exc_info.value.rcvd
    assert close.code == status.WS_1008_POLICY_VIOLATION
    assert "Message rate limit exceeded" in str(close.reason)
    
    await websocket_helper.disconnect()

@pytest.mark.asyncio
@pytest.mark.real_service
async def test_message_rate_limit_per_minute(
    test_user: User,
    websocket_helper: WebSocketTestHelper,
    websocket_manager: WebSocketManager,
    rate_limiter: WebSocketRateLimiter
):
    """Test message rate limiting per minute."""
    ws = await websocket_helper.connect()
    
    # Send messages up to per-minute limit with delay to avoid per-second limit
    for i in range(MESSAGES_PER_MINUTE):
        await websocket_helper.send_message({"type": "test", "content": f"message {i}"})
        await asyncio.sleep(0.1)  # Add delay to avoid per-second limit
    
    # Try to exceed per-minute limit
    with pytest.raises(ConnectionClosed) as exc_info:
        await websocket_helper.send_message({"type": "test", "content": "over limit"})
    
    close = exc_info.value.rcvd
    assert close.code == status.WS_1008_POLICY_VIOLATION
    assert "Message rate limit exceeded" in str(close.reason)
    
    await websocket_helper.disconnect()

@pytest.mark.asyncio
@pytest.mark.real_service
async def test_rate_limit_reset(
    test_user: User,
    websocket_helper: WebSocketTestHelper,
    websocket_manager: WebSocketManager,
    rate_limiter: WebSocketRateLimiter
):
    """Test rate limit counters reset after window."""
    ws = await websocket_helper.connect()
    
    # Send messages up to half the per-minute limit
    for i in range(MESSAGES_PER_MINUTE // 2):
        await websocket_helper.send_message({"type": "test", "content": f"message {i}"})
        await asyncio.sleep(0.1)
    
    # Wait for rate limit window to expire
    await asyncio.sleep(RATE_LIMIT_WINDOW)
    
    # Should be able to send messages again
    for i in range(MESSAGES_PER_MINUTE // 2):
        await websocket_helper.send_message({"type": "test", "content": f"message {i}"})
        await asyncio.sleep(0.1)
    
    await websocket_helper.disconnect() 