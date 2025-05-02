"""Test configuration and fixtures."""
import pytest
import pytest_asyncio
import asyncio
from typing import AsyncGenerator, Generator, Dict, Optional, List
from unittest.mock import patch
from tests.mocks.anthropic_mock import MockModelClient
import os
from dotenv import load_dotenv
from pathlib import Path
from redis import Redis
from redis.asyncio import Redis as AsyncRedis
from app.core.redis import RedisClient
from app.core.monitoring import TelemetryService, RateLimiter
from tests.mocks.redis_mock import MockRedis
from fastapi.testclient import TestClient
from app.main import app as fastapi_app
from app.core.websocket import WebSocketManager, WebSocketRateLimiter
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.db.session import get_async_session, init_db
from app.models.user import User
from sqlalchemy import text
from httpx import AsyncClient
import sys
from tests.utils.websocket_test_helper import WebSocketTestHelper
from app.core.auth import create_access_token
from datetime import timedelta
from app.core.config import Settings

# Load test environment variables
load_dotenv(Path(__file__).parent / ".env.test")

# Global state for service mocking
patcher = None

@pytest.fixture
def app():
    """Get FastAPI application."""
    return fastapi_app

@pytest_asyncio.fixture
async def async_test_client():
    """Async test client fixture."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

@pytest.fixture
def test_settings():
    """Get test settings."""
    return Settings(ENVIRONMENT="test")

@pytest.fixture
def client(app):
    """Get test client."""
    return TestClient(app)

@pytest.fixture
async def auth_token(test_user: User, test_settings: Settings) -> str:
    """Create auth token for test user."""
    return create_access_token(
        subject=test_user.id,
        expires_delta=timedelta(minutes=30),
        settings=test_settings
    )

@pytest.fixture(scope="function")
async def db_engine() -> AsyncGenerator:
    """Get database engine."""
    try:
        await init_db()
        yield
    finally:
        pass

@pytest_asyncio.fixture(scope="function")
async def db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session with proper cleanup."""
    session = await get_async_session().__anext__()
    try:
        # Start a transaction
        await session.begin()
        yield session
    finally:
        # Rollback any changes and close
        await session.rollback()
        await session.close()

@pytest.fixture
async def redis_client(request) -> AsyncGenerator[RedisClient, None]:
    """Get Redis client.
    
    Uses real Redis for integration tests, mock Redis for unit tests.
    """
    if "real_service" in request.keywords:
        # Use real Redis for integration tests
        redis = RedisClient(
            host=os.getenv("REDIS_HOST", "redis-test"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            db=int(os.getenv("REDIS_DB", 0))
        )
    else:
        # Use mock Redis for unit tests
        redis = MockRedis()
        
    try:
        yield redis
    finally:
        if "real_service" in request.keywords:
            # Clean up real Redis
            await redis.flushdb()
            await redis.flushall()
        await redis.aclose()

@pytest.fixture
async def websocket_manager(redis_client) -> WebSocketManager:
    """Create WebSocket manager with Redis client."""
    manager = WebSocketManager(redis_client=redis_client)
    try:
        yield manager
    finally:
        await manager.cleanup()

@pytest.fixture
async def rate_limiter(redis_client) -> WebSocketRateLimiter:
    """Create rate limiter with Redis client."""
    limiter = WebSocketRateLimiter(
        redis=redis_client,
        max_connections=5,
        messages_per_minute=60,
        messages_per_hour=1000,
        messages_per_day=10000,
        max_messages_per_second=10,
        rate_limit_window=60,
        connect_timeout=5.0,
        message_timeout=1.0
    )
    try:
        yield limiter
    finally:
        await limiter.clear_all()

@pytest.fixture
async def websocket_test_helper(
    websocket_manager,
    rate_limiter,
    test_user: User,
    auth_token: str
) -> AsyncGenerator[WebSocketTestHelper, None]:
    """Get WebSocket test helper."""
    helper = WebSocketTestHelper(
        websocket_manager=websocket_manager,
        rate_limiter=rate_limiter,
        test_user_id=test_user.id,
        auth_token=auth_token,
        test_ip="127.0.0.1",
        message_timeout=1.0,
        connect_timeout=5.0
    )
    try:
        yield helper
    finally:
        await helper.cleanup()

@pytest.fixture
async def test_helpers() -> List[WebSocketTestHelper]:
    """Track WebSocket test helpers for cleanup."""
    helpers = []
    yield helpers
    for helper in helpers:
        await helper.cleanup()

@pytest.fixture(scope="function")
async def telemetry_service(redis_client) -> AsyncGenerator[TelemetryService, None]:
    """Get telemetry service."""
    service = TelemetryService(redis_client)
    try:
        yield service
    finally:
        await service.clear_all()

@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch):
    """Set up test environment variables."""
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("REDIS_HOST", "redis-test")
    monkeypatch.setenv("REDIS_PORT", "6379")
    monkeypatch.setenv("REDIS_DB", "0")
    monkeypatch.setenv("POSTGRES_HOST", "db-test")
    monkeypatch.setenv("POSTGRES_PORT", "5432")
    monkeypatch.setenv("POSTGRES_USER", "postgres")
    monkeypatch.setenv("POSTGRES_PASSWORD", "postgres")
    monkeypatch.setenv("POSTGRES_DB", "test_db")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("SECRET_KEY", "test_secret_key")
    monkeypatch.setenv("ALGORITHM", "HS256")
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
    monkeypatch.setenv("FIRST_SUPERUSER", "admin@example.com")
    monkeypatch.setenv("FIRST_SUPERUSER_PASSWORD", "admin")

