"""Mock WebSocket implementation for testing."""
import json
import logging
from typing import Dict, Any, Optional, List, AsyncIterator
from starlette.websockets import WebSocketState
from websockets.exceptions import ConnectionClosed
from websockets.frames import Close
from fastapi import status
from datetime import datetime, UTC
import asyncio
import traceback
import os

logger = logging.getLogger(__name__)

class MockContentBlock:
    """Mock content block that matches Anthropic's format."""
    def __init__(self, text: str, block_type: str = "text"):
        self.type = block_type
        self.text = text

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "text": self.text
        }

class MockStreamResponse:
    """Mock stream response generator."""
    DEBUG_LOGGING = True  # Set to False to disable debug prints

    def __init__(self, content: str, chunk_size: int = 5):
        """Initialize mock stream response.

        Args:
            content: Content to stream
            chunk_size: Size of each chunk
        """
        self.content = content
        self.chunk_size = chunk_size
        self.position = 0

    def __aiter__(self):
        return self

    def debug_log(self, msg):
        if self.DEBUG_LOGGING:
            print(msg)
            logger.debug(msg)

    async def __anext__(self):
        """Get next chunk of content.

        Returns:
            Next chunk as a stream message

        Raises:
            StopAsyncIteration: When stream is complete
        """
        if self.position >= len(self.content):
            self.debug_log(f"[MockStreamResponse] End of stream at position {self.position}")
            raise StopAsyncIteration

        # Get next chunk
        end = min(self.position + self.chunk_size, len(self.content))
        chunk = self.content[self.position:end]
        self.position = end

        self.debug_log(f"[MockStreamResponse] Yielding chunk: '{chunk}' (position {self.position})")

        # Add small delay to simulate streaming
        await asyncio.sleep(0.05)

        # Create content block delta with proper structure
        content_block = MockContentBlock(text=chunk)
        return {
            "type": "stream",
            "content": {
                "content_block_delta": content_block.to_dict()
            },
            "metadata": {}
        }

