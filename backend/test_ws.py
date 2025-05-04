import asyncio
import websockets
from tests.conftest import test_settings

async def test_websocket():
    uri = f"ws://{test_settings.MCP_HOST}:{test_settings.MCP_PORT}/api/v1/ws"
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected to websocket")
            await websocket.close()
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(test_websocket()) 