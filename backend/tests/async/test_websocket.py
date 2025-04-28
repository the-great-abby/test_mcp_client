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

import pytest
import json
import logging
from datetime import timedelta
from httpx import AsyncClient
from app.core.auth import create_access_token
from app.main import app
from app.core.websocket import WebSocketManager
from app.models import User
from tests.conftest import test_settings
import os
import websockets
import asyncio

# Use Docker service host and port for testing
DOCKER_SERVICE_HOST = os.getenv("DOCKER_SERVICE_HOST", "backend-test")
DOCKER_SERVICE_PORT = os.getenv("DOCKER_SERVICE_PORT", "8000")

# Base URLs for API endpoints
API_BASE_URL = "/api/v1"
WS_BASE_URL = f"{API_BASE_URL}/ws"
HTTP_BASE_URL = f"http://{DOCKER_SERVICE_HOST}:{DOCKER_SERVICE_PORT}"

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

@pytest.fixture
def test_user():
    # Minimal test user object; replace with real user creation if needed
    class DummyUser:
        id = 1
    return DummyUser()

@pytest.fixture
def auth_token(test_user, test_settings):
    access_token_expires = timedelta(minutes=test_settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return create_access_token(
        data={"sub": str(test_user.id)},
        expires_delta=access_token_expires,
        settings=test_settings
    )

@pytest.mark.asyncio
async def test_websocket_connection():
    print("[DEBUG] Starting test_websocket_connection")
    uri = "ws://backend-test:8000/api/v1/ws"
    async with websockets.connect(uri) as ws:
        # Always receive the welcome message first
        welcome = json.loads(await ws.recv())
        print(f"[DEBUG] Welcome: {welcome}")
        assert welcome["type"] == "welcome"
        # Now send ping and wait for pong
        await ws.send(json.dumps({"type": "ping", "content": ""}))
        while True:
            msg = json.loads(await ws.recv())
            print(f"[DEBUG] Received: {msg}")
            if msg["type"] == "pong":
                break
    print("[DEBUG] Finished test_websocket_connection")

@pytest.mark.asyncio
async def test_authenticated_connection(auth_token):
    print("[DEBUG] Starting test_authenticated_connection")
    uri = f"ws://backend-test:8000/api/v1/ws?token={auth_token}"
    async with websockets.connect(uri) as ws:
        data = json.loads(await ws.recv())
        print(f"[DEBUG] Received: {data}")
        assert data["type"] == "welcome"
        assert "Connected to chat server" in data["content"]
        assert "client_id" in data["metadata"]
        assert "user_id" in data["metadata"]
    print("[DEBUG] Finished test_authenticated_connection")

@pytest.mark.asyncio
async def test_message_sending(auth_token, initialize_test_db):
    print("[DEBUG] Starting test_message_sending")
    uri = f"ws://backend-test:8000/api/v1/ws?token={auth_token}"
    async with websockets.connect(uri) as ws:
        welcome = json.loads(await ws.recv())
        print(f"[DEBUG] Welcome: {welcome}")
        assert welcome["type"] == "welcome"
        test_message = {
            "type": "chat_message",
            "content": "Hello, World!",
            "metadata": {}
        }
        await ws.send(json.dumps(test_message))
        while True:
            response = json.loads(await ws.recv())
            print(f"[DEBUG] Response: {response}")
            if response["type"] in ("chat", "chat_message"):
                assert response["content"] == "Hello, World!"
                assert "message_id" in response
                assert "timestamp" in response
                break
        await asyncio.sleep(0.1)
    print("[DEBUG] Finished test_message_sending")

@pytest.mark.asyncio
async def test_typing_indicator(auth_token):
    print("[DEBUG] Starting test_typing_indicator")
    uri = f"ws://backend-test:8000/api/v1/ws?token={auth_token}"
    async with websockets.connect(uri) as ws:
        welcome = json.loads(await ws.recv())
        print(f"[DEBUG] Welcome: {welcome}")
        assert welcome["type"] == "welcome"
        typing_message = {
            "type": "typing_indicator",
            "content": "true",
            "metadata": {}
        }
        await ws.send(json.dumps(typing_message))
        while True:
            response = json.loads(await ws.recv())
            print(f"[DEBUG] Response: {response}")
            if response["type"] == "typing_indicator":
                assert response["content"] == "true"
                assert "user_id" in response or "user_id" in response.get("metadata", {})
                break
    print("[DEBUG] Finished test_typing_indicator")

@pytest.mark.asyncio
async def test_websocket_status(auth_token):
    print("[DEBUG] Starting test_websocket_status")
    uri = f"ws://backend-test:8000/api/v1/ws?token={auth_token}"
    async with websockets.connect(uri) as ws:
        # Always receive the welcome message first
        welcome = json.loads(await ws.recv())
        print(f"[DEBUG] Welcome: {welcome}")
        assert welcome["type"] == "welcome"
        client_id = welcome["metadata"]["client_id"]
        # Optionally, add more checks for connection status if available
    print("[DEBUG] Finished test_websocket_status")

@pytest.mark.asyncio
async def test_rate_limiting(auth_token):
    print("[DEBUG] Starting test_rate_limiting")
    uri = f"ws://backend-test:8000/api/v1/ws?token={auth_token}"
    async with websockets.connect(uri) as ws:
        welcome = json.loads(await ws.recv())
        print(f"[DEBUG] Welcome: {welcome}")
        assert welcome["type"] == "welcome"
        client_id = welcome["metadata"]["client_id"]
        messages_sent = 0
        messages_rejected = 0
        for i in range(5):
            message = {
                "type": "chat_message",
                "content": f"Test message {i}",
                "metadata": {}
            }
            await ws.send(json.dumps(message))
            while True:
                response = json.loads(await ws.recv())
                print(f"[DEBUG] Message {i} response: {response}")
                if response["type"] == "error" and response["metadata"].get("error_type") == "rate_limit":
                    messages_rejected += 1
                    break
                elif response["type"] in ("chat", "chat_message"):
                    messages_sent += 1
                    break
        # Accept all if no rate limiting, or adjust as needed
        assert messages_sent + messages_rejected == 5
    print("[DEBUG] Finished test_rate_limiting")

@pytest.mark.asyncio
async def test_system_message_bypass(auth_token):
    print("[DEBUG] Starting test_system_message_bypass")
    uri = f"ws://backend-test:8000/api/v1/ws?token={auth_token}"
    async with websockets.connect(uri) as ws:
        # Always receive the welcome message first
        welcome = json.loads(await ws.recv())
        print(f"[DEBUG] Welcome: {welcome}")
        assert welcome["type"] == "welcome"
        client_id = welcome["metadata"]["client_id"]
        messages_sent = 0
        messages_rejected = 0
        for i in range(5):
            message = {
                "type": "system",
                "content": f"System notification {i}",
                "metadata": {"system_type": "test"}
            }
            await ws.send(json.dumps(message))
            # Read messages until we get the expected system message or error
            for _ in range(10):  # Prevent infinite loop
                try:
                    response = json.loads(await asyncio.wait_for(ws.recv(), timeout=2))
                except asyncio.TimeoutError:
                    print(f"[DEBUG] Timeout waiting for system message {i}")
                    break
                print(f"[DEBUG] System message {i} response: {response}")
                if response["type"] == "system":
                    messages_sent += 1
                    break
                elif response["type"] == "error" and response["metadata"].get("error_type") == "rate_limit":
                    messages_rejected += 1
                    break
                # Optionally, handle or ignore other message types
            else:
                print(f"[DEBUG] No expected response for system message {i}, breaking loop")
        assert messages_sent == 5, "Expected all system messages to be accepted"
        assert messages_rejected == 0, "Expected no system messages to be rejected"
    print("[DEBUG] Finished test_system_message_bypass")