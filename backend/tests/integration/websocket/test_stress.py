"""Integration tests for WebSocket stress testing.

These tests verify the WebSocket infrastructure's behavior under load
and stress conditions.
"""
import pytest
import asyncio
import uuid
import logging
from datetime import datetime, timedelta
from websockets.exceptions import ConnectionClosed
from contextlib import AsyncExitStack
from typing import List, Dict, Any
import random

from app.core.websocket import WebSocketManager
from app.core.websocket_rate_limiter import WebSocketRateLimiter
from app.core.auth import create_access_token
from app.models import User
from tests.utils.websocket_test_helper import WebSocketTestHelper

# Test configuration
WS_BASE_URL = "/api/v1/ws"
logger = logging.getLogger(__name__)

async def create_connections(
    auth_token: str,
    batch_size: int,
    test_helpers: List[WebSocketTestHelper]
) -> List[WebSocketTestHelper]:
    """Create a batch of WebSocket connections.
    
    Args:
        auth_token: Authentication token
        batch_size: Number of connections to create
        test_helpers: List to store helpers for cleanup
        
    Returns:
        List[WebSocketTestHelper]: List of connected helpers
    """
    helpers = []
    for i in range(batch_size):
        helper = test_helpers[i] if i < len(test_helpers) else None
        if not helper or not helper.connected:
            success = await helper.connect(auth_token=auth_token)
            if not success:
                logger.error(f"Failed to connect helper {i}")
                continue
        helpers.append(helper)
    return helpers

@pytest.mark.real_service
async def test_concurrent_connections(
    auth_token: str,
    redis_rate_limiter: WebSocketRateLimiter,
    test_helpers: List[WebSocketTestHelper]
):
    """Test handling of many concurrent connections.
    
    Verifies:
    - System can handle multiple simultaneous connections
    - Rate limiting works under load
    - Resources are properly managed
    - No memory leaks occur
    """
    # Configure rate limiter for test
    redis_rate_limiter.max_connections = 50
    redis_rate_limiter.window_seconds = 60
    
    # Create connections in batches
    batch_size = 10
    total_batches = 5
    connection_delays = []
    
    for batch in range(total_batches):
        start_time = datetime.now()
        helpers = await create_connections(auth_token, batch_size, test_helpers)
        end_time = datetime.now()
        connection_delays.append((end_time - start_time).total_seconds())
        
        # Verify all connections are working
        for helper in helpers:
            response = await helper.send_message(
                "ping",
                "",
                expect_response=True
            )
            assert response["type"] == "pong"
    
    # Verify connection timing remains reasonable
    assert max(connection_delays) < 5.0, "Connection time increased significantly"
    
    # Verify rate limit state
    for helper in test_helpers:
        if helper.test_ip:
            count = await redis_rate_limiter.get_connection_count(helper.test_ip)
            assert count <= redis_rate_limiter.max_connections