from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import os
from app.db.base import Base
from app.models.context import Context
import uuid

class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class Message(Base):
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content = Column(String, nullable=False)
    role = Column(String, nullable=False)  # Store as string, not enum
    meta_data = Column(JSONB, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()")
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()")
    )
    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE", deferrable=True, initially="DEFERRED"),
        nullable=False
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE", deferrable=True, initially="DEFERRED"),
        nullable=False
    )

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    user = relationship("User", back_populates="messages")
    contexts = relationship("Context", back_populates="message")

    def __repr__(self):
        return f"<Message {self.id} ({self.role})>"