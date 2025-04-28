"""
WebSocket endpoint for real-time communication.
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException, Depends, status
from typing import Dict, Optional, Any
import json
from uuid import uuid4
from datetime import datetime, UTC
import logging
import asyncio

from app.core.config import settings, Settings
from app.core.auth import verify_token
from app.api.deps import get_settings, get_websocket_manager_ws
from app.core.websocket import ChatMessage, WebSocketManager
from app.core.errors import RateLimitExceeded, ConnectionLimitExceeded

# Create router with prefix and tags
router = APIRouter(
    prefix=f"{settings.API_V1_STR}",
    tags=["websocket"]
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = None,
    settings: Settings = Depends(get_settings),
    websocket_manager: WebSocketManager = Depends(get_websocket_manager_ws),
):
    """WebSocket endpoint for real-time communication."""
    try:
        await websocket.accept()
        
        # Handle authentication
        user_id = None
        if token:
            try:
                payload = await verify_token(token=token)
                user_id = payload.sub
                logger.debug(f"Authenticated WebSocket connection for user {user_id}")
            except HTTPException as e:
                logger.warning(f"Token verification failed: {str(e)}")
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                return
        
        # Add connection to manager
        try:
            client_id = str(uuid4())
            connected = await websocket_manager.connect(client_id, websocket, user_id)
            if not connected:
                logger.warning(f"Connection limit exceeded for user {user_id}")
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                return
        except (RateLimitExceeded, ConnectionLimitExceeded) as e:
            logger.warning(f"Connection limit exceeded for user {user_id}: {str(e)}")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        try:
            while True:
                data = await websocket.receive_text()
                try:
                    msg_dict = json.loads(data)
                    logger.debug(f"Received message: {msg_dict}")
                    # Ensure required fields for ChatMessage
                    if "type" not in msg_dict:
                        logger.error(f"Incoming message missing 'type': {msg_dict}")
                        continue
                    if "content" not in msg_dict:
                        msg_dict["content"] = ""
                    # Handle ping/pong
                    if msg_dict["type"] == "ping":
                        pong = {"type": "pong", "content": msg_dict.get("content", ""), "metadata": msg_dict.get("metadata", {})}
                        await websocket.send_text(json.dumps(pong))
                        continue
                    # Broadcast supported types
                    if msg_dict["type"] == "typing_indicator":
                        # Add user_id to metadata if available
                        if user_id:
                            msg_dict.setdefault("metadata", {})["user_id"] = user_id
                        if client_id:
                            msg_dict.setdefault("metadata", {})["client_id"] = client_id
                        message = ChatMessage.from_dict(msg_dict)
                        await websocket_manager.broadcast(message)
                        continue
                    elif msg_dict["type"] == "system":
                        # Echo system message back to sender
                        await websocket_manager.send_message(
                            client_id,
                            ChatMessage(
                                type="system",
                                content=msg_dict.get("content", ""),
                                metadata=msg_dict.get("metadata", {})
                            )
                        )
                        continue
                    elif msg_dict["type"] in ("message", "chat", "chat_message"):
                        content = msg_dict["content"].strip()
                        if not content:
                            await websocket_manager.send_message(
                                client_id,
                                ChatMessage(
                                    type="error",
                                    content="Invalid message format: missing or empty content",
                                    metadata={"error_type": "validation"}
                                )
                            )
                            logger.debug("Error message sent to client")
                            continue
                        # Always use 'chat_message' as the outgoing type
                        message = ChatMessage(
                            type="chat_message",
                            content=content,
                            metadata={
                                "client_id": client_id,
                                "user_id": user_id,
                                "timestamp": msg_dict.get("metadata", {}).get("timestamp")
                            }
                        )
                        await websocket_manager.send_message(client_id, message)
                        await websocket_manager.broadcast(message, exclude={client_id})
                except Exception as e:
                    logger.error(f"Failed to parse incoming message: {data} | Error: {e}")
                    continue
        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected for user {user_id}")
            await websocket_manager.disconnect(client_id)
            
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        if not websocket.client_state.DISCONNECTED:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)

@router.get("/ws/status")
async def get_websocket_status(
    websocket_manager: WebSocketManager = Depends(get_websocket_manager_ws)
) -> Dict[str, Any]:
    """Get status of WebSocket connections."""
    active_connections = {
        client_id: metadata.to_dict()
        for client_id, metadata in websocket_manager.connection_metadata.items()
    }
    return {
        "active_connections": active_connections,
        "total_messages": len(websocket_manager.message_history)
    }