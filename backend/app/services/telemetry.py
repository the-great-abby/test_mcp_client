from redis.asyncio import Redis
from typing import Dict, Any, Optional

class TelemetryService:
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self.user_metrics_key = lambda user_id: f"user:{user_id}:metrics"
        self.global_metrics_key = "global:metrics"

    async def record_model_call(
        self, 
        user_id: str, 
        model: str, 
        prompt_tokens: int, 
        completion_tokens: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Record metrics for a model call."""
        user_key = self.user_metrics_key(user_id)
        
        # Use pipeline for atomic updates
        pipe = self.redis.pipeline()
        
        # Update user metrics
        pipe.hincrby(user_key, "total_calls", 1)
        pipe.hincrby(user_key, "total_prompt_tokens", prompt_tokens)
        pipe.hincrby(user_key, "total_completion_tokens", completion_tokens)
        
        # Update global metrics
        pipe.hincrby(self.global_metrics_key, "total_calls", 1)
        pipe.hincrby(self.global_metrics_key, "total_prompt_tokens", prompt_tokens)
        pipe.hincrby(self.global_metrics_key, "total_completion_tokens", completion_tokens)
        
        await pipe.execute()

    async def record_cache_hit(self, user_id: str, tokens_saved: int) -> None:
        """Record metrics for a cache hit."""
        user_key = self.user_metrics_key(user_id)
        
        pipe = self.redis.pipeline()
        
        # Update user metrics
        pipe.hincrby(user_key, "cache_hits", 1)
        pipe.hincrby(user_key, "tokens_saved", tokens_saved)
        
        # Update global metrics
        pipe.hincrby(self.global_metrics_key, "cache_hits", 1)
        pipe.hincrby(self.global_metrics_key, "tokens_saved", tokens_saved)
        
        await pipe.execute()

    async def get_user_metrics(self, user_id: str) -> Dict[str, int]:
        """Get metrics for a specific user."""
        metrics = await self.redis.hgetall(self.user_metrics_key(user_id))
        return {k: int(v) for k, v in metrics.items()}

    async def get_global_metrics(self) -> Dict[str, int]:
        """Get global metrics across all users."""
        metrics = await self.redis.hgetall(self.global_metrics_key)
        return {k: int(v) for k, v in metrics.items()} 