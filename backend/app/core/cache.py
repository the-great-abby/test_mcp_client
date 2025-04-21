"""Redis caching functionality."""
import json
import logging
import hashlib
from typing import Any, Optional
from datetime import timedelta
from redis.asyncio import Redis
from .config import settings

logger = logging.getLogger(__name__)

async def get_cached_data(redis: Redis, key: str) -> Optional[Any]:
    """Get data from Redis cache."""
    if not key:
        raise ValueError("Cache key cannot be None or empty")
    if not redis:
        raise AttributeError("Redis client is required")
    
    try:
        data = await redis.get(key)
        if data:
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                # Return raw bytes for non-JSON data
                return data
        return None
    except Exception as e:
        logger.error(f"Cache get error for key {key}: {str(e)}")
        return None

async def set_cached_data(redis: Redis, key: str, data: Any, expiry: int = 300) -> bool:
    """Set data in Redis cache with expiry in seconds."""
    if not key:
        raise ValueError("Cache key cannot be None or empty")
    if data is None:
        raise ValueError("Cache data cannot be None")
    if expiry < 0:
        raise ValueError("Cache expiry must be non-negative")
    if not redis:
        raise AttributeError("Redis client is required")
    
    try:
        # Convert data to JSON string if not already a string/bytes
        if not isinstance(data, (str, bytes)):
            json_data = json.dumps(data)
        else:
            json_data = data
        # Set with expiry
        await redis.set(key, json_data, ex=expiry)
        return True
    except Exception as e:
        logger.error(f"Cache set error for key {key}: {str(e)}")
        return False

async def invalidate_cache(redis: Redis, key: str) -> bool:
    """Remove data from Redis cache."""
    if not key:
        raise ValueError("Cache key cannot be None or empty")
    if not redis:
        raise AttributeError("Redis client is required")
    
    try:
        await redis.delete(key)
        return True
    except Exception as e:
        logger.error(f"Cache invalidation error for key {key}: {str(e)}")
        return False

def get_cache_key(*args) -> str:
    """Generate a cache key from the given arguments.
    
    The key is a colon-separated string containing all arguments.
    - Dictionaries are formatted as 'key=value' pairs
    - Empty lists/tuples are represented as '[]'
    - Empty dictionaries are represented as '{}'
    - None values are represented as 'None'
    
    Example:
        get_cache_key("test", [], {"a": 1}) -> "test:[]:a=1"
    """
    parts = []
    
    for arg in args:
        if arg is None:
            parts.append("None")
        elif isinstance(arg, (list, tuple)):
            if not arg:
                parts.append("[]")
            else:
                parts.extend(str(item) for item in arg)
        elif isinstance(arg, dict):
            if not arg:
                parts.append("{}")
            else:
                parts.extend(f"{k}={v}" for k, v in sorted(arg.items()))
        else:
            parts.append(str(arg))
    
    return ":".join(filter(None, parts))

class ModelResponseCache:
    """Cache handler for model responses."""
    
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self.default_ttl = timedelta(hours=24)  # Cache responses for 24 hours by default
    
    def _generate_cache_key(self, messages: list, system_prompt: Optional[str] = None) -> str:
        """Generate a unique cache key for the conversation context."""
        # Use get_cache_key to properly handle empty lists and other edge cases
        cache_key = get_cache_key(
            "model_response",
            messages,
            system_prompt,
            settings.MODEL_NAME,
            settings.MODEL_TEMPERATURE
        )
        
        # Generate a hash of the formatted key
        return hashlib.sha256(cache_key.encode()).hexdigest()
    
    async def get_cached_response(
        self,
        messages: list,
        system_prompt: Optional[str] = None
    ) -> Optional[str]:
        """Get a cached model response if it exists."""
        try:
            cache_key = self._generate_cache_key(messages, system_prompt)
            cached = await self.redis.get(cache_key)
            
            if cached:
                logger.info("Cache hit for model response", extra={
                    "cache_key": cache_key,
                    "model": settings.MODEL_NAME
                })
                return cached.decode()
            
            logger.info("Cache miss for model response", extra={
                "cache_key": cache_key,
                "model": settings.MODEL_NAME
            })
            return None
            
        except Exception as e:
            logger.error("Error getting cached response", exc_info=True)
            return None
    
    async def cache_response(
        self,
        messages: list,
        response: str,
        system_prompt: Optional[str] = None,
        ttl: Optional[timedelta] = None
    ) -> None:
        """Cache a model response."""
        try:
            cache_key = self._generate_cache_key(messages, system_prompt)
            await self.redis.set(
                cache_key,
                response,
                ex=int(ttl.total_seconds() if ttl else self.default_ttl.total_seconds())
            )
            
            logger.info("Cached model response", extra={
                "cache_key": cache_key,
                "model": settings.MODEL_NAME,
                "ttl": str(ttl or self.default_ttl)
            })
            
        except Exception as e:
            logger.error("Error caching response", exc_info=True)
    
    async def invalidate_cache(
        self,
        messages: list,
        system_prompt: Optional[str] = None
    ) -> None:
        """Invalidate a cached response."""
        try:
            cache_key = self._generate_cache_key(messages, system_prompt)
            await self.redis.delete(cache_key)
            
            logger.info("Invalidated cached response", extra={
                "cache_key": cache_key,
                "model": settings.MODEL_NAME
            })
            
        except Exception as e:
            logger.error("Error invalidating cache", exc_info=True)