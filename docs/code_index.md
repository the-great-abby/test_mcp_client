# Code Documentation Index

## backend/setup.py
---
## backend/test_ws.py
---
## backend/migrate.py
### Module Docstring
Simple script to run database migrations.

---
## backend/app/__init__.py
### Module Docstring
This module contains the FastAPI application and its components.

---
## backend/app/main.py
### Module Docstring
Main FastAPI application.

### Functions
#### def create_app()
Create FastAPI application.

---
## backend/app/core/auth.py
### Module Docstring
Authentication utilities.

### Functions
#### def create_access_token()
Create JWT access token.

#### def get_password_hash()
Get password hash.

---
## backend/app/core/logging.py
### Classes
#### class JSONFormatter
_No docstring_

### Functions
#### def setup_logging()
Configure logging with JSON formatting and appropriate log levels

Args:
    output_stream: Optional stream to write logs to. Defaults to sys.stdout.

#### def format()
_No docstring_

---
## backend/app/core/config.py
### Classes
#### class Settings
_No docstring_

### Functions
#### def get_settings()
Get cached settings instance.

#### def uppercase_log_level()
_No docstring_

#### def validate_postgres_port()
Validate and convert POSTGRES_PORT to integer.

#### def SQLALCHEMY_DATABASE_URI()
Get the database URI, either from DATABASE_URL or individual components.

#### def DATABASE_URL()
Alias for SQLALCHEMY_DATABASE_URI for backward compatibility.

#### def TEST_DATABASE_URL()
Get the test database URL.

#### def REDIS_URI()
_No docstring_

#### def MCP_WEBSOCKET_URL()
_No docstring_

#### def MCP_HTTP_URL()
_No docstring_

---
## backend/app/core/monitoring.py
### Module Docstring
Monitoring and telemetry functionality.

### Classes
#### class RateLimiter
Rate limiter using Redis.

#### class TelemetryService
Service for tracking API usage and metrics.

### Functions
#### def rate_limit()
Rate limit decorator for FastAPI endpoints.

#### def decorator()
_No docstring_

#### def __init__()
Initialize rate limiter.

#### def _get_key()
Generate Redis key for rate limiting.

#### def __init__()
Initialize telemetry service with Redis client.

#### def _get_user_key()
Generate Redis key for user-specific metrics.

#### def _get_global_key()
Generate Redis key for global metrics.

---
## backend/app/core/security.py
### Module Docstring
Security utilities for authentication and authorization.

### Functions
#### def verify_password()
Verify a password against a hash.

#### def get_password_hash()
Get password hash.

#### def create_access_token()
Create access token.

#### def decode_token()
Decode token.

---
## backend/app/core/chat_message.py
### Classes
#### class ChatMessage
Represents a chat message in the system.

### Functions
#### def __init__()
_No docstring_

#### def to_dict()
Convert the message to a dictionary for serialization.

#### def mark_delivered()
Mark the message as delivered.

#### def from_dict()
Create a ChatMessage instance from a dictionary.

---
## backend/app/core/cache.py
### Module Docstring
Redis caching functionality.

### Classes
#### class ModelResponseCache
Cache handler for model responses.

### Functions
#### def get_cache_key()
Generate a cache key from the given arguments.

The key is a colon-separated string containing all arguments.
- Dictionaries are formatted as 'key=value' pairs
- Empty lists/tuples are represented as '[]'
- Empty dictionaries are represented as '{}'
- None values are represented as 'None'

Example:
    get_cache_key("test", [], {"a": 1}) -> "test:[]:a=1"

#### def __init__()
_No docstring_

#### def _generate_cache_key()
Generate a unique cache key for the conversation context.

---
## backend/app/core/telemetry.py
### Classes
#### class TelemetryService
Service for tracking model usage and metrics.

### Functions
#### def __init__()
_No docstring_

---
## backend/app/core/websocket_rate_limiter.py
### Module Docstring
WebSocket rate limiting functionality.

### Classes
#### class WebSocketRateLimiter
Rate limiter for WebSocket connections and messages.

### Functions
#### def __init__()
Initialize rate limiter.

