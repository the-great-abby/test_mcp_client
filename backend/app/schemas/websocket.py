"""WebSocket schemas."""
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class WebSocketMessageType(str, Enum):
    """WebSocket message types."""
    WELCOME = "welcome"
    MESSAGE = "message"
    TYPING = "typing"
    STATUS = "status"
    ERROR = "error"
    HISTORY = "history"
    PRESENCE = "presence"


class WebSocketMessage(BaseModel):
    """Base WebSocket message schema."""
    type: WebSocketMessageType
    content: str
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    timestamp: Optional[datetime] = Field(default_factory=datetime.utcnow)
    message_id: Optional[str] = None
    user_id: Optional[str] = None


class WebSocketHistoryMessage(BaseModel):
    """WebSocket message history schema."""
    type: WebSocketMessageType = WebSocketMessageType.HISTORY
    messages: List[WebSocketMessage]
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class WebSocketPresenceMessage(BaseModel):
    """WebSocket presence update schema."""
    type: WebSocketMessageType = WebSocketMessageType.PRESENCE
    users: List[Dict[str, Any]]
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class WebSocketErrorMessage(BaseModel):
    """WebSocket error message schema."""
    type: WebSocketMessageType = WebSocketMessageType.ERROR
    content: str
    error_code: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict) 