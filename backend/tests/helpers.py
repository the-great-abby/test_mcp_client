"""Mock Redis client and pipeline for testing."""
from typing import Dict, Any, List, Optional, Union, Callable, Awaitable
from datetime import datetime
import time
from redis.asyncio import Redis
from redis.exceptions import WatchError, RedisError

class MockRedis:
    """Mock Redis client for testing."""
    
    def __init__(self):
        self.store: Dict[str, Any] = {}  # Main storage for all values
        self.expiry: Dict[str, float] = {}  # Expiration times
        self.watched_keys: Dict[str, Any] = {}  # Values of watched keys
        self.in_transaction = False
        self.transaction_store: Optional[Dict[str, Any]] = None
        self.transaction_expiry: Optional[Dict[str, float]] = None
        self.transaction_commands: List[Callable[[], Awaitable[Any]]] = []
    
    def _encode_key(self, key: Union[str, bytes]) -> str:
        """Convert key to string format for internal storage."""
        if isinstance(key, bytes):
            return key.decode('utf-8')
        return str(key)
    
    def _encode_value(self, value: Union[str, bytes, int]) -> bytes:
        """Convert value to bytes format for storage."""
        if isinstance(value, bytes):
            return value
        if isinstance(value, int):
            return str(value).encode('utf-8')
        return str(value).encode('utf-8')
    
    def _decode_value(self, value: Any) -> Optional[bytes]:
        """Convert stored value to bytes format for return."""
        if value is None:
            return None
        if isinstance(value, bytes):
            return value
        if isinstance(value, (str, int)):
            return str(value).encode('utf-8')
        return str(value).encode('utf-8')
    
    async def get(self, key: Union[str, bytes]) -> Optional[bytes]:
        """Get value of key."""
        key = self._encode_key(key)
        if key not in self.store:
            return None
        if key in self.expiry and time.time() > self.expiry[key]:
            del self.store[key]
            del self.expiry[key]
            return None
        return self._decode_value(self.store[key])
    
    async def set(
        self,
        key: Union[str, bytes],
        value: Union[str, bytes],
        ex: Optional[int] = None
    ) -> bool:
        """Set key to value with optional expiry."""
        key = self._encode_key(key)
        value = self._encode_value(value)
        self.store[key] = value
        if ex is not None:
            self.expiry[key] = time.time() + ex
        return True
    
    async def delete(self, *keys: Union[str, bytes]) -> int:
        """Delete one or more keys."""
        count = 0
        for key in keys:
            key = self._encode_key(key)
            if key in self.store:
                del self.store[key]
                if key in self.expiry:
                    del self.expiry[key]
                count += 1
        return count
    
    async def exists(self, key: Union[str, bytes]) -> int:
        """Check if key exists."""
        key = self._encode_key(key)
        if key in self.expiry and time.time() > self.expiry[key]:
            del self.store[key]
            del self.expiry[key]
            return 0
        return int(key in self.store)
    
    async def expire(self, key: Union[str, bytes], seconds: int) -> bool:
        """Set key expiry in seconds."""
        key = self._encode_key(key)
        if key not in self.store:
            return False
        self.expiry[key] = time.time() + seconds
        return True
    
    async def incr(self, key: Union[str, bytes]) -> int:
        """Increment value of key."""
        key = self._encode_key(key)
        if key not in self.store:
            self.store[key] = b"0"
        try:
            value = int(self.store[key].decode('utf-8'))
            value += 1
            self.store[key] = str(value).encode('utf-8')
            return value
        except (ValueError, TypeError):
            raise RedisError("Value is not an integer")
    
    async def decr(self, key: Union[str, bytes]) -> int:
        """Decrement value of key."""
        key = self._encode_key(key)
        if key not in self.store:
            self.store[key] = b"0"
        try:
            value = int(self.store[key].decode('utf-8'))
            value -= 1
            self.store[key] = str(value).encode('utf-8')
            return value
        except (ValueError, TypeError):
            raise RedisError("Value is not an integer")
    
    async def lpush(self, key: Union[str, bytes], *values: Union[str, bytes]) -> int:
        """Push values to head of list."""
        key = self._encode_key(key)
        if key not in self.store:
            self.store[key] = []
        if not isinstance(self.store[key], list):
            raise RedisError("Key contains a non-list value")
        encoded_values = [self._encode_value(v) for v in values]
        self.store[key] = encoded_values + self.store[key]
        return len(self.store[key])
    
    async def rpush(self, key: Union[str, bytes], *values: Union[str, bytes]) -> int:
        """Push values to tail of list."""
        key = self._encode_key(key)
        if key not in self.store:
            self.store[key] = []
        if not isinstance(self.store[key], list):
            raise RedisError("Key contains a non-list value")
        encoded_values = [self._encode_value(v) for v in values]
        self.store[key].extend(encoded_values)
        return len(self.store[key])
    
    async def lrange(
        self,
        key: Union[str, bytes],
        start: int,
        stop: int
    ) -> List[bytes]:
        """Get range of values from list."""
        key = self._encode_key(key)
        if key not in self.store:
            return []
        if not isinstance(self.store[key], list):
            raise RedisError("Key contains a non-list value")
        # Handle negative indices
        if start < 0:
            start = max(len(self.store[key]) + start, 0)
        if stop < 0:
            stop = len(self.store[key]) + stop + 1
        elif stop > 0:
            stop = min(stop + 1, len(self.store[key]))
        return [self._decode_value(v) for v in self.store[key][start:stop]]
    
    async def llen(self, key: Union[str, bytes]) -> int:
        """Get length of list."""
        key = self._encode_key(key)
        if key not in self.store:
            return 0
        if not isinstance(self.store[key], list):
            raise RedisError("Key contains a non-list value")
        return len(self.store[key])
    
    async def keys(self, pattern: Union[str, bytes]) -> List[bytes]:
        """Get all keys matching pattern."""
        pattern = self._encode_key(pattern)
        # Simple pattern matching for now
        if pattern == "*":
            return [k.encode('utf-8') for k in self.store.keys()]
        return [k.encode('utf-8') for k in self.store.keys() if pattern in k]
    
    async def hset(
        self,
        key: Union[str, bytes],
        field: Union[str, bytes],
        value: Union[str, bytes, int]
    ) -> int:
        """Set hash field to value."""
        key = self._encode_key(key)
        field = self._encode_key(field)
        value = self._encode_value(value)
        
        if key not in self.store:
            self.store[key] = {}
        if not isinstance(self.store[key], dict):
            raise RedisError("Key contains a non-hash value")
            
        is_new = field not in self.store[key]
        self.store[key][field] = value
        return int(is_new)
    
    async def hget(
        self,
        key: Union[str, bytes],
        field: Union[str, bytes]
    ) -> Optional[bytes]:
        """Get value of hash field."""
        key = self._encode_key(key)
        field = self._encode_key(field)
        
        if key not in self.store:
            return None
        if not isinstance(self.store[key], dict):
            raise RedisError("Key contains a non-hash value")
            
        value = self.store[key].get(field)
        return self._decode_value(value)
    
    async def hgetall(self, key: Union[str, bytes]) -> Dict[bytes, bytes]:
        """Get all fields and values in a hash."""
        key = self._encode_key(key)
        
        if key not in self.store:
            return {}
        if not isinstance(self.store[key], dict):
            raise RedisError("Key contains a non-hash value")
            
        return {
            field.encode('utf-8'): self._decode_value(value)
            for field, value in self.store[key].items()
        }
    
    async def hincrby(
        self,
        key: Union[str, bytes],
        field: Union[str, bytes],
        amount: int = 1
    ) -> int:
        """Increment value of hash field by amount."""
        key = self._encode_key(key)
        field = self._encode_key(field)
        
        if key not in self.store:
            self.store[key] = {}
        if not isinstance(self.store[key], dict):
            raise RedisError("Key contains a non-hash value")
            
        if field not in self.store[key]:
            self.store[key][field] = b"0"
            
        try:
            value = int(self.store[key][field].decode('utf-8'))
            value += amount
            self.store[key][field] = str(value).encode('utf-8')
            return value
        except (ValueError, TypeError):
            raise RedisError("Hash field value is not an integer")
    
    async def watch(self, *keys: Union[str, bytes]) -> bool:
        """Watch keys for changes."""
        if self.in_transaction:
            raise RedisError("Watch after multi not allowed")
        for key in keys:
            key = self._encode_key(key)
            self.watched_keys[key] = self.store.get(key)
        return True
    
    async def multi(self) -> bool:
        """Start a transaction."""
        if self.in_transaction:
            raise RedisError("Transaction already in progress")
        self.in_transaction = True
        self.transaction_store = self.store.copy()
        self.transaction_expiry = self.expiry.copy()
        self.transaction_commands = []
        return True
    
    async def execute(self) -> List[Any]:
        """Execute transaction."""
        if not self.in_transaction:
            raise RedisError("No transaction in progress")
        
        # Check watched keys
        for key, old_value in self.watched_keys.items():
            if self.store.get(key) != old_value:
                self.in_transaction = False
                self.transaction_store = None
                self.transaction_expiry = None
                self.transaction_commands = []
                self.watched_keys.clear()
                raise WatchError("Watched key changed")
        
        try:
            results = []
            for cmd in self.transaction_commands:
                result = await cmd()
                results.append(result)
            
            # Commit transaction
            self.store = self.transaction_store
            self.expiry = self.transaction_expiry
            
            # Clear transaction state
            self.in_transaction = False
            self.transaction_store = None
            self.transaction_expiry = None
            self.transaction_commands = []
            self.watched_keys.clear()
            
            return results
            
        except Exception as e:
            # Rollback on error
            self.in_transaction = False
            self.transaction_store = None
            self.transaction_expiry = None
            self.transaction_commands = []
            self.watched_keys.clear()
            raise e
    
    async def discard(self) -> bool:
        """Discard transaction."""
        if not self.in_transaction:
            raise RedisError("No transaction in progress")
        self.in_transaction = False
        self.transaction_store = None
        self.transaction_expiry = None
        self.transaction_commands = []
        self.watched_keys.clear()
        return True
    
    async def flushdb(self) -> bool:
        """Clear current database."""
        self.store.clear()
        self.expiry.clear()
        self.watched_keys.clear()
        self.in_transaction = False
        self.transaction_store = None
        self.transaction_expiry = None
        self.transaction_commands = []
        return True
    
    async def aclose(self) -> None:
        """Close Redis connection."""
        await self.flushdb()
    
    def pipeline(self) -> 'MockRedisPipeline':
        """Get pipeline for batched commands."""
        return MockRedisPipeline(self)