Args:
    redis: Optional Redis client
    max_connections: Maximum concurrent connections per user
    messages_per_minute: Maximum messages per minute
    messages_per_hour: Maximum messages per hour
    messages_per_day: Maximum messages per day
    max_messages_per_second: Maximum messages per second
    rate_limit_window: Rate limit window in seconds
    connect_timeout: Connection timeout in seconds
    message_timeout: Message timeout in seconds
    max_messages_per_minute: Alias for messages_per_minute (deprecated)
    max_messages_per_hour: Alias for messages_per_hour (deprecated)
    max_messages_per_day: Alias for messages_per_day (deprecated)

#### def _get_connection_key()
Get Redis key for connection tracking.

Args:
    client_id: Client ID
    user_id: User ID
    ip_address: IP address
    
Returns:
    str: Redis key

#### def _get_message_key()
Get Redis key for message tracking.

Args:
    client_id: Client ID
    user_id: User ID
    ip_address: IP address
    window: Time window (second, minute, hour, day)
    
Returns:
    str: Redis key

---
## backend/app/core/model.py
### Module Docstring
Model client implementation for handling AI model interactions.

### Classes
#### class ModelClient
Client for interacting with AI models.
Currently supports Anthropic's Claude models.

### Functions
#### def __init__()
Initialize the model client based on configuration.

#### def _init_real_client()
Initialize the real Anthropic client.

#### def format_prompt()
Format conversation messages for the model.

Args:
    conversation_messages: List of conversation messages
    system_prompt: Optional system prompt to set context
    
Returns:
    tuple: (formatted_messages, system_prompt)

---
## backend/app/core/redis.py
### Classes
#### class RedisClient
Redis client wrapper with async support.

### Functions
#### def __init__()
Initialize Redis client.

Args:
    host: Redis host
    port: Redis port
    db: Redis database number

---
## backend/app/core/connection_metadata.py
### Classes
#### class ConnectionMetadata
Metadata for tracking WebSocket connection state and attributes.

### Functions
#### def __init__()
_No docstring_

#### def to_dict()
Convert the metadata to a dictionary for serialization.

#### def update_last_seen()
Update the last_seen timestamp to current UTC time.

#### def set_typing()
Update the typing status of the connection.

#### def set_state()
Update the connection state.

#### def update_last_message()
Update the last message ID received by this connection.

---
## backend/app/core/errors.py
### Classes
#### class ErrorResponse
Standard error response model.

#### class AppError
Base class for application errors.

#### class RateLimitExceeded
Error raised when rate limit is exceeded.

#### class ConnectionLimitExceeded
Error raised when connection limit is exceeded.

#### class NotFoundError
Error raised when a resource is not found.

#### class ValidationError
Validation error.

#### class DataValidationError
Data validation error.

### Functions
#### def register_error_handlers()
Register all error handlers in order of specificity.

#### def setup_error_handlers()
Set up error handlers for the FastAPI application.

#### def __init__()
_No docstring_

#### def __init__()
_No docstring_

#### def __init__()
_No docstring_

#### def __init__()
_No docstring_

#### def __init__()
_No docstring_

#### def __init__()
_No docstring_

---
## backend/app/core/connection_state.py
### Module Docstring
Connection state enum.

### Classes
#### class ConnectionState
Connection state enum.

---
## backend/app/core/websocket.py
### Module Docstring
WebSocket connection management utilities.

### Classes
#### class WebSocketManager
Manages WebSocket connections and message handling.

### Functions
#### def __init__()
Initialize the WebSocket manager.

Args:
    redis_client: Optional Redis client for distributed state

#### def get_message_history()
Get the message history.

#### def get_message_by_id()
Get a message by its ID.

---
## backend/app/tests/__init__.py
### Module Docstring
Test package for the application.

---
## backend/app/tests/utils/user.py
### Module Docstring
User test utilities.

### Functions
#### def random_lower_string()
Generate a random lowercase string.

#### def random_email()
Generate a random email address.

---
## backend/app/tests/utils/__init__.py
### Module Docstring
Test utilities package.

---
## backend/app/tests/utils/utils.py
### Module Docstring
General test utilities.

### Functions
#### def random_lower_string()
Generate a random lowercase string.

#### def random_email()
Generate a random email address.

#### def get_test_db_url()
Get the test database URL based on environment settings.

---
## backend/app/utils/__init__.py
### Module Docstring
Utility functions for the application.

### Functions
#### def get_client_ip()
Extract the client IP address from a WebSocket connection.

Args:
    websocket: The WebSocket connection
    
Returns:
    str: The client's IP address or None if not found

