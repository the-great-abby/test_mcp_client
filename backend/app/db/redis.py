from redis.asyncio import Redis
from app.core.config import settings

async def get_redis() -> Redis:
    redis = Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        decode_responses=True
    )
    try:
        yield redis
    finally:
        await redis.aclose() 