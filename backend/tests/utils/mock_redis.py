"""Mock Redis implementation for testing."""
import asyncio
import time
import re
from typing import Dict, List, Any, Optional, Set, Union, Callable
from redis.exceptions import WatchError, RedisError
import json
import fnmatch
import copy

class MockRedis:
    """Mock Redis implementation for testing."""
    
    def __init__(self):
        """Initialize mock Redis."""
        self._data: Dict[bytes, Any] = {}
        self._expires: Dict[bytes, float] = {}
        self._watched_keys: Set[bytes] = set()
        self._transaction_data: Dict[bytes, Any] = {}
        self._in_transaction = False
        self._pipeline_commands: List[tuple] = []
        self._transaction_failed = False
        self._error_mode = False
        self._watched_values: Dict[bytes, Any] = {}
        self._lists: Dict[bytes, List[bytes]] = {}
        self._type_handlers: Dict[type, Callable] = {
            dict: self._handle_dict,
            list: self._handle_list,
            str: self._handle_str,
            int: self._handle_int,
            float: self._handle_float,
            bytes: self._handle_bytes
        }
        self._pubsub_channels: Dict[str, List[asyncio.Queue]] = {}
    
    def _encode_key(self, key: Union[str, bytes]) -> bytes:
        """Encode key to bytes."""
        if isinstance(key, str):
            return key.encode()
        return key
    
    def _encode_value(self, value: Any) -> bytes:
        """Encode value to bytes."""
        if isinstance(value, bytes):
            return value
        if isinstance(value, (int, float, bool)):
            return str(int(value) if isinstance(value, bool) else value).encode()
        if isinstance(value, str):
            return value.encode()
        raise RedisError(f"Cannot encode value of type {type(value)}")
    
    def _decode_value(self, value: bytes) -> Any:
        """Decode bytes to value."""
        try:
            return value.decode()
        except:
            return value
    
    def _check_expiry(self, key: bytes) -> bool:
        """Check if key has expired."""
        if key in self._expires:
            if time.time() > self._expires[key]:
                del self._data[key]
                del self._expires[key]
                return True
        return False
    
    def _check_type(self, key: bytes, expected_type: type) -> None:
        """Check if value is of expected type, raise RedisError if not."""
        if key in self._data:
            value = self._data[key]
            if not isinstance(value, expected_type):
                raise RedisError(f"Key contains a non-{expected_type.__name__} value")
    
    def _handle_dict(self, value: Any) -> dict:
        """Convert value to dict."""
        if isinstance(value, bytes):
            try:
                return json.loads(value.decode())
            except json.JSONDecodeError:
                return {}
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return {}
        if isinstance(value, dict):
            return value
        raise RedisError("Cannot convert value to dict")
    
    def _handle_list(self, value: Any) -> list:
        """Convert value to list."""
        if isinstance(value, bytes):
            try:
                return json.loads(value.decode())
            except json.JSONDecodeError:
                return [value]
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return [value.encode()]
        if isinstance(value, list):
            return value
        return [self._encode_value(value)]
    
    def _handle_str(self, value: Any) -> str:
        """Convert value to str."""
        if isinstance(value, bytes):
            return value.decode()
        return str(value)
    
    def _handle_int(self, value: Any) -> int:
        """Convert value to int."""
        if isinstance(value, bytes):
            return int(value.decode())
        if isinstance(value, str):
            return int(value)
        if isinstance(value, (int, float)):
            return int(value)
        raise RedisError("Cannot convert value to int")
    
    def _handle_float(self, value: Any) -> float:
        """Convert value to float."""
        if isinstance(value, bytes):
            return float(value.decode())
        if isinstance(value, str):
            return float(value)
        if isinstance(value, (int, float)):
            return float(value)
        raise RedisError("Cannot convert value to float")
    
    def _handle_bytes(self, value: Any) -> bytes:
        """Convert value to bytes."""
        if isinstance(value, str):
            return value.encode()
        if isinstance(value, (int, float)):
            return str(value).encode()
        if isinstance(value, bytes):
            return value
        raise RedisError("Cannot convert value to bytes")
    
    def enable_errors(self) -> None:
        """Enable error mode for testing error handling."""
        self._error_mode = True
    
    def disable_errors(self) -> None:
        """Disable error mode."""
        self._error_mode = False
    
    async def set(
        self,
        key: Union[str, bytes],
        value: Any,
        ex: Optional[int] = None
    ) -> bool:
        """Set key to value with optional expiry. Always store as bytes."""
        if self._error_mode:
            raise RedisError("Redis error (mock)")
        key = self._encode_key(key)
        value = self._encode_value(value)  # Always store as bytes
        if self._in_transaction:
            # Queue the set operation for later execution
            self._pipeline_commands.append(("set", key, value, ex))
            return True
        self._data[key] = value
        if ex is not None:
            if ex <= 0:
                raise RedisError("Invalid expire time")
            self._expires[key] = time.time() + ex
        return True
    
    async def get(self, key: Union[str, bytes]) -> Optional[bytes]:
        """Get value for key. Always return bytes or None."""
        if self._error_mode:
            raise RedisError("Redis error (mock)")
        key = self._encode_key(key)
        if self._in_transaction:
            self._pipeline_commands.append(("get", key))
            return None
        if self._check_expiry(key):
            return None
        value = self._data.get(key)
        if value is None:
            return None
        if not isinstance(value, bytes):
            return self._encode_value(value)
        return value

    async def delete(self, *keys: bytes) -> int:
        """Delete keys and return the count of deleted keys. Debug output for test diagnosis."""
        if self._error_mode:
            raise RedisError("Redis error (mock)")
        if self._in_transaction:
            for key in keys:
                self._pipeline_commands.append(("delete", key))
            return len(keys)
        count = 0
        for key in keys:
            key = self._encode_key(key)
            if key in self._data:
                del self._data[key]
                count += 1
        print(f"[MockRedis.delete] Deleted {count} of {len(keys)} keys: {keys}")
        return count
    
    async def expire(self, key: Union[str, bytes], seconds: int) -> bool:
        """Set a key's time to live in seconds."""
        if self._error_mode:
            raise RedisError("Redis error (mock)")
        key = self._encode_key(key)
        if seconds <= 0:
            raise RedisError("Invalid expire time")
        if self._in_transaction:
            self._pipeline_commands.append(("expire", key, seconds))
            return True
        if key not in self._data:
            return False
        if key in self._watched_keys and key in self._watched_values:
            if self._watched_values[key] != self._data.get(key):
                raise WatchError()
        self._expires[key] = time.time() + seconds
        return True
    
    async def hset(self, key: Union[str, bytes], field: Any, value: Any) -> int:
        """Set hash field to value."""
        if self._error_mode:
            raise RedisError("Redis error (mock)")
        key = self._encode_key(key)
        field = self._encode_key(field)
        value = self._encode_value(value)
        if self._in_transaction:
            self._pipeline_commands.append(("hset", key, field, value))
            return 1
        if key not in self._data:
            self._data[key] = {}
        try:
            self._check_type(key, dict)
        except RedisError:
            raise RedisError("Key contains a non-hash value")
        if key in self._watched_keys and key in self._watched_values:
            if self._watched_values[key] != self._data.get(key):
                raise WatchError()
        is_new = field not in self._data[key]
        self._data[key][field] = value
        return 1 if is_new else 0
    
    async def hget(self, key: Union[str, bytes], field: Any) -> Any:
        """Get value of hash field."""
        if self._error_mode:
            raise RedisError("Redis error (mock)")
            
        key = self._encode_key(key)
        field = self._encode_key(field)
        
        try:
            self._check_type(key, dict)
        except RedisError:
            raise RedisError("Key contains a non-hash value")
            
        if self._in_transaction:
            self._pipeline_commands.append(("hget", key, field))
            return None
            
        if key not in self._data:
            return None
            
        return self._data[key].get(field)
    
    async def hgetall(self, key: Union[str, bytes]) -> dict:
        """Get all fields and values in hash."""
        if self._error_mode:
            raise RedisError("Redis error (mock)")
            
        key = self._encode_key(key)
        try:
            self._check_type(key, dict)
        except RedisError:
            raise RedisError("Key contains a non-hash value")
            
        if self._in_transaction:
            self._pipeline_commands.append(("hgetall", key))
            return {}
            
        if key not in self._data:
            return {}
            
        return self._data[key]
    
    async def hincrby(
        self,
        key: Union[str, bytes],
        field: Any,
        amount: int = 1
    ) -> int:
        """Increment the integer value of a hash field by the given number."""
        if self._error_mode:
            raise RedisError("Redis error (mock)")
        key = self._encode_key(key)
        field = self._encode_key(field)
        if self._in_transaction:
            self._pipeline_commands.append(("hincrby", key, field, amount))
            return amount
        try:
            self._check_type(key, dict)
        except RedisError:
            raise RedisError("Key contains a non-hash value")
        if key in self._watched_keys and key in self._watched_values:
            if self._watched_values[key] != self._data.get(key):
                raise WatchError()
        if key not in self._data:
            self._data[key] = {}
        if field not in self._data[key]:
            self._data[key][field] = b"0"
        try:
            current = int(self._data[key][field].decode())
            new_value = current + amount
            self._data[key][field] = str(new_value).encode()
            return new_value
        except (ValueError, UnicodeDecodeError):
            raise RedisError("Hash field value is not an integer")
    
    async def lpush(self, key: Union[str, bytes], *values: Any) -> int:
        """Push values to the head of a list."""
        key = self._encode_key(key)
        if self._in_transaction:
            self._pipeline_commands.append(("lpush", key, *values))
            return len(values)
        if key in self._data and not isinstance(self._data[key], list):
            raise RedisError("Key contains a non-list value")
        if key not in self._lists:
            self._lists[key] = []
        for value in values:
            self._lists[key].insert(0, self._encode_value(value))
        self._data[key] = self._lists[key]
        return len(self._lists[key])
    
    async def lpop(self, key: bytes) -> Optional[bytes]:
        """Pop value from the head of a list and return as bytes."""
        if key not in self._lists or not self._lists[key]:
            return None
        value = self._lists[key].pop(0)
        return value if isinstance(value, bytes) else value.encode()
    
    async def lrange(self, key: Union[str, bytes], start: int, stop: int) -> list:
        """Get a range of values from a list, all as bytes."""
        key = self._encode_key(key)
        # Type check: must be a list
        if key in self._data and not isinstance(self._data[key], list):
            raise RedisError("Key contains a non-list value")
        if key not in self._lists:
            return []
        l = self._lists[key]
        list_len = len(l)
        if start < 0:
            start = max(list_len + start, 0)
        if stop < 0:
            stop = list_len + stop
        stop = min(stop, list_len - 1)
        if start > stop or start >= list_len:
            return []
        result = l[start:stop+1]
        return [item if isinstance(item, bytes) else self._encode_value(item) for item in result]
    
    async def keys(self, pattern: str = "*") -> list:
        """Return a list of keys matching the given glob-style pattern."""
        all_keys = list(self._data.keys())
        return [k for k in all_keys if fnmatch.fnmatch(k.decode() if isinstance(k, bytes) else k, pattern)]
    
    async def scan(self, cursor: int = 0, match: str = "*", count: int = 10) -> tuple:
        """Iterate the set of keys matching a pattern. Returns (next_cursor, keys)."""
        all_keys = [k for k in self._data.keys() if fnmatch.fnmatch(k.decode() if isinstance(k, bytes) else k, match)]
        # Simple implementation: return a slice of keys, no real cursor logic
        end = cursor + count
        next_cursor = 0 if end >= len(all_keys) else end
        return next_cursor, all_keys[cursor:end]
    
    def pipeline(self):
        """Create a pipeline for executing multiple commands atomically."""
        return MockPipeline(self)
    
    async def watch(self, *keys: str):
        """Return a transaction object with watched keys/values set."""
        watched_keys = set()
        watched_values = dict()
        for key in keys:
            encoded_key = self._encode_key(key)
            watched_keys.add(encoded_key)
            watched_values[encoded_key] = copy.deepcopy(self._data.get(encoded_key))
        return MockTransaction(self, watched_keys, watched_values)
    
    async def unwatch(self) -> bool:
        """Forget about all watched keys."""
        if self._error_mode:
            raise RedisError("Redis error (mock)")
        self._watched_keys.clear()
        self._watched_values.clear()
        return True
    
    def multi(self):
        """Start a new transaction object."""
        return MockTransaction(self)
    
    async def execute(self) -> list:
        """Execute all queued commands in a transaction. Simulate watch logic."""
        if self._error_mode:
            self._reset_transaction_state()
            raise RedisError("Redis error (mock)")
        if not self._in_transaction:
            raise RedisError("Not in transaction")
        # Check watched keys before executing
        for key in self._watched_keys:
            if self._data.get(key) != self._watched_values.get(key):
                self._reset_transaction_state()
                raise WatchError("Watched key changed before transaction execution")
        results = []
        try:
            for cmd in self._pipeline_commands:
                method_name = cmd[0]
                args = cmd[1:]
                method = getattr(self, f"_apply_{method_name}", None)
                if method is not None:
                    result = await method(*args)
                else:
                    # Fallback to the normal method if no _apply_ version exists
                    method = getattr(self, method_name)
                    result = await method(*args)
                results.append(result)
        except Exception as e:
            self._reset_transaction_state()
            raise e
        self._reset_transaction_state()
        return results
    
    async def exists(self, *keys: bytes) -> int:
        """Check if keys exist."""
        count = 0
        for key in keys:
            if key in self._data and (key not in self._expires or self._expires[key] > time.time()):
                count += 1
        return count
    
    async def rpush(self, key: Union[str, bytes], *values: Any) -> int:
        """Push values to the tail of a list."""
        key = self._encode_key(key)
        if self._in_transaction:
            self._pipeline_commands.append(("rpush", key, *values))
            return len(values)
        if key in self._data and not isinstance(self._data[key], list):
            raise RedisError("Key contains a non-list value")
        if key not in self._lists:
            self._lists[key] = []
        for value in values:
            self._lists[key].append(self._encode_value(value))
        self._data[key] = self._lists[key]
        return len(self._lists[key])
    
    async def rpop(self, key: bytes) -> Optional[bytes]:
        """Pop value from the tail of a list and return as bytes."""
        if key not in self._lists or not self._lists[key]:
            return None
        value = self._lists[key].pop()
        return value if isinstance(value, bytes) else value.encode()

    async def publish(self, channel: str, message: str) -> int:
        """Publish a message to a channel. Returns number of subscribers."""
        queues = self._pubsub_channels.get(channel, [])
        for queue in queues:
            await queue.put(message)
        return len(queues)

    async def subscribe(self, channel: str) -> asyncio.Queue:
        """Subscribe to a channel. Returns an asyncio.Queue for messages."""
        queue = asyncio.Queue()
        self._pubsub_channels.setdefault(channel, []).append(queue)
        return queue

    async def unsubscribe(self, channel: str, queue: asyncio.Queue) -> None:
        """Unsubscribe a queue from a channel."""
        if channel in self._pubsub_channels:
            self._pubsub_channels[channel].remove(queue)
            if not self._pubsub_channels[channel]:
                del self._pubsub_channels[channel]

    async def ttl(self, key: Union[str, bytes]) -> int:
        """Return time-to-live in seconds. -2 if key does not exist, -1 if no expiry."""
        key = self._encode_key(key)
        if key not in self._data:
            return -2
        if key not in self._expires:
            return -1
        ttl = int(self._expires[key] - time.time())
        return ttl if ttl > 0 else -2

    async def pttl(self, key: Union[str, bytes]) -> int:
        """Return time-to-live in milliseconds. -2 if key does not exist, -1 if no expiry."""
        key = self._encode_key(key)
        if key not in self._data:
            return -2
        if key not in self._expires:
            return -1
        pttl = int((self._expires[key] - time.time()) * 1000)
        return pttl if pttl > 0 else -2 

    async def incr(self, key: Union[str, bytes]) -> int:
        """Atomically increment the integer value of a key by 1. Create key if missing, store as bytes, return new value."""
        if self._error_mode:
            raise RedisError("Redis error (mock)")
        key = self._encode_key(key)
        if self._in_transaction:
            self._pipeline_commands.append(("incr", key))
            return 1
        if key not in self._data:
            self._data[key] = b"0"
        try:
            value = int(self._data[key].decode())
        except Exception:
            raise RedisError("Value is not an integer")
        value += 1
        self._data[key] = str(value).encode()
        return value

    async def decr(self, key: Union[str, bytes]) -> int:
        """Atomically decrement the integer value of a key by 1. Create key if missing, store as bytes, return new value."""
        if self._error_mode:
            raise RedisError("Redis error (mock)")
        key = self._encode_key(key)
        if self._in_transaction:
            self._pipeline_commands.append(("decr", key))
            return -1
        if key not in self._data:
            self._data[key] = b"0"
        try:
            value = int(self._data[key].decode())
        except Exception:
            raise RedisError("Value is not an integer")
        value -= 1
        self._data[key] = str(value).encode()
        return value

    async def incrby(self, key: Union[str, bytes], amount: int = 1) -> int:
        """Atomically increment the integer value of a key by the given amount."""
        if self._error_mode:
            raise RedisError("Redis error (mock)")
        key = self._encode_key(key)
        if self._in_transaction:
            self._pipeline_commands.append(("incrby", key, amount))
            return amount
        if key not in self._data:
            self._data[key] = b"0"
        try:
            value = int(self._data[key].decode())
        except Exception:
            raise RedisError("Value is not an integer")
        value += amount
        self._data[key] = str(value).encode()
        return value

    async def invalid_command(self, *args, **kwargs):
        raise RedisError("Invalid command")

    def _reset_transaction_state(self):
        """Reset transaction and watch state after error or completion."""
        self._in_transaction = False
        self._pipeline_commands = []
        self._transaction_failed = False
        self._watched_keys.clear()
        self._watched_values.clear()

    # Add a private method to apply set directly to self._data
    async def _apply_set(self, key, value, ex=None):
        self._data[key] = value
        if ex is not None:
            if ex <= 0:
                raise RedisError("Invalid expire time")
            self._expires[key] = time.time() + ex
        return True

    # --- _apply_* methods for transaction execution ---
    async def _apply_delete(self, key):
        if key in self._data:
            del self._data[key]
            return 1
        return 0

    async def _apply_expire(self, key, seconds):
        if key not in self._data:
            return False
        self._expires[key] = time.time() + seconds
        return True

    async def _apply_hset(self, key, field, value):
        if key not in self._data:
            self._data[key] = {}
        self._data[key][field] = value
        return 1

    async def _apply_hincrby(self, key, field, amount):
        if key not in self._data:
            self._data[key] = {}
        if field not in self._data[key]:
            self._data[key][field] = b"0"
        current = int(self._data[key][field].decode())
        new_value = current + amount
        self._data[key][field] = str(new_value).encode()
        return new_value

    async def _apply_lpush(self, key, *values):
        if key not in self._lists:
            self._lists[key] = []
        for value in values:
            self._lists[key].insert(0, self._encode_value(value))
        self._data[key] = self._lists[key]
        return len(self._lists[key])

    async def _apply_rpush(self, key, *values):
        if key not in self._lists:
            self._lists[key] = []
        for value in values:
            self._lists[key].append(self._encode_value(value))
        self._data[key] = self._lists[key]
        return len(self._lists[key])

    async def _apply_incr(self, key):
        if key not in self._data:
            self._data[key] = b"0"
        value = int(self._data[key].decode()) + 1
        self._data[key] = str(value).encode()
        return value

    async def _apply_decr(self, key):
        if key not in self._data:
            self._data[key] = b"0"
        value = int(self._data[key].decode()) - 1
        self._data[key] = str(value).encode()
        return value

    async def _apply_incrby(self, key, amount):
        if key not in self._data:
            self._data[key] = b"0"
        value = int(self._data[key].decode()) + amount
        self._data[key] = str(value).encode()
        return value

    async def _apply_get(self, key):
        if self._check_expiry(key):
            return None
        value = self._data.get(key)
        if value is None:
            return None
        if not isinstance(value, bytes):
            return self._encode_value(value)
        return value