---
## backend/app/models/user.py
### Module Docstring
User model for SQLAlchemy.

### Classes
#### class User
User model.

### Functions
#### def __repr__()
_No docstring_

---
## backend/app/models/health.py
### Classes
#### class Health
Health check record model.

#### class HealthResponse
Health check response model.

### Functions
#### def __repr__()
_No docstring_

---
## backend/app/models/conversation.py
### Module Docstring
Conversation model for SQLAlchemy.

### Classes
#### class Conversation
Conversation model.

### Functions
#### def __repr__()
_No docstring_

---
## backend/app/models/__init__.py
### Module Docstring
Model imports for SQLAlchemy.

---
## backend/app/models/message.py
### Classes
#### class MessageRole
_No docstring_

#### class Message
_No docstring_

### Functions
#### def __repr__()
_No docstring_

---
## backend/app/models/context.py
### Module Docstring
Context model for SQLAlchemy.

### Classes
#### class Context
_No docstring_

### Functions
#### def __repr__()
_No docstring_

---
## backend/app/schemas/auth.py
### Classes
#### class LoginRequest
Schema for login request.

#### class LoginResponse
Schema for login response.

---
## backend/app/schemas/user.py
### Classes
#### class UserBase
_No docstring_

#### class UserCreate
_No docstring_

#### class UserUpdate
_No docstring_

#### class UserResponse
_No docstring_

#### class Config
_No docstring_

---
## backend/app/schemas/token.py
### Module Docstring
Token schemas.

### Classes
#### class TokenPayload
Token payload schema.

---
## backend/app/schemas/conversation.py
### Classes
#### class ConversationBase
_No docstring_

#### class ConversationCreate
_No docstring_

#### class ConversationUpdate
_No docstring_

#### class ConversationResponse
_No docstring_

#### class Config
_No docstring_

---
## backend/app/schemas/message.py
### Classes
#### class MessageBase
_No docstring_

#### class MessageCreate
_No docstring_

#### class MessageResponse
_No docstring_

#### class MessageList
_No docstring_

#### class Config
_No docstring_

#### class Config
_No docstring_

---
## backend/app/schemas/context.py
### Classes
#### class ContextBase
_No docstring_

#### class ContextCreate
_No docstring_

#### class ContextResponse
_No docstring_

#### class Config
_No docstring_

---
## backend/app/schemas/websocket.py
### Module Docstring
WebSocket schemas.

### Classes
#### class WebSocketMessageType
WebSocket message types.

#### class WebSocketMessage
Base WebSocket message schema.

#### class WebSocketHistoryMessage
WebSocket message history schema.

#### class WebSocketPresenceMessage
WebSocket presence update schema.

#### class WebSocketErrorMessage
WebSocket error message schema.

---
## backend/app/scripts/setup_test_db.py
---
## backend/app/db/base_models.py
### Module Docstring
Import all SQLAlchemy models here to ensure they are registered with Base.metadata.
This file should be imported whenever you need to create all tables.

---
## backend/app/db/base_class.py
### Module Docstring
SQLAlchemy declarative base class.

---
## backend/app/db/session.py
### Module Docstring
Database session management.

---
## backend/app/db/engine.py
### Functions
#### def get_engine()
Return the SQLAlchemy async engine instance.

#### def get_async_sessionmaker()
Return a sessionmaker for the given async engine.

---
## backend/app/db/cli.py
### Module Docstring
CLI for running database migrations.

### Functions
#### def create()
Create all database tables.

#### def drop()
Drop all database tables.

#### def recreate()
Drop and recreate all tables.

#### def list_tables()
List all tables in the database.

#### def show_create_sql()
Show SQL for creating tables.

#### def show_drop_sql()
Show SQL for dropping tables.

---
## backend/app/db/redis.py
---
## backend/app/db/migrations.py
### Module Docstring
Direct SQLAlchemy migrations without Alembic.

---
## backend/app/db/base.py
### Module Docstring
SQLAlchemy base configuration.

---
## backend/app/api/deps.py
### Module Docstring
Dependencies for FastAPI endpoints.

---
## backend/app/api/health.py
---
## backend/app/api/__init__.py
### Module Docstring
API package for MCP Chat Backend.

---
## backend/app/api/errors.py
### Classes
#### class AppError
Base class for application errors.

