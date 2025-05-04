import pytest
from tests.utils.mock_redis import SyncMockRedis

@pytest.fixture
def redis():
    """Provide an isolated mock Redis instance for unit tests."""
    mock = SyncMockRedis()
    yield mock
    # Clean up after each test
    mock.flushdb()

@pytest.fixture
def pipeline(redis):
    """Provide a pipeline instance for the mock Redis."""
    return redis.pipeline() 