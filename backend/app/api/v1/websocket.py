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
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings, Settings, get_settings
from app.core.auth import verify_token, get_current_user_from_token
from jose import jwt, JWTError
from app.utils import get_client_ip
import os

from app.core.websocket import WebSocketManager, ChatMessage
from app.models import User
from app.core.redis import get_redis, RedisClient
from app.core.websocket_rate_limiter import WebSocketRateLimiter
from app.core.errors import RateLimitExceeded
from app.db.session import get_db
from websockets.exceptions import ConnectionClosed
from websockets.frames import Close

# Create router with prefix and tags
router = APIRouter(
    tags=["websocket"]
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Create a WebSocket manager instance for this endpoint
manager = None
rate_limiter = None

async def get_manager(redis: RedisClient = Depends(get_redis)) -> WebSocketManager:
    """Get or create WebSocket manager instance."""
    global manager
    if manager is None:
        manager = WebSocketManager(redis)
    return manager

async def get_rate_limiter(redis: RedisClient = Depends(get_redis)) -> WebSocketRateLimiter:
    """Get or create rate limiter instance."""
    global rate_limiter
    if rate_limiter is None:
        rate_limiter = WebSocketRateLimiter(redis)
    return rate_limiter

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    websocket_manager: WebSocketManager = Depends(get_manager),
    rate_limiter: WebSocketRateLimiter = Depends(get_rate_limiter),
    db: AsyncSession = Depends(get_db)
):
    """WebSocket endpoint for real-time communication.

    Args:
        websocket: WebSocket connection
        websocket_manager: WebSocket manager instance
        rate_limiter: Rate limiter instance
    """
    client_id = None
    try:
        # Get auth token from query parameters
        token = websocket.query_params.get("token")
        if not token:
            raise ConnectionClosed(
                rcvd=Close(code=status.WS_1008_POLICY_VIOLATION, reason="Missing token"),
                sent=None
            )

        # Validate token and get user
        try:
            user = await get_current_user_from_token(token, db)
            if not user:
                raise ConnectionClosed(
                    rcvd=Close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token"),
                    sent=None
                )
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            raise ConnectionClosed(
                rcvd=Close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token"),
                sent=None
            )

        # Get client ID from query parameters
        client_id = websocket.query_params.get("client_id")
        if not client_id:
            raise ConnectionClosed(
                rcvd=Close(code=status.WS_1008_POLICY_VIOLATION, reason="Missing client_id"),
                sent=None
            )

        # Accept connection
        await websocket.accept()

        # Connect to WebSocket manager
        success = await websocket_manager.connect(
            client_id=client_id,
            websocket=websocket,
            user_id=str(user.id)
        )

        if not success:
            raise ConnectionClosed(
                rcvd=Close(code=status.WS_1011_INTERNAL_ERROR, reason="Connection failed"),
                sent=None
            )

        # Handle messages
        try:
            while True:
                message = await websocket.receive_json()
                await websocket_manager.handle_message(client_id, message)
        except ConnectionClosed:
            logger.info(f"Client {client_id} disconnected")
            await websocket_manager.disconnect(client_id)
        except Exception as e:
            logger.error(f"Error handling message from {client_id}: {e}")
            await websocket_manager.disconnect(client_id)
            raise ConnectionClosed(
                rcvd=Close(code=status.WS_1011_INTERNAL_ERROR, reason=str(e)),
                sent=None
            )

    except ConnectionClosed as e:
        logger.warning(f"WebSocket connection closed: {e}")
        if client_id:
            await websocket_manager.disconnect(client_id)
        if not e.sent:
            await websocket.close(code=e.rcvd.code, reason=e.rcvd.reason)

    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        if client_id:
            await websocket_manager.disconnect(client_id)
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR, reason=str(e))

@router.get("/ws/status")
async def websocket_status(manager: WebSocketManager = Depends(get_manager)):
    """Get WebSocket connection status."""
    return {
        "active_connections": len(manager.active_connections),
        "message_history_length": len(manager.message_history)
    }