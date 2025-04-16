from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

class ContextBase(BaseModel):
    content: str
    meta_data: Optional[Dict[str, Any]] = None
    message_id: int
    conversation_id: int

class ContextCreate(ContextBase):
    pass

class ContextResponse(ContextBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True 