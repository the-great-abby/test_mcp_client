import pytest
from datetime import datetime, UTC
from app.core.monitoring import TelemetryService
from app.core.redis import RedisClient

@pytest.mark.asyncio
async def test_record_model_call(redis_client: RedisClient) -> None:
    """Test recording a model call with metrics."""
    telemetry = TelemetryService(redis_client)
    user_id = "user1"
    date = datetime.now(UTC).strftime("%Y-%m-%d")
    
    # Record a model call
    await telemetry.record_model_call(
        user_id=user_id,
        model="gpt-4",
        tokens=150
    )
    
    # Check user-specific metrics
    user_metrics = await telemetry.get_user_metrics(user_id, date)
    assert user_metrics["model_calls"] == 1
    assert user_metrics["tokens_used"] == 150
    
    # Check global metrics
    global_metrics = await telemetry.get_global_metrics()
    assert global_metrics["count"] == 1
    assert global_metrics["tokens"] == 150

@pytest.mark.asyncio
async def test_record_cache_hit(redis_client: RedisClient):
    """Test recording a cache hit with metrics."""
    telemetry = TelemetryService(redis_client)
    user_id = "user1"
    date = datetime.now(UTC).strftime("%Y-%m-%d")
    
    # Record a cache hit
    await telemetry.record_cache_hit(user_id=user_id)
    
    # Check user-specific metrics
    user_metrics = await telemetry.get_user_metrics(user_id, date)
    assert user_metrics["cache_hits"] == 1
    
    # Check global metrics
    global_metrics = await telemetry.get_global_metrics()
    assert global_metrics.get("cache_hits", 0) == 1

@pytest.mark.asyncio
async def test_multiple_users(redis_client: RedisClient):
    """Test recording metrics for multiple users."""
    telemetry = TelemetryService(redis_client)
    date = datetime.now(UTC).strftime("%Y-%m-%d")
    
    # Record calls for user1
    await telemetry.record_model_call(
        user_id="user1",
        model="gpt-4",
        tokens=150
    )
    await telemetry.record_cache_hit("user1")
    
    # Record calls for user2
    await telemetry.record_model_call(
        user_id="user2",
        model="gpt-4",
        tokens=300
    )
    await telemetry.record_cache_hit("user2")
    
    # Check user1 metrics
    user1_metrics = await telemetry.get_user_metrics("user1", date)
    assert user1_metrics["model_calls"] == 1
    assert user1_metrics["tokens_used"] == 150
    assert user1_metrics["cache_hits"] == 1
    
    # Check user2 metrics
    user2_metrics = await telemetry.get_user_metrics("user2", date)
    assert user2_metrics["model_calls"] == 1
    assert user2_metrics["tokens_used"] == 300
    assert user2_metrics["cache_hits"] == 1
    
    # Check global metrics
    global_metrics = await telemetry.get_global_metrics()
    assert global_metrics["count"] == 2
    assert global_metrics["tokens"] == 450 