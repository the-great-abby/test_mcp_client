"""Token schemas."""
from typing import Optional
from pydantic import BaseModel

class TokenPayload(BaseModel):
    """Token payload schema."""
    sub: Optional[str] = None
    exp: Optional[int] = None 