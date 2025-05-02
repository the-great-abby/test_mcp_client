import asyncio
import pytest
from redis.asyncio import Redis
from app.core.cache import get_cached_data, set_cached_data, invalidate_cache, get_cache_key
from unittest.mock import AsyncMock
from tests.helpers import MockRedis
import json

@pytest.fixture
async def async_redis_client():
    """Create a mock Redis client for testing."""
    client = MockRedis()
    yield client

@pytest.mark.asyncio
async def test_cache_operations(async_redis_client, initialize_test_db):
    """Test basic cache operations."""
    test_key = "test:key"
    test_data = {"message": "Hello, World!"}
    
    # Test setting data
    success = await set_cached_data(async_redis_client, test_key, test_data)
    assert success is True
    
    # Test getting data
    cached_data = await get_cached_data(async_redis_client, test_key)
    assert cached_data == test_data
    
    # Test cache expiry
    success = await set_cached_data(async_redis_client, "expiry:test", "temp", expiry=1)
    assert success is True
    await asyncio.sleep(1.1)  # Wait for expiry
    expired_data = await get_cached_data(async_redis_client, "expiry:test")
    assert expired_data is None
    
    # Test cache invalidation
    success = await invalidate_cache(async_redis_client, test_key)
    assert success is True
    invalidated_data = await get_cached_data(async_redis_client, test_key)
    assert invalidated_data is None

@pytest.mark.asyncio
async def test_cache_key_generation(async_redis_client):
    """Test cache key generation with different input types."""
    # Test string input
    key1 = get_cache_key("test", "key")
    assert isinstance(key1, str)
    assert key1 == "test:key"
    
    # Test dictionary input
    key2 = get_cache_key({"a": 1, "b": 2})
    assert isinstance(key2, str)
    assert key2 == "a=1:b=2"
    
    # Test mixed input types
    key3 = get_cache_key("prefix", {"id": 123}, ["a", "b"])
    assert isinstance(key3, str)
    assert key3 == "prefix:id=123:a:b"
    
    # Test empty args
    key4 = get_cache_key()
    assert key4 == ""
    
    # Test None values
    key5 = get_cache_key(None)
    assert key5 == "None"
    
    # Test complex nested structures
    key6 = get_cache_key(
        {"nested": {"a": 1, "b": 2}},
        [1, 2, {"x": "y"}]
    )
    assert isinstance(key6, str)
    assert "nested={'a': 1, 'b': 2}" in key6
    assert "{'x': 'y'}" in key6
    
    # Test empty list and empty dict
    key7 = get_cache_key([], {})
    assert key7 == "[]:{}",  "Empty lists and dicts should be represented as [] and {}"

@pytest.mark.asyncio
async def test_cache_data_types(async_redis_client, initialize_test_db):
    """Test caching different data types."""
    test_cases = [
        ("string:test", json.dumps("Hello")),  # JSON encode string
        ("int:test", 42),
        ("float:test", 3.14),
        ("list:test", [1, 2, 3]),
        ("dict:test", {"a": 1, "b": 2}),
        ("none:test", json.dumps("null")),  # JSON encode string
        ("bool:test", True),
        ("complex:test", {"nested": {"data": [1, 2, 3]}}),
    ]
    
    for key, value in test_cases:
        # Set value
        success = await set_cached_data(async_redis_client, key, value)
        assert success is True
        
        # Get and verify value
        cached = await get_cached_data(async_redis_client, key)
        if isinstance(value, str):
            # For string values, we need to JSON decode them
            assert cached == json.loads(value)
        else:
            assert cached == value

@pytest.mark.asyncio
async def test_cache_errors(async_redis_client, initialize_test_db):
    """Test error handling in cache operations."""
    # Test None key
    with pytest.raises(ValueError):
        await get_cached_data(async_redis_client, None)
    
    # Test empty key
    with pytest.raises(ValueError):
        await set_cached_data(async_redis_client, "", "data")
    
    # Test None data
    with pytest.raises(ValueError):
        await set_cached_data(async_redis_client, "key", None)
    
    # Test negative expiry
    with pytest.raises(ValueError):
        await set_cached_data(async_redis_client, "key", "data", expiry=-1)
    
    # Test None redis client
    with pytest.raises(AttributeError):
        await get_cached_data(None, "key")

@pytest.mark.asyncio
async def test_cache_error_handling(async_redis_client, monkeypatch):
    """Test error handling for Redis operations."""
    
    # Test Redis get error
    async def mock_get(*args, **kwargs):
        raise Exception("Redis get error")
    monkeypatch.setattr(async_redis_client, "get", mock_get)
    
    result = await get_cached_data(async_redis_client, "test:key")
    assert result is None
    
    # Test Redis set error
    async def mock_set(*args, **kwargs):
        raise Exception("Redis set error")
    monkeypatch.setattr(async_redis_client, "set", mock_set)
    
    success = await set_cached_data(async_redis_client, "test:key", "data")
    assert success is False
    
    # Test Redis delete error
    async def mock_delete(*args, **kwargs):
        raise Exception("Redis delete error")
    monkeypatch.setattr(async_redis_client, "delete", mock_delete)
    
    success = await invalidate_cache(async_redis_client, "test:key")
    assert success is False
    
    # Test non-JSON data handling
    async def mock_get_bytes(*args, **kwargs):
        return b"not json"
    monkeypatch.setattr(async_redis_client, "get", mock_get_bytes)
    
    result = await get_cached_data(async_redis_client, "test:key")
    assert result == b"not json"  # Should return raw data when JSON parsing fails
    
    # Test JSON serialization error
    class UnserializableObject:
        pass
    
    success = await set_cached_data(async_redis_client, "test:key", UnserializableObject())
    assert success is False

@pytest.mark.asyncio
async def test_cache_key_edge_cases():
    """Test edge cases in cache key generation."""
    # Test empty list handling
    key1 = get_cache_key("test", [], {"a": 1})
    assert "test:" in key1
    assert "[]" in key1
    assert "a=1" in key1

    # Test list with empty elements
    key2 = get_cache_key("test", [None, "", []], {"b": 2})
    assert "test:" in key2
    assert "None" in key2
    assert "[]" in key2
    assert "b=2" in key2

@pytest.mark.asyncio
async def test_cache_set_exceptions(initialize_test_db):
    """Test exception handling in set_cached_data."""
    redis_client = AsyncMock()
    redis_client.set.side_effect = Exception("Redis error")
    
    result = await set_cached_data(redis_client, "test_key", "test_value", 60)
    assert result is False
    redis_client.set.assert_called_once() 