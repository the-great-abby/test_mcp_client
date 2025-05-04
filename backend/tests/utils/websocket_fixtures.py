import pytest
import os
from tests.utils.real_websocket_client import RealWebSocketClient

@pytest.fixture
async def real_websocket_client(request):
    """
    Provides a connected RealWebSocketClient for integration tests.
    Only runs for tests marked with @pytest.mark.real_websocket.
    """
    if not request.node.get_closest_marker("real_websocket"):
        pytest.skip("Test requires @pytest.mark.real_websocket")
    # Use environment variable or default for WebSocket URI
    uri = os.getenv("TEST_WS_URI", "ws://backend-test:8000/ws")
    token = os.getenv("TEST_USER_TOKEN")  # Or set as needed
    debug = bool(os.getenv("WS_CLIENT_DEBUG", False))
    print(f"[DEBUG][real_websocket_client] Using URI: {uri}")
    print(f"[DEBUG][real_websocket_client] Using TOKEN: {token}")
    async with RealWebSocketClient(uri=uri, token=token, debug=debug) as client:
        yield client 