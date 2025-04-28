"""
Context model for SQLAlchemy.
"""
from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base_class import Base
import uuid

class Context(Base):
    __tablename__ = "contexts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id", ondelete="CASCADE"), nullable=False)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False)
    meta_data = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    message = relationship("Message", back_populates="contexts")
    conversation = relationship("Conversation", back_populates="contexts")

    def __repr__(self):
        return f"<Context(id={self.id}, message_id={self.message_id})>"