"""
Shared fixtures for WebSocket integration tests.
"""
import pytest
import asyncio
import uuid
from datetime import timedelta
from typing import AsyncGenerator, List
from app.core.websocket import WebSocketManager
from app.core.websocket_rate_limiter import WebSocketRateLimiter
from app.core.redis import get_redis
from app.core.auth import create_access_token
from app.models import User
from tests.utils.websocket_test_helper import WebSocketTestHelper
import os
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_session

@pytest.fixture
async def redis_client() -> AsyncGenerator:
    """Get Redis client for testing."""
    redis = await get_redis()
    try:
        yield redis
    finally:
        await redis.flushdb()
        await redis.aclose()

@pytest.fixture
async def redis_rate_limiter(redis_client) -> AsyncGenerator[WebSocketRateLimiter, None]:
    """Get WebSocket rate limiter with proper cleanup."""
    limiter = WebSocketRateLimiter(
        redis=redis_client,
        max_connections=50,  # Higher limit for stress tests
        messages_per_minute=100,  # Higher limit for stress tests
        messages_per_hour=1000,
        messages_per_day=10000
    )
    try:
        yield limiter
    finally:
        await limiter.clear_all()

@pytest.fixture
async def websocket_manager(redis_client) -> AsyncGenerator[WebSocketManager, None]:
    """Get WebSocket manager instance."""
    manager = WebSocketManager(redis_client=redis_client)
    try:
        yield manager
    finally:
        await manager.clear_all_connections()

@pytest.fixture
async def rate_limiter(redis_client) -> AsyncGenerator[WebSocketRateLimiter, None]:
    """Get rate limiter instance."""
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
async def test_helpers(
    websocket_manager: WebSocketManager,
    rate_limiter: WebSocketRateLimiter,
    test_user: User
) -> List[WebSocketTestHelper]:
    """List to track test helpers for cleanup.
    
    Pre-initializes a pool of helpers for stress testing.
    """
    helpers = []
    # Pre-initialize 50 helpers for stress testing
    for i in range(50):
        helper = WebSocketTestHelper(
            websocket_manager=websocket_manager,
            rate_limiter=rate_limiter,
            test_user_id=test_user.id,
            test_ip=f"192.168.1.{i+1}"  # Use unique IPs for rate limiting
        )
        helpers.append(helper)
    return helpers

@pytest.fixture
async def test_user(db: AsyncSession) -> User:
    """Create and persist a test user in the DB."""
    user = User(
        id=str(uuid.uuid4()),
        email="test@example.com",
        username="testuser",
        hashed_password="test_hash",
        is_active=True,
        is_superuser=False
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

@pytest.fixture
def auth_token(test_user: User) -> str:
    """Create an authentication token for testing."""
    return create_access_token(
        data={"sub": str(test_user.id)},
        expires_delta=timedelta(minutes=15)
    )

def ws_helper_fixture_debug(request, use_mock, auth_token):
    test_name = getattr(request, 'node', None)
    test_name = getattr(test_name, 'name', 'unknown') if test_name else 'unknown'
    print(f"[DEBUG][ws_helper fixture] test_name: {test_name}, use_mock: {use_mock}, auth_token: {auth_token}")

@pytest.fixture
async def ws_helper(
    websocket_manager: WebSocketManager,
    rate_limiter: WebSocketRateLimiter,
    test_helpers: List[WebSocketTestHelper],
    test_user: User,
    auth_token: str,
    request
) -> AsyncGenerator[WebSocketTestHelper, None]:
    """
    Get WebSocket test helper.
    Uses mock WebSocket if:
      - The test is marked with @pytest.mark.mock_service
      - OR the USE_MOCK_WEBSOCKET environment variable is set to '1' or 'true'
      - OR the pytest config option --use-mock-websocket is set
    Otherwise, uses the real WebSocket client.
    """
    print("[DEBUG][ws_helper] fixture executing...")

    use_mock = False
    # Check for marker
    if request.node.get_closest_marker("mock_service"):
        use_mock = True
    # Check for environment variable
    if os.environ.get("USE_MOCK_WEBSOCKET", "").lower() in ("1", "true", "yes"): 
        use_mock = True
    # Check for pytest config option
    if hasattr(request.config, "getoption") and request.config.getoption("use_mock_websocket", default=False):
        use_mock = True

    print(f"[DEBUG][ws_helper] USE_MOCK_WEBSOCKET env: {os.environ.get('USE_MOCK_WEBSOCKET')}, use_mock: {use_mock}")

    # Use dummy token in mock mode, real token otherwise
    token_to_use = "dummy-token" if use_mock else auth_token
    helper = WebSocketTestHelper(
        websocket_manager=websocket_manager,
        rate_limiter=rate_limiter,
        test_user_id=test_user.id,
        auth_token=token_to_use,
        mock_mode=use_mock,
        ws_token_query=request.config.getoption('ws_token_query', False)
    )
    test_helpers.append(helper)
    ws_helper_fixture_debug(request, use_mock, token_to_use)
    try:
        yield helper
    finally:
        await helper.cleanup()

@pytest.fixture(autouse=True)
async def cleanup_helpers(test_helpers: List[WebSocketTestHelper]):
    """Automatically clean up all test helpers."""
    try:
        yield
    finally:
        for helper in test_helpers:
            await helper.cleanup()

@pytest.fixture(autouse=True)
def enforce_websocket_mode(request):
    """
    Fail fast if test is not explicitly marked with one of the required markers.
    - If @pytest.mark.mock_service: require USE_MOCK_WEBSOCKET=1/true/yes
    - If @pytest.mark.real_websocket: require USE_MOCK_WEBSOCKET not set or 0/false/no
    - If @pytest.mark.real_redis: require REDIS_HOST=db-test or redis-test
    - If @pytest.mark.real_anthropic: require ANTHROPIC_API_KEY set
    - If none: fail (all tests must be explicitly marked)
    """
    is_mock = request.node.get_closest_marker("mock_service") is not None
    is_real_ws = request.node.get_closest_marker("real_websocket") is not None
    is_real_redis = request.node.get_closest_marker("real_redis") is not None
    is_real_anthropic = request.node.get_closest_marker("real_anthropic") is not None
    env_ws = os.environ.get("USE_MOCK_WEBSOCKET", "0").lower()
    env_redis = os.environ.get("REDIS_HOST", "").lower()
    env_anthropic = os.environ.get("ANTHROPIC_API_KEY", "")

    if not (is_mock or is_real_ws or is_real_redis or is_real_anthropic):
        pytest.fail("All WebSocket integration tests must be marked with one of: @pytest.mark.mock_service, @pytest.mark.real_websocket, @pytest.mark.real_redis, @pytest.mark.real_anthropic.")
    if is_mock and env_ws not in ("1", "true", "yes"):
        pytest.fail(f"Mock WebSocket test requires USE_MOCK_WEBSOCKET=1/true/yes (env is '{env_ws}')")
    if is_real_ws and env_ws not in ("0", "false", "no", ""):
        pytest.fail(f"Real WebSocket test requires USE_MOCK_WEBSOCKET=0/false/no or unset (env is '{env_ws}')")
    if is_real_redis and env_redis not in ("db-test", "redis-test"):
        pytest.fail(f"Real Redis test requires REDIS_HOST=db-test or redis-test (env is '{env_redis}')")
    if is_real_anthropic and not env_anthropic:
        pytest.fail("Real Anthropic test requires ANTHROPIC_API_KEY to be set in the environment.") 