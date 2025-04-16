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
import websockets

logger = logging.getLogger(__name__)

# Constants for WebSocket configuration
PING_TIMEOUT = 60  # seconds
MAX_CONNECTIONS_PER_USER = 5
MAX_MESSAGE_HISTORY = 100
RATE_LIMIT = 10  # messages per second

class WebSocketManager:
    """Manages active WebSocket connections and message history."""
    
    def __init__(self):
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
        # Rate limiting - maps client_id to last message timestamps
        self.message_timestamps: Dict[str, deque[datetime]] = defaultdict(lambda: deque(maxlen=RATE_LIMIT))
        
        # Configuration properties
        self.ping_timeout = PING_TIMEOUT
        self.max_connections_per_user = MAX_CONNECTIONS_PER_USER
        self.max_message_history = MAX_MESSAGE_HISTORY
        self.rate_limit = RATE_LIMIT
    
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
            self.active_connections[client_id] = websocket
            self.connection_metadata[client_id] = ConnectionMetadata(
                client_id=client_id,
                user_id=user_id,
                connected_at=datetime.now(UTC),
                last_seen=datetime.now(UTC),
                state=ConnectionState.CONNECTED,
                is_typing=False
            )
            
            if user_id:
                self.user_connections[user_id].add(client_id)
                logger.debug(f"Added client {client_id} to user {user_id} connections")
                
            # 1. Send welcome message first
            await self.send_message(
                client_id,
                ChatMessage(
                    type="welcome",
                    content="Welcome to the chat!",
                    metadata={"client_id": client_id, "user_id": user_id} if user_id else {"client_id": client_id}
                )
            )
            
            # 2. Send message history if any exists
            if self.message_history:
                await self.send_message(
                    client_id,
                    ChatMessage(
                        type="history",
                        content="",
                        metadata={"messages": [msg.to_dict() for msg in self.message_history]}
                    )
                )
            
            # 3. Send presence update to other clients
            if user_id:
                await self.broadcast(
                    ChatMessage(
                        type="presence",
                        content="",
                        metadata={
                            "client_id": client_id,
                            "user_id": user_id,
                            "status": "connected"
                        }
                    ),
                    exclude={client_id}  # Don't send to the connecting client
                )
            
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
                if message.type not in ["welcome", "presence", "error"]:
                    now = datetime.now(UTC)
                    timestamps = self.message_timestamps[client_id]
                    
                    # Remove old timestamps
                    while timestamps and (now - timestamps[0]).total_seconds() > 1:
                        timestamps.popleft()
                    
                    # Check if rate limit exceeded
                    if len(timestamps) >= self.rate_limit:
                        await self.active_connections[client_id].send_json(
                            ChatMessage(
                                type="error",
                                content="Rate limit exceeded. Please wait before sending more messages.",
                                metadata={"error_type": "rate_limit"}
                            ).to_dict()
                        )
                        return False
                    
                    timestamps.append(now)
                
                # Update last seen
                if client_id in self.connection_metadata:
                    self.connection_metadata[client_id].last_seen = datetime.now(UTC)
                
                # Send the message
                await self.active_connections[client_id].send_json(message.to_dict())
                logger.debug(f"Sent message to client {client_id}: {message.type}")
                
                # Store message in history if it's a chat message
                if message.type == "chat_message":
                    self.message_history.append(message)
                    if message.metadata.get("message_id"):
                        self.message_by_id[message.metadata["message_id"]] = message
                
                return True
            except Exception as e:
                logger.error(f"Error sending message to client {client_id}: {str(e)}", exc_info=True)
                # Only disconnect if it's a connection-related error
                if isinstance(e, (websockets.exceptions.ConnectionClosed, 
                               websockets.exceptions.ConnectionClosedError,
                               websockets.exceptions.ConnectionClosedOK)):
                    await self.disconnect(client_id)
                return False
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
        
        # Store message in history if it's a chat message
        if message.type == "chat_message":
            self.message_history.append(message)
            if message.metadata.get("message_id"):
                self.message_by_id[message.metadata["message_id"]] = message
        
        for client_id, websocket in self.active_connections.items():
            if client_id not in exclude:
                try:
                    # Update last seen
                    if client_id in self.connection_metadata:
                        self.connection_metadata[client_id].last_seen = datetime.now(UTC)
                    
                    # Send the message
                    await websocket.send_json(message.to_dict())
                    logger.debug(f"Broadcast message to client {client_id}: {message.type}")
                except Exception as e:
                    logger.error(f"Error broadcasting to client {client_id}: {str(e)}", exc_info=True)
                    disconnected.add(client_id)
        
        # Clean up any disconnected websockets
        for client_id in disconnected:
            await self.disconnect(client_id)

    def get_message_history(self) -> List[dict]:
        """Get the message history as a list of dictionaries."""
        return [msg.to_dict() for msg in self.message_history]

# Global WebSocket manager instance
manager = WebSocketManager() 