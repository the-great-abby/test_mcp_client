import asyncio
import logging
from typing import Dict, Any, Optional, List, Tuple
from websockets.exceptions import ConnectionClosed
from websockets.frames import Close
from datetime import datetime, UTC
from fastapi import status
from starlette.websockets import WebSocketState
import uuid
import copy

from app.core.websocket import WebSocketManager
from app.core.websocket_rate_limiter import WebSocketRateLimiter
from tests.utils.mock_websocket import MockWebSocket

logger = logging.getLogger(__name__)

class WebSocketTestHelper:
    """Helper class for WebSocket testing."""
    
    def __init__(
        self,
        websocket_manager: WebSocketManager,
        rate_limiter: Optional[WebSocketRateLimiter] = None,
        test_user_id: str = "test_user",
        test_ip: str = "127.0.0.1",
        auth_token: Optional[str] = None,
        connect_timeout: float = 5.0,
        message_timeout: float = 5.0
    ):
        """Initialize WebSocket test helper.

        Args:
            websocket_manager: WebSocket manager instance
            rate_limiter: Optional rate limiter
            test_user_id: Test user ID
            test_ip: Test IP address
            auth_token: Optional auth token
            connect_timeout: Connection timeout in seconds
            message_timeout: Message timeout in seconds
        """
        self.websocket_manager = websocket_manager
        self.rate_limiter = rate_limiter
        self.test_user_id = test_user_id
        self.test_ip = test_ip
        self.auth_token = auth_token
        self.connect_timeout = connect_timeout
        self.message_timeout = message_timeout
        self.active_connections: Dict[str, MockWebSocket] = {}
        self.stream_messages: Dict[str, List[Dict[str, Any]]] = {}

    async def connect(
        self,
        client_id: Optional[str] = None,
        user_id: Optional[str] = None,
        auth_token: Optional[str] = None,
        connect_timeout: Optional[float] = None
    ) -> MockWebSocket:
        """Create and connect a mock WebSocket.

        Args:
            client_id: Optional client ID (generated if not provided)
            user_id: Optional user ID (uses test_user_id if not provided)
            auth_token: Optional auth token (overrides instance auth_token)
            connect_timeout: Optional connection timeout

        Returns:
            Connected MockWebSocket instance

        Raises:
            ConnectionClosed: If connection is rejected
            TimeoutError: If connection times out
            RuntimeError: If connection succeeds with missing client ID
        """
        user_id = user_id or self.test_user_id
        auth_token = auth_token or self.auth_token
        timeout = connect_timeout or self.connect_timeout

        # Create mock WebSocket
        websocket = MockWebSocket(
            client_id=client_id,  # Pass None directly to test missing client ID
            user_id=user_id,
            ip_address=self.test_ip,
            query_params={"token": auth_token} if auth_token else {}
        )

        try:
            # Connect with timeout
            async with asyncio.timeout(timeout):
                await self.websocket_manager.connect(
                    client_id=client_id,  # Pass None directly to test missing client ID
                    websocket=websocket,
                    user_id=user_id
                )

            # If we get here with a missing client ID, something is wrong
            if not client_id:
                raise RuntimeError("Connection succeeded with missing client ID")

            self.active_connections[client_id] = websocket
            return websocket

        except ConnectionClosed:
            # Expected for missing client ID
            raise
        except asyncio.TimeoutError:
            logger.error(f"Connection timeout for client {client_id}")
            raise
        except Exception as e:
            logger.error(f"Connection error for client {client_id}: {e}")
            raise

    async def disconnect(self, client_id: str) -> None:
        """Disconnect a WebSocket connection.

        Args:
            client_id: Client ID to disconnect
        """
        if client_id in self.active_connections:
            await self.websocket_manager.disconnect(client_id)
            del self.active_connections[client_id]
            if client_id in self.stream_messages:
                del self.stream_messages[client_id]

    async def send_json(
        self,
        data: Dict[str, Any],
        client_id: str,
        ignore_errors: bool = False,
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """Send JSON data and wait for response.

        Args:
            data: Data to send
            client_id: Client ID to send to
            ignore_errors: Whether to ignore errors in response
            timeout: Optional timeout override

        Returns:
            Response data
        """
        websocket = self.active_connections.get(client_id)
        if not websocket:
            raise ValueError(f"No active connection for client {client_id}")

        try:
            async with asyncio.timeout(timeout or self.message_timeout):
                await self.websocket_manager.send_message(client_id, data)
                response = await websocket.receive_json()

                if not ignore_errors and response.get("type") == "error":
                    raise ConnectionClosed(
                        Close(code=status.WS_1008_POLICY_VIOLATION, reason=response.get("content", "Unknown error")),
                        None
                    )

                return response

        except asyncio.TimeoutError:
            logger.error(f"Message timeout for client {client_id}")
            raise
        except Exception as e:
            if not ignore_errors:
                raise
            logger.warning(f"Error ignored for client {client_id}: {e}")
            return {"type": "error", "content": str(e)}

    async def wait_for_stream(
        self,
        initial_message: Dict[str, Any],
        client_id: str,
        ignore_errors: bool = False,
        timeout: Optional[float] = None
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Wait for a complete stream of messages.

        Args:
            initial_message: Message to start the stream
            client_id: Client ID
            ignore_errors: Whether to ignore errors
            timeout: Optional timeout override

        Returns:
            Tuple of (stream messages, final message)
        """
        print(f"[wait_for_stream] Called with initial_message: {initial_message}, client_id: {client_id}")
        websocket = self.active_connections.get(client_id)
        if not websocket:
            raise ValueError(f"No active connection for client {client_id}")

        stream_messages = []
        try:
            async with asyncio.timeout(timeout or self.message_timeout):
                # Send initial message
                await self.websocket_manager.send_message(client_id, initial_message)

                while True:
                    response = await websocket.mock_send()
                    print(f"[wait_for_stream] Received message: {response} (id={id(response)})")
                    await asyncio.sleep(0)  # Yield to event loop

                    # If error message with non-empty content, return it immediately
                    if response.get("type") == "error":
                        print(f"[wait_for_stream] About to check error content: {response.get('content')} (id={id(response)})")
                        if response.get("content"):
                            print(f"[wait_for_stream] Returning due to error: {response} (id={id(response)})")
                            return stream_messages, copy.deepcopy(response)
                        else:
                            print(f"[wait_for_stream] Skipping error with empty content: {response} (id={id(response)})")
                            continue

                    if response.get("type") == "stream":
                        stream_messages.append(response)
                    elif response.get("type") == "stream_end":
                        print(f"[wait_for_stream] Returning stream_messages: {stream_messages}, final_message: {response} (id={id(response)})")
                        return stream_messages, copy.deepcopy(response)
        except Exception as e:
            if not ignore_errors:
                raise
            print(f"[wait_for_stream] Exception ignored: {e}")
            return stream_messages, {"type": "error", "content": str(e)}

    def get_connection_state(self, client_id: str) -> WebSocketState:
        """Get the connection state for a client.

        Args:
            client_id: Client ID

        Returns:
            Current WebSocket state
        """
        websocket = self.active_connections.get(client_id)
        if not websocket:
            return WebSocketState.DISCONNECTED
        return websocket.client_state

    async def cleanup(self) -> None:
        """Clean up all test connections."""
        for client_id in list(self.active_connections.keys()):
            await self.disconnect(client_id)
        self.active_connections.clear()
        self.stream_messages.clear()

    def get_active_connections(self) -> List[str]:
        """Get list of active connection IDs.

        Returns:
            List of client IDs
        """
        return list(self.active_connections.keys())

    def get_connection_count(self) -> int:
        """Get count of active connections.

        Returns:
            Number of active connections
        """
        return len(self.active_connections)

    async def wait_for_state(
        self,
        client_id: str,
        expected_state: WebSocketState,
        timeout: Optional[float] = None
    ) -> bool:
        """Wait for a client to reach an expected state.

        Args:
            client_id: Client ID to check
            expected_state: Expected WebSocket state
            timeout: Optional timeout override

        Returns:
            True if state reached, False if timeout
        """
        timeout = timeout or self.connect_timeout
        start_time = datetime.now(UTC)

        while (datetime.now(UTC) - start_time).total_seconds() < timeout:
            if self.get_connection_state(client_id) == expected_state:
                return True
            await asyncio.sleep(0.1)

        return False

    async def wait_for_disconnect(
        self,
        client_id: str,
        timeout: Optional[float] = None
    ) -> bool:
        """Wait for a client to disconnect.

        Args:
            client_id: Client ID to check
            timeout: Optional timeout override

        Returns:
            True if disconnected, False if timeout
        """
        return await self.wait_for_state(
            client_id=client_id,
            expected_state=WebSocketState.DISCONNECTED,
            timeout=timeout
        )

    async def send_message(
        self,
        client_id: str,
        message: Dict[str, Any]
    ) -> None:
        """Send a message through a test WebSocket client.

        Args:
            client_id: Client ID
            message: Message to send
        """
        if client_id not in self.active_connections:
            raise ValueError(f"Client {client_id} not connected")

        websocket = self.active_connections[client_id]
        await websocket.send_json(message)

    async def receive_message(
        self,
        client_id: str,
        timeout: float = 5.0
    ) -> Dict[str, Any]:
        """Receive a message from a test WebSocket client.

        Args:
            client_id: Client ID
            timeout: Timeout in seconds

        Returns:
            Received message
        """
        if client_id not in self.active_connections:
            raise ValueError(f"Client {client_id} not connected")

        websocket = self.active_connections[client_id]
        try:
            async with asyncio.timeout(timeout):
                return await websocket.receive_json()
        except asyncio.TimeoutError:
            logger.error(f"Timeout waiting for message from {client_id}")
            raise

    async def send_and_receive(
        self,
        client_id: str,
        message: Dict[str, Any],
        timeout: float = 5.0
    ) -> Dict[str, Any]:
        """Send a message and wait for response.

        Args:
            client_id: Client ID
            message: Message to send
            timeout: Timeout in seconds

        Returns:
            Response message
        """
        await self.send_message(client_id, message)
        return await self.receive_message(client_id, timeout)

    async def wait_for_message(
        self,
        client_id: str,
        message_type: str,
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """Wait for a specific message type.

        Args:
            client_id: Client ID
            message_type: Expected message type
            timeout: Optional timeout override

        Returns:
            Message of the expected type
        """
        websocket = self.active_connections.get(client_id)
        if not websocket:
            raise ValueError(f"No active connection for client {client_id}")

        try:
            async with asyncio.timeout(timeout or self.message_timeout):
                while True:
                    response = await websocket.receive_json()
                    if response.get("type") == message_type:
                        return response
                    elif response.get("type") == "error":
                        raise ConnectionClosed(
                            Close(code=status.WS_1008_POLICY_VIOLATION, reason=response.get("content", "Unknown error")),
                            None
                        )

        except asyncio.TimeoutError:
            logger.error(f"Timeout waiting for message type {message_type}")
            raise