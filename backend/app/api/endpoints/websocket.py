"""
WebSocket endpoints for real-time communication.
"""
from fastapi import APIRouter, WebSocket, Depends
from app.core.security import get_current_user_ws
from backend.app.core.websocket import manager
from app.models import User

router = APIRouter()

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    user: User = Depends(get_current_user_ws)
):
    """
    WebSocket endpoint for real-time communication.
    
    Args:
        websocket: The WebSocket connection
        user: The authenticated user (from token)
    """
    await manager.connect(websocket, user)
    try:
        while True:
            # Wait for messages from the client
            data = await websocket.receive_json()
            
            # Echo the message back to all user's connections
            await manager.broadcast_to_user(
                user.id,
                {
                    "type": "message",
                    "data": data
                }
            )
    except Exception:
        pass
    finally:
        manager.disconnect(websocket, user) 