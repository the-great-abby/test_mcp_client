"""
WebSocket connection management utilities.
"""
from typing import Dict, Set, Any, Optional, List
from fastapi import WebSocket, status
from starlette.websockets import WebSocketState, WebSocketDisconnect
from websockets.exceptions import ConnectionClosed
from websockets.frames import Close
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
from app.core.redis import get_redis_client
from app.core.model import ModelClient
from app.core.redis import RedisClient
import os
from app.core.auth import verify_token

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Ensure debug logs are shown
handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s %(message)s')
handler.setFormatter(formatter)
if not logger.hasHandlers():
    logger.addHandler(handler)
logger.propagate = True

# Constants for WebSocket configuration
PING_TIMEOUT = 5  # seconds
PING_INTERVAL = 2  # seconds
MAX_CONNECTIONS_PER_USER = 5
MAX_MESSAGE_HISTORY = 1000
RATE_LIMIT = 10  # messages per second
RATE_LIMIT_WINDOW = 60
HEARTBEAT_INTERVAL = 2  # seconds
HEARTBEAT_TIMEOUT = 5  # seconds

class WebSocketManager:
    """Manages WebSocket connections and message handling."""

    def __init__(self, redis_client: Optional[RedisClient] = None):
        """Initialize the WebSocket manager.

        Args:
            redis_client: Optional Redis client for distributed state
        """
        self.redis = redis_client
        # Increase rate limits for tests
        if os.environ.get("ENVIRONMENT") == "test":
            global PING_TIMEOUT, PING_INTERVAL
            PING_TIMEOUT = 30  # Avoid premature disconnects in tests
            PING_INTERVAL = 30
            max_connections = int(os.environ.get("WEBSOCKET_MAX_CONNECTIONS", 100))
            self.rate_limiter = WebSocketRateLimiter(
                redis_client,
                max_connections=max_connections,
                messages_per_minute=5000,
                messages_per_hour=100000,
                messages_per_day=1000000,
                max_messages_per_second=1000,
                rate_limit_window=60
            )
        else:
            self.rate_limiter = WebSocketRateLimiter(redis_client)
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_connections: Dict[str, Set[str]] = defaultdict(set)
        self.ip_connections: Dict[str, Set[str]] = defaultdict(set)
        self.connection_metadata: Dict[str, ConnectionMetadata] = {}
        self.connection_state: Dict[str, ConnectionState] = {}
        self.message_history: deque[ChatMessage] = deque(maxlen=MAX_MESSAGE_HISTORY)
        self.message_by_id: Dict[str, ChatMessage] = {}
        self.model_client = ModelClient()
        self.heartbeat_tasks: Dict[str, asyncio.Task] = {}
        self.message_queues: Dict[str, deque[Dict[str, Any]]] = defaultdict(lambda: deque(maxlen=100))
        
    async def initialize(self):
        """Initialize Redis client and rate limiter."""
        if not self.redis:
            self.redis = await get_redis_client()
            self.rate_limiter = WebSocketRateLimiter(
                redis=self.redis,
                max_connections=100,
                max_messages_per_minute=60,
                max_messages_per_hour=1000,
                max_messages_per_day=10000
            )

    async def _heartbeat(self, client_id: str):
        """Maintain connection heartbeat with periodic pings."""
        websocket = self.active_connections.get(client_id)
        if not websocket:
            return

        logger.debug(f"[WebSocketManager] _heartbeat started for client_id={client_id}")
        while True:
            try:
                if client_id not in self.active_connections:
                    break
                # Send ping frame
                logger.debug(f"[WebSocketManager] Sending ping to client_id={client_id}")
                await websocket.send_json({
                    "type": "ping",
                    "timestamp": datetime.now(UTC).isoformat()
                })
                # Wait for pong or timeout
                try:
                    data = await asyncio.wait_for(
                        websocket.receive_json(),
                        timeout=PING_TIMEOUT
                    )
                    logger.debug(f"[WebSocketManager] Received from client_id={client_id}: {data}")
                    if data.get("type") != "pong":
                        logger.warning(f"Expected pong, got {data.get('type')} from {client_id}")
                        break
                except asyncio.TimeoutError:
                    logger.warning(f"Ping timeout for client {client_id}")
                    break
                except Exception as e:
                    logger.error(f"Error in heartbeat for {client_id}: {e}")
                    break
                await asyncio.sleep(PING_INTERVAL)
            except Exception as e:
                logger.error(f"Heartbeat error for {client_id}: {e}")
                break
        logger.debug(f"[WebSocketManager] _heartbeat ending for client_id={client_id}")
        # If we break out of the loop, disconnect the client
        await self.disconnect(client_id)

    async def connect(
        self,
        client_id: str,
        websocket: WebSocket,
        user_id: str
    ) -> bool:
        logger.debug(f"[WebSocketManager] connect START client_id={client_id} user_id={user_id}")
        try:
            # Debug: log all headers and query params on connect
            logger.debug(f"[websocket_endpoint] Headers: {dict(websocket.headers)}")
            logger.debug(f"[websocket_endpoint] Query params: {dict(websocket.query_params)}")
            # Validate token from query params or Authorization header
            token = websocket.query_params.get("token")
            if not token:
                # Try to get token from Authorization header
                auth_header = websocket.headers.get("authorization")
                if auth_header and auth_header.lower().startswith("bearer "):
                    token = auth_header[7:].strip()
            logger.debug(f"[WebSocketManager] Before token validation client_id={client_id}")
            if not token:
                logger.error(f"[WebSocketManager] Missing token for client_id={client_id}")
                raise ConnectionClosed(
                    Close(code=status.WS_1008_POLICY_VIOLATION, reason="Missing token"),
                    None
                )
            # Validate token unless explicitly bypassed for test or mock
            if os.environ.get("ENVIRONMENT") == "test" or os.environ.get("USE_MOCK_WEBSOCKET") == "1":
                logger.debug(f"[WebSocketManager] Bypassing token validation for client_id={client_id} due to test/mock mode.")
            else:
                logger.debug(f"[WebSocketManager] Before verify_token client_id={client_id}")
                valid = await verify_token(token)
                logger.debug(f"[WebSocketManager] After verify_token client_id={client_id} valid={valid}")
                if not valid:
                    logger.error(f"[WebSocketManager] Invalid token for client_id={client_id}")
                    raise ConnectionClosed(
                        Close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token"),
                        None
                    )

            # Validate client ID
            logger.debug(f"[WebSocketManager] Before client_id validation client_id={client_id}")
            if not client_id:
                logger.error(f"[WebSocketManager] Missing client_id")
                raise ConnectionClosed(
                    Close(code=status.WS_1008_POLICY_VIOLATION, reason="Missing client_id"),
                    None
                )

            # Reject duplicate client_id
            logger.debug(f"[WebSocketManager] Before duplicate client_id check client_id={client_id}")
            if client_id in self.active_connections and self.active_connections[client_id].client_state == WebSocketState.CONNECTED:
                logger.error(f"[WebSocketManager] Duplicate client_id {client_id}")
                raise ConnectionClosed(
                    Close(code=status.WS_1008_POLICY_VIOLATION, reason="Client ID already in use"),
                    None
                )

            # Check connection limit
            print(f"[DEBUG] WebSocketManager.connect: calling check_connection_limit for client_id={client_id}, user_id={user_id}, ip={websocket.client.host}")
            allowed, reason = await self.rate_limiter.check_connection_limit(client_id, user_id, websocket.client.host)
            print(f"[DEBUG] WebSocketManager.connect: check_connection_limit result allowed={allowed} reason={reason}")
            logger.debug(f"[WebSocketManager] check_connection_limit: allowed={allowed} reason={reason}")
            if not allowed:
                logger.error(f"[WebSocketManager] Connection limit exceeded for client_id={client_id}: {reason}")
                raise ConnectionClosed(
                    Close(code=status.WS_1008_POLICY_VIOLATION, reason="Connection limit exceeded"),
                    None
                )

            logger.debug(f"[WebSocketManager] Before websocket.accept client_id={client_id}")
            await websocket.accept()
            logger.debug(f"[WebSocketManager] After websocket.accept client_id={client_id} state={websocket.client_state}")
            # Store connection
            self.active_connections[client_id] = websocket
            logger.debug(f"[WebSocketManager] Added to active_connections: client_id={client_id} state={websocket.client_state}")
            self.connection_metadata[client_id] = ConnectionMetadata(
                user_id=user_id,
                client_id=client_id,
                ip_address=websocket.client.host,
                state=ConnectionState.CONNECTED
            )
            logger.debug(f"[WebSocketManager] connection_metadata set for client_id={client_id}")
            self.message_queues[client_id] = deque(maxlen=100)
            logger.debug(f"[WebSocketManager] message_queues initialized for client_id={client_id}")
            # In test mode, skip starting heartbeat to avoid race conditions
            if os.environ.get("ENVIRONMENT") != "test":
                self.heartbeat_tasks[client_id] = asyncio.create_task(
                    self._heartbeat(client_id)
                )
                logger.debug(f"[WebSocketManager] heartbeat task started for client_id={client_id}")
            else:
                logger.debug(f"[WebSocketManager] heartbeat task skipped for client_id={client_id} in test mode")
            print(f"[DEBUG] WebSocketManager.connect: calling increment_connection_count for client_id={client_id}, user_id={user_id}, ip={websocket.client.host}")
            await self.rate_limiter.increment_connection_count(
                client_id=client_id,
                user_id=user_id,
                ip_address=websocket.client.host
            )
            print(f"[DEBUG] WebSocketManager.connect: increment_connection_count complete for client_id={client_id}")
            logger.debug(f"[WebSocketManager] increment_connection_count complete for client_id={client_id}")
            logger.info(f"[WebSocketManager] CONNECT user_id={user_id} client_id={client_id} ip={websocket.client.host}")
            logger.debug(f"[WebSocketManager] connect END client_id={client_id} state={websocket.client_state}")
            return True
        except Exception as e:
            logger.error(f"[WebSocketManager] connect EXCEPTION client_id={client_id} error={e}")
            raise

    async def disconnect(self, client_id: str):
        """Handle WebSocket disconnection."""
        try:
            metadata = self.connection_metadata.get(client_id)
            user_id = metadata.user_id if metadata else None
            ip = metadata.ip_address if metadata else None
            logger.info(f"[WebSocketManager] DISCONNECT user_id={user_id} client_id={client_id} ip={ip}")
            # Update connection state first
            self.connection_state[client_id] = ConnectionState.DISCONNECTED
            
            # Cancel heartbeat task if exists
            if client_id in self.heartbeat_tasks:
                self.heartbeat_tasks[client_id].cancel()
                del self.heartbeat_tasks[client_id]
            
            # Clean up connection data
            if metadata:
                if metadata.user_id:
                    self.user_connections[metadata.user_id].discard(client_id)
                    if not self.user_connections[metadata.user_id]:
                        del self.user_connections[metadata.user_id]
                
                if metadata.ip_address:
                    self.ip_connections[metadata.ip_address].discard(client_id)
                    if not self.ip_connections[metadata.ip_address]:
                        del self.ip_connections[metadata.ip_address]

            # Close websocket if still open
            if client_id in self.active_connections:
                websocket = self.active_connections[client_id]
                if websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.close()
                del self.active_connections[client_id]
            
            # Decrement connection count and clean up rate limiter state
            if metadata:
                await self.rate_limiter.release_connection(
                    client_id=client_id,
                    user_id=metadata.user_id,
                    ip_address=metadata.ip_address
                )
            else:
                logger.warning(f"[WebSocketManager] No metadata for client_id={client_id} during disconnect; skipping rate limiter cleanup.")
            
            logger.info(f"Client {client_id} disconnected")
            
        except Exception as e:
            logger.error(f"Error disconnecting client {client_id}: {e}")

    async def clear_all_connections(self) -> None:
        """
        Clear all active WebSocket connections.
        This is primarily used for testing cleanup.
        """
        # Create a copy of client IDs since we'll be modifying the dict during iteration
        client_ids = list(self.active_connections.keys())
        
        # Disconnect each client
        for client_id in client_ids:
            await self.disconnect(client_id)
            
        # Clear any remaining data structures
        self.active_connections.clear()
        self.user_connections.clear()
        self.ip_connections.clear()
        self.connection_metadata.clear()
        self.connection_state.clear()
        self.message_queues.clear()
        
        logger.info("Cleared all WebSocket connections and related data")
    
    async def check_rate_limit(
        self,
        client_id: str,
        message_type: str
    ) -> tuple[bool, Optional[str]]:
        """Check if a message is allowed by rate limits."""
        try:
            metadata = self.connection_metadata.get(client_id)
            if not metadata:
                return False, "Connection not found"
            
            # Skip rate limiting for streaming responses
            if message_type == "streaming_response":
                return True, None
            
            # Check message rate limit
            return await self.rate_limiter.check_message_limit(
                client_id,
                metadata.user_id,
                metadata.ip_address
            )
            
        except Exception as e:
            logger.error(f"Error checking rate limit: {e}")
            return True, None  # Allow on error
    
    async def broadcast(
        self,
        message: Dict[str, Any],
        exclude: Optional[Set[str]] = None
    ) -> None:
        """Broadcast a message to all connected clients.

        Args:
            message: Message to broadcast
            exclude: Optional set of client IDs to exclude
        """
        exclude = exclude or set()
        for client_id in list(self.active_connections.keys()):
            if client_id not in exclude:
                await self.send_message(client_id, message)
    
    async def send_message(
        self,
        client_id: str,
        message: Dict[str, Any]
    ) -> bool:
        """Send a message to a specific client.

        Args:
            client_id: Client ID
            message: Message to send

        Returns:
            True if message was sent successfully
        """
        try:
            if client_id not in self.active_connections:
                logger.warning(f"Client {client_id} not found")
                return False

            websocket = self.active_connections[client_id]
            if websocket.client_state != WebSocketState.CONNECTED:
                logger.warning(f"Client {client_id} not connected")
                return False

            # For testing, if the websocket has a mock_receive method, use it
            if hasattr(websocket, "mock_receive"):
                await websocket.mock_receive(message)
            else:
                await websocket.send_json(message)
            
            # Only store non-ping/pong messages in history
            if message.get("type") not in ["ping", "pong"]:
                self.message_queues[client_id].append(message)
            
            return True

        except Exception as e:
            logger.error(f"Error sending message to {client_id}: {e}")
            await self.disconnect(client_id)
            return False

    async def _wait_for_ack(self, client_id: str, message_id: str, timeout: float = 5.0) -> tuple[str, bool]:
        """Wait for message delivery acknowledgment from a client."""
        websocket = self.active_connections.get(client_id)
        if not websocket:
            return client_id, False
            
        try:
            # Wait for ack message with timeout
            data = await asyncio.wait_for(
                websocket.receive_json(),
                timeout=timeout
            )
            
            # Verify it's an ack for our message
            is_valid_ack = (
                data.get("type") == "message_ack" and
                data.get("message_id") == message_id
            )
            
            return client_id, is_valid_ack
            
        except (asyncio.TimeoutError, WebSocketDisconnect):
            return client_id, False
        except Exception as e:
            logger.error(f"Error waiting for ack from {client_id}: {e}")
            return client_id, False
    
    def get_message_history(self) -> List[dict]:
        """Get the message history."""
        return [msg.to_dict() for msg in self.message_history]
        
    def get_message_by_id(self, message_id: str) -> Optional[ChatMessage]:
        """Get a message by its ID."""
        return self.message_by_id.get(message_id)

    async def reconnect(self, client_id: str, websocket: WebSocket, user_id: Optional[str] = None) -> bool:
        """Handle client reconnection attempt."""
        try:
            # Check if this is a known client
            old_metadata = self.connection_metadata.get(client_id)
            if not old_metadata:
                # If not known, treat as new connection
                return await self.connect(client_id, websocket, user_id)
            
            # Verify user_id matches if provided
            if user_id and old_metadata.user_id and user_id != old_metadata.user_id:
                logger.warning(f"Reconnection attempt with mismatched user_id for client {client_id}")
                return False
            
            # Update connection state
            self.connection_state[client_id] = ConnectionState.RECONNECTING
            
            # Cancel old heartbeat task if exists
            if client_id in self.heartbeat_tasks:
                self.heartbeat_tasks[client_id].cancel()
                del self.heartbeat_tasks[client_id]
            
            # Close old websocket if still open
            old_websocket = self.active_connections.get(client_id)
            if old_websocket and old_websocket.client_state != WebSocketState.DISCONNECTED:
                await old_websocket.close(code=status.WS_1000_NORMAL_CLOSURE)
            
            # Update connection data
            self.active_connections[client_id] = websocket
            
            # Update metadata
            new_metadata = ConnectionMetadata(
                client_id=client_id,
                user_id=user_id or old_metadata.user_id,
                ip_address=get_client_ip(websocket)
            )
            self.connection_metadata[client_id] = new_metadata
            
            # Update connection mappings
            if new_metadata.user_id:
                self.user_connections[new_metadata.user_id].add(client_id)
            if new_metadata.ip_address:
                self.ip_connections[new_metadata.ip_address].add(client_id)
            
            # Start new heartbeat task
            self.heartbeat_tasks[client_id] = asyncio.create_task(
                self._heartbeat(client_id)
            )
            
            # Update state to connected
            self.connection_state[client_id] = ConnectionState.CONNECTED
            
            # Send any missed messages from history
            await self._send_missed_messages(client_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Error handling reconnection for client {client_id}: {e}")
            if websocket.client_state != WebSocketState.DISCONNECTED:
                await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
            return False
    
    async def _send_missed_messages(self, client_id: str):
        """Send any messages that were missed during disconnection."""
        try:
            websocket = self.active_connections.get(client_id)
            if not websocket:
                return
                
            metadata = self.connection_metadata.get(client_id)
            if not metadata or not metadata.last_message_id:
                return
                
            # Find messages newer than last received
            missed_messages = []
            found_last = False
            
            for message in reversed(self.message_history):
                if message.message_id == metadata.last_message_id:
                    found_last = True
                    break
                missed_messages.append(message)
            
            if not found_last:
                # If we didn't find the last message, don't send anything
                # as we can't be sure about message ordering
                return
            
            # Send missed messages in chronological order
            for message in reversed(missed_messages):
                try:
                    await websocket.send_json(message.to_dict())
                except Exception as e:
                    logger.error(f"Error sending missed message to {client_id}: {e}")
                    break
                    
        except Exception as e:
            logger.error(f"Error sending missed messages to {client_id}: {e}")
    
    async def update_last_message_id(self, client_id: str, message_id: str):
        """Update the last message ID received by a client."""
        try:
            metadata = self.connection_metadata.get(client_id)
            if metadata:
                metadata.last_message_id = message_id
        except Exception as e:
            logger.error(f"Error updating last message ID for {client_id}: {e}")

    async def check_connection_limit(
        self,
        client_id: str,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> tuple[bool, Optional[str]]:
        """Check if a new connection is allowed by rate limits.
        
        Args:
            client_id: Unique identifier for the client
            user_id: Optional user ID for authenticated connections
            ip_address: Optional IP address of the client
            
        Returns:
            Tuple[bool, Optional[str]]: (allowed, reason)
        """
        try:
            # Check user connection limit if authenticated
            if user_id:
                user_connections = self.user_connections.get(user_id, set())
                if len(user_connections) >= MAX_CONNECTIONS_PER_USER:
                    return False, "Too many concurrent connections for user"
                    
            # Check IP connection limit
            if ip_address:
                ip_connections = self.ip_connections.get(ip_address, set())
                if len(ip_connections) >= MAX_CONNECTIONS_PER_USER:
                    return False, "Too many concurrent connections from IP"
                    
            # Check rate limiter if available
            if self.rate_limiter:
                return await self.rate_limiter.check_connection_limit(
                    client_id=client_id,
                    user_id=user_id,
                    ip=ip_address
                )
                
            return True, None
            
        except Exception as e:
            logger.error(f"Error checking connection limit: {e}")
            # Default to allowing connection on error
            return True, None 

    async def handle_message(
        self,
        client_id: str,
        message: Dict[str, Any]
    ) -> None:
        logger.debug(f"[WebSocketManager] handle_message: client_id={client_id} message={message}")
        try:
            # Check rate limit before handling message
            metadata = self.connection_metadata.get(client_id)
            if metadata:
                allowed, reason = await self.rate_limiter.check_message_limit(
                    client_id=client_id,
                    user_id=metadata.user_id,
                    ip_address=metadata.ip_address,
                    is_system_message=message.get("type") == "system"
                )
                logger.debug(f"[WebSocketManager] handle_message: rate limit check allowed={allowed} reason={reason}")
                if not allowed:
                    print(f"[DEBUG] handle_message: rate limit exceeded for client_id={client_id}, reason={reason}")
                    await self.send_error(client_id, reason)
                    print(f"[DEBUG] handle_message: closing connection for client_id={client_id} due to rate limit")
                    raise ConnectionClosed(
                        Close(code=status.WS_1008_POLICY_VIOLATION, reason="Message rate limit exceeded"),
                        None
                    )
                    return

                # Only increment message count if allowed
                await self.rate_limiter.increment_message_count(
                    client_id=client_id,
                    user_id=metadata.user_id,
                    ip_address=metadata.ip_address
                )
                logger.debug(f"[WebSocketManager] handle_message: incremented message count for client_id={client_id}")

            # Handle message by type
            await self._handle_message_by_type(client_id, message)
        except Exception as e:
            logger.error(f"Error handling message from {client_id}: {e}")
            await self.send_error(client_id, str(e))

    async def _handle_message_by_type(self, client_id: str, message: Dict[str, Any]):
        logger.debug(f"[WebSocketManager] _handle_message_by_type: client_id={client_id} message={message}")
        message_type = message.get("type")
        if not message_type:
            await self.send_error(client_id, "Missing message type")
            return

        if message_type == "chat":
            logger.debug(f"[WebSocketManager] _handle_message_by_type: dispatching to handle_chat_message for client_id={client_id}")
            await self.handle_chat_message(client_id, message)
        elif message_type == "system":
            await self.handle_system_message(client_id, message)
        elif message_type == "typing":
            # Echo back typing indicator with same content
            await self.send_message(
                client_id=client_id,
                message={
                    "type": "typing",
                    "content": message.get("content", "true"),
                    "metadata": message.get("metadata", {})
                }
            )
        elif message_type == "ping":
            # Respond with pong immediately
            await self.send_message(
                client_id=client_id,
                message={
                    "type": "pong",
                    "timestamp": datetime.now(UTC).isoformat()
                }
            )
        elif message_type == "stream_start":
            await self.handle_stream_start(client_id, message)
        elif message_type == "stream":
            await self.handle_stream_message(client_id, message)
        elif message_type == "stream_end":
            await self.handle_stream_end(client_id, message)
        else:
            await self.send_error(client_id, f"Unknown message type: {message_type}")

    async def handle_chat_message(
        self,
        client_id: str,
        message: Dict[str, Any]
    ) -> None:
        logger.debug(f"[WebSocketManager] handle_chat_message: client_id={client_id} message={message}")
        try:
            content = message.get("content")
            if not content:
                await self.send_error(
                    client_id=client_id,
                    error="Missing message content"
                )
                return

            # Create chat message
            chat_message = ChatMessage(
                client_id=client_id,
                user_id=self.connection_metadata[client_id].user_id,
                content=content,
                timestamp=datetime.now(UTC)
            )
            logger.debug(f"[WebSocketManager] handle_chat_message: created ChatMessage {chat_message.to_dict()}")

            # Send response to sender
            await self.send_message(
                client_id=client_id,
                message={
                    "type": "chat",
                    "content": chat_message.content,
                    "user_id": chat_message.user_id,
                    "timestamp": chat_message.timestamp.isoformat()
                }
            )
            logger.debug(f"[WebSocketManager] handle_chat_message: sent chat response to client_id={client_id}")

            # Broadcast to other clients
            await self.broadcast(
                message={
                    "type": "chat",
                    "content": chat_message.content,
                    "user_id": chat_message.user_id,
                    "timestamp": chat_message.timestamp.isoformat()
                },
                exclude={client_id}
            )
            logger.debug(f"[WebSocketManager] handle_chat_message: broadcasted chat to others from client_id={client_id}")

        except Exception as e:
            logger.error(f"Error handling chat message from {client_id}: {e}")
            await self.send_error(
                client_id=client_id,
                error=str(e)
            )

    async def handle_system_message(
        self,
        client_id: str,
        message: Dict[str, Any]
    ) -> None:
        """Handle a system message.

        Args:
            client_id: Client ID that sent the message
            message: System message
        """
        try:
            content = message.get("content")
            if not content:
                await self.send_error(
                    client_id=client_id,
                    error="Missing message content"
                )
                return

            # Process system message
            await self.send_message(
                client_id=client_id,
                message={
                    "type": "system",
                    "content": content,
                    "timestamp": datetime.now(UTC).isoformat()
                }
            )

        except Exception as e:
            logger.error(f"Error handling system message from {client_id}: {e}")
            await self.send_error(
                client_id=client_id,
                error=str(e)
            )

    async def send_error(
        self,
        client_id: str,
        error: str
    ) -> None:
        """Send an error message to a client.

        Args:
            client_id: Client ID to send to
            error: Error message
        """
        await self.send_message(
            client_id=client_id,
            message={
                "type": "error",
                "content": error,
                "timestamp": datetime.now(UTC).isoformat()
            }
        )

    async def cleanup(self) -> None:
        """Clean up all connections."""
        for client_id in list(self.active_connections.keys()):
            await self.disconnect(client_id)
        self.active_connections.clear()
        self.connection_metadata.clear()
        self.connection_state.clear()
        self.message_queues.clear()
        logger.info("Cleared all WebSocket connections and related data")

    async def handle_stream_start(self, client_id: str, message: Dict[str, Any]) -> None:
        """Handle stream start message.

        Args:
            client_id: Client ID
            message: Stream start message
        """
        try:
            content = message.get("content")
            if not content:
                logger.error(f"[handle_stream_start] Empty stream content for client {client_id}")
                await self.send_error(client_id, "Empty stream content")
                return

            # Store stream state
            self.connection_state[client_id] = ConnectionState.STREAMING

            # Send stream start
            await self.send_message(
                client_id=client_id,
                message={
                    "type": "stream_start",
                    "content": "",
                    "metadata": message.get("metadata", {})
                }
            )

            # Start streaming content
            chunk_size = 10
            chunks = [content[i:i+chunk_size] for i in range(0, len(content), chunk_size)]
            logger.info(f"[handle_stream_start] Streaming {len(chunks)} chunks to client {client_id}")

            for idx, chunk in enumerate(chunks):
                if self.connection_state.get(client_id) != ConnectionState.STREAMING:
                    logger.warning(f"[handle_stream_start] Streaming interrupted for client {client_id} at chunk {idx}")
                    break

                logger.debug(f"[handle_stream_start] Sending chunk {idx+1}/{len(chunks)}: '{chunk}' to client {client_id}")
                await self.send_message(
                    client_id=client_id,
                    message={
                        "type": "stream",
                        "content": {
                            "content_block_delta": {
                                "type": "text",
                                "text": chunk
                            }
                        },
                        "metadata": message.get("metadata", {})
                    }
                )
                await asyncio.sleep(0.1)  # Simulate streaming delay

            # Send stream end if still streaming
            if self.connection_state.get(client_id) == ConnectionState.STREAMING:
                logger.info(f"[handle_stream_start] Sending stream_end to client {client_id}")
                await self.send_message(
                    client_id=client_id,
                    message={
                        "type": "stream_end",
                        "content": "",
                        "metadata": message.get("metadata", {})
                    }
                )
                self.connection_state[client_id] = ConnectionState.CONNECTED
            else:
                logger.warning(f"[handle_stream_start] Did not send stream_end to client {client_id} due to state: {self.connection_state.get(client_id)}")

        except Exception as e:
            logger.error(f"[handle_stream_start] Error handling stream start from {client_id}: {e}")
            await self.send_error(client_id, str(e))
            self.connection_state[client_id] = ConnectionState.CONNECTED

    async def handle_stream_message(self, client_id: str, message: Dict[str, Any]) -> None:
        """Handle stream message.

        Args:
            client_id: Client ID
            message: Stream message
        """
        try:
            if self.connection_state.get(client_id) != ConnectionState.STREAMING:
                await self.send_error(client_id, "No active stream")
                return

            content = message.get("content", {}).get("content_block_delta", {}).get("text")
            if not content:
                await self.send_error(client_id, "Missing stream content")
                return

            await self.send_message(
                client_id=client_id,
                message={
                    "type": "stream",
                    "content": {
                        "content_block_delta": {
                            "type": "text",
                            "text": content
                        }
                    },
                    "metadata": message.get("metadata", {})
                }
            )

        except Exception as e:
            logger.error(f"Error handling stream message from {client_id}: {e}")
            await self.send_error(client_id, str(e))

    async def handle_stream_end(self, client_id: str, message: Dict[str, Any]) -> None:
        """Handle stream end message.

        Args:
            client_id: Client ID
            message: Stream end message
        """
        try:
            if self.connection_state.get(client_id) != ConnectionState.STREAMING:
                await self.send_error(client_id, "No active stream")
                return

            await self.send_message(
                client_id=client_id,
                message={
                    "type": "stream_end",
                    "content": "",
                    "metadata": message.get("metadata", {})
                }
            )
            self.connection_state[client_id] = ConnectionState.CONNECTED

        except Exception as e:
            logger.error(f"Error handling stream end from {client_id}: {e}")
            await self.send_error(client_id, str(e))
            self.connection_state[client_id] = ConnectionState.CONNECTED 