class MockTransaction:
    def __init__(self, redis, watched_keys=None, watched_values=None):
        self.redis = redis
        self._pipeline_commands = []
        self._watched_keys = watched_keys or set()
        self._watched_values = watched_values or dict()

    async def set(self, key, value, ex=None):
        self._pipeline_commands.append(("set", key, value, ex))
        return True

    async def get(self, key):
        self._pipeline_commands.append(("get", key))
        return None

    async def delete(self, *keys):
        for key in keys:
            self._pipeline_commands.append(("delete", key))
        return len(keys)

    async def expire(self, key, seconds):
        self._pipeline_commands.append(("expire", key, seconds))
        return True

    async def hset(self, key, field, value):
        self._pipeline_commands.append(("hset", key, field, value))
        return 1

    async def hincrby(self, key, field, amount=1):
        self._pipeline_commands.append(("hincrby", key, field, amount))
        return amount

    async def lpush(self, key, *values):
        self._pipeline_commands.append(("lpush", key, *values))
        return len(values)

    async def rpush(self, key, *values):
        self._pipeline_commands.append(("rpush", key, *values))
        return len(values)

    async def incr(self, key):
        self._pipeline_commands.append(("incr", key))
        return 1

    async def decr(self, key):
        self._pipeline_commands.append(("decr", key))
        return -1

    async def incrby(self, key, amount=1):
        self._pipeline_commands.append(("incrby", key, amount))
        return amount

    async def execute(self):
        # Check watched keys for changes
        for key in self._watched_keys:
            if self.redis._data.get(key) != self._watched_values.get(key):
                raise WatchError("Watched key changed before transaction execution")
        results = []
        for cmd in self._pipeline_commands:
            method_name = cmd[0]
            args = cmd[1:]
            method = getattr(self.redis, f"_apply_{method_name}", None)
            if method is not None:
                result = await method(*args)
            else:
                method = getattr(self.redis, method_name)
                result = await method(*args)
            results.append(result)
        self._pipeline_commands = []
        self._watched_keys.clear()
        self._watched_values.clear()
        return results

    async def unwatch(self):
        self._watched_keys.clear()
        self._watched_values.clear()
        return True

