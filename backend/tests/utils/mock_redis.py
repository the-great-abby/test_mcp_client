"""Mock Redis implementation for testing."""
import asyncio
import time
import re
from typing import Dict, List, Any, Optional, Set, Union, Callable
from redis.exceptions import WatchError, RedisError
import json

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
        """Check if value is of expected type."""
        if key in self._data:
            value = self._data[key]
            if not isinstance(value, expected_type):
                # Try to convert the value using type handlers
                if expected_type in self._type_handlers:
                    try:
                        self._data[key] = self._type_handlers[expected_type](value)
                    except Exception:
                        raise RedisError(f"Key contains a non-{expected_type.__name__} value")
                else:
                    raise RedisError(f"Unsupported type conversion to {expected_type.__name__}")
    
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
        """Set key to value with optional expiry."""
        if self._error_mode:
            raise RedisError("Redis error (mock)")
            
        key = self._encode_key(key)
        value = self._encode_value(value)
        
        if self._in_transaction:
            self._pipeline_commands.append(("set", key, value, ex))
            return True
            
        if key in self._watched_keys and key in self._watched_values:
            if self._watched_values[key] != self._data.get(key):
                raise WatchError()
            
        self._data[key] = value
        if ex is not None:
            if ex <= 0:
                raise RedisError("Invalid expire time")
            self._expires[key] = time.time() + ex
        return True
    
    async def get(self, key: Union[str, bytes]) -> Optional[bytes]:
        """Get value for key."""
        if self._error_mode:
            raise RedisError("Redis error (mock)")
            
        key = self._encode_key(key)
        if self._check_expiry(key):
            return None
            
        if self._in_transaction:
            self._pipeline_commands.append(("get", key))
            return None
            
        return self._data.get(key)
    
    async def delete(self, *keys: bytes) -> int:
        """Delete keys."""
        if self._error_mode:
            raise RedisError("Redis error (mock)")
            
        count = 0
        for key in keys:
            if key in self._data:
                if key in self._watched_keys and key in self._watched_values:
                    if self._watched_values[key] != self._data.get(key):
                        raise WatchError()
                del self._data[key]
                if key in self._expires:
                    del self._expires[key]
                count += 1
        return count
    
    async def expire(self, key: Union[str, bytes], seconds: int) -> bool:
        """Set a key's time to live in seconds."""
        if self._error_mode:
            raise RedisError("Redis error (mock)")
            
        key = self._encode_key(key)
        if seconds <= 0:
            return False
            
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
    
    async def hset(self, key: Union[str, bytes], field: str, value: Any) -> int:
        """Set hash field to value."""
        if self._error_mode:
            raise RedisError("Redis error (mock)")
            
        key = self._encode_key(key)
        if key not in self._data:
            self._data[key] = {}
        
        try:
            self._check_type(key, dict)
        except RedisError:
            raise RedisError("Key contains a non-hash value")
        
        if self._in_transaction:
            self._pipeline_commands.append(("hset", key, field, value))
            return 1
            
        if key in self._watched_keys and key in self._watched_values:
            if self._watched_values[key] != self._data.get(key):
                raise WatchError()
                
        field = self._encode_key(field)
        value = self._encode_value(value)
        is_new = field not in self._data[key]
        self._data[key][field] = value
        return 1 if is_new else 0
    
    async def hget(self, key: Union[str, bytes], field: str) -> Optional[bytes]:
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
    
    async def hgetall(self, key: Union[str, bytes]) -> Dict[bytes, bytes]:
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
        field: str,
        amount: int = 1
    ) -> int:
        """Increment the integer value of a hash field by the given number."""
        if self._error_mode:
            raise RedisError("Redis error (mock)")
            
        key = self._encode_key(key)
        field = self._encode_key(field)
        
        try:
            self._check_type(key, dict)
        except RedisError:
            raise RedisError("Key contains a non-hash value")
            
        if self._in_transaction:
            self._pipeline_commands.append(("hincrby", key, field, amount))
            return amount
            
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
    
    async def lpush(self, key: bytes, *values: bytes) -> int:
        """Push values to the head of a list."""
        if key not in self._lists:
            self._lists[key] = []
        for value in values:
            self._lists[key].insert(0, value)
        return len(self._lists[key])
    
    async def lpop(self, key: bytes) -> Optional[bytes]:
        """Pop value from the head of a list."""
        if key not in self._lists or not self._lists[key]:
            return None
        return self._lists[key].pop(0)
    
    async def lrange(
        self,
        key: Union[str, bytes],
        start: int,
        stop: int
    ) -> List[bytes]:
        """Get a range of elements from a list."""
        if self._error_mode:
            raise RedisError("Redis error (mock)")
            
        key = self._encode_key(key)
        try:
            self._check_type(key, list)
        except RedisError:
            raise RedisError("Key contains a non-list value")
            
        if self._in_transaction:
            self._pipeline_commands.append(("lrange", key, start, stop))
            return []
            
        if key not in self._data:
            return []
            
        if stop < 0:
            stop = len(self._data[key]) + stop + 1
        else:
            stop += 1
            
        return self._data[key][start:stop]
    
    async def keys(self, pattern: Union[str, bytes]) -> List[bytes]:
        """Find all keys matching the given pattern."""
        if self._error_mode:
            raise RedisError("Redis error (mock)")
            
        if isinstance(pattern, str):
            pattern = pattern.encode()
            
        if self._in_transaction:
            self._pipeline_commands.append(("keys", pattern))
            return []
            
        # Convert Redis pattern to regex pattern
        regex_pattern = pattern.decode().replace("*", ".*").replace("?", ".") + "$"
        compiled_pattern = re.compile(regex_pattern)
        
        matching_keys = []
        for key in self._data.keys():
            if compiled_pattern.match(key.decode()):
                matching_keys.append(key)
                
        return matching_keys
    
    def pipeline(self):
        """Create a pipeline for executing multiple commands atomically."""
        return self
    
    async def watch(self, *keys: str) -> bool:
        """Watch the given keys to determine execution of transaction."""
        if self._error_mode:
            raise RedisError("Redis error (mock)")
            
        for key in keys:
            encoded_key = self._encode_key(key)
            self._watched_keys.add(encoded_key)
            self._watched_values[encoded_key] = self._data.get(encoded_key)
        return True
    
    async def unwatch(self) -> bool:
        """Forget about all watched keys."""
        if self._error_mode:
            raise RedisError("Redis error (mock)")
            
        self._watched_keys.clear()
        self._watched_values.clear()
        return True
    
    def multi(self) -> 'MockRedis':
        """Start a transaction."""
        if self._error_mode:
            raise RedisError("Redis error (mock)")
            
        self._in_transaction = True
        self._transaction_data = self._data.copy()
        self._pipeline_commands = []
        return self
    
    async def execute(self) -> List[Any]:
        """Execute transaction."""
        if self._error_mode:
            raise RedisError("Redis error (mock)")
            
        if not self._in_transaction:
            raise RedisError("Not in transaction")
            
        if self._transaction_failed:
            raise WatchError()
            
        # Check watched keys
        for key in self._watched_keys:
            if self._data.get(key) != self._watched_values.get(key):
                self._in_transaction = False
                self._watched_keys.clear()
                self._watched_values.clear()
                raise WatchError("Watched key changed")

        # Execute commands
        results = []
        try:
            for cmd in self._pipeline_commands:
                method = getattr(self, cmd[0])
                args = cmd[1:]
                result = await method(*args)
                results.append(result)
        except Exception as e:
            self._in_transaction = False
            self._pipeline_commands = []
            self._transaction_failed = True
            raise e
            
        self._in_transaction = False
        self._pipeline_commands = []
        self._watched_keys.clear()
        self._watched_values.clear()
        return results
    
    async def exists(self, *keys: bytes) -> int:
        """Check if keys exist."""
        count = 0
        for key in keys:
            if key in self._data and (key not in self._expires or self._expires[key] > time.time()):
                count += 1
        return count
    
    async def rpush(self, key: bytes, *values: bytes) -> int:
        """Push values to the tail of a list."""
        if key not in self._lists:
            self._lists[key] = []
        for value in values:
            self._lists[key].append(value)
        return len(self._lists[key])
    
    async def rpop(self, key: bytes) -> Optional[bytes]:
        """Pop value from the tail of a list."""
        if key not in self._lists or not self._lists[key]:
            return None
        return self._lists[key].pop()

    async def lrange(self, key: bytes, start: int, stop: int) -> List[bytes]:
        """Get a range of values from a list."""
        if key not in self._lists:
            return []
        
        # Handle negative indices
        list_len = len(self._lists[key])
        if start < 0:
            start = max(list_len + start, 0)
        if stop < 0:
            stop = list_len + stop + 1
        else:
            stop = min(stop + 1, list_len)
            
        return self._lists[key][start:stop] 