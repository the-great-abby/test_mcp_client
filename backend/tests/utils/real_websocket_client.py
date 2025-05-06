import asyncio
import json
from websockets import connect, ConnectionClosed
from starlette.websockets import WebSocketState
import os

class RealWebSocketClient:
    """
    Async WebSocket client for integration tests.
    Connects to a real WebSocket server, sends/receives JSON, and tracks connection state.
    Supports custom headers for external APIs.
    """
    def __init__(self, uri, token=None, debug=False, headers=None, ws_token_query=False):
        # Fast-fail if running in mock mode
        if os.environ.get("USE_MOCK_WEBSOCKET", "0").lower() in ("1", "true", "yes"):
            raise RuntimeError("RealWebSocketClient should not be used in mock mode (USE_MOCK_WEBSOCKET=1)")
        self.uri = uri
        self.token = token
        self.headers = headers or {}
        self.websocket = None
        self.client_state = WebSocketState.CONNECTING
        self.debug = debug
        self.ws_token_query = ws_token_query  # If True, send token as query param

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()

    async def connect(self):
        connect_kwargs = {}
        uri = self.uri
        if self.ws_token_query and self.token:
            # Append token as query parameter
            sep = '&' if '?' in uri else '?'
            uri = f"{uri}{sep}token={self.token}"
        elif self.token and 'Authorization' not in self.headers:
            # Add token as Bearer if not already present
            connect_kwargs.setdefault('extra_headers', {})['Authorization'] = f'Bearer {self.token}'
        if self.headers:
            connect_kwargs['extra_headers'] = {**connect_kwargs.get('extra_headers', {}), **self.headers}
        if self.debug:
            print(f"[RealWebSocketClient] Connecting to {uri} with headers: {connect_kwargs.get('extra_headers')}")
        self.websocket = await connect(uri, **connect_kwargs)
        self.client_state = WebSocketState.CONNECTED

    async def send_json(self, data):
        if self.debug:
            print(f"[RealWebSocketClient] Sending: {data}")
        await self.websocket.send(json.dumps(data))

    async def receive_json(self):
        msg = await self.websocket.recv()
        if self.debug:
            print(f"[RealWebSocketClient] Received: {msg}")
        return json.loads(msg)

    async def close(self):
        if self.websocket and self.client_state == WebSocketState.CONNECTED:
            await self.websocket.close()
            self.client_state = WebSocketState.DISCONNECTED

    def is_connected(self):
        return self.client_state == WebSocketState.CONNECTED 