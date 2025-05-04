import pytest
from unittest.mock import patch, AsyncMock
from tests.mocks.anthropic_mock import MockModelClient, get_mock_anthropic
import asyncio
from app.core.model import ModelClient
import anthropic
from app.core.websocket import WebSocketManager

@pytest.fixture(autouse=True)
def mock_anthropic():
    """Fixture to mock the Anthropic client for all tests"""
    with patch('anthropic.AsyncAnthropic', return_value=get_mock_anthropic()):
        yield

@pytest.fixture
def mock_model():
    """Fixture to mock the ModelClient for testing"""
    mock_client = MockModelClient()
    yield mock_client 