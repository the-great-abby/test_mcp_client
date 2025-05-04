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
import os

from app.core.websocket import WebSocketManager
from app.core.websocket_rate_limiter import WebSocketRateLimiter
from tests.utils.mock_websocket import MockWebSocket
from tests.utils.real_websocket_client import RealWebSocketClient

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
        message_timeout: float = 5.0,
        mock_mode: bool = False,
        ws_token_query: bool = False
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
            mock_mode: Whether to use the mock WebSocket (default False)
            ws_token_query: Whether to send token as query param (default False)
        """
        self.websocket_manager = websocket_manager
        self.rate_limiter = rate_limiter
        self.test_user_id = test_user_id
        self.test_ip = test_ip
        self.auth_token = auth_token
        self.connect_timeout = connect_timeout
        self.message_timeout = message_timeout
        self.mock_mode = mock_mode
        self.ws_token_query = ws_token_query
        print(f"[DEBUG][WebSocketTestHelper.__init__] mock_mode: {mock_mode} ws_token_query: {ws_token_query}")
        self.active_connections: Dict[str, MockWebSocket] = {}
        self.stream_messages: Dict[str, List[Dict[str, Any]]] = {}

    async def connect_and_catch(
        self,
        client_id: Optional[str] = None,
        user_id: Optional[str] = None,
        auth_token: Optional[str] = None,
        token: Optional[str] = None,
        connect_timeout: Optional[float] = None,
        request=None
    ):
        """Create and connect a mock or real WebSocket, returning (ws, exc)."""
        print(f"[DEBUG][WebSocketTestHelper.connect_and_catch] called. Using class: {self.__class__.__name__}")
        print(f"[DEBUG][WebSocketTestHelper.connect_and_catch] self.mock_mode: {self.mock_mode}")
        user_id = user_id or self.test_user_id
        auth_token = token or auth_token or self.auth_token
        timeout = connect_timeout or self.connect_timeout
        ws = None
        exc = None
        ws_token_query = self.ws_token_query
        if request is not None and hasattr(request, 'config') and hasattr(request.config, 'getoption'):
            ws_token_query = request.config.getoption('ws_token_query', False)
        if self.mock_mode:
            print(f"[DEBUG][WebSocketTestHelper.connect_and_catch] Instantiating MockWebSocket for client_id={client_id}")
            ws = MockWebSocket(
                client_id=client_id,
                user_id=user_id,
                ip_address=self.test_ip,
                query_params={"token": auth_token} if auth_token and ws_token_query else {}
            )
            logger.debug(f"[WebSocketTestHelper] After MockWebSocket __init__: client_id={client_id} state={ws.client_state}")
            try:
                print(f"[DEBUG][WebSocketTestHelper.connect_and_catch] About to call websocket_manager.connect for client_id={client_id}")
                async with asyncio.timeout(timeout):
                    await self.websocket_manager.connect(
                        client_id=client_id,
                        websocket=ws,
                        user_id=user_id
                    )
                print(f"[DEBUG][WebSocketTestHelper.connect_and_catch] After websocket_manager.connect for client_id={client_id}")
                if not client_id:
                    raise RuntimeError("Connection succeeded with missing client ID")
                self.add_connection(client_id, ws)
                logger.debug(f"[WebSocketTestHelper] After websocket_manager.connect: client_id={client_id} state={ws.client_state}")
                logger.debug(f"[WebSocketTestHelper] After add_connection: client_id={client_id} state={ws.client_state}")
                self.debug_active_connections()
                if os.environ.get("ENVIRONMENT") == "test":
                    await self.send_message(client_id, {"type": "ping"})
                    pong = await self.receive_message(client_id)
                    logger.debug(f"[WebSocketTestHelper] Received pong after connect: {pong}")
            except Exception as e:
                exc = e
        else:
            print(f"[DEBUG][WebSocketTestHelper.connect_and_catch] Instantiating RealWebSocketClient for client_id={client_id}")
            ws_uri = os.getenv("TEST_WS_URI", "ws://backend-test:8000/ws")
            ws_token = auth_token or os.getenv("TEST_USER_TOKEN")
            print(f"[DEBUG][WebSocketTestHelper.connect_and_catch] Connecting to URL: {ws_uri}?token={ws_token}&client_id={client_id}")
            ws = RealWebSocketClient(uri=ws_uri, token=ws_token, debug=True, ws_token_query=ws_token_query)
            try:
                await ws.connect()
            except Exception as e:
                exc = e
        print(f"[DEBUG][WebSocketTestHelper.connect_and_catch] ws instance type: {type(ws)} exc: {exc}")
        return ws, exc

    async def connect(
        self,
        client_id: Optional[str] = None,
        user_id: Optional[str] = None,
        auth_token: Optional[str] = None,
        token: Optional[str] = None,
        connect_timeout: Optional[float] = None
    ):
        ws, exc = await self.connect_and_catch(
            client_id=client_id,
            user_id=user_id,
            auth_token=auth_token,
            token=token,
            connect_timeout=connect_timeout
        )
        if exc is not None:
            raise exc
        return ws

    async def disconnect(self, client_id: str) -> None:
        """Disconnect a WebSocket connection.

        Args:
            client_id: Client ID to disconnect
        """
        logger.debug(f"[WebSocketTestHelper] disconnect called for client_id={client_id}")
        if client_id in self.active_connections:
            websocket = self.active_connections[client_id]
            logger.debug(f"[WebSocketTestHelper] disconnect: websocket id={id(websocket)} state={websocket.client_state}")
            await self.websocket_manager.disconnect(client_id)
            # Ensure the mock websocket state is set to DISCONNECTED
            if hasattr(websocket, "client_state") and websocket.client_state != WebSocketState.DISCONNECTED:
                websocket.client_state = WebSocketState.DISCONNECTED
                logger.debug(f"[WebSocketTestHelper] Forced client_state DISCONNECTED for client_id={client_id}")
            logger.debug(f"[WebSocketTestHelper] Removing client_id={client_id} from active_connections (final state: {websocket.client_state}, id={id(websocket)})")
            self.remove_connection(client_id)
            self.debug_active_connections()
            if client_id in self.stream_messages:
                del self.stream_messages[client_id]
            await asyncio.sleep(0)  # Yield to event loop

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
        print(f"[DEBUG][WebSocketTestHelper.send_json] called. Using class: {self.__class__.__name__}")
        ws = self.active_connections.get(client_id)
        print(f"[DEBUG][WebSocketTestHelper.send_json] ws instance type: {type(ws)} for client_id={client_id}")
        logger.debug(f"[WebSocketTestHelper] send_json: client_id={client_id} data={data}")
        if not ws:
            logger.error(f"[WebSocketTestHelper] send_json: No active connection for client {client_id}")
            raise ValueError(f"No active connection for client {client_id}")

        logger.debug(f"[WebSocketTestHelper] send_json: connection state before send: {ws.client_state}")
        try:
            logger.debug(f"[WebSocketTestHelper] send_json: Before send_message client_id={client_id}")
            async with asyncio.timeout(timeout or self.message_timeout):
                await self.websocket_manager.send_message(client_id, data)
                logger.debug(f"[WebSocketTestHelper] send_json: After send_message, before receive_json client_id={client_id} connection state: {ws.client_state}")
                response = await ws.receive_json()
                logger.debug(f"[WebSocketTestHelper] send_json: After receive_json client_id={client_id} response={response} connection state: {ws.client_state}")

                if not ignore_errors and response.get("type") == "error":
                    logger.error(f"[WebSocketTestHelper] send_json: Received error response for client_id={client_id}: {response}")
                    raise ConnectionClosed(
                        Close(code=status.WS_1008_POLICY_VIOLATION, reason=response.get("content", "Unknown error")),
                        None
                    )

                return response

        except asyncio.TimeoutError:
            logger.error(f"[WebSocketTestHelper] send_json: Message timeout for client {client_id}")
            raise
        except Exception as e:
            logger.error(f"[WebSocketTestHelper] send_json: Exception for client {client_id}: {e}")
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
        logger.debug(f"[WebSocketTestHelper] get_connection_state: client_id={client_id} id={id(websocket) if websocket else None} state={websocket.client_state if websocket else None}")
        self.debug_active_connections()
        return websocket.client_state if websocket else WebSocketState.DISCONNECTED

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
        """Receive a message from a test WebSocket client, skipping 'ping' messages."""
        if client_id not in self.active_connections:
            raise ValueError(f"Client {client_id} not connected")

        websocket = self.active_connections[client_id]
        try:
            async with asyncio.timeout(timeout):
                while True:
                    msg = await websocket.receive_json()
                    if msg.get("type") == "ping":
                        continue  # Skip echoed ping
                    return msg
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

    @property
    def ws_manager(self) -> WebSocketManager:
        """Expose the underlying WebSocketManager for test patching."""
        return self.websocket_manager

    def debug_active_connections(self):
        """Log all active connection ids and their states/ids for debugging."""
        for cid, ws in self.active_connections.items():
            logger.debug(f"[WebSocketTestHelper] active: client_id={cid} state={ws.client_state} id={id(ws)}")

    def add_connection(self, client_id: str, ws: MockWebSocket):
        logger.debug(f"[WebSocketTestHelper] ADD active_connections: client_id={client_id} id={id(ws)} state={ws.client_state}")
        self.active_connections[client_id] = ws

    def remove_connection(self, client_id: str):
        ws = self.active_connections.get(client_id)
        logger.debug(f"[WebSocketTestHelper] REMOVE active_connections: client_id={client_id} id={id(ws) if ws else None} state={ws.client_state if ws else None}")
        if client_id in self.active_connections:
            del self.active_connections[client_id]