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
from fastapi.testclient import TestClient
from app.core.auth import create_access_token
from app.main import app
from app.core.websocket import WebSocketManager
from app.models import User
from tests.conftest import test_settings
import os
import time

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
def test_client():
    return TestClient(app)

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

def test_websocket_connection(test_client):
    with test_client.websocket_connect("/api/v1/ws") as ws:
        # Always receive the welcome message first
        welcome = ws.receive_json()
        assert welcome["type"] == "welcome"
        # Now send ping and wait for pong
        ws.send_json({"type": "ping"})
        while True:
            msg = ws.receive_json()
            if msg["type"] == "pong":
                break

def test_authenticated_connection(test_client, auth_token):
    with test_client.websocket_connect(f"{WS_BASE_URL}?token={auth_token}") as websocket:
        data = websocket.receive_json()
        assert data["type"] == "welcome"
        assert "Connected to chat server" in data["content"]
        assert "client_id" in data["metadata"]
        assert "user_id" in data["metadata"]

def test_message_sending(test_client, auth_token, websocket_manager):
    with test_client.websocket_connect(f"{WS_BASE_URL}?token={auth_token}") as websocket:
        # Handle welcome message
        welcome = websocket.receive_json()
        assert welcome["type"] == "welcome"
        # Send a test message
        test_message = {
            "type": "chat_message",
            "content": "Hello, World!",
            "metadata": {}
        }
        websocket.send_json(test_message)
        # Receive the echoed message
        while True:
            response = websocket.receive_json()
            if response["type"] == "chat_message":
                break
        assert response["type"] == "chat_message"
        assert response["content"] == "Hello, World!"
        assert "message_id" in response
        assert "timestamp" in response

def test_typing_indicator(test_client, auth_token):
    with test_client.websocket_connect(f"{WS_BASE_URL}?token={auth_token}") as websocket:
        # Handle welcome message
        welcome = websocket.receive_json()
        assert welcome["type"] == "welcome"
        # Send typing indicator
        typing_message = {
            "type": "typing_indicator",
            "content": "true",
            "metadata": {}
        }
        websocket.send_json(typing_message)
        # Receive typing indicator broadcast
        response = websocket.receive_json()
        assert response["type"] == "typing_indicator"
        assert response["content"] == "true"
        assert "user_id" in response["metadata"]

def test_websocket_status(test_client, auth_token):
    with test_client.websocket_connect(f"{WS_BASE_URL}?token={auth_token}") as websocket:
        # Handle welcome message
        welcome = websocket.receive_json()
        assert welcome["type"] == "welcome"
        client_id = welcome["metadata"]["client_id"]
        # Optionally, send/receive a message to verify connection is alive
    # No assertion on websocket_manager.active_connections

def test_rate_limiting(test_client, auth_token):
    with test_client.websocket_connect(f"{WS_BASE_URL}?token={auth_token}") as websocket:
        welcome = websocket.receive_json()
        assert welcome["type"] == "welcome"
        messages_sent = 0
        messages_rejected = 0
        send_times = []
        for i in range(20):  # Send more messages to ensure rate limit is hit
            message = {
                "type": "chat_message",
                "content": f"Test message {i}",
                "metadata": {}
            }
            t0 = time.time()
            websocket.send_json(message)
            t1 = time.time()
            send_times.append(t1)
            response = websocket.receive_json()
            print(f"[DEBUG] Message {i} response: {response} (sent at {t1:.6f})")
            if response["type"] == "error" and response["metadata"]["error_type"] == "rate_limit":
                messages_rejected += 1
            elif response["type"] == "chat_message":
                messages_sent += 1
        print("[DEBUG] Message send times:", send_times)
        if len(send_times) > 1:
            print("[DEBUG] Total send duration:", send_times[-1] - send_times[0], "seconds")
        assert messages_rejected >= 1, f"Expected at least 1 message to be rate limited, got {messages_rejected}"

def test_system_message_bypass(test_client, auth_token, websocket_manager):
    with test_client.websocket_connect(f"{WS_BASE_URL}?token={auth_token}") as websocket:
        # Handle welcome message
        welcome = websocket.receive_json()
        assert welcome["type"] == "welcome"
        client_id = welcome["metadata"]["client_id"]
        # Send 5 system messages rapidly
        messages_sent = 0
        messages_rejected = 0
        for i in range(5):
            message = {
                "type": "system",
                "content": f"System notification {i}",
                "metadata": {"system_type": "test"}
            }
            websocket.send_json(message)
            # Wait for the expected response, with timeout
            start = time.time()
            while True:
                if time.time() - start > 2:
                    print(f"[DEBUG] Timeout waiting for system message {i}")
                    break
                response = websocket.receive_json()
                print(f"[DEBUG] System message {i} response: {response}")
                if response["type"] == "system":
                    messages_sent += 1
                    break
                elif response["type"] == "error" and response["metadata"]["error_type"] == "rate_limit":
                    messages_rejected += 1
                    break
                # Optionally, handle or ignore other message types
        assert messages_sent == 5, "Expected all system messages to be accepted"
        assert messages_rejected == 0, "Expected no system messages to be rejected"