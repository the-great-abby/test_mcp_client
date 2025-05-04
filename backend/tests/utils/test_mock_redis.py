"""Tests for the Redis mock implementation."""
import pytest
import asyncio
from typing import Dict, Any
from redis.exceptions import WatchError, RedisError
from tests.utils.mock_redis import MockRedis
import sys

@pytest.fixture
async def mock_redis():
    """Create a fresh MockRedis instance for each test."""
    return MockRedis()

@pytest.mark.asyncio
async def test_set_get(mock_redis):
    """Test basic set/get operations."""
    key = b"test_key"
    value = b"test_value"
    assert await mock_redis.set(key, value) is True
    assert await mock_redis.get(key) == value

@pytest.mark.asyncio
async def test_set_get_with_expiry(mock_redis):
    """Test set/get with expiry."""
    key = b"test_key"
    value = b"test_value"
    assert await mock_redis.set(key, value, ex=1) is True
    assert await mock_redis.get(key) == value
    await asyncio.sleep(1.1)
    assert await mock_redis.get(key) is None

@pytest.mark.asyncio
async def test_hset_hget(mock_redis):
    """Test hash operations."""
    key = b"test_hash"
    field = b"test_field"
    value = b"test_value"
    assert await mock_redis.hset(key, field, value) == 1
    assert await mock_redis.hget(key, field) == value

@pytest.mark.asyncio
async def test_hgetall(mock_redis):
    """Test getting all hash fields."""
    key = b"test_hash"
    data = {b"field1": b"value1", b"field2": b"value2"}
    for field, value in data.items():
        await mock_redis.hset(key, field, value)
    assert await mock_redis.hgetall(key) == data

@pytest.mark.asyncio
async def test_delete(mock_redis):
    """Test key deletion."""
    key = b"test_key"
    value = b"test_value"
    await mock_redis.set(key, value)
    assert await mock_redis.delete(key) == 1
    assert await mock_redis.get(key) is None

@pytest.mark.asyncio
async def test_exists(mock_redis):
    """Test key existence check."""
    key = b"test_key"
    value = b"test_value"
    assert await mock_redis.exists(key) == 0
    await mock_redis.set(key, value)
    assert await mock_redis.exists(key) == 1

@pytest.mark.asyncio
async def test_lpush_lpop(mock_redis):
    """Test list operations."""
    key = b"test_list"
    value1 = b"value1"
    value2 = b"value2"
    assert await mock_redis.lpush(key, value1, value2) == 2
    assert await mock_redis.lpop(key) == value2
    assert await mock_redis.lpop(key) == value1
    assert await mock_redis.lpop(key) is None

@pytest.mark.asyncio
async def test_rpush_rpop(mock_redis):
    """Test list operations from right side."""
    key = b"test_list"
    value1 = b"value1"
    value2 = b"value2"
    assert await mock_redis.rpush(key, value1, value2) == 2
    assert await mock_redis.rpop(key) == value2
    assert await mock_redis.rpop(key) == value1
    assert await mock_redis.rpop(key) is None

@pytest.mark.asyncio
async def test_lrange(mock_redis):
    """Test list range retrieval."""
    key = b"test_list"
    values = [b"value1", b"value2", b"value3"]
    await mock_redis.rpush(key, *values)
    assert await mock_redis.lrange(key, 0, -1) == values
    assert await mock_redis.lrange(key, 0, 1) == values[:2]
    assert await mock_redis.lrange(key, -2, -1) == values[-2:]

@pytest.mark.asyncio
async def test_watch_multi_exec(mock_redis):
    """Test transaction handling."""
    key = b"test_key"
    value1 = b"value1"
    value2 = b"value2"
    
    # Start transaction with watch
    tr = await mock_redis.watch(key)
    # Queue commands on transaction object
    await tr.set(key, value1)
    await tr.get(key)
    # Execute transaction
    results = await tr.execute()
    assert results == [True, value1]
    # Verify final state
    assert await mock_redis.get(key) == value1

