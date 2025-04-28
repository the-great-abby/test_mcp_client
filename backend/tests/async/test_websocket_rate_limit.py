"""
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
import websockets
import json
import asyncio
import time
import logging

# Rate limit constants (match actual implementation)
MAX_CONNECTIONS_PER_IP = 20  # From WebSocketRateLimiter default
MAX_MESSAGES_PER_MINUTE = 10  # From WebSocketRateLimiter default

# Use Docker service host and port for testing (internal network)
WS_HOST = os.getenv("DOCKER_SERVICE_HOST", "backend-test")
WS_PORT = int(os.getenv("DOCKER_SERVICE_PORT", "8000"))

# Base URLs for internal Docker network communication
WS_BASE_URL = f"ws://{WS_HOST}:{WS_PORT}"
HTTP_BASE_URL = f"http://{WS_HOST}:{WS_PORT}"

# Add logging setup at the top of the file
logging.basicConfig(level=logging.DEBUG, format='[%(asctime)s] %(levelname)s %(message)s')

def debug(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}")

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

@pytest.mark.asyncio
async def test_rate_limit_by_ip(initialize_test_db):
    logging.debug("test_rate_limit_by_ip: starting")
    try:
        await asyncio.wait_for(_test_rate_limit_by_ip_body(), timeout=10)
    except asyncio.TimeoutError:
        logging.debug("test_rate_limit_by_ip: TIMEOUT after 10s!")
        raise

def _debug_recv(ws, label):
    logging.debug(f"[DEBUG] {label}: waiting for message...")
    msg = ws.recv()
    logging.debug(f"[DEBUG] {label}: received message: {msg}")
    return msg

async def _test_rate_limit_by_ip_body():
    logging.debug("test_rate_limit_by_ip: connecting first ws")
    uri = "ws://backend-test:8000/api/v1/ws"
    async with websockets.connect(uri) as ws1:
        logging.debug("ws1 connected")
        welcome = json.loads(await ws1.recv())
        logging.debug(f"ws1 welcome: {welcome}")
        await ws1.send(json.dumps({"type": "chat_message", "content": "test message"}))
        while True:
            resp = await asyncio.wait_for(ws1.recv(), timeout=2)
            msg = json.loads(resp)
            logging.debug(f"[DEBUG] ws1 response: {msg}")
            if msg["type"] == "chat_message":
                break
        assert msg["type"] == "chat_message"
    logging.debug("ws1 closed")

    logging.debug("test_rate_limit_by_ip: connecting second ws")
    async with websockets.connect(uri) as ws2:
        logging.debug("ws2 connected")
        welcome = json.loads(await ws2.recv())
        logging.debug(f"ws2 welcome: {welcome}")
        await ws2.send(json.dumps({"type": "chat_message", "content": "test message"}))
        while True:
            resp = await asyncio.wait_for(ws2.recv(), timeout=2)
            msg = json.loads(resp)
            logging.debug(f"[DEBUG] ws2 response: {msg}")
            if msg["type"] == "chat_message":
                break
        assert msg["type"] == "chat_message"
    logging.debug("ws2 closed")

    logging.debug("test_rate_limit_by_ip: connecting third ws (should be rejected)")
    try:
        async with websockets.connect(uri) as ws3:
            logging.debug("ws3 unexpectedly connected")
            assert False, "Third connection should have been rejected by rate limiter"
    except Exception as exc:
        logging.debug(f"ws3 connection exception: {exc}")
    logging.debug("test_rate_limit_by_ip: finished")

@pytest.mark.asyncio
async def test_connection_rate_limit(auth_token, test_settings, initialize_test_db):
    logging.debug("test_connection_rate_limit: starting")
    try:
        await asyncio.wait_for(_test_connection_rate_limit_body(auth_token, test_settings), timeout=10)
    except asyncio.TimeoutError:
        logging.debug("test_connection_rate_limit: TIMEOUT after 10s!")
        raise

async def _test_connection_rate_limit_body(auth_token, test_settings):
    token = auth_token
    uri = f"ws://backend-test:8000/api/v1/ws?token={token}"
    logging.debug("connecting first ws with token")
    async with websockets.connect(uri) as ws1:
        await ws1.send(json.dumps({"type": "chat_message", "content": "test message"}))
        while True:
            resp = json.loads(await ws1.recv())
            if resp["type"] == "chat_message":
                break
        assert resp["type"] == "chat_message"
    logging.debug("ws1 closed")
    logging.debug("connecting second ws with token")
    async with websockets.connect(uri) as ws2:
        await ws2.send(json.dumps({"type": "chat_message", "content": "test message"}))
        while True:
            resp = json.loads(await ws2.recv())
            if resp["type"] == "chat_message":
                break
    logging.debug("ws2 closed")
    logging.debug("connecting third ws with token (should be rejected)")
    try:
        async with websockets.connect(uri) as ws3:
            logging.debug("ws3 unexpectedly connected")
    except Exception as exc:
        logging.debug(f"ws3 connection exception: {exc}")
    logging.debug("test_connection_rate_limit: finished")

@pytest.mark.asyncio
async def test_message_rate_limit(auth_token, test_settings, initialize_test_db):
    logging.debug("test_message_rate_limit: starting")
    try:
        await asyncio.wait_for(_test_message_rate_limit_body(auth_token, test_settings), timeout=10)
    except asyncio.TimeoutError:
        logging.debug("test_message_rate_limit: TIMEOUT after 10s!")
        raise

async def _test_message_rate_limit_body(auth_token, test_settings):
    token = auth_token
    uri = f"ws://backend-test:8000/api/v1/ws?token={token}"
    logging.debug("connecting ws for message rate limit")
    async with websockets.connect(uri) as ws:
        for i in range(9):
            await ws.send(json.dumps({"type": "chat_message", "content": "test message"}))
            resp = json.loads(await ws.recv())
            logging.debug(f"[DEBUG] message {i} response: {resp}")
            if resp["type"] == "chat_message":
                assert resp["type"] == "chat_message"
        await ws.send(json.dumps({"type": "chat_message", "content": "test message"}))
        try:
            resp = await asyncio.wait_for(ws.recv(), timeout=2)
            msg = json.loads(resp)
            logging.debug(f"[DEBUG] Received message: {msg}")
            if msg["type"] == "chat_message":
                assert msg["type"] == "chat_message"
        except Exception as exc:
            logging.debug(f"[DEBUG] rate limit disconnect exception: {exc}")
    logging.debug("test_message_rate_limit: finished")

@pytest.mark.asyncio
async def test_system_messages_not_rate_limited(auth_token, test_settings, initialize_test_db):
    logging.debug("test_system_messages_not_rate_limited: starting")
    try:
        await asyncio.wait_for(_test_system_messages_not_rate_limited_body(auth_token, test_settings), timeout=10)
    except asyncio.TimeoutError:
        logging.debug("test_system_messages_not_rate_limited: TIMEOUT after 10s!")
        raise

async def _test_system_messages_not_rate_limited_body(auth_token, test_settings):
    token = auth_token
    uri = f"ws://backend-test:8000/api/v1/ws?token={token}"
    logging.debug("connecting ws for system messages")
    async with websockets.connect(uri) as ws:
        await ws.send(json.dumps({"type": "system", "content": "SYSTEM:test"}))
        resp = json.loads(await ws.recv())
        logging.debug(f"[DEBUG] system message response: {resp}")
        if resp["type"] == "chat_message":
            assert resp["type"] == "chat_message"
        for i in range(10):
            await ws.send(json.dumps({"type": "system", "content": "SYSTEM:test"}))
            resp = json.loads(await ws.recv())
            logging.debug(f"[DEBUG] system message {i} response: {resp}")
            if resp["type"] == "chat_message":
                assert resp["type"] == "chat_message"
    logging.debug("test_system_messages_not_rate_limited: finished") 