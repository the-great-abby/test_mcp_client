print("USING backend/tests/conftest.py")

import asyncio
import pytest
import pytest_asyncio
from typing import AsyncGenerator, Dict, Any, Optional, Union, List, Generator
from fastapi import FastAPI, APIRouter, Depends, HTTPException
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker, AsyncEngine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from redis.asyncio import Redis
from sqlalchemy import text
import logging
from fastapi.responses import JSONResponse
import time
from fastapi import status
from starlette.middleware.exceptions import ExceptionMiddleware
import os
import sys
from pathlib import Path

from app.core.errors import (
    AppError,
    NotFoundError,
    DataValidationError,
    app_error_handler,
    not_found_error_handler,
    validation_error_handler,
    generic_error_handler,
    setup_error_handlers
)
from app.api.router import router
from app.db.base import Base
from app.core.monitoring import RateLimiter, TelemetryService
from app.core.config import settings
from app.core.redis import RedisClient
from app.api.deps import get_db, get_redis
from app.main import app as main_app

# Configure logging for tests
def setup_test_logging():
    """Configure logging for tests with debug level and console output."""
    # Remove all existing handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Set up console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    
    # Use a more readable format for tests
    test_formatter = logging.Formatter(
        '\n%(asctime)s %(levelname)s [%(name)s] %(message)s\n  File "%(pathname)s", line %(lineno)d\n'
    )
    console_handler.setFormatter(test_formatter)
    
    # Configure root logger
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(console_handler)
    
    # Configure app loggers
    for logger_name in ['app', 'tests', 'websockets', 'aiohttp', 'fastapi']:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.DEBUG)
        logger.addHandler(console_handler)
        logger.propagate = False

# Set up logging at module import
setup_test_logging()

# Configure logger
logger = logging.getLogger(__name__)

# Test database URL - use environment variables with fallbacks
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "db-test")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "test_db")

# Use SQLite for local testing, PostgreSQL for Docker tests
TEST_SQLALCHEMY_DATABASE_URL = (
    "sqlite+aiosqlite:///:memory:"
    if os.getenv("TEST_DB") == "sqlite"
    else f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)

# Test Redis URL
TEST_REDIS_URL = f"redis://{os.getenv('REDIS_HOST', 'redis-test')}:{os.getenv('REDIS_PORT', '6379')}/1"

# Docker service configuration
DOCKER_SERVICE_HOST = os.getenv("DOCKER_SERVICE_HOST", "localhost")
DOCKER_SERVICE_PORT = int(os.getenv("DOCKER_SERVICE_PORT", "8000"))

# Base URL for tests
TEST_BASE_URL = f"http://{DOCKER_SERVICE_HOST}:{DOCKER_SERVICE_PORT}"

# Create test engine with connection pooling
engine = create_async_engine(
    TEST_SQLALCHEMY_DATABASE_URL,
    echo=True,
    future=True,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,  # Recycle connections after 30 minutes
    pool_pre_ping=True  # Enable connection health checks
)
async_session = async_sessionmaker(engine, expire_on_commit=False)

# Test router for error handling tests
test_router = APIRouter()

@test_router.get("/test/app-error")
async def test_app_error():
    """Test endpoint that raises an AppError."""
    raise AppError("Test error message", code="test_error")

@test_router.get("/test/not-found")
async def test_not_found():
    """Test endpoint that raises a NotFoundError."""
    raise NotFoundError("Resource not found")

@test_router.get("/test/validation-error")
async def test_validation_error():
    """Test endpoint that raises a ValidationError."""
    raise DataValidationError("Invalid data", errors={"field": "error"})

@test_router.get("/test/generic-error")
async def test_generic_error():
    """Test endpoint that raises a generic error."""
    try:
        raise Exception("Internal server error")
    except Exception as e:
        # Return error response directly
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": str(e) if settings.DEBUG else "Internal server error",
                "code": "internal_server_error"
            }
        )