@pytest.mark.asyncio
async def test_watch_multi_exec_conflict(mock_redis):
    """Test transaction conflict handling."""
    key = b"test_key"
    value1 = b"value1"
    value2 = b"value2"
    
    # Start transaction with watch
    tr = await mock_redis.watch(key)
    # Simulate concurrent modification outside transaction
    await mock_redis.set(key, value2)
    # Queue commands on transaction object
    await tr.set(key, value1)
    await tr.get(key)
    # Execute should fail
    with pytest.raises(WatchError):
        await tr.execute()
    # Verify state unchanged
    assert await mock_redis.get(key) == value2

@pytest.mark.asyncio
async def test_type_conversion(mock_redis):
    """Test type conversion handling."""
    key = b"test_key"
    int_value = 42
    float_value = 3.14
    bool_value = True
    
    # Test integer
    await mock_redis.set(key, int_value)
    assert await mock_redis.get(key) == str(int_value).encode()
    
    # Test float
    await mock_redis.set(key, float_value)
    assert await mock_redis.get(key) == str(float_value).encode()
    
    # Test boolean
    await mock_redis.set(key, bool_value)
    assert await mock_redis.get(key) == str(int(bool_value)).encode()

@pytest.mark.asyncio
async def test_error_handling(mock_redis):
    """Test error handling."""
    key = b"test_key"
    value = b"test_value"
    
    # Test wrong type operation
    await mock_redis.lpush(key, value)
    with pytest.raises(RedisError):
        await mock_redis.get(key)
    
    # Test invalid command
    with pytest.raises(RedisError):
        await mock_redis.invalid_command()

@pytest.mark.asyncio
async def test_pubsub_basic(mock_redis):
    """Test basic pub/sub functionality."""
    channel = "test_channel"
    message = "hello world"

    # Subscribe to the channel
    queue = await mock_redis.subscribe(channel)

    # Publish a message
    num_subs = await mock_redis.publish(channel, message)
    assert num_subs == 1

    # Receive the message
    received = await queue.get()
    assert received == message

    # Unsubscribe and ensure no more messages are received
    await mock_redis.unsubscribe(channel, queue)
    num_subs = await mock_redis.publish(channel, "should not be received")
    assert num_subs == 0

@pytest.mark.asyncio
async def test_ttl_pttl(mock_redis):
    """Test ttl and pttl methods for expiry semantics."""
    key = b"ttl_key"
    value = b"value"

    # Key does not exist
    assert await mock_redis.ttl(key) == -2
    assert await mock_redis.pttl(key) == -2

    # Key exists, no expiry
    await mock_redis.set(key, value)
    assert await mock_redis.ttl(key) == -1
    assert await mock_redis.pttl(key) == -1

    # Key with expiry
    await mock_redis.set(key, value, ex=2)
    ttl = await mock_redis.ttl(key)
    pttl = await mock_redis.pttl(key)
    assert 0 < ttl <= 2
    assert 0 < pttl <= 2000

    # After expiry
    await asyncio.sleep(2.1)
    assert await mock_redis.ttl(key) == -2
    assert await mock_redis.pttl(key) == -2

@pytest.mark.asyncio
async def test_keys_and_scan(mock_redis):
    """Test keys and scan pattern matching and pagination."""
    # Add some keys
    await mock_redis.set(b"foo1", b"bar")
    await mock_redis.set(b"foo2", b"baz")
    await mock_redis.set(b"bar1", b"qux")

    # Test keys pattern matching
    keys = await mock_redis.keys("foo*")
    assert set(keys) == {b"foo1", b"foo2"}
    keys = await mock_redis.keys("bar*")
    assert keys == [b"bar1"]
    keys = await mock_redis.keys("nope*")
    assert keys == []

    # Test scan pagination
    all_keys = set([b"foo1", b"foo2", b"bar1"])
    cursor, batch = await mock_redis.scan(0, match="*", count=2)
    assert set(batch).issubset(all_keys)
    if cursor != 0:
        cursor, batch2 = await mock_redis.scan(cursor, match="*", count=2)
        assert set(batch2).issubset(all_keys)
        assert set(batch + batch2) == all_keys
    else:
        assert set(batch) == all_keys 