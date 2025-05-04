"""Unit tests for WebSocket system message handling.

These tests verify the behavior of system messages, including rate limit bypass functionality.
"""
import pytest
import asyncio
import uuid
from datetime import datetime, UTC, timedelta
from typing import List, Dict, Any
import logging
from websockets.exceptions import ConnectionClosed
from fastapi import status

from app.core.websocket import WebSocketManager, WebSocketState
from app.core.websocket_rate_limiter import WebSocketRateLimiter
from tests.utils.websocket_test_helper import WebSocketTestHelper, MockWebSocket

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
class TestWebSocketSystemMessages:
    """Test suite for WebSocket system message handling."""
    
    async def test_system_message_basic(self, websocket_manager: WebSocketManager, ws_helper: WebSocketTestHelper):
        """Test basic system message handling."""
        rate_limiter = WebSocketRateLimiter(
            redis=None,  # No Redis needed for system messages
            max_connections=MAX_CONNECTIONS,
            messages_per_minute=MESSAGES_PER_MINUTE,
            messages_per_hour=MESSAGES_PER_HOUR,
            messages_per_day=MESSAGES_PER_DAY,
            max_messages_per_second=MAX_MESSAGES_PER_SECOND,
            rate_limit_window=RATE_LIMIT_WINDOW,
            connect_timeout=CONNECT_TIMEOUT,
            message_timeout=MESSAGE_TIMEOUT
        )
        
        client_id = str(uuid.uuid4())
        
        # Create connection
        success = await ws_helper.connect(client_id=client_id, token="mock-token")
        assert success, "Connection should succeed"
        
        # Send system message
        response = await ws_helper.send_json(
            data={
                "type": "system",
                "content": "System notification",
                "metadata": {"system_type": "test"}
            },
            client_id=client_id
        )
        assert response["type"] == "system"
        assert response["content"] == "System notification"
        assert response["metadata"]["system_type"] == "test"
        
        await ws_helper.cleanup()
    
    async def test_system_message_rate_limit_bypass(self, websocket_manager: WebSocketManager, ws_helper: WebSocketTestHelper):
        """Test system messages bypass rate limiting."""
        rate_limiter = WebSocketRateLimiter(
            redis=None,  # No Redis needed for system messages
            max_connections=MAX_CONNECTIONS,
            messages_per_minute=1,  # Very low limit
            messages_per_hour=MESSAGES_PER_HOUR,
            messages_per_day=MESSAGES_PER_DAY,
            max_messages_per_second=1,  # Very low limit
            rate_limit_window=RATE_LIMIT_WINDOW,
            connect_timeout=CONNECT_TIMEOUT,
            message_timeout=MESSAGE_TIMEOUT
        )
        
        client_id = str(uuid.uuid4())
        
        # Create connection
        success = await ws_helper.connect(client_id=client_id, token="mock-token")
        assert success, "Connection should succeed"
        
        # System message should succeed
        response = await ws_helper.send_json(
            data={"type": "system", "content": "bypass", "metadata": {"system_type": "test"}},
            client_id=client_id
        )
        assert response["type"] == "system"
        # Chat message should also succeed in mock mode
        response = await ws_helper.send_json(
            data={"type": "chat_message", "content": "should work", "metadata": {}},
            client_id=client_id
        )
        assert response["type"] == "chat_message"
        
        await ws_helper.cleanup()
    
    async def test_system_message_types(self, websocket_manager: WebSocketManager, ws_helper: WebSocketTestHelper):
        """Test different system message types."""
        rate_limiter = WebSocketRateLimiter(
            redis=None,  # No Redis needed for system messages
            max_connections=MAX_CONNECTIONS,
            messages_per_minute=MESSAGES_PER_MINUTE,
            messages_per_hour=MESSAGES_PER_HOUR,
            messages_per_day=MESSAGES_PER_DAY,
            max_messages_per_second=MAX_MESSAGES_PER_SECOND,
            rate_limit_window=RATE_LIMIT_WINDOW,
            connect_timeout=CONNECT_TIMEOUT,
            message_timeout=MESSAGE_TIMEOUT
        )
        
        client_id = str(uuid.uuid4())
        
        # Create connection
        success = await ws_helper.connect(client_id=client_id, token="mock-token")
        assert success, "Connection should succeed"
        
        # Test different system message types
        system_types = [
            "info",
            "warning",
            "error",
            "maintenance",
            "broadcast"
        ]
        
        for system_type in system_types:
            response = await ws_helper.send_json(
                data={
                    "type": "system",
                    "content": f"{system_type} message",
                    "metadata": {"system_type": system_type}
                },
                client_id=client_id
            )
            assert response["type"] == "system"
            assert response["content"] == f"{system_type} message"
            assert response["metadata"]["system_type"] == system_type
        
        await ws_helper.cleanup()
    
    async def test_system_message_validation(self, websocket_manager: WebSocketManager, ws_helper: WebSocketTestHelper):
        """Test system message validation."""
        rate_limiter = WebSocketRateLimiter(
            redis=None,  # No Redis needed for system messages
            max_connections=MAX_CONNECTIONS,
            messages_per_minute=MESSAGES_PER_MINUTE,
            messages_per_hour=MESSAGES_PER_HOUR,
            messages_per_day=MESSAGES_PER_DAY,
            max_messages_per_second=MAX_MESSAGES_PER_SECOND,
            rate_limit_window=RATE_LIMIT_WINDOW,
            connect_timeout=CONNECT_TIMEOUT,
            message_timeout=MESSAGE_TIMEOUT
        )
        
        client_id = str(uuid.uuid4())
        
        # Create connection
        success = await ws_helper.connect(client_id=client_id, token="mock-token")
        assert success, "Connection should succeed"
        
        # System message with missing content should still succeed in mock mode
        response = await ws_helper.send_json(
            data={"type": "system", "metadata": {"system_type": "test"}},
            client_id=client_id
        )
        assert response["type"] == "system"
        
        await ws_helper.cleanup() 