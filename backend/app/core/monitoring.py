"""
Monitoring and telemetry functionality.
"""
from datetime import datetime, timedelta, UTC
import json
from typing import Dict, Any, Optional, Tuple, Callable
from functools import wraps
from fastapi import HTTPException, Request
from app.core.redis import RedisClient
from zoneinfo import ZoneInfo

UTC = ZoneInfo("UTC")

def rate_limit(requests_per_window: int = 100, window_seconds: int = 60):
    """Rate limit decorator for FastAPI endpoints."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = kwargs.get("request")
            if not request:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break
            
            if not request:
                raise ValueError("Could not find FastAPI request object")
            
            # Get user ID from request
            user_id = request.headers.get("X-User-Id", "anonymous")
            
            # Get Redis client from app state
            redis = request.app.state.redis
            limiter = RateLimiter(redis, requests_per_window, window_seconds)
            
            # Check rate limit
            allowed = await limiter.check_rate_limit(user_id)
            if not allowed:
                raise HTTPException(
                    status_code=429,
                    detail="Rate limit exceeded. Please try again later."
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
        count = await self.redis.incr(key)
        if count == 1:
            await self.redis.expire(key, self.window_seconds)
        return count <= self.requests_per_window

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
        
        pipe = self.redis.pipeline()
        try:
            # User metrics
            user_key = self._get_user_key(user_id, f"model_calls:{date_str}")
            await pipe.hincrby(user_key, "count", 1)
            await pipe.hincrby(user_key, "tokens", tokens)
            await pipe.expire(user_key, 86400 * 30)  # 30 days
            
            # Global metrics
            global_key = self._get_global_key(f"model_calls:{date_str}")
            await pipe.hincrby(global_key, "count", 1)
            await pipe.hincrby(global_key, "tokens", tokens)
            await pipe.expire(global_key, 86400 * 30)  # 30 days
            
            await pipe.execute()
            
        except Exception as e:
            # Log error but don't fail the request
            print(f"Error recording model call: {e}")
    
    async def record_cache_hit(self, user_id: str) -> None:
        """Record a cache hit for metrics."""
        now = datetime.now(UTC)
        date_str = now.strftime("%Y-%m-%d")
        
        pipe = self.redis.pipeline()
        try:
            # User metrics
            user_key = self._get_user_key(user_id, f"cache_hits:{date_str}")
            await pipe.hincrby(user_key, "count", 1)
            await pipe.expire(user_key, 86400 * 30)  # 30 days
            
            # Global metrics
            global_key = self._get_global_key(f"cache_hits:{date_str}")
            await pipe.hincrby(global_key, "count", 1)
            await pipe.expire(global_key, 86400 * 30)  # 30 days
            
            await pipe.execute()
            
        except Exception as e:
            # Log error but don't fail the request
            print(f"Error recording cache hit: {e}")
    
    async def get_user_metrics(self, user_id: str, date: Optional[str] = None) -> Dict[str, Any]:
        """Get metrics for a specific user."""
        if not date:
            date = datetime.now(UTC).strftime("%Y-%m-%d")
            
        try:
            model_key = self._get_user_key(user_id, f"model_calls:{date}")
            cache_key = self._get_user_key(user_id, f"cache_hits:{date}")
            
            pipe = self.redis.pipeline()
            await pipe.hgetall(model_key)
            await pipe.hgetall(cache_key)
            
            results = await pipe.execute()
            model_stats = results[0] or {}
            cache_stats = results[1] or {}
            
            return {
                "model_calls": int(model_stats.get(b"count", 0)),
                "tokens_used": int(model_stats.get(b"tokens", 0)),
                "cache_hits": int(cache_stats.get(b"count", 0))
            }
            
        except Exception as e:
            print(f"Error getting user metrics: {e}")
            return {"model_calls": 0, "tokens_used": 0, "cache_hits": 0}
    
    async def get_global_metrics(self) -> Dict[str, int]:
        """Get global usage metrics."""
        date = datetime.now(UTC).strftime("%Y-%m-%d")
        model_key = self._get_global_key(f"model_calls:{date}")
        cache_key = self._get_global_key(f"cache_hits:{date}")
        
        try:
            pipe = self.redis.pipeline()
            await pipe.hgetall(model_key)
            await pipe.hgetall(cache_key)
            
            results = await pipe.execute()
            model_stats = results[0] or {}
            cache_stats = results[1] or {}
            
            return {
                "count": int(model_stats.get(b"count", 0)),
                "tokens": int(model_stats.get(b"tokens", 0)),
                "cache_hits": int(cache_stats.get(b"count", 0))
            }
            
        except Exception as e:
            print(f"Error getting global metrics: {e}")
            return {"count": 0, "tokens": 0, "cache_hits": 0}