"""Health check endpoints."""
from datetime import datetime, UTC
from typing import Dict, Any
import json
import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_session
from app.models.health import Health

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_session)) -> Dict[str, Any]:
    """Health check endpoint."""
    try:
        # Create health check record
        health_check = Health(
            status="ok",
            details={"message": "Service is healthy"}
        )
        db.add(health_check)
        await db.commit()
        
        return {
            "status": "ok",
            "timestamp": datetime.now(UTC).isoformat(),
            "details": {
                "database": "ok",
                "api": "ok"
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "error",
            "timestamp": datetime.now(UTC).isoformat(),
            "details": {
                "error": str(e)
            }
        } 