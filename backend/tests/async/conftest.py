import pytest
from tests.helpers import MockRedis
from app.main import app as fastapi_app
from app.api.deps import get_redis
from httpx import AsyncClient

@pytest.fixture
async def async_redis_client():
    """Create a mock async Redis client for async tests."""
    client = MockRedis()
    yield client
    await client.flushdb()

@pytest.fixture
async def websocket_manager(async_redis_client):
    """Create a WebSocketManager with an async mock Redis client."""
    from app.core.websocket import WebSocketManager
    return WebSocketManager(redis_client=async_redis_client)

@pytest.fixture
async def rate_limiter(async_redis_client):
    """Create a WebSocketRateLimiter with an async mock Redis client."""
    from app.core.websocket_rate_limiter import WebSocketRateLimiter
    return WebSocketRateLimiter(redis=async_redis_client)

@pytest.fixture(autouse=True)
async def override_redis_dependency(async_redis_client):
    async def _get_redis_override():
        return async_redis_client
    fastapi_app.dependency_overrides[get_redis] = _get_redis_override
    yield
    fastapi_app.dependency_overrides.pop(get_redis, None)

@pytest.fixture
def app():
    """FastAPI app fixture for async tests."""
    return fastapi_app

@pytest.fixture
def auth_token(test_user, test_settings):
    from datetime import timedelta
    from app.core.auth import create_access_token
    access_token_expires = timedelta(minutes=getattr(test_settings, 'ACCESS_TOKEN_EXPIRE_MINUTES', 30))
    return create_access_token(
        data={"sub": str(test_user.id)},
        expires_delta=access_token_expires,
        settings=test_settings
    )

@pytest.fixture(autouse=True)
async def clear_rate_limiter_state(async_redis_client):
    keys = await async_redis_client.keys("ws:active:*")
    for key in keys:
        await async_redis_client.delete(key)

@pytest.fixture
async def async_test_client():
    """Async HTTPX client for async FastAPI tests."""
    async with AsyncClient(app=fastapi_app, base_url="http://test") as ac:
        yield ac 