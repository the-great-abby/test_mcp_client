"""
Mock Redis implementation for testing.
"""
from typing import Any, Dict, List, Optional, Union, Set, AsyncGenerator
import json
import asyncio
from datetime import datetime, timedelta
import time
import fnmatch
from redis.asyncio import Redis
import re
from redis.exceptions import WatchError

class MockRedisPipeline:
    """Mock Redis pipeline with async context manager support."""
    
    def __init__(self, redis_instance):
        self.redis = redis_instance
        self.commands = []
        self.in_transaction = False
        self.watched_keys = set()
        
    async def __aenter__(self):
        """Enter async context."""
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context."""
        if not exc_type:
            await self.execute()
        self.commands = []
        
    async def execute_command(self, cmd: str, *args, **kwargs):
        """Add command to pipeline."""
        self.commands.append((cmd, args, kwargs))
        return self
        
    async def hincrby(self, key: str, field: str, amount: int = 1):
        """Increment hash field by amount."""
        return await self.execute_command("HINCRBY", key, field, amount)
        
    async def hgetall(self, key: str):
        """Get all fields and values in hash."""
        return await self.execute_command("HGETALL", key)
        
    async def hget(self, key: str, field: str):
        """Get hash field value."""
        return await self.execute_command("HGET", key, field)
        
    async def hset(self, key: str, field: str, value: Any):
        """Set hash field value."""
        return await self.execute_command("HSET", key, field, value)
        
    async def expire(self, key: str, seconds: int):
        """Set expiry on key."""
        return await self.execute_command("EXPIRE", key, seconds)

    async def delete(self, *keys: str):
        """Delete one or more keys."""
        return await self.execute_command("DELETE", *keys)

    async def watch(self, *keys: str):
        """Watch keys for changes."""
        self.watched_keys.update(keys)
        return await self.execute_command("WATCH", *keys)

    async def multi(self):
        """Start a transaction."""
        self.in_transaction = True
        return await self.execute_command("MULTI")

    async def execute(self):
        """Execute all commands in pipeline."""
        results = []
        try:
            for cmd, args, kwargs in self.commands:
                if cmd == "HINCRBY":
                    key, field, amount = args
                    value = await self.redis.hincrby(key, field, amount)
                    results.append(value)
                elif cmd == "HGETALL":
                    key = args[0]
                    value = await self.redis.hgetall(key)
                    results.append(value)
                elif cmd == "HGET":
                    key, field = args
                    value = await self.redis.hget(key, field)
                    results.append(value)
                elif cmd == "HSET":
                    key, field, value = args
                    result = await self.redis.hset(key, field, value)
                    results.append(result)
                elif cmd == "EXPIRE":
                    key, seconds = args
                    value = await self.redis.expire(key, seconds)
                    results.append(value)
                elif cmd == "DELETE":
                    value = await self.redis.delete(*args)
                    results.append(value)
                elif cmd == "WATCH":
                    value = await self.redis.watch(*args)
                    results.append(value)
                elif cmd == "MULTI":
                    value = await self.redis.multi()
                    results.append(value)
                else:
                    results.append(None)
        except Exception as e:
            if self.in_transaction:
                # In a transaction, any error aborts all commands
                results = []
                raise e
            # Outside transaction, continue with other commands
            results.append(None)
            
        # Reset pipeline state
        self.commands = []
        self.in_transaction = False
        return results

class MockRedis:
    """Mock Redis implementation for testing."""
    
    def __init__(self):
        """Initialize mock Redis."""
        self.store: Dict[str, bytes] = {}
        self.expiry: Dict[str, float] = {}
        self._transaction_store: Optional[Dict[str, bytes]] = None
        self._transaction_expiry: Optional[Dict[str, float]] = None
        self._in_transaction = False
        self._watch_keys: Set[str] = set()
        self._redis = self
        
    @property
    async def redis(self):
        """Get Redis client instance."""
        return self._redis
        
    def _encode(self, value: Any) -> bytes:
        """Encode value to bytes."""
        if isinstance(value, bytes):
            return value
        if isinstance(value, (int, float)):
            return str(value).encode('utf-8')
        if isinstance(value, str):
            return value.encode('utf-8')
        # For complex types, use JSON encoding
        return json.dumps(value).encode('utf-8')
        
    def _decode(self, value: Optional[bytes]) -> Optional[Any]:
        """Decode bytes to string or original type."""
        if value is None:
            return None
        try:
            # Try to decode as JSON first
            return json.loads(value.decode('utf-8'))
        except json.JSONDecodeError:
            # If not JSON, return as string
            try:
                # Try to convert to number if possible
                decoded = value.decode('utf-8')
                if decoded.isdigit():
                    return int(decoded)
                if decoded.replace('.', '', 1).isdigit():
                    return float(decoded)
                return decoded
            except:
                return value.decode('utf-8')
        
    def _check_expiry(self, key: str) -> None:
        """Check if key has expired."""
        if key in self.expiry and time.time() > self.expiry[key]:
            del self.store[key]
            del self.expiry[key]
            
    async def get(self, key: str) -> Optional[bytes]:
        """Get value for key."""
        self._check_expiry(key)
        return self.store.get(key)
        
    async def set(
        self,
        key: str,
        value: Any,
        ex: Optional[int] = None,
        px: Optional[int] = None
    ) -> bool:
        """Set key to value with optional expiry."""
        encoded_value = self._encode(value)
        self.store[key] = encoded_value
        
        if ex is not None:
            self.expiry[key] = time.time() + ex
        elif px is not None:
            self.expiry[key] = time.time() + (px / 1000.0)
            
        return True
        
    async def delete(self, *keys: str) -> int:
        """Delete one or more keys."""
        count = 0
        for key in keys:
            if key in self.store:
                del self.store[key]
                if key in self.expiry:
                    del self.expiry[key]
                count += 1
        return count
        
    async def exists(self, key: str) -> int:
        """Check if key exists."""
        self._check_expiry(key)
        return int(key in self.store)
        
    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiry on key."""
        if key not in self.store:
            return False
        self.expiry[key] = time.time() + seconds
        return True
        
    async def ttl(self, key: str) -> int:
        """Get time to live for key."""
        if key not in self.store:
            return -2
        if key not in self.expiry:
            return -1
        ttl = int(self.expiry[key] - time.time())
        return ttl if ttl > 0 else -2
        
    async def keys(self, pattern: str = "*") -> List[bytes]:
        """Get all keys matching pattern."""
        # Remove expired keys first
        for key in list(self.store.keys()):
            self._check_expiry(key)
            
        # Convert glob pattern to regex
        regex = fnmatch.translate(pattern)
        return [key.encode('utf-8') for key in self.store.keys() if re.match(regex, key)]
        
    async def incr(self, key: str) -> int:
        """Increment value at key."""
        if key not in self.store:
            value = 1
        else:
            value = int(self._decode(self.store[key])) + 1
        await self.set(key, value)
        return value
        
    async def decr(self, key: str) -> int:
        """Decrement value at key."""
        if key not in self.store:
            value = -1
        else:
            value = int(self._decode(self.store[key])) - 1
        await self.set(key, value)
        return value
        
    async def lpush(self, key: str, *values: Any) -> int:
        """Push values to start of list."""
        if key not in self.store:
            current_list = []
        else:
            current_list = self._decode(self.store[key]) or []
            
        if not isinstance(current_list, list):
            raise Exception("Value at key is not a list")
            
        # Add new values to start
        for value in values:
            current_list.insert(0, value)
            
        await self.set(key, current_list)
        return len(current_list)
        
    async def rpush(self, key: str, *values: Any) -> int:
        """Push values to end of list."""
        if key not in self.store:
            current_list = []
        else:
            current_list = self._decode(self.store[key]) or []
            
        if not isinstance(current_list, list):
            raise Exception("Value at key is not a list")
            
        # Add new values to end
        current_list.extend(values)
            
        await self.set(key, current_list)
        return len(current_list)
        
    async def lrange(self, key: str, start: int, stop: int) -> List[bytes]:
        """Get range of values from list."""
        if key not in self.store:
            return []
            
        current_list = self._decode(self.store[key]) or []
        if not isinstance(current_list, list):
            raise Exception("Value at key is not a list")
            
        # Handle negative indices
        if start < 0:
            start = max(len(current_list) + start, 0)
        if stop < 0:
            stop = max(len(current_list) + stop + 1, 0)
        elif stop > 0:
            stop = min(stop + 1, len(current_list))
            
        return [self._encode(x) for x in current_list[start:stop]]
        
    async def watch(self, *keys: str) -> bool:
        """Watch keys for changes."""
        self._watch_keys.update(keys)
        return True
        
    async def multi(self) -> None:
        """Start a transaction."""
        if self._in_transaction:
            raise Exception("Transaction already in progress")
        self._in_transaction = True
        self._transaction_store = self.store.copy()
        self._transaction_expiry = self.expiry.copy()
        
    async def exec(self) -> Optional[List[Any]]:
        """Execute transaction."""
        if not self._in_transaction:
            raise Exception("No transaction in progress")
            
        # Check if watched keys have changed
        for key in self._watch_keys:
            if (key in self.store and key not in self._transaction_store) or \
               (key not in self.store and key in self._transaction_store) or \
               (key in self.store and key in self._transaction_store and \
                self.store[key] != self._transaction_store[key]):
                # Watched key changed, abort transaction
                self._in_transaction = False
                self._transaction_store = None
                self._transaction_expiry = None
                self._watch_keys.clear()
                return None
                
        # No changes to watched keys, commit transaction
        self.store = self._transaction_store
        self.expiry = self._transaction_expiry
        self._in_transaction = False
        self._transaction_store = None
        self._transaction_expiry = None
        self._watch_keys.clear()
        
        return []
        
    async def discard(self) -> bool:
        """Discard transaction."""
        if not self._in_transaction:
            raise Exception("No transaction in progress")
            
        self._in_transaction = False
        self._transaction_store = None
        self._transaction_expiry = None
        self._watch_keys.clear()
        return True
        
    async def aclose(self) -> None:
        """Close Redis connection."""
        self.store.clear()
        self.expiry.clear()
        self._watch_keys.clear()
        
    async def clear(self) -> None:
        """Clear all data."""
        self.store.clear()
        self.expiry.clear()
        
    async def flushdb(self) -> bool:
        """Clear current database."""
        await self.clear()
        return True
        
    async def flushall(self) -> bool:
        """Clear all databases."""
        await self.clear()
        return True
        
    async def pipeline(self) -> 'MockRedisPipeline':
        """Create pipeline for batching commands."""
        return MockRedisPipeline(self)
        
    async def hget(self, key: str, field: str) -> Optional[bytes]:
        """Get hash field value."""
        if key not in self.store:
            return None
        hash_data = self._decode(self.store[key]) or {}
        if not isinstance(hash_data, dict):
            raise Exception("Value at key is not a hash")
        value = hash_data.get(field)
        return self._encode(value) if value is not None else None
        
    async def hset(self, key: str, field: str, value: Any) -> int:
        """Set hash field value."""
        if key not in self.store:
            hash_data = {}
        else:
            hash_data = self._decode(self.store[key]) or {}
            
        if not isinstance(hash_data, dict):
            raise Exception("Value at key is not a hash")
            
        is_new = field not in hash_data
        hash_data[field] = value
        await self.set(key, hash_data)
        return int(is_new)
        
    async def hincrby(self, key: str, field: str, amount: int = 1) -> int:
        """Increment hash field by amount."""
        if key not in self.store:
            hash_data = {}
        else:
            hash_data = self._decode(self.store[key]) or {}
            
        if not isinstance(hash_data, dict):
            raise Exception("Value at key is not a hash")
            
        current = int(hash_data.get(field, 0))
        new_value = current + amount
        hash_data[field] = new_value
        await self.set(key, hash_data)
        return new_value
        
    async def hgetall(self, key: str) -> Dict[bytes, bytes]:
        """Get all fields and values in hash."""
        if key not in self.store:
            return {}
            
        hash_data = self._decode(self.store[key]) or {}
        if not isinstance(hash_data, dict):
            raise Exception("Value at key is not a hash")
            
        return {
            field.encode('utf-8'): self._encode(value)
            for field, value in hash_data.items()
        }
        
    async def scan_iter(self, match: Optional[str] = None) -> AsyncGenerator[str, None]:
        """Scan through keys."""
        pattern = match or "*"
        regex = fnmatch.translate(pattern)
        for key in self.store:
            if re.match(regex, key):
                yield key 