from datetime import datetime
from typing import Optional, Dict, Any
from uuid import uuid4

class ChatMessage:
    """Represents a chat message in the system."""
    def __init__(
        self,
        content: str,
        type: str = "chat_message",
        sender_id: Optional[str] = None,
        client_id: Optional[str] = None,
        message_id: Optional[str] = None,
        timestamp: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None,
        delivered: bool = False
    ):
        self.content = content
        self.type = type
        self.sender_id = sender_id
        self.client_id = client_id
        self.message_id = message_id or str(uuid4())
        self.timestamp = timestamp or datetime.utcnow()
        self.metadata = metadata or {}
        self.delivered = delivered

    def to_dict(self) -> dict:
        """Convert the message to a dictionary for serialization."""
        return {
            "message_id": self.message_id,
            "content": self.content,
            "type": self.type,
            "sender_id": self.sender_id,
            "client_id": self.client_id,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
            "delivered": self.delivered
        }

    def mark_delivered(self) -> None:
        """Mark the message as delivered."""
        self.delivered = True

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChatMessage":
        """Create a ChatMessage instance from a dictionary."""
        if "timestamp" in data and isinstance(data["timestamp"], str):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data) 