@pytest.fixture(autouse=True)
async def override_redis_dependency(monkeypatch, redis_client, request):
    """Override Redis dependency unless using real_service."""
    if "real_service" not in request.keywords:
        try:
            from app.api import deps
            async def async_get_redis():
                return redis_client
            monkeypatch.setattr(deps, "get_redis", async_get_redis)
        except ImportError:
            pass

@pytest.fixture
async def test_user(db: AsyncSession):
    """Create test user."""
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

@pytest.fixture(scope="function", autouse=True)
async def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()

@pytest_asyncio.fixture(scope="function")
async def initialize_test_db():
    """Initialize test database with proper cleanup."""
    await init_db()
    yield
    # Clean up database after tests
    async for session in get_async_session():
        await session.execute(text("DROP SCHEMA public CASCADE;"))
        await session.execute(text("CREATE SCHEMA public;"))
        await session.commit()
        await session.close()

@pytest.fixture(autouse=True)
async def clean_users_table(db: AsyncSession, initialize_test_db):
    """Clean users table between tests with proper transaction handling."""
    await db.begin_nested()  # Create a savepoint
    await db.execute(text("TRUNCATE TABLE users RESTART IDENTITY CASCADE;"))
    await db.commit()

@pytest_asyncio.fixture(autouse=True)
async def cleanup_websockets(websocket_manager: WebSocketManager):
    """Fixture to ensure WebSocket connections are properly closed after each test."""
    yield
    # Allow any pending WebSocket operations to complete
    await asyncio.sleep(0.1)
    # Clear all connections
    await websocket_manager.clear_all_connections()
    # Give tasks time to clean up
    await asyncio.sleep(0.1)

# Conditional patching based on test marker
def pytest_runtest_setup(item):
    """Set up test environment based on markers."""
    global patcher
    if 'mock_service' in item.keywords:
        patcher = patch('app.core.model.ModelClient', MockModelClient)
        patcher.start()
    elif 'real_service' in item.keywords:
        # Ensure no patch is applied for real_service tests
        if patcher:
            patcher.stop()
            patcher = None

def pytest_runtest_teardown(item, nextitem):
    """Clean up test environment after each test."""
    global patcher
    if patcher:
        patcher.stop()
        patcher = None

@pytest.fixture(scope="session", autouse=True)
def load_test_env():
    """Ensure test environment variables are loaded."""
    if not os.getenv("ENVIRONMENT") == "test":
        pytest.fail("Test environment not properly configured. ENVIRONMENT must be 'test'")
    if not os.getenv("REDIS_HOST") == "redis-test":
        pytest.fail("Redis test configuration not properly loaded")

def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "real_service: mark test to use real services"
    )
    config.addinivalue_line(
        "markers", "mock_service: mark test to use mock services"
    )

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for tests."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture(scope="function")
async def initialize_test_db() -> None:
    """Initialize test database with proper cleanup."""
    await init_db()

@pytest.fixture(scope="function")
def mock_model_client() -> MockModelClient:
    """Get mock model client."""
    with patch("app.core.model.ModelClient", MockModelClient):
        yield MockModelClient()

@pytest_asyncio.fixture(scope="function")
async def redis_client() -> AsyncGenerator[RedisClient, None]:
    """Get Redis client with proper cleanup."""
    if "real_service" in pytest.mark.real_service.args:
        client = RedisClient()
    else:
        client = MockRedis()
    try:
        yield client
    finally:
        await client.aclose()

@pytest_asyncio.fixture(scope="function")
async def rate_limiter(redis_client: RedisClient) -> AsyncGenerator[RateLimiter, None]:
    """Get rate limiter with proper cleanup."""
    limiter = RateLimiter(redis_client)
    try:
        yield limiter
    finally:
        await limiter.clear_all()

@pytest_asyncio.fixture(scope="function")
async def websocket_manager(redis_client: RedisClient) -> AsyncGenerator[WebSocketManager, None]:
    """Get WebSocket manager with proper cleanup."""
    manager = WebSocketManager(redis_client)
    try:
        yield manager
    finally:
        await manager.clear_all_connections()

@pytest_asyncio.fixture(scope="function")
async def websocket_rate_limiter(redis_client: RedisClient) -> AsyncGenerator[WebSocketRateLimiter, None]:
    """Get WebSocket rate limiter with proper cleanup."""
    limiter = WebSocketRateLimiter(redis_client)
    try:
        yield limiter
    finally:
        await limiter.clear_all()

@pytest.fixture(scope="function")
def test_client() -> Generator[TestClient, None, None]:
    """Get test client."""
    with TestClient(fastapi_app) as client:
        yield client

@pytest_asyncio.fixture(scope="function")
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Get async test client."""
    async with AsyncClient(app=fastapi_app, base_url="http://test") as client:
        yield client 