"""
NOTE: These tests are for reference only.
See async/test_websocket_rate_limit.py for actual rate limit enforcement tests.

Tests for WebSocket rate limiting functionality.
"""
import pytest
from fastapi import status
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocketDisconnect
from app.main import app
from app.core.websocket import WebSocketManager
from app.core.websocket_rate_limiter import WebSocketRateLimiter
from app.core.auth import create_access_token
from app.core.config import Settings
from tests.conftest import test_settings
import os
import json

# Rate limit constants (match actual implementation)
MAX_CONNECTIONS_PER_IP = 20  # From WebSocketRateLimiter default
MAX_MESSAGES_PER_MINUTE = 10  # From WebSocketRateLimiter default

# Use Docker service host and port for testing (internal network)
WS_HOST = os.getenv("DOCKER_SERVICE_HOST", "backend-test")
WS_PORT = int(os.getenv("DOCKER_SERVICE_PORT", "8000"))

# Base URLs for internal Docker network communication
WS_BASE_URL = f"ws://{WS_HOST}:{WS_PORT}"
HTTP_BASE_URL = f"http://{WS_HOST}:{WS_PORT}"

@pytest.fixture
def test_client():
    return TestClient(app)

@pytest.fixture
def websocket_manager():
    return WebSocketManager()

@pytest.fixture
def rate_limiter(redis_client):
    return WebSocketRateLimiter(
        redis=redis_client,
        max_connections_per_user=MAX_CONNECTIONS_PER_IP,
        max_connections_per_ip=MAX_CONNECTIONS_PER_IP,
        connection_window_seconds=1,
        max_connections_per_window=MAX_CONNECTIONS_PER_IP,
        message_window_seconds=1,
        max_messages_per_window=MAX_MESSAGES_PER_MINUTE
    )

@pytest.fixture
def test_user():
    class DummyUser:
        id = 1
    return DummyUser()

@pytest.fixture
def test_settings():
    return Settings(ENVIRONMENT="test")

@pytest.mark.skip(reason='Reference only; see async/test_websocket_rate_limit.py for actual rate limit enforcement tests.')
def test_rate_limit_by_ip(test_client, websocket_manager, rate_limiter):
    websocket_manager.rate_limiter = rate_limiter
    # First connection should work
    with test_client.websocket_connect("/api/v1/ws") as websocket:
        resp = websocket.receive_json()
        assert resp["type"] == "welcome"
        websocket.send_json({"type": "chat_message", "content": "test message"})
        while True:
            resp = websocket.receive_json()
            if resp["type"] == "chat_message":
                break
        assert resp["content"] == "test message"
    # Second connection should work
    with test_client.websocket_connect("/api/v1/ws") as websocket:
        resp = websocket.receive_json()
        assert resp["type"] == "welcome"
        websocket.send_json({"type": "chat_message", "content": "test message"})
        while True:
            resp = websocket.receive_json()
            if resp["type"] == "chat_message":
                break
        assert resp["content"] == "test message"
    # Third connection should be rejected
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with test_client.websocket_connect("/api/v1/ws"):
            pass
    assert exc_info.value.code == status.WS_1008_POLICY_VIOLATION

@pytest.mark.skip(reason='Reference only; see async/test_websocket_rate_limit.py for actual rate limit enforcement tests.')
def test_connection_rate_limit(test_client, websocket_manager, rate_limiter, test_user, test_settings):
    websocket_manager.rate_limiter = rate_limiter
    token = create_access_token(settings=test_settings, data={"sub": str(test_user.id)})
    ws_path_with_token = f"/api/v1/ws?token={token}"
    for _ in range(2):
        with test_client.websocket_connect(ws_path_with_token) as websocket:
            websocket.send_json({"type": "chat_message", "content": "test"})
            while True:
                resp = websocket.receive_json()
                if resp["type"] == "chat_message":
                    break
            assert resp["content"] == "test"
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with test_client.websocket_connect(ws_path_with_token):
            pass
    assert exc_info.value.code == status.WS_1008_POLICY_VIOLATION

@pytest.mark.skip(reason='Reference only; see async/test_websocket_rate_limit.py for actual rate limit enforcement tests.')
def test_message_rate_limit(test_client, websocket_manager, rate_limiter, test_user, test_settings):
    websocket_manager.rate_limiter = rate_limiter
    token = create_access_token(settings=test_settings, data={"sub": str(test_user.id)})
    ws_path_with_token = f"/api/v1/ws?token={token}"
    with test_client.websocket_connect(ws_path_with_token) as websocket:
        for _ in range(9):
            websocket.send_json({"type": "chat_message", "content": "test message"})
            while True:
                resp = websocket.receive_json()
                if resp["type"] == "chat_message":
                    break
            assert resp["content"] == "test message"
        websocket.send_json({"type": "chat_message", "content": "test message"})
        with pytest.raises(WebSocketDisconnect) as exc_info:
            websocket.receive_json()
        assert exc_info.value.code == status.WS_1008_POLICY_VIOLATION

@pytest.mark.skip(reason='Reference only; see async/test_websocket_rate_limit.py for actual rate limit enforcement tests.')
def test_system_messages_not_rate_limited(test_client, websocket_manager, rate_limiter, test_user, test_settings):
    websocket_manager.rate_limiter = rate_limiter
    token = create_access_token(settings=test_settings, data={"sub": str(test_user.id)})
    ws_path_with_token = f"/api/v1/ws?token={token}"
    with test_client.websocket_connect(ws_path_with_token) as websocket:
        websocket.send_json({"type": "system", "content": "SYSTEM:test"})
        while True:
            resp = websocket.receive_json()
            if resp["type"] == "system":
                break
        assert resp["content"] == "SYSTEM:test"
        for _ in range(10):
            websocket.send_json({"type": "system", "content": "SYSTEM:test"})
            while True:
                resp = websocket.receive_json()
                if resp["type"] == "system":
                    break
            assert resp["content"] == "SYSTEM:test" 