class MockPipeline:
    """Mock Redis pipeline for batching commands."""
    def __init__(self, redis: 'MockRedis'):
        self.redis = redis
        self.commands = []
        self._in_multi = False  # Always initialize
        self._watched_keys = set()
        self._watched_values = dict()
        self._error_mode = getattr(redis, '_error_mode', False)
        # Ensure all attributes are initialized

    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    async def __aenter__(self):
        return self
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    # Queue commands for later execution
    async def set(self, key, value, ex=None):
        self.commands.append((self.redis.set, (key, value, ex), {}))
        return self

    async def get(self, key):
        self.commands.append((self.redis.get, (key,), {}))
        return self

    async def delete(self, key):
        self.commands.append((self.redis.delete, (key,), {}))
        return self

    async def hget(self, key, field):
        self.commands.append((self.redis.hget, (key, field), {}))
        return self

    async def hset(self, key, field, value):
        self.commands.append((self.redis.hset, (key, field, value), {}))
        return self

    async def lpush(self, key, *values):
        self.commands.append((self.redis.lpush, (key, *values), {}))
        return self

    async def rpush(self, key, *values):
        self.commands.append((self.redis.rpush, (key, *values), {}))
        return self

    async def expire(self, key, seconds):
        self.commands.append((self.redis.expire, (key, seconds), {}))
        return self

    async def hincrby(self, key, field, amount=1):
        self.commands.append((self.redis.hincrby, (key, field, amount), {}))
        return self

    async def lrange(self, key, start, stop):
        self.commands.append((self.redis.lrange, (key, start, stop), {}))
        return self

    def watch(self, *keys):
        import copy
        for key in keys:
            bkey = self.redis._encode_key(key)
            self._watched_keys.add(bkey)
            # Store a deep copy of the value to detect changes
            self._watched_values[bkey] = copy.deepcopy(self.redis._data.get(bkey))

    async def multi(self):
        self._in_multi = True

    async def execute(self):
        import copy
        # Debug output: print watched keys and values before the watch check
        print("[MockPipeline.execute] Watched keys and values before check:")
        for key, old_value in self._watched_values.items():
            current_value = self.redis._data.get(key)
            print(f"  key={key!r}, old_value={old_value!r}, current_value={current_value!r}")
        # Move the watch check to the very start, before any commands are executed
        def is_falsy(val):
            return val in [None, b"", b"0"]
        for key, old_value in self._watched_values.items():
            current_value = self.redis._data.get(key)
            # Treat all falsy values as equivalent for watch
            if is_falsy(current_value) and is_falsy(old_value):
                continue
            if current_value != old_value:
                print(f"[MockPipeline.execute] WatchError: key={key!r}, old_value={old_value!r}, current_value={current_value!r}")
                self.commands.clear()
                self._in_multi = False
                self._watched_keys.clear()
                self._watched_values.clear()
                raise WatchError("Watched key changed before transaction execution")
        # After the check passes, execute all commands atomically
        orig_data = copy.deepcopy(self.redis._data)
        orig_lists = {k: v.copy() for k, v in self.redis._lists.items()}
        try:
            results = []
            for func, args, kwargs in self.commands:
                result = await func(*args, **kwargs)
                results.append(result)
            self.commands.clear()
            self._in_multi = False
            self._watched_keys.clear()
            self._watched_values.clear()
            return results
        except Exception as e:
            # Roll back all changes (deep copy)
            self.redis._data = copy.deepcopy(orig_data)
            self.redis._lists = {k: v.copy() for k, v in orig_lists.items()}
            self.commands.clear()
            self._in_multi = False
            self._watched_keys.clear()
            self._watched_values.clear()
            raise e

    def __await__(self):
        return self.execute().__await__()

    async def incrby(self, key, amount=1):
        self.commands.append((self.redis.incrby, (key, amount), {}))
        return self

