"""
WARNING: These tests are designed to run in Docker.
Use 'make test' or related commands instead of running pytest directly.
See testing.mdc for more information.
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

# Use Docker service host and port for testing
DOCKER_SERVICE_HOST = os.getenv("DOCKER_SERVICE_HOST", "backend-test")
DOCKER_SERVICE_PORT = os.getenv("DOCKER_SERVICE_PORT", "8000")

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    """Initialize database before running tests."""
    await init_db()

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
    HEALTH_CHECK_URL = f"{HTTP_BASE_URL}/api/v1/health"

    # Wait for server to be ready with exponential backoff
    max_retries = 15  # Increased from 8
    retry_count = 0
    while retry_count < max_retries:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(HEALTH_CHECK_URL) as response:
                    if response.status == 200:
                        break
            retry_count += 1
            # Exponential backoff: wait longer between each retry
            await asyncio.sleep(2 ** retry_count)  # 2, 4, 8, 16... seconds
        except aiohttp.ClientError as e:
            retry_count += 1
            if retry_count == max_retries:
                raise RuntimeError(f"Server not ready after {max_retries} attempts: {str(e)}") from e
            await asyncio.sleep(2 ** retry_count)

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
async def test_websocket_connection(test_client):
    """Test that WebSocket connection requires authentication."""
    logger.info("Testing unauthenticated WebSocket connection")
    ws_url = f"{test_client}/api/v1/ws"
    logger.debug(f"Attempting to connect to: {ws_url}")
    
    try:
        # The server should reject the connection attempt
        async with ws_connect(ws_url) as _:
            logger.warning("Connection unexpectedly succeeded")
            pytest.fail("Expected connection to be rejected")
    except (ConnectionClosedError, InvalidStatusCode) as e:
        # Both exceptions are acceptable - the server is rejecting the connection
        logger.info(f"Connection rejected as expected: {str(e)}")
        # Note: We can't check the exact status code because FastAPI might handle
        # the rejection differently than a raw WebSocket server
        logger.info("Authentication check passed - connection rejected as expected")
    except Exception as e:
        logger.error(f"Unexpected error during WebSocket connection test: {str(e)}")
        raise

    logger.info("WebSocket authentication test completed successfully")

@pytest.mark.asyncio
async def test_authenticated_connection(test_client, auth_token):
    """Test that authenticated WebSocket connection works."""
    logger.info("Testing authenticated WebSocket connection")
    
    # Connect with auth token in URL
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
async def test_message_sending(test_client, auth_token):
    """Test sending and receiving messages with proper message format."""
    logger.info("Testing message sending and receiving")
    
    ws_url = f"{test_client}/api/v1/ws?token={auth_token}"
    
    async with ws_connect(ws_url) as ws:
        # Wait for welcome message
        welcome = await ws.recv()
        welcome_data = json.loads(welcome)
        client_id = welcome_data["metadata"]["client_id"]
        
        # Send a test message with proper format
        test_message = {
            "type": "chat_message",
            "content": "Hello, World!",
            "metadata": {
                "client_id": client_id,
                "timestamp": time.time()
            }
        }
        
        logger.debug(f"Sending message: {test_message}")
        await ws.send(json.dumps(test_message))
        
        # Receive and validate response
        response = await ws.recv()
        data = json.loads(response)
        
        assert data["type"] == "chat_message"
        assert data["content"] == test_message["content"]
        assert "client_id" in data["metadata"]
        logger.info("Message exchange successful") 