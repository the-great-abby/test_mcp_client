from typing import Optional, Union, Any, List, Dict, TYPE_CHECKING
from redis.asyncio import Redis, ConnectionPool
from fastapi import Depends
from app.core.config import settings
import json
import logging
from datetime import timedelta
from redis.asyncio.client import Pipeline
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)

class RedisClient:
    """Redis client wrapper with async support."""
    
    def __init__(self, host: str, port: int, db: int = 0):
        """Initialize Redis client.
        
        Args:
            host: Redis host
            port: Redis port
            db: Redis database number
        """
        self.pool = ConnectionPool(
            host=host,
            port=port,
            db=db,
            decode_responses=True
        )
        self._redis: Optional[Redis] = None
        
    @property
    async def redis(self) -> Redis:
        """Get Redis client instance."""
        if not self._redis:
            self._redis = Redis(connection_pool=self.pool)
        return self._redis
        
    async def ping(self) -> bool:
        """Test connection."""
        try:
            redis = await self.redis
            return await redis.ping()
        except RedisError as e:
            logger.error(f"Redis ping failed: {e}")
            return False
            
    async def get(self, key: str) -> Optional[str]:
        """Get value for key."""
        try:
            redis = await self.redis
            return await redis.get(key)
        except RedisError as e:
            logger.error(f"Redis get failed for key {key}: {e}")
            return None
            
    async def set(
        self,
        key: str,
        value: str,
        ex: Optional[int] = None
    ) -> bool:
        """Set key to value with optional expiry.
        
        Args:
            key: Key to set
            value: Value to set
            ex: Expiry time in seconds
            
        Returns:
            bool: True if successful
        """
        try:
            redis = await self.redis
            return await redis.set(key, value, ex=ex)
        except RedisError as e:
            logger.error(f"Redis set failed for key {key}: {e}")
            return False
            
    async def delete(self, key: str) -> bool:
        """Delete key.
        
        Args:
            key: Key to delete
            
        Returns:
            bool: True if key was deleted
        """
        try:
            redis = await self.redis
            return bool(await redis.delete(key))
        except RedisError as e:
            logger.error(f"Redis delete failed for key {key}: {e}")
            return False
            
    async def exists(self, key: str) -> bool:
        """Check if key exists.
        
        Args:
            key: Key to check
            
        Returns:
            bool: True if key exists
        """
        try:
            redis = await self.redis
            return bool(await redis.exists(key))
        except RedisError as e:
            logger.error(f"Redis exists failed for key {key}: {e}")
            return False
            
    async def incr(self, key: str) -> Optional[int]:
        """Increment value for key.
        
        Args:
            key: Key to increment
            
        Returns:
            int: New value or None on error
        """
        try:
            redis = await self.redis
            return await redis.incr(key)
        except RedisError as e:
            logger.error(f"Redis incr failed for key {key}: {e}")
            return None
            
    async def decr(self, key: str) -> Optional[int]:
        """Decrement value for key.
        
        Args:
            key: Key to decrement
            
        Returns:
            int: New value or None on error
        """
        try:
            redis = await self.redis
            return await redis.decr(key)
        except RedisError as e:
            logger.error(f"Redis decr failed for key {key}: {e}")
            return None
            
    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiry on key.
        
        Args:
            key: Key to set expiry on
            seconds: Expiry time in seconds
            
        Returns:
            bool: True if expiry was set
        """
        try:
            redis = await self.redis
            return await redis.expire(key, seconds)
        except RedisError as e:
            logger.error(f"Redis expire failed for key {key}: {e}")
            return False
            
    async def ttl(self, key: str) -> Optional[int]:
        """Get remaining time to live for key.
        
        Args:
            key: Key to check TTL for
            
        Returns:
            int: TTL in seconds or None on error
        """
        try:
            redis = await self.redis
            return await redis.ttl(key)
        except RedisError as e:
            logger.error(f"Redis ttl failed for key {key}: {e}")
            return None
            
    async def keys(self, pattern: str) -> List[str]:
        """Get all keys matching pattern.
        
        Args:
            pattern: Pattern to match keys against
            
        Returns:
            List[str]: List of matching keys
        """
        try:
            redis = await self.redis
            return await redis.keys(pattern)
        except RedisError as e:
            logger.error(f"Redis keys failed for pattern {pattern}: {e}")
            return []
            
    async def pipeline(self) -> Pipeline:
        """Get Redis pipeline."""
        redis = await self.redis
        return redis.pipeline()
        
    async def flushdb(self) -> bool:
        """Delete all keys in the current database.
        
        Returns:
            bool: True if successful
        """
        try:
            redis = await self.redis
            return await redis.flushdb()
        except RedisError as e:
            logger.error(f"Redis flushdb failed: {e}")
            return False
            
    async def aclose(self) -> None:
        """Close Redis connection."""
        if self._redis:
            await self._redis.aclose()
            self._redis = None

_redis_client: Optional[RedisClient] = None

async def get_redis_client() -> RedisClient:
    """
    Get Redis connection.
    """
    global _redis_client
    if _redis_client is None:
        redis = RedisClient(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
        )
        _redis_client = redis
    return _redis_client

async def get_redis() -> RedisClient:
    """
    Get Redis connection as a FastAPI dependency.
    Do not close since it's a singleton.
    """
    return await get_redis_client() 