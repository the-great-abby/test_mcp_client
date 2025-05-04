import pytest
import time
from redis.exceptions import WatchError, RedisError
from tests.utils.mock_redis import MockRedis
import asyncio

@pytest.fixture
def redis():
    """Provide a fresh MockRedis instance for each test."""
    return MockRedis()

@pytest.fixture
def pipeline(redis):
    """Provide a pipeline instance for each test."""
    return redis.pipeline()

@pytest.mark.asyncio
async def test_basic_operations(redis):
    """Test basic Redis operations."""
    # Test set and get
    assert await redis.set("key1", "value1") is True
    assert await redis.get("key1") == b"value1"
    
    # Test non-existent key
    assert await redis.get("nonexistent") is None
    
    # Test delete
    assert await redis.delete("key1") == 1
    assert await redis.get("key1") is None
    assert await redis.delete("nonexistent") == 0

@pytest.mark.asyncio
async def test_expiry_operations(redis):
    """Test key expiry operations."""
    # Test setting with expiry
    await redis.set("temp_key", "temp_value", ex=1)
    assert await redis.get("temp_key") == b"temp_value"
    
    # Wait for expiry
    await asyncio.sleep(1.1)
    assert await redis.get("temp_key") is None
    
    # Test expire command
    await redis.set("another_key", "value")
    assert await redis.expire("another_key", 1) is True
    assert await redis.get("another_key") == b"value"
    await asyncio.sleep(1.1)
    assert await redis.get("another_key") is None
    
    # Test expire on non-existent key
    assert await redis.expire("nonexistent", 1) is False

@pytest.mark.asyncio
async def test_hash_operations(redis):
    """Test Redis hash operations."""
    # Test hash operations
    assert await redis.hset("myhash", "field1", "value1") == 1
    assert await redis.hset("myhash", "field2", "value2") == 1
    
    # Test individual field get
    assert await redis.hget("myhash", "field1") == b"value1"
    assert await redis.hget("myhash", "field2") == b"value2"
    
    # Test getting all fields
    result = await redis.hgetall("myhash")
    assert result == {
        b"field1": b"value1",
        b"field2": b"value2"
    }
    
    # Test non-existent hash
    assert await redis.hgetall("nonexistent") == {}
    
    # Test non-existent field
    assert await redis.hget("myhash", "nonexistent") is None
    assert await redis.hget("nonexistent", "field") is None

@pytest.mark.asyncio
async def test_hash_increment(redis):
    """Test hash field increment operations."""
    # Test basic increment
    assert await redis.hincrby("hash1", "field1", 1) == 1
    assert await redis.hincrby("hash1", "field1", 1) == 2
    
    # Test custom increment amount
    assert await redis.hincrby("hash1", "field2", 5) == 5
    assert await redis.hincrby("hash1", "field2", 3) == 8
    
    # Test negative increment
    assert await redis.hincrby("hash1", "field3", -3) == -3
    
    # Test increment on non-numeric value
    await redis.hset("hash1", "field4", "not_a_number")
    with pytest.raises(RedisError, match="Hash field value is not an integer"):
        await redis.hincrby("hash1", "field4", 1)

@pytest.mark.asyncio
async def test_list_operations(redis):
    """Test Redis list operations."""
    # Test lpush and lrange
    assert await redis.lpush("mylist", "value1") == 1
    assert await redis.lpush("mylist", "value2") == 2
    assert await redis.lpush("mylist", "value3") == 3
    
    # Test lrange
    assert await redis.lrange("mylist", 0, -1) == [b"value3", b"value2", b"value1"]
    assert await redis.lrange("mylist", 1, 2) == [b"value2", b"value1"]
    assert await redis.lrange("mylist", -2, -1) == [b"value2", b"value1"]
    
    # Test empty list
    assert await redis.lrange("nonexistent", 0, -1) == []
    
    # Test invalid list operation
    await redis.set("not_a_list", "string_value")
    with pytest.raises(RedisError, match="Key contains a non-list value"):
        await redis.lpush("not_a_list", "value")

@pytest.mark.asyncio
async def test_key_pattern_matching(redis):
    """Test Redis key pattern matching."""
    # Set up some keys
    await redis.set("user:1", "data1")
    await redis.set("user:2", "data2")
    await redis.set("post:1", "post1")
    await redis.set("comment:1", "comment1")
    
    # Test exact match
    assert await redis.keys("user:1") == [b"user:1"]
    
    # Test wildcard patterns
    user_keys = await redis.keys("user:*")
    assert set(user_keys) == {b"user:1", b"user:2"}
    
    keys_with_1 = await redis.keys("*:1")
    assert set(keys_with_1) == {b"user:1", b"post:1", b"comment:1"}
    
    # Test multiple wildcards
    all_keys = await redis.keys("*")
    assert set(all_keys) == {b"user:1", b"user:2", b"post:1", b"comment:1"}
    
    # Test no matches
    assert await redis.keys("nonexistent:*") == []

