import asyncio
import websockets

async def test_websocket():
    uri = "ws://backend-test:8000/api/v1/ws"
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected to websocket")
            await websocket.close()
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(test_websocket()) 