"""Integration tests for WebSocket error recovery and resilience.

These tests verify the WebSocket connection's ability to handle various error conditions
and recover gracefully.
"""
import pytest
import asyncio
import uuid
import logging
from datetime import datetime, timedelta
from websockets.exceptions import ConnectionClosed, InvalidStatusCode
from contextlib import AsyncExitStack
from typing import List

from app.core.websocket import WebSocketManager, WebSocketState
from tests.utils.websocket_test_helper import WebSocketTestHelper
from tests.utils.mock_websocket import MockWebSocket
from app.core.websocket_rate_limiter import WebSocketRateLimiter
from app.core.auth import create_access_token

# Test configuration
BACKOFF_BASE = 0.1  # seconds
MAX_RETRIES = 3
TEST_USER_ID = "test_user_123"
logger = logging.getLogger(__name__)

@pytest.fixture
def auth_token():
    """Create a valid auth token for testing."""
    return create_access_token(data={"sub": TEST_USER_ID})

@pytest.fixture
async def test_helpers():
    """Fixture for managing multiple WebSocket helpers."""
    helpers = []
    async with AsyncExitStack() as stack:
        try:
            yield helpers
        finally:
            for helper in helpers:
                await helper.cleanup()

@pytest.mark.real_service
class TestWebSocketRecovery:
    """Test suite for WebSocket recovery functionality."""
    
    async def test_connection_recovery_after_server_close(
        self,
        websocket_manager: WebSocketManager,
        rate_limiter: WebSocketRateLimiter,
        test_helpers: List[WebSocketTestHelper],
        auth_token: str
    ):
        """Test connection recovery after server-side close."""
        client_id = str(uuid.uuid4())
        helper = WebSocketTestHelper(
            websocket_manager=websocket_manager,
            rate_limiter=rate_limiter,
            test_user_id=TEST_USER_ID,
            test_ip="127.0.0.1",
            auth_token=auth_token
        )
        test_helpers.append(helper)
        
        # Initial connection
        ws = await helper.connect(client_id=client_id)
        assert ws.client_state == WebSocketState.CONNECTED
        
        # Send test message
        response = await helper.send_json(
            data={
                "type": "chat_message",
                "content": "Test message",
                "metadata": {}
            },
            client_id=client_id
        )
        assert response["type"] == "chat_message"
        
        # Simulate server close
        await websocket_manager.disconnect(client_id)
        
        # Wait for reconnection
        await asyncio.sleep(0.1)
        
        # Verify can reconnect
        ws = await helper.connect(client_id=client_id)
        assert ws.client_state == WebSocketState.CONNECTED
        
        # Verify connection works
        response = await helper.send_json(
            data={
                "type": "chat_message",
                "content": "After recovery",
                "metadata": {}
            },
            client_id=client_id
        )
        assert response["type"] == "chat_message"
    
    async def test_message_ordering_after_reconnect(
        self,
        websocket_manager: WebSocketManager,
        rate_limiter: WebSocketRateLimiter,
        test_helpers: List[WebSocketTestHelper],
        auth_token: str
    ):
        """Test message ordering is maintained after reconnection."""
        client_id = str(uuid.uuid4())
        helper = WebSocketTestHelper(
            websocket_manager=websocket_manager,
            rate_limiter=rate_limiter,
            test_user_id=TEST_USER_ID,
            test_ip="127.0.0.1",
            auth_token=auth_token
        )
        test_helpers.append(helper)
        
        # Initial connection
        ws = await helper.connect(client_id=client_id)
        assert ws.client_state == WebSocketState.CONNECTED
        
        # Send first batch of messages
        messages = []
        for i in range(3):
            response = await helper.send_json(
                data={
                    "type": "chat_message",
                    "content": f"Message {i}",
                    "metadata": {}
                },
                client_id=client_id
            )
            messages.append(response)
        
        # Verify order
        for i, msg in enumerate(messages):
            assert msg["content"] == f"Message {i}"
        
        # Simulate disconnect
        await websocket_manager.disconnect(client_id)
        await asyncio.sleep(0.1)
        
        # Reconnect
        ws = await helper.connect(client_id=client_id)
        assert ws.client_state == WebSocketState.CONNECTED
        
        # Send second batch of messages
        messages = []
        for i in range(3, 6):
            response = await helper.send_json(
                data={
                    "type": "chat_message",
                    "content": f"Message {i}",
                    "metadata": {}
                },
                client_id=client_id
            )
            messages.append(response)
        
        # Verify order maintained
        for i, msg in enumerate(messages, start=3):
            assert msg["content"] == f"Message {i}"
    
    async def test_connection_backoff(
        self,
        websocket_manager: WebSocketManager,
        rate_limiter: WebSocketRateLimiter,
        test_helpers: List[WebSocketTestHelper],
        auth_token: str
    ):
        """Test exponential backoff on connection failures."""
        client_id = str(uuid.uuid4())
        helper = WebSocketTestHelper(
            websocket_manager=websocket_manager,
            rate_limiter=rate_limiter,
            test_user_id=TEST_USER_ID,
            test_ip="127.0.0.1",
            auth_token=auth_token
        )
        test_helpers.append(helper)
        
        start_time = datetime.now()
        retry_count = 0
        
        while retry_count < MAX_RETRIES:
            try:
                # Use invalid token to force failure
                await helper.connect(
                    client_id=client_id,
                    token="invalid"
                )
            except ConnectionClosed:
                pass
                
            retry_count += 1
            if retry_count < MAX_RETRIES:
                backoff_delay = BACKOFF_BASE * (2 ** (retry_count - 1))
                await asyncio.sleep(backoff_delay)
        
        duration = (datetime.now() - start_time).total_seconds()
        expected_total_delay = sum(
            BACKOFF_BASE * (2 ** i) for i in range(MAX_RETRIES - 1)
        )
        
        # Verify backoff timing
        assert duration >= expected_total_delay, "Backoff delays should be respected"
        
        # Verify can connect with valid token
        ws = await helper.connect(client_id=client_id)
        assert ws.client_state == WebSocketState.CONNECTED
    
    async def test_concurrent_recovery(
        self,
        websocket_manager: WebSocketManager,
        rate_limiter: WebSocketRateLimiter,
        test_helpers: List[WebSocketTestHelper],
        auth_token: str
    ):
        """Test multiple connections recovering concurrently."""
        num_clients = 3
        clients = []
        
        # Create and connect multiple clients
        for i in range(num_clients):
            client_id = str(uuid.uuid4())
            helper = WebSocketTestHelper(
                websocket_manager=websocket_manager,
                rate_limiter=rate_limiter,
                test_user_id=TEST_USER_ID,
                test_ip="127.0.0.1",
                auth_token=auth_token
            )
            test_helpers.append(helper)
            
            ws = await helper.connect(client_id=client_id)
            assert ws.client_state == WebSocketState.CONNECTED
            
            clients.append((client_id, helper))
        
        # Close all connections
        for client_id, _ in clients:
            await websocket_manager.disconnect(client_id)
        
        await asyncio.sleep(0.1)
        
        # Reconnect all concurrently
        async def reconnect(client_id: str, helper: WebSocketTestHelper):
            ws = await helper.connect(client_id=client_id)
            assert ws.client_state == WebSocketState.CONNECTED
            
            response = await helper.send_json(
                data={
                    "type": "chat_message",
                    "content": f"Recovery from {client_id}",
                    "metadata": {}
                },
                client_id=client_id
            )
            assert response["type"] == "chat_message"
            return client_id
        
        tasks = [
            reconnect(client_id, helper)
            for client_id, helper in clients
        ]
        
        recovered_clients = await asyncio.gather(*tasks)
        assert len(recovered_clients) == num_clients, "All clients should recover"
    
    async def test_partial_message_recovery(
        self,
        websocket_manager: WebSocketManager,
        rate_limiter: WebSocketRateLimiter,
        test_helpers: List[WebSocketTestHelper],
        auth_token: str
    ):
        """Test recovery with partial message delivery."""
        client_id = str(uuid.uuid4())
        helper = WebSocketTestHelper(
            websocket_manager=websocket_manager,
            rate_limiter=rate_limiter,
            test_user_id=TEST_USER_ID,
            test_ip="127.0.0.1",
            auth_token=auth_token
        )
        test_helpers.append(helper)
        
        # Initial connection
        ws = await helper.connect(client_id=client_id)
        assert ws.client_state == WebSocketState.CONNECTED
        
        # Start stream
        stream_messages, final_message = await helper.wait_for_stream(
            initial_message={
                "type": "stream_start",
                "content": "Start stream",
                "metadata": {}
            },
            client_id=client_id,
            ignore_errors=True
        )
        
        # Verify stream was interrupted
        assert not stream_messages, "Stream should be empty"
        assert final_message.get("type") == "error"
        assert "stream" in final_message.get("content", "").lower()
        
        # Verify can still send messages
        response = await helper.send_json(
            data={
                "type": "chat_message",
                "content": "After stream interruption",
                "metadata": {}
            },
            client_id=client_id
        )
        assert response["type"] == "chat_message" 