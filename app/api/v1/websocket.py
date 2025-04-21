"""
WebSocket endpoint for real-time communication.
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException, Depends
from typing import Dict, Optional, Any
import json
from uuid import uuid4
from datetime import datetime, UTC
import logging
import asyncio
from app.core.config import settings
from app.core.auth import verify_token
from jose.exceptions import JWTError as jose_exceptions

from app.core.websocket import manager, ChatMessage
from app.core.auth import get_current_user
from app.models import User

# Create router with prefix and tags
router = APIRouter(
    tags=["websocket"]
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: Optional[str] = Query(None)):
    """WebSocket endpoint handling real-time chat communication."""
    logger.debug(f"WebSocket connection attempt with token: {'present' if token else 'missing'}")
    
    client_id = None
    user_id = None
    last_typing_time = 0
    
    try:
        # Accept the connection first so we can send error messages
        logger.debug("Attempting to accept WebSocket connection")
        await websocket.accept()
        logger.debug("WebSocket connection accepted")
        
        # Check for token in query param or Authorization header
        if not token:
            # Try to get token from Authorization header
            auth_header = websocket.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
            
        # Require authentication for all connections
        if not token:
            logger.debug("No token provided, closing connection")
            await websocket.close(code=1008, reason="Authentication required")
            return
            
        try:
            logger.debug("Verifying token")
            payload = await verify_token(token)  # This will raise JWTError if invalid
            user_id = str(payload["sub"])  # Now we can safely access sub
            logger.debug(f"Token verified, user_id: {user_id}")
        except jwt.ExpiredSignatureError:
            logger.debug("Token has expired")
            await websocket.close(code=1008, reason="Token has expired")
            return
        except jwt.InvalidTokenError:
            logger.debug("Invalid token")
            await websocket.close(code=1008, reason="Invalid token format")
            return
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}", exc_info=True)
            await websocket.close(code=1008, reason="Authentication failed")
            return
            
        # Connect to WebSocket manager
        client_id = str(uuid4())
        logger.debug(f"Generated client_id: {client_id}")
        
        if not await manager.connect(client_id, websocket, user_id):
            logger.error(f"Failed to connect client {client_id} to manager")
            await websocket.close(code=1000, reason="Connection rejected: too many connections")
            return
            
        logger.debug(f"Client {client_id} connected successfully")
        
        # Main message handling loop - welcome message already sent by manager.connect()
        while True:
            try:
                data = await websocket.receive_json()
                logger.debug(f"Received message from client {client_id}: {data.get('type')}")
                
                # Handle different message types
                message_type = data.get("type")
                if not message_type:
                    await manager.send_message(
                        client_id,
                        ChatMessage(
                            type="error",
                            content="Invalid message format: missing type",
                            metadata={"error_type": "validation"}
                        )
                    )
                    logger.debug("Error message sent to client")
                    continue
                
                # Update last seen time
                if client_id in manager.connection_metadata:
                    manager.connection_metadata[client_id].last_seen = datetime.now(UTC)
                
                if message_type == "ping":
                    await manager.send_message(
                        client_id,
                        ChatMessage(
                            type="pong",
                            content=""
                        )
                    )
                
                elif message_type == "message" or message_type == "chat_message":
                    content = data.get("content", "").strip()
                    if not content:
                        await manager.send_message(
                            client_id,
                            ChatMessage(
                                type="error",
                                content="Invalid message format: missing or empty content",
                                metadata={"error_type": "validation"}
                            )
                        )
                        logger.debug("Error message sent to client")
                        continue
                    
                    # Create and broadcast message
                    message = ChatMessage(
                        type="chat_message",  # Always send back as chat_message
                        content=content,
                        metadata={
                            "client_id": client_id,
                            "user_id": user_id,
                            "timestamp": data.get("metadata", {}).get("timestamp")
                        }
                    )
                    # Send response back to sender first
                    await manager.send_message(client_id, message)
                    # Then broadcast to all other clients
                    await manager.broadcast(message, exclude={client_id})
                
                elif message_type == "typing":
                    is_typing = data.get("metadata", {}).get("is_typing", False)
                    await manager.broadcast(
                        ChatMessage(
                            type="typing",
                            content="",
                            metadata={
                                "client_id": client_id,
                                "user_id": user_id,
                                "is_typing": is_typing
                            }
                        ),
                        exclude={client_id}
                    )
                
                else:
                    logger.debug(f"Unknown message type received: {message_type}")
                    await manager.send_message(
                        client_id,
                        ChatMessage(
                            type="error",
                            content=f"Unknown message type: {message_type}",
                            metadata={"error_type": "validation"}
                        )
                    )
                    logger.debug("Error message sent to client")
                    continue
                    
            except json.JSONDecodeError:
                logger.debug("Invalid JSON received")
                await manager.send_message(
                    client_id,
                    ChatMessage(
                        type="error",
                        content="Invalid JSON",
                        metadata={"error_type": "validation"}
                    )
                )
                logger.debug("Error message sent to client")
                continue
            except WebSocketDisconnect:
                logger.debug(f"WebSocket disconnected: client_id={client_id}")
                break
            except Exception as e:
                logger.error(f"Error processing message: {str(e)}", exc_info=True)
                await manager.send_message(
                    client_id,
                    ChatMessage(
                        type="error",
                        content="Internal server error",
                        metadata={"error_type": "internal"}
                    )
                )
                continue
    except Exception as e:
        logger.error(f"Error in websocket endpoint: {str(e)}", exc_info=True)
    finally:
        if client_id:  # Only disconnect if client_id was set
            await manager.disconnect(client_id)

@router.get("/ws/status")
async def get_websocket_status() -> Dict[str, Any]:
    active_connections = {
        client_id: metadata.to_dict()
        for client_id, metadata in manager.connection_metadata.items()
    }
    return {
        "active_connections": active_connections,
        "total_messages": len(manager.message_history)
    } 