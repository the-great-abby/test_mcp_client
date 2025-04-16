"""
Cache utilities for model responses and other data.
"""
from typing import Optional, Any, Dict
import json
from datetime import timedelta
import hashlib
import logging
from redis import Redis
from .config import settings

logger = logging.getLogger(__name__)

class ModelResponseCache:
    """Cache handler for model responses."""
    
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self.default_ttl = timedelta(hours=24)  # Cache responses for 24 hours by default
    
    def _generate_cache_key(self, messages: list, system_prompt: Optional[str] = None) -> str:
        """Generate a unique cache key for the conversation context."""
        # Create a string representation of the input
        cache_input = {
            "messages": messages,
            "system_prompt": system_prompt,
            "model": settings.MODEL_NAME,
            "temperature": settings.MODEL_TEMPERATURE
        }
        
        # Generate a hash of the input
        cache_key = hashlib.sha256(
            json.dumps(cache_input, sort_keys=True).encode()
        ).hexdigest()
        
        return f"model_response:{cache_key}"
    
    async def get_cached_response(
        self,
        messages: list,
        system_prompt: Optional[str] = None
    ) -> Optional[str]:
        """
        Get a cached model response if it exists.
        
        Args:
            messages: List of conversation messages
            system_prompt: Optional system prompt
            
        Returns:
            Cached response if found, None otherwise
        """
        try:
            cache_key = self._generate_cache_key(messages, system_prompt)
            cached = self.redis.get(cache_key)
            
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
        """
        Cache a model response.
        
        Args:
            messages: List of conversation messages
            response: Model response to cache
            system_prompt: Optional system prompt
            ttl: Optional time-to-live for the cache entry
        """
        try:
            cache_key = self._generate_cache_key(messages, system_prompt)
            self.redis.setex(
                cache_key,
                ttl or self.default_ttl,
                response
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
        """
        Invalidate a cached response.
        
        Args:
            messages: List of conversation messages
            system_prompt: Optional system prompt
        """
        try:
            cache_key = self._generate_cache_key(messages, system_prompt)
            self.redis.delete(cache_key)
            
            logger.info("Invalidated cached response", extra={
                "cache_key": cache_key,
                "model": settings.MODEL_NAME
            })
            
        except Exception as e:
            logger.error("Error invalidating cache", exc_info=True) 