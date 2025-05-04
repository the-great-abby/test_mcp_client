#!/usr/bin/env python3
"""
Standalone script to test Anthropic's WebSocket API (Claude-3 streaming).

Usage:
  export ANTHROPIC_API_KEY=your_real_key
  python scripts/anthropic_ws_direct.py

This script will incur real API usage and should only be run intentionally.
"""
import os
import sys
import asyncio
from tests.utils.real_websocket_client import RealWebSocketClient

ANTHROPIC_WS_URI = os.getenv("ANTHROPIC_WS_URI", "wss://api.anthropic.com/v1/messages")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

async def main():
    if not ANTHROPIC_API_KEY:
        print("No Anthropic API key set in ANTHROPIC_API_KEY")
        sys.exit(1)
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
    }
    try:
        async with RealWebSocketClient(uri=ANTHROPIC_WS_URI, headers=headers, debug=True) as client:
            await client.send_json({
                "model": "claude-3-opus-20240229",
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
    except Exception as e:
        print(f"Anthropic API test FAILED: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 