#### class NotFoundError
Error raised when a resource is not found.

#### class ValidationError
Error raised when validation fails.

### Functions
#### def format_error_response()
Format error response consistently.

#### def format_validation_error()
Format a single validation error consistently.

#### def setup_error_handlers()
Set up error handlers for the application.

#### def __init__()
_No docstring_

#### def __init__()
_No docstring_

#### def __init__()
_No docstring_

---
## backend/app/api/router.py
---
## backend/app/api/v1/auth.py
---
## backend/app/api/v1/users.py
---
## backend/app/api/v1/health.py
### Module Docstring
Health check endpoints.

---
## backend/app/api/v1/messages.py
---
## backend/app/api/v1/conversations.py
---
## backend/app/api/v1/websocket.py
### Module Docstring
WebSocket endpoint for real-time communication.

---
## backend/app/services/telemetry.py
### Classes
#### class TelemetryService
_No docstring_

### Functions
#### def __init__()
_No docstring_

---
## backend/tests/conftest.py
### Module Docstring
Test configuration and fixtures.

### Functions
#### def app()
Get FastAPI application.

#### def test_settings()
Get test settings.

#### def client()
Get test client.

#### def setup_test_env()
Set up test environment variables.

#### def pytest_runtest_setup()
Set up test environment based on markers.

#### def pytest_runtest_teardown()
Clean up test environment after each test.

#### def load_test_env()
Ensure test environment variables are loaded.

#### def pytest_configure()
Register custom markers.

#### def event_loop()
Create event loop for tests.

#### def mock_model_client()
Get mock model client.

#### def test_client()
Get test client.

#### def ws_helper()
_No docstring_

#### def pytest_addoption()
_No docstring_

---
## backend/tests/__init__.py
### Module Docstring
Test package for MCP Chat Backend.

---
## backend/tests/helpers.py
### Module Docstring
Mock Redis client and pipeline for testing.

### Classes
#### class MockRedis
Mock Redis client for testing.

#### class MockRedisPipeline
Mock Redis pipeline for batched commands.

### Functions
#### def __init__()
_No docstring_

#### def _encode_key()
Convert key to string format for internal storage.

#### def _encode_value()
Convert value to bytes format for storage.

#### def _decode_value()
Convert stored value to bytes format for return.

#### def pipeline()
Get pipeline for batched commands.

#### def __init__()
_No docstring_

---
## backend/tests/mocks/anthropic_mock.py
### Classes
#### class MockStreamResponse
Mock response that yields chunks of text

#### class MockAnthropicMessage
Mock message for streaming responses

#### class MockAnthropicContent
Mock content object for streaming responses

#### class MockAnthropicEvent
Mock event object that matches the expected Anthropic client format

#### class MockAnthropicDelta
Mock delta object that matches the expected Anthropic client format

#### class MockModelClient
Mock client that simulates the Anthropic API

#### class MockAnthropicClient
_No docstring_

### Functions
#### def get_mock_anthropic()
_No docstring_

#### def __init__()
_No docstring_

#### def __aiter__()
_No docstring_

#### def __init__()
_No docstring_

#### def __init__()
_No docstring_

#### def __init__()
_No docstring_

#### def __init__()
_No docstring_

#### def __init__()
_No docstring_

#### def __init__()
_No docstring_

---
## backend/tests/mocks/redis_mock.py
### Module Docstring
Mock Redis implementation for testing.

### Classes
#### class MockRedisPipeline
Mock Redis pipeline with async context manager support.

#### class MockRedis
Mock Redis implementation for testing.

### Functions
#### def __init__()
_No docstring_

#### def __init__()
Initialize mock Redis.

#### def _encode()
Encode value to bytes.

#### def _decode()
Decode bytes to string or original type.

#### def _check_expiry()
Check if key has expired.

---
## backend/tests/unit/conftest.py
### Functions
#### def redis()
Provide an isolated mock Redis instance for unit tests.

#### def pipeline()
Provide a pipeline instance for the mock Redis.

---
## backend/tests/unit/test_websocket_rate_limit.py
### Module Docstring
Unit tests for WebSocket rate limiting functionality.

### Classes
#### class TestWebSocketRateLimiter
Test suite for WebSocket rate limiting.

### Functions
#### def auth_token()
Create a valid auth token for testing.

#### def mock_websocket()
Mock WebSocket connection.

