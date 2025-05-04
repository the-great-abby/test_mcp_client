"""
Monitoring and telemetry functionality.
"""
from datetime import datetime, timedelta, UTC
import json
from typing import Dict, Any, Optional, Tuple, Callable
from functools import wraps
from fastapi import HTTPException, Request, Depends
from app.core.redis import RedisClient, get_redis
from zoneinfo import ZoneInfo

UTC = ZoneInfo("UTC")

def rate_limit(requests_per_window: int = 60, window_seconds: int = 60):
    """Rate limit decorator for FastAPI endpoints."""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = kwargs.get("request")
            if not request:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break
            
            if not request:
                # If no request object found in args/kwargs, try to get it from FastAPI's dependency injection
                from app.api.deps import get_current_request
                request = await get_current_request()
            
            if not request:
                raise ValueError("Could not find FastAPI request object")
                
            user_id = request.headers.get("X-User-Id", "default")
            redis_client = await get_redis()
            rate_limiter = RateLimiter(redis_client, requests_per_window, window_seconds)
            
            allowed = await rate_limiter.check_rate_limit(user_id)
            if not allowed:
                raise HTTPException(
                    status_code=429,
                    detail={
                        "error": "Rate limit exceeded",
                        "code": "rate_limit_exceeded"
                    }
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

class RateLimiter:
    """Rate limiter using Redis."""
    
    def __init__(self, redis: RedisClient, requests_per_window: int = 100, window_seconds: int = 60):
        """Initialize rate limiter."""
        self.redis = redis
        self.requests_per_window = requests_per_window
        self.window_seconds = window_seconds
    
    def _get_key(self, user_id: str) -> str:
        """Generate Redis key for rate limiting."""
        return f"rate_limit:{user_id}"
    
    async def check_rate_limit(self, user_id: str) -> bool:
        """Check if user has exceeded rate limit."""
        key = self._get_key(user_id)
        redis = await self.redis.redis
        
        # Check if key exists
        exists = await redis.exists(key)
        if not exists:
            # Key doesn't exist, set initial count and expiry
            await redis.set(key, "1", ex=self.window_seconds)
            return True
            
        # Get current count
        count = await redis.get(key)
        if count is None:
            # Key expired between exists check and get
            await redis.set(key, "1", ex=self.window_seconds)
            return True
            
        count = int(count)
        if count >= self.requests_per_window:
            return False
            
        # Increment count
        await redis.incr(key)
        return True
        
    async def clear_all(self) -> None:
        """Clear all rate limit data."""
        # Delete all keys with the rate_limit: prefix
        redis = await self.redis.redis
        async for key in redis.scan_iter("rate_limit:*"):
            await redis.delete(key)

class TelemetryService:
    """Service for tracking API usage and metrics."""
    
    def __init__(self, redis: RedisClient):
        """Initialize telemetry service with Redis client."""
        self.redis = redis
    
    def _get_user_key(self, user_id: str, metric: str) -> str:
        """Generate Redis key for user-specific metrics."""
        return f"metrics:user:{user_id}:{metric}"
    
    def _get_global_key(self, metric: str) -> str:
        """Generate Redis key for global metrics."""
        return f"metrics:global:{metric}"
    
    async def record_model_call(self, user_id: str, model: str, tokens: int) -> None:
        """Record a model API call with token usage."""
        now = datetime.now(UTC)
        date_str = now.strftime("%Y-%m-%d")
        redis = await self.redis.redis
        
        try:
            # User metrics
            user_key = self._get_user_key(user_id, f"model_calls:{date_str}")
            await redis.hincrby(user_key, "count", 1)
            await redis.hincrby(user_key, "tokens", tokens)
            await redis.expire(user_key, 86400 * 30)  # 30 days
            
            # Global metrics
            global_key = self._get_global_key(f"model_calls:{date_str}")
            await redis.hincrby(global_key, "count", 1)
            await redis.hincrby(global_key, "tokens", tokens)
            await redis.expire(global_key, 86400 * 30)  # 30 days
                
        except Exception as e:
            # Log error and propagate
            print(f"Error recording model call: {e}")
            raise  # Re-raise the exception to fail the test
    
    async def record_cache_hit(self, user_id: str) -> None:
        """Record a cache hit for metrics."""
        now = datetime.now(UTC)
        date_str = now.strftime("%Y-%m-%d")
        redis = await self.redis.redis
        
        try:
            # User metrics
            user_key = self._get_user_key(user_id, f"cache_hits:{date_str}")
            await redis.hincrby(user_key, "count", 1)
            await redis.expire(user_key, 86400 * 30)  # 30 days
            
            # Global metrics
            global_key = self._get_global_key(f"cache_hits:{date_str}")
            await redis.hincrby(global_key, "count", 1)
            await redis.expire(global_key, 86400 * 30)  # 30 days
                
        except Exception as e:
            # Log error and propagate
            print(f"Error recording cache hit: {e}")
            raise  # Re-raise the exception to fail the test
    
    async def get_user_metrics(self, user_id: str, date: Optional[str] = None) -> Dict[str, Any]:
        """Get metrics for a specific user."""
        if not date:
            date = datetime.now(UTC).strftime("%Y-%m-%d")
        redis = await self.redis.redis
            
        try:
            model_key = self._get_user_key(user_id, f"model_calls:{date}")
            cache_key = self._get_user_key(user_id, f"cache_hits:{date}")
            
            # Execute commands individually instead of using pipeline
            model_stats = await redis.hgetall(model_key)
            cache_stats = await redis.hgetall(cache_key)
            
            # Convert bytes to strings and then to integers
            return {
                "model_calls": int(model_stats.get(b"count", 0) if model_stats else 0),
                "tokens_used": int(model_stats.get(b"tokens", 0) if model_stats else 0),
                "cache_hits": int(cache_stats.get(b"count", 0) if cache_stats else 0)
            }
                
        except Exception as e:
            print(f"Error getting user metrics: {e}")
            raise  # Re-raise the exception to fail the test
    
    async def get_global_metrics(self) -> Dict[str, int]:
        """Get global usage metrics."""
        date = datetime.now(UTC).strftime("%Y-%m-%d")
        redis = await self.redis.redis
        model_key = self._get_global_key(f"model_calls:{date}")
        cache_key = self._get_global_key(f"cache_hits:{date}")
        
        try:
            # Execute commands individually instead of using pipeline
            model_stats = await redis.hgetall(model_key)
            cache_stats = await redis.hgetall(cache_key)
            
            # Convert bytes to strings and then to integers
            return {
                "count": int(model_stats.get(b"count", 0) if model_stats else 0),
                "tokens": int(model_stats.get(b"tokens", 0) if model_stats else 0),
                "cache_hits": int(cache_stats.get(b"count", 0) if cache_stats else 0)
            }
                
        except Exception as e:
            print(f"Error getting global metrics: {e}")
            raise  # Re-raise the exception to fail the test
    
    async def clear_all(self) -> None:
        """Clear all telemetry data (used for testing)."""
        redis = await self.redis.redis
        try:
            # Get all metric keys
            user_keys = await redis.keys("metrics:user:*")
            global_keys = await redis.keys("metrics:global:*")
            
            # Delete all keys
            if user_keys:
                await redis.delete(*user_keys)
            if global_keys:
                await redis.delete(*global_keys)
                
        except Exception as e:
            print(f"Error clearing telemetry data: {e}")
            raise  # Re-raise the exception to fail the test