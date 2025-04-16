from typing import Optional
import logging
from app.core.redis import RedisClient

logger = logging.getLogger(__name__)


class TelemetryService:
    """
    Service for tracking model usage and metrics.
    """
    def __init__(self, redis: RedisClient):
        self.redis = redis

    async def record_model_call(self, user_id: str, prompt_tokens: int, completion_tokens: int) -> None:
        """
        Record a model call with token usage.
        """
        try:
            # Record total calls
            await self.redis.incr(f"user:{user_id}:total_calls")
            await self.redis.incr("global:total_calls")

            # Record token usage
            await self.redis.hincrby(f"user:{user_id}:tokens", "prompt", prompt_tokens)
            await self.redis.hincrby(f"user:{user_id}:tokens", "completion", completion_tokens)
            await self.redis.hincrby("global:tokens", "prompt", prompt_tokens)
            await self.redis.hincrby("global:tokens", "completion", completion_tokens)

            # Record user activity
            await self.redis.lpush(f"user:{user_id}:activity", "model_call")
            await self.redis.ltrim(f"user:{user_id}:activity", 0, 99)  # Keep last 100 activities

            logger.info(f"Recorded model call for user {user_id}", extra={
                "user_id": user_id,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens
            })
        except Exception as e:
            logger.error(f"Failed to record model call: {e}", exc_info=True)

    async def record_cache_hit(self, user_id: str, tokens_saved: int) -> None:
        """
        Record a cache hit and tokens saved.
        """
        try:
            # Record cache hits
            await self.redis.incr(f"user:{user_id}:cache_hits")
            await self.redis.incr("global:cache_hits")

            # Record tokens saved
            await self.redis.hincrby(f"user:{user_id}:tokens", "saved", tokens_saved)
            await self.redis.hincrby("global:tokens", "saved", tokens_saved)

            # Record user activity
            await self.redis.lpush(f"user:{user_id}:activity", "cache_hit")
            await self.redis.ltrim(f"user:{user_id}:activity", 0, 99)  # Keep last 100 activities

            logger.info(f"Recorded cache hit for user {user_id}", extra={
                "user_id": user_id,
                "tokens_saved": tokens_saved
            })
        except Exception as e:
            logger.error(f"Failed to record cache hit: {e}", exc_info=True)

    async def get_user_metrics(self, user_id: str) -> dict:
        """
        Get metrics for a specific user.
        """
        try:
            total_calls = await self.redis.get(f"user:{user_id}:total_calls") or 0
            cache_hits = await self.redis.get(f"user:{user_id}:cache_hits") or 0
            tokens = await self.redis.hgetall(f"user:{user_id}:tokens") or {}

            return {
                "total_calls": int(total_calls),
                "cache_hits": int(cache_hits),
                "tokens": {k: int(v) for k, v in tokens.items()}
            }
        except Exception as e:
            logger.error(f"Failed to get user metrics: {e}", exc_info=True)
            return {}

    async def get_global_metrics(self) -> dict:
        """
        Get global metrics across all users.
        """
        try:
            total_calls = await self.redis.get("global:total_calls") or 0
            cache_hits = await self.redis.get("global:cache_hits") or 0
            tokens = await self.redis.hgetall("global:tokens") or {}

            return {
                "total_calls": int(total_calls),
                "cache_hits": int(cache_hits),
                "tokens": {k: int(v) for k, v in tokens.items()}
            }
        except Exception as e:
            logger.error(f"Failed to get global metrics: {e}", exc_info=True)
            return {} 