import pytest
from app.core.config import Settings
import os
from fastapi.testclient import TestClient
from app.main import app
from app.core.websocket import WebSocketManager
from tests.helpers import MockRedis
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_async_session, init_db
from app.models.user import User
from sqlalchemy import text

@pytest.fixture
def test_settings():
    return Settings(ENVIRONMENT="test")

@pytest.fixture
def test_client():
    return TestClient(app)

@pytest.fixture
def websocket_manager():
    return WebSocketManager()

@pytest.fixture
def redis_client():
    return MockRedis()

@pytest.fixture(autouse=True)
def override_redis_dependency(monkeypatch, redis_client):
    try:
        from app.api import deps
        def sync_get_redis():
            return redis_client
        monkeypatch.setattr(deps, "get_redis", sync_get_redis)
    except ImportError:
        pass

@pytest.fixture
async def db() -> AsyncSession:
    async for session in get_async_session():
        yield session 

@pytest.fixture
async def test_user(db: AsyncSession):
    user = User(
        id="123e4567-e89b-12d3-a456-426614174000",
        email="test@example.com",
        username="testuser",
        hashed_password="fakehashedpassword",
        is_active=True,
        is_superuser=False
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

@pytest.fixture
async def initialize_test_db():
    await init_db()

@pytest.fixture(autouse=True)
async def clean_users_table(db: AsyncSession):
    await db.execute(text("TRUNCATE TABLE users RESTART IDENTITY CASCADE;"))
    await db.commit() 