#### def mock_user()
Mock user for testing.

#### def mock_redis()
Mock Redis client.

#### def rate_limiter()
Get rate limiter instance with mock Redis.

---
## backend/tests/unit/test_logging.py
### Functions
#### def capture_logs()
Capture logs in a StringIO buffer

#### def clean_logging()
Reset logging configuration before each test

#### def test_valid_log_levels()
Test that valid log levels are properly set

#### def test_invalid_log_level_defaults_to_info()
Test that invalid log levels default to INFO

#### def test_lowercase_log_level()
Test that lowercase log levels are converted to uppercase

#### def test_json_log_format()
Test that logs are properly formatted as JSON

#### def test_request_id_logging()
Test that request_id is included when present

#### def test_exception_logging()
Test that exceptions are properly logged

#### def test_third_party_logger_levels()
Test that third-party loggers are set to WARNING level

---
## backend/tests/unit/test_mock_redis.py
### Functions
#### def redis()
Provide a fresh MockRedis instance for each test.

#### def pipeline()
Provide a pipeline instance for each test.

---
## backend/tests/unit/test_auth.py
### Module Docstring
Unit tests for authentication functionality.

### Functions
#### def mock_user()
Get mock user.

#### def mock_superuser()
Get mock superuser.

---
## backend/tests/unit/test_errors.py
### Classes
#### class TestModel
_No docstring_

### Functions
#### def mock_request()
Create a mock request for testing.

#### def pydantic_test_app()
Minimal app fixture ONLY for the Pydantic validation test.

#### def pydantic_test_client()
Client fixture ONLY for the Pydantic validation test.

#### def test_pydantic_validation_error()
Test Pydantic validation error through the API.

---
## backend/tests/unit/test_health.py
### Module Docstring
Unit tests for health check endpoint.

---
## backend/tests/unit/websocket/conftest.py
### Module Docstring
Shared fixtures for WebSocket unit tests.

### Classes
#### class ErrorInjectingRedis
Redis mock that can inject errors for testing.

### Functions
#### def mock_redis()
Get mock Redis client.

#### def test_helpers()
List to track test helpers for cleanup.

#### def mock_websocket()
Get mock WebSocket instance.

#### def error_redis()
Get error injecting Redis instance.

#### def mock_ws_connect_error_marker()
If a test is marked with @pytest.mark.mock_ws_connect_error, set MOCK_WS_CONNECT_ERROR=1 for that test only.
Usage:
    @pytest.mark.mock_ws_connect_error
    def test_foo(...): ...

#### def __init__()
_No docstring_

#### def inject_error()
Inject an error to be raised on next operations.

---
## backend/tests/unit/websocket/test_system_messages.py
### Module Docstring
Unit tests for WebSocket system message handling.

These tests verify the behavior of system messages, including rate limit bypass functionality.

### Classes
#### class TestWebSocketSystemMessages
Test suite for WebSocket system message handling.

---
## backend/tests/unit/websocket/test_redis_errors.py
### Module Docstring
Unit tests for WebSocket Redis error handling.

These tests verify the system's behavior when Redis encounters errors or becomes unavailable.

### Classes
#### class TestWebSocketRedisErrors
Test suite for WebSocket Redis error handling.

#### class MockRedisWithErrors
_No docstring_

### Functions
#### def mock_redis()
Mock Redis client that raises errors.

#### def rate_limiter()
Create rate limiter with mock Redis.

#### def __init__()
_No docstring_

#### def enable_errors()
_No docstring_

#### def disable_errors()
_No docstring_

---
## backend/tests/integration/conftest.py
### Functions
#### def mock_anthropic()
Fixture to mock the Anthropic client for all tests

#### def mock_model()
Fixture to mock the ModelClient for testing

---
## backend/tests/integration/test_model_cache.py
### Functions
#### def mock_get()
_No docstring_

#### def mock_set()
_No docstring_

#### def mock_delete()
_No docstring_

---
## backend/tests/integration/test_cache.py
### Classes
#### class UnserializableObject
_No docstring_

---
## backend/tests/integration/websocket/test_stress.py
### Module Docstring
Integration tests for WebSocket stress testing.

These tests verify the WebSocket infrastructure's behavior under load
and stress conditions.

---
## backend/tests/integration/websocket/test_redis.py
### Module Docstring
Integration tests for WebSocket and Redis interactions.

