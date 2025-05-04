from unittest.mock import AsyncMock, MagicMock
from typing import Dict, Any, List, Optional, AsyncIterator
import asyncio

class MockStreamResponse:
    """Mock response that yields chunks of text"""
    def __init__(self, send_stream_start=False):
        self.chunks = ["Paris", " is", " the", " capital", " of", " France", "."]
        self.send_stream_start = send_stream_start
        self._index = -1 if send_stream_start else 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._index == -1:
            self._index = 0
            return MockAnthropicEvent(type="stream_start")
        
        if self._index < len(self.chunks):
            chunk = self.chunks[self._index]
            self._index += 1
            return MockAnthropicEvent(type="stream", delta=MockAnthropicDelta(text=chunk))
        
        if self._index == len(self.chunks):
            self._index += 1
            return MockAnthropicEvent(type="stream_end")
        
        raise StopAsyncIteration

class MockAnthropicMessage:
    """Mock message for streaming responses"""
    def __init__(self, role: str, content: str):
        self.role = role
        self.content = content

class MockAnthropicContent:
    """Mock content object for streaming responses"""
    def __init__(self, text: str):
        self.text = text

class MockAnthropicEvent:
    """Mock event object that matches the expected Anthropic client format"""
    def __init__(self, type: str, delta=None, message=None):
        self.type = type
        self.delta = delta
        self.message = message

class MockAnthropicDelta:
    """Mock delta object that matches the expected Anthropic client format"""
    def __init__(self, text: str = None, type: str = None):
        self.text = text
        self.type = type

class MockModelClient:
    """Mock client that simulates the Anthropic API"""
    def __init__(self):
        self.messages = []
        self.system = None
        self.messages = type('Messages', (), {'create': self.messages_create})()

    async def messages_create(self, *args, **kwargs):
        """Mock message creation that returns a streaming response"""
        stream = kwargs.get('stream', False)
        if stream:
            return MockStreamResponse(send_stream_start=True)
        return MockAnthropicEvent(
            type="message",
            message={"content": [{"type": "text", "text": "This is a mock response"}]}
        )

    async def stream(self, event):
        """Convert Anthropic events to the format expected by the websocket"""
        if event.type == "stream_start":
            return {
                "type": "stream_start",
                "content": "",
                "metadata": {}
            }
        elif event.type == "stream":
            # Handle the case where event.delta is None or text is None
            text = ""
            if event.delta and event.delta.text is not None:
                text = event.delta.text
            
            return {
                "type": "stream",
                "content": {
                    "content_block_delta": {
                        "type": "text",
                        "text": text
                    }
                },
                "metadata": {}
            }
        elif event.type == "stream_end":
            return {
                "type": "stream_end",
                "content": "",
                "metadata": {}
            }
        return None

class MockAnthropicClient:
    def __init__(self):
        self.messages = []
        self.system = None
        self.messages = type('Messages', (), {'create': self.messages_create})()
        
    async def messages_create(self, *args, **kwargs):
        """Mock message creation that handles both streaming and non-streaming"""
        messages = kwargs.get("messages", [])
        self.system = next((m["content"] for m in messages if m["role"] == "system"), None)
        
        if kwargs.get("stream", False):
            # Return an async generator that matches the expected format
            async def stream_response():
                chunks = [
                    "Paris",
                    " is",
                    " the",
                    " capital",
                    " of",
                    " France",
                    "."
                ]
                
                # First yield a stream_start event
                yield type('Event', (), {
                    'type': 'stream_start',
                    'delta': None,
                    'message': None
                })()
                
                # Then yield content blocks
                for chunk in chunks:
                    yield type('Event', (), {
                        'type': 'stream',
                        'delta': type('Delta', (), {
                            'type': 'text',
                            'text': chunk
                        })(),
                        'message': None
                    })()
                
                # End the stream
                yield type('Event', (), {
                    'type': 'stream_end',
                    'delta': None,
                    'message': None
                })()
            
            return stream_response()
        else:
            # Non-streaming response
            return type('Response', (), {
                'content': [{'type': 'text', 'text': 'Paris is the capital of France.'}],
                'model': 'claude-3-opus-20240229',
                'role': 'assistant',
                'type': 'message',
                'id': 'mock_msg_123',
            })()

def get_mock_anthropic():
    return MockAnthropicClient()