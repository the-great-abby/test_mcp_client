import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
import logging
from unittest.mock import AsyncMock, patch
from fastapi import status
from sqlalchemy.exc import SQLAlchemyError
from redis.exceptions import RedisError

from app.api.health import router as health_router
from app.core.errors import AppError
from app.db.base import get_db
from app.core.redis import get_redis

@pytest.fixture
def app():
    """Create a test FastAPI application."""
    app = FastAPI()
    app.include_router(health_router)
    return app

@pytest.fixture
async def mock_db():
    """Mock database session for testing."""
    db = AsyncMock()
    db.execute = AsyncMock()
    db.close = AsyncMock()
    return db

@pytest.fixture
async def mock_redis():
    """Mock Redis client for testing."""
    redis = AsyncMock()
    redis.ping = AsyncMock()
    redis.close = AsyncMock()
    return redis

@pytest.mark.asyncio
async def test_health_check_healthy(app, mock_db, mock_redis):
    """Test health check when all services are healthy."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Configure mocks
        mock_db.execute.return_value = AsyncMock()
        mock_redis.ping.return_value = True
        
        # Override dependencies
        app.dependency_overrides = {
            get_db: lambda: mock_db,
            get_redis: lambda: mock_redis
        }

        response = await client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["status"] == "healthy"
        assert data["components"]["database"] == "healthy"
        assert data["components"]["redis"] == "healthy"

@pytest.mark.asyncio
async def test_health_check_unhealthy_db(app, mock_db, mock_redis):
    """Test health check when database is unhealthy."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Configure mocks
        mock_db.execute.side_effect = SQLAlchemyError("DB Error")
        mock_redis.ping.return_value = True
        
        # Override dependencies
        app.dependency_overrides = {
            get_db: lambda: mock_db,
            get_redis: lambda: mock_redis
        }

        response = await client.get("/health")
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        data = response.json()
        
        assert data["status"] == "unhealthy"
        assert "unhealthy" in data["components"]["database"]
        assert "DB Error" in data["components"]["database"]
        assert data["components"]["redis"] == "healthy"

@pytest.mark.asyncio
async def test_health_check_unhealthy_redis(app, mock_db, mock_redis):
    """Test health check when Redis is unhealthy."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Configure mocks
        mock_db.execute.return_value = AsyncMock()
        mock_redis.ping.side_effect = RedisError("Redis Error")
        
        # Override dependencies
        app.dependency_overrides = {
            get_db: lambda: mock_db,
            get_redis: lambda: mock_redis
        }

        response = await client.get("/health")
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        data = response.json()
        
        assert data["status"] == "unhealthy"
        assert data["components"]["database"] == "healthy"
        assert "unhealthy" in data["components"]["redis"]
        assert "Redis Error" in data["components"]["redis"]

@pytest.mark.asyncio
async def test_health_check_all_unhealthy(app, mock_db, mock_redis):
    """Test health check when all services are unhealthy."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Configure mocks
        mock_db.execute.side_effect = SQLAlchemyError("DB Error")
        mock_redis.ping.side_effect = RedisError("Redis Error")
        
        # Override dependencies
        app.dependency_overrides = {
            get_db: lambda: mock_db,
            get_redis: lambda: mock_redis
        }

        response = await client.get("/health")
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        data = response.json()
        
        assert data["status"] == "unhealthy"
        assert "unhealthy" in data["components"]["database"]
        assert "DB Error" in data["components"]["database"]
        assert "unhealthy" in data["components"]["redis"]
        assert "Redis Error" in data["components"]["redis"]