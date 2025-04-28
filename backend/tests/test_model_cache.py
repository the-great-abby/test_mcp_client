import pytest
from datetime import timedelta
import json
import asyncio
from redis.asyncio import Redis
from app.core.cache import ModelResponseCache
from app.core.config import settings
from tests.helpers import MockRedis

@pytest.fixture
async def async_redis_client():
    """Create a Redis client for testing."""
    return MockRedis()

@pytest.fixture
async def model_cache(async_redis_client):
    """Create a ModelResponseCache instance for testing."""
    return ModelResponseCache(async_redis_client)

@pytest.mark.asyncio
async def test_generate_cache_key(model_cache):
    """Test cache key generation for model responses."""
    messages = [{"role": "user", "content": "Hello"}]
    system_prompt = "You are a helpful assistant"
    
    # Test with system prompt
    key1 = model_cache._generate_cache_key(messages, system_prompt)
    assert isinstance(key1, str)
    assert len(key1) == 64  # SHA-256 hash length
    
    # Test without system prompt
    key2 = model_cache._generate_cache_key(messages)
    assert isinstance(key2, str)
    assert len(key2) == 64  # SHA-256 hash length
    
    # Verify different prompts generate different keys
    key3 = model_cache._generate_cache_key(
        messages, 
        "Different system prompt"
    )
    assert key3 != key1
    
    # Verify same inputs generate same key
    key4 = model_cache._generate_cache_key(messages, system_prompt)
    assert key4 == key1

@pytest.mark.asyncio
async def test_cache_response_operations(model_cache):
    """Test caching and retrieving model responses."""
    messages = [{"role": "user", "content": "Test message"}]
    response = "Test response"
    system_prompt = "Test system prompt"
    
    # Test caching with default TTL
    await model_cache.cache_response(messages, response, system_prompt)
    cached = await model_cache.get_cached_response(messages, system_prompt)
    assert cached == response
    
    # Test caching with custom TTL
    custom_ttl = timedelta(minutes=5)
    await model_cache.cache_response(
        messages, 
        response, 
        system_prompt, 
        ttl=custom_ttl
    )
    cached = await model_cache.get_cached_response(messages, system_prompt)
    assert cached == response
    
    # Test cache miss
    different_messages = [{"role": "user", "content": "Different"}]
    cached = await model_cache.get_cached_response(different_messages)
    assert cached is None
    
    # Test cache invalidation
    await model_cache.invalidate_cache(messages, system_prompt)
    cached = await model_cache.get_cached_response(messages, system_prompt)
    assert cached is None

@pytest.mark.asyncio
async def test_error_handling(model_cache, monkeypatch):
    """Test error handling in cache operations."""
    messages = [{"role": "user", "content": "Test"}]
    
    # Test get_cached_response error handling
    def mock_get(*args, **kwargs):
        raise Exception("Redis error")
    monkeypatch.setattr(model_cache.redis, "get", mock_get)
    result = await model_cache.get_cached_response(messages)
    assert result is None
    
    # Test cache_response error handling
    def mock_set(*args, **kwargs):
        raise Exception("Redis error")
    monkeypatch.setattr(model_cache.redis, "set", mock_set)
    # Should not raise exception
    await model_cache.cache_response(messages, "test")
    
    # Test invalidate_cache error handling
    def mock_delete(*args, **kwargs):
        raise Exception("Redis error")
    monkeypatch.setattr(model_cache.redis, "delete", mock_delete)
    # Should not raise exception
    await model_cache.invalidate_cache(messages)

@pytest.mark.asyncio
async def test_cache_expiry(model_cache):
    """Test that cached responses expire correctly."""
    messages = [{"role": "user", "content": "Test"}]
    response = "Test response"
    
    # Cache with very short TTL
    await model_cache.cache_response(
        messages, 
        response, 
        ttl=timedelta(seconds=1)
    )
    
    # Verify it's cached
    cached = await model_cache.get_cached_response(messages)
    assert cached == response
    
    # Wait for expiry
    await asyncio.sleep(1.1)
    
    # Verify it's expired
    cached = await model_cache.get_cached_response(messages)
    assert cached is None 