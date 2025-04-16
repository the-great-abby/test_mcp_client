from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from typing import Dict
from fastapi.responses import JSONResponse
import logging

from app.db.base import get_db
from app.core.redis import get_redis

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/health")
async def health_check(
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis)
) -> Dict[str, str]:
    """
    Health check endpoint that checks database and Redis connectivity.
    """
    status = "healthy"
    db_status = "healthy"
    redis_status = "healthy"
    db_error = None
    redis_error = None

    # Check database connection
    try:
        await db.execute("SELECT 1")
    except Exception as e:
        status = "unhealthy"
        db_status = "unhealthy"
        db_error = str(e)
        logger.error(f"Database health check failed: {e}")

    # Check Redis connection
    try:
        await redis.ping()
    except Exception as e:
        status = "unhealthy"
        redis_status = "unhealthy"
        redis_error = str(e)
        logger.error(f"Redis health check failed: {e}")

    response = {
        "status": status,
        "details": {
            "database": {
                "status": db_status,
                "error": db_error
            },
            "redis": {
                "status": redis_status,
                "error": redis_error
            }
        }
    }

    return JSONResponse(
        status_code=503 if status == "unhealthy" else 200,
        content=response
    ) 