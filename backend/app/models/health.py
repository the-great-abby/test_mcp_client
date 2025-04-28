from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, func, JSON
from app.db.base_class import Base
from pydantic import BaseModel
from typing import Dict, Any, Literal

class Health(Base):
    """Health check record model."""
    __tablename__ = "health_checks"

    id = Column(Integer, primary_key=True, index=True)
    status = Column(String, nullable=False)
    details = Column(JSON)
    checked_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<Health {self.id}: {self.status}>"

class HealthResponse(BaseModel):
    """Health check response model."""
    status: Literal["ok", "error"]
    details: Dict[str, Dict[str, Any]] 