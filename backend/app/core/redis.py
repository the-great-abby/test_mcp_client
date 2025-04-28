from typing import Optional, Union, Any, List, TYPE_CHECKING
from redis.asyncio import Redis
from fastapi import Depends
from app.core.config import settings

class RedisClient:
    def __init__(self, redis: Redis):
        self.redis = redis
        self._pipeline = None

    async def get(self, key: str) -> Optional[bytes]:
        """Get value for key, returns bytes or None."""
        return await self.redis.get(key)

    async def set(self, key: str, value: Union[str, bytes, int], ex: Optional[int] = None) -> bool:
        """Set key to value with optional expiry."""
        if isinstance(value, str):
            value = value.encode()
        elif isinstance(value, int):
            value = str(value).encode()
        return await self.redis.set(key, value, ex=ex)

    async def hset(self, key: str, field: str, value: Union[str, bytes, int]) -> int:
        """Set hash field to value."""
        if isinstance(value, str):
            value = value.encode()
        elif isinstance(value, int):
            value = str(value).encode()
        return await self.redis.hset(key, field, value)

    async def hget(self, key: str, field: str) -> Optional[bytes]:
        """Get value of hash field."""
        return await self.redis.hget(key, field)

    async def hgetall(self, key: str) -> dict:
        """Get all fields and values in hash."""
        result = await self.redis.hgetall(key)
        return {k: v for k, v in result.items()}

    async def lpush(self, key: str, *values: Union[str, bytes, int]) -> int:
        """Push values onto start of list."""
        encoded = []
        for value in values:
            if isinstance(value, str):
                encoded.append(value.encode())
            elif isinstance(value, int):
                encoded.append(str(value).encode())
            else:
                encoded.append(value)
        return await self.redis.lpush(key, *encoded)

    async def lrange(self, key: str, start: int, end: int) -> List[bytes]:
        """Get range of elements from list."""
        return await self.redis.lrange(key, start, end)

    async def ltrim(self, key: str, start: int, end: int) -> bool:
        """Trim list to specified range."""
        return await self.redis.ltrim(key, start, end)

    async def incr(self, key: str) -> int:
        """Increment value of key."""
        return await self.redis.incr(key)

    async def hincrby(self, key: str, field: str, amount: int = 1) -> int:
        """Increment value of hash field by amount."""
        return await self.redis.hincrby(key, field, amount)

    async def ping(self) -> bool:
        """Test connection."""
        return await self.redis.ping()

    def pipeline(self):
        """Get a pipeline for batching commands."""
        self._pipeline = self.redis.pipeline()
        return self

    async def watch(self, *keys: str):
        """Watch keys for changes during transaction."""
        if self._pipeline:
            await self._pipeline.watch(*keys)

    async def multi(self):
        """Start a transaction."""
        if self._pipeline:
            await self._pipeline.multi()

    async def execute(self):
        """Execute pipeline commands."""
        if self._pipeline:
            try:
                return await self._pipeline.execute()
            finally:
                self._pipeline = None
        return []

    async def delete(self, *names: str) -> int:
        """Delete one or more keys."""
        return await self.redis.delete(*names)

    async def close(self):
        """Close the Redis connection."""
        await self.redis.close()

    async def expire(self, key, seconds):
        if self._pipeline:
            await self._pipeline.expire(key, seconds)

_redis_client: Optional[RedisClient] = None

async def get_redis_client() -> RedisClient:
    """
    Get Redis connection.
    """
    global _redis_client
    if _redis_client is None:
        redis = Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            decode_responses=False,  # Keep responses as bytes for consistency
        )
        _redis_client = RedisClient(redis)
    return _redis_client

async def get_redis() -> RedisClient:
    """
    Get Redis connection as a FastAPI dependency.
    Do not close since it's a singleton.
    """
    return await get_redis_client() 