class MockRedisPipeline:
    """Mock Redis pipeline for batched commands."""
    
    def __init__(self, redis: MockRedis):
        self.redis = redis
        self.commands: List[Callable[[], Awaitable[Any]]] = []
    
    async def execute(self) -> List[Any]:
        """Execute batched commands."""
        results = []
        for cmd in self.commands:
            results.append(await cmd())
        self.commands = []
        return results
    
    async def get(self, key: Union[str, bytes]) -> None:
        """Queue get command."""
        self.commands.append(lambda: self.redis.get(key))
    
    async def set(
        self,
        key: Union[str, bytes],
        value: Union[str, bytes],
        ex: Optional[int] = None
    ) -> None:
        """Queue set command."""
        self.commands.append(lambda: self.redis.set(key, value, ex=ex))
    
    async def delete(self, *keys: Union[str, bytes]) -> None:
        """Queue delete command."""
        self.commands.append(lambda: self.redis.delete(*keys))
    
    async def incr(self, key: Union[str, bytes]) -> None:
        """Queue incr command."""
        self.commands.append(lambda: self.redis.incr(key))
    
    async def decr(self, key: Union[str, bytes]) -> None:
        """Queue decr command."""
        self.commands.append(lambda: self.redis.decr(key))
    
    async def expire(self, key: Union[str, bytes], seconds: int) -> None:
        """Queue expire command."""
        self.commands.append(lambda: self.redis.expire(key, seconds))
    
    async def watch(self, *keys: Union[str, bytes]) -> None:
        """Queue watch command."""
        self.commands.append(lambda: self.redis.watch(*keys))
    
    async def multi(self) -> None:
        """Queue multi command."""
        self.commands.append(lambda: self.redis.multi())
    
    async def execute_transaction(self) -> None:
        """Queue execute command."""
        self.commands.append(lambda: self.redis.execute())
    
    async def discard(self) -> None:
        """Queue discard command."""
        self.commands.append(lambda: self.redis.discard())
    
    async def lpush(self, key: Union[str, bytes], *values: Union[str, bytes]) -> None:
        """Queue lpush command."""
        self.commands.append(lambda: self.redis.lpush(key, *values))
    
    async def rpush(self, key: Union[str, bytes], *values: Union[str, bytes]) -> None:
        """Queue rpush command."""
        self.commands.append(lambda: self.redis.rpush(key, *values))
    
    async def lrange(
        self,
        key: Union[str, bytes],
        start: int,
        stop: int
    ) -> None:
        """Queue lrange command."""
        self.commands.append(lambda: self.redis.lrange(key, start, stop))
    
    async def llen(self, key: Union[str, bytes]) -> None:
        """Queue llen command."""
        self.commands.append(lambda: self.redis.llen(key))
    
    async def keys(self, pattern: Union[str, bytes]) -> None:
        """Queue keys command."""
        self.commands.append(lambda: self.redis.keys(pattern))
    
    async def hset(
        self,
        key: Union[str, bytes],
        field: Union[str, bytes],
        value: Union[str, bytes, int]
    ) -> None:
        """Queue hset command."""
        self.commands.append(lambda: self.redis.hset(key, field, value))
    
    async def hget(
        self,
        key: Union[str, bytes],
        field: Union[str, bytes]
    ) -> None:
        """Queue hget command."""
        self.commands.append(lambda: self.redis.hget(key, field))
    
    async def hgetall(self, key: Union[str, bytes]) -> None:
        """Queue hgetall command."""
        self.commands.append(lambda: self.redis.hgetall(key))
    
    async def hincrby(
        self,
        key: Union[str, bytes],
        field: Union[str, bytes],
        amount: int = 1
    ) -> None:
        """Queue hincrby command."""
        self.commands.append(lambda: self.redis.hincrby(key, field, amount))
