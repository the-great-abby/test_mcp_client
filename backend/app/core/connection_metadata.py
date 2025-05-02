from datetime import datetime
from typing import Optional

from app.core.connection_state import ConnectionState

class ConnectionMetadata:
    """Metadata for tracking WebSocket connection state and attributes."""
    def __init__(
        self,
        client_id: str,
        user_id: Optional[str] = None,
        state: ConnectionState = ConnectionState.CONNECTED,
        connected_at: Optional[datetime] = None,
        last_seen: Optional[datetime] = None,
        is_typing: bool = False,
        ip_address: Optional[str] = None,
        last_message_id: Optional[str] = None
    ):
        self.client_id = client_id
        self.user_id = user_id
        self.state = state
        self.connected_at = connected_at or datetime.utcnow()
        self.last_seen = last_seen or datetime.utcnow()
        self.is_typing = is_typing
        self.ip_address = ip_address
        self.last_message_id = last_message_id

    def to_dict(self) -> dict:
        """Convert the metadata to a dictionary for serialization."""
        return {
            "client_id": self.client_id,
            "user_id": self.user_id,
            "state": self.state.value,
            "connected_at": self.connected_at.isoformat(),
            "last_seen": self.last_seen.isoformat(),
            "is_typing": self.is_typing,
            "ip_address": self.ip_address,
            "last_message_id": self.last_message_id
        }

    def update_last_seen(self) -> None:
        """Update the last_seen timestamp to current UTC time."""
        self.last_seen = datetime.utcnow()

    def set_typing(self, is_typing: bool) -> None:
        """Update the typing status of the connection."""
        self.is_typing = is_typing
        self.update_last_seen()

    def set_state(self, state: ConnectionState) -> None:
        """Update the connection state."""
        self.state = state
        self.update_last_seen()
        
    def update_last_message(self, message_id: str) -> None:
        """Update the last message ID received by this connection."""
        self.last_message_id = message_id
        self.update_last_seen() 