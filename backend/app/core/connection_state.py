from enum import Enum

class ConnectionState(str, Enum):
    """Enum representing the possible states of a WebSocket connection."""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    RECONNECTING = "reconnecting" 