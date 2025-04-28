"""
WebSocket connection management utilities.
"""
from typing import Dict, Set, Any, Optional, List
from fastapi import WebSocket
import logging
from collections import defaultdict, deque
from app.models import User
from datetime import datetime
from pytz import UTC
from app.core.connection_metadata import ConnectionMetadata
from app.core.connection_state import ConnectionState
from app.core.chat_message import ChatMessage
from app.core.websocket_rate_limiter import WebSocketRateLimiter
import websockets
from app.utils import get_client_ip
import asyncio
from app.core.redis import RedisClient
from starlette.websockets import WebSocketDisconnect

logger = logging.getLogger(__name__)

# Constants for WebSocket configuration
PING_TIMEOUT = 60  # seconds
MAX_CONNECTIONS_PER_USER = 5
MAX_MESSAGE_HISTORY = 100
RATE_LIMIT = 10  # messages per second
RATE_LIMIT_WINDOW = 60  # seconds

class WebSocketManager:
    """Manages active WebSocket connections and message history."""
    
    def __init__(self, redis_client: Optional[RedisClient] = None):
        # Maps client_id to WebSocket connection
        self.active_connections: Dict[str, WebSocket] = {}
        # Maps client_id to connection metadata
        self.connection_metadata: Dict[str, ConnectionMetadata] = {}
        # Maps user_id to set of their client_ids
        self.user_connections: Dict[str, Set[str]] = defaultdict(set)
        # Message history as a deque with max size
        self.message_history: deque[ChatMessage] = deque(maxlen=MAX_MESSAGE_HISTORY)
        # Maps message_id to ChatMessage for tracking
        self.message_by_id: Dict[str, ChatMessage] = {}
        
        # Configuration properties
        self.ping_timeout = PING_TIMEOUT
        self.max_connections_per_user = MAX_CONNECTIONS_PER_USER
        self.max_message_history = MAX_MESSAGE_HISTORY
        self.rate_limit = RATE_LIMIT
        self.rate_limit_window = RATE_LIMIT_WINDOW
        
        # Redis client for distributed deployments
        self.redis_client = redis_client
        
        # Rate limiter instance with configuration
        self.rate_limiter = WebSocketRateLimiter(
            redis=redis_client,
            max_connections_per_user=MAX_CONNECTIONS_PER_USER,
            max_connections_per_ip=20,  # Default from rate limiter
            connection_window_seconds=RATE_LIMIT_WINDOW,
            max_connections_per_window=50,  # Default from rate limiter
            message_window_seconds=1,  # 1 second window for message rate limiting
            max_messages_per_window=RATE_LIMIT
        )
    
    async def connect(self, client_id: str, websocket: WebSocket, user_id: Optional[str] = None) -> bool:
        """
        Connect a new WebSocket client.
        
        Args:
            client_id: Unique identifier for the client
            websocket: The WebSocket connection
            user_id: Optional user ID for authenticated connections
            
        Returns:
            bool: True if connection was successful, False otherwise
        """
        try:
            # Check connection limits for authenticated users
            if user_id and len(self.user_connections[user_id]) >= MAX_CONNECTIONS_PER_USER:
                logger.warning(f"User {user_id} exceeded max connections")
                return False
            
            # Store connection info
            ip_address = get_client_ip(websocket)
            self.active_connections[client_id] = websocket
            self.connection_metadata[client_id] = ConnectionMetadata(
                client_id=client_id,
                user_id=user_id,
                connected_at=datetime.now(UTC),
                last_seen=datetime.now(UTC),
                state=ConnectionState.CONNECTED,
                is_typing=False,
                ip_address=ip_address
            )
            
            if user_id:
                self.user_connections[user_id].add(client_id)
                logger.debug(f"Added client {client_id} to user {user_id} connections")
            
            # 1. Send welcome message first
            logger.debug("Sending welcome message...")
            welcome_msg = ChatMessage(
                type="welcome",
                content="Connected to chat server",
                metadata={
                    "client_id": client_id,
                    "user_id": user_id
                }
            )
            logger.debug(f"Welcome message type: {welcome_msg.type}")
            await self.send_message(client_id, welcome_msg)
            logger.debug("Welcome message sent")
            
            # 2. Send message history if any exists
            if self.message_history:
                logger.debug("Sending history message...")
                history_msg = ChatMessage(
                    type="history",
                    content="",
                    metadata={"messages": [msg.to_dict() for msg in self.message_history]}
                )
                logger.debug(f"History message type: {history_msg.type}")
                await self.send_message(client_id, history_msg)
                logger.debug("History message sent")
            
            # 3. Send presence update to other clients
            if user_id:
                logger.debug("Sending presence update...")
                presence_msg = ChatMessage(
                    type="presence",
                    content="",
                    metadata={
                        "client_id": client_id,
                        "user_id": user_id,
                        "status": "connected"
                    }
                )
                logger.debug(f"Presence message type: {presence_msg.type}")
                await self.broadcast(presence_msg, exclude={client_id})
                logger.debug("Presence update sent")
            
            return True
            
        except Exception as e:
            logger.error(f"Error during connection setup for client {client_id}: {str(e)}", exc_info=True)
            if client_id in self.active_connections:
                del self.active_connections[client_id]
            if client_id in self.connection_metadata:
                del self.connection_metadata[client_id]
            if user_id and client_id in self.user_connections.get(user_id, set()):
                self.user_connections[user_id].discard(client_id)
            return False
    
    async def disconnect(self, client_id: str) -> None:
        """
        Disconnect a WebSocket client.
        
        Args:
            client_id: The client ID to disconnect
        """
        if client_id in self.active_connections:
            metadata = self.connection_metadata.get(client_id)
            if metadata and metadata.user_id:
                user_id = metadata.user_id
                self.user_connections[user_id].discard(client_id)
                if not self.user_connections[user_id]:
                    # Last connection for this user
                    del self.user_connections[user_id]
                    await self.broadcast(
                        ChatMessage(
                            type="presence",
                            content="",
                            sender_id=user_id,
                            metadata={"user_id": user_id, "status": "offline"}
                        ),
                        exclude={client_id}
                    )
            
            del self.active_connections[client_id]
            if client_id in self.connection_metadata:
                del self.connection_metadata[client_id]
            logger.info(f"WebSocket connection {client_id} closed")
    
    async def send_message(self, client_id: str, message: ChatMessage) -> bool:
        """
        Send a message to a specific client.
        
        Args:
            client_id: The client ID to send to
            message: The ChatMessage to send
            
        Returns:
            bool: True if message was sent successfully, False otherwise
        """
        if client_id in self.active_connections:
            try:
                # Check rate limit for non-system messages
                if message.type not in ["welcome", "presence", "error", "history", "ping", "system"]:
                    metadata = self.connection_metadata.get(client_id)
                    logging.debug(f"[RateLimit] Checking message limit for client_id={client_id}, user_id={getattr(metadata, 'user_id', None)}, ip={getattr(metadata, 'ip_address', None)}")
                    allowed = True
                    if metadata:
                        allowed, reason = await self.rate_limiter.check_message_limit(
                            client_id=client_id,
                            user_id=metadata.user_id,
                            ip_address=metadata.ip_address
                        )
                        if not allowed:
                            logging.debug(f"[RateLimit] Rate limit exceeded for client_id={client_id}, user_id={metadata.user_id}, ip={metadata.ip_address}")
                            error_msg = ChatMessage(
                                type="error",
                                content="Rate limit exceeded. Please wait before sending more messages.",
                                metadata={"error_type": "rate_limit"}
                            )
                            await self.active_connections[client_id].send_json(error_msg.to_dict())
                            return False
                        else:
                            logging.debug(f"[RateLimit] Message allowed for client_id={client_id}, user_id={metadata.user_id}, ip={metadata.ip_address}")
                # Send the message
                await self.active_connections[client_id].send_json(message.to_dict())
                # Update message history for chat messages
                if message.type == "chat_message":
                    self.message_history.append(message)
                    self.message_by_id[message.message_id] = message
                return True
            except websockets.exceptions.ConnectionClosed:
                logger.warning(f"Connection closed while sending to {client_id}")
                await self.disconnect(client_id)
            except Exception as e:
                logger.error(f"Error sending message to {client_id}: {str(e)}", exc_info=True)
        return False
    
    async def broadcast(self, message: ChatMessage, exclude: Optional[Set[str]] = None) -> None:
        """
        Broadcast a message to all connected clients except those in exclude set.
        
        Args:
            message: The ChatMessage to broadcast
            exclude: Optional set of client IDs to exclude from broadcast
        """
        exclude = exclude or set()
        disconnected = set()
        
        # Store message in history if it's a chat or chat_message
        if message.type in ("chat_message", "chat"):
            self.message_history.append(message)
            if message.metadata.get("message_id"):
                self.message_by_id[message.metadata["message_id"]] = message
        
        for client_id, websocket in list(self.active_connections.items()):
            if client_id not in exclude:
                try:
                    # Update last seen
                    if client_id in self.connection_metadata:
                        self.connection_metadata[client_id].last_seen = datetime.now(UTC)
                    # Send the message
                    await websocket.send_json(message.to_dict())
                    logger.debug(f"Broadcast message to client {client_id}: {message.type}")
                except (WebSocketDisconnect, websockets.exceptions.ConnectionClosed, RuntimeError) as e:
                    logger.warning(f"Client {client_id} disconnected during broadcast: {e}")
                    disconnected.add(client_id)
                except Exception as e:
                    logger.error(f"Why is this closed? - Error broadcasting to client {client_id}: {str(e)}", exc_info=True)
                    disconnected.add(client_id)
        # Clean up any disconnected websockets
        for client_id in disconnected:
            await self.disconnect(client_id)

    def get_message_history(self) -> List[dict]:
        """Get the message history as a list of dictionaries."""
        return [msg.to_dict() for msg in self.message_history]

# Global WebSocket manager instance
manager = WebSocketManager() 