@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture
async def app(redis_client: RedisClient) -> FastAPI:
    """Create a FastAPI test application."""
    # Override settings for testing
    from app.core.config import settings
    settings.WS_PING_TIMEOUT = 1  # Shorter timeout for tests
    settings.WS_MAX_HISTORY_SIZE = 10  # Smaller history size for tests
    settings.WS_MAX_CONNECTIONS_PER_USER = 3  # Fewer connections for tests
    settings.WS_RATE_LIMIT = 10  # Lower rate limit for tests
    
    app = FastAPI(debug=False)  # Explicitly disable debug mode
    
    # Set Redis client in app state
    app.state.redis = redis_client
    
    # Set up error handlers using the standard method
    setup_error_handlers(app)
    
    # Add test routes
    app.include_router(test_router, prefix="/api/v1")
    
    # Add WebSocket router
    from app.api.v1.websocket import router as websocket_router
    app.include_router(websocket_router)  # No prefix needed since it's in the router
    
    # Add health check router
    from app.api.v1.health import router as health_router
    app.include_router(health_router, prefix="/api/v1")
    
    # Debug: print all registered routes
    print("\nRegistered routes in test app:")
    for route in app.routes:
        print(f"ROUTE: {route.path} [methods: {getattr(route, 'methods', None)}]")

    # Add monitoring test routes
    @app.post("/api/v1/test/record_model_call")
    async def test_record_model_call(
        user_id: str,
        tokens: int,
        model: str = "test-model"
    ):
        telemetry = TelemetryService(redis_client)
        await telemetry.record_model_call(
            user_id=user_id,
            model=model,
            tokens=tokens
        )
        return {"status": "success"}

    @app.post("/api/v1/test/record_cache_hit")
    async def test_record_cache_hit(
        user_id: str
    ):
        telemetry = TelemetryService(redis_client)
        await telemetry.record_cache_hit(user_id)
        return {"status": "success"}

    return app

@pytest_asyncio.fixture
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Wait for database to be ready with exponential backoff
        max_retries = 10  # Increased from 5
        retry_count = 0
        while retry_count < max_retries:
            try:
                async with async_session() as session:
                    await session.execute(text("SELECT 1"))
                    await session.commit()
                break
            except Exception as e:
                retry_count += 1
                if retry_count == max_retries:
                    raise RuntimeError(f"Database not ready after {max_retries} attempts: {str(e)}") from e
                # Exponential backoff: wait longer between each retry
                await asyncio.sleep(2 ** retry_count)  # 2, 4, 8, 16... seconds
        
        # Add database session to client for convenience
        client.db = async_session
        yield client

@pytest.fixture
def sync_client(app: FastAPI) -> Generator:
    """Create a synchronous test client."""
    with TestClient(app, base_url="http://test") as client:
        yield client

class MockRedisPipeline:
    """Mock Redis pipeline implementation for testing."""
    
    def __init__(self, redis_instance):
        self.redis = redis_instance
        self.transaction = False
        self.watched_keys = set()
        self.commands = []
        self.results = []

    async def watch(self, *keys):
        """Watch keys for changes."""
        self.watched_keys.update(keys)
        return True

    async def multi(self):
        """Start a transaction."""
        self.transaction = True
        return True

    async def execute(self):
        """Execute all commands in the pipeline."""
        results = []
        for cmd, *args in self.commands:
            if cmd == "get":
                results.append(await self.redis.get(args[0]))
            elif cmd == "set":
                results.append(await self.redis.set(args[0], args[1], args[2]))
            elif cmd == "hset":
                results.append(await self.redis.hset(args[0], args[1], args[2]))
            elif cmd == "hget":
                results.append(await self.redis.hget(args[0], args[1]))
            elif cmd == "hincrby":
                results.append(await self.redis.hincrby(args[0], args[1], args[2]))
            elif cmd == "hgetall":
                results.append(await self.redis.hgetall(args[0]))
            elif cmd == "incr":
                results.append(await self.redis.incr(args[0]))
            elif cmd == "expire":
                results.append(await self.redis.expire(args[0], args[1]))
            elif cmd == "delete":
                results.append(await self.redis.delete(args[0]))
        
        self.commands = []
        self.transaction = False
        return results

    async def get(self, key: str):
        """Add get command to pipeline."""
        self.commands.append(("get", key))
        return self

    async def set(self, key: str, value: Any, ex: Optional[int] = None):
        """Add set command to pipeline."""
        self.commands.append(("set", key, value, ex))
        return self

    async def hset(self, key: str, field: str, value: Any):
        """Add hset command to pipeline."""
        self.commands.append(("hset", key, field, value))
        return self

    async def hget(self, key: str, field: str):
        """Add hget command to pipeline."""
        self.commands.append(("hget", key, field))
        return self

    async def hincrby(self, key: str, field: str, amount: int = 1):
        """Add hincrby command to pipeline."""
        self.commands.append(("hincrby", key, field, amount))
        return self

    async def hgetall(self, key: str):
        """Add hgetall command to pipeline."""
        self.commands.append(("hgetall", key))
        return self

    async def incr(self, key: str):
        """Add incr command to pipeline."""
        self.commands.append(("incr", key))
        return self

    async def expire(self, key: str, seconds: int):
        """Add expire command to pipeline."""
        self.commands.append(("expire", key, seconds))
        return self

    async def delete(self, key: str):
        """Add delete command to pipeline."""
        self.commands.append(("delete", key))
        return self