These tests verify the integration between WebSocket connections and Redis-based rate limiting.
All tests use real Redis service and should be run in the test Docker network.

### Classes
#### class TestWebSocketRedisIntegration
Integration tests for WebSocket Redis functionality.

### Functions
#### def auth_token()
Create a valid auth token for testing.

---
## backend/tests/integration/websocket/test_basic.py
### Classes
#### class DummyUser
_No docstring_

### Functions
#### def test_client()
_No docstring_

#### def test_user()
_No docstring_

#### def auth_token()
_No docstring_

---
## backend/tests/integration/websocket/conftest.py
### Module Docstring
Shared fixtures for WebSocket integration tests.

### Functions
#### def auth_token()
Create an authentication token for testing.

#### def enforce_websocket_mode()
Fail fast if test is not explicitly marked with one of the required markers.
- If @pytest.mark.mock_service: require USE_MOCK_WEBSOCKET=1/true/yes
- If @pytest.mark.real_websocket: require USE_MOCK_WEBSOCKET not set or 0/false/no
- If @pytest.mark.real_redis: require REDIS_HOST=db-test or redis-test
- If @pytest.mark.real_anthropic: require ANTHROPIC_API_KEY set
- If none: fail (all tests must be explicitly marked)

---
## backend/tests/integration/websocket/test_recovery.py
### Module Docstring
Integration tests for WebSocket error recovery and resilience.

These tests verify the WebSocket connection's ability to handle various error conditions
and recover gracefully.

### Classes
#### class TestWebSocketRecovery
Test suite for WebSocket recovery functionality.

### Functions
#### def auth_token()
Create a valid auth token for testing.

---
## backend/tests/integration/websocket/test_rate_limit.py
### Module Docstring
WebSocket rate limiting integration tests.

---
## backend/tests/integration/websocket/test_anthropic_mock.py
### Module Docstring
Integration tests for Anthropic-style WebSocket streaming.

### Classes
#### class TestAnthropicStreamingMock
Test suite for Anthropic-style streaming functionality.

---
## backend/tests/integration/websocket/test_anthropic_external.py
---
## backend/tests/async/conftest.py
### Functions
#### def app()
FastAPI app fixture for async tests.

#### def auth_token()
_No docstring_

---
## backend/tests/async/test_monitoring.py
---
## backend/tests/async/websocket/conftest.py
### Module Docstring
Shared fixtures for WebSocket async tests.

### Functions
#### def test_helpers()
List to track test helpers for cleanup.

#### def test_token()
Create a test token.

---
## backend/tests/async/websocket/test_chat.py
### Module Docstring
WebSocket chat message streaming tests using async websockets library.
These tests verify the streaming behavior of chat messages in an async context.

---
## backend/tests/utils/real_websocket_client.py
### Classes
#### class RealWebSocketClient
Async WebSocket client for integration tests.
Connects to a real WebSocket server, sends/receives JSON, and tracks connection state.
Supports custom headers for external APIs.

### Functions
#### def __init__()
_No docstring_

#### def is_connected()
_No docstring_

---
## backend/tests/utils/websocket_fixtures.py
---
## backend/tests/utils/test_mock_redis.py
### Module Docstring
Tests for the Redis mock implementation.

---
## backend/tests/utils/test_sync_mock_redis.py
### Module Docstring
Sync-only tests for the SyncMockRedis and SyncMockPipeline.
These tests should be run in a synchronous context (e.g., with pytest, not pytest-asyncio).

### Functions
#### def test_pipeline_basic()
Test basic pipeline batching and result order (sync mock only).

---
## backend/tests/utils/mock_websocket.py
### Module Docstring
Mock WebSocket implementation for testing.

### Classes
#### class MockContentBlock
Mock content block that matches Anthropic's format.

#### class MockStreamResponse
Mock stream response generator.

#### class MockWebSocket
Mock WebSocket implementation for testing.

### Functions
#### def __init__()
_No docstring_

#### def to_dict()
_No docstring_

#### def __init__()
Initialize mock stream response.

Args:
    content: Content to stream
    chunk_size: Size of each chunk

#### def __aiter__()
_No docstring_

#### def debug_log()
_No docstring_

#### def debug_log()
_No docstring_

#### def __init__()
Initialize mock WebSocket.

Args:
    client_id: Client ID
    user_id: User ID
    ip_address: IP address
    query_params: Optional query parameters

