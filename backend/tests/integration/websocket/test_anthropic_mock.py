"""Integration tests for Anthropic-style WebSocket streaming."""
import pytest
import uuid
import asyncio
from datetime import datetime, UTC
from starlette.websockets import WebSocketState
from websockets.exceptions import ConnectionClosed
from fastapi import status
from typing import List, Dict, Any
import logging

from app.core.websocket import WebSocketManager
from app.core.websocket_rate_limiter import WebSocketRateLimiter
from app.models.user import User
from tests.utils.websocket_test_helper import WebSocketTestHelper
from tests.utils.mock_websocket import MockWebSocket

# Test Configuration
TEST_USER_ID = "test_user_123"
TEST_IP = "127.0.0.1"
TEST_CONTENT = "This is a test message that will be streamed in chunks."

logging.basicConfig(level=logging.DEBUG)

@pytest.mark.mock_service
class TestAnthropicStreamingMock:
    """Test suite for Anthropic-style streaming functionality."""

    @pytest.mark.integration
    async def test_stream_content_blocks(self, ws_helper: WebSocketTestHelper):
        """Test streaming with content blocks."""
        print(f"[DEBUG] ws_helper type: {type(ws_helper)}, value: {ws_helper}")
        client_id = str(uuid.uuid4())
        ws = await ws_helper.connect(client_id=client_id)
        assert ws.client_state == WebSocketState.CONNECTED

        # Start stream
        stream_messages, final_message = await ws_helper.wait_for_stream(
            initial_message={
                "type": "stream_start",
                "content": TEST_CONTENT,
                "metadata": {}
            },
            client_id=client_id,
            ignore_errors=True,
            timeout=10.0  # Increased timeout for async streaming
        )

        # Verify stream messages
        assert len(stream_messages) > 0, "Should receive multiple stream messages"
        for msg in stream_messages:
            assert msg["type"] == "stream"
            assert "content_block_delta" in msg["content"]
            assert msg["content"]["content_block_delta"]["type"] == "text"
            assert isinstance(msg["content"]["content_block_delta"]["text"], str)

        # Verify final message
        assert final_message["type"] == "stream_end"

        await ws_helper.disconnect(client_id)

    @pytest.mark.integration
    async def test_stream_interruption_recovery(self, ws_helper: WebSocketTestHelper):
        """Test recovery from stream interruption."""
        client_id = str(uuid.uuid4())
        ws = await ws_helper.connect(client_id=client_id)
        assert ws.client_state == WebSocketState.CONNECTED

        # Start stream
        stream_future = asyncio.create_task(
            ws_helper.wait_for_stream(
                initial_message={
                    "type": "stream_start",
                    "content": TEST_CONTENT,
                    "metadata": {}
                },
                client_id=client_id,
                ignore_errors=True
            )
        )

        # Wait briefly then interrupt
        await asyncio.sleep(0.1)
        await ws_helper.disconnect(client_id)

        # Reconnect
        ws = await ws_helper.connect(client_id=client_id)
        assert ws.client_state == WebSocketState.CONNECTED

        # Start new stream
        new_stream_messages, final_message = await ws_helper.wait_for_stream(
            initial_message={
                "type": "stream_start",
                "content": "New stream after interruption",
                "metadata": {}
            },
            client_id=client_id,
            ignore_errors=True
        )

        # Verify new stream works
        assert len(new_stream_messages) > 0
        assert final_message["type"] == "stream_end"

        await ws_helper.disconnect(client_id)

    @pytest.mark.integration
    async def test_concurrent_streams(self, ws_helper: WebSocketTestHelper):
        """Test handling of concurrent stream attempts."""
        client_id = str(uuid.uuid4())
        ws = await ws_helper.connect(client_id=client_id)
        assert ws.client_state == WebSocketState.CONNECTED

        # Start first stream
        print("[test] Starting first stream")
        first_stream_future = asyncio.create_task(
            ws_helper.wait_for_stream(
                initial_message={
                    "type": "stream_start",
                    "content": "First stream",
                    "metadata": {}
                },
                client_id=client_id,
                ignore_errors=True
            )
        )

        # Wait for the first stream to be acknowledged before starting the second
        await ws.wait_for_stream_start()

        # Try to start second stream immediately
        print("[test] Starting second stream (should error)")
        print(f"[test] About to call wait_for_stream for second stream")
        second_stream_messages, second_final_message = await ws_helper.wait_for_stream(
            initial_message={
                "type": "stream_start",
                "content": "Second stream",
                "metadata": {}
            },
            client_id=client_id,
            ignore_errors=True
        )
        print(f"[test] After wait_for_stream, second_stream_messages: {second_stream_messages}")
        print(f"[test] After wait_for_stream, second_final_message: {second_final_message}")
        print(f"[test] Type of second_final_message['content']: {type(second_final_message['content'])}")
        print(f"[test] Value of second_final_message['content']: {repr(second_final_message['content'])}")

        # Wait for first stream to complete before assertions
        print("[test] Waiting for first stream to complete (before assertions)")
        first_stream_messages, first_final_message = await first_stream_future
        print(f"[test] First stream messages: {first_stream_messages}")
        print(f"[test] First stream final message: {first_final_message}")
        assert len(first_stream_messages) > 0
        assert first_final_message["type"] == "stream_end"

        # Second stream should fail
        print(f"[test] Before assertion: second_final_message['content']: {repr(second_final_message['content'])}")
        assert not second_stream_messages
        assert second_final_message["type"] == "error"
        print(f"[test] Before 'active stream' assertion: {repr(second_final_message['content'])}")
        assert "active stream" in second_final_message["content"].lower()

        await ws_helper.disconnect(client_id)

    @pytest.mark.integration
    async def test_stream_content_validation(self, ws_helper: WebSocketTestHelper):
        """Test content validation in streams."""
        # Test empty content with a fresh client
        empty_client_id = str(uuid.uuid4())
        ws_empty = await ws_helper.connect(client_id=empty_client_id)
        assert ws_empty.client_state == WebSocketState.CONNECTED

        empty_messages, empty_final = await ws_helper.wait_for_stream(
            initial_message={
                "type": "stream_start",
                "content": "",
                "metadata": {}
            },
            client_id=empty_client_id,
            ignore_errors=True
        )
        print(f"[DEBUG] Empty content: messages={empty_messages}, final={empty_final}")
        assert not empty_messages
        assert empty_final["type"] == "error"
        assert "empty" in empty_final["content"].lower()
        await ws_helper.disconnect(empty_client_id)

        # Test very long content with a new fresh client
        long_client_id = str(uuid.uuid4())
        ws_long = await ws_helper.connect(client_id=long_client_id)
        assert ws_long.client_state == WebSocketState.CONNECTED

        # Use a smaller content size to avoid rate limits in test
        long_content = "x" * 200  # 20 chunks of 10 chars
        long_messages, long_final = await ws_helper.wait_for_stream(
            initial_message={
                "type": "stream_start",
                "content": long_content,
                "metadata": {}
            },
            client_id=long_client_id,
            ignore_errors=True
        )
        logging.error(f"[ASSERT] Long content: num_messages={len(long_messages)}, final={long_final}")
        assert long_final["type"] != "error" or long_final["content"], f"Error content: {long_final['content']}"
        assert len(long_messages) > 10  # Should be split into many chunks, but below rate limit
        await ws_helper.disconnect(long_client_id)

    @pytest.mark.integration
    async def test_stream_rate_limiting(self, ws_helper: WebSocketTestHelper):
        """Test rate limiting for streams."""
        client_id = str(uuid.uuid4())
        ws = await ws_helper.connect(client_id=client_id)
        assert ws.client_state == WebSocketState.CONNECTED

        # Patch the rate limiter to a low value for this test (on the mock websocket)
        orig_limit = ws.max_streams_per_minute
        ws.max_streams_per_minute = 3

        try:
            # Send three streams, all should succeed
            for i in range(3):
                messages, final = await ws_helper.wait_for_stream(
                    initial_message={
                        "type": "stream_start",
                        "content": f"Stream {i}",
                        "metadata": {}
                    },
                    client_id=client_id
                )
                assert final["type"] == "stream_end"
                assert not (final["type"] == "error")
                assert messages  # Should have stream messages

            # Fourth stream should trigger rate limit
            rate_limit_messages, rate_limit_final = await ws_helper.wait_for_stream(
                initial_message={
                    "type": "stream_start",
                    "content": "Rate limit test",
                    "metadata": {}
                },
                client_id=client_id,
                ignore_errors=True
            )
            print(f"[DEBUG] rate_limit_final: type={rate_limit_final.get('type')}, content={rate_limit_final.get('content')}, num_messages={len(rate_limit_messages)}")
            assert rate_limit_final["type"] == "error"
            assert "Rate limit exceeded" in rate_limit_final["content"]
            assert not rate_limit_messages  # Should not have stream messages
        finally:
            ws.max_streams_per_minute = orig_limit

        await ws_helper.disconnect(client_id) 