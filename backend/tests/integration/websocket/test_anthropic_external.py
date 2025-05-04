import os
import pytest
from tests.utils.real_websocket_client import RealWebSocketClient

ANTHROPIC_WS_URI = os.getenv("ANTHROPIC_WS_URI", "wss://api.anthropic.com/v1/messages")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

pytestmark = pytest.mark.xfail(reason="Anthropic WebSocket access requires account enablement; see .cursor/rules/websocket_anthropic.mdc")

@pytest.mark.real_anthropic
@pytest.mark.real_websocket
@pytest.mark.anthropic
@pytest.mark.external
@pytest.mark.asyncio
async def test_anthropic_websocket_direct():
    """
    Directly test Anthropic's WebSocket API with a Claude-3 streaming payload.
    WARNING: This test will incur real API usage and should only be run intentionally.
    Run with: pytest -m anthropic or pytest -m external
    Set ANTHROPIC_API_KEY and optionally ANTHROPIC_WS_URI in your environment.
    """
    if not ANTHROPIC_API_KEY:
        pytest.skip("No Anthropic API key set in ANTHROPIC_API_KEY")
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        # Add any other required headers here
    }
    async with RealWebSocketClient(uri=ANTHROPIC_WS_URI, headers=headers, debug=True) as client:
        # Send a valid Claude-3 streaming message
        await client.send_json({
            "model": "claude-3-opus-20240229",  # Update to your available model if needed
            "max_tokens": 1024,
            "messages": [
                {"role": "user", "content": "Hello, Claude!"}
            ],
            "stream": True
        })
        got_response = False
        for _ in range(3):
            response = await client.receive_json()
            print("Anthropic response:", response)
            if response:
                got_response = True
        assert got_response, "No response received from Anthropic API!"
        print("Anthropic API test PASSED") 