#### def application_state()
Get the application state.

Returns:
    Current WebSocket state

#### def _validate_message()
Validate message structure. Returns error string if invalid, else None.

#### def set_client_state()
_No docstring_

#### def get_header()
Get header value.

Args:
    key: Header key

Returns:
    Header value if exists

#### def get_query_params()
Get query parameters.

Returns:
    Query parameters

#### def get_path_params()
Get path parameters.

Returns:
    Path parameters

#### def client()
Get the client information.

Returns:
    Client information dictionary

#### def client()
Set the client information.

Args:
    value: Client information dictionary

#### def set_auto_pong()
Enable or disable automatic pong responses.

Args:
    enabled: Whether to automatically respond to pings

#### def _check_rate_limit()
Generic rate limit checker. Returns error string if not allowed, else None.

#### def set_disconnected()
_No docstring_

---
## backend/tests/utils/__init__.py
### Module Docstring
Test utilities package.

---
## backend/tests/utils/websocket_test_helper.py
### Classes
#### class WebSocketTestHelper
Helper class for WebSocket testing.

### Functions
#### def __init__()
Initialize WebSocket test helper.

Args:
    websocket_manager: WebSocket manager instance
    rate_limiter: Optional rate limiter
    test_user_id: Test user ID
    test_ip: Test IP address
    auth_token: Optional auth token
    connect_timeout: Connection timeout in seconds
    message_timeout: Message timeout in seconds
    mock_mode: Whether to use the mock WebSocket (default False)
    ws_token_query: Whether to send token as query param (default False)

#### def get_connection_state()
Get the connection state for a client.

Args:
    client_id: Client ID

Returns:
    Current WebSocket state

#### def get_active_connections()
Get list of active connection IDs.

Returns:
    List of client IDs

#### def get_connection_count()
Get count of active connections.

Returns:
    Number of active connections

#### def ws_manager()
Expose the underlying WebSocketManager for test patching.

#### def debug_active_connections()
Log all active connection ids and their states/ids for debugging.

#### def add_connection()
_No docstring_

#### def remove_connection()
_No docstring_

---
## backend/tests/utils/mock_redis.py
### Module Docstring
Mock Redis implementation for testing.

### Classes
#### class MockRedis
Mock Redis implementation for testing.

#### class MockTransaction
_No docstring_

#### class MockPipeline
Mock Redis pipeline for batching commands.

#### class SyncMockRedis
Synchronous Mock Redis for use with sync test clients (e.g., FastAPI TestClient).

#### class SyncMockPipeline
Synchronous Mock Redis pipeline.

### Functions
#### def __init__()
Initialize mock Redis.

#### def _encode_key()
Encode key to bytes.

#### def _encode_value()
Encode value to bytes.

#### def _decode_value()
Decode bytes to value.

#### def _check_expiry()
Check if key has expired.

#### def _check_type()
Check if value is of expected type, raise RedisError if not.

#### def _handle_dict()
Convert value to dict.

#### def _handle_list()
Convert value to list.

#### def _handle_str()
Convert value to str.

#### def _handle_int()
Convert value to int.

#### def _handle_float()
Convert value to float.

#### def _handle_bytes()
Convert value to bytes.

#### def enable_errors()
Enable error mode for testing error handling.

#### def disable_errors()
Disable error mode.

#### def pipeline()
Create a pipeline for executing multiple commands atomically.

#### def multi()
Start a new transaction object.

#### def _reset_transaction_state()
Reset transaction and watch state after error or completion.

#### def __init__()
_No docstring_

#### def __init__()
_No docstring_

#### def __enter__()
_No docstring_

#### def __exit__()
_No docstring_

#### def watch()
_No docstring_

#### def __await__()
_No docstring_

#### def __init__()
_No docstring_

#### def _encode_key()
_No docstring_

#### def _encode_value()
_No docstring_

#### def set()
_No docstring_

#### def get()
_No docstring_

#### def delete()
_No docstring_

#### def hset()
_No docstring_

#### def hget()
_No docstring_

#### def lpush()
_No docstring_

#### def lpop()
_No docstring_

#### def rpush()
_No docstring_

#### def rpop()
_No docstring_

#### def keys()
_No docstring_

#### def exists()
_No docstring_

#### def expire()
_No docstring_

#### def ttl()
_No docstring_

