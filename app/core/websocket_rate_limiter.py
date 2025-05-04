class WebSocketRateLimiter:
    """Rate limiter for WebSocket connections and messages."""
    
    def __init__(
        self,
        redis,
        max_connections: int = 50,
        window_seconds: int = 60,
        max_messages: int = 100
    ):
        """Initialize rate limiter.
        
        Args:
            redis: Redis client instance
            max_connections: Maximum concurrent connections per IP
            window_seconds: Time window for rate limiting in seconds
            max_messages: Maximum messages per window per IP
        """
        self.redis = redis
        self.max_connections = max_connections
        self.window_seconds = window_seconds
        self.max_messages = max_messages
        self.connection_key_prefix = "ws:conn"
        self.message_key_prefix = "ws:msg"
    
    async def check_connection_limit(self, client_ip: str) -> bool:
        """Check if client has exceeded connection limit.
        
        Args:
            client_ip: Client IP address
            
        Returns:
            bool: True if limit not exceeded
        """
        key = f"{self.connection_key_prefix}:{client_ip}"
        count = await self.redis.get(key)
        count = int(count) if count else 0
        return count < self.max_connections
    
    async def increment_connection_count(self, client_ip: str) -> None:
        """Increment connection count for client IP.
        
        Args:
            client_ip: Client IP address
        """
        key = f"{self.connection_key_prefix}:{client_ip}"
        await self.redis.incr(key)
        await self.redis.expire(key, self.window_seconds)
    
    async def decrement_connection_count(self, client_ip: str) -> None:
        """Decrement connection count for client IP.
        
        Args:
            client_ip: Client IP address
        """
        key = f"{self.connection_key_prefix}:{client_ip}"
        count = await self.redis.get(key)
        if count and int(count) > 0:
            await self.redis.decr(key)
    
    async def check_message_limit(self, client_ip: str) -> bool:
        """Check if client has exceeded message rate limit.
        
        Args:
            client_ip: Client IP address
            
        Returns:
            bool: True if limit not exceeded
        """
        key = f"{self.message_key_prefix}:{client_ip}"
        count = await self.redis.get(key)
        count = int(count) if count else 0
        return count < self.max_messages
    
    async def increment_message_count(self, client_ip: str) -> None:
        """Increment message count for client IP.
        
        Args:
            client_ip: Client IP address
        """
        key = f"{self.message_key_prefix}:{client_ip}"
        await self.redis.incr(key)
        await self.redis.expire(key, self.window_seconds)
    
    async def clear_connection_count(self, client_ip: str) -> None:
        """Clear connection count for a client IP.
        
        Args:
            client_ip: The client IP to clear
        """
        key = f"{self.connection_key_prefix}:{client_ip}"
        await self.redis.delete(key)
    
    async def clear_message_count(self, client_ip: str) -> None:
        """Clear message count for a client IP.
        
        Args:
            client_ip: The client IP to clear
        """
        key = f"{self.message_key_prefix}:{client_ip}"
        await self.redis.delete(key)
    
    async def clear_all(self) -> None:
        """Clear all rate limit data."""
        # Clear connection counts
        pattern = f"{self.connection_key_prefix}:*"
        keys = await self.redis.keys(pattern)
        if keys:
            await self.redis.delete(*keys)
        
        # Clear message counts
        pattern = f"{self.message_key_prefix}:*"
        keys = await self.redis.keys(pattern)
        if keys:
            await self.redis.delete(*keys) 