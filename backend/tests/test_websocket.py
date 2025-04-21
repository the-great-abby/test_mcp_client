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

import pytest_asyncio
import asyncio
import websockets
import json
import logging
from httpx import AsyncClient
import pytest
import os
from typing import AsyncGenerator
import time
from websockets.client import connect as ws_connect
from websockets.exceptions import WebSocketException, ConnectionClosedError, InvalidStatusCode
from datetime import timedelta
from sqlalchemy.ext.asyncio import AsyncSession
import aiohttp

from app.core.config import settings
from app.tests.utils.user import create_random_user
from app.core.auth import create_access_token
from app.db.session import get_async_session, init_db
from app.core.websocket import WebSocketManager

# Use Docker service host and port for testing
DOCKER_SERVICE_HOST = os.getenv("DOCKER_SERVICE_HOST", "backend-test")
DOCKER_SERVICE_PORT = os.getenv("DOCKER_SERVICE_PORT", "8000")

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    """Initialize database before running tests."""
    await init_db()

@pytest_asyncio.fixture(autouse=True)
async def clear_message_history(manager: WebSocketManager):
    """Clear WebSocket manager's message history before each test."""
    manager.message_history.clear()
    manager.message_by_id.clear()
    yield

@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    """Get a database session for testing."""
    async for session in get_async_session():
        yield session

@pytest_asyncio.fixture
async def test_client():
    """Create a test client for WebSocket connections."""
    # Configure base URLs for WebSocket and HTTP
    WS_BASE_URL = f"ws://{DOCKER_SERVICE_HOST}:{DOCKER_SERVICE_PORT}"
    HTTP_BASE_URL = f"http://{DOCKER_SERVICE_HOST}:{DOCKER_SERVICE_PORT}"
    
    # Try both health check endpoints
    HEALTH_CHECK_URLS = [
        f"{HTTP_BASE_URL}/health",
        f"{HTTP_BASE_URL}/api/v1/health"
    ]

    # Wait for server to be ready with gentler exponential backoff
    max_retries = 15
    retry_count = 0
    last_error = None
    
    while retry_count < max_retries:
        for health_url in HEALTH_CHECK_URLS:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(health_url) as response:
                        if response.status == 200:
                            logger.info(f"Server ready at {health_url}")
                            return WS_BASE_URL
            except aiohttp.ClientError as e:
                last_error = e
                logger.debug(f"Health check failed for {health_url}: {str(e)}")
                continue
        
        retry_count += 1
        if retry_count == max_retries:
            raise RuntimeError(f"Server not ready after {max_retries} attempts. Last error: {str(last_error)}")
        
        # Gentler backoff: 1, 2, 3, 4... seconds
        await asyncio.sleep(min(retry_count, 10))

    return WS_BASE_URL

@pytest_asyncio.fixture
async def auth_token(db: AsyncSession) -> str:
    """Create a test user and return their authentication token."""
    # Create a test user
    user = await create_random_user(db=db)
    
    # Generate access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=access_token_expires
    )
    return access_token

@pytest.mark.asyncio
async def test_websocket_connection(test_client, manager):
    """Test that WebSocket connection requires authentication."""
    logger.info("Testing unauthenticated WebSocket connection")
    ws_url = f"{test_client}/api/v1/ws"
    logger.debug(f"Attempting to connect to: {ws_url}")
    
    try:
        async with ws_connect(ws_url) as _:
            logger.warning("Connection unexpectedly succeeded")
            pytest.fail("Expected connection to be rejected")
    except (ConnectionClosedError, InvalidStatusCode) as e:
        logger.info(f"Connection rejected as expected: {str(e)}")
        logger.info("Authentication check passed - connection rejected as expected")
    except Exception as e:
        logger.error(f"Unexpected error during WebSocket connection test: {str(e)}")
        raise

@pytest.mark.asyncio
async def test_authenticated_connection(test_client, auth_token, manager):
    """Test that authenticated WebSocket connection works."""
    logger.info("Testing authenticated WebSocket connection")
    
    ws_url = f"{test_client}/api/v1/ws?token={auth_token}"
    logger.debug(f"Connecting to: {ws_url}")
    
    async with ws_connect(ws_url) as ws:
        try:
            msg = await ws.recv()
            data = json.loads(msg)
            assert data["type"] == "welcome"
            assert "client_id" in data["metadata"]
            logger.info("Successfully received welcome message")
        except Exception as e:
            logger.error(f"Error during authenticated connection: {str(e)}")
            raise

@pytest.mark.asyncio
async def test_message_sending(test_client, auth_token, manager):
    """Test sending and receiving messages through WebSocket."""
    ws_url = f"{test_client}/api/v1/ws?token={auth_token}"
    
    async with ws_connect(ws_url) as websocket:
        # Process initial messages (welcome, history, presence)
        initial_messages = []
        while len(initial_messages) < 2:  # At minimum, expect welcome and presence
            msg = await websocket.recv()
            data = json.loads(msg)
            initial_messages.append(data)
            
            if len(initial_messages) == 1:
                # First message should be welcome
                assert data["type"] == "welcome"
                assert "client_id" in data["metadata"]
            elif data["type"] == "history":
                # If we get history, we need one more message (presence)
                continue
        
        # Send a test message
        test_message = {
            "type": "chat_message",
            "content": "Hello, World!",
            "metadata": {
                "timestamp": str(time.time())
            }
        }
        await websocket.send(json.dumps(test_message))
        
        # Wait for the chat message echo
        while True:
            response = await websocket.recv()
            response_data = json.loads(response)
            
            if response_data["type"] == "chat_message":
                assert response_data["content"] == "Hello, World!"
                assert "client_id" in response_data["metadata"]
                assert "user_id" in response_data["metadata"]
                assert "timestamp" in response_data["metadata"]
                break
        
        logger.info("Message exchange successful") 