class SyncMockRedis:
    """Synchronous Mock Redis for use with sync test clients (e.g., FastAPI TestClient)."""
    def __init__(self):
        self._data = {}
        self._expires = {}
        self._lists = {}
        self._error_mode = False

    def _encode_key(self, key):
        return key.encode() if isinstance(key, str) else key

    def _encode_value(self, value):
        if isinstance(value, bytes):
            return value
        if isinstance(value, (int, float, bool)):
            return str(int(value) if isinstance(value, bool) else value).encode()
        if isinstance(value, str):
            return value.encode()
        raise Exception(f"Cannot encode value of type {type(value)}")

    def set(self, key, value, ex=None):
        key = self._encode_key(key)
        value = self._encode_value(value)
        self._data[key] = value
        if ex is not None:
            self._expires[key] = time.time() + ex
        return True

    def get(self, key):
        key = self._encode_key(key)
        if key in self._expires and time.time() > self._expires[key]:
            del self._data[key]
            del self._expires[key]
            return None
        return self._data.get(key)

    def delete(self, *keys):
        count = 0
        for key in keys:
            key = self._encode_key(key)
            if key in self._data:
                del self._data[key]
                count += 1
        return count

    def hset(self, key, field, value):
        key = self._encode_key(key)
        field = self._encode_key(field)
        value = self._encode_value(value)
        if key not in self._data or not isinstance(self._data[key], dict):
            self._data[key] = {}
        is_new = field not in self._data[key]
        self._data[key][field] = value
        return 1 if is_new else 0

    def hget(self, key, field):
        key = self._encode_key(key)
        field = self._encode_key(field)
        if key not in self._data or not isinstance(self._data[key], dict):
            return None
        return self._data[key].get(field)

    def lpush(self, key, *values):
        key = self._encode_key(key)
        if key not in self._lists:
            self._lists[key] = []
        for value in values:
            self._lists[key].insert(0, self._encode_value(value))
        self._data[key] = self._lists[key]
        return len(self._lists[key])

    def lpop(self, key):
        key = self._encode_key(key)
        if key not in self._lists or not self._lists[key]:
            return None
        return self._lists[key].pop(0)

    def rpush(self, key, *values):
        key = self._encode_key(key)
        if key not in self._lists:
            self._lists[key] = []
        for value in values:
            self._lists[key].append(self._encode_value(value))
        self._data[key] = self._lists[key]
        return len(self._lists[key])

    def rpop(self, key):
        key = self._encode_key(key)
        if key not in self._lists or not self._lists[key]:
            return None
        return self._lists[key].pop()

    def keys(self, pattern="*"):
        import fnmatch
        return [k for k in self._data.keys() if fnmatch.fnmatch(k.decode() if isinstance(k, bytes) else k, pattern)]

    def exists(self, *keys):
        count = 0
        for key in keys:
            key = self._encode_key(key)
            if key in self._data:
                count += 1
        return count

    def expire(self, key, seconds):
        key = self._encode_key(key)
        if key not in self._data:
            return False
        self._expires[key] = time.time() + seconds
        return True

    def ttl(self, key):
        key = self._encode_key(key)
        if key not in self._data:
            return -2
        if key not in self._expires:
            return -1
        ttl = int(self._expires[key] - time.time())
        return ttl if ttl > 0 else -2

    def pttl(self, key):
        key = self._encode_key(key)
        if key not in self._data:
            return -2
        if key not in self._expires:
            return -1
        pttl = int((self._expires[key] - time.time()) * 1000)
        return pttl if pttl > 0 else -2

    def incr(self, key):
        key = self._encode_key(key)
        if key not in self._data:
            self._data[key] = b"0"
        value = int(self._data[key].decode())
        value += 1
        self._data[key] = str(value).encode()
        return value

    def decr(self, key):
        key = self._encode_key(key)
        if key not in self._data:
            self._data[key] = b"0"
        value = int(self._data[key].decode())
        value -= 1
        self._data[key] = str(value).encode()
        return value

    def incrby(self, key, amount=1):
        key = self._encode_key(key)
        if key not in self._data:
            self._data[key] = b"0"
        value = int(self._data[key].decode())
        value += amount
        self._data[key] = str(value).encode()
        return value

    def pipeline(self):
        return SyncMockPipeline(self)

class SyncMockPipeline:
    """Synchronous Mock Redis pipeline."""
    def __init__(self, redis):
        self.redis = redis
        self.commands = []

    def set(self, key, value, ex=None):
        self.commands.append((self.redis.set, (key, value, ex)))
        return self

    def get(self, key):
        self.commands.append((self.redis.get, (key,)))
        return self

    def delete(self, key):
        self.commands.append((self.redis.delete, (key,)))
        return self

    def hset(self, key, field, value):
        self.commands.append((self.redis.hset, (key, field, value)))
        return self

    def hget(self, key, field):
        self.commands.append((self.redis.hget, (key, field)))
        return self

    def lpush(self, key, *values):
        self.commands.append((self.redis.lpush, (key, *values)))
        return self

    def rpush(self, key, *values):
        self.commands.append((self.redis.rpush, (key, *values)))
        return self

    def execute(self):
        results = []
        for func, args in self.commands:
            results.append(func(*args))
        self.commands.clear()
        return results 