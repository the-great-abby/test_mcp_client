"""
WebSocket rate limiting functionality.
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Set
from app.core.redis import RedisClient
import json
import logging
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)
UTC = ZoneInfo("UTC")

class WebSocketRateLimiter:
    """Rate limiter for WebSocket connections and messages."""
    
    def __init__(
        self,
        redis: RedisClient,
        max_connections_per_user: int = 5,
        max_connections_per_ip: int = 20,
        connection_window_seconds: int = 60,
        max_connections_per_window: int = 50,
        message_window_seconds: int = 1,
        max_messages_per_window: int = 10
    ):
        """Initialize the WebSocket rate limiter.
        
        Args:
            redis: Redis client for distributed rate limiting
            max_connections_per_user: Maximum concurrent connections per user
            max_connections_per_ip: Maximum concurrent connections per IP
            connection_window_seconds: Time window for connection rate limiting
            max_connections_per_window: Maximum new connections per window
            message_window_seconds: Time window for message rate limiting
            max_messages_per_window: Maximum messages per window
        """
        self.redis = redis
        self.max_connections_per_user = max_connections_per_user
        self.max_connections_per_ip = max_connections_per_ip
        self.connection_window_seconds = connection_window_seconds
        self.max_connections_per_window = max_connections_per_window
        self.message_window_seconds = message_window_seconds
        self.max_messages_per_window = max_messages_per_window
    
    def _get_connection_key(self, identifier: str) -> str:
        """Get Redis key for connection rate limiting."""
        return f"ws:conn_limit:{identifier}"
    
    def _get_message_key(self, identifier: str) -> str:
        """Get Redis key for message rate limiting."""
        return f"ws:msg_limit:{identifier}"
        
    def _get_active_connections_key(self, identifier: str) -> str:
        """Get Redis key for active connections tracking."""
        return f"ws:active:{identifier}"
    
    async def check_connection_limit(
        self,
        client_id: str,
        user_id: Optional[str],
        ip_address: str
    ) -> tuple[bool, Optional[str]]:
        """Check if a new connection should be allowed.
        
        Args:
            client_id: Unique identifier for the client
            user_id: Optional user ID for authenticated connections
            ip_address: IP address of the client
            
        Returns:
            Tuple of (allowed: bool, reason: Optional[str])
        """
        try:
            # Check concurrent connection limits using Redis
            pipe = self.redis.pipeline()
            
            # Check user connections if authenticated
            if user_id:
                user_key = self._get_active_connections_key(f"user:{user_id}")
                await pipe.hlen(user_key)
            else:
                await pipe.echo("0")  # Placeholder for unauthenticated users
                
            # Check IP connections
            ip_key = self._get_active_connections_key(f"ip:{ip_address}")
            await pipe.hlen(ip_key)
            
            # Execute pipeline
            results = await pipe.execute()
            user_conn_count = int(results[0]) if isinstance(results[0], bytes) else 0
            ip_conn_count = int(results[1]) if isinstance(results[1], bytes) else 0
            
            # Check limits
            if user_id and user_conn_count >= self.max_connections_per_user:
                return False, "Too many concurrent connections for user"
                
            if ip_conn_count >= self.max_connections_per_ip:
                return False, "Too many concurrent connections from IP"
            
            # Check rate limits
            now = datetime.now(UTC)
            window_start = int(now.timestamp())
            
            # Use IP if no user_id
            identifier = user_id if user_id else ip_address
            key = self._get_connection_key(identifier)
            
            # Get current count
            count = await self.redis.get(key)
            if count is None:
                # First connection in window
                await self.redis.set(key, "1", ex=self.connection_window_seconds)
                return True, None
            
            try:
                current = int(count.decode())
                if current >= self.max_connections_per_window:
                    return False, "Connection rate limit exceeded"
                
                # Increment counter
                pipe = self.redis.pipeline()
                await pipe.incr(key)
                await pipe.expire(key, self.connection_window_seconds)
                await pipe.execute()
                return True, None
                
            except (ValueError, UnicodeDecodeError):
                # Reset corrupted counter
                await self.redis.delete(key)
                await self.redis.set(key, "1", ex=self.connection_window_seconds)
                return True, None
                
        except Exception as e:
            logger.error(f"Error checking connection limit: {str(e)}", exc_info=True)
            # Allow connection on error to prevent blocking all traffic
            return True, None
    
    async def check_message_limit(
        self,
        client_id: str,
        user_id: Optional[str],
        ip_address: str
    ) -> tuple[bool, Optional[str]]:
        """Check if a new message should be allowed.
        
        Args:
            client_id: Unique identifier for the client
            user_id: Optional user ID for authenticated connections
            ip_address: IP address of the client
            
        Returns:
            Tuple of (allowed: bool, reason: Optional[str])
        """
        try:
            # Use IP if no user_id
            identifier = user_id if user_id else ip_address
            key = self._get_message_key(identifier)
            
            # Get current count
            count = await self.redis.get(key)
            if count is None:
                # First message in window
                await self.redis.set(key, "1", ex=self.message_window_seconds)
                return True, None
            
            try:
                current = int(count.decode())
                if current >= self.max_messages_per_window:
                    return False, "Message rate limit exceeded"
                
                # Increment counter
                pipe = self.redis.pipeline()
                await pipe.incr(key)
                await pipe.expire(key, self.message_window_seconds)
                await pipe.execute()
                return True, None
                
            except (ValueError, UnicodeDecodeError):
                # Reset corrupted counter
                await self.redis.delete(key)
                await self.redis.set(key, "1", ex=self.message_window_seconds)
                return True, None
                
        except Exception as e:
            logger.error(f"Error checking message limit: {str(e)}", exc_info=True)
            # Allow message on error to prevent blocking all traffic
            return True, None
    
    async def add_connection(self, client_id: str, user_id: Optional[str], ip_address: str):
        """Track a new connection."""
        try:
            pipe = self.redis.pipeline()
            
            # Add to user connections if authenticated
            if user_id:
                user_key = self._get_active_connections_key(f"user:{user_id}")
                await pipe.hset(user_key, client_id, "1")
            
            # Add to IP connections
            ip_key = self._get_active_connections_key(f"ip:{ip_address}")
            await pipe.hset(ip_key, client_id, "1")
            
            await pipe.execute()
            
        except Exception as e:
            logger.error(f"Error adding connection: {str(e)}", exc_info=True)
    
    async def remove_connection(self, client_id: str, user_id: Optional[str], ip_address: str):
        """Remove a tracked connection."""
        try:
            pipe = self.redis.pipeline()
            
            # Remove from user connections if authenticated
            if user_id:
                user_key = self._get_active_connections_key(f"user:{user_id}")
                await pipe.hdel(user_key, client_id)
            
            # Remove from IP connections
            ip_key = self._get_active_connections_key(f"ip:{ip_address}")
            await pipe.hdel(ip_key, client_id)
            
            await pipe.execute()
            
        except Exception as e:
            logger.error(f"Error removing connection: {str(e)}", exc_info=True) 