#### def pttl()
_No docstring_

#### def incr()
_No docstring_

#### def decr()
_No docstring_

#### def incrby()
_No docstring_

#### def pipeline()
_No docstring_

#### def __init__()
_No docstring_

#### def set()
_No docstring_

#### def get()
_No docstring_

#### def delete()
_No docstring_

#### def hset()
_No docstring_

#### def hget()
_No docstring_

#### def lpush()
_No docstring_

#### def rpush()
_No docstring_

#### def execute()
_No docstring_

#### def is_falsy()
_No docstring_

---
## backend/scripts/anthropic_ws_direct.py
### Module Docstring
Standalone script to test Anthropic's WebSocket API (Claude-3 streaming).

Usage:
  export ANTHROPIC_API_KEY=your_real_key
  python backend/scripts/anthropic_ws_direct.py

This script will incur real API usage and should only be run intentionally.

---
## backend/scripts/setup_test_db.py
---
## app/core/websocket_rate_limiter.py
### Classes
#### class WebSocketRateLimiter
Rate limiter for WebSocket connections and messages.

### Functions
#### def __init__()
Initialize rate limiter.

Args:
    redis: Redis client instance
    max_connections: Maximum concurrent connections per IP
    window_seconds: Time window for rate limiting in seconds
    max_messages: Maximum messages per window per IP

---
## app/api/v1/websocket.py
### Module Docstring
WebSocket endpoint for real-time communication.

---

# Admin API Endpoints

All endpoints below require an **admin JWT token** in the `Authorization: Bearer <token>` header.

---

## GET `/api/v1/admin/rate-limits`
- **Description:** Get current rate limit configuration and status.
- **Permissions:** Admin only
- **Request:** None
- **Response:**
  ```json
  { "message": "Only admins can see this. Current rate limit config and status (stub)" }
  ```

---

## GET `/api/v1/admin/metrics`
- **Description:** Get a snapshot of key metrics for admin UI.
- **Permissions:** Admin only
- **Request:** None
- **Response:**
  ```json
  { "user_count": 42, "message_count": 1234 }
  ```

---

## GET `/api/v1/admin/rate-limit-violations`
- **Description:** List recent rate limit violations (WebSocket).
- **Permissions:** Admin only
- **Request:** None
- **Response:**
  ```json
  { "violations": [ { "identifier": "user123", "count": 3, "ttl": 57 } ] }
  ```

---

## POST `/api/v1/admin/rate-limits/reset`
- **Description:** Reset rate limit counters for a user or globally.
- **Permissions:** Admin only
- **Request:**
  - Optional query param: `user_id=<user_id>`
- **Response:**
  ```json
  { "message": "Rate limits reset for user user123" }
  ```

---

## GET `/api/v1/admin/users`
- **Description:** List all users.
- **Permissions:** Admin only
- **Request:** None
- **Response:**
  ```json
  { "users": [ { "id": "...", "username": "...", "email": "...", "is_active": true, "is_admin": false } ] }
  ```

---

## POST `/api/v1/admin/users/{user_id}/promote`
- **Description:** Promote a user to admin.
- **Permissions:** Admin only
- **Request:** None
- **Response:**
  ```json
  { "message": "User {user_id} promoted to admin" }
  ```

---

## POST `/api/v1/admin/users/{user_id}/deactivate`
- **Description:** Deactivate a user account.
- **Permissions:** Admin only
- **Request:** None
- **Response:**
  ```json
  { "message": "User {user_id} deactivated" }
  ```

---

## GET `/api/v1/admin/system-status`
- **Description:** Get system resource usage (CPU, memory, disk).
- **Permissions:** Admin only
- **Request:** None
- **Response:**
  ```json
  { "cpu": 12.3, "memory": 45.6, "disk": 78.9 }
  ```

---

## GET `/api/v1/admin/service-status`
- **Description:** Get status of dependent services (DB, Redis).
- **Permissions:** Admin only
- **Request:** None
- **Response:**
  ```json
  { "db": "ok", "redis": "ok" }
  ```

---

## GET `/api/v1/admin/audit-log`
- **Description:** Get recent admin actions and security events.
- **Permissions:** Admin only
- **Request:** None
- **Response:**
  ```json
  { "audit_log": [ { "timestamp": "...", "admin_id": "...", "action": "...", ... } ] }
  ```

---