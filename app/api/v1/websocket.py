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
from app.core.config import settings, Settings, get_settings
from app.core.auth import verify_token, get_current_user_from_token
from jose import jwt, JWTError
from app.utils import get_client_ip
import os

from app.core.websocket import WebSocketManager, ChatMessage
from app.core.auth import get_current_user
from app.models import User
from app.core.redis import get_redis
from app.core.websocket_rate_limiter import WebSocketRateLimiter
from app.core.errors import WebSocketError

# Create router with prefix and tags
router = APIRouter(
    tags=["websocket"]
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Create a WebSocket manager instance for this endpoint
manager = None
rate_limiter = None

async def get_manager(redis = Depends(get_redis)) -> WebSocketManager:
    """Get or create WebSocket manager instance."""
    global manager
    if manager is None:
        manager = WebSocketManager(redis)
    return manager

async def get_rate_limiter(redis = Depends(get_redis)) -> WebSocketRateLimiter:
    """Get or create rate limiter instance."""
    global rate_limiter
    if rate_limiter is None:
        rate_limiter = WebSocketRateLimiter(redis)
    return rate_limiter

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(...),
    client_id: str = Query(...),
    settings: Settings = Depends(get_settings),
    manager: WebSocketManager = Depends(get_manager),
    rate_limiter: WebSocketRateLimiter = Depends(get_rate_limiter)
):
    """WebSocket endpoint for real-time communication."""
    logger.debug(f"WebSocket connection attempt with token: {'present' if token else 'missing'}")
    
    try:
        # Authenticate user
        user = await get_current_user_from_token(token, settings)
        if not user:
            logger.error("Authentication failed")
            await websocket.close(code=4001, reason="Authentication failed")
            return

        # Get client IP
        client_ip = get_client_ip(websocket)
        
        # Check rate limits
        can_connect, reason = await rate_limiter.check_connection_limit(
            client_id=client_id,
            user_id=str(user.id),
            ip_address=client_ip
        )
        
        if not can_connect:
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            await websocket.close(code=4002, reason=reason or "Rate limit exceeded")
            return
            
        # Accept connection
        logger.debug("Attempting to accept WebSocket connection")
        await websocket.accept()
        logger.debug("WebSocket connection accepted")
            
        # Add connection to manager
        await manager.connect(client_id, websocket, user.id)
        logger.debug(f"Client {client_id} connected")
        
        try:
            # Send welcome message
            await websocket.send_json({
                "type": "welcome",
                "client_id": client_id,
                "user_id": str(user.id),
                "timestamp": datetime.now(UTC).isoformat()
            })
            logger.debug("Welcome message sent")
            
            # Handle messages
            while True:
                try:
                    # Receive message
                    data = await websocket.receive_json()
                    
                    # Check rate limit
                    can_send, reason = await rate_limiter.check_message_limit(
                        client_id=client_id,
                        user_id=str(user.id),
                        ip_address=client_ip
                    )
                    
                    if not can_send:
                        await websocket.send_json({
                            "type": "error",
                            "message": reason or "Message rate limit exceeded",
                            "timestamp": datetime.now(UTC).isoformat()
                        })
                        continue
                    
                    # Process message
                    message_type = data.get("type")
                    if not message_type:
                        raise WebSocketError("Missing message type")
                        
                    if message_type == "ping":
                        await websocket.send_json({
                            "type": "pong",
                            "timestamp": datetime.now(UTC).isoformat()
                        })
                    elif message_type == "chat_message":
                        # Handle chat message
                        await manager.broadcast_message(
                            sender_id=user.id,
                            message_content=data.get("content", ""),
                            metadata=data.get("metadata", {})
                        )
                    else:
                        logger.warning(f"Unknown message type: {message_type}")
                        
                except json.JSONDecodeError:
                    logger.error("Invalid JSON received")
                    await websocket.send_json({
                        "type": "error",
                        "message": "Invalid JSON",
                        "timestamp": datetime.now(UTC).isoformat()
                    })
                    
        except WebSocketDisconnect:
            logger.info(f"Client {client_id} disconnected")
        except Exception as e:
            logger.error(f"Error in websocket connection: {e}", exc_info=True)
            await websocket.close(code=1011, reason="Internal server error")
            
        finally:
            # Clean up
            await manager.disconnect(client_id)
            await rate_limiter.release_connection(
                client_id=client_id,
                user_id=str(user.id),
                ip_address=client_ip
            )
            logger.debug(f"Client {client_id} cleanup complete")
            
    except Exception as e:
        logger.error(f"Error in websocket endpoint: {e}", exc_info=True)
        if not websocket.client_state.is_connected:
            await websocket.close(code=1011, reason="Internal server error")

@router.get("/ws/status")
async def websocket_status(
    manager: WebSocketManager = Depends(get_manager),
    rate_limiter: WebSocketRateLimiter = Depends(get_rate_limiter)
):
    """Get WebSocket connection status."""
    return {
        "active_connections": len(manager.active_connections),
        "message_history_length": len(manager.message_history),
        "rate_limiter_status": await rate_limiter.get_status()
    } 