class MockWebSocket:
    """Mock WebSocket implementation for testing."""
    DEBUG_LOGGING = True  # Set to False to disable debug prints
    DEBUG_STACK_TRACES = False  # Set to True to enable stack trace logging

    def debug_log(self, msg, stack_trace: bool = False):
        if self.DEBUG_LOGGING:
            logger.debug(msg)
            if stack_trace and self.DEBUG_STACK_TRACES:
                import traceback
                logger.debug('Stack trace:\n' + ''.join(traceback.format_stack()))

    def __init__(
        self,
        client_id: str,
        user_id: str,
        ip_address: str = "127.0.0.1",
        query_params: Optional[Dict[str, str]] = None
    ):
        """Initialize mock WebSocket.

        Args:
            client_id: Client ID
            user_id: User ID
            ip_address: IP address
            query_params: Optional query parameters
        """
        self.client_id = client_id
        self.user_id = user_id
        self.ip_address = ip_address
        self.query_params = query_params or {}
        self.client_state = WebSocketState.CONNECTING
        self.send_queue: asyncio.Queue[str] = asyncio.Queue()
        self.receive_queue: asyncio.Queue[str] = asyncio.Queue()
        self.closed = False
        self.close_code = None
        self.close_reason = None
        self.headers: Dict[str, str] = {
            "X-Client-ID": client_id,
            "X-User-ID": user_id,
            "X-Real-IP": ip_address
        }
        self._client = type('Client', (), {
            'host': ip_address,
            'port': 12345,
            'client': f"{ip_address}:12345"
        })
        self._receive_task: Optional[asyncio.Task] = None
        self._auto_pong = True  # Always enabled for test stability
        self._message_handlers: Dict[str, Any] = {
            "ping": self._handle_ping,
            "pong": self._handle_pong,
            "chat_message": self._handle_chat_message,
            "chat": self._handle_chat,
            "typing": self._handle_typing,
            "stream_start": self._handle_stream_start,
            "stream": self._handle_stream,
            "stream_end": self._handle_stream_end,
            "system": self._handle_system,
            "test": self._handle_test_message
        }
        self._current_stream: Optional[MockStreamResponse] = None
        self._stream_lock = asyncio.Lock()
        self._stream_start_event = asyncio.Event()
        self._stream_timestamps: List[float] = []  # For simple rate limiting
        self.max_streams_per_minute: int = 60  # Default, can be patched in tests
        self._message_timestamps: List[float] = []  # For message rate limiting
        self.max_messages_per_minute: int = 60  # Default, can be patched in tests
        self.max_messages_per_second: int = 10  # Default, can be patched in tests
        self.response_delay: float = 0.0  # Add configurable response delay
        self._last_stream_start_metadata: Dict[str, Any] = {}  # Added for stream interruption logic
        self.simulate_connect_error = (
            os.environ.get("MOCK_WS_CONNECT_ERROR", "0").lower() in ("1", "true", "yes")
        )
        self.debug_log(f"[MockWebSocket] __init__ called for client_id={client_id}, user_id={user_id}, simulate_connect_error={self.simulate_connect_error}")

    @property
    def application_state(self) -> WebSocketState:
        """Get the application state.

        Returns:
            Current WebSocket state
        """
        return self.client_state

    async def accept(self) -> None:
        """Accept the WebSocket connection."""
        self.debug_log(f"[MockWebSocket] accept called for client_id={self.client_id}, current state={self.client_state}")
        if self.simulate_connect_error:
            await self.send_error("Redis connection error", close=True)
            raise ConnectionClosed(
                Close(code=status.WS_1008_POLICY_VIOLATION, reason="Redis connection error"),
                None
            )
        if self.client_state == WebSocketState.CONNECTING:
            self.debug_log(f"[MockWebSocket] accept stack trace:", stack_trace=True)
            self.set_client_state(WebSocketState.CONNECTED, context="accept")
            self.debug_log(f"[MockWebSocket] accept after set_client_state: client_id={self.client_id}, new state={self.client_state}")

    async def close(self, code: int = status.WS_1000_NORMAL_CLOSURE, reason: str = None) -> None:
        """Close the WebSocket connection.

        Args:
            code: Close status code
            reason: Close reason
        """
        prev_state = self.client_state
        self.debug_log(f"[MockWebSocket] close ENTRY: client_id={self.client_id}, id={id(self)}, prev_state={prev_state}, current state={self.client_state}, code={code}, reason={reason}", stack_trace=True)
        if self.client_state != WebSocketState.DISCONNECTED:
            self.set_client_state(WebSocketState.DISCONNECTED, context="close")
            self.closed = True
            self.close_code = code
            self.close_reason = reason
            self.debug_log(f"[MockWebSocket] close after set_client_state: client_id={self.client_id}, new state={self.client_state}")
            # Cancel receive task if running
            if self._receive_task and not self._receive_task.done():
                self._receive_task.cancel()
        else:
            self.debug_log(f"[MockWebSocket] close called for client_id={self.client_id}, id={id(self)}, already DISCONNECTED")
        self.debug_log(f"[MockWebSocket] close EXIT: client_id={self.client_id}, client_state={self.client_state}, code={code}, reason={reason}")

    async def send_text(self, data: str) -> None:
        """Send text data.

        Args:
            data: Text data to send

        Raises:
            ConnectionClosed: If connection is closed
        """
        if self.client_state != WebSocketState.CONNECTED:
            raise ConnectionClosed(
                Close(code=status.WS_1006_ABNORMAL_CLOSURE, reason="WebSocket not connected"),
                None
            )
        await self.send_queue.put(data)

    def _validate_message(self, data: Dict[str, Any]) -> Optional[str]:
        """Validate message structure. Returns error string if invalid, else None."""
        message_type = data.get("type")
        if not message_type:
            return "Missing message type"
        if message_type in ("chat", "chat_message"):
            content = data.get("content")
            if not content:
                return "Missing message content"
            if isinstance(content, str) and len(content.encode("utf-8")) > 1024 * 1024:
                return "Message size exceeds limit"
        if message_type not in self._message_handlers:
            return f"Unknown message type: {message_type}"
        return None

    async def send_json(self, data: Dict[str, Any]) -> None:
        self.debug_log(f"[MockWebSocket] send_json ENTRY: data={data} (id={id(data)}), client_state={self.client_state}")
        if self.client_state != WebSocketState.CONNECTED:
            self.debug_log(f"[MockWebSocket] send_json ABORT: not connected, state={self.client_state}")
            raise ConnectionClosed(
                Close(code=status.WS_1006_ABNORMAL_CLOSURE, reason="WebSocket not connected"),
                None
            )
        # Do not dispatch error messages to handlers
        if data.get("type") == "error":
            try:
                await self.send_queue.put(json.dumps(data, allow_nan=False))
            except (TypeError, ValueError) as e:
                logger.error(f"[MockWebSocket] send_json: JSON serialization error for error message: {e}")
                raise ValueError(f"Invalid JSON in error message: {e}")
            self.debug_log(f"[MockWebSocket] send_json: Skipping handler dispatch for error message: {data}")
            return
        error = self._validate_message(data)
        if error:
            await self.send_error(error, close=False)
            return
        message_type = data["type"]
        handler = self._message_handlers[message_type]
        self.debug_log(f"[MockWebSocket] send_json: Before put to send_queue (id={id(self.send_queue)})")
        try:
            await self.send_queue.put(json.dumps(data, allow_nan=False))
        except (TypeError, ValueError) as e:
            logger.error(f"[MockWebSocket] send_json: JSON serialization error: {e}")
            raise ValueError(f"Invalid JSON in message: {e}")
        self.debug_log(f"[MockWebSocket] send_json after put: {data} (id={id(data)}) send_queue size={self.send_queue.qsize()}")
        self.debug_log(f"[MockWebSocket] send_json: Calling handler for type={message_type}")
        await handler(data)
        self.debug_log(f"[MockWebSocket] send_json EXIT: data={data} (id={id(data)}), client_state={self.client_state}")

    async def receive_text(self) -> str:
        """Receive text data.

        Returns:
            Received data
        """
        if self.client_state != WebSocketState.CONNECTED:
            raise ConnectionClosed(
                Close(code=status.WS_1006_ABNORMAL_CLOSURE, reason="WebSocket not connected"),
                None
            )

        try:
            # Create receive task if not exists
            if not self._receive_task or self._receive_task.done():
                self._receive_task = asyncio.create_task(self.receive_queue.get())

            # Wait for data
            return await self._receive_task

        except asyncio.CancelledError:
            # Only raise ConnectionClosed if we're actually closed
            if self.closed:
                raise ConnectionClosed(
                    Close(code=self.close_code or status.WS_1006_ABNORMAL_CLOSURE, reason=self.close_reason or "Operation cancelled"),
                    None
                )
            raise

    async def receive_json(self) -> Dict[str, Any]:
        self.debug_log(f"[MockWebSocket] receive_json ENTRY: client_state={self.client_state}")
        if self.client_state != WebSocketState.CONNECTED:
            self.debug_log(f"[MockWebSocket] receive_json ABORT: not connected, state={self.client_state}")
            raise ConnectionClosed(
                Close(code=status.WS_1006_ABNORMAL_CLOSURE, reason="WebSocket not connected"),
                None
            )
        self.debug_log(f"[MockWebSocket] receive_json: Before get from send_queue (id={id(self.send_queue)})")
        text = await self.send_queue.get()
        self.debug_log(f"[MockWebSocket] receive_json: Got text from send_queue: {text}")
        parsed = json.loads(text)
        self.debug_log(f"[MockWebSocket] receive_json parsed: {parsed}")
        self.debug_log(f"[MockWebSocket] receive_json EXIT: parsed={parsed}, client_state={self.client_state}")
        return parsed

    def set_client_state(self, new_state, context=""):
        prev_state = self.client_state
        self.client_state = new_state
        self.debug_log(f"[MockWebSocket] set_client_state called for client_id={self.client_id}, id={id(self)}, prev_state={prev_state}, new_state={new_state}, context={context}", stack_trace=True)
        if new_state == WebSocketState.CONNECTED:
            self.debug_log(f"[MockWebSocket] set_client_state CONNECTED stack trace (again):", stack_trace=True)
        if new_state == WebSocketState.DISCONNECTED:
            self.debug_log(f"[MockWebSocket] set_client_state DISCONNECTED stack trace (again):", stack_trace=True)

    async def send_error(self, message: str, code: int = status.WS_1008_POLICY_VIOLATION, close: bool = True) -> None:
        """Send error message and optionally close connection.

        Args:
            message: Error message
            code: Error code
            close: Whether to close the connection after sending error
        """
        self.debug_log(f"[MockWebSocket] send_error called with message: {message} (id={id(message)})")
        try:
            # Put error message directly on the send queue to avoid recursion
            error_msg = {"type": "error", "content": str(message)}
            await self.send_queue.put(json.dumps(error_msg, allow_nan=False))
            self.debug_log(f"[MockWebSocket] send_error after put: message={message} (id={id(message)})")
        finally:
            if close:
                await self.close(code=code, reason=message)

    async def mock_receive(self, data: Dict[str, Any]) -> None:
        self.debug_log(f"[MockWebSocket] mock_receive ENTRY: data={data}, client_state={self.client_state}")
        if self.client_state != WebSocketState.CONNECTED:
            self.debug_log(f"[MockWebSocket] mock_receive ABORT: not connected, state={self.client_state}")
            raise ConnectionClosed(
                Close(code=status.WS_1006_ABNORMAL_CLOSURE, reason="WebSocket not connected"),
                None
            )
        # Do not dispatch error messages to handlers
        if data.get("type") == "error":
            await self.send_queue.put(json.dumps(data, allow_nan=False))
            self.debug_log(f"[MockWebSocket] mock_receive: Skipping handler dispatch for error message: {data}")
            return
        if data.get("type") == "ping":
            await self.send_json({
                "type": "pong",
                "timestamp": datetime.now(UTC).isoformat()
            })
            self.debug_log(f"[MockWebSocket] mock_receive EXIT: handled ping, client_state={self.client_state}")
            return
        error = self._validate_message(data)
        if error:
            await self.send_error(error, close=False)
            return
        message_type = data["type"]
        handler = self._message_handlers[message_type]
        self.debug_log(f"[MockWebSocket] mock_receive: Calling handler for type={message_type}")
        await handler(data)
        self.debug_log(f"[MockWebSocket] mock_receive EXIT: data={data}, client_state={self.client_state}")

    async def mock_send(self) -> Dict[str, Any]:
        self.debug_log(f"[MockWebSocket] mock_send ENTRY: client_state={self.client_state}")
        text = await self.send_queue.get()
        self.debug_log(f"[MockWebSocket] mock_send got from send_queue: {text}")
        parsed = json.loads(text)
        self.debug_log(f"[MockWebSocket] mock_send parsed: {parsed}")
        self.debug_log(f"[MockWebSocket] mock_send EXIT: parsed={parsed}, client_state={self.client_state}")
        return parsed

    def get_header(self, key: str) -> Optional[str]:
        """Get header value.

        Args:
            key: Header key

        Returns:
            Header value if exists
        """
        return self.headers.get(key)

    def get_query_params(self) -> Dict[str, List[str]]:
        """Get query parameters.

        Returns:
            Query parameters
        """
        return {k: [v] for k, v in self.query_params.items()}

    def get_path_params(self) -> Dict[str, str]:
        """Get path parameters.

        Returns:
            Path parameters
        """
        return {}

    @property
    def client(self) -> Dict[str, Any]:
        """Get the client information.

        Returns:
            Client information dictionary
        """
        return self._client

    @client.setter
    def client(self, value: Dict[str, Any]) -> None:
        """Set the client information.

        Args:
            value: Client information dictionary
        """
        self._client = value

    def set_auto_pong(self, enabled: bool) -> None:
        """Enable or disable automatic pong responses.

        Args:
            enabled: Whether to automatically respond to pings
        """
        self._auto_pong = enabled

    async def _handle_ping(self, data: Dict[str, Any]) -> None:
        """Handle ping message.

        Args:
            data: Ping message data
        """
        if self._auto_pong:
            await self.send_json({
                "type": "pong",
                "timestamp": datetime.now(UTC).isoformat()
            })

    def _check_rate_limit(self, timestamps: List[float], max_per_minute: int, max_per_second: int) -> Optional[str]:
        """Generic rate limit checker. Returns error string if not allowed, else None."""
        now = asyncio.get_event_loop().time()
        # Clean up old timestamps
        timestamps[:] = [t for t in timestamps if now - t < 60]
        # Per-minute limit
        if len(timestamps) >= max_per_minute:
            return f"Rate limit exceeded ({max_per_minute} messages per minute)"
        # Per-second limit
        per_second = len([t for t in timestamps if now - t < 1])
        if per_second >= max_per_second:
            return f"Rate limit exceeded ({max_per_second} messages per second)"
        return None

    async def _rate_limit_check(self, message_type: str) -> Optional[str]:
        """Check if message is allowed by rate limits. Returns error string if not allowed."""
        if message_type == "system":
            return None  # System messages bypass rate limiting
        return self._check_rate_limit(self._message_timestamps, self.max_messages_per_minute, self.max_messages_per_second)

    async def _handle_chat_message(self, data: Dict[str, Any]) -> None:
        self.debug_log(f"[MockWebSocket] _handle_chat_message called with data: {data}")
        # Rate limit check
        error = await self._rate_limit_check("chat_message")
        if error:
            await self.send_error(error, close=False)
            return
        # Only echo if this is the original message (no '_echoed' marker)
        if not data.get("_echoed", False):
            now = asyncio.get_event_loop().time()
            self._message_timestamps.append(now)
            if self.response_delay > 0:
                await asyncio.sleep(self.response_delay)
            response = {
                "type": "chat_message",
                "content": data.get("content", ""),
                "metadata": data.get("metadata", {}),
                "timestamp": datetime.now(UTC).isoformat(),
                "_echoed": True  # Mark as echoed to prevent recursion
            }
            self.debug_log(f"[MockWebSocket] _handle_chat_message echoing: {response}")
            await self.send_queue.put(json.dumps(response, allow_nan=False))
        else:
            self.debug_log(f"[MockWebSocket] _handle_chat_message skipping echo to prevent recursion: {data}")

    async def _handle_chat(self, data: Dict[str, Any]) -> None:
        self.debug_log(f"[MockWebSocket] _handle_chat called with data: {data}")
        # Rate limit check
        error = await self._rate_limit_check("chat")
        if error:
            await self.send_error(error, close=False)
            return
        now = asyncio.get_event_loop().time()
        self._message_timestamps.append(now)
        if self.response_delay > 0:
            await asyncio.sleep(self.response_delay)
        # Echo back the message with the same type and content (matching real server)
        response = {
            "type": "chat",
            "content": data.get("content", ""),
            "user_id": data.get("user_id", self.user_id),
            "timestamp": datetime.now(UTC).isoformat(),
            "metadata": data.get("metadata", {})
        }
        self.debug_log(f"[MockWebSocket] _handle_chat echoing: {response}")
        await self.send_queue.put(json.dumps(response, allow_nan=False))

    async def _handle_typing(self, data: Dict[str, Any]) -> None:
        """Handle typing indicator message.

        Args:
            data: Typing indicator message data
        """
        # Echo back the typing indicator with the same content
        response = {
            "type": "typing",
            "content": data.get("content", "true"),
            "metadata": data.get("metadata", {})
        }
        self.debug_log(f"[MockWebSocket] _handle_typing echoing: {response}")
        await self.send_queue.put(json.dumps(response, allow_nan=False))

    async def _handle_stream_start(self, data: Dict[str, Any]) -> None:
        self.debug_log(f"[MockWebSocket] _handle_stream_start called with data: {data}")
        content = data.get("content", "")
        async with self._stream_lock:
            # Use consolidated rate limiting
            error = self._check_rate_limit(self._stream_timestamps, self.max_streams_per_minute, self.max_streams_per_minute)
            if error:
                self.debug_log("[MockWebSocket] Rate limit exceeded for stream_start")
                await self.send_error(error, close=False)
                return
            if not content:
                self.debug_log("[MockWebSocket] _handle_stream_start: sending error 'Empty stream content'")
                await self.send_error("Empty stream content")
                return

            if self._current_stream is not None:
                self.debug_log("[MockWebSocket] _handle_stream_start: sending error 'Active stream already in progress'")
                # Do not close the connection for concurrent stream error
                await self.send_error("Active stream already in progress", close=False)
                return

            # Append timestamp for rate limiting
            now = asyncio.get_event_loop().time()
            self._stream_timestamps.append(now)

            # Store the metadata for stream interruption logic
            self._last_stream_start_metadata = data.get("metadata", {})

            # Send stream start acknowledgment to receive queue (messages from server to client)
            await self.receive_queue.put(json.dumps({
                "type": "stream_start",
                "content": "",
                "metadata": data.get("metadata", {})
            }, allow_nan=False))
            self._stream_start_event.set()

            # Start streaming in background
            self._current_stream = MockStreamResponse(content)
            asyncio.create_task(self._process_stream())

    async def _handle_stream(self, data: Dict[str, Any]) -> None:
        """Handle stream message."""
        if not self._current_stream:
            await self.send_error("No active stream")
            return

    async def _handle_stream_end(self, data: Dict[str, Any]) -> None:
        """Handle stream end message."""
        self._current_stream = None

    async def _process_stream(self) -> None:
        """Process current stream and send messages."""
        if not self._current_stream:
            self.debug_log("[MockWebSocket] No current stream to process.")
            return

        self.debug_log(f"[MockWebSocket] Starting stream processing for client_id={self.client_id}")
        normal_completion = True
        try:
            # Check if we should interrupt the stream (set by test via metadata)
            interrupt_stream = False
            if hasattr(self, '_last_stream_start_metadata') and self._last_stream_start_metadata.get('interrupt_stream'):
                interrupt_stream = True
            if interrupt_stream:
                await self.send_error("Stream interrupted for test", close=False)
                normal_completion = False
                return
            async for message in self._current_stream:
                self.debug_log(f"[MockWebSocket] Streaming message: {message}")
                if self.client_state != WebSocketState.CONNECTED:
                    self.debug_log("[MockWebSocket] Client disconnected during stream.")
                    normal_completion = False
                    break
                await self.send_queue.put(json.dumps(message, allow_nan=False))
                await asyncio.sleep(0.05)
        except Exception as e:
            self.debug_log(f"[MockWebSocket] Error during stream: {e}")
            normal_completion = False
            # Send error message
            await self.send_error(str(e))
        finally:
            if normal_completion:
                self.debug_log("[MockWebSocket] Sending stream_end message.")
                await self.send_queue.put(json.dumps({
                    "type": "stream_end",
                    "content": "",
                    "metadata": {}
                }, allow_nan=False))
            self._current_stream = None 

    async def wait_for_stream_start(self, timeout: float = 5.0):
        try:
            await asyncio.wait_for(self._stream_start_event.wait(), timeout)
        finally:
            self._stream_start_event.clear() 

    def set_disconnected(self, context: str = ""):
        prev_state = self.client_state
        self.set_client_state(WebSocketState.DISCONNECTED, context=context)
        self.debug_log(f"[MockWebSocket] set_disconnected called for client_id={self.client_id}, id={id(self)}, prev_state={prev_state}, new_state={self.client_state}, context={context}") 

    async def _handle_system(self, data: Dict[str, Any]) -> None:
        self.debug_log(f"[MockWebSocket] _handle_system called with data: {data}")
        response = {
            "type": "system",
            "content": data.get("content", ""),
            "metadata": data.get("metadata", {}),
            "timestamp": datetime.now(UTC).isoformat()
        }
        self.debug_log(f"[MockWebSocket] _handle_system echoing: {response}")
        await self.send_queue.put(json.dumps(response, allow_nan=False))

    async def _handle_pong(self, data: Dict[str, Any]) -> None:
        self.debug_log(f"[MockWebSocket] _handle_pong called with data: {data}")
        # No-op: just ignore pong messages 

    async def _handle_test_message(self, data: Dict[str, Any]) -> None:
        self.debug_log(f"[MockWebSocket] _handle_test_message called with data: {data}")
        # Rate limit check
        error = await self._rate_limit_check("test")
        if error:
            await self.send_error(error, close=True)
            raise ConnectionClosed(
                Close(code=status.WS_1008_POLICY_VIOLATION, reason="Message rate limit exceeded"),
                None
            )
        now = asyncio.get_event_loop().time()
        self._message_timestamps.append(now)
        if self.response_delay > 0:
            await asyncio.sleep(self.response_delay)
        # Echo back the message with the same type and content
        response = {
            "type": "test",
            "content": data.get("content", ""),
            "user_id": data.get("user_id", self.user_id),
            "timestamp": datetime.now(UTC).isoformat(),
            "metadata": data.get("metadata", {})
        }
        self.debug_log(f"[MockWebSocket] _handle_test_message echoing: {response}")
        await self.send_queue.put(json.dumps(response, allow_nan=False)) 