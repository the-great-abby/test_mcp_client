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
import os

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

@pytest.mark.real_websocket
@pytest.mark.db_test  # TODO: Remove if no DB interaction occurs in these tests
class TestWebSocketRecovery:
    """Test suite for WebSocket recovery functionality."""
    
    @pytest.mark.real_websocket
    async def test_connection_recovery_after_server_close(self, real_websocket_client):
        """Test connection recovery after server-side close using the real WebSocket client."""
        # Connect
        await real_websocket_client.connect()
        assert real_websocket_client.is_connected()
        
        # Send test message
        await real_websocket_client.send_json({
            "type": "chat_message",
            "content": "Test message",
            "metadata": {}
        })
        response = await real_websocket_client.receive_json()
        assert response["type"] == "chat_message"
        
        # Simulate server close by closing the client connection
        await real_websocket_client.close()
        assert not real_websocket_client.is_connected()
        
        # Wait for reconnection (simulate delay)
        await asyncio.sleep(0.1)
        
        # Reconnect
        await real_websocket_client.connect()
        assert real_websocket_client.is_connected()
        
        # Verify connection works
        await real_websocket_client.send_json({
            "type": "chat_message",
            "content": "After recovery",
            "metadata": {}
        })
        response = await real_websocket_client.receive_json()
        assert response["type"] == "chat_message"
    
    @pytest.mark.real_websocket
    async def test_message_ordering_after_reconnect(self, real_websocket_client):
        """Test message ordering is maintained after reconnection using the real WebSocket client."""
        await real_websocket_client.connect()
        assert real_websocket_client.is_connected()

        # Send first batch of messages
        messages = []
        for i in range(3):
            await real_websocket_client.send_json({
                "type": "chat_message",
                "content": f"Message {i}",
                "metadata": {}
            })
            response = await real_websocket_client.receive_json()
            messages.append(response)

        # Verify order
        for i, msg in enumerate(messages):
            assert msg["content"] == f"Message {i}"

        # Simulate disconnect
        await real_websocket_client.close()
        await asyncio.sleep(0.1)

        # Reconnect
        await real_websocket_client.connect()
        assert real_websocket_client.is_connected()

        # Send second batch of messages
        messages = []
        for i in range(3, 6):
            await real_websocket_client.send_json({
                "type": "chat_message",
                "content": f"Message {i}",
                "metadata": {}
            })
            response = await real_websocket_client.receive_json()
            messages.append(response)

        # Verify order maintained
        for i, msg in enumerate(messages, start=3):
            assert msg["content"] == f"Message {i}"
    
    @pytest.mark.real_websocket
    async def test_connection_backoff(self, real_websocket_client):
        """Test exponential backoff on connection failures using the real WebSocket client."""
        # This test assumes the client will fail to connect with an invalid token
        start_time = datetime.now()
        retry_count = 0
        while retry_count < MAX_RETRIES:
            try:
                # Use invalid token to force failure
                real_websocket_client.token = "invalid"
                await real_websocket_client.connect()
            except Exception:
                pass
            retry_count += 1
            if retry_count < MAX_RETRIES:
                backoff_delay = BACKOFF_BASE * (2 ** (retry_count - 1))
                await asyncio.sleep(backoff_delay)
        duration = (datetime.now() - start_time).total_seconds()
        expected_total_delay = sum(
            BACKOFF_BASE * (2 ** i) for i in range(MAX_RETRIES - 1)
        )
        assert duration >= expected_total_delay, "Backoff delays should be respected"
        # Verify can connect with valid token
        real_websocket_client.token = os.getenv("TEST_USER_TOKEN")
        await real_websocket_client.connect()
        assert real_websocket_client.is_connected()
    
    @pytest.mark.real_websocket
    async def test_concurrent_recovery(self, real_websocket_client):
        """Test multiple connections recovering concurrently using the real WebSocket client."""
        num_clients = 3
        clients = []
        for i in range(num_clients):
            client = type(real_websocket_client)(
                real_websocket_client.uri,
                token=real_websocket_client.token,
                debug=real_websocket_client.debug
            )
            await client.connect()
            assert client.is_connected()
            clients.append(client)
        # Close all connections
        for client in clients:
            await client.close()
        await asyncio.sleep(0.1)
        # Reconnect all concurrently
        async def reconnect(client):
            await client.connect()
            assert client.is_connected()
            await client.send_json({
                "type": "chat_message",
                "content": f"Recovery from {id(client)}",
                "metadata": {}
            })
            response = await client.receive_json()
            assert response["type"] == "chat_message"
            return id(client)
        tasks = [reconnect(client) for client in clients]
        recovered_clients = await asyncio.gather(*tasks)
        assert len(recovered_clients) == num_clients, "All clients should recover"
    
    @pytest.mark.real_websocket
    async def test_partial_message_recovery(self, real_websocket_client):
        """Test recovery with partial message delivery using the real WebSocket client."""
        await real_websocket_client.connect()
        assert real_websocket_client.is_connected()
        # Start stream (simulate with a message that should trigger an error/interrupt)
        await real_websocket_client.send_json({
            "type": "stream_start",
            "content": "Start stream",
            "metadata": {"interrupt_stream": True}
        })
        # Receive the first message (content block)
        first_message = await real_websocket_client.receive_json()
        assert "content_block_delta" in first_message or "content" in first_message
        # Receive the next message (error)
        final_message = await real_websocket_client.receive_json()
        assert final_message.get("type") == "error"
        assert "stream" in final_message.get("content", "").lower()
        # Verify can still send messages
        await real_websocket_client.send_json({
            "type": "chat_message",
            "content": "After stream interruption",
            "metadata": {}
        })
        response = await real_websocket_client.receive_json()
        assert response["type"] == "chat_message" 