"""
Tests for monitoring, telemetry and rate limiting functionality.
"""
import json
import asyncio
from datetime import datetime, timedelta, UTC

import pytest
from app.core.redis import RedisClient
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import FastAPI, Request
from httpx import AsyncClient
from fastapi.responses import JSONResponse
from fastapi import status

from app.core.monitoring import RateLimiter, TelemetryService, rate_limit
from app.core.config import settings

@pytest.mark.asyncio
async def test_record_model_call(
    app: FastAPI,
    async_test_client: AsyncClient,
    redis_client: RedisClient,
    initialize_test_db
) -> None:
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
async def test_record_cache_hit(
    app: FastAPI,
    async_test_client: AsyncClient,
    redis_client: RedisClient,
    initialize_test_db
):
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
async def test_multiple_users(
    app: FastAPI,
    async_test_client: AsyncClient,
    redis_client: RedisClient,
    initialize_test_db
):
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

@pytest.mark.asyncio
async def test_rate_limiter(app: FastAPI, async_test_client: AsyncClient, redis_client: RedisClient, initialize_test_db):
    """Test that rate limiting works correctly."""
    requests_per_window = 2
    window_seconds = 1
    limiter = RateLimiter(redis_client, requests_per_window, window_seconds)

    @app.get("/api/v1/test/rate_limit")
    async def test_route(request: Request):
        allowed = await limiter.check_rate_limit(request.headers.get("X-User-Id", "default"))
        print(f"[DEBUG] Rate limit allowed: {allowed}")
        # Print Redis state for debugging
        if hasattr(redis_client, 'store'):
            print(f"[DEBUG] Redis store: {redis_client.store}")
        if not allowed:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"error": "Rate limit exceeded", "code": "rate_limit_exceeded"}
            )
        return {"status": "ok"}

    # Make initial requests within limit
    for i in range(requests_per_window):
        print(f"[DEBUG] Sending request {i+1}")
        response = await async_test_client.get(
            "/api/v1/test/rate_limit",
            headers={"X-User-Id": "test_user"}
        )
        print(f"[DEBUG] Response {i+1} status: {response.status_code}")
        assert response.status_code == 200

    # Next request should be rate limited
    print("[DEBUG] Sending request for rate limit exceedance")
    response = await async_test_client.get(
        "/api/v1/test/rate_limit",
        headers={"X-User-Id": "test_user"}
    )
    print(f"[DEBUG] Final response status: {response.status_code}")
    assert response.status_code == 429

@pytest.mark.asyncio
async def test_telemetry_with_metadata(redis_client: RedisClient, initialize_test_db):
    """Test telemetry with metadata recording."""
    service = TelemetryService(redis_client)
    user_id = "test_user"
    model = "gpt-4"
    tokens = 150
    date = datetime.now(UTC).strftime("%Y-%m-%d")
    
    await service.record_model_call(
        user_id=user_id,
        model=model,
        tokens=tokens
    )
    
    # Check user metrics
    user_metrics = await service.get_user_metrics(user_id, date)
    assert user_metrics["model_calls"] == 1
    assert user_metrics["tokens_used"] == 150
    
    # Check global metrics
    global_metrics = await service.get_global_metrics()
    assert global_metrics["count"] == 1
    assert global_metrics["tokens"] == 150

@pytest.mark.asyncio
async def test_get_user_metrics(redis_client: RedisClient, initialize_test_db):
    """Test getting user metrics."""
    service = TelemetryService(redis_client)
    user_id = "test_user"
    model = "gpt-4"
    date = datetime.now(UTC).strftime("%Y-%m-%d")
    
    # Record some activity
    await service.record_model_call(
        user_id=user_id,
        model=model,
        tokens=150
    )
    await service.record_cache_hit(user_id)
    
    # Check metrics
    metrics = await service.get_user_metrics(user_id, date)
    assert metrics["model_calls"] == 1
    assert metrics["tokens_used"] == 150
    assert metrics["cache_hits"] == 1

@pytest.mark.asyncio
async def test_get_global_metrics(redis_client: RedisClient, initialize_test_db):
    """Test getting global metrics."""
    service = TelemetryService(redis_client)
    model = "gpt-4"
    
    # Record activity for multiple users
    await service.record_model_call(
        user_id="user1",
        model=model,
        tokens=150
    )
    await service.record_cache_hit("user1")
    
    await service.record_model_call(
        user_id="user2",
        model=model,
        tokens=300
    )
    await service.record_cache_hit("user2")
    
    # Check global metrics
    global_metrics = await service.get_global_metrics()
    assert global_metrics["count"] == 2
    assert global_metrics["tokens"] == 450 