class MockRedis:
    """Mock Redis implementation for testing."""
    
    def __init__(self):
        self._data = {}
        self._hash_data = {}
        self._list_data = {}
        self._expires = {}
        self._expire_times = {}  # Store actual expiration timestamps

    async def ping(self):
        """Test Redis connection."""
        return True

    async def get(self, key: str) -> Optional[bytes]:
        """Get a value from Redis."""
        # Check if key has expired
        if key in self._expire_times:
            if time.time() >= self._expire_times[key]:
                # Key has expired
                del self._data[key]
                del self._expires[key]
                del self._expire_times[key]
                return None
            
        if key in self._data:
            value = self._data[key]
            if isinstance(value, str):
                return value.encode()
            elif isinstance(value, bytes):
                return value
            elif isinstance(value, int):
                return str(value).encode()
            return value
        return None

    async def set(
        self,
        key: str,
        value: Union[str, bytes, int],
        ex: Optional[int] = None
    ) -> bool:
        """Set a value in Redis."""
        if isinstance(value, (str, bytes)):
            self._data[key] = value
        else:
            self._data[key] = str(value)
        
        if ex is not None:
            self._expires[key] = ex
            self._expire_times[key] = time.time() + ex
        return True

    async def delete(self, key: str) -> bool:
        """Delete a key from Redis."""
        if key in self._data:
            del self._data[key]
            if key in self._expires:
                del self._expires[key]
            if key in self._expire_times:
                del self._expire_times[key]
            return True
        return False

    async def exists(self, key: str) -> bool:
        """Check if a key exists in Redis."""
        # Check expiration first
        if key in self._expire_times and time.time() >= self._expire_times[key]:
            # Key has expired
            del self._data[key]
            del self._expires[key]
            del self._expire_times[key]
            return False
        return key in self._data

    async def expire(self, key: str, seconds: int) -> bool:
        """Set an expiration on a key."""
        if key in self._data:
            self._expires[key] = seconds
            self._expire_times[key] = time.time() + seconds
            return True
        return False

    async def ttl(self, key: str) -> int:
        """Get the TTL of a key."""
        return self._expires.get(key, -1)

    async def incr(self, key: str) -> int:
        """Increment a counter."""
        # Check expiration first
        if key in self._expire_times and time.time() >= self._expire_times[key]:
            # Key has expired
            del self._data[key]
            del self._expires[key]
            del self._expire_times[key]
            self._data[key] = "0"
            
        if key not in self._data:
            self._data[key] = "0"
        value = int(self._data[key]) + 1
        self._data[key] = str(value)
        return value

    async def hget(self, key: str, field: str) -> Optional[bytes]:
        """Get a hash field."""
        if key in self._hash_data and field in self._hash_data[key]:
            value = self._hash_data[key][field]
            if isinstance(value, str):
                return value.encode()
            elif isinstance(value, int):
                return str(value).encode()
            return value
        return None

    async def hset(self, key: str, field: str, value: Any) -> int:
        """Set a hash field."""
        if key not in self._hash_data:
            self._hash_data[key] = {}
        self._hash_data[key][field] = value
        return 1

    async def hdel(self, key: str, field: str) -> int:
        """Delete a hash field."""
        if key in self._hash_data and field in self._hash_data[key]:
            del self._hash_data[key][field]
            return 1
        return 0

    async def hgetall(self, key: str) -> Dict[bytes, bytes]:
        """Get all fields in a hash."""
        if key in self._hash_data:
            return {
                k.encode(): str(v).encode()
                for k, v in self._hash_data[key].items()
            }
        return {}

    async def hincrby(self, key: str, field: str, amount: int = 1) -> int:
        """Increment a hash field by the given amount."""
        if key not in self._hash_data:
            self._hash_data[key] = {}
        if field not in self._hash_data[key]:
            self._hash_data[key][field] = 0
        self._hash_data[key][field] = int(self._hash_data[key][field]) + amount
        return self._hash_data[key][field]

    async def lpush(self, key: str, *values: Any) -> int:
        """Push values onto the head of a list."""
        if key not in self._list_data:
            self._list_data[key] = []
        for value in values:
            if isinstance(value, (str, bytes)):
                self._list_data[key].insert(0, value)
            else:
                self._list_data[key].insert(0, str(value))
        return len(self._list_data[key])

    async def lrange(self, key: str, start: int, stop: int) -> List[bytes]:
        """Get a range of elements from a list."""
        if key not in self._list_data:
            return []
        # Handle negative indices
        if start < 0:
            start = max(len(self._list_data[key]) + start, 0)
        if stop < 0:
            stop = max(len(self._list_data[key]) + stop + 1, 0)
        else:
            stop = min(stop + 1, len(self._list_data[key]))
        
        return [
            v.encode() if isinstance(v, str) else v
            for v in self._list_data[key][start:stop]
        ]

    async def ltrim(self, key: str, start: int, stop: int) -> bool:
        """Trim a list to the specified range."""
        if key not in self._list_data:
            return True
        # Handle negative indices
        if start < 0:
            start = max(len(self._list_data[key]) + start, 0)
        if stop < 0:
            stop = max(len(self._list_data[key]) + stop + 1, 0)
        else:
            stop = min(stop + 1, len(self._list_data[key]))
        
        self._list_data[key] = self._list_data[key][start:stop]
        return True

    def pipeline(self) -> MockRedisPipeline:
        """Create a pipeline."""
        return MockRedisPipeline(self)

