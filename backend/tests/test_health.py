import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.redis import RedisClient
import os

# Get Docker service configuration from environment or use defaults
DOCKER_SERVICE_HOST = os.getenv("DOCKER_SERVICE_HOST", "backend-test")
DOCKER_SERVICE_PORT = int(os.getenv("DOCKER_SERVICE_PORT", "8000"))

@pytest.mark.asyncio
async def test_health_check_success(app: FastAPI, client: AsyncClient):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["details"]["database"]["status"] == "healthy"
    assert data["details"]["redis"]["status"] == "healthy"

@pytest.mark.asyncio
async def test_health_check_db_failure(app: FastAPI, client: AsyncClient):
    # Mock get_db to raise an exception
    async def mock_get_db():
        class DummySession:
            async def execute(self, *args, **kwargs):
                raise Exception("Database error")
        yield DummySession()
    from app.api.v1.health import get_db
    app.dependency_overrides[get_db] = mock_get_db

    response = await client.get("/api/v1/health")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "unhealthy"
    assert data["details"]["database"]["status"] == "unhealthy"

@pytest.mark.asyncio
async def test_health_check_redis_failure(app: FastAPI, client: AsyncClient):
    # Mock get_redis to raise an exception
    async def mock_get_redis():
        class DummyRedis:
            async def ping(self):
                raise Exception("Redis error")
        yield DummyRedis()
    from app.api.v1.health import get_redis
    app.dependency_overrides[get_redis] = mock_get_redis

    response = await client.get("/api/v1/health")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "unhealthy"
    assert data["details"]["redis"]["status"] == "unhealthy"