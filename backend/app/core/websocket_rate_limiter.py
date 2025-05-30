"""
WebSocket rate limiting functionality.
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Set, Tuple, Any
from app.core.redis import RedisClient
import json
import logging
from zoneinfo import ZoneInfo
from redis.asyncio import Redis
import asyncio
import os
from app.metrics import rate_limit_violations, backoff_active

logger = logging.getLogger(__name__)
UTC = ZoneInfo("UTC")

class WebSocketRateLimiter:
    """Rate limiter for WebSocket connections and messages."""
    
    # Redis key prefixes
    CONNECTION_COUNT_PREFIX = "ws:conn_count"
    MESSAGE_COUNT_PREFIX = "ws:msg_count"
    
    BASE_BACKOFF_SECONDS = 2
    MAX_BACKOFF_SECONDS = 300  # 5 minutes
    BACKOFF_RESET_SECONDS = 600  # 10 minutes of quiet resets violations
    
    def __init__(
        self,
        redis: Optional[Redis] = None,
        max_connections: int = 5,
        messages_per_minute: int = 60,
        messages_per_hour: int = 1000,
        messages_per_day: int = 10000,
        max_messages_per_second: int = 10,
        rate_limit_window: int = 60,
        connect_timeout: float = 5.0,
        message_timeout: float = 5.0,
        max_messages_per_minute: Optional[int] = None,  # For backward compatibility
        max_messages_per_hour: Optional[int] = None,    # For backward compatibility
        max_messages_per_day: Optional[int] = None,     # For backward compatibility
        client_type_limits: Optional[dict] = None,      # NEW
    ):
        """Initialize rate limiter.
        
        Args:
            redis: Optional Redis client
            max_connections: Maximum concurrent connections per user
            messages_per_minute: Maximum messages per minute
            messages_per_hour: Maximum messages per hour
            messages_per_day: Maximum messages per day
            max_messages_per_second: Maximum messages per second
            rate_limit_window: Rate limit window in seconds
            connect_timeout: Connection timeout in seconds
            message_timeout: Message timeout in seconds
            max_messages_per_minute: Alias for messages_per_minute (deprecated)
            max_messages_per_hour: Alias for messages_per_hour (deprecated)
            max_messages_per_day: Alias for messages_per_day (deprecated)
            client_type_limits: Optional client type-specific rate limits
        """
        self.redis = redis
        self.max_connections = max_connections
        self.messages_per_minute = max_messages_per_minute or messages_per_minute
        self.messages_per_hour = max_messages_per_hour or messages_per_hour
        self.messages_per_day = max_messages_per_day or messages_per_day
        self.max_messages_per_second = max_messages_per_second
        self.rate_limit_window = rate_limit_window
        self.connect_timeout = connect_timeout
        self.message_timeout = message_timeout
        self._connection_counts: Dict[str, int] = {}
        self._message_counts: Dict[str, Dict[str, int]] = {}
        self.client_type_limits = client_type_limits or {
            "authenticated": {
                "second": self.max_messages_per_second,
                "minute": self.messages_per_minute,
                "hour": self.messages_per_hour,
                "day": self.messages_per_day,
            },
            "anonymous": {
                "second": max(1, self.max_messages_per_second // 2),
                "minute": max(1, self.messages_per_minute // 4),
                "hour": max(1, self.messages_per_hour // 4),
                "day": max(1, self.messages_per_day // 4),
            }
        }
        
    def _get_connection_key(self, client_id: str, user_id: str, ip_address: str) -> str:
        """Get Redis key for connection tracking.
        
        Args:
            client_id: Client ID
            user_id: User ID
            ip_address: IP address
            
        Returns:
            str: Redis key
        """
        return f"ws:conn:{user_id}:{ip_address}:{client_id}"
        
    def _get_message_key(self, client_id: str, user_id: str, ip_address: str, window: str) -> str:
        """Get Redis key for message tracking.
        
        Args:
            client_id: Client ID
            user_id: User ID
            ip_address: IP address
            window: Time window (second, minute, hour, day)
            
        Returns:
            str: Redis key
        """
        return f"ws:msg:{user_id}:{ip_address}:{client_id}:{window}"
        
    async def check_connection_limit(
        self,
        client_id: str,
        user_id: str,
        ip_address: str
    ) -> Tuple[bool, Optional[str]]:
        """Check if connection is allowed.
        
        Args:
            client_id: Client ID
            user_id: User ID
            ip_address: IP address
            
        Returns:
            Tuple[bool, Optional[str]]: (allowed, reason if not allowed)
        """
        if os.environ.get("ENVIRONMENT") == "test" or os.environ.get("USE_MOCK_WEBSOCKET") == "1":
            return True, None
        key = self._get_connection_key(client_id, user_id, ip_address)
        user_key = f"{self.CONNECTION_COUNT_PREFIX}:{user_id}"
        
        if self.redis:
            try:
                count = await self.redis.get(key)
                count = int(count) if count else 0
                user_count = await self.redis.get(user_key)
                user_count = int(user_count) if user_count else 0
            except Exception as e:
                logger.error(f"Redis error in check_connection_limit: {e}")
                count = self._connection_counts.get(key, 0)
                user_count = self._connection_counts.get(user_key, 0)
        else:
            count = self._connection_counts.get(key, 0)
            user_count = self._connection_counts.get(user_key, 0)
        print(f"[DEBUG] check_connection_limit: key={key} count={count} user_key={user_key} user_count={user_count} max_connections={self.max_connections}")
        logger.debug(f"[RateLimiter] check_connection_limit: key={key} count={count} user_key={user_key} user_count={user_count} max_connections={self.max_connections}")
        if user_count >= self.max_connections:
            return False, f"Maximum connections ({self.max_connections}) exceeded for user"
        if count >= self.max_connections:
            return False, f"Maximum connections ({self.max_connections}) exceeded for connection key"
        return True, None
        
    async def increment_connection_count(
        self,
        client_id: str,
        user_id: str,
        ip_address: str
    ) -> None:
        """Increment connection count for both per-connection and per-user aggregate keys."""
        conn_key = self._get_connection_key(client_id, user_id, ip_address)
        user_key = f"{self.CONNECTION_COUNT_PREFIX}:{user_id}"
        print(f"[DEBUG] increment_connection_count: conn_key={conn_key} user_key={user_key}")
        logger.debug(f"[RateLimiter] INCR conn_key={conn_key} user_key={user_key}")
        if self.redis:
            try:
                new_conn = await self.redis.incr(conn_key)
                await self.redis.expire(conn_key, self.rate_limit_window)
                new_user = await self.redis.incr(user_key)
                await self.redis.expire(user_key, self.rate_limit_window)
                logger.debug(f"[RateLimiter] After INCR: {conn_key}={new_conn}, {user_key}={new_user}")
            except Exception as e:
                logger.error(f"Redis error in increment_connection_count: {e}")
                self._connection_counts[conn_key] = self._connection_counts.get(conn_key, 0) + 1
                self._connection_counts[user_key] = self._connection_counts.get(user_key, 0) + 1
        else:
            self._connection_counts[conn_key] = self._connection_counts.get(conn_key, 0) + 1
            self._connection_counts[user_key] = self._connection_counts.get(user_key, 0) + 1
            print(f"[DEBUG] (no redis) After INCR: {conn_key}={self._connection_counts[conn_key]}, {user_key}={self._connection_counts[user_key]}")
            logger.debug(f"[RateLimiter] (no redis) After INCR: {conn_key}={self._connection_counts[conn_key]}, {user_key}={self._connection_counts[user_key]}")
            
    async def decrement_connection_count(
        self,
        client_id: str,
        user_id: str,
        ip_address: str
    ) -> None:
        """Decrement connection count for both per-connection and per-user aggregate keys."""
        conn_key = self._get_connection_key(client_id, user_id, ip_address)
        user_key = f"{self.CONNECTION_COUNT_PREFIX}:{user_id}"
        print(f"[DEBUG] decrement_connection_count: conn_key={conn_key} user_key={user_key}")
        logger.debug(f"[RateLimiter] DECR conn_key={conn_key} user_key={user_key}")
        if self.redis:
            try:
                new_conn = await self.redis.decr(conn_key)
                user_count = await self.redis.decr(user_key)
                if user_count < 0:
                    await self.redis.set(user_key, 0)
                logger.debug(f"[RateLimiter] After DECR: {conn_key}={new_conn}, {user_key}={user_count}")
            except Exception as e:
                logger.error(f"Redis error in decrement_connection_count: {e}")
                count = self._connection_counts.get(conn_key, 0)
                if count > 0:
                    self._connection_counts[conn_key] = count - 1
                user_count = self._connection_counts.get(user_key, 0)
                if user_count > 0:
                    self._connection_counts[user_key] = user_count - 1
        else:
            count = self._connection_counts.get(conn_key, 0)
            if count > 0:
                self._connection_counts[conn_key] = count - 1
            user_count = self._connection_counts.get(user_key, 0)
            if user_count > 0:
                self._connection_counts[user_key] = user_count - 1
            print(f"[DEBUG] (no redis) After DECR: {conn_key}={self._connection_counts.get(conn_key, 0)}, {user_key}={self._connection_counts.get(user_key, 0)}")
            logger.debug(f"[RateLimiter] (no redis) After DECR: {conn_key}={self._connection_counts.get(conn_key, 0)}, {user_key}={self._connection_counts.get(user_key, 0)}")
                
    async def get_backoff_key(self, identifier: str) -> str:
        return f"ws:backoff:{identifier}"

    async def get_violation_key(self, identifier: str) -> str:
        return f"ws:violations:{identifier}"

    async def get_backoff(self, identifier: str) -> int:
        key = await self.get_backoff_key(identifier)
        if self.redis:
            ttl = await self.redis.ttl(key)
            return max(ttl, 0)
        return 0

    async def increment_violation(self, identifier: str) -> int:
        key = await self.get_violation_key(identifier)
        if self.redis:
            count = await self.redis.incr(key)
            await self.redis.expire(key, self.BACKOFF_RESET_SECONDS)
            return int(count)
        return 1

    async def reset_violations(self, identifier: str):
        key = await self.get_violation_key(identifier)
        if self.redis:
            await self.redis.delete(key)

    async def set_backoff(self, identifier: str, seconds: int):
        key = await self.get_backoff_key(identifier)
        if self.redis:
            await self.redis.set(key, "1", ex=seconds)

    async def check_backoff(self, identifier: str) -> int:
        return await self.get_backoff(identifier)

    async def handle_rate_limit_violation(self, identifier: str) -> int:
        violations = await self.increment_violation(identifier)
        backoff = min(self.BASE_BACKOFF_SECONDS * (2 ** (violations - 1)), self.MAX_BACKOFF_SECONDS)
        await self.set_backoff(identifier, backoff)
        return backoff

    async def check_message_limit(
        self,
        client_id: str,
        user_id: str,
        ip_address: str,
        client_type: str = "anonymous",
        is_system_message: bool = False
    ) -> Tuple[bool, Optional[str]]:
        """Check if message is allowed.
        
        Args:
            client_id: Client ID
            user_id: User ID
            ip_address: IP address
            client_type: Client type
            is_system_message: Whether this is a system message
            
        Returns:
            Tuple[bool, Optional[str]]: (allowed, reason if not allowed)
        """
        if os.environ.get("ENVIRONMENT") == "test" or os.environ.get("USE_MOCK_WEBSOCKET") == "1":
            return True, None
        if is_system_message:
            return True, None
            
        identifier = f"{user_id}:{ip_address}:{client_id}"
        backoff = await self.check_backoff(identifier)
        if backoff > 0:
            return False, f"Rate limit exceeded. Please wait {backoff} seconds before retrying."
            
        now = datetime.now(UTC)
        # Use client_type-specific limits
        limits = self.client_type_limits.get(client_type, self.client_type_limits["anonymous"])
        windows = {
            "second": (1, limits["second"]),
            "minute": (60, limits["minute"]),
            "hour": (3600, limits["hour"]),
            "day": (86400, limits["day"])
        }
        
        for window, (seconds, limit) in windows.items():
            key = self._get_message_key(client_id, user_id, ip_address, window)
            
            if self.redis:
                try:
                    count = await self.redis.get(key)
                    count = int(count) if count else 0
                except Exception as e:
                    logger.error(f"Redis error in check_message_limit: {e}")
                    count = self._message_counts.get(key, {}).get(window, 0)
            else:
                count = self._message_counts.get(key, {}).get(window, 0)
            print(f"[DEBUG] check_message_limit: client_id={client_id} user_id={user_id} ip_address={ip_address} window={window} count={count} limit={limit}")
            if count >= limit:
                await self.handle_rate_limit_violation(identifier)
                return False, f"Rate limit exceeded ({limit} messages per {window}). Backoff applied."
            else:
                logger.info(f"[RateLimiter] Allowed: client_id={client_id}, user_id={user_id}, ip={ip_address}, window={window}, limit={limit}, count={count}")
        
        await self.reset_violations(identifier)  # Reset on success
        return True, None
        
    async def increment_message_count(
        self,
        client_id: str,
        user_id: str,
        ip_address: str
    ) -> None:
        """Increment message count.
        
        Args:
            client_id: Client ID
            user_id: User ID
            ip_address: IP address
        """
        windows = {
            "second": 1,
            "minute": 60,
            "hour": 3600,
            "day": 86400
        }
        
        for window, seconds in windows.items():
            key = self._get_message_key(client_id, user_id, ip_address, window)
            
            if self.redis:
                try:
                    new_val = await self.redis.incr(key)
                    await self.redis.expire(key, seconds)
                    print(f"[DEBUG] increment_message_count: key={key} new_val={new_val}")
                except Exception as e:
                    logger.error(f"Redis error in increment_message_count: {e}")
                    if key not in self._message_counts:
                        self._message_counts[key] = {}
                    self._message_counts[key][window] = self._message_counts[key].get(window, 0) + 1
            else:
                if key not in self._message_counts:
                    self._message_counts[key] = {}
                self._message_counts[key][window] = self._message_counts[key].get(window, 0) + 1
                print(f"[DEBUG] (no redis) increment_message_count: key={key} val={self._message_counts[key][window]}")
                
    async def get_message_count(self, identifier: str) -> int:
        """Get the current message count for an identifier.
        
        Args:
            identifier: The identifier to check (user ID, IP, or client ID)
            
        Returns:
            int: Current message count for the identifier
        """
        try:
            minute_key = f"{self.MESSAGE_COUNT_PREFIX}:minute:{identifier}"
            count = await self.redis.get(minute_key)
            return int(count) if count else 0
        except Exception as e:
            logger.error(f"Error getting message count: {e}")
            return 0

    async def get_connection_count(self, identifier: str) -> int:
        """Get current aggregate connection count for a user (per-user key)."""
        user_key = f"{self.CONNECTION_COUNT_PREFIX}:{identifier}"
        logger.debug(f"[RateLimiter] GET user_key={user_key}")
        try:
            count = await self.redis.get(user_key)
            logger.debug(f"[RateLimiter] GET result: {user_key}={count}")
            return int(count) if count else 0
        except Exception as e:
            logger.error(f"Error getting connection count: {e}")
            return self._connection_counts.get(user_key, 0)

    async def clear_connection_count(self, identifier: str) -> None:
        """Clear the connection count for an identifier.
        
        Args:
            identifier: User ID, IP, or client ID
        """
        try:
            key = f"{self.CONNECTION_COUNT_PREFIX}:{identifier}"
            await self.redis.delete(key)
        except Exception as e:
            logger.error(f"Error clearing connection count: {e}")

    async def clear_message_count(self, identifier: str) -> None:
        """Clear the message count for an identifier.
        
        Args:
            identifier: User ID, IP, or client ID
        """
        try:
            # Clear all time-based counters
            pipe = await self.redis.pipeline()
            await pipe.delete(f"{self.MESSAGE_COUNT_PREFIX}:second:{identifier}")
            await pipe.delete(f"{self.MESSAGE_COUNT_PREFIX}:minute:{identifier}")
            await pipe.delete(f"{self.MESSAGE_COUNT_PREFIX}:hour:{identifier}")
            await pipe.delete(f"{self.MESSAGE_COUNT_PREFIX}:day:{identifier}")
            await pipe.execute()
        except Exception as e:
            logger.error(f"Error clearing message count: {e}")

    async def clear_all(self) -> None:
        """Clear all rate limit data."""
        if self.redis:
            try:
                # Clear all WebSocket-related keys
                keys = await self.redis.keys("ws:*")
                if keys:
                    await self.redis.delete(*keys)
            except Exception as e:
                logger.error(f"Redis error in clear_all: {e}")
                
        self._connection_counts.clear()
        self._message_counts.clear()

    async def add_rate_limit_block(self, identifier: str, duration: int) -> None:
        """Add a rate limit block for an identifier.
        
        Args:
            identifier: User ID or IP address
            duration: Block duration in seconds
        """
        try:
            block_until = datetime.now(UTC) + timedelta(seconds=duration)
            block_data = {
                "until": block_until.timestamp(),
                "reason": f"Rate limit exceeded, blocked for {duration} seconds"
            }
            
            await self.redis.set(
                f"rate_limit_block:{identifier}",
                json.dumps(block_data),
                ex=duration
            )
        except Exception as e:
            logger.error(f"Error adding rate limit block: {e}")

    async def clear_rate_limit_block(self, identifier: str) -> None:
        """Clear rate limit block for an identifier.
        
        Args:
            identifier: User ID or IP address
        """
        try:
            await self.redis.delete(f"rate_limit_block:{identifier}")
        except Exception as e:
            logger.error(f"Error clearing rate limit block: {e}")

    async def get_message_counts(self, identifier: str) -> Dict[str, int]:
        """Get current message counts for an identifier.
        
        Args:
            identifier: User ID or IP address
            
        Returns:
            Dict[str, int]: Message counts by interval
        """
        try:
            pipe = await self.redis.pipeline()
            await pipe.get(f"messages:minute:{identifier}")
            await pipe.get(f"messages:hour:{identifier}")
            await pipe.get(f"messages:day:{identifier}")
            
            if self.max_messages_per_second:
                await pipe.get(f"messages:second:{identifier}")
            
            results = await pipe.execute()
            
            counts = {
                "minute": int(results[0]) if results[0] else 0,
                "hour": int(results[1]) if results[1] else 0,
                "day": int(results[2]) if results[2] else 0
            }
            
            if self.max_messages_per_second:
                counts["second"] = int(results[3]) if results[3] else 0
            
            return counts
            
        except Exception as e:
            logger.error(f"Error getting message counts: {e}")
            return {"minute": 0, "hour": 0, "day": 0}

    async def release_connection(
        self,
        client_id: str,
        user_id: str,
        ip_address: str
    ) -> None:
        """Release a connection and clean up rate limit data.
        
        Args:
            client_id: Client ID
            user_id: User ID
            ip_address: IP address
        """
        # Decrement connection count
        await self.decrement_connection_count(client_id, user_id, ip_address)
        
        # Clear message counts for this connection
        for window in ["second", "minute", "hour", "day"]:
            key = self._get_message_key(client_id, user_id, ip_address, window)
            if self.redis:
                try:
                    await self.redis.delete(key)
                except Exception as e:
                    logger.error(f"Redis error in release_connection: {e}")
                    if key in self._message_counts:
                        del self._message_counts[key]
            else:
                if key in self._message_counts:
                    del self._message_counts[key] 

    async def get_user_message_count(self, user_id: str, window: str = "minute") -> int:
        """Sum all per-user message counts for the given window."""
        pattern = f"ws:msg:{user_id}:*:*:{window}"
        if not self.redis:
            # Fallback to in-memory counts if no redis
            total = 0
            for key, counts in self._message_counts.items():
                if key.startswith(f"ws:msg:{user_id}:") and key.endswith(f":{window}"):
                    print(f"[DEBUG] get_user_message_count (no redis): key={key} val={counts.get(window, 0)}")
                    total += counts.get(window, 0)
            print(f"[DEBUG] get_user_message_count (no redis): total={total}")
            return total
        keys = await self.redis.keys(pattern)
        print(f"[DEBUG] get_user_message_count: pattern={pattern} keys={keys}")
        total = 0
        for key in keys:
            val = await self.redis.get(key)
            print(f"[DEBUG] get_user_message_count: key={key} val={val}")
            total += int(val) if val else 0
        print(f"[DEBUG] get_user_message_count: total={total}")
        return total 

    def record_violation(self, user_id):
        rate_limit_violations.labels(user_id=user_id).inc()

    def record_backoff(self, client_id):
        backoff_active.inc()

    def clear_backoff(self, client_id):
        backoff_active.dec() 