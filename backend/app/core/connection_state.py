"""Connection state enum."""
from enum import Enum

class ConnectionState(Enum):
    """Connection state enum."""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    RECONNECTING = "reconnecting"
    STREAMING = "streaming" 