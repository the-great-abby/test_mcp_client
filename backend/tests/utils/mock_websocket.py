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

    def debug_log(self, msg):
        if self.DEBUG_LOGGING:
            print(msg)
            logger.debug(msg)

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
        self._auto_pong = True  # Whether to automatically respond to pings
        self._message_handlers: Dict[str, Any] = {
            "ping": self._handle_ping,
            "chat_message": self._handle_chat_message,
            "typing": self._handle_typing,
            "stream_start": self._handle_stream_start,
            "stream": self._handle_stream,
            "stream_end": self._handle_stream_end
        }
        self._current_stream: Optional[MockStreamResponse] = None
        self._stream_lock = asyncio.Lock()
        self._stream_start_event = asyncio.Event()

    @property
    def application_state(self) -> WebSocketState:
        """Get the application state.

        Returns:
            Current WebSocket state
        """
        return self.client_state

    async def accept(self) -> None:
        """Accept the WebSocket connection."""
        if self.client_state == WebSocketState.CONNECTING:
            self.client_state = WebSocketState.CONNECTED

    async def close(self, code: int = status.WS_1000_NORMAL_CLOSURE, reason: str = None) -> None:
        """Close the WebSocket connection.

        Args:
            code: Close status code
            reason: Close reason
        """
        if self.client_state != WebSocketState.DISCONNECTED:
            self.client_state = WebSocketState.DISCONNECTED
            self.closed = True
            self.close_code = code
            self.close_reason = reason

            # Cancel receive task if running
            if self._receive_task and not self._receive_task.done():
                self._receive_task.cancel()
                try:
                    await self._receive_task
                except asyncio.CancelledError:
                    pass

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

    async def send_json(self, data: Dict[str, Any]) -> None:
        self.debug_log(f"[MockWebSocket] send_json called with data: {data} (id={id(data)})")
        if self.client_state != WebSocketState.CONNECTED:
            raise ConnectionClosed(
                Close(code=status.WS_1006_ABNORMAL_CLOSURE, reason="WebSocket not connected"),
                None
            )

        # Put message in send queue (messages sent by server to client)
        await self.send_queue.put(json.dumps(data))
        self.debug_log(f"[MockWebSocket] send_json after put: {data} (id={id(data)})")

        # Handle message based on type
        message_type = data.get("type")
        handler = self._message_handlers.get(message_type)
        if handler:
            await handler(data)

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
        if self.client_state != WebSocketState.CONNECTED:
            raise ConnectionClosed(
                Close(code=status.WS_1006_ABNORMAL_CLOSURE, reason="WebSocket not connected"),
                None
            )

        # Get message from send queue (messages sent by server to client)
        text = await self.send_queue.get()
        parsed = json.loads(text)
        self.debug_log(f"[MockWebSocket] receive_json parsed: {parsed}")
        return parsed

    def set_client_state(self, state: WebSocketState) -> None:
        """Set the client state.

        Args:
            state: New WebSocket state
        """
        self.client_state = state

    async def send_error(self, message: str, code: int = status.WS_1008_POLICY_VIOLATION, close: bool = True) -> None:
        """Send error message and optionally close connection.

        Args:
            message: Error message
            code: Error code
            close: Whether to close the connection after sending error
        """
        self.debug_log(f"[MockWebSocket] send_error called with message: {message} (id={id(message)})")
        try:
            # Always send a new error message dictionary object
            error_msg = {"type": "error", "content": str(message)}
            await self.send_json(error_msg)
            self.debug_log(f"[MockWebSocket] send_error after send_json: message={message} (id={id(message)})")
        finally:
            if close:
                await self.close(code=code, reason=message)

    async def mock_receive(self, data: Dict[str, Any]) -> None:
        """Mock receiving data from client.

        Args:
            data: Data to receive
        """
        if self.client_state != WebSocketState.CONNECTED:
            raise ConnectionClosed(
                Close(code=status.WS_1006_ABNORMAL_CLOSURE, reason="WebSocket not connected"),
                None
            )

        # Handle ping messages immediately with pong response
        if data.get("type") == "ping" and self._auto_pong:
            await self.send_json({
                "type": "pong",
                "timestamp": datetime.now(UTC).isoformat()
            })
            return

        # Dispatch to handler if exists
        message_type = data.get("type")
        handler = self._message_handlers.get(message_type)
        if handler:
            await handler(data)
        else:
            # Put message in receive queue if no handler
            await self.receive_queue.put(json.dumps(data))

    async def mock_send(self) -> Dict[str, Any]:
        text = await self.send_queue.get()
        self.debug_log(f"[MockWebSocket] mock_send got from send_queue: {text}")
        parsed = json.loads(text)
        self.debug_log(f"[MockWebSocket] mock_send parsed: {parsed}")
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

    async def _handle_chat_message(self, data: Dict[str, Any]) -> None:
        """Handle chat message.

        Args:
            data: Chat message data
        """
        # Echo back the message with the same type and content
        await self.mock_receive({
            "type": "chat_message",
            "content": data.get("content", ""),
            "metadata": data.get("metadata", {}),
            "timestamp": datetime.now(UTC).isoformat()
        })

    async def _handle_typing(self, data: Dict[str, Any]) -> None:
        """Handle typing indicator message.

        Args:
            data: Typing indicator message data
        """
        # Echo back the typing indicator with the same content
        await self.mock_receive({
            "type": "typing",
            "content": data.get("content", "true"),
            "metadata": data.get("metadata", {})
        })

    async def _handle_stream_start(self, data: Dict[str, Any]) -> None:
        self.debug_log(f"[MockWebSocket] _handle_stream_start called with data: {data}")
        content = data.get("content", "")
        async with self._stream_lock:
            if not content:
                self.debug_log("[MockWebSocket] _handle_stream_start: sending error 'Empty stream content'")
                await self.send_error("Empty stream content")
                return

            if self._current_stream is not None:
                self.debug_log("[MockWebSocket] _handle_stream_start: sending error 'Active stream already in progress'")
                # Do not close the connection for concurrent stream error
                await self.send_error("Active stream already in progress", close=False)
                return

            # Send stream start acknowledgment to receive queue (messages from server to client)
            await self.receive_queue.put(json.dumps({
                "type": "stream_start",
                "content": "",
                "metadata": data.get("metadata", {})
            }))
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
            async for message in self._current_stream:
                self.debug_log(f"[MockWebSocket] Streaming message: {message}")
                if self.client_state != WebSocketState.CONNECTED:
                    self.debug_log("[MockWebSocket] Client disconnected during stream.")
                    normal_completion = False
                    break

                # Send stream message to send queue (messages from server to client)
                self.debug_log(f"[MockWebSocket] Putting message on send_queue: {message}")
                await self.send_queue.put(json.dumps(message))
                await asyncio.sleep(0.05)  # Add delay between messages
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
                }))
            self._current_stream = None 

    async def wait_for_stream_start(self, timeout: float = 5.0):
        try:
            await asyncio.wait_for(self._stream_start_event.wait(), timeout)
        finally:
            self._stream_start_event.clear() 