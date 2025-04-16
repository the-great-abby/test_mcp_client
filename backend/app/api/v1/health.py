"""Health check endpoints."""
from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from redis import Redis
import json
import logging

from app.db.session import get_async_session as get_db
from app.core.redis import get_redis

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/health")
async def health_check(
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis)
):
    """Health check endpoint."""
    db_status = "healthy"
    redis_status = "healthy"
    status_code = 200

    # Check database connection
    try:
        await db.execute(text("SELECT 1"))
        await db.commit()  # Ensure transaction is committed
    except Exception as e:
        logger.error("Database health check failed", exc_info=True)
        db_status = "unhealthy"
        status_code = 503

    # Check Redis connection
    try:
        await redis.ping()
    except Exception as e:
        logger.error("Redis health check failed", exc_info=True)
        redis_status = "unhealthy"
        status_code = 503

    # Overall status is unhealthy if either component is unhealthy
    overall_status = "healthy" if all(s == "healthy" for s in [db_status, redis_status]) else "unhealthy"
    
    response = {
        "status": overall_status,
        "details": {
            "database": {"status": db_status},
            "redis": {"status": redis_status}
        }
    }

    return Response(
        status_code=status_code,
        content=json.dumps(response),
        media_type="application/json"
    ) 