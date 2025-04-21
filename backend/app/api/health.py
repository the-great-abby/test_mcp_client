from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from typing import Dict
import logging
from sqlalchemy import text

from app.db.base import get_db
from app.core.redis import get_redis

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/health")
async def health_check(
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis)
) -> JSONResponse:
    """
    Health check endpoint that checks database and Redis connectivity.
    Returns appropriate status codes based on component health.
    """
    response = {
        "status": "healthy",
        "components": {
            "database": "healthy",
            "redis": "healthy"
        }
    }
    status_code = status.HTTP_200_OK

    try:
        await db.execute(text("SELECT 1"))
    except Exception as e:
        response["status"] = "unhealthy"
        response["components"]["database"] = f"unhealthy: {str(e)}"
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    try:
        await redis.ping()
    except Exception as e:
        response["status"] = "unhealthy"
        response["components"]["redis"] = f"unhealthy: {str(e)}"
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(content=response, status_code=status_code)