@pytest_asyncio.fixture
async def redis_client() -> AsyncGenerator[RedisClient, None]:
    """Create a mock Redis client for testing."""
    client = MockRedis()
    yield client
    # No cleanup needed for mock client

@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh database for each test."""
    engine = create_async_engine(
        TEST_SQLALCHEMY_DATABASE_URL,
        echo=True,
        future=True
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
        await session.rollback()
        await session.close()
    
    await engine.dispose()

@pytest.fixture(autouse=True)
def clear_websocket_state():
    """Clear WebSocket manager state before and after each test."""
    from app.core.websocket import manager
    manager.active_connections.clear()
    manager.connection_metadata.clear()
    manager.user_connections.clear()
    manager.message_history.clear()
    manager.message_by_id.clear()
    yield

    # After the test, clear the WebSocket state
    manager.active_connections.clear()
    manager.connection_metadata.clear()
    manager.user_connections.clear()
    manager.message_history.clear()
    manager.message_by_id.clear()

@pytest.fixture
def test_client(app: FastAPI) -> TestClient:
    """Create a test client that supports WebSocket connections."""
    return TestClient(app)

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Add the project root to the Python path if needed
project_root = backend_dir.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# This ensures both local and Docker environments can find the modules
os.environ["PYTHONPATH"] = f"{backend_dir}:{project_root}"

@pytest.fixture(scope="session")
def docker_compose_file(pytestconfig):
    """Get the Docker compose file path."""
    return os.path.join(str(pytestconfig.rootdir), "docker-compose.test.yml")

@pytest.fixture(scope="session")
def docker_compose_project_name():
    """Get the Docker compose project name."""
    return "mcp-chat-test"

print("CWD:", os.getcwd())
print("sys.path:", sys.path) 