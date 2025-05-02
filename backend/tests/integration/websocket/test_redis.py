"""Integration tests for WebSocket and Redis interactions.

These tests verify the integration between WebSocket connections and Redis-based rate limiting.
All tests use real Redis service and should be run in the test Docker network.
"""
import pytest
import asyncio
import uuid
import logging
from datetime import datetime, UTC, timedelta
from websockets.exceptions import ConnectionClosed
from typing import List, Dict, Any
from contextlib import AsyncExitStack
from fastapi import status
from starlette.websockets import WebSocketState
from websockets.frames import Close

from app.core.websocket import WebSocketManager
from app.core.websocket_rate_limiter import WebSocketRateLimiter
from app.models.user import User
from tests.utils.websocket_test_helper import WebSocketTestHelper
from tests.utils.mock_websocket import MockWebSocket
from app.core.auth import create_access_token

logger = logging.getLogger(__name__)

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

@pytest.mark.integration
@pytest.mark.real_service
class TestWebSocketRedisIntegration:
    """Integration tests for WebSocket Redis functionality."""
    
    @pytest.fixture
    def auth_token(self):
        """Create a valid auth token for testing."""
        return create_access_token(data={"sub": TEST_USER_ID})
    
    @pytest.fixture
    async def rate_limiter(self, redis_client) -> WebSocketRateLimiter:
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
    
    @pytest.fixture
    async def ws_helper(
        self,
        websocket_manager,
        rate_limiter,
        auth_token
    ) -> WebSocketTestHelper:
        """Create WebSocket test helper with real Redis."""
        helper = WebSocketTestHelper(
            websocket_manager=websocket_manager,
            rate_limiter=rate_limiter,
            test_user_id=TEST_USER_ID,
            test_ip=TEST_IP,
            auth_token=auth_token
        )
        try:
            yield helper
        finally:
            await helper.cleanup()
            
    async def test_redis_connection_tracking(self, ws_helper: WebSocketTestHelper):
        """Test Redis-based connection tracking."""
        client_id = "test_client"
        
        # Create connection
        ws = await ws_helper.connect(client_id=client_id)
        assert ws.client_state == WebSocketState.CONNECTED
        
        # Verify Redis tracking
        count = await ws_helper.rate_limiter.get_connection_count(TEST_USER_ID)
        assert count == 1, "Redis should track one connection"
        
        # Disconnect
        await ws_helper.disconnect(client_id)
        assert ws_helper.get_connection_state(client_id) == WebSocketState.DISCONNECTED
        
        # Verify Redis cleanup
        count = await ws_helper.rate_limiter.get_connection_count(TEST_USER_ID)
        assert count == 0, "Redis should clear connection count"
        
    async def test_redis_message_tracking(self, ws_helper: WebSocketTestHelper):
        """Test Redis-based message tracking."""
        client_id = "test_client"
        
        # Create connection
        ws = await ws_helper.connect(client_id=client_id)
        assert ws.client_state == WebSocketState.CONNECTED
        
        # Send messages
        for i in range(MESSAGES_PER_MINUTE // 2):
            response = await ws_helper.send_json(
                data={"type": "chat", "content": f"Message {i}"},
                client_id=client_id,
                ignore_errors=True
            )
            assert response["type"] != "error", f"Message {i} should succeed"
            
        # Verify Redis message count
        count = await ws_helper.rate_limiter.get_message_count(TEST_USER_ID)
        assert count == MESSAGES_PER_MINUTE // 2, "Redis should track message count"
        
    async def test_redis_rate_limit_persistence(self, ws_helper: WebSocketTestHelper):
        """Test Redis rate limit persistence."""
        client_id = "test_client"
        
        # Create connection
        ws = await ws_helper.connect(client_id=client_id)
        assert ws.client_state == WebSocketState.CONNECTED
        
        # Send messages up to limit
        for i in range(MESSAGES_PER_MINUTE):
            response = await ws_helper.send_json(
                data={"type": "chat", "content": f"Message {i}"},
                client_id=client_id,
                ignore_errors=True
            )
            assert response["type"] != "error", f"Message {i} should succeed"
            
        # Verify Redis limit is enforced
        response = await ws_helper.send_json(
            data={"type": "chat", "content": "Excess message"},
            client_id=client_id,
            ignore_errors=True
        )
        assert response["type"] == "error"
        assert "rate limit" in response["content"].lower()
        
        # Wait for window reset
        await asyncio.sleep(RATE_LIMIT_WINDOW)
        
        # Verify Redis limit is reset
        response = await ws_helper.send_json(
            data={"type": "chat", "content": "New message"},
            client_id=client_id,
            ignore_errors=True
        )
        assert response["type"] != "error", "Message should succeed after window reset"
        
    async def test_redis_connection_cleanup(self, ws_helper: WebSocketTestHelper):
        """Test Redis connection cleanup on errors."""
        client_ids = []
        
        try:
            # Create multiple connections
            for i in range(MAX_CONNECTIONS):
                client_id = f"test_client_{i}"
                ws = await ws_helper.connect(client_id=client_id)
                assert ws.client_state == WebSocketState.CONNECTED
                client_ids.append(client_id)
                
            # Verify Redis tracking
            count = await ws_helper.rate_limiter.get_connection_count(TEST_USER_ID)
            assert count == MAX_CONNECTIONS, "Redis should track all connections"
            
            # Simulate connection error
            for client_id in client_ids[:2]:
                await ws_helper.disconnect(client_id)
                assert ws_helper.get_connection_state(client_id) == WebSocketState.DISCONNECTED
                
            # Verify Redis cleanup
            count = await ws_helper.rate_limiter.get_connection_count(TEST_USER_ID)
            assert count == MAX_CONNECTIONS - 2, "Redis should remove closed connections"
            
            # Verify can create new connections
            for i in range(2):
                client_id = f"new_client_{i}"
                ws = await ws_helper.connect(client_id=client_id)
                assert ws.client_state == WebSocketState.CONNECTED
                client_ids.append(client_id)
                
        finally:
            # Cleanup all connections
            for client_id in client_ids:
                try:
                    await ws_helper.disconnect(client_id)
                except Exception as e:
                    logger.error(f"Error cleaning up connection {client_id}: {e}")
                    
    async def test_redis_error_recovery(self, ws_helper: WebSocketTestHelper, redis_client):
        """Test recovery from Redis errors."""
        client_id = "test_client"
        
        # Create connection
        ws = await ws_helper.connect(client_id=client_id)
        assert ws.client_state == WebSocketState.CONNECTED
        
        try:
            # Simulate Redis error by closing connection
            await redis_client.aclose()
            
            # Attempt operations during error
            response = await ws_helper.send_json(
                data={"type": "chat", "content": "Test message"},
                client_id=client_id,
                ignore_errors=True
            )
            assert response["type"] == "error"
            assert "redis" in response["content"].lower()
            
        finally:
            # Restore Redis connection
            await redis_client.ping()
            
        # Verify system recovers
        response = await ws_helper.send_json(
            data={"type": "chat", "content": "Recovery message"},
            client_id=client_id,
            ignore_errors=True
        )
        assert response["type"] != "error", "System should recover after Redis restoration"
        
    async def test_redis_concurrent_access(self, ws_helper: WebSocketTestHelper):
        """Test concurrent Redis access patterns."""
        client_ids = [f"client_{i}" for i in range(MAX_CONNECTIONS)]
        
        async def client_workflow(client_id: str) -> None:
            """Simulate client connection and message workflow."""
            try:
                # Connect
                ws = await ws_helper.connect(client_id=client_id)
                assert ws.client_state == WebSocketState.CONNECTED
                
                # Send messages
                for i in range(3):  # Reduced count to avoid rate limits
                    response = await ws_helper.send_json(
                        data={"type": "chat", "content": f"Message {i}"},
                        client_id=client_id,
                        ignore_errors=True
                    )
                    assert response["type"] != "error", f"Message {i} from {client_id} should succeed"
                    
                # Small delay to simulate real usage
                await asyncio.sleep(0.1)
                
            finally:
                await ws_helper.disconnect(client_id)
                assert ws_helper.get_connection_state(client_id) == WebSocketState.DISCONNECTED
                
        # Run concurrent client workflows
        tasks = [client_workflow(cid) for cid in client_ids]
        await asyncio.gather(*tasks)
        
        # Verify final state
        count = await ws_helper.rate_limiter.get_connection_count(TEST_USER_ID)
        assert count == 0, "All connections should be cleaned up"

@pytest.mark.asyncio
@pytest.mark.real_service
async def test_redis_connection(
    test_user: User,
    websocket_helper: WebSocketTestHelper,
    websocket_manager: WebSocketManager,
    rate_limiter: WebSocketRateLimiter
):
    """Test WebSocket connection with Redis."""
    # Connect client
    ws = await websocket_helper.connect()
    assert ws.client_state == WebSocketState.CONNECTED
    
    # Send test message
    test_message = {"type": "test", "content": "Hello Redis!"}
    await websocket_helper.send_json(test_message)
    
    # Receive message back
    response = await websocket_helper.receive_json()
    assert response["type"] == "test"
    assert response["content"] == "Hello Redis!"
    
    # Clean up
    await websocket_helper.disconnect()

@pytest.mark.asyncio
@pytest.mark.real_service
async def test_redis_broadcast(
    test_user: User,
    websocket_helper: WebSocketTestHelper,
    websocket_manager: WebSocketManager,
    rate_limiter: WebSocketRateLimiter
):
    """Test broadcasting messages through Redis."""
    # Connect multiple clients
    ws1 = await websocket_helper.connect()
    ws2 = await websocket_helper.connect()
    
    assert ws1.client_state == WebSocketState.CONNECTED
    assert ws2.client_state == WebSocketState.CONNECTED
    
    # Send broadcast message from first client
    broadcast_message = {"type": "broadcast", "content": "Hello everyone!"}
    await websocket_helper.send_json(broadcast_message, ws1.client_id)
    
    # Both clients should receive the message
    response1 = await websocket_helper.receive_json(ws1.client_id)
    response2 = await websocket_helper.receive_json(ws2.client_id)
    
    assert response1["type"] == "broadcast"
    assert response1["content"] == "Hello everyone!"
    assert response2["type"] == "broadcast"
    assert response2["content"] == "Hello everyone!"
    
    # Clean up
    await websocket_helper.disconnect(ws1.client_id)
    await websocket_helper.disconnect(ws2.client_id)

@pytest.mark.asyncio
@pytest.mark.real_service
async def test_redis_reconnect(
    test_user: User,
    websocket_helper: WebSocketTestHelper,
    websocket_manager: WebSocketManager,
    rate_limiter: WebSocketRateLimiter
):
    """Test WebSocket reconnection with Redis."""
    # Connect client
    ws1 = await websocket_helper.connect()
    assert ws1.client_state == WebSocketState.CONNECTED
    
    # Send initial message
    message1 = {"type": "test", "content": "Before disconnect"}
    await websocket_helper.send_json(message1, ws1.client_id)
    
    # Verify message received
    response1 = await websocket_helper.receive_json(ws1.client_id)
    assert response1["type"] == "test"
    assert response1["content"] == "Before disconnect"
    
    # Disconnect
    await websocket_helper.disconnect(ws1.client_id)
    
    # Reconnect with same client ID
    ws2 = await websocket_helper.connect(client_id=ws1.client_id)
    assert ws2.client_state == WebSocketState.CONNECTED
    
    # Send message after reconnect
    message2 = {"type": "test", "content": "After reconnect"}
    await websocket_helper.send_json(message2, ws2.client_id)
    
    # Verify message received
    response2 = await websocket_helper.receive_json(ws2.client_id)
    assert response2["type"] == "test"
    assert response2["content"] == "After reconnect"
    
    # Clean up
    await websocket_helper.disconnect(ws2.client_id)

@pytest.mark.asyncio
@pytest.mark.real_service
async def test_redis_error_handling(
    test_user: User,
    websocket_helper: WebSocketTestHelper,
    websocket_manager: WebSocketManager,
    rate_limiter: WebSocketRateLimiter
):
    """Test Redis error handling."""
    # Connect client
    ws = await websocket_helper.connect()
    assert ws.client_state == WebSocketState.CONNECTED
    
    # Simulate Redis connection error
    # This should be handled gracefully and not crash the WebSocket
    error_message = {"type": "simulate_redis_error"}
    await websocket_helper.send_json(error_message)
    
    # Connection should still be alive
    assert ws.client_state == WebSocketState.CONNECTED
    
    # Should still be able to send/receive messages
    test_message = {"type": "test", "content": "After error"}
    await websocket_helper.send_json(test_message)
    
    response = await websocket_helper.receive_json()
    assert response["type"] == "test"
    assert response["content"] == "After error"
    
    # Clean up
    await websocket_helper.disconnect() 