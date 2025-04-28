"""Utility functions for the application."""
from fastapi import WebSocket
from typing import Optional

def get_client_ip(websocket: WebSocket) -> Optional[str]:
    """
    Extract the client IP address from a WebSocket connection.
    
    Args:
        websocket: The WebSocket connection
        
    Returns:
        str: The client's IP address or None if not found
    """
    client = websocket.client
    if client is None:
        return None
        
    # Try to get IP from headers first (for proxied connections)
    headers = websocket.headers
    forwarded_for = headers.get("x-forwarded-for")
    if forwarded_for:
        # Get the first IP in case of multiple proxies
        return forwarded_for.split(",")[0].strip()
        
    # Fallback to direct client address
    return client.host 