@pytest.mark.asyncio
async def test_pipeline_operations(pipeline, redis):
    """Test Redis pipeline operations."""
    # Queue multiple commands
    await pipeline.set("key1", "value1")
    await pipeline.set("key2", "value2")
    await pipeline.get("key1")
    await pipeline.get("key2")
    
    # Execute pipeline
    results = await pipeline.execute()
    assert len(results) == 4
    assert results[0] is True  # set result
    assert results[1] is True  # set result
    assert results[2] == b"value1"  # get result
    assert results[3] == b"value2"  # get result

@pytest.mark.asyncio
async def test_pipeline_error_handling(pipeline, redis):
    """Test Redis pipeline error handling."""
    # Test pipeline with invalid operations
    await redis.set("string_key", "value")
    
    await pipeline.set("key1", "value1")
    await pipeline.hget("string_key", "field")  # Will fail - string_key is not a hash
    await pipeline.set("key2", "value2")
    
    with pytest.raises(RedisError, match="Key contains a non-hash value"):
        await pipeline.execute()
    
    # Verify that no commands were executed (transaction-like behavior)
    assert await redis.get("key1") is None
    assert await redis.get("key2") is None

@pytest.mark.asyncio
async def test_transaction_watch(pipeline, redis):
    """Test Redis transaction with WATCH command."""
    # Set initial value
    await redis.set("watched_key", "initial")
    
    # Start transaction
    pipeline.watch("watched_key")
    await pipeline.multi()
    await pipeline.set("watched_key", "changed")
    await pipeline.get("watched_key")
    
    # Execute should succeed if no one modified the key
    results = await pipeline.execute()
    assert len(results) == 2
    assert results[0] is True
    assert results[1] == b"changed"

@pytest.mark.asyncio
async def test_transaction_watch_conflict(redis):
    """Test Redis transaction with WATCH command and conflict."""
    # Set initial value
    await redis.set("watched_key", "initial")
    
    # Start transaction with first pipeline
    pipeline1 = redis.pipeline()
    pipeline1.watch("watched_key")
    await pipeline1.multi()
    await pipeline1.set("watched_key", "pipeline1_value")
    
    # Modify watched key with second client
    await redis.set("watched_key", "modified")
    
    # First pipeline's execution should fail
    with pytest.raises(WatchError):
        await pipeline1.execute()
    
    # Verify key was not changed by failed transaction
    assert await redis.get("watched_key") == b"modified"

@pytest.mark.asyncio
async def test_complex_transaction(redis):
    """Test complex transaction with multiple operations."""
    pipeline = redis.pipeline()
    
    # Set up initial data
    await redis.set("key1", "1")
    await redis.set("key2", "2")
    
    # Start transaction
    pipeline.watch("key1", "key2")
    await pipeline.multi()
    
    # Queue multiple operations
    await pipeline.incrby("key1", 1)
    await pipeline.incrby("key2", 6)
    await pipeline.set("key3", "new")
    
    # Execute transaction
    results = await pipeline.execute()
    assert results == [2, 8, True]

@pytest.mark.asyncio
async def test_type_validation(redis):
    """Test type validation in Redis operations."""
    # Set up test data
    await redis.set("string_key", "value")
    await redis.hset("hash_key", "field", "value")
    await redis.lpush("list_key", "value")
    
    # Test string operations on wrong types
    with pytest.raises(RedisError, match="Key contains a non-hash value"):
        await redis.hget("string_key", "field")
    
    with pytest.raises(RedisError, match="Key contains a non-list value"):
        await redis.lrange("hash_key", 0, -1)

@pytest.mark.asyncio
async def test_transaction_edge_cases(redis):
    """Test edge cases in Redis transactions."""
    pipeline = redis.pipeline()
    
    # Test empty transaction
    await pipeline.multi()
    results = await pipeline.execute()
    assert results == []
    
    # Test transaction with invalid command
    await pipeline.multi()
    await pipeline.set("key", "value")
    await pipeline.hget("key", "field")  # Will fail - key is not a hash
    with pytest.raises(RedisError):
        await pipeline.execute()

@pytest.mark.asyncio
async def test_expire_edge_cases(redis):
    """Test edge cases for expiry operations."""
    # Test expire on non-existent key
    assert await redis.expire("nonexistent", 1) is False
    
    # Test expire with invalid timeout
    with pytest.raises(RedisError):
        await redis.expire("key", -1)
    
    # Test expire on existing key
    await redis.set("key", "value")
    assert await redis.expire("key", 1) is True

@pytest.mark.asyncio
async def test_key_pattern_edge_cases(redis):
    """Test edge cases for key pattern matching."""
    # Test empty pattern
    assert await redis.keys("") == []
    
    # Test pattern with special characters
    await redis.set("key:with:colons", "value")
    await redis.set("key*with*stars", "value")
    
    assert len(await redis.keys("key:*")) == 1
    assert len(await redis.keys("key*")) == 2 