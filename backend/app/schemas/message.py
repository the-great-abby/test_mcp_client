from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.models.message import MessageRole

class MessageBase(BaseModel):
    role: MessageRole
    content: str
    conversation_id: int

class MessageCreate(MessageBase):
    pass

class MessageResponse(MessageBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    context: Optional["ContextResponse"] = None

    class Config:
        from_attributes = True

class MessageList(BaseModel):
    conversation_id: int
    messages: List[MessageResponse]

    class Config:
        from_attributes = True

from .context import ContextResponse
MessageResponse.model_rebuild() 