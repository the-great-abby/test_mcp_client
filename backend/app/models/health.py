from pydantic import BaseModel
from typing import Dict, Any, Literal

class HealthResponse(BaseModel):
    """Health check response model."""
    status: Literal["ok", "error"]
    details: Dict[str, Dict[str, Any]] 