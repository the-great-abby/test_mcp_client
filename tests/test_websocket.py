import pytest
import json
import time
import logging
import asyncio
from websockets.client import connect as ws_connect
import os

logger = logging.getLogger(__name__)

DOCKER_SERVICE_HOST = os.getenv("DOCKER_SERVICE_HOST", "backend-test")
DOCKER_SERVICE_PORT = os.getenv("DOCKER_SERVICE_PORT", "8000")

HTTP_BASE_URL = f"http://{DOCKER_SERVICE_HOST}:{DOCKER_SERVICE_PORT}"
WS_BASE_URL = f"ws://{DOCKER_SERVICE_HOST}:{DOCKER_SERVICE_PORT}"

# Health check URL for REST endpoint
HEALTH_CHECK_URL = f"{HTTP_BASE_URL}/api/v1/health"

@pytest.mark.asyncio
async def test_message_sending(test_client, auth_token):
    """Test sending and receiving messages with proper message format."""
    logger.info("Testing message sending and receiving")
    
    ws_url = f"{test_client}/api/v1/ws?token={auth_token}"
    
    async with ws_connect(ws_url) as ws:
        # Store all received messages
        received_messages = []
        
        # Wait for welcome message
        welcome = await ws.recv()
        welcome_data = json.loads(welcome)
        received_messages.append(welcome_data)
        assert welcome_data["type"] == "welcome"
        client_id = welcome_data["metadata"]["client_id"]
        
        # Skip history message if present
        history = await ws.recv()
        history_data = json.loads(history)
        received_messages.append(history_data)
        assert history_data["type"] == "history"
        
        # Send a test message with proper format
        test_message = {
            "type": "message",
            "content": "Hello, World!",
            "metadata": {
                "client_id": client_id,
                "timestamp": time.time()
            }
        }
        
        logger.debug(f"Sending message: {test_message}")
        await ws.send(json.dumps(test_message))
        
        # Keep receiving messages until we get our chat message response or timeout
        try:
            async with asyncio.timeout(5.0):  # 5 second timeout
                while True:
                    response = await ws.recv()
                    data = json.loads(response)
                    received_messages.append(data)
                    logger.debug(f"Received message: {data}")
                    
                    # Add detailed logging
                    logger.info(f"Received response data: {json.dumps(data, indent=2)}")
                    logger.info(f"Expected type: 'chat_message', got type: '{data.get('type')}'")
                    if data.get('type') == 'error':
                        logger.info(f"Error content: {data.get('content')}")
                        logger.info(f"Error metadata: {data.get('metadata')}")

                    assert data["type"] == "chat_message"
                    
                    if data["type"] == "chat_message" and data["content"] == test_message["content"]:
                        # Found our response
                        assert "client_id" in data["metadata"], "Missing client_id in response metadata"
                        logger.info("Message exchange successful")
                        break
                    
                    # Avoid infinite loop
                    if len(received_messages) > 10:
                        logger.error(f"Message sequence: {[msg.get('type') for msg in received_messages]}")
                        raise AssertionError("Did not receive expected chat message response after 10 messages")
        except asyncio.TimeoutError:
            logger.error(f"Test timed out. Received messages: {[msg.get('type') for msg in received_messages]}")
            raise AssertionError("Test timed out waiting for chat message response") 